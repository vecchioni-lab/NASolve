"""Bounded observation of native local chiral construction, without repair."""
from inspect import getsource
from itertools import combinations
import math

from .cif_source_constructor import _snapshot
from .cif_declared_charge_control import native_inventory
from .cif_stereochemistry_audit import _values,_graph,_coordinates,_volume,reader_stereo_inventory,VOLUME_EPSILON

POLICY_ID='cif-native-chiral-boundary-observation-v1'


def assess_snapshot_hands(source,code,snapshot):
    """Compare all four neighbor bases, without assigning absolute CIP."""
    values=_values(source,code);elements,bonds,charges,neighbors=_graph(values);_,reference=_coordinates(values,source=True)
    stereo=reader_stereo_inventory(source,code);atoms,observed_bonds,valid=_snapshot(snapshot)
    xyz={n:a['xyz'] for n,a in atoms.items()} if valid else {}
    signed={r['center']:r for r in stereo['source_signed_chirality']}
    known={n for n,r in stereo['atoms'].items() if r['declared_stereo'] in {'R','S'}}
    def volume(points,center,ordered):
        if any(n not in points or len(points[n])!=3 or any(not math.isfinite(v) for v in points[n]) for n in [center,*ordered]):return None
        return _volume(points,center,ordered)
    def match(a,b):return a is not None and b is not None and min(abs(a),abs(b))>VOLUME_EPSILON and a*b>0
    rows=[]
    for center in sorted(set(signed)|known):
        adjacent=sorted(neighbors[center]);bases=[]
        for ordered in combinations(adjacent,3):
            a,b=(volume(p,center,ordered) for p in [reference,xyz])
            bases.append({'ordered_neighbors':list(ordered),'source_volume':a,'observed_volume':b,'hand_preserved':match(a,b)})
        a,b=(volume(p,adjacent[0],adjacent[1:]) for p in [reference,xyz]) if len(adjacent)==4 else (None,None)
        rows.append({'centre':center,'requires_fixed_hand':center in known or signed[center]['volume_sign'].lower()!='both',
            'triple_bases':bases,'all_bases_preserve_hand':len(adjacent)==4 and len(bases)==4 and all(v['hand_preserved'] for v in bases),
            'four_neighbor_source_volume':a,'four_neighbor_observed_volume':b,'four_neighbor_hand_preserved':match(a,b)})
    orders={'SINGLE':1,'DOUBLE':2,'TRIPLE':3,'AROMATIC':1.5,'DELOCALIZED':1.5}
    graph=(valid and set(atoms)==set(elements) and observed_bonds=={p:orders[o] for p,o in bonds.items()}
        and snapshot['molecule_charge']==sum(charges.values())
        and all(atoms[n]['element'].upper()==e and atoms[n]['native_atom_charge']==charges[n] for n,e in elements.items()))
    return {'centres':rows,'finite_complete_snapshot':valid,'graph_and_charges_preserved':graph,'absolute_cip_assignment':'NOT_RUN'}


