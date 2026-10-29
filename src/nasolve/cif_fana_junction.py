"""Explicit missing-angle adapter for a frozen three-site FANA control.

This compiles native template values, not new chemistry. A captured existing
bond, source projection and exact model are required. No model or library edit,
link creation, optimization or automatic adoption occurs here.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import combinations
import math
from pathlib import Path
import shutil

from .cif_captured_geometry import review_captured_geometry
from .cif_fana_component import _digest, _load, _save
from .cif_fana_placement import read_fana_linked_control
from .cif_fragment_restoration import _model
from .cif_linked_preparation import component_values, _prune
from .cif_terminal_qualification import _CATEGORIES, _rows, _signature, _proxy_subset
from .dictionary_compatibility import normalize_torsion_block
from .ligand_profiles import _blocks

POLICY_ID = 'cif-source-bound-fana-junction-angles-v1'
_FILES = {'model.pdb', 'native.json', 'link.cif', 'angles.phil', 'junction.json'}
_KINDS = {'bond_simple', 'bond_asu', 'angle', 'dihedral', 'const_dihedral',
          'chirality', 'planarity', 'parallelity'}


def _path(path, *, directory=False):
    p = Path(path).expanduser().absolute()
    if any(x.is_symlink() for x in [p, *p.parents]) or not (p.is_dir() if directory else p.is_file()):
        raise ValueError('Require an existing nonsymlinked input')
    return p


def _canonical(indices):
    key = tuple(indices)
    return min(key, key[::-1])


def _number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean restraint parameter')
    n = float(value)
    if not math.isfinite(n) or n <= 0:
        raise ValueError('Require finite positive template parameters')
    return n


def _weight(sigma):
    square = sigma * sigma
    if not math.isfinite(square) or square == 0:
        raise ValueError('Template sigma cannot produce a finite positive weight')
    weight = 1 / square
    if not math.isfinite(weight) or weight <= 0:
        raise ValueError('Template sigma cannot produce a finite positive weight')
    return weight


def _template(path):
    blocks = _blocks(path)
    if len(blocks) != 1 or blocks[0].values.get('data_') != 'link_rna3p':
        raise ValueError('Require the explicit single RNA/DNA 3-prime link template')
    v = blocks[0].values
    bonds, angles = _rows(v, '_chem_link_bond'), _rows(v, '_chem_link_angle')
    def endpoints(row, size):
        return tuple((row['atom_'+str(i)+'_comp_id'], row['atom_id_'+str(i)]) for i in range(1, size+1))
    bond = (('1', "O3'"), ('2', 'P'))
    expected = [(('1', "O3'"), ('2', 'P'), ('2', n)) for n in ("O5'", 'OP1', 'OP2')]
    expected.append((('1', "C3'"), ('1', "O3'"), ('2', 'P')))
    if (len(bonds) != 1 or endpoints(bonds[0], 2) != bond or bonds[0]['type'].lower() != 'single'
            or len(angles) != 4 or Counter(endpoints(r, 3) for r in angles) != Counter(expected)):
        raise ValueError('Unsupported or ambiguous native link topology')
    b = bonds[0]
    _weight(_number(b['value_dist_esd']))
    result = {'bond': {'atoms': bond, 'target': _number(b['value_dist']), 'sigma': _number(b['value_dist_esd'])}, 'angles': []}
    for row in angles:
        target, sigma = _number(row['value_angle']), _number(row['value_angle_esd'])
        _weight(sigma)
        if target >= 180:
            raise ValueError('Invalid angle target')
        result['angles'].append({'atoms': endpoints(row, 3), 'target': target, 'sigma': sigma})
    # Preserve even the installed file's rna2p row identifiers as evidence;
    # block identity and literal topology, not that column, select this rule.
    result['row_link_ids'] = sorted({r['link_id'] for r in bonds+angles})
    return result


def _capture(native):
    review_captured_geometry(native)
    if native.get('fatal_problems') or native.get('unsupported_fields') or native.get('unused_definitions'):
        raise ValueError('Require a usable complete native inventory')
    g = native['geometry']; details = g['proxy_details']
    if set(details) != _KINDS or any(g['proxy_counts'].get(k) != len(details[k]) for k in _KINDS):
        raise ValueError('Incomplete proxy inventory')
    if g['simple_bonds'] != details['bond_simple'] or g['asu_bonds'] != details['bond_asu']:
        raise ValueError('Captured bond inventories disagree')
    if details['bond_asu'] or any(r.get('symmetry_operation') not in (None, 'x,y,z') for r in details['bond_simple']):
        raise ValueError('Symmetry links require a separate policy')
    for kind in _KINDS:
        _proxy_subset(native, set(), kind)
    for kind in ('bond_simple', 'angle'):
        if any(len(set(r['i_seqs'])) != len(r['i_seqs']) for r in details[kind]):
            raise ValueError('Repeated native bond or angle endpoint')
        keys = [_canonical(r['i_seqs']) for r in details[kind]]
        if len(keys) != len(set(keys)):
            raise ValueError('Duplicate native bond or angle')
    if any(a['identity']['icode'].strip() or a['identity']['altloc'].strip() for a in native['atoms']):
        raise ValueError('Ambiguous native identity')
    return details


def _bind(control, model, native):
    placement = read_fana_linked_control(control)
    actual = _model(native, model, coordinates_match=True)
    from .cif_construction_provenance import _pdb_inventory
    original = _pdb_inventory(control/'model.pdb')
    if actual.keys() != original.keys():
        raise ValueError('Model differs from the whole-residue control inventory')
    # This first adapter accepts translation of the intact central residue.
    # Geometry-changing candidates need their own source/stereo assessment.
    key = ('A', '2', '', '', 'P')
    shift = [a-b for a, b in zip(actual[key]['xyz'], original[key]['xyz'])]
    old_lines = (control/'model.pdb').read_text().splitlines(keepends=True)
    expected = []
    for line in old_lines:
        if line[:6] in {'ATOM  ', 'HETATM'} and line[21:26] == 'A   2':
            xyz = [float(line[i:i+8])+d for i, d in zip((30,38,46), shift)]
            line = line[:30]+''.join(f'{x:8.3f}' for x in xyz)+line[54:]
        expected.append(line)
    if ''.join(expected).encode() != model.read_bytes():
        raise ValueError('Require an unchanged or translated whole residue with exact flanks')
    values = _prune(component_values(control/'numerical.cif', placement['component']),
                    set(placement['deleted_source_atoms_for_declared_links']), outgoing=True)
    values, _ = normalize_torsion_block(values)
    rows = native['monomer_mappings']['rows']
    if len({r['site'] for r in rows}) != len(rows):
        raise ValueError('Duplicate native monomer mapping')
    target = next((r for r in rows if r['site'] == 'A:2'), {})
    if (target.get('resname') != placement['component']
            or target.get('unexpected_atoms', {}).get('atom_ids')
            or target.get('missing_non_hydrogen_atoms', {}).get('atom_ids')):
        raise ValueError('Incomplete target monomer mapping')
    definition = target.get('metadata', {}).get('effective_definition', {})
    for category, (prefix, fields) in _CATEGORIES.items():
        if (category not in definition or Counter(_signature(r, fields) for r in definition[category])
                != Counter(_signature(r, fields) for r in _rows(values, prefix))):
            raise ValueError('Native target differs from declared source projection: '+category)
    return placement, values, shift


def _derive(control, model, native, template):
    details = _capture(native)
    placement, values, shift = _bind(control, model, native)
    spec = _template(template)
    atoms = native['atoms']
    by = {(a['identity']['resseq'].strip(), a['atom_id']): a['i_seq'] for a in atoms
          if a['identity']['chain_id'].strip() == 'A'}
    target_names = {name for site, name in by if site == '2'}
    aliases = {}
    for role, pair in [('OP1', {'OP1','O1P'}), ('OP2', {'OP2','O2P'})]:
        matches = pair & target_names
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous phosphate alias: '+role)
        aliases[role] = next(iter(matches))
    def indices(ends):
        try:
            return [by[(s, aliases.get(n, n) if s == '2' else n)] for s, n in ends]
        except KeyError as exc:
            raise ValueError('Template endpoint absent from exact control') from exc
    bond_map = {_canonical(r['i_seqs']):r for r in details['bond_simple']}
    b = spec['bond']; bond_key = _canonical(indices(b['atoms']))
    if bond_key not in bond_map or any(not math.isclose(bond_map[bond_key][k], v, rel_tol=1e-12, abs_tol=1e-12)
            for k,v in [('distance_ideal', b['target']), ('weight', _weight(b['sigma']))]):
        raise ValueError('Required native incoming link is absent or differs from template')
    p = by['2','P']; left = by['1',"O3'"]
    neighbors = {next(i for i in r['i_seqs'] if i != p) for r in details['bond_simple'] if p in r['i_seqs']}
    expected_neighbors = {left, by['2',"O5'"], by['2',aliases['OP1']], by['2',aliases['OP2']]}
    if neighbors != expected_neighbors:
        raise ValueError('Require exactly four declared native phosphate neighbors')
    # The source must independently assign those three retained oxygens to P.
    graph_neighbors = {r['atom_id_2'] if r['atom_id_1']=='P' else r['atom_id_1']
                       for r in _rows(values,'_chem_comp_bond') if 'P' in (r['atom_id_1'],r['atom_id_2'])}
    if graph_neighbors != {"O5'", *aliases.values()}:
        raise ValueError('Phosphate alias roles contradict the projected source graph')
    angle_map = {_canonical(r['i_seqs']):r for r in details['angle']}
    required = {_canonical((a,p,b)) for a,b in combinations(neighbors,2)}
    allowed_missing = {_canonical((left,p,by['2',name])) for name in aliases.values()}
    if required - set(angle_map) - allowed_missing:
        raise ValueError('Existing internal phosphate angle coverage is incomplete')
    requests = []
    for row in spec['angles']:
        ids = indices(row['atoms']); key = _canonical(ids)
        target, weight = row['target'], _weight(row['sigma'])
        if key in angle_map:
            if any(not math.isclose(angle_map[key][k],v,rel_tol=1e-12,abs_tol=1e-12)
                   for k,v in [('angle_ideal',target),('weight',weight)]):
                raise ValueError('Existing junction angle conflicts with the explicit template')
            continue
        if key not in allowed_missing:
            raise ValueError('Only the two nonbridging incoming angles may be added')
        selected = [atoms[i] for i in ids]
        selections = ["chain A and resid {} and resname {} and name {}".format(
            a['identity']['resseq'].strip(),a['identity']['resname'].strip(),a['atom_id']) for a in selected]
        requests.append({'kind':'angle','action':'add','i_seqs':ids,'atoms':[a['label'] for a in selected],
                         'angle_ideal':target,'sigma':row['sigma'],'weight':weight,'selections':selections,
                         'template_atoms':[list(x) for x in row['atoms']]})
    # A pending edit must not duplicate a previous explicit request whose
    # native materialization is absent; that discrepancy needs investigation.
    requested_keys = {_canonical(q['i_seqs']) for q in requests}
    if any(q['kind']=='angle' and _canonical(q['i_seqs']) in requested_keys for q in native['geometry']['custom_proxy_requests']):
        raise ValueError('Existing explicit angle request did not materialize')
    blocks = []
    for q in requests:
        fields = ['    action = add']+[f'    atom_selection_{i} = {s}' for i,s in enumerate(q['selections'],1)]
        fields += [f"    angle_ideal = {q['angle_ideal']:.17g}", f"    sigma = {q['sigma']:.17g}"]
        blocks.append('   angle {\n'+'\n'.join(fields)+'\n   }')
    phil = 'refinement {\n geometry_restraints {\n  edits {\n'+'\n'.join(blocks)+'\n  }\n }\n}\n'
    report = {'schema_version':1,'policy_id':POLICY_ID,'status':'JUNCTION_ANGLES_COMPILED',
              'component':placement['component'],'link':['A:1', 'A:2'],'aliases':aliases,'requests':requests,
              'phosphate_angles_before':len(required & set(angle_map)),'required_phosphate_angles':6,
              'translation_angstrom':shift,'template_row_link_ids':spec['row_link_ids'],
              'template_sha256':_digest(template)['sha256'],'native_sha256':None,
              'native_delta_validation':'NOT_RUN','chemical_qualification':'NOT_ESTABLISHED',
              'automatic_adoption':False,'scope':'SEPARATE_MECHANICS_CONTROL; NO_LINK_CREATION_OR_GEOMETRY_REPAIR'}
    return report, phil


def prepare_fana_junction_angles(control, model, native, link_template, output):
    """Freeze a separate angle supplement from an already bonded native capture."""
    control = _path(control, directory=True)
    model, native, link_template = [_path(p) for p in (model,native,link_template)]
    out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (control,model,native,link_template)):
        raise ValueError('Output must be separate from all inputs')
    read_fana_linked_control(control)
    before = {p:p.read_bytes() for p in [model,native,link_template,*[p for p in control.rglob('*') if p.is_file()]]}
    report, phil = _derive(control,model,_load(native),link_template)
    report['native_sha256'] = _digest(native)['sha256']
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(control,out/'placement')
    for name,path in [('model.pdb',model),('native.json',native),('link.cif',link_template)]:
        (out/name).write_bytes(before[path])
    frozen, frozen_phil = _derive(out/'placement',out/'model.pdb',_load(out/'native.json'),out/'link.cif')
    frozen['native_sha256'] = _digest(out/'native.json')['sha256']
    if report != frozen or phil != frozen_phil or any(p.read_bytes()!=b for p,b in before.items()):
        raise ValueError('Junction authority changed during preparation')
    (out/'angles.phil').write_text(phil)
    _save(out/'junction.json',report)
    files = {p.relative_to(out).as_posix():_digest(p) for p in out.rglob('*') if p.is_file()}
    _save(out/'receipt.json',{'schema_version':1,'policy_id':POLICY_ID,'files':files})
    return read_fana_junction_angles(out)


def read_fana_junction_angles(directory):
    """Read and rederive without installed libraries, execution or mutation."""
    root = _path(directory,directory=True); paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('Junction package cannot traverse symlinks')
    expected = _FILES | {'receipt.json'} | {'placement/'+p.relative_to(root/'placement').as_posix() for p in (root/'placement').rglob('*') if p.is_file()}
    before = {p:p.read_bytes() for p in paths if p.is_file()}
    if {p.relative_to(root).as_posix() for p in before} != expected:
        raise ValueError('Unexpected or missing junction package file')
    r = _load(root/'receipt.json')
    if (set(r) != {'schema_version','policy_id','files'} or type(r['schema_version']) is not int
            or r['schema_version'] != 1 or r['policy_id'] != POLICY_ID or set(r['files']) != expected-{'receipt.json'}
            or any(_digest(root/name)!=value for name,value in r['files'].items())):
        raise ValueError('Invalid junction completion receipt or checksum')
    report, phil = _derive(root/'placement',root/'model.pdb',_load(root/'native.json'),root/'link.cif')
    report['native_sha256'] = _digest(root/'native.json')['sha256']
    if (report != _load(root/'junction.json') or phil.encode() != (root/'angles.phil').read_bytes()
            or any(p.read_bytes()!=b for p,b in before.items())):
        raise ValueError('Stored junction outputs differ from fresh derivation')
    return report


def qualify_fana_junction_angles(directory, after):
    """Require exactly the requested native additions and unchanged mechanics."""
    root = _path(directory,directory=True); report = read_fana_junction_angles(root)
    before = _load(root/'native.json'); checks = []
    def check(name, passed):
        checks.append({'check':name,'status':'PASS' if passed else 'REVIEW'})
    try:
        _capture(after)
        check('exact-model',after['atoms']==before['atoms'])
        check('exact-effective-definitions',after['monomer_mappings']==before['monomer_mappings'])
        check('unchanged-policy',after['restraint_policy']==before['restraint_policy'])
        remaining = deepcopy(after); details = remaining['geometry']['proxy_details']
        edit_origin = after['restraint_policy']['origin_ids']['edits']
        for q in report['requests']:
            matches = [r for r in details['angle'] if _canonical(r['i_seqs'])==_canonical(q['i_seqs'])
                       and r['origin_id']==edit_origin and r['angle_ideal']==q['angle_ideal'] and r['weight']==q['weight']]
            check('exact-added-angle:'+str(q['i_seqs']),len(matches)==1)
            if len(matches)==1:
                details['angle'].remove(matches[0])
        for kind in sorted(_KINDS):
            check('preserved-proxies:'+kind,_proxy_subset(before,set(),kind)==_proxy_subset(remaining,set(),kind))
        requests = deepcopy(after['geometry']['custom_proxy_requests'])
        for q in report['requests']:
            expected = {k:v for k,v in q.items() if k not in {'sigma','template_atoms'}}
            matches = [r for r in requests if r==expected]
            check('exact-added-request:'+str(q['i_seqs']),len(matches)==1)
            if len(matches)==1:
                requests.remove(matches[0])
        check('preserved-explicit-requests',requests==before['geometry']['custom_proxy_requests'])
        # Re-derive against the resulting manager: no missing angle remains.
        result, _ = _derive(root/'placement',root/'model.pdb',after,root/'link.cif')
        check('six-phosphate-angles',result['phosphate_angles_before']==6 and not result['requests'])
    except (KeyError,TypeError,ValueError,IndexError) as exc:
        checks.append({'check':'complete-consistent-native-evidence','status':'REVIEW','error':str(exc)})
    passed = bool(checks) and all(r['status']=='PASS' for r in checks)
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'JUNCTION_ANGLE_MECHANICS_PASS' if passed else 'REVIEW',
            'checks':checks,'chemical_qualification':'NOT_ESTABLISHED','automatic_adoption':False}
