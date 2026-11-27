"""Observe all requested crystal phosphates in the same native refinement."""
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


def _observe_grouped_model(observer, model, owners, observation):
    """Lend the full model for this synchronous observation while the registered phosphate forces are active."""
    from copy import deepcopy
    from .cif_refinement_output import _hierarchy, _scattering

    geometry = model.restraints_manager.geometry
    def atom_state():
        return _hierarchy(model), _scattering(model.get_xray_structure())[0]

    active = True
    def gradient_counts():
        if not active:
            raise ValueError("Phosphate counters are available only in the active preflight observation")
        return dict(joint_full_gradients=owners[0].joint_calls[(7,) * len(owners), True],
                    groups=[dict(continuation_id=o.inspection["registered_continuation"]["continuation_id"],
                                 full_gradients=o.calls[7, True]) for o in owners])

    before = atom_state()
    try:
        observer(model, deepcopy(observation), gradient_counts)
    finally:
        active = False
    if model.restraints_manager.geometry is not geometry or atom_state() != before:
        raise ValueError("Preflight observation changed the native model or restraint manager")
    for owner in owners:
        owner.owned[geometry].check_proxies(geometry)
        if verify_phosphate_bond(model, owner.inspection, owner.live_terms) != owner.bond:
            raise ValueError("Preflight observation changed a registered phosphate or its exclusion")


def run_phase(root, phase, expected_sha256, arguments, *, observe_preflight=None):
    """Execute a bound phase, or lend a grouped dry-run model to a trusted local observer.

    The observer receives the model, a detached phase observation and a live count reader.
    The caller owns the diagnostic process, the authenticated runtime and its fresh round.
    An observed dry run returns its restored phase observation without publishing a normal
    phosphate phase receipt. No saved request can select or supply a callback.
    """
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
    intent = request["phosphate"]
    grouped = "inspections" in intent
    if observe_preflight is not None:
        if (not callable(observe_preflight) or not dry or not grouped or
                request.get('policy_id') != 'round-local-registered-phosphate-set-execution-v12'):
            raise ValueError("A preflight observer requires a grouped v12 dry run and a trusted callable")
        if root.name != 'parallelity_runtime' or root.resolve().parent != Path.cwd() or (root/phase).exists():
            raise ValueError("Run the observation in its own fresh diagnostic round")
    inspections = intent["inspections"] if grouped else [intent["inspection"]]
    if grouped and len(inspections) < 2:
        raise ValueError("A grouped refinement requires at least two crystal phosphates")
    model_bytes = Path(arguments[1]).read_bytes()
    owners = [RegisteredPhosphateRuntime(inspection, model_bytes) for inspection in inspections]
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
    with patch.object(Program, "validate", observe_start), owners[0].active(*owners[1:]):
        result = run_compatible_refinement(arguments, evidence_directory=root/phase, chemistry_sites=sites,
                                           capture_written_model=True)
        if (result.iparams.refinement.dry_run is not dry or result.fmodels.fmodel_neutron() is not None):
            raise ValueError("Unexpected crystal phosphate refinement phase or scattering model")
        model = result.model
        geometry = model.restraints_manager.geometry
        for owner in owners:
            if dry and owner.full is None:
                # A native dry run can return before entering the optimizer's setup.
                owner.attach(model)
            if owner.live_terms is None or geometry not in owner.owned:
                raise ValueError("The final native model does not own every registered phosphate")
            owner.owned[geometry].check_proxies(geometry)
        if dry:
            geometry.energies_sites(sites_cart=model.get_xray_structure().sites_cart(), compute_gradients=True)
        joint_calls = owners[0].joint_calls[(7,) * len(owners), True]
        if joint_calls < 1:
            raise ValueError("Phenix did not evaluate gradients for all requested crystal phosphates together")
        edges = []
        for owner in owners:
            inspection = owner.inspection
            bond = verify_phosphate_bond(model, inspection, owner.live_terms)
            if bond != owner.bond:
                raise ValueError("The native model changed a phosphate bond or bonded-neighbour exclusion")
            fitted = dict(oxygen_operator_xyz=inspection["o3_image"], live_sources_sha256=recipe_digest(owner.live_terms),
                          families=dict(Counter(term["kind"] for term in owner.live_terms)), bond=bond)
            if grouped:
                fitted["continuation_id"] = inspection["registered_continuation"]["continuation_id"]
            edges.append(fitted)
        flags = reflection_change(initial, _observations(result.fmodels.fmodel_xray()))
        observation = dict(schema_version=2 if grouped else 1, phase=phase, request_sha256=expected_sha256,
                           parent_model_sha256=inspections[0]["model_sha256"], full_gradient_calls=joint_calls,
                           reflections=flags, **({"edges": edges} if grouped else edges[0]))
        if observe_preflight is not None:
            _observe_grouped_model(observe_preflight, model, owners, observation)
    if not all(owner.restored for owner in owners) or Program.validate is not validate:
        raise ValueError("The native phosphate or diffraction observation binding was not restored")
    restored = dict(observation, bindings_restored=True)
    if observe_preflight is not None:
        return restored
    with (root/phase/"phosphate.json").open("x", encoding="utf8") as handle:
        json.dump(restored, handle, sort_keys=True, allow_nan=False)
        handle.write("\n")
