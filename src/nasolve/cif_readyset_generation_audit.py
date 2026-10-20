"""Isolated ReadySet generation with observed, unmodified eLBOW calls.

This diagnostic never changes a scaffold or installs a dictionary. Process-local
observers record original calls/results, including caught failures and fallback
templates. Generation may perform native internal geometry operations.
"""
from hashlib import sha256
from inspect import getsource
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

from .cif_declared_charge_control import native_inventory
from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import _inside, MAX_SOURCE_BYTES
from .cif_generation import _terminate_owned_group
from .cif_native_validation import inspect_native_bundle
from .cif_doctor import assess_dictionaries, compare_dictionaries
from .cif_triple_bond_audit import audit_triple_bonds, write_component_control_model

POLICY_ID='cif-isolated-readyset-call-and-triple-restraint-audit-v1'
MODULES={'readyset':'elbow.command_line.ready_set','builder':'elbow.command_line.builder',
         'route':'elbow.scripts.elbow_on_pdb_file'}
ACTIONS={'hydrogens':False,'ligands':True,'optimise_ligand_geometry':False,
    'optimise_final_geometry_of_hydrogens':False,'trust_residue_code_is_chemical_components_code':False,
    'metals':False,'link_to_edits':False,'remove_waters':False}


def _json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')


def _artifact(path,directory):
    data=path.read_bytes()
    return {'anchor':'readyset_directory','path':path.relative_to(directory).as_posix(),
        'size':len(data),'sha256':sha256(data).hexdigest()}


WORKER=getsource(native_inventory)+'\n'+r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,inspect,json,math,sys,traceback
sys.dont_write_bytecode=True
spec=json.loads(Path(sys.argv[1]).read_text());directory=Path.cwd().resolve();root=Path(spec['installation']).resolve(strict=True)
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory];sys.path.insert(0,spec['library'])
def verify():
    for row in spec['sources']:
        p=Path(row['installed']).resolve(strict=True)
        if not p.is_relative_to(root) or sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Selected ReadySet source changed')
verify();modules={}
for key,row in spec['modules'].items():
    found=importlib.util.find_spec(row['module']);path=Path(row['installed']).resolve(strict=True)
    if found is None or Path(found.origin).resolve(strict=True)!=path:raise ValueError('Unselected ReadySet module')
    modules[key]=importlib.import_module(row['module'])
    if Path(modules[key].__file__).resolve(strict=True)!=path:raise ValueError('Unselected ReadySet import')
trace={'schema_version':1,'events':[],'event_budget':64,'truncated':False,'argument_overrides':'NONE'}
def save():
    p=Path('call_trace.tmp');p.write_text(json.dumps(trace,indent=2,allow_nan=False)+'\n');p.replace('call_trace.json')
def value(v):
    if type(v) is float and not math.isfinite(v):return {'nonfinite_native_float':str(v)}
    if type(v) in (str,bool,int,float,type(None)):return v
    if type(v) in (list,tuple):return [value(x) for x in v]
    if type(v) is dict:return {str(k):value(x) for k,x in v.items()}
    return {'unsupported_native_type':type(v).__name__}
def observe(api,original):
    def call(*args,**kwargs):
        event=None
        if len(trace['events'])<trace['event_budget']:
            frame=inspect.currentframe().f_back;caller=Path(frame.f_code.co_filename).resolve()
            event={'api':api,'args':value(args),'kwargs':value(kwargs),'status':'STARTED',
                'caller':{'anchor':'phenix_installation' if caller.is_relative_to(root) else 'external',
                    'path':caller.relative_to(root).as_posix() if caller.is_relative_to(root) else str(caller),'line':frame.f_lineno}}
            del frame;trace['events'].append(event)
        else:trace['truncated']=True
        save()
        try:
            result=original(*args,**kwargs)
        except BaseException as exc:
            if event is not None:event.update(status='EXCEPTION',exception_type=type(exc).__name__,message=str(exc))
            save();raise
        if event is not None:
            event.update(status='RETURNED',return_type=type(result).__name__)
            if result is not None:
                try:event['molecule']=value(native_inventory(result))
                except Exception as exc:event['inventory_error']=type(exc).__name__+': '+str(exc)
        save();return result
    return call
