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
SOURCE_PATHS=('elbow/chemistry/any_chemical_format_reader.py','elbow/formats/monomer_library_cif_parser.py',
    'elbow/utilities/Utilities.py','elbow/chemistry/MoleculeClass.py','elbow/chemistry/SimpleMoleculeClass.py',
    'elbow/chemistry/TopologyMixins.py','elbow/chemistry/ChiralClass.py')
PRIOR_PATHS=tuple(p for p in SOURCE_PATHS if not p.endswith('/SimpleMoleculeClass.py'))


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


def qualify_constructor_evidence(source,code,result,dialect):
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
    shifted=[math.dist(source_xyz[n],a['xyz']) for n,a in current.items() if valid and n in source_xyz]
    if source.read_bytes()!=before:raise ValueError('Constructor qualification changed its input')
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'SOURCE_CONSTRUCTOR_HANDOFF_PASS' if all(checks.values()) else 'REVIEW',
        'checks':checks,'checks_pass':all(checks.values()),'raw_reader_checks':raw_checks,'constructor_status':constructor.get('status','NOT_RUN'),
        'source_relative_handedness':terms,'maximum_coordinate_shift_angstrom':max(shifted,default=0.),
        'source_sha256':sha256(before).hexdigest(),'absolute_cip_assignment':'NOT_RUN','whole_builder_replay':'NOT_RUN',
        'whole_molecule_optimization':'NOT_REQUESTED','constructor_local_optimization':'NATIVE_INTERNALS_NOT_INSTRUMENTED',
        'dictionary_generation':'NOT_RUN','model_editing':'NOT_RUN','automatic_adoption':False}


WORKER=getsource(native_inventory)+'\n'+getsource(control_declared_charges)+'\n'+r'''from pathlib import Path
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
        result['constructor'].update(status='STARTED',native_class=type(molecule).__module__+'.'+type(molecule).__name__)
        method()
        result['constructor'].update(status='COMPLETED',after=native_inventory(molecule),after_format=molecule.GetOriginalFormat())
except Exception as exc:
    result['constructor'].update(status='EXCEPTION',exception_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    if result['reader']['execution']=='COMPLETED':
        try:result['constructor']['after']=native_inventory(molecule)
        except Exception:pass
if digest(source)!=original:raise ValueError('Constructor changed frozen source')
for row in spec['sources']:
    if digest(row['installed'])!=row['sha256']:raise ValueError('Installed constructor source changed')
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
    return True


def audit_source_constructor(installation_root,python_executable,api_sources,source,code,output,*,environment,expected_dialect,prior_sources,timeout_seconds=60):
    """Run one exact-source reader/charge/promotion/Chiralise handoff."""
    if expected_dialect not in {'MONOMER_LIBRARY_CIF','CHEMICAL_COMPONENTS_CIF'}:raise ValueError('Unsupported explicit reader dialect')
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
    output.mkdir(parents=True,exist_ok=False)
    for name,data in payloads.items():
        target=output/(name+'.txt');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (output/'source.cif').write_bytes(original);(output/'constructor_worker.py').write_text(WORKER)
    spec={'component':code,'library':str(root/site),'constructor_module':str(root/site/'elbow/chemistry/TopologyMixins.py'),
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
                    report['qualification']=qualify_constructor_evidence(source,code,result,expected_dialect);report['status']='REVIEW'
        verify_constructor_capture(root,report,output)
    except (OSError,ValueError,KeyError,TypeError) as exc:report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
    report['source_preserved']=source.read_bytes()==original and (output/'source.cif').read_bytes()==original and python_executable.read_bytes()==dispatcher
    if not report['source_preserved']:report.update(status='FAILED',error='Constructor source or dispatcher changed')
    report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    report['outputs']=[{'anchor':'constructor_directory','path':p.relative_to(output).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
        for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink()]
    if any(p.is_symlink() for p in output.rglob('*')):report.update(status='FAILED',error='Unexpected constructor output symlink')
    (output/'constructor_receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report
