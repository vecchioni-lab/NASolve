"""Bounded torsion-only FANA construction seeds, not native refinement.

The declared leaving oxygen is a virtual fit point for its incoming replacement.
It is never written to the linked model. Only acyclic single-bond rotations and
a proper whole-residue transform are allowed; ring geometry remains source-bound.
"""
from itertools import combinations, product
import math
from pathlib import Path
import shutil

import numpy as np

from .cif_construction_provenance import _pdb_inventory
from .cif_fana_component import _digest, _load, _save
from .cif_fana_placement import read_fana_linked_control, _hand
from .cif_fana_junction import _path
from .cif_stereochemistry_audit import _values, _graph, _coordinates, _volume
from .cif_captured_geometry import _observed

POLICY_ID = 'cif-fana-torsion-bridge-seed-v1'
_AXES = (("C4'", "C5'"), ("C5'", "O5'"), ("O5'", 'P'))
_ANCHORS = ('P', "O5'", "C5'", "C4'", "O4'", "C1'", "C2'", "C3'", "O3'")
_STEPS = (60., 20., 5., 1., .25)
_FILES = {'config.json', 'model.pdb', 'seed.json'}


def _moving_group(graph, bonds, a, b):
    if bonds.get(tuple(sorted((a,b)))) != 'SINGLE':
        raise ValueError('Rotatable axis must be an explicit source single bond')
    seen = set(); pending = [b]
    while pending:
        n = pending.pop()
        if n in seen:
            continue
        seen.add(n)
        pending.extend(k for k in graph[n] if {n,k} != {a,b} and k not in seen)
    if a in seen:
        raise ValueError('A ring bond cannot be a bridge rotor')
    return seen


def _fit(xyz, axes, angles, indices, target, weights):
    points = xyz.copy()
    for angle, (a,b,group) in zip(angles,axes):
        vector = points[b]-points[a]; length = np.linalg.norm(vector)
        if not np.isfinite(length) or length < .5:
            raise ValueError('Degenerate source rotor axis')
        axis = vector/length; offset = points[group]-points[a]; theta = math.radians(angle)
        points[group] = (points[a]+offset*math.cos(theta)+np.cross(axis,offset)*math.sin(theta)
                         +np.outer(offset@axis,axis)*(1-math.cos(theta)))
    moving = points[indices]; total = weights.sum()
    centre = (weights[:,None]*moving).sum(0)/total
    reference = (weights[:,None]*target).sum(0)/total
    left, singular, right = np.linalg.svd((weights[:,None]*(moving-centre)).T@(target-reference))
    if not np.isfinite(singular).all() or singular[-1] < 1e-8:
        raise ValueError('Degenerate reference fit')
    correction = np.eye(3); correction[2,2] = 1 if np.linalg.det(left@right)>0 else -1
    rotation = left@correction@right; determinant = float(np.linalg.det(rotation))
    points = (points-centre)@rotation+reference
    loss = float(((points[indices]-target)**2*weights[:,None]).sum()/total)
    if not np.isfinite(points).all() or not math.isfinite(loss) or abs(determinant-1)>1e-10:
        raise ValueError('Nonfinite or improper rigid fit')
    return loss, points, determinant


def _search(xyz, axes, indices, target, weights):
    trials = []; calls = 0
    initial_loss = _fit(xyz,axes,[0.,0.,0.],indices,target,weights)[0]; calls += 1
    for initial in product((-120.,0.,120.),repeat=3):
        angles = list(initial)
        best,points,det = _fit(xyz,axes,angles,indices,target,weights); calls += 1
        sweeps = []
        for step in _STEPS:
            used = 0
            for _ in range(8):
                improved = False; used += 1
                for i in range(3):
                    choices = []
                    for sign in (-1,1):
                        trial = angles.copy(); trial[i] += sign*step
                        loss,q,d = _fit(xyz,axes,trial,indices,target,weights); calls += 1
                        choices.append((loss,trial,q,d))
                    loss,trial,q,d = min(choices,key=lambda x:x[0])
                    if loss < best-1e-12:
                        best,angles,points,det = loss,trial,q,d; improved = True
                if not improved:
                    break
            sweeps.append(used)
        trials.append({'initial_degrees':list(initial),'degrees':angles,'weighted_mean_square':best,
                       'sweeps':sweeps,'points':points,'determinant':det})
    selected = min(range(len(trials)),key=lambda i:trials[i]['weighted_mean_square'])
    winner = trials[selected]; points = winner['points']
    report = {'starts':27,'evaluations':calls,'max_evaluations':27*(1+len(_STEPS)*8*6)+1,
              'step_degrees':list(_STEPS),'max_sweeps_per_step':8,'selected_trial':selected,
              'initial_zero_torsion_score':initial_loss,
              'trials':[{k:v for k,v in t.items() if k!='points'} for t in trials],
              'global_minimum_claimed':False,'native_energy':'NOT_EVALUATED'}
    return points, report


