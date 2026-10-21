"""Audit temporary native chiral construction after source-exact reading.

This is a handoff diagnostic, not a complete builder or an absolute CIP test.
The native constructor can optimize local chiral templates internally.
"""
from copy import deepcopy
from hashlib import sha256
from inspect import getsource
import ast,json,math,os
from pathlib import Path
import subprocess,time

from .cif_declared_charge_control import native_inventory,control_declared_charges
from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import _inside,MAX_SOURCE_BYTES
from .cif_generation import _terminate_owned_group
from .cif_source_reader import source_reader_checks
from .cif_stereochemistry_audit import _values,_graph,_coordinates,_volume,reader_stereo_inventory,VOLUME_EPSILON

POLICY_ID='cif-source-native-constructor-handoff-v1'
BACKEND_POLICY_ID='cif-native-chiral-cctbx-preparation-v1'
SOURCE_PATHS=('elbow/chemistry/any_chemical_format_reader.py','elbow/formats/monomer_library_cif_parser.py',
    'elbow/utilities/Utilities.py','elbow/chemistry/MoleculeClass.py','elbow/chemistry/SimpleMoleculeClass.py',
    'elbow/chemistry/TopologyMixins.py','elbow/chemistry/ChiralClass.py')
PRIOR_PATHS=tuple(p for p in SOURCE_PATHS if not p.endswith('/SimpleMoleculeClass.py'))


def native_cctbx_reference(text):
    """Recognize the native reader's explicit same-object backend handoff."""
    import ast
    tree=ast.parse(text)
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_elbow_molecule_from_chemical_components']
    if len(functions)!=1:raise ValueError('Missing native CCTBX preparation reference')
    def call(statement,name,args):
        return (isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call)
            and isinstance(statement.value.func,ast.Attribute) and isinstance(statement.value.func.value,ast.Name)
            and statement.value.func.value.id=='molecule' and statement.value.func.attr==name
            and not statement.value.keywords and len(statement.value.args)==len(args)
            and all(isinstance(a,ast.Constant) and a.value is b for a,b in zip(statement.value.args,args)))
    rows=[n for n in functions[0].body if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='chirals'
        and len(n.body)==2 and not n.orelse and call(n.body[0],'SetCCTBX',[True]) and call(n.body[1],'Chiralise',[])]
    if len(rows)!=1:raise ValueError('Unsupported native CCTBX preparation reference')
    return {'function':functions[0].name,'setter_line':rows[0].body[0].lineno,'constructor_line':rows[0].body[1].lineno,'value':True}


def prepare_native_cctbx(molecule,spec,result):
    """Use selected native methods, capturing their source and exact state delta."""
    from pathlib import Path
    from hashlib import sha256
    import ast,importlib.util,inspect
    root=Path(spec['installation_root']).resolve(strict=True);library=Path(spec['library']).resolve(strict=True)
    reference=native_cctbx_reference(Path(spec['backend_reference']).read_text())
    control={'policy_id':BACKEND_POLICY_ID,'status':'STARTED','reference':reference,'methods':{},'sources':[],
        'before':native_inventory(molecule),'before_format':molecule.GetOriginalFormat()}
    result['backend_control']=control
    methods={name:getattr(molecule,name) for name in ['SetCCTBX','GetCCTBX']}
    for name,method in methods.items():
        if not inspect.ismethod(method) or method.__self__ is not molecule:raise ValueError('Unsupported bound native backend API')
        module=inspect.getmodule(method);path=Path(module.__file__).absolute();resolved=path.resolve(strict=True)
        if (path!=resolved or not path.is_relative_to(library) or path.suffix!='.py'
                or any(p.is_symlink() for p in [path,*path.parents])):raise ValueError('Unselected native backend method source')
        found=importlib.util.find_spec(module.__name__)
        if found is None or found.origin is None or Path(found.origin).resolve(strict=True)!=path:raise ValueError('Unselected native backend import')
        data=path.read_bytes()
        if len(data)>1024*1024:raise ValueError('Oversized native backend source')
        ast.parse(data);relative=path.relative_to(root).as_posix();snapshot='backend_sources/'+relative+'.txt'
        row={'anchor':'phenix_installation','path':relative,'sha256':sha256(data).hexdigest(),'size':len(data),
            'snapshot':{'anchor':'constructor_directory','path':snapshot}}
        if row not in control['sources']:
            target=Path(snapshot);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);control['sources'].append(row)
        control['methods'][name]={'module':module.__name__,'path':relative,'sha256':row['sha256'],'selected_source':True}
    inspect.signature(methods['SetCCTBX']).bind(True);inspect.signature(methods['GetCCTBX']).bind()
    control['previous_value']=methods['GetCCTBX']()
    if type(control['previous_value']) not in (bool,int) or control['previous_value'] not in (False,True):
        raise ValueError('Unsupported native backend flag type')
    methods['SetCCTBX'](True)
    control.update(selected_value=methods['GetCCTBX'](),after=native_inventory(molecule),after_format=molecule.GetOriginalFormat())
    if (type(control['selected_value']) not in (bool,int) or control['selected_value']!=True
            or control['after']!=control['before'] or control['after_format']!=control['before_format']):
        raise ValueError('Native backend preparation changed chemical state or failed selection')
    control['status']='NATIVE_CCTBX_PREPARATION_PASS'


