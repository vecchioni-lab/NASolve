"""Bounded native interpretation of an explicitly selected restraint bundle.

The isolated worker uses the installed Phenix reader and interpretation APIs.
It inventories the resulting manager; it never refines, adopts a dictionary,
retries ReadySet or writes an edited coordinate model.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import signal
import subprocess
from tempfile import mkdtemp
import time
from typing import Mapping, Sequence

NATIVE_POLICY_ID = "cif-native-bundle-inventory-v1"
PHIL_NAMESPACE_POLICIES = ("direct", "refinement-root-to-interpreter-v1")
API_SOURCES = [
    {"url": "https://github.com/cctbx/cctbx_project/blob/master/mmtbx/monomer_library/server.py",
     "git_blob": "af1ac801d43c33b235584e1a6a59d82c137cd8de"},
    {"url": "https://github.com/cctbx/cctbx_project/blob/master/mmtbx/monomer_library/pdb_interpretation.py",
     "git_blob": "6e341cb0ba30ed1f71a79b4f3776cbe63df2d48e"},
    {"url": "https://github.com/cctbx/cctbx_project/blob/master/mmtbx/command_line/pdb_interpretation.py",
     "git_blob": "eff2ce4704afefd193fd6678939c508501d8fd25"},
    {"url": "https://github.com/cctbx/cctbx_project/blob/master/libtbx/phil/__init__.py",
     "git_blob": "0aca55ce594f5cf1c0a404378e904f2acb216575"},
    {"url": "https://github.com/cctbx/cctbx_project/blob/master/cctbx/geometry_restraints/manager.py",
     "git_blob": "354b7f62dffb8c4ce38c0e6c3e9ced66798c1e22"},
    {"url": "https://github.com/cctbx/cctbx_project/blob/master/cctbx/geometry_restraints/bond_bpl.cpp",
     "git_blob": "e6b1dca8c4159c2e1beba2858e803fcdaedf5470"},
]

# Written unchanged into the exclusive diagnostic directory.  No NASolve,
# Biopython, external candidate generator or model-optimization import occurs.
_NATIVE_WORKER = r'''from __future__ import print_function
import hashlib, json, math, sys, traceback
from pathlib import Path

spec = json.loads(Path(sys.argv[1]).read_text())
report = {"schema_version": 1, "policy_id": spec["policy_id"], "status": "RUNNING",
          "scientific_approval": "NOT_RUN", "automatic_adoption": False,
          "model_editing": "NOT_RUN", "optimization": "NOT_RUN", "readyset_retry": "NOT_RUN",
          "dictionary_loading": [], "phil_adaptations": [], "unsupported_fields": [],
          "monomer_mappings": {"status": "NOT_RUN", "rows": []},
          "geometry": {"status": "NOT_RUN"}}

class UnsupportedNativeAPI(RuntimeError):
    pass

def save():
    Path("native_validation.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")

def definitions(scope):
    return [{"path": row.path, "value_tokens": [word.value for word in row.object.words]}
            for row in scope.all_definitions()]

def atom_record(atom, index):
    labels = atom.fetch_labels()
    if int(atom.i_seq) != index:
        raise UnsupportedNativeAPI("Interpreted atom i_seq ordering does not match manager indices")
    xyz = [float(value) for value in atom.xyz]
    if not all(math.isfinite(value) for value in xyz):
        raise RuntimeError("Native hierarchy contains non-finite atom coordinates")
    return {"i_seq": index, "label": atom.id_str(), "atom_id": atom.name.strip(),
            "atom_name_field": atom.name, "element": atom.element,
            "xyz": xyz, "occupancy": float(atom.occ),
            "identity": {key: getattr(labels, key) for key in
                         ("model_id", "chain_id", "resseq", "icode", "resname", "altloc")}}

def monomer_metadata(monomer):
    if monomer is None:
        return {"status": "UNSUPPORTED", "reason": "no-effective-monomer"}
    chem = monomer.chem_comp
    return {"status": "RECORDED", "id": chem.id, "group": chem.group,
            "atom_ids": [atom.atom_id for atom in monomer.atom_list]}

try:
    from iotbx import phil
    from iotbx.file_reader import any_file
    from mmtbx.command_line import pdb_interpretation as native_command
    from mmtbx.monomer_library import server, pdb_interpretation
    report["installed_api_sources"] = []
    for module in (phil, native_command, server, pdb_interpretation):
        path = Path(module.__file__)
        report["installed_api_sources"].append({"module": module.__name__, "historical_path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None})

    sources = []
    for index, filename in enumerate(spec["phil_files"]):
        original = phil.parse(file_name=filename)
        before = definitions(original)
        if spec["phil_namespace_policy"] == "refinement-root-to-interpreter-v1":
            pieces = []
            for obj in original.objects:
                if obj.is_scope and obj.name == "refinement":
                    pieces.extend(child.as_str() for child in obj.objects)
                else:
                    pieces.append(obj.as_str())
            adapted = phil.parse(input_string="\n".join(pieces), source_info=filename)
        else:
            adapted = original
        after = definitions(adapted)
        expected = [{"path": row["path"][len("refinement."):] if
                     spec["phil_namespace_policy"] == "refinement-root-to-interpreter-v1"
                     and row["path"].startswith("refinement.") else row["path"],
                     "value_tokens": row["value_tokens"]} for row in before]
        if after != expected:
            raise UnsupportedNativeAPI("PHIL namespace preparation changed or discarded a parameter definition")
        canonical = "canonical_{:03d}.phil".format(index)
        Path(canonical).write_text(adapted.as_str())
        report["phil_adaptations"].append({"input": filename, "canonical": canonical,
            "policy": spec["phil_namespace_policy"], "definitions_preserved": len(before),
            "field_mapping": [{"source": left["path"], "interpreter": right["path"],
                               "value_tokens": right["value_tokens"]} for left, right in zip(before, after)]})
        sources.append(adapted)
    work, unused = native_command.get_master_phil().fetch(sources=sources, track_unused_definitions=True)
    report["unused_definitions"] = [{"path": row.path, "definition": row.object.as_str()} for row in unused]
    if unused:
        raise UnsupportedNativeAPI("Explicit PHIL contains unconsumed interpreter definitions")
    Path("native_effective.phil").write_text(work.as_str())
    params = work.extract()
    report["parameter_consumers"] = {
        "pdb_interpretation": "pdb_interpretation.process(params=...)",
        "geometry_restraints.edits": "processed.geometry_restraints_manager(params_edits=...)",
        "geometry_restraints.remove": "processed.geometry_restraints_manager(params_remove=...)"}

    mon_lib, energies = server.server(), server.ener_lib()
    for filename in spec["dictionaries"]:
        before = {key: id(value) for key, value in mon_lib.comp_comp_id_dict.items()}
        previous_mods = {key: id(value) for key, value in mon_lib.mod_mod_id_dict.items()}
        loaded = any_file(file_name=filename)
        cif = loaded.file_object.model()
        mon_lib.process_cif_object(cif_object=cif, file_name=loaded.file_name, process_tor=True)
        energies.process_cif_object(cif_object=cif, file_name=loaded.file_name, process_tor=False)
        changed = [key for key, value in mon_lib.comp_comp_id_dict.items() if before.get(key) != id(value)]
        mods = [key for key, value in mon_lib.mod_mod_id_dict.items() if previous_mods.get(key) != id(value)]
        report["dictionary_loading"].append({"input": filename, "status": "RECORDED",
            "component_metadata": [monomer_metadata(mon_lib.comp_comp_id_dict[key]) for key in sorted(changed)],
            "modification_ids": sorted(mods)})
    save()
    processed = pdb_interpretation.process(mon_lib_srv=mon_lib, ener_lib=energies,
        params=params.pdb_interpretation, file_name=spec["model"], strict_conflict_handling=True,
        substitute_non_crystallographic_unit_cell_if_necessary=True,
        keep_monomer_mappings=True, log=sys.stdout)
    acp = processed.all_chain_proxies
    report["fatal_problems"] = acp.fatal_problems_message()
    report["atoms"] = [atom_record(atom, index) for index, atom in enumerate(acp.pdb_atoms)]
    report["atom_count"] = len(report["atoms"])
    rows = []
    if hasattr(acp, "all_monomer_mappings"):
        for mm in acp.all_monomer_mappings:
            entry = {"residue_label": mm.pdb_residue_id_str, "chain_id": mm.chainid,
                     "interpreted_residue_name": mm.residue_name,
                     "metadata": monomer_metadata(mm.monomer),
                     "resname": None, "literal_identity": {"status": "UNSUPPORTED"}}
            residue_atoms = mm.pdb_residue.atoms()
            if len(residue_atoms):
                labels = residue_atoms[0].fetch_labels()
                identity = {key: getattr(labels, key) for key in
                            ("model_id", "chain_id", "resseq", "icode", "resname", "altloc")}
                entry["literal_identity"] = {"status": "RECORDED", **identity}
                entry["resname"] = labels.resname.strip()
                entry["site"] = labels.chain_id.strip() + ":" + labels.resseq.strip() + labels.icode.strip()
            else:
                report["unsupported_fields"].append("monomer_mapping.literal_identity")
            for field in ("chem_mod_ids", "missing_non_hydrogen_atoms", "missing_hydrogen_atoms", "unexpected_atoms"):
                if hasattr(mm, field):
                    entry[field] = {"status": "RECORDED",
                                    "ids" if field == "chem_mod_ids" else "atom_ids": sorted(getattr(mm, field))}
                else:
                    entry[field] = {"status": "UNSUPPORTED"}
                    report["unsupported_fields"].append("monomer_mapping." + field)
            rows.append(entry)
        report["monomer_mappings"] = {"status": "RECORDED", "rows": rows}
    else:
        report["monomer_mappings"] = {"status": "UNSUPPORTED", "rows": []}
        report["unsupported_fields"].append("all_monomer_mappings")
    save()
    if report["fatal_problems"] is not None:
        raise RuntimeError("Native interpretation reports fatal scattering or energy-type problems: " + str(report["fatal_problems"]))
    geo = processed.geometry_restraints_manager(params_edits=params.geometry_restraints.edits,
                                               params_remove=params.geometry_restraints.remove)
    if geo is None:
        raise UnsupportedNativeAPI("Native interpretation did not construct a geometry restraints manager")
    sites = acp.sites_cart_exact()
    labels = [row["label"] for row in report["atoms"]]
    if len(sites) != len(labels):
        raise RuntimeError("Native geometry sites and interpreted atom indices differ")
    pairs = geo.pair_proxies(sites_cart=sites)
    bonds = pairs.bond_proxies

    def endpoints(indices):
        indices = [int(index) for index in indices]
        if any(index < 0 or index >= len(labels) for index in indices):
            raise RuntimeError("Native proxy references an out-of-range atom index")
        return {"i_seqs": indices, "atoms": [labels[index] for index in indices]}

    simple, asu = [], []
    for proxy in bonds.simple:
        row = endpoints(proxy.i_seqs)
        row.update(distance_ideal=float(proxy.distance_ideal), weight=float(proxy.weight),
                   origin_id=getattr(proxy, "origin_id", None))
        operator = getattr(proxy, "rt_mx_ji", None)
        row["symmetry_operation"] = None if operator is None else str(operator)
        simple.append(row)
    for proxy in bonds.asu:
        row = endpoints((proxy.i_seq, proxy.j_seq))
        row.update(j_sym=int(proxy.j_sym), distance_ideal=float(proxy.distance_ideal),
                   weight=float(proxy.weight), origin_id=getattr(proxy, "origin_id", None))
        try:
            row["symmetry_operation"] = {"status": "RECORDED",
                "operator": str(bonds.asu_mappings().get_rt_mx_ji(pair=proxy))}
        except (AttributeError, TypeError):
            row["symmetry_operation"] = {"status": "UNSUPPORTED"}
            report["unsupported_fields"].append("asu_bond_symmetry_operation")
        asu.append(row)
    counts, statuses = {"bond_simple": len(simple), "bond_asu": len(asu)}, {}
    for kind in ("angle", "dihedral", "const_dihedral", "chirality", "planarity", "parallelity"):
        field = kind + "_proxies"
        if hasattr(geo, field):
            value = getattr(geo, field)
            counts[kind], statuses[kind] = (0 if value is None else len(value)), "RECORDED"
        else:
            counts[kind], statuses[kind] = None, "UNSUPPORTED"
            report["unsupported_fields"].append(field)
    report["geometry"] = {"status": "RECORDED", "simple_bonds": simple, "asu_bonds": asu,
                          "proxy_counts": counts, "proxy_count_status": statuses,
                          "sites_cart_exact": [[float(value) for value in xyz] for xyz in sites]}
    report["status"] = "REVIEW"
except (ImportError, UnsupportedNativeAPI, AttributeError, TypeError) as exc:
    report.update(status="UNSUPPORTED", error=type(exc).__name__ + ": " + str(exc))
    traceback.print_exc()
except Exception as exc:
    report.update(status="FAILED", error=type(exc).__name__ + ": " + str(exc))
    traceback.print_exc()
finally:
    save()
sys.exit(0 if report["status"] == "REVIEW" else 2)
'''


def _sha(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _artifact(path: Path, work: Path) -> dict:
    payload = path.read_bytes()
    return {"anchor": "native_directory", "path": path.relative_to(work).as_posix(),
            "sha256": _sha(payload), "size": len(payload)}


def _stop(process: subprocess.Popen) -> None:
    if process.returncode is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        process.kill()
    process.wait(timeout=5)


def _check_native_report(report: dict, dictionary_count: int) -> None:
    if (not isinstance(report, dict) or report.get("schema_version") != 1
            or report.get("policy_id") != NATIVE_POLICY_ID
            or report.get("status") not in {"REVIEW", "FAILED", "UNSUPPORTED"}):
        raise ValueError("Native worker returned an unsupported diagnostic receipt schema")
    if report["status"] == "REVIEW":
        if (report.get("automatic_adoption") is not False or report.get("scientific_approval") != "NOT_RUN"
                or report.get("model_editing") != "NOT_RUN" or report.get("optimization") != "NOT_RUN"):
            raise ValueError("Native worker returned an unsupported approval or model-editing claim")
        if (not isinstance(report.get("dictionary_loading"), list)
                or len(report["dictionary_loading"]) != dictionary_count
                or any(row.get("status") != "RECORDED" for row in report["dictionary_loading"])):
            raise ValueError("Native worker did not record the complete selected dictionary bundle")
        atoms = report.get("atoms")
        if not isinstance(atoms, list) or report.get("atom_count") != len(atoms):
            raise ValueError("Native worker did not record its interpreted atom inventory")
        geometry = report.get("geometry", {})
        if (geometry.get("status") != "RECORDED"
                or not isinstance(geometry.get("simple_bonds"), list)
                or not isinstance(geometry.get("asu_bonds"), list)):
            raise ValueError("Native worker did not record its geometry manager inventory")


def inspect_native_bundle(model: Path, dictionaries: Sequence[Path], output_parent: Path,
                          executable: Path, *, environment: Mapping[str, str],
                          phenix_version: str, timeout_seconds: float = 600,
                          phil_files: Sequence[Path] = (),
                          phil_namespace_policy: str = "direct") -> dict:
    """Freeze explicit inputs and record native reader/manager evidence.

    ``executable`` is the selected installation's phenix.python. Optional PHIL
    namespace adaptation is performed by its native parser, with every active
    definition's path/value tokens checked and all unused definitions rejected.
    Successful execution remains REVIEW, never chemistry or linkage approval.
    """
    if phil_namespace_policy not in PHIL_NAMESPACE_POLICIES:
        raise ValueError("Unsupported native PHIL namespace policy")
    if not phenix_version or not str(phenix_version).strip():
        raise ValueError("An explicit Phenix version is required")
    if not isfinite(float(timeout_seconds)) or timeout_seconds <= 0:
        raise ValueError("Native interpretation timeout must be finite and positive")
    model, executable = Path(model).resolve(), Path(executable).resolve()
    dictionaries, phil_files = [Path(path).resolve() for path in dictionaries], [Path(path).resolve() for path in phil_files]
    if not dictionaries:
        raise ValueError("At least one explicit dictionary is required")
    paths = [model, *dictionaries, *phil_files]
    if len(set(paths)) != len(paths):
        raise ValueError("Native inputs must be distinct explicit files")
    payloads = [path.read_bytes() for path in paths]
    output_parent = Path(output_parent).resolve()
    if any(output_parent == path.parent or path.parent in output_parent.parents for path in paths):
        raise ValueError("Native output parent must be outside every source input directory")
    output_parent.mkdir(parents=True, exist_ok=True)
    work = Path(mkdtemp(prefix="cif-native-", dir=output_parent))
    inputs = work / "inputs"
    inputs.mkdir()
    frozen, descriptors = [], []
    for index, (path, payload) in enumerate(zip(paths, payloads)):
        role = "model" if index == 0 else "dictionary" if index <= len(dictionaries) else "phil"
        target = inputs / ("{:03d}_".format(index) + role + path.suffix)
        with target.open("xb") as handle:
            handle.write(payload)
        frozen.append(target)
        descriptors.append({"input_index": index, "role": role, "source_provenance": str(path),
                            **_artifact(target, work)})
    spec = {"policy_id": NATIVE_POLICY_ID, "model": frozen[0].relative_to(work).as_posix(),
            "dictionaries": [path.relative_to(work).as_posix() for path in frozen[1:1+len(dictionaries)]],
            "phil_files": [path.relative_to(work).as_posix() for path in frozen[1+len(dictionaries):]],
            "phil_namespace_policy": phil_namespace_policy}
    (work / "native_spec.json").write_text(json.dumps(spec, indent=2) + "\n")
    (work / "native_worker.py").write_text(_NATIVE_WORKER, encoding="utf-8")
    command = [str(executable), "native_worker.py", "native_spec.json"]
    clock = time.monotonic()
    receipt = {"schema_version": 1, "audit_kind": "cif_native_bundle_inspection", "policy_id": NATIVE_POLICY_ID,
        "status": "FAILED", "native_directory": str(work), "command": command, "inputs": descriptors,
        "phenix_version": str(phenix_version), "executable_provenance": str(executable),
        "api_sources": API_SOURCES, "phil_namespace_policy": phil_namespace_policy,
        "automatic_adoption": False, "scientific_approval": "NOT_RUN",
        "readyset_retry": "NOT_RUN", "optimization": "NOT_RUN", "model_editing": "NOT_RUN",
        "native_validation": None,
        "execution": {"status": "NOT_RUN", "started_at": datetime.now(timezone.utc).isoformat(),
                      "timeout_seconds": timeout_seconds}}
    try:
        receipt["executable_sha256"] = _sha(executable.read_bytes())
        with (work / "native.log").open("xb") as log:
            process = subprocess.Popen(command, cwd=work, env=dict(environment), stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name == "posix")
            try:
                code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _stop(process)
                receipt["execution"].update(status="TIMED_OUT", returncode=process.returncode)
                receipt["error"] = "Owned native interpreter process group exceeded the requested timeout"
            except BaseException:
                _stop(process)
                raise
            else:
                receipt["execution"].update(status="COMPLETED" if code == 0 else "FAILED", returncode=code)
                report_path = work / "native_validation.json"
                if not report_path.is_file() or report_path.is_symlink():
                    receipt["error"] = "Native worker did not produce the exact regular native_validation.json"
                else:
                    native = json.loads(report_path.read_text())
                    _check_native_report(native, len(dictionaries))
                    receipt["native_validation"] = native
                    if native.get("status") == "REVIEW" and code == 0:
                        receipt["status"] = "REVIEW"
                    elif native.get("status") == "UNSUPPORTED":
                        receipt["status"] = "UNSUPPORTED"
                    else:
                        receipt["error"] = native.get("error", "Native worker failed or returned an unsupported result state")
    except (OSError, ValueError) as exc:
        receipt["error"] = type(exc).__name__ + ": " + str(exc)
        receipt["execution"]["status"] = "FAILED"
    preserved = []
    frozen_preserved = []
    for path, snapshot, payload in zip(paths, frozen, payloads):
        try:
            preserved.append(path.read_bytes() == payload)
        except OSError:
            preserved.append(False)
        try:
            frozen_preserved.append(snapshot.read_bytes() == payload)
        except OSError:
            frozen_preserved.append(False)
    receipt["source_preserved"] = all(preserved)
    receipt["frozen_inputs_preserved"] = all(frozen_preserved)
    receipt["input_integrity"] = [{"input_index": index, "source_preserved": original,
                                  "snapshot_preserved": snapshot} for index, (original, snapshot) in
                                 enumerate(zip(preserved, frozen_preserved))]
    if not all(preserved) or not all(frozen_preserved):
        receipt.update(status="FAILED", error="Original or frozen native inputs changed during interpretation")
    receipt["execution"].update(finished_at=datetime.now(timezone.utc).isoformat(),
                                elapsed_seconds=round(time.monotonic() - clock, 6))
    receipt["outputs"] = [_artifact(path, work) for path in sorted(work.rglob("*"))
                          if path.is_file() and not path.is_symlink()]
    receipt["symlink_outputs"] = [path.relative_to(work).as_posix() for path in sorted(work.rglob("*")) if path.is_symlink()]
    receipt["receipt"] = {"anchor": "native_directory", "path": "native_receipt.json"}
    with (work / "native_receipt.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return receipt