def _seed(control, config):
    if (set(config) != {'endpoint_weight'} or type(config['endpoint_weight']) not in (float,int)
            or not math.isfinite(config['endpoint_weight']) or not 1 <= config['endpoint_weight'] <= 1000):
        raise ValueError('Require explicit finite construction endpoint weight in [1,1000]')
    placement = read_fana_linked_control(control); code = placement['component']
    v = _values(control/'numerical.cif',code); elements,bonds,_,graph = _graph(v)
    _,coordinates = _coordinates(v,source=False)
    leaving = placement['context']['leaving_atom']; removed = set(placement['deleted_source_atoms_for_declared_links'])
    heavy = sorted(n for n,e in elements.items() if e not in {'H','D'})
    retained = sorted(set(heavy)-removed)
    if set(heavy)-set(retained) != {leaving}:
        raise ValueError('Require exactly one declared virtual leaving oxygen')
    index = {n:i for i,n in enumerate(heavy)}
    xyz = np.array([coordinates[n] for n in heavy],dtype=float)
    axes = []; groups = []
    for a,b in _AXES:
        group = _moving_group(graph,bonds,a,b)
        if not {leaving,'P'} <= group or group & {"C1'","C2'","C3'","C4'","O4'","O3'"}:
            raise ValueError('Rotor must move only the declared acyclic phosphate arm')
        groups.append({'axis':[a,b],'moving_source_atoms':sorted(group)})
        axes.append((index[a],index[b],[index[n] for n in heavy if n in group]))
    frame = _pdb_inventory(control/'frame.pdb'); prior = _pdb_inventory(control/'model.pdb')
    anchors = [*_ANCHORS,leaving]
    target = np.array([frame['A','1' if n==leaving else '2','','',"O3'" if n==leaving else n]['xyz'] for n in anchors])
    weights = np.array([config['endpoint_weight'] if n in {'P',"O3'",leaving} else 1. for n in anchors])
    points,search = _search(xyz,axes,[index[n] for n in anchors],target,weights)
    fitted = {n:points[index[n]].tolist() for n in heavy}
    rounded = {n:[float(f'{x:.3f}') for x in fitted[n]] for n in retained}
    lengths = []; rounded_lengths = []; angles = []; rounded_angles = []
    for a,b in bonds:
        if a in retained and b in retained:
            original = math.dist(coordinates[a],coordinates[b])
            lengths.append(abs(math.dist(fitted[a],fitted[b])-original))
            rounded_lengths.append(abs(math.dist(rounded[a],rounded[b])-original))
    for centre in retained:
        for a,b in combinations(sorted(graph[centre]&set(retained)),2):
            before = _observed('angle',[coordinates[n] for n in (a,centre,b)])
            after = _observed('angle',[fitted[n] for n in (a,centre,b)])
            final = _observed('angle',[rounded[n] for n in (a,centre,b)])
            if None in (before,after,final):
                raise ValueError('Degenerate internal angle')
            angles.append(abs(after-before)); rounded_angles.append(abs(final-before))
    hands = []
    for centre in ("C1'","C2'","C3'","C4'"):
        neighbors = sorted(n for n in graph[centre] if elements[n] not in {'H','D'})
        if (len(neighbors)!=3 or not _hand(_volume(coordinates,centre,neighbors),_volume(fitted,centre,neighbors))
                or not _hand(_volume(coordinates,centre,neighbors),_volume(rounded,centre,neighbors))):
            raise ValueError('Seed must preserve all four source sugar hands')
        hands.append({'centre':centre,'ordered_neighbors':neighbors,'source_volume':_volume(coordinates,centre,neighbors),
                      'full_volume':_volume(fitted,centre,neighbors),'rounded_volume':_volume(rounded,centre,neighbors)})
    if max(lengths)>1e-9 or max(angles)>1e-8 or max(rounded_lengths)>.002:
        raise ValueError('Kinematic or PDB serialization preservation failed')
    lines = []
    for line in (control/'model.pdb').read_text().splitlines(keepends=True):
        if line[:6] in {'ATOM  ','HETATM'} and line[21:26]=='A   2':
            fields = ''.join(f'{x:8.3f}' for x in fitted[line[12:16].strip()])
            if len(fields)!=24:
                raise ValueError('Seed exceeds fixed PDB coordinate fields')
            line = line[:30]+fields+line[54:]
        lines.append(line)
    junctions = []
    for partner,n in [(('A','1','','',"O3'"),'P'),(('A','3','','','P'),"O3'")]:
        other = frame[partner]['xyz']
        junctions.append({'target_atom':n,'partner_atom':':'.join([partner[0],partner[1],partner[-1]]),
                          'before':math.dist(prior['A','2','','',n]['xyz'],other),
                          'full_precision':math.dist(fitted[n],other),'pdb_rounded':math.dist(rounded[n],other)})
    report = {'schema_version':1,'policy_id':POLICY_ID,'status':'FANA_BRIDGE_SEED_REVIEW','component':code,
              'config':config,'virtual_leaving_atom':leaving,'virtual_atom_written':False,
              'virtual_partner_error':math.dist(fitted[leaving],frame['A','1','','',"O3'"]['xyz']),
              'fit_anchors':anchors,'fit_weights':weights.tolist(),'rotors':groups,'search':search,
              'full_precision_heavy_coordinates':{n:fitted[n] for n in retained},'sugar_hands':hands,'junctions':junctions,
              'preservation':{'four_sugar_hands':True,'max_bond_length_error':max(lengths),'max_angle_error_degrees':max(angles),
                              'rounded_max_bond_length_error':max(rounded_lengths),'rounded_max_angle_error_degrees':max(rounded_angles),
                              'flanking_records_exact':True,'source_dictionary_unchanged':True},
              'numpy_version':np.__version__,'native_linkage':'NOT_ASSESSED','chemical_qualification':'NOT_ESTABLISHED',
              'clashes':'NOT_ASSESSED','automatic_adoption':False,'diffraction_refinement':'NOT_RUN'}
    return report, ''.join(lines)


