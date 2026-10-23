"""Observe ordinary ReadySet consumption of separately qualified cached inputs.

The optional transport executes the dispatcher's exact literal Python entrypoint
with ordinary CLI arguments. A profile observer records calls without replacing
native functions or changing arguments. This is an isolated diagnostic, not an
ordinary full-run or exhaustive native-optimization proof.
"""
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

from .cif_generation import _terminate_owned_group
from .cif_postmr_cache import verify_current_consumer
from .cif_readyset_source_audit import capture_readyset_sources, verify_readyset_sources
from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import _inside, MAX_SOURCE_BYTES

POLICY_ID = 'cif-ordinary-readyset-cached-input-consumption-v1'
EXPECTED_ACTIONS = {'hydrogens':False,'ligands':True,'optimise_ligand_geometry':False,
                    'optimise_final_geometry_of_hydrogens':False}
OBSERVED_MODULES = ('elbow/command_line/ready_set.py','elbow/command_line/builder.py',
                    'elbow/scripts/elbow_on_pdb_file.py')


def _capture_consumption_sources(root,site,dispatcher,output):
    """Freeze observer targets even when the bounded import scan stops earlier.

    Explicit observer roots do not extend or relabel transitive import coverage.
    Every additional root retains the same containment, size and hash checks.
    """
    report=capture_readyset_sources(root,site,dispatcher,output)
    seen={r['path'] for r in report['sources']};added=[]
    total=sum(r['size'] for r in report['sources'])
    for module in OBSERVED_MODULES:
        relative=(site/module).as_posix()
        if relative in seen:continue
        path=_inside(root,relative);data=path.read_bytes()
        if (len(report['sources'])>=report['source_file_budget'] or len(data)>MAX_SOURCE_BYTES
                or total+len(data)>8*MAX_SOURCE_BYTES):raise ValueError('Observed ReadySet source budget exceeded')
        target=output/'sources'/(module+'.txt');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
        report['sources'].append({'anchor':'phenix_installation','path':relative,'size':len(data),
            'sha256':sha256(data).hexdigest(),'snapshot':{'anchor':'readyset_audit_directory','path':target.relative_to(output).as_posix()}})
        seen.add(relative);added.append(relative);total+=len(data)
    report['observed_module_roots']=[(site/module).as_posix() for module in OBSERVED_MODULES]
    report['explicit_observer_sources']=added
    report['observer_coverage']='EXACT_NAMED_OBSERVER_ROOTS; TRANSITIVE_IMPORT_COVERAGE_UNCHANGED'
    verify_readyset_sources(root,report,output)
    return report

