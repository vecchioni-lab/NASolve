"""Explicit graph-bound furanose construction seeds; not refinement or adoption.

A bounded acyclic-arm search and proper body fit retain source bond geometry and
all declared hands. Base movement has an explicit limit. Native links, NAR policy,
clashes and achieved geometry must be checked separately on the emitted model.
"""
from itertools import combinations
import math
from pathlib import Path
import shutil

import numpy as np

from .cif_attachment_profiles import inspect_attachment_profile
from .cif_attachment_sites import _model
from .cif_captured_geometry import _observed
from .cif_construction_provenance import _pdb_inventory
from .cif_fana_bridge import _moving_group, _search
from .cif_fana_component import _digest, _load, _save
from .cif_fana_junction import _path
from .cif_stereochemistry_audit import _values, _graph, _coordinates, _volume
from .cif_whole_furanose import base_fragment_atoms, read_base_anchored_furanose_control, _hand
from .cif_base_displacement import POLICY_ID as BASE_B_POLICY, inherit_base_displacement

POLICY_ID = 'cif-graph-furanose-bounded-bridge-seed-v1'
BASE_B_SEED_POLICY = 'cif-graph-furanose-bounded-bridge-seed-v2'
_FILES = {'config.json', 'model.pdb', 'seed.json'}


def phosphate_arm_rotors(roles, graph, bonds, *, leaving_atom):
    """Find the single-bond rotations in a declared furanose phosphate arm.

    Return atom names from the source, including the leaving atom. A caller
    working on a linked model must verify its actual retained atoms and links.
    """
    phosphorus = roles["phosphate"]
    if leaving_atom == roles["five_o"] or leaving_atom not in graph[phosphorus]:
        raise ValueError("Require a declared leaving atom bonded to the phosphate")
    protected = base_fragment_atoms(roles, graph) | {
        roles[r] for r in ("anomeric", "ring_o", "ring_c2", "ring_c3", "ring_c4", "three_o")
    }
    groups = []
    for left, right in (("ring_c4", "five_c"), ("five_c", "five_o"), ("five_o", "phosphate")):
        a, b = roles[left], roles[right]
        group = _moving_group(graph, bonds, a, b)
        if not {leaving_atom, phosphorus} <= group or group & protected:
            raise ValueError("Rotor must move only the acyclic source phosphate arm")
        groups.append({"axis_roles": [left, right], "axis_atoms": [a, b],
                       "moving_source_atoms": sorted(group)})
    return groups