def _snapshot(row):
    """Reject incomplete, duplicate and nonfinite native inventory records."""
    try:
        atoms={a['atom']:a for a in row['atoms']};bonds={tuple(b['atoms']):b['native_order'] for b in row['bonds']}
        valid=(len(atoms)==len(row['atoms']) and len(bonds)==len(row['bonds'])
            and type(row['molecule_charge']) in (int,float) and math.isfinite(row['molecule_charge'])
            and all(len(a['xyz'])==3 and all(type(x) in (int,float) and math.isfinite(x) for x in a['xyz'])
                and type(a['native_atom_charge']) in (int,float) and math.isfinite(a['native_atom_charge']) for a in atoms.values())
            and all(len(ids)==2 and ids==tuple(sorted(ids)) and len(set(ids))==2 and set(ids)<=set(atoms)
                and type(order) in (int,float) and math.isfinite(order) for ids,order in bonds.items()))
        return atoms,bonds,valid
    except (KeyError,TypeError,ValueError):return {},{},False


def qualify_constructor_evidence(source,code,result,dialect,*,native_cctbx=False):
    """Recompute chemical/state/stereo gates from complete saved snapshots."""
    source=Path(source);before=source.read_bytes();values=_values(source,code)
    elements,bonds,charges,neighbors=_graph(values);_,source_xyz=_coordinates(values,source=True)
    stereo=reader_stereo_inventory(source,code);reader=result.get('reader',{});control=result.get('charge_control',{})
    constructor=result.get('constructor',{});charged=control.get('after',{});after=constructor.get('after',{})
    try:raw_checks=source_reader_checks(source,code,reader,dialect)
    except (KeyError,TypeError,ValueError):raw_checks={}
    raw,_,raw_valid=_snapshot(reader);prepared,_,prepared_valid=_snapshot(charged);current,current_bonds,valid=_snapshot(after)
    declared_orders={'SINGLE':1,'DOUBLE':2,'TRIPLE':3,'AROMATIC':1.5,'DELOCALIZED':1.5}
    expected_bonds={p:declared_orders.get(order) for p,order in bonds.items()}
    def state_matches(row):
        a,b,ok=_snapshot(row)
        return (ok and set(a)==set(elements) and b==expected_bonds and row['molecule_charge']==sum(charges.values())
            and all(a[n]['element'].upper()==e and a[n]['native_atom_charge']==charges[n] for n,e in elements.items()))
    def except_charge(row):
        return {'atoms':[{k:v for k,v in a.items() if k!='native_atom_charge'} for a in row.get('atoms',[])],
            'bonds':row.get('bonds')}
    raw_snapshot={k:reader.get(k) for k in ['atoms','bonds','molecule_charge']}
    complete_charges=all(type(q) in (int,float) and math.isfinite(q) and float(q).is_integer() and abs(q)<=4 for q in charges.values())
    if complete_charges:
        already=raw_valid and state_matches(raw_snapshot)
        omitted=raw_valid and dialect=='MONOMER_LIBRARY_CIF' and all(a['native_atom_charge']==0 for a in raw.values()) and reader['molecule_charge']==0
    else:already=omitted=False
    expected_action='ALREADY_PRESERVED' if already else 'POPULATED_FROM_EXPLICIT_SOURCE' if omitted else None
    source_centres={r['center'] for r in stereo['source_signed_chirality']}
    known_centres={n for n,v in stereo['atoms'].items() if v['declared_stereo'] in {'R','S'}}
    accounted=source_centres|known_centres
    signs={'positiv':'positive','positive':'positive','negativ':'negative','negative':'negative','both':'both'}
    checks={'reader_route_and_graph':bool(raw_checks) and all(v for k,v in raw_checks.items() if k!='atom_charge_values'),
        'charge_control_before_matches_reader':control.get('before')==raw_snapshot,
        'complete_integer_source_charges':complete_charges,
        'source_charge_transfer':control.get('status')=='DECLARED_CHARGE_CONTROL_PASS' and expected_action is not None
            and control.get('action')==expected_action and state_matches(charged) and except_charge(control.get('before',{}))==except_charge(charged),
        'native_promotion_preserved':prepared_valid and constructor.get('promoted')==charged,
        'native_reader_route_preserved':constructor.get('promoted_format')==constructor.get('after_format')==reader.get('format')
            and reader.get('format') in {'CIF','CHEMICAL COMPONENTS'},
        'constructor_completed':constructor.get('status')=='COMPLETED',
        'constructor_graph_and_charges_preserved':complete_charges and state_matches(after),
        'declared_atom_markers_preserved':valid and prepared_valid and all(
            current.get(n,{}).get('native_chiral_marker')==prepared.get(n,{}).get('native_chiral_marker')==v['declared_stereo']
            for n,v in stereo['atoms'].items() if v['declared_stereo'] in {'R','S'}),
        'declared_nonchiral_markers_preserved':raw_valid and valid and prepared_valid and all(
            all(a.get(n,{}).get('native_chiral_marker') in (None,False,0,'') for a in [raw,prepared,current])
            for n,v in stereo['atoms'].items() if v['declared_stereo']=='N'),
        'declared_signed_markers_read':raw_valid and all(signs.get(str(raw.get(r['center'],{}).get('native_volume_sign')).lower())
            ==signs.get(r['volume_sign'].lower()) and r['volume_sign'].lower() in signs for r in stereo['source_signed_chirality']),
        'signed_marker_metadata_preserved':valid and prepared_valid and all(current.get(n,{}).get('native_volume_sign')==a.get('native_volume_sign') for n,a in prepared.items()),
        'no_unaccounted_new_centres':valid and prepared_valid and not any(a.get('native_chiral_marker') and not prepared.get(n,{}).get('native_chiral_marker')
            and n not in accounted for n,a in current.items())}
    terms=[];seen=set();xyz={n:a['xyz'] for n,a in current.items()} if valid else {}
    declared=stereo['source_signed_chirality']+[{'center':n,'ordered_neighbors':sorted(neighbors[n])[:3],'volume_sign':None} for n in sorted(known_centres-source_centres)]
    for row in declared:
        center=row['center'];ordered=row['ordered_neighbors'];key=(center,tuple(ordered));seen.add(key)
        tetra=(center in neighbors and len(neighbors[center])==4 and len(ordered)==3 and len(set(ordered))==3 and set(ordered)<=neighbors[center])
        a,b=(_volume(p,center,ordered) for p in [source_xyz,xyz]) if tetra else (None,None)
        mode=signs.get(str(row['volume_sign']).lower());sign={'positive':1,'negative':-1}.get(mode)
        fixed_hand=mode!='both' or center in known_centres
        hand=a is not None and b is not None and min(abs(a),abs(b))>VOLUME_EPSILON and a*b>0
        target=True if mode=='both' else (sign is not None and a is not None and b is not None and min(sign*a,sign*b)>VOLUME_EPSILON) if row['volume_sign'] is not None else None
        terms.append({**row,'valid_declared_tetrahedron':tetra,'source_volume':a,'constructor_volume':b,'requires_fixed_hand':fixed_hand,
            'source_hand_preserved':hand,'declared_target_matches_both':target})
    checks['source_handedness_assessed']=any(t['requires_fixed_hand'] for t in terms) and len(seen)==len(terms)
    checks['source_handedness_preserved']=bool(terms) and all(t['valid_declared_tetrahedron'] and (not t['requires_fixed_hand'] or
        t['source_hand_preserved'] and (t['volume_sign'] is None or t['declared_target_matches_both'] is True)) for t in terms)
    if native_cctbx:
        backend=result.get('backend_control',{});reference=backend.get('reference',{})
        checks['native_backend_selected']=(backend.get('policy_id')==BACKEND_POLICY_ID
            and backend.get('status')=='NATIVE_CCTBX_PREPARATION_PASS'
            and type(backend.get('selected_value')) in (bool,int) and backend['selected_value']==True)
        checks['native_backend_reference']=(reference.get('function')=='get_elbow_molecule_from_chemical_components'
            and reference.get('value') is True and type(reference.get('setter_line')) is int
            and type(reference.get('constructor_line')) is int and 0<reference['setter_line']<reference['constructor_line'])
        checks['native_backend_chemistry_preserved']=(backend.get('before')==backend.get('after')==constructor.get('promoted')==charged
            and backend.get('before_format')==backend.get('after_format')==reader.get('format'))
        checks['native_backend_methods_selected']=(set(backend.get('methods',{}))=={'SetCCTBX','GetCCTBX'}
            and all(v.get('selected_source') is True for v in backend['methods'].values()))
    shifted=[math.dist(source_xyz[n],a['xyz']) for n,a in current.items() if valid and n in source_xyz]
    if source.read_bytes()!=before:raise ValueError('Constructor qualification changed its input')
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'SOURCE_CONSTRUCTOR_HANDOFF_PASS' if all(checks.values()) else 'REVIEW',
        'checks':checks,'checks_pass':all(checks.values()),'raw_reader_checks':raw_checks,'constructor_status':constructor.get('status','NOT_RUN'),
        'source_relative_handedness':terms,'maximum_coordinate_shift_angstrom':max(shifted,default=0.),
        'source_sha256':sha256(before).hexdigest(),'absolute_cip_assignment':'NOT_RUN','whole_builder_replay':'NOT_RUN',
        'whole_molecule_optimization':'NOT_REQUESTED','constructor_local_optimization':'NATIVE_INTERNALS_NOT_INSTRUMENTED',
        'dictionary_generation':'NOT_RUN','model_editing':'NOT_RUN','automatic_adoption':False,
        **({'backend_policy_id':BACKEND_POLICY_ID} if native_cctbx else {})}


