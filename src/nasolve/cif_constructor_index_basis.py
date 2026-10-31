"""Prove native named restraint order separately from coordinate evaluation order."""
import math
from .cif_stereochemistry_audit import _values,_graph,_coordinates,_volume,VOLUME_EPSILON

POLICY_ID='cif-native-named-restraint-index-basis-v1'
INTEGER_KEYS_POLICY_ID='cif-native-integer-restraint-keys-v2'
SOURCE_PATHS=('elbow/cctbx_api/RestraintClass.py','elbow/cctbx_api/geometry_manager.py')


def analyze_index_basis(source,code,trace):
    """Retain both array interpretations without rewriting a native manager."""
    values=_values(source,code);_,_,_,neighbors=_graph(values);_,xyz=_coordinates(values,source=True)
    events=trace.get('events',[]);managers=[]
    proofs={r.get('path'):r for r in trace.get('index_sources',[])}
    integer_keys=trace.get('index_policy_id')==INTEGER_KEYS_POLICY_ID
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
        local=e.get('local_atoms',[])
        binding=bind_integer_keys(basis,local,selected) if integer_keys else None
        records=binding['named_atoms'] if binding else basis.get('native_atom_keys',[])
        named=lambda rows:[(r.get('atom'),r.get('global_index')) for r in rows]
        keys=named(records);local_keys=named(local)
        valid=(bool(records) and len(records)==len(local) and len(set(keys))==len(records)
            and len({i for _,i in keys})==len(keys) and all(type(i) is int for _,i in keys)
            and set(keys)==set(local_keys) and all(r.get('same_parent_object') is True and vector(r.get('stored_xyz')) for r in records))
        ordered=sorted(records,key=lambda a:a['restraint_index'] if integer_keys else a['global_index']) if valid else []
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
        if integer_keys:checks['integer_key_binding']=binding['checks_pass']
        managers.append({'call_id':e['call_id'],'centre':e.get('centre'),'checks':checks,'checks_pass':all(checks.values()),
            'restraint_atom_order':[r['atom'] for r in ordered],'evaluation_atom_order':[r.get('atom') for r in local],
            'orders_identical':aligned and evaluation_ok and named(ordered)==named(local),
            'restraint_basis_targets':declared,'evaluation_basis_targets':evaluated,
            'returned_chirality_parameters':basis.get('returned_chirality_parameters'),
            'target_source_hands_preserved':bool(declared) and all(p['source_hand_matches_target'] for p in declared)})
        if integer_keys:managers[-1]['integer_key_binding']=binding
    methods=trace.get('index_method_sources',[])
    policy=INTEGER_KEYS_POLICY_ID if integer_keys else POLICY_ID
    checks={'policy':trace.get('index_policy_id')==policy,'managers_recorded':bool(managers),
        'named_basis_evidence':all(m['checks_pass'] for m in managers),
        'native_factory_source_selected':len(methods)==1 and methods[0].get('method')=='geometry_manager.run' and selected(methods[0]),
        'methods_restored':trace.get('methods_restored') is True,'source_hashes_preserved':trace.get('source_hashes_preserved') is True}
    return {'schema_version':1,'policy_id':policy,'status':'INDEX_BASIS_OBSERVATION_PASS' if all(checks.values()) else 'REVIEW','checks':checks,'checks_pass':all(checks.values()),
        'managers':managers,'target_source_hands_preserved':bool(managers) and all(m['target_source_hands_preserved'] for m in managers),
        'absolute_cip_assignment':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'interpretation':'Named native dictionary keys plus exact returned-coordinate alignment prove a restraint order. The observed getter order is retained separately. Neither is silently substituted into native computation; original mapping/hand/metadata findings remain recorded.'}


def bind_integer_keys(basis,local,selected):
    """Bind recorded native integer keys/link positions to exact shared atoms.

    No GetRestraints/GetCoordinates/get_key call is repeated. The adapter follows
    the selected native get_key convention (unique_index before index); the
    recorded link and returned vectors must independently agree. V1 observations
    remain replayable and their empty atom-key records are never filled in.
    """
    atoms=basis.get('local_atom_keys',[]);entries=basis.get('integer_coordinate_entries',[]);links=basis.get('native_link',[])
    def unique(rows,key):return len(rows)==len({r.get(key) for r in rows})
    bounded=all(isinstance(rows,list) and 0<len(rows)<=64 and all(isinstance(r,dict) for r in rows) for rows in [atoms,entries,links,local])
    valid=False;named=[]
    if bounded:
        valid=(len(atoms)==len(entries)==len(links)==len(local)
            and unique(atoms,'atom') and unique(atoms,'native_key') and unique(entries,'native_key') and unique(links,'native_key')
            and unique(links,'index') and unique(local,'atom')
            and all(type(r.get('native_key')) is int for r in atoms+entries+links)
            and all(type(r.get('index')) is int for r in links)
            and {r['native_key'] for r in atoms}=={r['native_key'] for r in entries}=={r['native_key'] for r in links}
            and {r['index'] for r in links}==set(range(len(local)))
            and {(r.get('atom'),r.get('global_index')) for r in atoms}=={(r.get('atom'),r.get('global_index')) for r in local}
            and all(r.get('same_parent_object') is True and type(r.get('global_index')) is int
                and r.get('key_attribute')==('unique_index' if r.get('unique_index') is not None else 'index')
                and r['native_key']==(r.get('unique_index') if r.get('key_attribute')=='unique_index' else r['global_index']) for r in atoms))
        if valid:
            positions={r['native_key']:r['index'] for r in links};vectors={r['native_key']:r.get('stored_xyz') for r in entries}
            valid=all(positions[key]==i for i,key in enumerate(sorted(positions)))
            if valid:named=[{'atom':r['atom'],'global_index':r['global_index'],'same_parent_object':True,
                'stored_xyz':vectors[r['native_key']],'restraint_index':positions[r['native_key']],'native_key':r['native_key']} for r in atoms]
    methods=basis.get('integer_key_methods',[])
    checks={'bounded_complete_key_inventory':bounded,'integer_keys_link_and_named_atoms_agree':valid,
        'selected_native_key_methods':len(methods)==2 and {r.get('method') for r in methods}=={'RestraintClass.get_key','RestraintClass.GetCoordinates'} and all(selected(r) for r in methods)}
    return {'checks':checks,'checks_pass':all(checks.values()),'named_atoms':named if all(checks.values()) else []}