def _seed(control, config):
    if (set(config)-{'base_b_policy'} != {'endpoint_weight', 'max_base_displacement'}
            or ('base_b_policy' in config and config['base_b_policy'] != BASE_B_POLICY)):
        raise ValueError('Require explicit endpoint weight and base displacement limit')
    for key, maximum in [('endpoint_weight', 1000), ('max_base_displacement', 5)]:
        value = config[key]
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 < value <= maximum:
            raise ValueError('Invalid finite search bound: '+key)
    if config['endpoint_weight'] < 1:
        raise ValueError('Endpoint weight must be at least one')
    placement = read_base_anchored_furanose_control(control); code = placement['component']
    context = placement['context']; selected = context['site']; chain, resid = selected.split(':')
    profile = inspect_attachment_profile(control/'source.cif', code, workbook=control/'Ligands.xlsx')
    roles = profile['bindings']; values = _values(control/'numerical.cif', code)
    elements, bonds, _, graph = _graph(values); _, coordinates = _coordinates(values, source=False)
    leaving = context['ports']['phosphate']['leaving_atom']
    retained = set(placement['model_heavy_atoms'])
    heavy = sorted(n for n, e in elements.items() if e not in {'H', 'D'})
    if set(heavy)-retained != {leaving}:
        raise ValueError('Require exactly one declared virtual heavy leaving atom')
    base = base_fragment_atoms(roles,graph) & retained
    index = {n:i for i,n in enumerate(heavy)}; xyz = np.array([coordinates[n] for n in heavy], dtype=float)
    groups = phosphate_arm_rotors(roles, graph, bonds, leaving_atom=leaving)
    axes = [(index[g['axis_atoms'][0]], index[g['axis_atoms'][1]],
             [index[n] for n in heavy if n in g['moving_source_atoms']]) for g in groups]
    frame = _pdb_inventory(control/'frame.pdb'); prior = _pdb_inventory(control/'model.pdb')
    anchors = [*placement['target_frame_atoms'], roles['phosphate'], roles['three_o'], leaving]
    host_code = _model((control/'frame.pdb').read_bytes())[selected]['component']
    host_profile = inspect_attachment_profile(control/'host.cif', host_code, workbook=control/'Ligands.xlsx')
    host = host_profile['bindings']
    host_anchors = [*placement['host_frame_atoms'], host['phosphate'], host['three_o']]
    target = [frame[(chain, resid, '', '', n)]['xyz'] for n in host_anchors]
    partner = context['ports']['phosphate']['partner']; pc, pr = partner['site'].split(':')
    target.append(frame[(pc, pr, '', '', partner['atom_id'])]['xyz'])
    weights = np.array([1.]*3+[float(config['endpoint_weight'])]*3)
    points, search = _search(xyz, axes, [index[n] for n in anchors], np.array(target), weights)
    fitted = {n:points[index[n]].tolist() for n in heavy}
    rounded = {n:[float(f'{x:.3f}') for x in fitted[n]] for n in retained}
    displacement = {n:math.dist(rounded[n], prior[(chain, resid, '', '', n)]['xyz']) for n in sorted(base)}
    if not displacement or max(displacement.values()) > config['max_base_displacement']:
        raise ValueError('Selected fit exceeds the explicit base displacement limit')
    lengths = []; final_lengths = []; angles = []; final_angles = []
    for a, b in bonds:
        if {a, b} <= retained:
            original = math.dist(coordinates[a], coordinates[b])
            lengths.append(abs(math.dist(fitted[a], fitted[b])-original))
            final_lengths.append(abs(math.dist(rounded[a], rounded[b])-original))
    for center in retained:
        for a, b in combinations(sorted(graph[center] & retained), 2):
            triple = (a, center, b)
            observations = [_observed('angle', [x[n] for n in triple]) for x in (coordinates, fitted, rounded)]
            if any(v is None or not math.isfinite(v) for v in observations):
                raise ValueError('Degenerate retained bond angle')
            angles.append(abs(observations[1]-observations[0])); final_angles.append(abs(observations[2]-observations[0]))
    hands = []
    for row in placement['retained_hands']:
        center, ordered = row['center'], row['ordered_neighbors']
        volumes = [_volume(x, center, ordered) for x in (coordinates, fitted, rounded)]
        if not _hand(volumes[0], volumes[1]) or not _hand(volumes[0], volumes[2]):
            raise ValueError('Seed changes or degenerates a declared source stereocentre')
        hands.append({'center':center, 'ordered_neighbors':ordered, 'source_volume':volumes[0], 'full_volume':volumes[1], 'rounded_volume':volumes[2]})
    if max(lengths) > 1e-9 or max(angles) > 1e-8 or max(final_lengths) > .002:
        raise ValueError('Kinematic or PDB-rounding preservation failed')
    lines = []
    for line in (control/'model.pdb').read_text().splitlines(keepends=True):
        if line[:6] in {'ATOM  ', 'HETATM'} and (line[21].strip() or '_', str(int(line[22:26]))) == (chain, resid):
            fields = ''.join(f'{x:8.3f}' for x in rounded[line[12:16].strip()])
            if len(fields) != 24:
                raise ValueError('Seed exceeds fixed PDB coordinate fields')
            line = line[:30]+fields+line[54:]
        lines.append(line)
    model = ''.join(lines)
    if _model(model.encode()) != _model((control/'model.pdb').read_bytes()):
        raise ValueError('Seed changed the model element/site inventory')
    junctions = []
    for port, role in [('phosphate', 'phosphate'), ('alcohol', 'three_o')]:
        p = context['ports'][port]['partner']; pc, pr = p['site'].split(':'); n = roles[role]
        other = frame[(pc, pr, '', '', p['atom_id'])]['xyz']
        junctions.append({'target_atom':n, 'partner_atom':p['site']+':'+p['atom_id'],
            'before':math.dist(prior[(chain, resid, '', '', n)]['xyz'], other),
            'full_precision':math.dist(fitted[n], other), 'pdb_rounded':math.dist(rounded[n], other)})
    report = {'schema_version':1, 'policy_id':POLICY_ID, 'status':'FURANOSE_BRIDGE_SEED_REVIEW',
        'component':code, 'site':selected, 'config':config, 'source_profile':profile['matched_profile'],
        'virtual_leaving_atom':leaving, 'virtual_atom_written':False,
        'virtual_partner_error':math.dist(fitted[leaving], target[-1]),
        'fit_anchors':anchors, 'fit_weights':weights.tolist(), 'rotors':groups, 'search':search,
        'full_precision_heavy_coordinates':{n:fitted[n] for n in sorted(retained)},
        'source_hands':hands, 'junctions':junctions, 'base_displacement_angstrom':displacement,
        'max_base_displacement_angstrom':max(displacement.values()),
        'preservation':{'all_declared_source_hands':True, 'max_bond_length_error':max(lengths),
            'max_angle_error_degrees':max(angles), 'rounded_max_bond_length_error':max(final_lengths),
            'rounded_max_angle_error_degrees':max(final_angles), 'bystander_records_exact':True},
        'numpy_version':np.__version__, 'native_linkage':'NOT_ASSESSED', 'NAR_policy':'REQUIRES_CURRENT_MODEL_BINDING',
        'chemical_qualification':'NOT_ESTABLISHED', 'clashes':'NOT_ASSESSED',
        'automatic_adoption':False, 'diffraction_refinement':'NOT_RUN'}
    if 'base_b_policy' in config:
        report['policy_id'] = BASE_B_SEED_POLICY
        model, report['base_displacement'] = inherit_base_displacement(host_profile,profile,
            _values(control/'host.cif',host_code),_values(control/'source.cif',code),
            (control/'frame.pdb').read_text(),model,selected)
    return report, model