WORKER=(getsource(native_inventory)+'\n'+getsource(control_declared_charges)+'\n'+getsource(native_cctbx_reference)+'\n'
    +getsource(prepare_native_cctbx)+f'\nBACKEND_POLICY_ID={BACKEND_POLICY_ID!r}\n')+r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,inspect,json,sys,traceback
spec=json.loads(Path(sys.argv[1]).read_text());directory=Path.cwd().resolve()
sys.argv=['constructor_worker.py']
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory];sys.path.insert(0,spec['library'])
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()
modules={}
for row in spec['sources']:
    path=Path(row['installed']).resolve(strict=True)
    if digest(path)!=row['sha256']:raise ValueError('Installed constructor source changed')
    found=importlib.util.find_spec(row['module'])
    if found is None or found.origin is None or Path(found.origin).resolve(strict=True)!=path:raise ValueError('Unselected constructor source')
    module=importlib.import_module(row['module'])
    if Path(module.__file__).resolve(strict=True)!=path:raise ValueError('Unselected constructor import')
    modules[row['module']]=module
api=modules['elbow.chemistry.any_chemical_format_reader']
if not {'data','simple','return_all_restraints','do_not_check_for_smiles'}<=set(inspect.signature(api.any_chemical_format_reader).parameters):raise ValueError('Unsupported reader signature')
if 'simple' not in inspect.signature(api.return_molecule_class).parameters:raise ValueError('Unsupported native promotion API')
source=Path('source.cif');original=digest(source)
result={'reader':{'execution':'NOT_RUN'},'charge_control':{'status':'NOT_RUN'},'constructor':{'status':'NOT_RUN'},
    'process_argv':list(sys.argv),'dictionary_generation':'NOT_RUN','whole_molecule_optimization':'NOT_REQUESTED',
    'constructor_local_optimization':'NATIVE_INTERNALS_NOT_INSTRUMENTED','captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN'}
