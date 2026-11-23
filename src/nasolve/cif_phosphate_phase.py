"""Observe one registered phosphate in the actual Phenix preflight and refinement."""
from collections import Counter
from functools import wraps
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

from .cif_phosphate_restraints import verify_phosphate_bond
from .cif_phosphate_runtime import RegisteredPhosphateRuntime
from .cif_refinement_runtime import run_compatible_refinement
from .topostitch_recipe import recipe_digest


def _observations(fmodel):
    obs, flags = fmodel.f_obs(), fmodel.r_free_flags()
    indices = list(map(tuple, obs.indices()))
    if len(set(indices)) != len(indices) or indices != list(map(tuple, flags.indices())):
        raise ValueError("Phosphate refinement requires unique, consistently indexed experimental and free-set data")
    return {h: (float(f), float(s), bool(b)) for h, f, s, b in
            zip(indices, obs.data(), obs.sigmas(), flags.data(), strict=True)}


def reflection_summary(rows):
    ordered = sorted(rows.items())
    flags = [[h, val[2]] for h, val in ordered]
    n_free = sum(flag for _, flag in flags)
    return dict(work=len(rows)-n_free, free=n_free, flags_sha256=recipe_digest(flags),
                observations_sha256=recipe_digest(ordered))


def reflection_change(before, after):
    if not before or not after or any(h not in before or v[2] != before[h][2] for h, v in after.items()):
        raise ValueError("Phenix added an unverified reflection or changed a work/free assignment")
    removed = set(before).difference(after)
    return dict(start=reflection_summary(before), finish=reflection_summary(after),
                removed_work=sum(not before[h][2] for h in removed), removed_free=sum(before[h][2] for h in removed))


def run_phase(root, phase, expected_sha256, arguments):
    from phenix.programs.phenix_refine import Program
    request_bytes = (root / "request.json").read_bytes()
    if sha256(request_bytes).hexdigest() != expected_sha256:
        raise ValueError("Registered phosphate request changed before native execution")
    request = json.loads(request_bytes)
    dry = phase == "preflight"
    expected = request["command"][1:]
    if dry:
        expected = ["output.prefix=parallelity_runtime/preflight/native" if a == "output.prefix=refined" else a
                    for a in expected] + ["refinement.dry_run=True"]
    if phase not in ("preflight", "refine") or arguments != expected:
        raise ValueError("Phosphate stage or native argument order differs from the saved round")
    for path, ref in zip(arguments, request["inputs"]):
        data = Path(path).read_bytes()
        if len(data) != ref["size"] or sha256(data).hexdigest() != ref["sha256"]:
            raise ValueError("A native phosphate refinement input changed")
    inspection = request["phosphate"]["inspection"]
    model_bytes = Path(arguments[1]).read_bytes()
    owner = RegisteredPhosphateRuntime(inspection, model_bytes)
    initial = {}
    validate = Program.validate

    @wraps(validate)
    def observe_start(program, *args, **kwargs):
        result = validate(program, *args, **kwargs)
        if initial or program.joint_xn:
            raise ValueError("Require one native X-ray refinement model")
        initial.update(_observations(program.fmodel))
        return result

    sites = [{key: row[key] for key in ("site", "component")} for row in request.get("chemistry_projections", [])]
    with patch.object(Program, "validate", observe_start), owner.active():
        result = run_compatible_refinement(arguments, evidence_directory=root/phase, chemistry_sites=sites,
                                           capture_written_model=True)
        if (result.iparams.refinement.dry_run is not dry or result.fmodels.fmodel_neutron() is not None):
            raise ValueError("Unexpected crystal phosphate refinement phase or scattering model")
        model = result.model
        if dry and owner.full is None:
            # A native dry run can return before entering the optimizer's setup.
            owner.attach(model)
        geometry = model.restraints_manager.geometry
        if owner.live_terms is None or geometry not in owner.owned:
            raise ValueError("The final native model does not own the registered phosphate")
        owner.owned[geometry].check_proxies(geometry)
        if dry:
            geometry.energies_sites(sites_cart=model.get_xray_structure().sites_cart(), compute_gradients=True)
        if owner.calls[7, True] < 1:
            raise ValueError("Phenix did not evaluate gradients for all seven phosphate orientation restraints")
        bond = verify_phosphate_bond(model, inspection, owner.live_terms)
        if bond != owner.bond:
            raise ValueError("The native model changed its phosphate bond or bonded-neighbour exclusions")
        flags = reflection_change(initial, _observations(result.fmodels.fmodel_xray()))
        families = Counter(term["kind"] for term in owner.live_terms)
        observation = dict(schema_version=1, phase=phase, request_sha256=expected_sha256,
            parent_model_sha256=inspection["model_sha256"], oxygen_operator_xyz=inspection["o3_image"],
            live_sources_sha256=recipe_digest(owner.live_terms), families=dict(families), bond=bond,
            full_gradient_calls=owner.calls[7, True], reflections=flags)
    if not owner.restored or Program.validate is not validate:
        raise ValueError("The native phosphate or diffraction observation binding was not restored")
    with (root/phase/"phosphate.json").open("x", encoding="utf8") as handle:
        json.dump(dict(observation, bindings_restored=True), handle, sort_keys=True, allow_nan=False)
        handle.write("\n")
