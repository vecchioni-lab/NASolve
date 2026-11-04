"""Read-only attribution of coordinate-dependent native manager differences.

An explanation never changes the original exact-comparison verdict. Origin
identifiers and cutoffs are explicit caller evidence, not residue exceptions.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from math import dist, isfinite
import re

from .cif_captured_geometry import _site, review_captured_geometry
from .cif_fixed_geometry import _points

RELOAD_POLICY = 'cif-native-reload-attribution-v1'


def native_hbond_cutoff(text: str) -> float:
    """Read one value from normalized native PHIL, without executing a parser.

    This intentionally supports native ``as_str`` scope/assignment lines only;
    it is not a general PHIL parser and is not used to supply runtime parameters.
    """
    scopes=[];values=[]
    target=['pdb_interpretation','secondary_structure','nucleic_acid']
    for line in text.splitlines():
        line=line.strip()
        if line=='}':
            if not scopes:raise ValueError('Unbalanced normalized native PHIL')
            scopes.pop();continue
        opened=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)\s*\{',line)
        if opened:scopes.append(opened[1]);continue
        assignment=re.fullmatch(r'hbond_distance_cutoff\s*=\s*(\S+)',line)
        if assignment and scopes==target:values.append(assignment[1])
    if scopes or len(values)!=1:raise ValueError('Require one scoped native hydrogen-bond cutoff')
    value=float(values[0])
    if not isfinite(value) or value<=0:raise ValueError('Require a finite positive native cutoff')
    return value


def _rows(rows):
    return Counter(json.dumps(r,sort_keys=True,allow_nan=False) for r in rows)


def _positive(value):
    return type(value) in {int,float} and isfinite(value) and value>0


def _identities(native):
    return [{k:v for k,v in a.items() if k!='xyz'} for a in native['atoms']]


def audit_native_reload(before: dict, after: dict, *, cutoff: float,
                        hydrogen_bond_origin_id: int) -> dict:
    """Explain only a narrow addition pattern, always retaining REVIEW.

    Exact original proxies must survive. Every added intersite bond must cross
    the supplied cutoff and have two new angles attached through original
    same-site covalent stems, one on each endpoint. Any other change remains
    unexplained. Matching this pattern is not causal proof or chemistry approval.
    """
    review_captured_geometry(before);review_captured_geometry(after)
    if type(hydrogen_bond_origin_id) is not int or isinstance(cutoff,bool) or not isfinite(float(cutoff)) or cutoff<=0:
        raise ValueError('Require explicit finite cutoff and native origin identifier')
    if len(before['atoms'])!=len(after['atoms']):raise ValueError('Attribution requires matching indexed atom counts')
    left,right=before['geometry'],after['geometry'];delta={}
    for kind in sorted(set(left['proxy_details'])|set(right['proxy_details'])):
        a,b=_rows(left['proxy_details'].get(kind,[])),_rows(right['proxy_details'].get(kind,[]))
        delta[kind]={'missing':[json.loads(s) for s in (a-b).elements()],
                     'extra':[json.loads(s) for s in (b-a).elements()]}
    exact=not any(v['missing'] or v['extra'] for v in delta.values())
    unchanged={'atom_identities':_identities(before)==_identities(after),
        'site_definitions':_rows(before.get('monomer_mappings',{}).get('rows',[]))==_rows(after.get('monomer_mappings',{}).get('rows',[])),
        'custom_requests':left.get('custom_proxy_requests')==right.get('custom_proxy_requests')}
    reasons=[]
    if not all(unchanged.values()):reasons.append('Identity, definition or custom-request changes')
    if any(v['missing'] for v in delta.values()):reasons.append('Original proxies removed or changed')
    if any(v['extra'] for k,v in delta.items() if k not in {'bond_simple','angle'}):reasons.append('Other proxy categories changed')
    bonds=delta.get('bond_simple',{}).get('extra',[]);angles=delta.get('angle',{}).get('extra',[])
    stems={frozenset(r['i_seqs']) for r in left['proxy_details']['bond_simple']
           if r.get('origin_id')!=hydrogen_bond_origin_id and r.get('symmetry_operation') in {None,'x,y,z'}
           and len({_site(before['atoms'][i]) for i in r['i_seqs']})==1}
    existing={frozenset(r['i_seqs']) for r in left['proxy_details']['bond_simple']}
    activations=[];edges={}
    for bond in bonds:
        i,j=bond['i_seqs'];edge=frozenset((i,j));a=dist(before['atoms'][i]['xyz'],before['atoms'][j]['xyz']);b=dist(after['atoms'][i]['xyz'],after['atoms'][j]['xyz'])
        supported=(bond.get('origin_id')==hydrogen_bond_origin_id and bond.get('symmetry_operation') in {None,'x,y,z'}
            and _site(before['atoms'][i])!=_site(before['atoms'][j]) and a>cutoff+1e-9 and b<cutoff-1e-9
            and edge not in existing and edge not in edges and _positive(bond.get('weight')) and _positive(bond.get('distance_ideal')))
        if not supported:reasons.append('Added bond lacks an unambiguous supported cutoff crossing')
        edges[edge]=[]
        activations.append({'atoms':bond['atoms'],'i_seqs':bond['i_seqs'],'before_distance':a,'after_distance':b,
                            'cutoff':cutoff,'consistent_with_activation':supported,'native_target':bond.get('distance_ideal'),
                            'native_weight':bond.get('weight')})
    for angle in angles:
        indices=angle['i_seqs'];matches=[]
        if len(set(indices))==3 and angle.get('origin_id')==hydrogen_bond_origin_id and _positive(angle.get('weight')) and _positive(angle.get('angle_ideal')) and angle['angle_ideal']<=180:
            first,central,last=indices
            for opposite,stem in [(first,last),(last,first)]:
                edge=frozenset((opposite,central))
                if edge in edges and frozenset((central,stem)) in stems:matches.append((edge,central))
        if len(matches)!=1:reasons.append('Added angle lacks one matching added bond and original covalent stem')
        else:edges[matches[0][0]].append(matches[0][1])
    if any(len(v)!=2 or set(v)!=set(edge) for edge,v in edges.items()):reasons.append('Added bond does not have exactly two endpoint angles')
    if exact and all(unchanged.values()):classification='NO_PROXY_DRIFT'
    elif bonds and not reasons:classification='CUTOFF_CONSISTENT_HBOND_ACTIVATION'
    else:classification='UNEXPLAINED_NATIVE_DRIFT'
    return {'schema_version':1,'audit_kind':'cif_native_reload_attribution','policy_id':RELOAD_POLICY,
        'status':'REVIEW','classification':classification,'exact_proxy_preservation':exact,
        'unchanged':unchanged,'delta':delta,'activations':activations,'added_hydrogen_bonds':len(bonds),
        'associated_angles':len(angles),'unexplained_reasons':sorted(set(reasons)),
        'explicit_origin_id':hydrogen_bond_origin_id,'explicit_cutoff':cutoff,
        'original_exact_qualification':'UNCHANGED','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'limitations':['Cutoff consistency explains the observed pattern; it is not installed-source causal proof or a passed exact-manager check.',
                       'New native targets remain visible and define a changed objective; no cross-objective ranking or automatic adoption.']}


def audit_saved_endpoint_readback(before: dict, after: dict, fixed_result: dict) -> dict:
    """Compare native reread endpoints to the saved manager's rounded vector.

    The returned energy is a preserved historical evaluation, not a newly
    calculated energy of the freshly rebuilt manager or the reread floats.
    """
    review_captured_geometry(before);review_captured_geometry(after)
    points=_points(fixed_result['final_sites_cart'],before['atom_count'])
    rounded=[[float(f'{v:.3f}') for v in p] for p in points]
    observed=after['geometry']['sites_cart_exact']
    same=_identities(before)==_identities(after) and len(observed)==len(rounded)
    differences=[abs(a-b) for p,q in zip(observed,rounded) for a,b in zip(p,q)]
    maximum=max(differences,default=0.)
    signature=fixed_result.get('constraint_signature_before')
    fixed=(fixed_result.get('status')=='REVIEW' and bool(signature) and signature==fixed_result.get('constraint_signature_after'))
    matches=same and fixed and maximum<=1e-10 and all([float(f'{v:.3f}') for v in p]==q for p,q in zip(observed,rounded))
    return {'schema_version':1,'audit_kind':'cif_saved_fixed_manager_endpoint_readback','policy_id':RELOAD_POLICY,
        'status':'MATCH_AT_PDB_PRECISION' if matches else 'REVIEW','atom_count':len(points),
        'identities_preserved':same,'saved_fixed_constraint_signature_preserved':fixed,
        'native_float_max_difference':maximum,'native_float_comparison_tolerance':1e-10,
        'recorded_fixed_manager_pdb_evaluation':deepcopy(fixed_result['serialized']),
        'energy_basis':'PRESERVED_ORIGINAL_MANAGER_EVALUATION_AT_SAVED_PDB_ROUNDED_VECTOR',
        'new_native_execution':'NOT_RUN','new_optimization':'NOT_RUN','fresh_manager_equality':'NOT_IMPLIED',
        'scientific_approval':'NOT_RUN','automatic_adoption':False}