try:
    molecule=api.any_chemical_format_reader(str(source.resolve()),simple=True,return_all_restraints=True,do_not_check_for_smiles=True)
    if type(molecule) is list:
        if len(molecule)!=1:raise ValueError('Require one source component')
        molecule=molecule[0]
    result['reader']={**native_inventory(molecule),'execution':'COMPLETED','format':molecule.GetOriginalFormat(),
        'dispatch_is_chemical_components':bool(api.is_chemical_components_file(source.read_text()))}
    result['charge_control']=control_declared_charges(molecule,spec['declared_charge_control'])
    if result['charge_control']['status']=='DECLARED_CHARGE_CONTROL_PASS':
        molecule=api.return_molecule_class(molecule,simple=False)
        result['constructor'].update(promoted=native_inventory(molecule),promoted_format=molecule.GetOriginalFormat())
        method=molecule.Chiralise
        if Path(inspect.getmodule(method).__file__).resolve(strict=True)!=Path(spec['constructor_module']).resolve(strict=True):raise ValueError('Unselected native constructor method')
        if 'chiral_treatment' not in inspect.signature(method).parameters:raise ValueError('Unsupported native constructor signature')
        if spec.get('native_cctbx') is True:prepare_native_cctbx(molecule,spec,result)
        result['constructor'].update(status='STARTED',native_class=type(molecule).__module__+'.'+type(molecule).__name__)
        method()
        result['constructor'].update(status='COMPLETED',after=native_inventory(molecule),after_format=molecule.GetOriginalFormat())
