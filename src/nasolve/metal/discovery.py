"""Place one retained AutoSol site using explicitly named atoms in a parent.

The shared image owner chooses crystallographic copies, not a chemical geometry.
Q, B and charge are declared starting hypotheses; raw discovery Q is never used
as a quantitative occupancy. Multi-site/cluster placement needs a separate policy.
"""
from copy import deepcopy
import json
import math

from .binding import AtomKey
from .recipe import RecipeError, canonical, _fields

POLICY_ID = 'single-autosol-site-placement-v1'


def _need(value, message):
    if not value:
        raise RecipeError(message)


def _review_inputs(context, recipe, discovery, atoms, *, report=None):
    from ..refinement_external_autosol import review_external_autosol
    from ..run_context import resolve_artifact_path
    from ..topostitch_images import closest_atom_images
    from ..topostitch_periodic import crystal_from_pdb_bytes
    from .context import parse_pdb
    from .materialize import _source, _sources

    _fields(discovery, {'policy_id', 'external_autosol', 'anchor_nodes',
                       'max_image_tests', 'image_ambiguity_tolerance_A'}, set(), 'discovery')
    _need(discovery['policy_id'] == POLICY_ID, 'Unsupported discovery placement policy')
    budget = discovery['max_image_tests']
    _need(type(budget) is int and 1 <= budget <= 2_000_000,
          'Require a per-anchor image budget from 1 to 2000000')
    tolerance = discovery['image_ambiguity_tolerance_A']
    _need(type(tolerance) in (int, float) and math.isfinite(tolerance) and 0 < tolerance <= .05,
          'Require image ambiguity tolerance in (0, 0.05] Angstrom')
    anchors = discovery['anchor_nodes']
    _need(isinstance(anchors, list) and 1 <= len(anchors) <= 8
          and all(isinstance(n, str) for n in anchors) and len(set(anchors)) == len(anchors),
          'Require one to eight distinct explicit anchor nodes')
    nodes = {n['id']: n for n in recipe.to_dict()['nodes']}
    metals = [n for n in nodes.values() if n['kind'] == 'metal']
    _need(len(metals) == 1, 'This discovery policy places one metal; clusters require a coherent multi-site policy')
    _need(all(n in nodes and nodes[n]['kind'] != 'metal' for n in anchors),
          'Image anchors must be explicit donor or atom nodes')
    parent = context.to_dict()
    _need(parent['sources']['phases'] is None,
          'External discovery cannot replace an approved parent phase source')
    raw, frozen_report = _sources(context, report=report)
    imported = parse_pdb(raw, checkpoint_id=parent['checkpoint_id'])
    _need(imported.to_dict() == context.imported.to_dict()
          and all(parent[k] == imported.to_dict()[k] for k in ('model', 'atomic_state')),
          'Parent inventory differs from captured source')
    external = discovery['external_autosol']
    _need(isinstance(external, dict), 'Require an explicit external AutoSol declaration')
    observations = resolve_artifact_path(parent['sources']['observations'], context.run)
    _, source_review = review_external_autosol(context.run, external,
        report=json.loads(frozen_report), observations=observations,
        phase_labels=external.get('phase_labels'))
    sites = source_review['sites']
    _need(len(sites) == 1 and sites[0]['element'] == metals[0]['element'].upper(),
          'Require exactly one discovered site matching the declared metal; no silent site omission')

    gemmi, cell, name = crystal_from_pdb_bytes(raw)
    group = gemmi.find_spacegroup_by_name(name)
    for role in ('mr_model', 'heavy_atoms'):
        _, other_cell, other_name = crystal_from_pdb_bytes(_source(external['sources'][role], context.run))
        _need(tuple(cell.parameters) == tuple(other_cell.parameters)
              and group.xhm() == gemmi.find_spacegroup_by_name(other_name).xhm(),
              'Parent, original MR and heavy-atom crystal frames differ')
    _need(isinstance(atoms, dict), 'Require explicit atom bindings')
    bindings = {key: AtomKey(**value) for key, value in atoms.items()}
    preview = context.preview(recipe, atom_bindings=bindings)
    resolved = {row['node_id']: row for row in preview['nodes']}
    image_rows = []
    identities = set()
    for node_id in anchors:
        row = resolved[node_id]
        _need(not row['issues'] and row['atom'] is not None,
              'Every discovery anchor must resolve to one exact parent atom')
        atom = row['atom']
        identity = canonical(atom['key'])
        _need(identity not in identities, 'Discovery anchors must name distinct parent atoms')
        identities.add(identity)
        matches = closest_atom_images(atom['xyz'], sites[0]['coordinates'], cell, group, gemmi,
                                      max_image_tests=budget)
        _need(matches[1]['distance_A'] - matches[0]['distance_A'] > tolerance,
              'Ambiguous metal image at a declared anchor; explicit review is required')
        image_rows.append(dict(node_id=node_id, atom=atom, nearest_images=matches))
    operators = {row['nearest_images'][0]['image']['operator_xyz'] for row in image_rows}
    _need(len(operators) == 1,
          'Declared anchors prefer different metal images; review the intended site context')
    image = image_rows[0]['nearest_images'][0]['image']
    fractional = cell.fractionalize(gemmi.Position(*sites[0]['coordinates']))
    transformed = gemmi.Op(image['operator_xyz']).apply_to_xyz(list(fractional))
    xyz = list(cell.orthogonalize(gemmi.Fractional(*transformed)))
    return dict(source_site=deepcopy(sites[0]), selected_image=image, metal_xyz=xyz,
                anchors=image_rows, cell_parameters=list(cell.parameters), space_group=group.xhm(),
                phase_origin=source_review['phase_origin'], producer_scope=source_review['producer_scope'],
                discovery_occupancy='RAW_DISCOVERY_OUTPUT_NOT_QUANTITATIVE_Q',
                initial_Q_B_charge='EXPLICIT_HYPOTHESIS_NOT_MEASURED',
                geometry_accepted=False, ordinary_autosol_approval=False, refined=False)