WORKER = r'''from pathlib import Path
from hashlib import sha256
import json,runpy,sys,traceback
sys.dont_write_bytecode=True
spec=json.loads(Path(sys.argv[1]).read_text());root=Path(spec['installation']).resolve(strict=True)
entry=root/spec['entrypoint'];directory=Path.cwd().resolve()
def verify():
    for row in spec['sources']:
        path=(root/row['path']).resolve(strict=True)
        if not path.is_relative_to(root) or sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('ReadySet source changed')
verify()
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory]
sys.path.insert(0,str(root/spec['library']))
trace={'schema_version':1,'events':[],'event_budget':128,'truncated':False,
       'builder_calls':0,'template_calls':0,'subprocess_calls':0,'effective_actions':None,
       'argument_overrides':'NONE','coverage':'SELECTED_ENTRYPOINT_BUILDER_CCD_TEMPLATE_AND_PYTHON_SUBPROCESS_CALLS; CURRENT_PROCESS_ONLY'}
trace['process_observation_schema_version']=1
trace['process_limits']={'argument_items':64,'string_characters':2048,'total_argument_characters':8192,'caller_frames':16}
paths={str((root/spec['library']/name).resolve()):kind for name,kind in [
    ('elbow/command_line/builder.py','builder'),('elbow/scripts/elbow_on_pdb_file.py','template')]}
def process_details(frame):
    remaining=8192;truncated=False;unsupported=False
    def literal(value):
        nonlocal remaining,truncated,unsupported
        if value is None or type(value) is bool:return value
        if type(value) in (str,bytes):
            keep=min(len(value),2048,remaining);remaining-=keep
            if keep!=len(value):truncated=True
            return value[:keep] if type(value) is str else {'encoding':'hex','value':value[:keep].hex()}
        unsupported=True
        return {'unsupported_type':type(value).__name__[:80]}
    values=frame.f_locals;args=values.get('args')
    if type(args) in (list,tuple):
        if len(args)>64:truncated=True
        args=[literal(v) for v in args[:64]]
    else:args=literal(args)
    result={'args':args,'executable':literal(values.get('executable')),
        'shell':literal(values.get('shell')),'cwd':literal(values.get('cwd')),
        'environment':'NOT_CAPTURED','truncated':truncated,
        'parameters_complete':not truncated and not unsupported,'callers':[]}
    caller=frame.f_back
    while caller is not None and len(result['callers'])<16:
        result['callers'].append({'source':caller.f_code.co_filename[:2048],
            'function':caller.f_code.co_name[:128],'line':caller.f_lineno})
        caller=caller.f_back
    result['callers_truncated']=caller is not None
    return result
def save():
    path=Path('consumption_trace.tmp');path.write_text(json.dumps(trace,indent=2,allow_nan=False)+'\n');path.replace('consumption_trace.json')
def profile(frame,event,arg):
    name=frame.f_code.co_name
    if event=='return' and name=='run' and frame.f_code.co_filename==str(entry):
        try:trace['effective_actions']={k:getattr(arg[1].ready_set.actions,k) for k in spec['expected_actions']}
        except (TypeError,IndexError,AttributeError):pass
        save()
    if event!='call' or name not in {'run','get_elbow_molecule_from_chemical_components','__init__'}:return
    kind=paths.get(frame.f_code.co_filename)
    if kind=='builder' and name!='run' or kind=='template' and name!='get_elbow_molecule_from_chemical_components':kind=None
    if name=='__init__' and frame.f_globals.get('__name__')=='subprocess' and frame.f_locals.get('self').__class__.__name__=='Popen':kind='subprocess'
    if kind:
        trace[kind+'_calls']+=1
        if len(trace['events'])<trace['event_budget']:
            observed={'kind':kind,'function':name,'source':frame.f_code.co_filename}
            if kind=='subprocess':observed['process']=process_details(frame)
            trace['events'].append(observed)
        else:trace['truncated']=True
        save()
result={'execution':'STARTED','argument_overrides':'NONE','native_internal_operations':'NOT_EXHAUSTIVELY_INSTRUMENTED'}
if sys.getprofile() is not None:raise ValueError('Unexpected pre-existing profiler')
save();sys.argv=[str(entry),*spec['arguments']]
result['entry_argv']=list(sys.argv)
try:
    sys.setprofile(profile)
    runpy.run_path(str(entry),run_name='__main__')
    result['execution']='COMPLETED'
except BaseException as exc:
    result.update(execution='EXCEPTION',exception_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
finally:
    result['observer_retained']=sys.getprofile() is profile
    sys.setprofile(None);verify();save()
Path('consumption_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
sys.exit(0 if result['execution']=='COMPLETED' else 1)
'''


def _json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def _ref(path,root):
    data=path.read_bytes()
    return {'anchor':'postmr_readyset_directory','path':path.relative_to(root).as_posix(),
            'sha256':sha256(data).hexdigest(),'size':len(data)}


def _atoms(path):
    result={}
    for line in path.read_text().splitlines():
        if line[:6].strip() not in {'ATOM','HETATM'}:continue
        key=(line[21:22],line[22:26].strip(),line[26:27].strip(),line[17:20].strip(),line[16:17].strip(),line[12:16].strip())
        element=line[76:78].strip().upper() or re.sub('[^A-Za-z]','',key[-1])[:1].upper()
        if element in {'H','D'}:continue
        if key in result:raise ValueError('Duplicate ReadySet heavy atom identity')
        xyz=tuple(float(line[i:i+8]) for i in [30,38,46])
        if not all(math.isfinite(x) for x in xyz):raise ValueError('Nonfinite ReadySet coordinates')
        result[key]=(element,xyz)
    if not result:raise ValueError('Empty ReadySet heavy model')
    return result


def heavy_control(model,output):
    """Omit H/D records from an isolated copied seed; retain heavy records exactly."""
    lines=[]
    for line in model.read_text().splitlines(keepends=True):
        if line[:6].strip() in {'ATOM','HETATM'}:
            element=line[76:78].strip().upper() or re.sub('[^A-Za-z]','',line[12:16])[:1].upper()
            if element in {'H','D'}:continue
        lines.append(line)
    output.write_text(''.join(lines))
    if _atoms(output)!=_atoms(model):raise ValueError('Heavy control changed named coordinates')


def effective_cached_input(dictionary,generated,output):
    """Use the ordinary parameterized-input precedence without editing raw output."""
    from .ligand_profiles import effective_restraints
    effective,views=effective_restraints([dictionary],generated,output,
        normalize_effective=True,prefer_parameterized_inputs=True)
    exact=len(effective)==len(views)==1 and effective[0].read_bytes()==dictionary.read_bytes()
    return (effective[0] if len(effective)==1 else None),{
        'single_effective_dictionary':len(effective)==len(views)==1,
        'effective_numerics_exact':exact}


