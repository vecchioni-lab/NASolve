"""Read the whole backbone of an ordinary Coot construction before native qualification."""
from hashlib import sha256
from pathlib import Path

from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _json
from .cif_model_context import _BACKBONE, _intent, _local_backbone
from .cif_phosphate_continuation import (
    RegisteredContinuation, _endpoint_atoms, _inherit_measured, _sources_match, inspect_registered_backbone,
)
from .postmr_lineage import read_postmr_construction


def _registered_partners(observations, model_sha256, sites, links, open_sites, terminal_sites):
    donors = {source for source, _ in links}
    targets = set()
    partners = []
    for observation in observations:
        _need(observation["model_sha256"] == model_sha256, "Crystal registration differs from the ordinary Coot model")
        edge = observation["registered_continuation"]
        _need(edge["measurement_status"] == "MEASURED",
              f"Cannot measure registered continuation {edge['continuation_id']}: {edge['reason']}")
        source, target = edge["source"]["coordinate_site"], edge["target"]["coordinate_site"]
        _need(edge["oxygen_operator_xyz"] != "x,y,z", "A crystal continuation requires a nonidentity image")
        _need(target not in terminal_sites, f"Registered phosphorus {target} is a protected terminal phosphate")
        _need(source not in donors, f"Registered O3' at {source} already has an outgoing partner")
        _need(target in open_sites and target not in targets, f"Registered P at {target} is not an open incoming end")
        _need(_BACKBONE <= sites[source]["atoms"] and
              all(angle is not None for angle in observation["coordinate_angles_degrees"].values()),
              f"Incomplete backbone or unoccupied angle atoms at {source} or {target}")
        donors.add(source)
        targets.add(target)
        partners.append(dict(id=edge["continuation_id"], logical_o3_site=edge["source"]["logical_site"],
            logical_phosphate_site=edge["target"]["logical_site"], o3_site=source, phosphate_site=target,
            o3_image=observation["o3_image"], target_operator_xyz=edge["target_operator_xyz"],
            distance_A=observation["distance_A"], coordinate_angles_degrees=observation["coordinate_angles_degrees"]))
    missing = sorted(set(open_sites) - targets)
    _need(not missing, "Open incoming phosphates lack a registered partner: " + ", ".join(missing))
    first = observations[0]["registered_continuation"]
    return dict(copy_id=first["copy_id"], graph_sha256=first["registered_graph_sha256"], **first["sources"]), partners


def _native_candidate(source, candidate, receipt, paths, observations, local, intent, codes):
    from .cif_phosphate_reference import measure_written_phosphate, read_phosphate_reference_set
    from .cif_phosphate_runtime import RegisteredPhosphateRuntime

    source_sites, source_links, source_audit, source_open = local
    sites, links, audit, open_sites = _local_backbone(candidate, intent, codes, review_open=True)
    original_bytes, original_atoms = _endpoint_atoms(source, source_sites)
    candidate_bytes, candidate_atoms = _endpoint_atoms(candidate, sites)
    # Includes residue identities, element, charge and occupied/unoccupied state.
    # The image-transfer owner below also checks hydrogen identities at each junction.
    if ({k for k in original_atoms if k[4] not in {"H", "D"}} !=
            {k for k in candidate_atoms if k[4] not in {"H", "D"}}):
        raise ValueError("The candidate changed modeled residue or atom identities")
    _need(links == source_links and set(open_sites) == set(source_open),
          "The candidate has different local bonds or open incoming phosphates")
    _need(sha256(original_bytes).hexdigest() == source_audit["input_sha256"] and
          sha256(candidate_bytes).hexdigest() == audit["input_sha256"], "Backbone inputs changed during comparison")
    transferred = []
    for observed in observations:
        reg = RegisteredContinuation(observed["registered_continuation"]["continuation_id"], *paths)
        transferred.append(_inherit_measured(source, candidate, reg, observed))
    RegisteredPhosphateRuntime.check_group(transferred)
    _need(all(row["model_sha256"] == audit["input_sha256"] for row in transferred),
          "Candidate crystal coordinates differ from the audited native input")
    endpoints = [(row["phosphate"][0], row["o3"][0]) for row in transferred]
    proof, references = read_phosphate_reference_set(receipt, candidate_bytes, endpoints)
    _need(proof["status"] == "REVIEW" and proof["execution"]["returncode"] == 0,
          "Require a successful native interpretation of these candidate inputs")
    local_links = {tuple(link) for link in links}
    partners = []
    for row, ref in zip(transferred, references, strict=True):
        _need(ref["status"] != "COMPETING_ENDPOINT_BOND", ref.get("reason", "Competing phosphate bond"))
        measured = measure_written_phosphate(candidate, dict(row, native_reference_links=ref),
                                             model_sha256=audit["input_sha256"])
        matched = ref["groups"][0]["links"]
        for donor, acceptor in matched:
            _need((donor, acceptor) in local_links,
                  f"Native reference {donor} O3′ to {acceptor} P is absent from the audited local bonds")
        for term in measured["terms"]:
            for sample in (term["written"], *term["ordinary_links"]):
                if sample["value"] is None:
                    donor = sample.get("o3_site", measured["o3_site"])
                    acceptor = sample.get("phosphate_site", measured["phosphate_site"])
                    raise ValueError(f"Unmeasurable native {term['kind']} at {donor} to {acceptor}: {sample['reason']}")
        bond, = (term for term in measured["terms"] if term["kind"] == "bond_simple")
        edge = row["registered_continuation"]
        partners.append(dict(id=edge["continuation_id"], o3_site=row["o3"][0], phosphate_site=row["phosphate"][0],
            o3_image=row["o3_image"], distance_A=row["distance_A"], coordinate_angles_degrees=row["coordinate_angles_degrees"],
            matched_local_links=matched, native_terms_sha256=measured["reference_terms_sha256"],
            measured_terms_per_link=len(measured["terms"]),
            native_bond_target_A=bond["target"], native_bond_sigma_A=bond["restraint_width"],
            frame_transfer=edge["frame_transfer"]))
    _need(_read(candidate) == candidate_bytes, "Candidate model changed during native readback")
    return dict(status="NATIVE_INPUTS_VERIFIED_FOR_REVIEW", candidate_model_sha256=audit["input_sha256"],
        native_receipt_sha256=references[0]["native_receipt_sha256"], phenix_version=proof["phenix_version"],
        native_inputs=[{k: r[k] for k in ("anchor", "path", "role", "sha256", "size")} for r in proof["inputs"]],
        registered_continuations=partners)