def _review(context, recipe, discovery, atoms, *, report=None):
    try:
        return _review_inputs(context, recipe, discovery, atoms, report=report)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, ImportError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot verify discovered placement: ' + str(exc)) from exc


def plan_autosol_site(context, recipe, *, external_autosol, anchor_nodes, site,
                      atoms=None, max_image_tests=100_000, image_ambiguity_tolerance_A=.01):
    """Return an explicit schema-2 plan without writing or changing a parent.

    ``site`` declares node_id, key, occupancy, b_iso, formal_charge and source_note.
    Coordinates come only from the verified discovery image. Every named anchor
    must independently prefer the same unambiguous image. No distance target,
    charge, occupancy, B value, geometry optimization or selection is inferred.
    """
    from .materialize import _plan
    _fields(site, {'node_id', 'key', 'occupancy', 'b_iso', 'formal_charge', 'source_note'}, set(), 'site')
    discovery = dict(policy_id=POLICY_ID, external_autosol=deepcopy(external_autosol),
        anchor_nodes=deepcopy(anchor_nodes), max_image_tests=max_image_tests,
        image_ambiguity_tolerance_A=image_ambiguity_tolerance_A)
    atoms = deepcopy(atoms) if atoms is not None else {}
    review = _review(context, recipe, discovery, atoms)
    plan = dict(kind='metal-placement-plan', schema_version=2,
                context_id=context.to_dict()['context_id'], recipe_sha256=recipe.sha256,
                atoms=atoms, sites=[dict(deepcopy(site), xyz=review['metal_xyz'])],
                discovery=dict(discovery, review=review))
    return _plan(plan, context, recipe)


def verify_autosol_plan(context, recipe, plan, *, report=None):
    """Rederive discovery identity and coordinates during ordinary build/replay."""
    discovery = deepcopy(plan['discovery'])
    _need(isinstance(discovery, dict) and 'review' in discovery, 'Missing discovery image review')
    recorded = discovery.pop('review')
    actual = _review(context, recipe, discovery, plan['atoms'], report=report)
    _need(canonical(actual) == canonical(recorded), 'Discovery image review differs from its exact inputs')
    _need(len(plan['sites']) == 1 and plan['sites'][0]['xyz'] == actual['metal_xyz'],
          'Placed coordinates differ from the verified AutoSol image')


def recheck_autosol_sources(context, plan):
    """Close the read/write window using the already verified immutable pins."""
    from .materialize import _source
    for reference in plan['discovery']['external_autosol']['sources'].values():
        _source(reference, context.run)