original_builder=modules['builder'].run
original_template=modules['route'].get_elbow_molecule_from_chemical_components
modules['builder'].run=observe('ELBOW_BUILDER',original_builder)
modules['route'].get_elbow_molecule_from_chemical_components=observe('CCD_TEMPLATE',original_template)
result={'execution':'STARTED','argument_overrides':'NONE','native_internal_operations':'NOT_INSTRUMENTED',
    'automatic_adoption':False,'refinement':'NOT_RUN','experimental_model_changes':'NOT_RUN'}
save()
try:
    sys.argv=[str(modules['readyset'].__file__),*spec['arguments']]
    output=modules['readyset'].run(spec['arguments'])
    result['effective_actions']={k:getattr(output[1].ready_set.actions,k) for k in spec['actions']}
    result['reported_outputs']=value(output[0]);result['execution']='COMPLETED'
except BaseException as exc:
    result.update(execution='EXCEPTION',exception_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
finally:
    modules['builder'].run=original_builder
    modules['route'].get_elbow_molecule_from_chemical_components=original_template
    verify();save()
Path('readyset_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def _sources(root,site,proofs,output):
    rows=[];seen=set()
    for row in proofs:
        if row.get('anchor')!='phenix_installation' or row['path'] in seen:raise ValueError('Require unique installation source proofs')
        seen.add(row['path']);p=_inside(root,row['path']);data=p.read_bytes()
        if len(data)>MAX_SOURCE_BYTES or sha256(data).hexdigest()!=row['sha256'] or 'size' in row and len(data)!=row['size']:
            raise ValueError('ReadySet source differs from its captured proof')
        target=output/'api_sources'/(row['path']+'.txt');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        rows.append({**row,'size':len(data),'snapshot':{'anchor':'readyset_directory','path':target.relative_to(output).as_posix()}})
    required={(site/(name.replace('.','/')+'.py')).as_posix() for name in MODULES.values()}
    if not required<=seen:raise ValueError('Require prior ReadySet, route and builder source proofs')
    return rows


def verify_readyset_generation_sources(root,rows,directory):
    root=Path(root).resolve(strict=True);directory=Path(directory).resolve(strict=True)
    for row in rows:
        if row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='readyset_directory':raise ValueError('Unsafe generation source anchor')
        a=_inside(root,row['path']).read_bytes();b=_inside(directory,row['snapshot']['path']).read_bytes()
        if len(a)!=row['size'] or sha256(a).hexdigest()!=row['sha256'] or a!=b:raise ValueError('ReadySet API or evidence snapshot changed')


def _generate(phenix,api_sources,proofs,code,model,directory,timeout):
    directory.mkdir(parents=True);root=Path(phenix.root).resolve(strict=True);site=_library_anchor(api_sources)
    executable=Path(phenix.executables['phenix.python']).resolve(strict=True)
    if not executable.is_relative_to(root):raise ValueError('Require selected Phenix Python')
    dispatcher=executable.read_bytes();rows=_sources(root,site,proofs,directory)
    source=model.read_bytes();(directory/'source_seed.pdb').write_bytes(source)
    args=['source_seed.pdb','ready_set.input.output_file_name=readyset_candidate',
        *['ready_set.actions.'+k+'='+str(v) for k,v in ACTIONS.items()]]
    sources=[{'installed':str(root/r['path']),'sha256':r['sha256']} for r in rows]
    spec={'installation':str(root),'library':str(root/site),'sources':sources,'arguments':args,'actions':ACTIONS,
        'modules':{k:{'module':m,'installed':str(root/site/(m.replace('.','/')+'.py'))} for k,m in MODULES.items()}}
    _json(directory/'readyset_spec.json',spec);(directory/'readyset_worker.py').write_text(WORKER)
    report={'schema_version':1,'policy_id':POLICY_ID,'component':code,'sources':rows,'arguments':args,'actions':ACTIONS,
        'execution':{'status':'NOT_RUN'},'candidate':{'status':'MISSING'},'trace':{'events':[]},
        'phenix_version':phenix.version,'invocation':'SELECTED_READYSET_PYTHON_API_RUN',
        'dispatcher_execution':'NOT_RUN','native_internal_operations':'NOT_INSTRUMENTED',
        'am1_ligand_optimization_requested':False,'experimental_model_changes':'NOT_RUN','automatic_adoption':False}
    verify_readyset_generation_sources(root,rows,directory)
    env={k:v for k,v in phenix.environment.items() if k!='READY_SET_LIGAND_CACHE_DIRECTORY'}
    env['PYTHONDONTWRITEBYTECODE']='1'
    clock=time.monotonic()
    with (directory/'readyset.log').open('xb') as log:
        process=subprocess.Popen([str(executable),'readyset_worker.py','readyset_spec.json'],cwd=directory,
            env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
        try:
            rc=process.wait(timeout=timeout);report['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
        except subprocess.TimeoutExpired:
            _terminate_owned_group(process);report['execution'].update(status='TIMED_OUT',returncode=process.returncode)
        except BaseException:
            _terminate_owned_group(process);raise
    report['execution']['elapsed_seconds']=round(time.monotonic()-clock,6)
    if executable.read_bytes()!=dispatcher or model.read_bytes()!=source or (directory/'source_seed.pdb').read_bytes()!=source:
        raise ValueError('ReadySet changed a frozen source seed or dispatcher')
    verify_readyset_generation_sources(root,rows,directory)
    for name in ['call_trace.json','readyset_result.json']:
        p=directory/name
        if p.is_symlink():raise ValueError('Unexpected ReadySet result symlink')
        if p.exists():report['trace' if name=='call_trace.json' else 'result']=json.loads(p.read_text())
    result=report.get('result',{})
    if result.get('execution')=='COMPLETED' and result.get('effective_actions')!=ACTIONS:raise ValueError('ReadySet effective actions differ from requested isolated policy')
    candidate=directory/(code+'.cif')
    if candidate.is_symlink():raise ValueError('Unexpected ReadySet candidate symlink')
    if candidate.is_file():report['candidate']={'status':'RECORDED',**_artifact(candidate,directory)}
    report['outputs']=[];report['excluded_serialized_outputs']=[]
    for p in sorted(directory.rglob('*')):
        if p.is_symlink():raise ValueError('Unexpected ReadySet output symlink')
        if not p.is_file():continue
        if p.suffix in {'.pickle','.pkl'}:
            report['excluded_serialized_outputs'].append({'anchor':'readyset_directory','path':p.relative_to(directory).as_posix(),'size':p.stat().st_size})
        elif p.suffix!='.pyc':report['outputs'].append(_artifact(p,directory))
    _json(directory/'readyset_generation_receipt.json',report)
    return report


def audit_readyset_controls(sources,output,*,phenix=None,api_sources=(),source_proofs=(),timeout_seconds=180):
    """Run separate default-code isolated controls, then inspect their terms.

    The supplied sources define fixed seed coordinates; numerical targets come
    from ReadySet. Heavy-only input matches NASolve's explicit hydrogens=False
    policy. The complete source and all raw comparison findings are retained.
    """
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=180:
        raise ValueError('Require a ReadySet deadline in (0,180] seconds')
    sources={c:Path(p).resolve(strict=True) for c,p in sources.items()};output=Path(output).absolute()
    if (not 1<=len(sources)<=3 or any(not re.fullmatch('[A-Z0-9]{1,3}',c) for c in sources)
            or output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents)
            or any(output.resolve().is_relative_to(p.parent) for p in sources.values())):
        raise ValueError('Require explicit components and fresh separate ReadySet output')
    if phenix is not None and output.resolve().is_relative_to(Path(phenix.root).resolve()):raise ValueError('Output must be outside installation')
    originals={p:p.read_bytes() for p in sources.values()};output.mkdir(parents=True)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','cases':{},'native_execution':'NOT_RUN',
        'experimental_model_changes':'NOT_RUN','refinement':'NOT_RUN','scientific_approval':'NOT_RUN','automatic_adoption':False,
        'limitations':['Isolated heavy-atom source seeds do not reproduce a linked scaffold or a historical ReadySet run.',
            'Native generation may optimize internal templates; AM1 ligand and final hydrogen optimization are explicitly disabled.',
            'Observers forward original arguments/returns and exceptions unchanged; caught errors/fallback remain evidence.',
            'Full-source hydrogen/stereo/charge differences stay visible; a triple-target pass is not chemistry or convergence approval.']}
    for code,source in sources.items():
        full=output/'models'/code/'complete_source_seed.pdb';preparation=write_component_control_model(source,code,full)
        model=full.with_name('source_seed.pdb');model.write_text(''.join(line for line in full.read_text().splitlines(keepends=True)
            if not line.startswith('HETATM') or line[76:78].strip() not in {'H','D','T'}))
        case={'source_sha256':sha256(source.read_bytes()).hexdigest(),'model_preparation':{**preparation,
            'hydrogen_policy':'EXPLICIT_HEAVY_ATOMS_ONLY','heavy_model_sha256':sha256(model.read_bytes()).hexdigest()},
            'generation':{'execution':{'status':'NOT_RUN'}},'native_triple_screen':{'status':'NOT_RUN'}}
        report['cases'][code]=case
        policy=model.parent/'isolated_component.phil';policy.write_text('pdb_interpretation {\n secondary_structure.enabled = False\n}\n')
        seeds=full.read_bytes(),model.read_bytes(),policy.read_bytes()
        if phenix is None:continue
        directory=output/'generation'/code
        generation=_generate(phenix,api_sources,source_proofs,code,model,directory,timeout_seconds)
        case['generation']={'directory':{'anchor':'readyset_control_directory','path':directory.relative_to(output).as_posix()},**generation}
        if generation['candidate']['status']=='RECORDED':
            candidate=directory/generation['candidate']['path']
            parsed=False
            try:
                case['dictionary_assessment']=assess_dictionaries([candidate],stage='isolated-readyset-output')
                case['raw_source_comparison']=compare_dictionaries([source],[candidate])
                case['dictionary_triple_screen']=audit_triple_bonds(source,code,dictionary=candidate)
                parsed=True
            except ValueError as exc:
                case['dictionary_triple_screen']={'status':'REVIEW','error':str(exc)}
            # Interpret only completed, policy-matched ReadySet output. Partial
            # candidates and exceptions remain captured, never silently reused.
            if parsed and generation['execution']['status']=='COMPLETED' and generation.get('result',{}).get('execution')=='COMPLETED':
                native=inspect_native_bundle(model,[candidate],output/'native'/code,phenix.executables['phenix.python'],
                    environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=60,
                    phil_files=[policy],inventory_detail='linked',policy_inventory=True)
                case['native_interpretation']=native
                validation=native.get('native_validation') or {}
                if native['status']=='REVIEW' and validation.get('status')=='REVIEW':
                    if validation.get('restraint_policy',{}).get('secondary_structure_enabled') is not False:raise ValueError('Native ReadySet control enabled SS inference')
                    case['native_triple_screen']=audit_triple_bonds(source,code,native=validation)
        if seeds!=(full.read_bytes(),model.read_bytes(),policy.read_bytes()):raise ValueError('ReadySet control changed fixed model/policy evidence')
        verify_readyset_generation_sources(phenix.root,generation['sources'],directory)
    if any(p.read_bytes()!=data for p,data in originals.items()):raise ValueError('ReadySet control source changed')
    if phenix is not None:report['native_execution']='ISOLATED_READYSET_GENERATION_AND_TRIPLE_PROXY_CONTROLS'
    _json(output/'readyset_control_receipt.json',report)
    return report