def read_readyset_consumption(directory):
    """Resolve frozen input/effective artifacts without the original installation."""
    root=Path(directory)
    if not root.is_dir() or any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('Unsafe ReadySet control directory')
    report_path=root/'readyset_consumption.json'
    if report_path.is_symlink():raise ValueError('Unsafe ReadySet control report')
    r=json.loads(report_path.read_bytes())
    if r['policy_id']!=POLICY_ID or r['requires_cif_review'] is not False:raise ValueError('ReadySet control policy differs')
    def resolve(ref):
        name=ref['path']
        if (ref.get('anchor')!='postmr_readyset_directory' or not isinstance(name,str)
                or '\\' in name or ':' in name or name.startswith('/') or any(v in {'','.','..'} for v in name.split('/'))):raise ValueError('Unsafe ReadySet reference')
        path=root/name
        if any(p.is_symlink() for p in [path,*path.parents]) or _ref(path,root)!=ref:raise ValueError('ReadySet frozen artifact changed')
        return path
    inputs={k:resolve(v) for k,v in r['inputs'].items()}
    resolve(r['heavy_control'])
    for ref in r['outputs']:resolve(ref)
    return {'report':r,**inputs,'dictionary':resolve(r['effective_dictionary']) if r.get('effective_dictionary') else inputs['dictionary']}