except Exception as exc:
    result['constructor'].update(status='EXCEPTION',exception_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    if result['reader']['execution']=='COMPLETED':
        try:result['constructor'].update(after=native_inventory(molecule),after_format=molecule.GetOriginalFormat())
        except Exception:pass
if digest(source)!=original:raise ValueError('Constructor changed frozen source')
for row in spec['sources']:
    if digest(row['installed'])!=row['sha256']:raise ValueError('Installed constructor source changed')
for row in result.get('backend_control',{}).get('sources',[]):
    if digest(Path(spec['installation_root'])/row['path'])!=row['sha256']:raise ValueError('Installed native backend source changed')
Path('constructor_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def verify_constructor_capture(installation_root,report,output):
    root=Path(installation_root).resolve(strict=True);output=Path(output).resolve(strict=True)
    rows=report['sources']
    if len(rows)!=len(SOURCE_PATHS) or {r['snapshot']['path'] for r in rows}!={p+'.txt' for p in SOURCE_PATHS}:raise ValueError('Constructor source scope differs')
    for row in rows:
        if row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='constructor_directory':raise ValueError('Invalid constructor source anchor')
        for path in [_inside(root,row['path']),_inside(output,row['snapshot']['path'])]:
            data=path.read_bytes()
            if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:raise ValueError('Installed/captured constructor source changed')
    for row in report.get('result',{}).get('backend_control',{}).get('sources',[]):
        if row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='constructor_directory':raise ValueError('Invalid native backend source anchor')
        for path in [_inside(root,row['path']),_inside(output,row['snapshot']['path'])]:
            data=path.read_bytes()
            if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:raise ValueError('Installed/captured native backend source changed')
    return True


def audit_source_constructor(installation_root,python_executable,api_sources,source,code,output,*,environment,expected_dialect,prior_sources,timeout_seconds=60,native_cctbx=False):
    """Run one exact-source reader/charge/promotion/Chiralise handoff."""
    if expected_dialect not in {'MONOMER_LIBRARY_CIF','CHEMICAL_COMPONENTS_CIF'}:raise ValueError('Unsupported explicit reader dialect')
    if type(native_cctbx) is not bool:raise ValueError('Require explicit native backend selection')
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=60:raise ValueError('Constructor timeout must be in (0,60]')
    root=Path(installation_root).resolve(strict=True);python_executable=Path(python_executable).resolve(strict=True)
    source=Path(source).resolve(strict=True);output=Path(output).absolute()
    if (not python_executable.is_relative_to(root) or output.resolve().is_relative_to(root) or output.resolve().is_relative_to(source.parent)
            or output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents)):
        raise ValueError('Require selected Phenix Python and fresh separate constructor output')
    original=source.read_bytes();dispatcher=python_executable.read_bytes();site=_library_anchor(api_sources)
    proof={r['path']:r for r in prior_sources}
    if (len(proof)!=len(prior_sources) or set(proof)!={(site/p).as_posix() for p in PRIOR_PATHS}
            or any(r.get('anchor')!='phenix_installation' for r in proof.values())):raise ValueError('Require exact prior reader/charge/chirality source proof')
    values=_values(source,code);elements,bonds,charges,_=_graph(values);_,coordinates=_coordinates(values,source=True)
    if (set(coordinates)!=set(elements) or any(q is None or not q.is_integer() or abs(q)>4 for q in charges.values())):
        raise ValueError('Require complete finite source coordinates and explicit representable charges')
    normalized={'SINGLE':1,'DOUBLE':2,'TRIPLE':3,'AROMATIC':1.5,'DELOCALIZED':1.5}
    if set(bonds.values())-set(normalized):raise ValueError('Unsupported declared source order')
    rows=[];payloads={}
    for name in SOURCE_PATHS:
        relative=(site/name).as_posix();data=_inside(root,relative).read_bytes()
        if len(data)>MAX_SOURCE_BYTES:raise ValueError('Oversized constructor source')
        ast.parse(data,filename=name)
        if relative in proof and (sha256(data).hexdigest()!=proof[relative]['sha256'] or len(data)!=proof[relative]['size']):raise ValueError('Prior constructor API source changed')
        payloads[name]=data;rows.append({'anchor':'phenix_installation','path':relative,'sha256':sha256(data).hexdigest(),'size':len(data),
            'snapshot':{'anchor':'constructor_directory','path':name+'.txt'}})
    if native_cctbx:native_cctbx_reference(payloads['elbow/utilities/Utilities.py'])
    output.mkdir(parents=True,exist_ok=False)
    for name,data in payloads.items():
        target=output/(name+'.txt');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (output/'source.cif').write_bytes(original);(output/'constructor_worker.py').write_text(WORKER)
    spec={'component':code,'library':str(root/site),'installation_root':str(root),'native_cctbx':native_cctbx,
        'backend_reference':str(root/site/'elbow/utilities/Utilities.py'),'constructor_module':str(root/site/'elbow/chemistry/TopologyMixins.py'),
        'sources':[{'installed':str(root/r['path']),'sha256':r['sha256'],'module':name[:-3].replace('/','.')} for name,r in zip(SOURCE_PATHS,rows)],
        'declared_charge_control':{'component':code,'dialect':expected_dialect,'elements':elements,'charges':{n:int(q) for n,q in charges.items()},
            'coordinates':coordinates,'bonds':[{'atoms':list(p),'order':normalized[o]} for p,o in bonds.items()]}}
    (output/'constructor_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'FAILED','component':code,'sources':rows,'expected_dialect':expected_dialect,
        'source_sha256':sha256(original).hexdigest(),'dispatcher_sha256':sha256(dispatcher).hexdigest(),'execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds},
        'dictionary_generation':'NOT_RUN','model_editing':'NOT_RUN','whole_builder_replay':'NOT_RUN','whole_molecule_optimization':'NOT_REQUESTED',
        'constructor_local_optimization':'NATIVE_INTERNALS_NOT_INSTRUMENTED','absolute_cip_assignment':'NOT_RUN','installed_phenix_edits':'NOT_RUN',
        'captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN','automatic_adoption':False}
    started=time.monotonic()
    try:
        verify_constructor_capture(root,report,output)
        with (output/'constructor_worker.log').open('xb') as log:
            process=subprocess.Popen([str(python_executable),'-B','constructor_worker.py','constructor_spec.json'],cwd=output,
                env={**environment,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:rc=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _terminate_owned_group(process);report['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_terminate_owned_group(process);raise
            else:
                report['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
                if rc==0:
                    result=json.loads((output/'constructor_result.json').read_text());report['result']=result
                    report['qualification']=qualify_constructor_evidence(source,code,result,expected_dialect,native_cctbx=native_cctbx);report['status']='REVIEW'
        verify_constructor_capture(root,report,output)
    except (OSError,ValueError,KeyError,TypeError) as exc:report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
    report['source_preserved']=source.read_bytes()==original and (output/'source.cif').read_bytes()==original and python_executable.read_bytes()==dispatcher
    if not report['source_preserved']:report.update(status='FAILED',error='Constructor source or dispatcher changed')
    report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    report['outputs']=[{'anchor':'constructor_directory','path':p.relative_to(output).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
        for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in output.rglob('*')):report.update(status='FAILED',error='Unexpected constructor output symlink')
    (output/'constructor_receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report