def analyze_constructor_trace(source,code,trace):
    """Replay observed boundaries and report first observations, not causality."""
    events=trace.get('events',[]);stack=[];ids=[];nesting=True;states=[];first={};prior_reviews=set();crossings=[]
    points=[('before',trace.get('before',{}))]+[(str(i),e.get('snapshot',{})) for i,e in enumerate(events)]+[('after',trace.get('after',{}))]
    def metadata(row):return {**row,'atoms':[{k:v for k,v in a.items() if k!='xyz'} for a in row.get('atoms',[])]}
    for label,snapshot in points:
        q=assess_snapshot_hands(source,code,snapshot);states.append({'boundary':label,**q})
        reviews={r['centre'] for r in q['centres'] if r['requires_fixed_hand'] and not (r['all_bases_preserve_hand'] and r['four_neighbor_hand_preserved'])}
        if reviews!=prior_reviews:crossings.append({'boundary':label,'new_reviews':sorted(reviews-prior_reviews),'cleared_reviews':sorted(prior_reviews-reviews)})
        if label not in {'before','after'}:
            e=events[int(label)]
            for center in reviews:
                first.setdefault(center,{'centre':center,'method':e.get('method'),'phase':e.get('phase'),'event_index':int(label),'call_id':e.get('call_id')})
        prior_reviews=reviews
    for e in events:
        if e.get('phase')=='enter':
            nesting=nesting and type(e.get('call_id')) is int and e['call_id'] not in ids and e.get('parent_call_id')==(stack[-1]['call_id'] if stack else None)
            ids.append(e.get('call_id'));stack.append(e)
        elif e.get('phase')=='exit':
            nesting=nesting and bool(stack)
            if stack:
                start=stack.pop();nesting=nesting and all(e.get(k)==start.get(k) for k in ['call_id','parent_call_id','method'])
            nesting=nesting and e.get('status') in {'COMPLETED','EXCEPTION'}
        else:nesting=False
    checks={'policy':trace.get('policy_id')==POLICY_ID,'complete_nested_calls':bool(ids) and not stack and nesting and len(events)==2*len(ids) and len(ids)<=256,
        'within_call_budget':trace.get('call_cap_reached',False) is False,
        'method_scope':all(e.get('method') in trace.get('hooks',[]) for e in events),
        'arguments_forwarded_unchanged':all(e.get('arguments_forwarded_unchanged') is True for e in events if e.get('phase')=='enter'),
        'methods_restored':trace.get('methods_restored') is True,'source_hashes_preserved':trace.get('source_hashes_preserved') is True,
        'finite_snapshots':all(s['finite_complete_snapshot'] for s in states),
        'graph_and_charges_preserved':all(s['graph_and_charges_preserved'] for s in states),
        'chemical_metadata_preserved':all(metadata(snapshot)==metadata(trace.get('before',{})) for _,snapshot in points),
        'shared_atom_coordinates_match':all(not a.get('same_parent_object') or any(p['atom']==a.get('atom') and p['xyz']==a.get('xyz')
            for p in e.get('snapshot',{}).get('atoms',[])) for e in events for a in e.get('local_atoms',[])),
        'endpoints_recorded':bool(events) and events[0].get('snapshot')==trace.get('before') and events[-1].get('snapshot')==trace.get('after')}
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'OBSERVATION_REPLAY_PASS' if all(checks.values()) else 'REVIEW',
        'checks':checks,'checks_pass':all(checks.values()),'call_count':len(ids),'states':states,
        'preexisting_hand_reviews':[r['centre'] for r in states[0]['centres'] if r['requires_fixed_hand'] and not (r['all_bases_preserve_hand'] and r['four_neighbor_hand_preserved'])],
        'first_observed_hand_reviews':[first[k] for k in sorted(first)],'adjacent_observed_crossings':crossings,
        'interpretation':'Boundaries include nested native operations. A first observation is not proof of a causal implementation defect or final molecular stereochemistry.',
        'absolute_cip_assignment':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False}


def compare_constructor_runs(control,observed,previous):
    """Separate fresh-repeat agreement from scientific handedness approval."""
    a,b=control.get('result',{}),observed.get('result',{})
    checks={'both_workers_completed':all(n.get('execution',{}).get('status')=='COMPLETED' and n['execution'].get('returncode')==0 for n in [control,observed]),
        'same_source':control.get('source_sha256')==observed.get('source_sha256')==previous.get('source_sha256'),
        'same_reader_and_charge':all(a.get(k)==b.get(k) for k in ['reader','charge_control']),
        'same_prepared_state':a.get('constructor',{}).get('promoted')==b.get('constructor',{}).get('promoted'),
        'same_constructor_status':a.get('constructor',{}).get('status')==b.get('constructor',{}).get('status')=='COMPLETED',
        'exact_endpoint_repeat':bool(a.get('constructor',{}).get('after')) and a['constructor']['after']==b.get('constructor',{}).get('after')}
    return {'status':'FRESH_REPEAT_MATCH' if all(checks.values()) else 'REVIEW','checks':checks,'checks_pass':all(checks.values()),
        'previous_endpoint_match':bool(a.get('constructor',{}).get('after')) and a['constructor']['after']==previous.get('result',{}).get('constructor',{}).get('after'),
        'random_state_control':'NOT_REQUESTED; DIFFERENCES MAY INCLUDE NATIVE NONDETERMINISM',
        'scientific_approval':'NOT_RUN','automatic_adoption':False}


