"""Read the whole backbone of an ordinary Coot construction before native qualification."""
from pathlib import Path

from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _json
from .cif_model_context import _BACKBONE, _intent, _local_backbone
from .cif_phosphate_continuation import inspect_registered_backbone
from .postmr_lineage import read_postmr_construction


def _registered_partners(model, model_sha256, paths, sites, links, open_sites, terminal_sites):
    observations = inspect_registered_backbone(model, *paths)
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


def review_prepared_backbone(run, *, registration=None, discovery=None, continuations=None):
    """Read the recorded Coot model, local backbone, terminal consent and optional crystal partners.

    Complete registration accounts for the identity of each open end. The measured
    distance and angles describe the written construction, including physically
    open junctions. This reader supplies no forces or checkpoint selection.
    """
    paths = (registration, discovery, continuations)
    _need(all(p is None for p in paths) or all(p is not None for p in paths),
          "Supply registration, discovery input and backbone continuations together")
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
    sites, links, audit, open_sites = _local_backbone(model, intent, codes, review_open=True)
    _need(audit["input_sha256"] == saved["outputs"]["prepared"]["sha256"],
          "The measured backbone differs from the recorded Coot model")
    registration_info, partners = None, []
    status = "OPEN_INCOMING" if open_sites else "LOCAL_BACKBONE_CHECKED"
    if registration is not None:
        registration_info, partners = _registered_partners(model, audit["input_sha256"], paths, sites, links,
                                                         open_sites, terminal)
        status = "REGISTERED_FOR_REVIEW"
    _need(_read(report_path) == original and all(_read(run / name) == data for name, data in construction["files"].items()),
          "The ordinary preparation changed during backbone review")
    return dict(schema_version=1, policy_id="prepared-backbone-review-v1", status=status,
        construction_sha256=saved["record_sha256"], prepared_model=saved["outputs"]["prepared"],
        construction_dictionaries=saved["inputs"]["dictionaries"], local_links=links,
        protected_terminal_phosphates=terminal, without_local_incoming=sorted(
            (r for r in audit["checked"] if r["site"] in open_sites), key=lambda row: row["site"]),
        registration=registration_info, registered_continuations=partners, scientific_qualification="NOT_ASSESSED")
