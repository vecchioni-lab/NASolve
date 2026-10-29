"""Immutable explicit FANA enantiomer packages and local NAR record overlays.

A namespace observation is not a global reservation. Binding into a new consumer
rechecks the supplied CCD and caller records. No installed library is modified.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re

from .cif_attachment_sites import _pairs, _projection_values
from .cif_catalogue import _workbook_records
from .cif_fana_enantiomer import inspect_fana_enantiomer, INTENT
from .component_records import resolve_component_record, role_signature

POLICY_ID = "cif-local-fana-enantiomer-component-v1"
_FILES = {"inputs/parent.cif", "inputs/target.cif", "inputs/Ligands.xlsx",
          "namespace.json", "binding.json"}
_SCOPE = "DECLARED_CCD_FILENAMES_AND_CALLER_CODES"


def _codes(codes):
    if not isinstance(codes, (list, tuple, set)) or any(
            not isinstance(c, str) or not re.fullmatch(r"[A-Z0-9]{1,5}", c) for c in codes):
        raise ValueError("Require explicit uppercase reserved component codes")
    return sorted(set(codes))


def _namespace(ccd_root, reserved_codes):
    root = Path(ccd_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Require an explicit CCD directory")
    codes = set()
    # Inspect names only; even a broken symlink or invalid definition occupies
    # its code. This is the declared CCD layout, not a global PDB namespace.
    for directory in root.iterdir():
        if directory.is_symlink():
            raise ValueError("CCD namespace cannot traverse a directory symlink")
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            match = re.fullmatch(r"data_([A-Z0-9]{1,5})\.cif", path.name, flags=re.IGNORECASE)
            if match:
                codes.add(match[1].upper())
    if not codes:
        raise ValueError("Require a nonempty declared CCD filename namespace")
    return {"scope": _SCOPE, "ccd_codes": sorted(codes), "reserved_codes": _codes(reserved_codes)}


def _check_namespace(namespace):
    if (not isinstance(namespace, dict) or set(namespace) != {"scope", "ccd_codes", "reserved_codes"}
            or namespace["scope"] != _SCOPE or not namespace["ccd_codes"]
            or any(namespace[k] != _codes(namespace[k]) for k in ("ccd_codes", "reserved_codes"))):
        raise ValueError("Invalid frozen namespace observation")


def _available(code, namespace, records):
    _check_namespace(namespace)
    if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9]{1,3}", code):
        raise ValueError("Require an explicit PDB-compatible target code")
    if (code in namespace["ccd_codes"] or code in namespace["reserved_codes"]
            or any(str(r.get("Ligand code")).upper() == code for r in records)):
        raise ValueError("Target component code is occupied: " + code)


def _derive(parent, source_code, target, target_code, workbook, namespace, intent):
    records, _ = _workbook_records(workbook)
    _available(target_code, namespace, records)
    _projection_values(target, target_code)  # No unselected blocks become part of the package.
    relation = inspect_fana_enantiomer(parent, source_code, target, target_code,
                                      workbook=workbook, intent=intent)
    if relation["status"] != "ENANTIOMER_SOURCE_PASS":
        raise ValueError("Require a verified whole-component FANA enantiomer")
    original, resolution = resolve_component_record(records, source_code)
    record = deepcopy(original)
    record["Ligand code"] = target_code
    record["Name"] = "Explicit " + relation["target_family"] + " enantiomer of " + source_code
    for key in ("Abbreviation", "Notes", "Ref", "Entries"):
        if key in record:
            record[key] = None  # Parent descriptive claims do not describe a new component.
    for key in ("Sugar Type", "SugarType"):
        if key in record:
            record[key] = relation["target_family"].removeprefix("beta-")
    left, right = role_signature(original), role_signature(record)
    if left["atom_roles"] != right["atom_roles"]:
        raise ValueError("Derived NAR base roles changed")
    allowed = {"Sugar Type", "SugarType"}
    if any(left["context"].get(k) != right["context"].get(k) for k in left["context"] if k not in allowed):
        raise ValueError("Derived NAR chemical/base context changed")
    return {"schema_version": 1, "policy_id": POLICY_ID, "status": "LOCAL_COMPONENT_BOUND",
            "source_code": source_code, "target_code": target_code, "intent": intent,
            "record": record, "parent_record": original, "record_resolution": resolution,
            "parent_roles": left["atom_roles"], "target_roles": right["atom_roles"],
            "enantiomer": relation, "namespace": namespace,
            "global_reservation": False, "installed_registration": "NOT_RUN",
            "model_editing": "NOT_RUN", "native_qualification": "NOT_ASSESSED",
            "automatic_adoption": False}


def _digest(path):
    data = path.read_bytes()
    return {"sha256": sha256(data).hexdigest(), "size": len(data)}


def _save(path, value):
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def _load(path):
    return json.loads(path.read_text(), object_pairs_hook=_pairs)


def prepare_fana_enantiomer_component(source, source_code, target, target_code, *,
                                      workbook, ccd_root, reserved_codes, output, intent):
    """Freeze verified source bytes and a derived NAR record in a fresh directory.

    The caller explicitly supplies the target identity and occupied run codes.
    This records availability at preparation, without reserving a global name.
    The completion receipt is written last; failed partial output is preserved.
    """
    paths = [Path(p).expanduser().resolve(strict=True) for p in (source, target, workbook)]
    out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents):
        raise ValueError("Package output cannot traverse symlinks")
    if any(out.resolve().is_relative_to(p) or p.is_relative_to(out.resolve()) for p in paths):
        raise ValueError("Package output must be separate from inputs")
    before = {p: p.read_bytes() for p in paths}
    namespace = _namespace(ccd_root, reserved_codes)
    _derive(paths[0], source_code, paths[1], target_code, paths[2], namespace, intent)
    out.mkdir(parents=True, exist_ok=False)
    (out / "inputs").mkdir()
    names = ["inputs/parent.cif", "inputs/target.cif", "inputs/Ligands.xlsx"]
    for name, path in zip(names, paths):
        with (out / name).open("xb") as stream:
            stream.write(before[path])
    report = _derive(out/names[0], source_code, out/names[1], target_code,
                     out/names[2], namespace, intent)
    _save(out/"namespace.json", namespace)
    _save(out/"binding.json", report)
    if any(p.read_bytes() != data for p, data in before.items()) or _namespace(ccd_root, reserved_codes) != namespace:
        raise ValueError("Component inputs or namespace changed during preparation")
    _save(out/"receipt.json", {"schema_version": 1, "policy_id": POLICY_ID,
        "source_code": source_code, "target_code": target_code, "intent": intent,
        "files": {name: _digest(out/name) for name in sorted(_FILES)}})
    return read_fana_enantiomer_component(out)


def read_fana_enantiomer_component(package):
    """Recompute a frozen binding offline; this does not assert current availability."""
    root = Path(package).expanduser().resolve(strict=True)
    paths = list(root.rglob("*"))
    if any(p.is_symlink() for p in paths) or {p.relative_to(root).as_posix() for p in paths if p.is_file()} != _FILES | {"receipt.json"}:
        raise ValueError("Require an exact, nonsymlinked component package")
    before = {p: p.read_bytes() for p in paths if p.is_file()}
    receipt = _load(root/"receipt.json")
    if (set(receipt) != {"schema_version", "policy_id", "source_code", "target_code", "intent", "files"}
            or type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1
            or receipt["policy_id"] != POLICY_ID or set(receipt["files"]) != _FILES):
        raise ValueError("Invalid component completion receipt")
    if any(_digest(root/name) != wanted for name, wanted in receipt["files"].items()):
        raise ValueError("Component package checksum mismatch")
    report = _derive(root/"inputs/parent.cif", receipt["source_code"], root/"inputs/target.cif",
        receipt["target_code"], root/"inputs/Ligands.xlsx", _load(root/"namespace.json"), receipt["intent"])
    if report != _load(root/"binding.json") or any(p.read_bytes() != data for p, data in before.items()):
        raise ValueError("Component binding differs from fresh source derivation")
    return report


def bind_fana_enantiomer_records(package, records, *, ccd_root, reserved_codes):
    """Return a local record overlay after replay and fresh consumer namespace checks.

    Callers supply all records/codes their consumer will use. No global loader
    is patched, no workbook is written, and no process-wide reservation is made.
    """
    report = read_fana_enantiomer_component(package)
    records = list(records)  # The occupancy scan must not exhaust an iterator.
    _available(report["target_code"], _namespace(ccd_root, reserved_codes), records)
    return deepcopy([*records, report["record"]])
