"""Explicit, bounded local bend previews; never a repair or refinement verdict.

Whole residues in a paired step share a rigid motion. A smooth taper reaches
zero at fixed anchors; inter-residue bonds/angles are audited after PDB rounding.
This is a trial generator, not an atomistic backbone closure solver.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

from .construct_registration import validate_construct_registration
from .run_context import artifact_reference, resolve_artifact_path
from .topostitch_coordinates import ResidueSite, _read_atoms, _residue, _plane, _mean
from .topostitch_discovery import plan_editable_windows
from .topostitch_inspect import _keys, _unique_object, load_registered_end_assignments
from .topostitch_registration import _coordinate_site


class TrialLimitError(ValueError):
    """A valid explicit trial exceeds its declared displacement/strain limits."""


_FILES = {'source': 'source.pdb', 'candidate': 'candidate.pdb',
          'discovery': 'discovery.json', 'registration': 'registration.json', 'trial': 'trial.json'}


def _json(data):
    return json.loads(data.decode('utf-8'), object_pairs_hook=_unique_object)


def _number(value, name, *, positive=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and (not positive or value > 0)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{name} must be a finite'+(' positive' if positive else '')+' number')
    return float(value)


def _vector(value, name):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f'{name} must contain three numbers')
    return tuple(_number(x, name) for x in value)


def _rotation(vector, weight):
    angle = math.radians(math.hypot(*vector))*weight
    if angle == 0:
        return ((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    length = math.hypot(*vector)
    x,y,z = (v/length for v in vector)
    c,s,d = math.cos(angle),math.sin(angle),1-math.cos(angle)
    return ((c+x*x*d,x*y*d-z*s,x*z*d+y*s),
            (y*x*d+z*s,c+y*y*d,y*z*d-x*s),
            (z*x*d-y*s,z*y*d+x*s,c+z*z*d))


def _apply(matrix, vector):
    return tuple(sum(a*b for a,b in zip(row,vector)) for row in matrix)


def _site(line):
    return ResidueSite(line[21:22].strip(),int(line[22:26]),line[26:27].strip())


def _atom_identity(line):
    return line[6:27],line[72:80].rstrip()


def _render(data, transforms, origin, translation):
    lines = data.decode('ascii').splitlines(keepends=True)
    selected_atoms = {_atom_identity(line) for line in lines
        if line[:6].strip() in ('ATOM','HETATM') and _site(line) in transforms}
    anisou_seen = set()
    result, moved_atoms, rotated_tensors = [], 0, 0
    for line in lines:
        record = line[:6].strip()
        if record not in ('ATOM','HETATM','ANISOU','SIGATM','SIGUIJ') or _site(line) not in transforms:
            result.append(line)
            continue
        rotation,weight = transforms[_site(line)]
        if record in ('SIGATM','SIGUIJ'):
            raise ValueError('Selected SIGATM/SIGUIJ uncertainty records are unsupported')
        if record == 'ANISOU':
            identity = _atom_identity(line)
            if identity not in selected_atoms or identity in anisou_seen:
                raise ValueError('Orphan, mismatched or duplicate selected ANISOU record')
            anisou_seen.add(identity)
            try:
                u11,u22,u33,u12,u13,u23 = [int(line[a:a+7]) for a in (28,35,42,49,56,63)]
            except ValueError as exc:
                raise ValueError('Malformed selected ANISOU record') from exc
            tensor = ((u11,u12,u13),(u12,u22,u23),(u13,u23,u33))
            rotated = [[sum(rotation[i][a]*tensor[a][b]*rotation[j][b]
                            for a in range(3) for b in range(3)) for j in range(3)] for i in range(3)]
            values = [round(rotated[i][j]) for i,j in ((0,0),(1,1),(2,2),(0,1),(0,2),(1,2))]
            fields = [f'{v:7d}' for v in values]
            if any(len(f) != 7 for f in fields):
                raise ValueError('Rotated ANISOU tensor exceeds PDB field width')
            if rotation != _rotation((0,0,0),0):
                line = line[:28]+''.join(fields)+line[70:]
                rotated_tensors += 1
        else:
            xyz = tuple(float(line[a:a+8]) for a in (30,38,46))
            changed = _apply(rotation,tuple(x-o for x,o in zip(xyz,origin)))
            changed = tuple(x+o+weight*t for x,o,t in zip(changed,origin,translation))
            fields = [f'{x:8.3f}' for x in changed]
            if any(not math.isfinite(x) for x in changed) or any(len(f) != 8 for f in fields):
                raise ValueError('Transformed coordinate exceeds PDB field width')
            if rotation != _rotation((0,0,0),0) or any(translation):
                line = line[:30]+''.join(fields)+line[54:]
            moved_atoms += 1
        result.append(line)
    return ''.join(result).encode('ascii'),moved_atoms,rotated_tensors


def _angle(a,b,c):
    u,v = tuple(x-y for x,y in zip(a,b)),tuple(x-y for x,y in zip(c,b))
    length = math.hypot(*u)*math.hypot(*v)
    if length < 1e-12 or not math.isfinite(length):
        raise ValueError('Degenerate backbone angle')
    return math.degrees(math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(u,v))/length))))


def _mapped_residues(data, registration, copy_id, required):
    atoms = _read_atoms(data)
    copy = next((c for c in registration['copies'] if c['copy_id']==copy_id), None)
    if copy is None:
        raise ValueError('Unknown preview copy')
    mapping = {r['logical_site']:r for r in copy['mappings']}
    sites, coordinates = {}, {}
    for logical in sorted(required):
        item = mapping.get(logical)
        if item is None or item['identity_relation'] != 'SAME':
            raise ValueError(f'Preview requires resolved unchanged chemistry at {logical}')
        site = _coordinate_site(item['coordinate_site'])
        _, points = _residue(atoms,site)
        rows = next(iter(atoms[site].values()))
        if ({r[1] for r in rows} != {item['coordinate_residue_code']}
                or item['coordinate_residue_code'] != item['target_residue_code']):
            raise ValueError(f'Preview coordinate identity mismatch at {logical}')
        if any(r[4] is None or not math.isfinite(r[4]) or not 0 < r[4] <= 1 for r in rows):
            raise ValueError(f'Preview requires usable occupancy for every atom at {logical}')
        sites[logical],coordinates[logical] = site,points
    if len(set(sites.values())) != len(sites):
        raise ValueError('Preview logical sites overlap in coordinate space')
    return sites,coordinates


def _audit_links(links, before, after, trial):
    rows = []
    for a,b in links:
        values = []
        for coordinates in (before,after):
            try:
                c3,o3,p,o5 = coordinates[a]["C3'"],coordinates[a]["O3'"],coordinates[b]['P'],coordinates[b]["O5'"]
            except KeyError as exc:
                raise ValueError(f'Missing backbone audit atom for {a} -> {b}: {exc}') from exc
            values.append((math.dist(o3,p),_angle(c3,o3,p),_angle(o3,p,o5)))
        original,current = values
        rows.append({'from_site':a,'to_site':b,
            'distance_angstrom':{'before':original[0],'after':current[0],'change':current[0]-original[0]},
            'angles_degrees':[{'atoms':names,'before':x,'after':y,'change':y-x}
                for names,x,y in zip((['C3\'','O3\'','P'],['O3\'','P','O5\'']),original[1:],current[1:])]})
    bond = max((abs(r['distance_angstrom']['change']) for r in rows),default=0.)
    angle = max((abs(a['change']) for r in rows for a in r['angles_degrees']),default=0.)
    if bond > trial['max_backbone_bond_change_angstrom'] or angle > trial['max_backbone_angle_change_degrees']:
        raise TrialLimitError(f'Backbone change exceeds trial limits: bond {bond:.6g} A; angle {angle:.6g} degrees')
    return {'links':rows,'max_bond_change_angstrom':bond,'max_angle_change_degrees':angle,
            'limits_passed':True,'ideal_geometry_validated':False}


def _prepare(model_path, discovery_path, registration_path, trial_path=None, *, trial_value=None):
    if (trial_path is None) == (trial_value is None):
        raise ValueError('Supply exactly one explicit trial path or trial value')
    paths = {'source':Path(model_path),'discovery':Path(discovery_path),
             'registration':Path(registration_path)}
    if trial_path is not None:
        paths['trial'] = Path(trial_path)
    snapshots = {name:path.read_bytes() for name,path in paths.items()}
    if trial_value is not None:
        snapshots['trial'] = (json.dumps(trial_value,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')
    trial = _json(snapshots['trial'])
    _keys(trial, {'schema_version','kind','model_sha256','discovery_file_sha256','registration_file_sha256',
        'window_id','max_window_pairs','fixed_anchor_pairs','rotation_vector_degrees','translation_angstrom',
        'max_atom_displacement_angstrom','max_backbone_bond_change_angstrom','max_backbone_angle_change_degrees'})
    if type(trial['schema_version']) is not int or trial['schema_version'] != 1 or trial['kind'] != 'topostitch-window-transform':
        raise ValueError('Expected schema-1 topostitch-window-transform trial')
    for name,key in (('source','model_sha256'),('discovery','discovery_file_sha256'),('registration','registration_file_sha256')):
        if sha256(snapshots[name]).hexdigest() != trial[key]:
            raise ValueError(f'{name} checksum mismatch')
    rotation = _vector(trial['rotation_vector_degrees'],'rotation_vector_degrees')
    translation = _vector(trial['translation_angstrom'],'translation_angstrom')
    if math.hypot(*rotation) > 180:
        raise ValueError('Rotation vector magnitude must not exceed 180 degrees')
    for name in ('max_atom_displacement_angstrom','max_backbone_bond_change_angstrom','max_backbone_angle_change_degrees'):
        _number(trial[name],name,positive=True)
    _, assignments, _, mapping = load_registered_end_assignments(model_path,discovery_path,registration_path)
    discovery = mapping.get('discovery_assessment')
    if discovery is None:
        raise ValueError('Bend preview requires a registered discovery manifest')
    windows = plan_editable_windows(discovery,max_base_pairs=trial['max_window_pairs'],fixed_anchor_pairs=trial['fixed_anchor_pairs'])
    matches = [w for end in windows['ends'] for w in end['windows'] if w['window_id']==trial['window_id']]
    if len(matches) != 1:
        raise ValueError('Selected window is absent, excluded or ambiguous')
    window = matches[0]
    if not any(a.end_id==window['end_id'] and a.state=='available' for a in assignments):
        raise ValueError('Selected window has an unresolved or unavailable end')
    moving = set(window['movable_sites'])
    links = [(a,b) for strand in discovery['inputs']['strands']
             for a,b in zip(strand['sites'],strand['sites'][1:]) if a in moving or b in moving]
    required = moving | set(window['fixed_sites']) | {s for pair in links for s in pair}
    registry = validate_construct_registration(_json(snapshots['registration']))
    sites,before = _mapped_residues(snapshots['source'],registry,window['copy_id'],required)
    terminal = window['movable_pairs'][0]
    origin = _mean([_plane(before[s])[0] for s in terminal])
    weights = {s:1. for s in window['overhang_sites']}
    count = len(window['movable_pairs'])
    for i,pair in enumerate(window['movable_pairs']):
        t = 1-i/count
        weights.update({s:t*t*(3-2*t) for s in pair})
    transforms = {sites[s]:(_rotation(rotation,w),w) for s,w in weights.items()}
    candidate,atom_count,tensor_count = _render(snapshots['source'],transforms,origin,translation)
    _,after = _mapped_residues(candidate,registry,window['copy_id'],required)
    displacement = max(math.dist(point,after[s][name]) for s in moving for name,point in before[s].items())
    if displacement > trial['max_atom_displacement_angstrom']:
        raise TrialLimitError(f'Atom displacement {displacement:.6g} A exceeds trial limit')
    audit = _audit_links(links,before,after,trial)
    # Loaders inspect paths; confirm that their evidence still refers to the
    # captured bytes before freezing anything. Computation above uses snapshots.
    if any(path.read_bytes() != snapshots[name] for name,path in paths.items()):
        raise ValueError('Preview inputs changed while being read')
    snapshots['candidate'] = candidate
    report = {'schema_version':1,'kind':'topostitch-bend-preview',
        'algorithm':'whole-pair-smoothstep-terminal-transform-v1',
        'source_model_sha256':trial['model_sha256'],'candidate_model_sha256':sha256(candidate).hexdigest(),
        'window':window,'terminal_origin_angstrom':list(origin),
        'site_weights':weights,'trial':trial,'transformed_atom_count':atom_count,
        'rotated_anisou_count':tensor_count,'max_atom_displacement_angstrom':displacement,
        'backbone_audit':audit,'discovery_coverage_complete':mapping['coverage_complete'],
        'workflow':{'execution_state':'CANDIDATE_BUILT','review_state':'UNREVIEWED','refinement_state':'NOT_ATTEMPTED'},
        'geometry_validated':False,'runtime_authority':False,
        'limitations':['Explicit single-window transform; no partner selection or automatic fitting',
            'Whole-residue rigid motion preserves local shape but does not solve backbone closure',
            'Bond/angle limits measure change from source, not ideal stereochemistry',
            'No packing, density, torsion, periodic-cut or native refinement qualification',
            'No new bonds, missing atoms, chemistry changes or campaign adoption']}
    return snapshots,report


def build_bend_preview(model_path, discovery_path, *, registration_path, trial_path, output_directory):
    """Write a new self-contained trial folder after validation; never overwrite."""
    root = Path(output_directory)
    if root.exists():
        raise FileExistsError(f'Preview output already exists: {root}')
    snapshots,report = _prepare(model_path,discovery_path,registration_path,trial_path)
    root.mkdir()  # exclusive creation also protects against concurrent writers
    references = {}
    for name,filename in _FILES.items():
        path = root/filename
        with path.open('xb') as stream:
            stream.write(snapshots[name])
        references[name] = {**artifact_reference(path,root),'sha256':sha256(snapshots[name]).hexdigest(),
                            'size_bytes':len(snapshots[name])}
    report['artifacts'] = references
    with (root/'preview.json').open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return report


def load_bend_preview(directory):
    """Resolve checksummed local snapshots and replay the exact trial after relocation."""
    root = Path(directory)
    report = _json((root/'preview.json').read_bytes())
    if not isinstance(report,dict) or report.get('kind') != 'topostitch-bend-preview' or type(report.get('schema_version')) is not int or report['schema_version'] != 1:
        raise ValueError('Unsupported bend-preview receipt')
    references = report.get('artifacts')
    if not isinstance(references,dict) or set(references) != set(_FILES):
        raise ValueError('Incomplete preview artifact inventory')
    paths = {}
    for name,filename in _FILES.items():
        reference = references[name]
        if (not isinstance(reference,dict) or reference.get('anchor') != 'run'
                or reference.get('relative_path') != filename):
            raise ValueError('Preview artifact must use its declared local run anchor')
        path = resolve_artifact_path(reference,root)
        if path is None or path.stat().st_size != reference.get('size_bytes'):
            raise ValueError('Missing or changed preview artifact')
        if sha256(path.read_bytes()).hexdigest() != reference.get('sha256'):
            raise ValueError('Missing or changed preview artifact checksum')
        paths[name] = path
    snapshots,expected = _prepare(paths['source'],paths['discovery'],paths['registration'],paths['trial'])
    expected['artifacts'] = references
    if snapshots['candidate'] != paths['candidate'].read_bytes() or expected != report:
        raise ValueError('Preview receipt or candidate does not reproduce from frozen inputs')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog='nasolve-topostitch-preview',
        description='Write an isolated explicit DNA bend preview; no repair or refinement acceptance.')
    parser.add_argument('model',type=Path)
    parser.add_argument('discovery',type=Path)
    parser.add_argument('--registration',required=True,type=Path)
    parser.add_argument('--trial',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path,help='New output directory; must not exist')
    args = parser.parse_args(argv)
    try:
        report = build_bend_preview(args.model,args.discovery,registration_path=args.registration,
                                   trial_path=args.trial,output_directory=args.out)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(2,f'{parser.prog}: {exc}\n')
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