def observe_native_constructor(parent,method,modules,spec,trace):
    """Process-local method observers; originals receive unchanged calls once."""
    from pathlib import Path
    from hashlib import sha256
    import functools,importlib,inspect,math
    scope=[('elbow.chemistry.ChiralClass','ChiralClass',name) for name in
        ['GenerateZMatrixClass','Chiralise','GetRestrainedParameters','TightenRestraints','Optimise','GetRSNotation']]
    scope.append(('elbow.cctbx_api.CCTBXMixins','CCTBXMixins','OptimiseCCTBX'))
    mapping=spec.get('coordinate_mapping') is True
    if mapping:
        scope.extend(('elbow.cctbx_api.CCTBXMixins','CCTBXMixins',name) for name in ['GetCoordinates','SetCoordinates','GetNewManager'])
    index_basis=spec.get('index_basis') is True
    integer_keys=spec.get('integer_keys') is True
    root=Path(spec['installation_root']).resolve(strict=True);proof={r['path']:r for r in spec['trace_sources']+spec.get('index_sources',[])}
    for row in spec['sources']:
        path=Path(row['installed']).resolve(strict=True)
        proof.setdefault(path.relative_to(root).as_posix(),{'sha256':row['sha256'],'size':path.stat().st_size})
    records=[];pins={};originals=[];stack=[];counter=0
    def fingerprint(function):
        module=inspect.getmodule(function);path=Path(module.__file__).resolve(strict=True);relative=path.relative_to(root).as_posix()
        row=proof.get(relative);found=importlib.util.find_spec(module.__name__)
        if (row is None or not inspect.isfunction(function)
                or found is None or found.origin is None or Path(found.origin).resolve(strict=True)!=path):raise ValueError('Unselected native trace method')
        data=path.read_bytes()
        if sha256(data).hexdigest()!=row['sha256'] or len(data)!=row['size']:raise ValueError('Native trace method source changed')
        pins[relative]=row
        return {'module':module.__name__,'path':relative,'sha256':row['sha256'],'definition_line':function.__code__.co_firstlineno}
    for module_name,class_name,name in scope:
        module=modules.get(module_name) or importlib.import_module(module_name);cls=getattr(module,class_name)
        if name not in vars(cls):raise ValueError('Unsupported native trace method scope')
        original=vars(cls)[name];record={'method':class_name+'.'+name,**fingerprint(original)}
        originals.append((cls,name,original));records.append(record)
    top=method.__func__;records.append({'method':'TopologyMixins.Chiralise',**fingerprint(top)})
    trace.update(policy_id='cif-native-chiral-boundary-observation-v1',hooks=[r['method'] for r in records],method_sources=records,
        before=native_inventory(parent),events=[],methods_restored=False,source_hashes_preserved=False,
        max_calls=256,random_state_control='NOT_REQUESTED',scientific_approval='NOT_RUN',automatic_adoption=False)
    if mapping:trace['mapping_policy_id']='cif-native-local-coordinate-mapping-v1'
    if index_basis:
        factory=importlib.import_module('elbow.cctbx_api.geometry_manager')
        trace.update(index_policy_id='cif-native-integer-restraint-keys-v2' if integer_keys else 'cif-native-named-restraint-index-basis-v1',index_sources=spec['index_sources'],
            index_method_sources=[{'method':'geometry_manager.run',**fingerprint(factory.run)}])
    def scalar(v):
        if type(v) in (str,bool,int,type(None)):return v
        if type(v) is float:return v if math.isfinite(v) else 'NONFINITE'
        if type(v) in (tuple,list) and len(v)<=32:return [scalar(a) for a in v]
        return 'NATIVE_TYPE:'+type(v).__module__+'.'+type(v).__name__
    def frame(obj):
        return [{'atom':a.name.strip(),'global_index':scalar(getattr(a,'index',None)),
            'same_parent_object':any(a is p for p in parent),'xyz':[float(a.xyz.x),float(a.xyz.y),float(a.xyz.z)]} for a in obj]
    def coordinates(value):
        try:
            if len(value)>64:return {'unsupported':'COORDINATE_CAP'}
            result=[[float(x) for x in row] for row in value]
            if any(len(row)!=3 or any(not math.isfinite(x) for x in row) for row in result):return {'unsupported':'NONFINITE_OR_SHAPE'}
            return result
        except (TypeError,ValueError,AttributeError):return {'unsupported':'COORDINATE_TYPE'}
    def local_state(obj):
        return {'original_order':[{'atom':a.name.strip(),'global_index':scalar(getattr(a,'index',None))} for a in getattr(obj,'original_order',[])],
            'input_volume':scalar(getattr(obj,'input_volume',None)),'equil':scalar(getattr(obj,'equil',None)),
            'native_marker':scalar(getattr(getattr(obj,'chiral_atom',None),'chiral',None))}
    def plain(value,depth=0):
        if type(value) in (str,bool,int,float,type(None)):return scalar(value)
        if depth<6 and isinstance(value,(list,tuple)) and len(value)<=64:return [plain(v,depth+1) for v in value]
        return {'unsupported_type':type(value).__module__+'.'+type(value).__name__}
    def restraint_basis(obj,value):
        rc=getattr(obj,'restraint_class',None)
        if not isinstance(rc,dict) or not isinstance(value,(list,tuple)) or len(value)!=6:return {'unsupported':'NATIVE_RESTRAINT_CONTAINER'}
        method=rc.GetRestraints
        if not inspect.ismethod(method) or method.__self__ is not rc:raise ValueError('Unsupported native restraint method')
        source={'method':'RestraintClass.GetRestraints',**fingerprint(method.__func__)}
        if len(rc)>256:return {'unsupported':'NATIVE_RESTRAINT_DICTIONARY_CAP','restraint_method':source}
        if integer_keys:
            methods=[]
            for name in ['get_key','GetCoordinates']:
                bound=getattr(rc,name)
                if not inspect.ismethod(bound) or bound.__self__ is not rc:raise ValueError('Unsupported native integer-key method')
                methods.append({'method':'RestraintClass.'+name,**fingerprint(bound.__func__)})
            link=getattr(rc,'link',None)
            if not isinstance(link,dict) or len(link)>64 or len(obj)>64:
                return {'unsupported':'NATIVE_INTEGER_KEY_SCOPE','restraint_method':source}
            entries=[{'native_key':key,'stored_xyz':plain(stored)} for key,stored in dict.items(rc) if type(key) is int]
            atoms=[{'atom':a.name.strip(),'global_index':scalar(a.index),
                'unique_index':scalar(getattr(a,'unique_index',None)),
                'key_attribute':'unique_index' if hasattr(a,'unique_index') else 'index',
                'native_key':scalar(getattr(a,'unique_index',a.index)),
                'same_parent_object':any(a is p for p in parent)} for a in obj]
            return {'restraint_method':source,'integer_key_methods':methods,'local_atom_keys':atoms,
                'integer_coordinate_entries':entries,'native_link':[{'native_key':scalar(k),'index':scalar(v)} for k,v in link.items()],
                'returned_coordinates':coordinates(value[0]),'returned_chirality_parameters':plain(value[5])}
        atoms=[]
        for atom,stored in rc.items():
            if not hasattr(atom,'name') or not hasattr(atom,'index'):continue
            atoms.append({'atom':atom.name.strip(),'global_index':scalar(atom.index),
                'same_parent_object':any(atom is p for p in parent),'stored_xyz':plain(stored)})
        return {'restraint_method':source,'native_atom_keys':atoms,'returned_coordinates':coordinates(value[0]),
            'returned_chirality_parameters':plain(value[5])}
    def invoke(label,original,obj,args,kwargs):
        nonlocal counter
        if counter>=256:
            trace['call_cap_reached']=True;raise ValueError('Native constructor trace call cap reached')
        call=counter;counter+=1;pid=stack[-1] if stack else None
        bound=inspect.signature(original).bind(obj,*args,**kwargs);bound.apply_defaults()
        start={'call_id':call,'parent_call_id':pid,'method':label,'phase':'enter','snapshot':native_inventory(parent),
            'centre':getattr(getattr(obj,'chiral_atom',None),'name','').strip(),'local_atoms':frame(obj),
            'resolved_arguments':{k:scalar(v) for k,v in bound.arguments.items() if k!='self'},
            'arguments_forwarded_unchanged':True}
        if mapping:
            start['mapping']={'local_state':local_state(obj)}
            if label=='CCTBXMixins.SetCoordinates':start['mapping']['coordinates_input']=coordinates(bound.arguments['coordinates'])
        trace['events'].append(start);stack.append(call);status='EXCEPTION';error=None;summary={};mapping_result={}
        try:
            value=original(obj,*args,**kwargs);status='COMPLETED'
            summary={'return_type':type(value).__name__}
            if type(value) in (str,bool,int,float,type(None)):summary['scalar_return']=scalar(value)
            if label=='CCTBXMixins.OptimiseCCTBX' and isinstance(value,tuple) and len(value)==2:
                minimizer=getattr(value[1],'minimizer',None);summary['lbfgs_minimizer_error']=scalar(getattr(minimizer,'error',None))
                summary['stopping_qualification']='NOT_INDEPENDENTLY_ASSESSED'
            if mapping:
                if index_basis and label=='ChiralClass.GetRestrainedParameters':mapping_result['index_basis']=restraint_basis(obj,value)
                if label=='CCTBXMixins.GetCoordinates':mapping_result['coordinates_returned']=coordinates(value)
                if label=='CCTBXMixins.OptimiseCCTBX':mapping_result['coordinates_returned']=coordinates(value[0] if isinstance(value,tuple) and len(value)==2 and bound.arguments.get('return_lbfgs_object') else value)
                if label=='CCTBXMixins.GetNewManager':
                    try:
                        proxies=value.chirality_proxies
                        if len(proxies)>64:raise ValueError('Native chirality proxy cap')
                        mapping_result['chirality_proxies']=[{'i_seqs':[int(i) for i in p.i_seqs],
                            'volume_ideal':scalar(p.volume_ideal),'weight':scalar(p.weight),'both_signs':scalar(p.both_signs)} for p in proxies]
                    except (AttributeError,TypeError,ValueError) as exc:mapping_result['proxy_observation_error']=type(exc).__name__+': '+str(exc)
            return value
        except BaseException as exc:
            error={'exception_type':type(exc).__name__,'message':str(exc)};raise
        finally:
            stack.pop();end={'call_id':call,'parent_call_id':pid,'method':label,'phase':'exit',
                'snapshot':native_inventory(parent),'local_atoms':frame(obj),'centre':start['centre'],'status':status,'exception':error,'return_summary':summary}
            if mapping:end['mapping']={'local_state':local_state(obj),**mapping_result}
            trace['events'].append(end)
    def wrapper(label,original):
        @functools.wraps(original)
        def observed(obj,*args,**kwargs):return invoke(label,original,obj,args,kwargs)
        return observed
    try:
        for (cls,name,original),record in zip(originals,records):setattr(cls,name,wrapper(record['method'],original))
        return invoke('TopologyMixins.Chiralise',top,parent,(),{})
    finally:
        for cls,name,original in reversed(originals):setattr(cls,name,original)
        trace['methods_restored']=all(vars(cls)[name] is original for cls,name,original in originals)
        trace['source_hashes_preserved']=all(sha256((root/name).read_bytes()).hexdigest()==row['sha256'] for name,row in pins.items())
        trace['after']=native_inventory(parent)


def constructor_trace_worker(base):
    token='        method()\n'
    if base.count(token)!=1:raise ValueError('Constructor worker observer insertion differs')
    return getsource(observe_native_constructor)+'\n'+base.replace(token,
        "        result['constructor_trace']={}\n        observe_native_constructor(molecule,method,modules,spec,result['constructor_trace'])\n")