def prepare_furanose_bridge_seed(placement, output, *, endpoint_weight, max_base_displacement,
                                 inherit_equivalent_base_b=False):
    """Freeze a fresh bounded seed, retaining the original placement and chemistry."""
    control = _path(placement, directory=True); out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents) or out.is_relative_to(control) or control.is_relative_to(out):
        raise ValueError('Seed output must be separate from its preserved source')
    config = {'endpoint_weight':endpoint_weight, 'max_base_displacement':max_base_displacement}
    if type(inherit_equivalent_base_b) is not bool:
        raise ValueError('Require a boolean choice for equivalent-base starting displacement')
    if inherit_equivalent_base_b: config['base_b_policy'] = BASE_B_POLICY
    before = {p:p.read_bytes() for p in control.rglob('*') if p.is_file()}
    report, model = _seed(control, config)
    if any(p.read_bytes()!=data for p,data in before.items()):raise ValueError('Seed authority changed during preflight')
    out.mkdir(parents=True, exist_ok=False); shutil.copytree(control, out/'placement'); _save(out/'config.json', config)
    frozen, frozen_model = _seed(out/'placement', config)
    if frozen!=report or frozen_model!=model or any(p.read_bytes()!=data for p,data in before.items()):
        raise ValueError('Seed authority changed while freezing inputs')
    with (out/'model.pdb').open('x') as stream:stream.write(model)
    _save(out/'seed.json', report)
    files = {p.relative_to(out).as_posix():_digest(p) for p in out.rglob('*') if p.is_file()}
    _save(out/'receipt.json', {'schema_version':1, 'policy_id':report['policy_id'], 'files':files})
    return read_furanose_bridge_seed(out)


def read_furanose_bridge_seed(directory):
    """Recompute graph binding, bounded search and exact output without native tools."""
    root = _path(directory, directory=True); paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths) or {p.relative_to(root).as_posix() for p in paths if p.is_dir()} != {'placement'}:
        raise ValueError('Require exact nonsymlinked seed directories')
    # The inner reader enforces its own exact inventory, including no extra directories.
    read_base_anchored_furanose_control(root/'placement')
    expected = _FILES | {'receipt.json'} | {'placement/'+p.name for p in (root/'placement').iterdir()}
    before = {p:p.read_bytes() for p in paths if p.is_file()}
    if {p.relative_to(root).as_posix() for p in before} != expected:
        raise ValueError('Unexpected or missing seed package file')
    r = _load(root/'receipt.json')
    if (set(r) != {'schema_version', 'policy_id', 'files'} or type(r['schema_version']) is not int
            or r['schema_version']!=1 or r['policy_id'] not in (POLICY_ID,BASE_B_SEED_POLICY) or set(r['files'])!=expected-{'receipt.json'}
            or any(_digest(root/name)!=value for name,value in r['files'].items())):
        raise ValueError('Invalid seed receipt or checksum')
    report, model = _seed(root/'placement', _load(root/'config.json'))
    if (r['policy_id']!=report['policy_id'] or report!=_load(root/'seed.json')
            or model.encode()!=(root/'model.pdb').read_bytes() or any(p.read_bytes()!=b for p,b in before.items())):
        raise ValueError('Stored seed differs from fresh derivation')
    return report
