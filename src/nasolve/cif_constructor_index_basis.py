"""Prove native named restraint order separately from coordinate evaluation order."""
import math
from .cif_stereochemistry_audit import _values,_graph,_coordinates,_volume,VOLUME_EPSILON

POLICY_ID='cif-native-named-restraint-index-basis-v1'
SOURCE_PATHS=('elbow/cctbx_api/RestraintClass.py','elbow/cctbx_api/geometry_manager.py')


def analyze_index_basis(source,code,trace):
    """Retain both array interpretations without rewriting a native manager."""
    values=_values(source,code);_,_,_,neighbors=_graph(values);_,xyz=_coordinates(values,source=True)
    events=trace.get('events',[]);managers=[]
    proofs={r.get('path'):r for r in trace.get('index_sources',[])}
    def selected(method):
        row=proofs.get(method.get('path'))
        return (row is not None and method.get('module')=='elbow.cctbx_api.'+row['path'].split('/')[-1].removesuffix('.py')
            and method.get('sha256')==row.get('sha256') and isinstance(method.get('sha256'),str)
            and len(method['sha256'])==64 and type(method.get('definition_line')) is int and method['definition_line']>0)
    def vector(v):return isinstance(v,list) and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in v)
    def targets(proxies,atoms,centre):
        result=[]
        for p in proxies:
            ids=p.get('i_seqs',[]);v=p.get('volume_ideal');w=p.get('weight');both=p.get('both_signs')
            ok=(len(ids)==4 and len(set(ids))==4 and all(type(i) is int and 0<=i<len(atoms) for i in ids)
                and type(v) in (int,float) and math.isfinite(v) and abs(v)>VOLUME_EPSILON
                and type(w) in (int,float) and math.isfinite(w) and w>0 and type(both) is bool)
            names=[atoms[i]['atom'] for i in ids] if ok else []
            ok=ok and names[0]==centre and len(neighbors.get(centre,()))==4 and set(names[1:])<=neighbors[centre]
            volume=_volume(xyz,names[0],names[1:]) if ok else None
            result.append({'i_seqs':ids,'ordered_atoms':names,'volume_ideal':v,'weight':w,'both_signs':both,'valid_proxy_basis':bool(ok),
                'source_volume_in_proxy_basis':volume,'source_hand_matches_target':bool(ok and not both and abs(volume)>VOLUME_EPSILON and volume*v>0)})
        return result
    for e in events:
        if e.get('method')!='CCTBXMixins.GetNewManager' or e.get('phase')!='exit':continue
        children=[c for c in events if c.get('parent_call_id')==e['call_id']]
        parameters=[c for c in children if c.get('method')=='ChiralClass.GetRestrainedParameters' and c.get('phase')=='exit']
        getters=[c for c in children if c.get('method')=='CCTBXMixins.GetCoordinates' and c.get('phase')=='exit']
        basis=parameters[0].get('mapping',{}).get('index_basis',{}) if len(parameters)==1 else {}
        records=basis.get('native_atom_keys',[]);local=e.get('local_atoms',[])
        named=lambda rows:[(r.get('atom'),r.get('global_index')) for r in rows]
        keys=named(records);local_keys=named(local)
        valid=(bool(records) and len(records)==len(local) and len(set(keys))==len(records)
            and len({i for _,i in keys})==len(keys) and all(type(i) is int for _,i in keys)
            and set(keys)==set(local_keys) and all(r.get('same_parent_object') is True and vector(r.get('stored_xyz')) for r in records))
        ordered=sorted(records,key=lambda a:a['global_index']) if valid else []
        coordinates=basis.get('returned_coordinates')
        aligned=(bool(ordered) and len({tuple(a['stored_xyz']) for a in ordered})==len(ordered)
            and coordinates==[a['stored_xyz'] for a in ordered])
        getter=getters[-1] if getters else {};returned=getter.get('mapping',{}).get('coordinates_returned')
        evaluation_ok=bool(getters) and returned==[a.get('xyz') for a in local] and all(vector(a.get('xyz')) for a in local)
        proxies=e.get('mapping',{}).get('chirality_proxies',[])
        declared=targets(proxies,ordered,e.get('centre')) if aligned and isinstance(proxies,list) else []
        evaluated=targets(proxies,local,e.get('centre')) if evaluation_ok and isinstance(proxies,list) else []
        checks={'completed':e.get('status')=='COMPLETED','native_named_keys':valid,'restraint_method_selected':selected(basis.get('restraint_method',{})),
            'parameter_coordinates_match_index_order':aligned,'evaluation_getter_matches_local_order':evaluation_ok,
            'restraint_proxy_bases_valid':bool(declared) and all(p['valid_proxy_basis'] for p in declared)}
        managers.append({'call_id':e['call_id'],'centre':e.get('centre'),'checks':checks,'checks_pass':all(checks.values()),
            'restraint_atom_order':[r['atom'] for r in ordered],'evaluation_atom_order':[r.get('atom') for r in local],
            'orders_identical':aligned and evaluation_ok and named(ordered)==named(local),
            'restraint_basis_targets':declared,'evaluation_basis_targets':evaluated,
            'returned_chirality_parameters':basis.get('returned_chirality_parameters'),
            'target_source_hands_preserved':bool(declared) and all(p['source_hand_matches_target'] for p in declared)})
    methods=trace.get('index_method_sources',[])
    checks={'policy':trace.get('index_policy_id')==POLICY_ID,'managers_recorded':bool(managers),
        'named_basis_evidence':all(m['checks_pass'] for m in managers),
        'native_factory_source_selected':len(methods)==1 and methods[0].get('method')=='geometry_manager.run' and selected(methods[0]),
        'methods_restored':trace.get('methods_restored') is True,'source_hashes_preserved':trace.get('source_hashes_preserved') is True}
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'INDEX_BASIS_OBSERVATION_PASS' if all(checks.values()) else 'REVIEW','checks':checks,'checks_pass':all(checks.values()),
        'managers':managers,'target_source_hands_preserved':bool(managers) and all(m['target_source_hands_preserved'] for m in managers),
        'absolute_cip_assignment':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'interpretation':'Named native dictionary keys plus exact returned-coordinate alignment prove a restraint order. The observed getter order is retained separately. Neither is silently substituted into native computation; original mapping/hand/metadata findings remain recorded.'}
