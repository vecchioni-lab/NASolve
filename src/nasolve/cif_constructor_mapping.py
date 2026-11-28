"""Replay named local template coordinates and native chirality proxy bases."""
from itertools import combinations
import math

from .cif_stereochemistry_audit import _values,_graph,_coordinates,_volume,VOLUME_EPSILON

POLICY_ID='cif-native-local-coordinate-mapping-v1'


def analyze_constructor_mapping(source,code,trace):
    """Keep coordinate assignment evidence separate from molecular approval."""
    values=_values(source,code);elements,_,_,neighbors=_graph(values);_,reference=_coordinates(values,source=True)
    events=trace.get('events',[]);starts={};getters=[];setters=[];targets=[];permutations=[];frames_valid=True
    def rows(value):
        return (isinstance(value,list) and bool(value) and all(isinstance(v,list) and len(v)==3
            and all(type(x) in (int,float) and math.isfinite(x) for x in v) for v in value))
    def frame(e):
        nonlocal frames_valid
        atoms=e.get('local_atoms',[]);keys=[(a.get('atom'),a.get('global_index')) for a in atoms]
        ok=(bool(atoms) and len(set(keys))==len(atoms) and len({n for n,_ in keys})==len(atoms)
            and len({i for _,i in keys})==len(atoms) and all(n in elements and type(i) is int for n,i in keys)
            and all(a.get('same_parent_object') is True for a in atoms) and rows([a.get('xyz') for a in atoms]))
        frames_valid=frames_valid and ok
        return atoms,ok
    def hand(atoms,center):
        xyz={a['atom']:a['xyz'] for a in atoms};adjacent=sorted(neighbors.get(center,()))
        if len(adjacent)!=4 or set(xyz)!={center,*adjacent}:return None
        pairs=[(_volume(reference,center,p),_volume(xyz,center,p)) for p in combinations(adjacent,3)]
        pairs.append((_volume(reference,adjacent[0],adjacent[1:]),_volume(xyz,adjacent[0],adjacent[1:])))
        return all(min(abs(a),abs(b))>VOLUME_EPSILON and a*b>0 for a,b in pairs)
    for index,e in enumerate(events):
        # The outer molecule is not a local chiral template.
        if e.get('method')=='TopologyMixins.Chiralise':continue
        atoms,valid=frame(e)
        if e.get('phase')=='enter':starts[e.get('call_id')]=e
        if e.get('phase')!='exit':continue
        start=starts.get(e.get('call_id'),{});before=start.get('local_atoms',[]);mapping=e.get('mapping',{});method=e.get('method')
        same_order=[(a.get('atom'),a.get('global_index')) for a in before]==[(a.get('atom'),a.get('global_index')) for a in atoms]
        complete=e.get('status')=='COMPLETED' and valid and same_order
        if method=='CCTBXMixins.GetCoordinates':
            returned=mapping.get('coordinates_returned');args=start.get('resolved_arguments',{})
            getters.append({'call_id':e['call_id'],'centre':e.get('centre'),'matches_named_order':complete and rows(returned)
                and args.get('cctbx_format') is True and args.get('proper_atoms_only') is False
                and returned==[a['xyz'] for a in before]==[a['xyz'] for a in atoms]})
        if method=='CCTBXMixins.SetCoordinates':
            supplied=start.get('mapping',{}).get('coordinates_input');args=start.get('resolved_arguments',{})
            local_names={a.get('atom') for a in before}
            outside=lambda event:{a['atom']:a for a in event.get('snapshot',{}).get('atoms',[]) if a['atom'] not in local_names}
            setters.append({'call_id':e['call_id'],'centre':e.get('centre'),'matches_named_order':complete and rows(supplied)
                and args.get('cctbx_format') is True and supplied==[a['xyz'] for a in atoms] and outside(start)==outside(e)})
        if method=='CCTBXMixins.GetNewManager':
            proxies=mapping.get('chirality_proxies')
            if not isinstance(proxies,list) or not proxies:
                targets.append({'call_id':e['call_id'],'valid_proxy_basis':False,'source_hand_matches_target':False});continue
            for p in proxies:
                ids=p.get('i_seqs',[]);target=p.get('volume_ideal');weight=p.get('weight');both=p.get('both_signs')
                ok=(complete and len(ids)==4 and len(set(ids))==4 and all(type(i) is int and 0<=i<len(atoms) for i in ids)
                    and type(target) in (int,float) and math.isfinite(target) and abs(target)>VOLUME_EPSILON
                    and type(weight) in (int,float) and math.isfinite(weight) and weight>0 and type(both) is bool)
                names=[atoms[i]['atom'] for i in ids] if ok else []
                ok=ok and set(names[1:])<=neighbors.get(names[0],set()) and len(neighbors.get(names[0],()))==4
                volume=_volume(reference,names[0],names[1:]) if ok else None
                targets.append({'call_id':e['call_id'],'centre':e.get('centre'),'i_seqs':ids,'ordered_atoms':names,
                    'volume_ideal':target,'weight':weight,'both_signs':both,'source_volume_in_proxy_basis':volume,
                    'valid_proxy_basis':bool(ok),'source_hand_matches_target':bool(ok and not both and abs(volume)>VOLUME_EPSILON and volume*target>0)})
        if method=='ChiralClass.Optimise':
            children=[x for x in events if x.get('parent_call_id')==e['call_id']]
            for j,child in enumerate(children):
                if child.get('method')!='ChiralClass.GetRSNotation' or child.get('phase')!='enter' or j==0:continue
                previous=children[j-1]
                if previous.get('method')!='ChiralClass.TightenRestraints' or previous.get('phase')!='exit':continue
                a=previous['local_atoms'];b=child['local_atoms'];keys=lambda rs:[(x['atom'],x['global_index']) for x in rs]
                ok=keys(a)==keys(b) and len({x['global_index'] for x in a})==len(a)
                expected={x['atom']:a[i]['xyz'] for i,x in enumerate(sorted(a,key=lambda x:x['global_index']))} if ok else {}
                permutations.append({'call_id':e['call_id'],'centre':e.get('centre'),'before_event':events.index(previous),'after_event':events.index(child),
                    'same_atom_order':ok,'coordinates_unchanged_by_identity':ok and all(x['xyz']==y['xyz'] for x,y in zip(a,b)),
                    'matches_sorted_index_transfer':ok and all(expected[x['atom']]==x['xyz'] for x in b),
                    'local_source_hand_before':hand(a,e.get('centre')),'local_source_hand_after':hand(b,e.get('centre'))})
    checks={'policy':trace.get('mapping_policy_id')==POLICY_ID,'local_named_frames':frames_valid,
        'getters_recorded':bool(getters),'getters_match_named_order':all(r['matches_named_order'] for r in getters),
        'setters_recorded':bool(setters),'setters_match_named_order':all(r['matches_named_order'] for r in setters),
        'native_chirality_proxies_recorded':bool(targets),'native_proxy_bases_valid':all(r['valid_proxy_basis'] for r in targets),
        'methods_restored':trace.get('methods_restored') is True,'source_hashes_preserved':trace.get('source_hashes_preserved') is True}
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'MAPPING_OBSERVATION_PASS' if all(checks.values()) else 'REVIEW',
        'checks':checks,'checks_pass':all(checks.values()),'coordinate_getters':getters,'coordinate_setters':setters,'native_chirality_targets':targets,
        'target_source_hands_preserved':bool(targets) and all(r['source_hand_matches_target'] for r in targets),
        'post_optimizer_transfers':permutations,'absolute_cip_assignment':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'interpretation':'Named local frames and native indexed proxy bases only. Parent atoms can occupy different temporary frames; transfers and local target signs do not establish a completed molecular configuration or causal defect.'}