def prepare_fana_bridge_seed(placement, output, *, endpoint_weight=1000.):
    """Freeze a separate bounded construction seed; preserve every prior attempt."""
    control = _path(placement,directory=True); out = Path(output).expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents) or out.is_relative_to(control) or control.is_relative_to(out):
        raise ValueError('Seed output must be separate from preserved source')
    config = {'endpoint_weight':endpoint_weight}
    report, model = _seed(control,config)
    before = {p:p.read_bytes() for p in control.rglob('*') if p.is_file()}
    out.mkdir(parents=True,exist_ok=False); shutil.copytree(control,out/'placement')
    _save(out/'config.json',config)
    frozen, frozen_model = _seed(out/'placement',config)
    if frozen!=report or frozen_model!=model or any(p.read_bytes()!=data for p,data in before.items()):
        raise ValueError('Seed authority changed while freezing inputs')
    (out/'model.pdb').write_text(model); _save(out/'seed.json',report)
    files = {p.relative_to(out).as_posix():_digest(p) for p in out.rglob('*') if p.is_file()}
    _save(out/'receipt.json',{'schema_version':1,'policy_id':POLICY_ID,'files':files})
    return read_fana_bridge_seed(out)


def read_fana_bridge_seed(directory):
    """Recompute source binding, search and output without native execution."""
    root = _path(directory,directory=True); paths = list(root.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('Seed package cannot traverse symlinks')
    expected = _FILES|{'receipt.json'}|{'placement/'+p.relative_to(root/'placement').as_posix() for p in (root/'placement').rglob('*') if p.is_file()}
    before = {p:p.read_bytes() for p in paths if p.is_file()}
    if {p.relative_to(root).as_posix() for p in before}!=expected:
        raise ValueError('Unexpected or missing seed package file')
    r = _load(root/'receipt.json')
    if (set(r)!={'schema_version','policy_id','files'} or type(r['schema_version']) is not int
            or r['schema_version']!=1 or r['policy_id']!=POLICY_ID or set(r['files'])!=expected-{'receipt.json'}
            or any(_digest(root/name)!=value for name,value in r['files'].items())):
        raise ValueError('Invalid seed receipt or checksum')
    report, model = _seed(root/'placement',_load(root/'config.json'))
    if (report!=_load(root/'seed.json') or model.encode()!=(root/'model.pdb').read_bytes()
            or any(p.read_bytes()!=b for p,b in before.items())):
        raise ValueError('Stored seed differs from fresh derivation')
    return report