def audit_readyset_consumption(source,dictionary,model,code,phenix,consumer,output,*,timeout_seconds=180):
    """One bounded ordinary helper call; retain verified inputs on failed evidence."""
    from .postmr import _run_readyset,PostMRPreparationError
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=180:
        raise ValueError('ReadySet deadline must be in (0,180] seconds')
    output=Path(output).absolute()
    if (not re.fullmatch('[A-Za-z0-9]{1,3}',code) or output.exists() or output.is_symlink()
            or any(p.is_symlink() for p in output.parents)):raise ValueError('Require fresh separate ReadySet control')
    output.mkdir(parents=True);inputs=output/'inputs';inputs.mkdir()
    originals={Path(p):Path(p).read_bytes() for p in [source,dictionary,model]}
    frozen={}
    for kind,path in [('source',source),('dictionary',dictionary),('model',model)]:
        target=inputs/(kind+('.pdb' if kind=='model' else '.cif'));target.write_bytes(Path(path).read_bytes());frozen[kind]=target
    heavy=inputs/'heavy_seed.pdb';heavy_control(frozen['model'],heavy)
    report={'schema_version':1,'policy_id':POLICY_ID,'component':code,'status':'PREPARED_ONLY',
        'inputs':{k:_ref(p,output) for k,p in frozen.items()},'heavy_control':_ref(heavy,output),
        'execution':{'status':'NOT_RUN'},'checks':{},'trace':{},'outputs':[],
        'requires_cif_review':False,'automatic_adoption':False,'verified_input_retained':True,
        'invocation':'SELECTED_LITERAL_READYSET_ENTRYPOINT_WITH_ORDINARY_ARGUMENTS',
        'dispatcher_execution':'NOT_RUN; SELECTED_PHENIX_PYTHON_OBSERVER_TRANSPORT',
        'scope':'ISOLATED_ORDINARY_READYSET_CONSUMPTION; NOT_FULL_POSTMR_OR_LINKED_MODEL',
        'model_optimization_requested':False,'native_internal_operations':'NOT_EXHAUSTIVELY_INSTRUMENTED'}
    if phenix is not None:
        if not verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer):raise ValueError('Current ReadySet consumer differs')
        root=Path(phenix.root).resolve(strict=True);site=_library_anchor(consumer['api_sources'])
        ready=Path(phenix.executables['phenix.ready_set']).resolve(strict=True)
        proof={'anchor':'phenix_installation','path':ready.relative_to(root).as_posix(),
            'size':ready.stat().st_size,'sha256':sha256(ready.read_bytes()).hexdigest()}
        sources=_capture_consumption_sources(root,site,proof,output/'source_evidence')
        required={str(site/name) for name in OBSERVED_MODULES}
        if not required<={r['path'] for r in sources['sources']}:raise ValueError('Incomplete ReadySet builder source coverage')
        report['source_evidence']=sources;report['readyset_dispatcher']=proof
        run=output/'readyset';run.mkdir();(run/'consumption_worker.py').write_text(WORKER)
        def execute(command,**kwargs):
            report['ordinary_arguments']=command
            spec={'installation':str(root),'library':str(site),'entrypoint':sources['entrypoint']['path'],
                'sources':[{k:r[k] for k in ['path','sha256']} for r in sources['sources']],
                'arguments':command[1:],'expected_actions':EXPECTED_ACTIONS}
            _json(run/'consumption_spec.json',spec)
            verify_readyset_sources(root,sources,output/'source_evidence')
            env=dict(phenix.environment);env.pop('READY_SET_LIGAND_CACHE_DIRECTORY',None)
            env['PYTHONDONTWRITEBYTECODE']='1'
            clock=time.monotonic()
            with (run/'observer.log').open('xb') as log:
                process=subprocess.Popen([str(phenix.executables['phenix.python']),'consumption_worker.py','consumption_spec.json'],
                    cwd=run,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
                try:
                    rc=process.wait(timeout=timeout_seconds);report['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
                except subprocess.TimeoutExpired:
                    _terminate_owned_group(process);rc=process.returncode;report['execution'].update(status='TIMED_OUT',returncode=rc)
                except BaseException:_terminate_owned_group(process);raise
            report['execution'].update(elapsed_seconds=round(time.monotonic()-clock,6),timeout_seconds=timeout_seconds)
            if _ref(heavy,output)!=report['heavy_control'] or any(_ref(p,output)!=report['inputs'][k] for k,p in frozen.items()):
                raise ValueError('ReadySet changed a frozen input')
            verify_readyset_sources(root,sources,output/'source_evidence')
            for name,key in [('consumption_trace.json','trace'),('consumption_result.json','worker_result')]:
                p=run/name
                if p.is_symlink():raise ValueError('Unexpected ReadySet observer symlink')
                if p.is_file():report[key]=json.loads(p.read_bytes())
            return subprocess.CompletedProcess(command,rc,(run/'observer.log').read_text(errors='replace'))
        try:
            checked,log,generated,command,audit=_run_readyset(heavy,ready,run,frozen['dictionary'],phenix.environment,
                allow_op3_sites=tuple(sorted({':'.join(k[:2]) for k in _atoms(heavy) if k[-1]=='OP3'})),process_runner=execute)
            report['ordinary_arguments']=command;report['readyset_output_mode']=audit['readyset_output_mode']
            report['phosphate_audit']=audit;report['readyset_model']=_ref(checked,output)
            report['raw_readyset_dictionary']=_ref(generated,output) if generated else None
            effective=output/'effective';effective.mkdir()
            selected,checks=effective_cached_input(frozen['dictionary'],generated,effective)
            report['checks'].update(checks)
            if selected:report['effective_dictionary']=_ref(selected,output)
            report['checks']['unchanged_heavy_sites']=_atoms(checked)==_atoms(heavy)
        except PostMRPreparationError as exc:report['error']=str(exc)
        trace=report['trace'];result=report.get('worker_result',{})
        report['checks'].update(
            readyset_completed=report['execution']['status']=='COMPLETED' and result.get('execution')=='COMPLETED',
            observer_complete=result.get('observer_retained') is True and trace.get('truncated') is False,
            effective_actions=trace.get('effective_actions')==EXPECTED_ACTIONS,
            no_observed_builder_or_template_calls=trace.get('builder_calls')==trace.get('template_calls')==0,
            no_observed_subprocess_calls=trace.get('subprocess_calls')==0)
        report['status']='READYSET_CACHED_INPUT_PASS' if len(report['checks'])==8 and all(report['checks'].values()) else 'REVIEW'
        if not verify_current_consumer(phenix,ready,consumer):raise ValueError('ReadySet consumer changed')
        if sha256(ready.read_bytes()).hexdigest()!=proof['sha256']:raise ValueError('ReadySet dispatcher changed')
    original_paths={'source':source,'dictionary':dictionary,'model':model}
    if (any(p.read_bytes()!=data for p,data in originals.items())
            or any(p.read_bytes()!=originals[Path(original_paths[k])] for k,p in frozen.items())):
        raise ValueError('ReadySet changed a frozen or original input')
    report['outputs']=[];report['excluded_serialized_outputs']=[]
    for p in sorted(output.rglob('*')):
        if p.is_symlink():raise ValueError('Unexpected ReadySet output symlink')
        if p.is_file() and p.name!='readyset_consumption.json':
            if p.suffix in {'.pickle','.pkl','.pyc'}:report['excluded_serialized_outputs'].append(_ref(p,output))
            else:report['outputs'].append(_ref(p,output))
    _json(output/'readyset_consumption.json',report);read_readyset_consumption(output)
    return report