def review_prepared_backbone(run, *, registration=None, discovery=None, continuations=None,
                             candidate_model=None, native_receipt=None):
    """Read the recorded Coot model, local backbone, terminal consent and optional crystal partners.

    Complete registration accounts for the identity of each open end. The measured
    distance and angles describe the written construction, including physically
    open junctions. With candidate coordinates and a native interpretation,
    also compare the returned backbone, frame and actual reference terms.
    """
    paths = (registration, discovery, continuations)
    _need(all(p is None for p in paths) or all(p is not None for p in paths),
          "Supply registration, discovery input and backbone continuations together")
    _need((candidate_model is None) == (native_receipt is None), "Supply the candidate model and native receipt together")
    _need(candidate_model is None or registration is not None, "A native candidate needs the complete crystal registration")
    run = Path(run)
    construction = read_postmr_construction(run)
    saved = construction["report"]
    model = construction["model"]
    report_path = run / "report.json"
    original = _read(report_path)
    report = _json(original)
    _need(isinstance(report, dict) and report.get("workflow") == "automr", "Require the original AutoMR run report")
    intent = _intent(report)
    controls = saved["controls"]
    terminal = sorted(intent["post_mr_plan"]["allow_op3_sites"])
    _need(terminal == controls["allow_op3_sites"] and not controls["passthrough_sites"],
          "Frozen phosphate/backbone intent differs from the recorded Coot construction")
    codes = {row["after"] for row in controls["actions"]}
    local = _local_backbone(model, intent, codes, review_open=True)
    sites, links, audit, open_sites = local
    _need(audit["input_sha256"] == saved["outputs"]["prepared"]["sha256"],
          "The measured backbone differs from the recorded Coot model")
    registration_info, partners = None, []
    candidate_info = {}
    status = "OPEN_INCOMING" if open_sites else "LOCAL_BACKBONE_CHECKED"
    if registration is not None:
        paths = tuple(Path(p).expanduser() for p in paths)
        observations = inspect_registered_backbone(model, *paths)
        registration_info, partners = _registered_partners(observations, audit["input_sha256"], sites, links, open_sites, terminal)
        status = "REGISTERED_FOR_REVIEW"
        if candidate_model is not None:
            candidate_info["native_candidate"] = _native_candidate(model, Path(candidate_model).expanduser(), native_receipt,
                                                                  paths, observations, local, intent, codes)
        _need(_sources_match(RegisteredContinuation(partners[0]["id"], *paths), registration_info),
              "Crystal registration changed during preparation review")
    _need(_read(report_path) == original and all(_read(run / name) == data for name, data in construction["files"].items()),
          "The ordinary preparation changed during backbone review")
    return dict(schema_version=1, policy_id="prepared-backbone-review-v1", status=status,
        construction_sha256=saved["record_sha256"], prepared_model=saved["outputs"]["prepared"],
        construction_dictionaries=saved["inputs"]["dictionaries"], local_links=links,
        protected_terminal_phosphates=terminal, without_local_incoming=sorted(
            (r for r in audit["checked"] if r["site"] in open_sites), key=lambda row: row["site"]),
        registration=registration_info, registered_continuations=partners, scientific_qualification="NOT_ASSESSED", **candidate_info)
