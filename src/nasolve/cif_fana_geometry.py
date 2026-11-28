"""Source/stereo and native endpoint checks for a separate selected FANA trial."""
from copy import deepcopy
from pathlib import Path
import math

from .cif_attachment_native import _capture, _json, COORDINATE_ROUNDOFF_A
from .cif_fana_topology import require_fana_topology
from .cif_fana_junction import _bind, _path
from .cif_fana_placement import _hand
from .cif_stereochemistry_audit import _graph, _coordinates, _volume
from .cif_selected_geometry import _start, run_selected_geometry, read_selected_geometry, SelectedCoordinates
from .cif_fixed_geometry import qualify_fixed_policy_geometry, review_fixed_coordinates
from .cif_native_gradients import review_native_gradients
from .cif_native_nonbonded import review_native_nonbonded
from .cif_nonbonded_cache_audit import compare_cache_snapshots
from .cif_mixed_gradient import _numeric_equal, _manager_digest
from .cif_topology_gate import review_native_topology
from .cif_catalogue import _digest

POLICY_ID = 'cif-source-bound-fana-selected-geometry-v1'


def _indices(native, site):
    chain,resseq=site.split(':')
    return [a['i_seq'] for a in native['atoms'] if a['identity']['chain_id'].strip()==chain and a['identity']['resseq'].strip()==resseq]


def review_fana_coordinates(values, native, site, selected, full, rounded):
    """Require exact whole-residue scope and all four source-relative sugar hands."""
    if selected != _indices(native,site):raise ValueError('Require the exact complete central residue selection')
    space=SelectedCoordinates(native['geometry']['sites_cart_exact'],selected);space.pack(full)
    if len(rounded)!=len(space.points) or any(len(p)!=3 for p in rounded):raise ValueError('Incomplete serialized native coordinates')
    space._finite([v for p in rounded for v in p],3*len(rounded))
    roundoff=max(math.dist(p,rounded[i]) for i,p in enumerate(space.points) if i not in selected)
    if roundoff>COORDINATE_ROUNDOFF_A:raise ValueError('Fixed native coordinates differ beyond existing capture roundoff')
    elements,_,_,graph=_graph(values);source=_coordinates(values,source=False)[1]
    coordinates=[{native['atoms'][i]['atom_id']:points[i] for i in selected} for points in [full,rounded]]
    if len(coordinates[0])!=len(selected):raise ValueError('Ambiguous selected atom identity')
    rows=[]
    for centre in ("C1'","C2'","C3'","C4'"):
        neighbors=sorted(n for n in graph[centre] if elements[n] not in {'H','D'})
        if len(neighbors)!=3:raise ValueError('Require source-defined FANA sugar centres')
        volumes=[_volume(p,centre,neighbors) for p in [source,*coordinates]]
        rows.append({'centre':centre,'ordered_neighbors':neighbors,'source_volume':volumes[0],
            'full_precision_volume':volumes[1],'serialized_volume':volumes[2],
            'preserved':all(_hand(volumes[0],v) for v in volumes[1:])})
    return {'site':site,'moving_atom_count':len(selected),'fixed_coordinates_preserved':True,'native_fixed_coordinate_roundoff_max_angstrom':roundoff,
            'native_coordinate_roundoff_tolerance_angstrom':COORDINATE_ROUNDOFF_A,'sugar_hands':rows,
            'four_sugar_hands_preserved':all(r['preserved'] for r in rows),'absolute_cip_assignment':'NOT_RUN'}


def run_fana_selected_geometry(control, bridge_seed, native_receipt, output_parent, executable, **kwargs):
    """Require the existing exact source/topology gate before allocating a trial."""
    _,native,model,_=_start(native_receipt)
    require_fana_topology(control,model,native_receipt,bridge_seed=bridge_seed)
    placement,_,_=_bind(Path(control),model,native,Path(bridge_seed))
    if 'moving_indices' in kwargs:raise ValueError('FANA trial selects its complete source-bound central residue')
    return run_selected_geometry(native_receipt,output_parent,executable,
        moving_indices=_indices(native,placement['context']['site']),**kwargs)


def inspect_fana_selected_geometry(control, bridge_seed, trial, endpoint_receipt, pair_receipt):
    """Review a candidate without weakening the exact seed binder or accepting geometry."""
    root=_path(trial,directory=True);control=_path(control,directory=True);bridge_seed=_path(bridge_seed,directory=True)
    trial_review=read_selected_geometry(root)
    before_receipt,before,model,_=_start(root/'start/native_receipt.json')
    start_topology=require_fana_topology(control,model,root/'start/native_receipt.json',bridge_seed=bridge_seed)
    placement,values,_=_bind(control,model,before,bridge_seed)
    raw=_json((root/'selected_result.json').read_bytes());candidate=root/'candidate.pdb';payload=candidate.read_bytes()
    endpoint_receipt=_path(endpoint_receipt);pair_receipt=_path(pair_receipt)
    er,after,frozen=_capture(endpoint_receipt,payload);pr,paired,pfrozen=_capture(pair_receipt,payload);frozen.update(pfrozen)
    for receipt,native in [(er,after),(pr,paired)]:
        if receipt['status']!='REVIEW' or native.get('fatal_problems') is not None or native.get('unused_definitions') or native.get('unsupported_fields'):
            raise ValueError('Require complete usable native endpoint interpretations')
        old=[(q['role'],q['sha256'],q['size']) for q in before_receipt['inputs'] if q['role']!='model']
        new=[(q['role'],q['sha256'],q['size']) for q in receipt['inputs'] if q['role']!='model']
        if old!=new or receipt['phil_namespace_policy']!=before_receipt['phil_namespace_policy']:
            raise ValueError('Endpoint source dictionaries or PHIL differ from the starting authority')
    if _manager_digest(after)!=_manager_digest(paired) or after['energy_inventory']!=paired['energy_inventory']:
        raise ValueError('Endpoint pair and derivative captures describe different managers')
    pairs=review_native_nonbonded(paired);derivatives=review_native_gradients(after)
    mechanics=qualify_fixed_policy_geometry(before,after,candidate,{'candidate_sha256':trial_review['candidate_sha256']})
    expected=[{'endpoints':[dict(zip(('site','component','atom_id'),p)) for p in edge]} for edge in start_topology['declared_links']]
    topology=review_native_topology(after,payload,expected)
    coords=review_fana_coordinates(values,before,placement['context']['site'],raw['moving_indices'],raw['final_sites_cart'],after['geometry']['sites_cart_exact'])
    comparison=compare_cache_snapshots(raw['serialized_pair_inventory']['snapshots'][-1],paired['nonbonded_inventory']['snapshots'][-1],before['atom_count'])
    # Neighbour counts may differ only with explicit zero-contribution pair proof.
    fixed=deepcopy(raw['serialized']);fresh=deepcopy(after['energy_inventory']['snapshots'][0])
    fixed['proxy_counts'].pop('n_nonbonded_proxies');fresh['proxy_counts'].pop('n_nonbonded_proxies')
    energy_match=_numeric_equal(fixed,fresh)
    checks={'source_and_native_mechanics_preserved':mechanics['mechanics_checks_pass'],
            'exact_declared_topology':topology['link_status']=='MATCH','four_sugar_hands_preserved':coords['four_sugar_hands_preserved'],
            'full_precision_sampled_derivatives':trial_review['endpoint_sampled_derivatives_pass'],
            'serialized_sampled_derivatives':derivatives['sampled_derivatives_pass'],'fixed_and_fresh_native_energy_gradient_match':energy_match,
            'nonbonded_cache_changes_proven_zero':comparison['checks_pass'],
            'same_numerical_sources':before['gradient_inventory']['installed_numeric_sources']==after['gradient_inventory']['installed_numeric_sources']}
    if any(p.read_bytes()!=data for p,data in frozen.items()):raise ValueError('Endpoint evidence changed during review')
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','candidate_checks_pass':all(checks.values()),'checks':checks,
        'trial':trial_review,'coordinates':coords,'topology':topology,'mechanics':mechanics,'cache_comparison':comparison,
        'endpoint_nonbonded':{k:pairs[k] for k in ('pair_count','positive_residual_pairs','total_residual','worst','by_site_pair')},
        'geometry_before':review_fixed_coordinates(before,before['geometry']['sites_cart_exact']),
        'geometry_after':review_fixed_coordinates(after,after['geometry']['sites_cart_exact']),
        'bindings':{'placement':_digest((control/'receipt.json').read_bytes()),'bridge_seed':_digest((bridge_seed/'receipt.json').read_bytes()),
                    'trial':_digest((root/'receipt.json').read_bytes()),'endpoint_receipt':_digest(endpoint_receipt.read_bytes()),'pair_receipt':_digest(pair_receipt.read_bytes())},
        'native_execution':'NOT_RUN_BY_READER','automatic_adoption':False,'chemical_qualification':'NOT_ESTABLISHED',
        'geometry_accepted':False,'limitations':['Source-relative hands do not independently assign absolute CIP or qualify protonation/numerical targets.',
            'A bounded central-only trial may stop at its limit; scores and preserved mechanics do not establish physical geometry.',
            'Flank H/charge/order/OP3 differences, ordinary mutation, whole-model support and diffraction refinement remain separate.']}
