"""Complete, separate native builder candidates from source-exact objects.

This adapter does not replace native mechanics or adopt a dictionary. It retains
written output across soft stopping/errors for later native usability selection.
"""
import ast
from hashlib import sha256
from inspect import getsource
import json,math,os
from pathlib import Path
import subprocess,time

from .cif_declared_charge_control import native_inventory,control_declared_charges
from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import _inside,MAX_SOURCE_BYTES
from .cif_generation import _generator_capabilities,_ideal_seed,_terminate_owned_group,inspect_component_generation,_explicit_formal_charges
from .cif_stereochemistry_audit import _values,_graph,_coordinates,_volume,reader_stereo_inventory,VOLUME_EPSILON,audit_optimizer_log

POLICY_ID='cif-source-native-complete-candidate-v1'
SOURCE_PATHS=('elbow/chemistry/any_chemical_format_reader.py','elbow/chemistry/MoleculeClass.py',
              'elbow/chemistry/SimpleMoleculeClass.py','elbow/command_line/builder.py')


def native_object_reference(text):
    """Recognize the installed run API's existing prepared-object route."""
    tree=ast.parse(text);runs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run']
    if len(runs)!=1:raise ValueError('Missing native builder run API')
    run=runs[0]
    def assign(n,name):
        return isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name
    handoffs=[n for n in run.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
        and isinstance(n.test.left,ast.Constant) and n.test.left.value=='molecule'
        and len(n.test.ops)==1 and isinstance(n.test.ops[0],ast.In) and isinstance(n.test.comparators[0],ast.Name)
        and n.test.comparators[0].id=='kwds' and any(assign(s,'molecule') and isinstance(s.value,ast.Subscript)
            and isinstance(s.value.value,ast.Name) and s.value.value.id=='kwds' and isinstance(s.value.slice,ast.Constant)
            and s.value.slice.value=='molecule' for s in n.body)]
    guards=[n for n in run.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare)
        and isinstance(n.test.left,ast.Name) and n.test.left.id=='molecule' and len(n.test.ops)==1
        and isinstance(n.test.ops[0],ast.Eq) and isinstance(n.test.comparators[0],ast.Constant)
        and n.test.comparators[0].value is None
        and any(assign(s,'molecule') and isinstance(s.value,ast.Call)
            and isinstance(s.value.func,ast.Name) and s.value.func.id=='parser' for s in n.body)]
    calls={name:[n for n in ast.walk(run) if assign(n,'molecule') and isinstance(n.value,ast.Call)
        and isinstance(n.value.func,ast.Name) and n.value.func.id==name and n.value.args
        and isinstance(n.value.args[0],ast.Name) and n.value.args[0].id=='molecule'] for name in ['builder','post_process']}
    parser_calls=[n for n in ast.walk(run) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='parser']
    if (len(handoffs)!=1 or len(guards)!=1 or len(parser_calls)!=1 or not all(len(v)==1 for v in calls.values())
            or not handoffs[0].lineno<guards[0].lineno<calls['builder'][0].lineno<calls['post_process'][0].lineno):
        raise ValueError('Unsupported native prepared-object builder route')
    return {'function':'run','object_line':handoffs[0].lineno,'guarded_parser_line':guards[0].lineno,
            'builder_line':calls['builder'][0].lineno,'postprocess_line':calls['post_process'][0].lineno}


def complete_candidate_stereo(source,candidate,code):
    """Check completed coordinates in fixed named source bases, including legacy signs.

    Missing labels, unavailable/degenerate coordinates and pucker are notes;
    demonstrated opposite handedness is distinct and is never silently accepted.
    This is source relative, not an independent absolute CIP calculation.
    """
    source,candidate=Path(source),Path(candidate);before=source.read_bytes(),candidate.read_bytes()
    sv,gv=_values(source,code),_values(candidate,code);inventory=reader_stereo_inventory(source,code)
    neighbors=_graph(sv)[3];_,sx=_coordinates(sv,source=True);_,cx=_coordinates(gv,source=False)
    signed={r['center']:r for r in inventory['source_signed_chirality'] if r['volume_sign'].lower()!='both'}
    centers=set(signed)|{n for n,r in inventory['atoms'].items() if r['declared_stereo'] in {'R','S'}}
    terms=[]
    for center in sorted(centers):
        ordered=list(signed[center]['ordered_neighbors']) if center in signed else sorted(neighbors[center])[:3]
        valid=len(neighbors.get(center,[]))==4 and len(ordered)==3 and len(set(ordered))==3 and set(ordered)<=neighbors[center]
        if valid:ordered+=sorted(neighbors[center]-set(ordered))
        # A central-atom/three-neighbor volume can cross zero during local
        # deformation without reversing the complete tetrahedron. Use all four
        # declared neighbors in a fixed named order for finished configuration.
        a,b=(_volume(x,ordered[3],ordered[:3]) for x in [sx,cx]) if valid else (None,None)
        state=('UNASSESSED' if a is None or b is None or min(abs(a),abs(b))<=VOLUME_EPSILON
               else 'PRESERVED' if a*b>0 else 'INVERTED')
        terms.append({'center':center,'basis':'FOUR_DECLARED_NEIGHBORS','ordered_neighbors':ordered,'source_volume':a,'candidate_volume':b,'handedness':state})
    status='INVERTED' if any(t['handedness']=='INVERTED' for t in terms) else 'PRESERVED' if terms and all(t['handedness']=='PRESERVED' for t in terms) else 'UNASSESSED'
    if (source.read_bytes(),candidate.read_bytes())!=before:raise ValueError('Complete stereo audit changed an input')
    return {'schema_version':1,'policy_id':POLICY_ID,'coordinate_stage':'COMPLETE_DICTIONARY',
            'stereochemistry':status,'terms':terms,'absolute_cip_assignment':'NOT_RUN','requires_cif_review':False,
            'source_sha256':sha256(before[0]).hexdigest(),'candidate_sha256':sha256(before[1]).hexdigest()}


WORKER=getsource(native_inventory)+'\n'+getsource(control_declared_charges)+'\n'+r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,inspect,json,sys,traceback
spec=json.loads(Path(sys.argv[1]).read_text());directory=Path.cwd().resolve()
sys.argv=['source_candidate_worker.py']
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory];sys.path.insert(0,spec['library'])
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()
modules={}
for row in spec['sources']:
 path=Path(row['installed']).resolve(strict=True)
 if digest(path)!=row['sha256']:raise ValueError('Installed candidate source changed')
 found=importlib.util.find_spec(row['module'])
 if found is None or found.origin is None or Path(found.origin).resolve(strict=True)!=path:raise ValueError('Unselected candidate source')
 module=importlib.import_module(row['module'])
 if Path(module.__file__).resolve(strict=True)!=path:raise ValueError('Unselected candidate import')
 modules[row['module']]=module
api=modules['elbow.chemistry.any_chemical_format_reader'];builder=modules['elbow.command_line.builder']
source=Path('source.cif');original=digest(source)
result={'reader':{'execution':'NOT_RUN'},'charge_control':{'status':'NOT_RUN'},'builder':{'status':'NOT_RUN'},
        'captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN'}
try:
 molecule=api.any_chemical_format_reader(str(source.resolve()),simple=True,return_all_restraints=True,do_not_check_for_smiles=True)
 if type(molecule) is list:
  if len(molecule)!=1:raise ValueError('Require one source component')
  molecule=molecule[0]
 result['reader']={**native_inventory(molecule),'execution':'COMPLETED','format':molecule.GetOriginalFormat(),
                   'dispatch_is_chemical_components':bool(api.is_chemical_components_file(source.read_text()))}
 result['charge_control']=control_declared_charges(molecule,spec['declared_charge_control'])
 if result['charge_control']['status']!='DECLARED_CHARGE_CONTROL_PASS':raise ValueError('Declared source charge handoff failed')
 molecule=api.return_molecule_class(molecule,simple=False)
 result['builder'].update(status='STARTED',before=native_inventory(molecule),before_format=molecule.GetOriginalFormat())
 # Native run owns Setup, complete construction, optimization and serialization.
 # Supply the prepared object once; never resume a local chiral-template frame.
 sys.argv=['source_candidate_worker.py',*spec['arguments']]
 inspect.signature(builder.run).bind(molecule=molecule,cctbx=True)
 output=builder.run(molecule=molecule,cctbx=True)
 if output is None or type(output) in (list,tuple):raise ValueError('Native builder returned no unique complete molecule')
 result['builder'].update(status='COMPLETED',after=native_inventory(output),after_format=output.GetOriginalFormat())
except Exception as exc:
 result['builder'].update(status='EXCEPTION',exception_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
if digest(source)!=original:raise ValueError('Native builder changed frozen source')
for row in spec['sources']:
 if digest(row['installed'])!=row['sha256']:raise ValueError('Installed candidate source changed')
Path('candidate_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def candidate_generation_diagnostic(report):
    """Explain recorded failure stages without changing a generation decision.

    This pure projection also reads old receipts. It does not validate a capture,
    infer chemistry from exception text, or grant native usability. In particular,
    a caught native exception can coexist with a retained reviewable candidate.
    """
    result=report.get('result',{});reader=result.get('reader',{})
    handoff=result.get('charge_control',{});builder=result.get('builder',{})
    execution=report.get('execution',{});inspection=report.get('inspection',{})
    failed=sorted({name for key in ('preconditions','checks')
                   for name,value in handoff.get(key,{}).items() if value is False})
    reasons=list(inspection.get('rejection_reasons',[]))
    if report.get('representation_validation',{}).get('status')=='BLOCKED':
        reasons.append('source-representation-handoff-not-qualified')
    if report.get('formal_charges_preserved') is False:
        reasons.append('complete-formal-charges-not-preserved')
    if report.get('finished_stereo',{}).get('stereochemistry')=='INVERTED':
        reasons.append('finished-source-relative-stereo-inverted')
    fields=sorted({row['field'] for row in inspection.get('chemical_changes',[])
                   if row['field'] in {'atom_elements','hydrogen_attachments'}
                   or (row['field']=='bond_orders' and
                       inspection.get('bond_representation',{}).get('status')!='SOURCE_DECLARED_EQUIVALENT')})
    candidate=bool(report.get('candidate'));status=report.get('status')
    state=('ABSENT' if not candidate else 'RETAINED_REVIEW' if status=='CANDIDATE_REVIEW'
           else 'RETAINED_REJECTED' if status=='REJECTED' else 'RETAINED_UNASSESSED')
    exception=({k:builder[k] for k in ('exception_type','message') if k in builder}
               if builder.get('status')=='EXCEPTION' else None)
    stage=None
    if report.get('error') or report.get('source_preserved') is False:
        stage='ADAPTER';summary=report.get('error') or 'Source preservation failed.'
    elif state=='RETAINED_REJECTED':
        stage='CANDIDATE_ASSESSMENT'
        summary='Retained candidate rejected: '+', '.join(reasons or ['see recorded assessment'])+'.'
        if fields:summary+=' Changed identity fields: '+', '.join(fields)+'.'
    elif state=='RETAINED_REVIEW':
        summary='Candidate retained for review; native usability requires separate qualification.'
    elif failed or handoff.get('status') in {'BLOCKED','REVIEW'}:
        stage='SOURCE_HANDOFF'
        summary='Source handoff blocked before construction: '+', '.join(failed or [handoff.get('reason','see recorded handoff')])+'.'
    elif builder.get('status')=='EXCEPTION':
        stage='NATIVE_BUILDER' if 'before' in builder else 'SOURCE_READER' if reader.get('execution')!='COMPLETED' else 'SOURCE_HANDOFF'
        summary=stage.replace('_',' ').capitalize()+': '+builder.get('message','native exception')
    elif execution.get('status') in {'FAILED','TIMED_OUT'}:
        stage='EXECUTION';summary='Native execution '+execution['status'].lower().replace('_',' ')+'.'
    else:
        stage='UNDETERMINED';summary='No reviewable candidate or completed failure stage was recorded.'
    if state=='RETAINED_REVIEW' and exception:
        summary+=' Native builder also reported: '+exception.get('message','an exception')
    return {'policy_id':'cif-source-candidate-diagnostic-v1','generation_status':status,
            'candidate_state':state,'blocking_stage':stage,'summary':summary,
            'builder_started':True if 'before' in builder else False if builder.get('status') in {'NOT_RUN','EXCEPTION'} else None,
            'failed_handoff_checks':failed,
            'handoff_reason':handoff.get('reason'),'native_exception':exception,
            'execution_status':execution.get('status'),'execution_returncode':execution.get('returncode'),
            'rejection_reasons':sorted(set(reasons)),'identity_change_fields':fields,
            'native_usability':'NOT_ASSESSED_BY_DIAGNOSTIC','automatic_adoption':False}


def generate_source_candidate(installation_root,python_executable,elbow_executable,api_sources,source,code,output,*,
        environment,expected_dialect,prior_sources,phenix_version,single_block_steps=180,timeout_seconds=600,bond_representation_policy=None):
    """Request one bounded full native builder and retain its exact written CIF."""
    from .cif_purine_representation import validate_policy
    validate_policy(bond_representation_policy)
    if type(single_block_steps) is not int or not 1<=single_block_steps<=600:raise ValueError('Require 1--600 optimization steps')
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=600:raise ValueError('Require a candidate deadline in (0,600]')
    root=Path(installation_root).resolve(strict=True);source=Path(source).resolve(strict=True);output=Path(output).absolute()
    python_executable,elbow_executable=(Path(p).resolve(strict=True) for p in [python_executable,elbow_executable])
    if (not all(p.is_relative_to(root) for p in [python_executable,elbow_executable]) or output.resolve().is_relative_to(root)
            or output.resolve().is_relative_to(source.parent) or output.exists() or output.is_symlink()
            or any(p.is_symlink() for p in output.parents)):raise ValueError('Require selected native dispatchers and a fresh separate output')
    original=source.read_bytes();dispatchers={p:p.read_bytes() for p in [python_executable,elbow_executable]};site=_library_anchor(api_sources)
    proof={r['path']:r for r in prior_sources};rows=[];payloads={}
    for name in SOURCE_PATHS:
        relative=(site/name).as_posix();data=_inside(root,relative).read_bytes();pin=proof.get(relative)
        if (len(data)>MAX_SOURCE_BYTES or pin is None or pin.get('anchor')!='phenix_installation'
                or sha256(data).hexdigest()!=pin.get('sha256') or len(data)!=pin.get('size')):raise ValueError('Prior native builder/source changed')
        ast.parse(data);payloads[name]=data
        rows.append({'anchor':'phenix_installation','path':relative,'sha256':sha256(data).hexdigest(),'size':len(data),
                     'snapshot':{'anchor':'candidate_directory','path':'api_sources/'+name+'.txt'}})
    reference=native_object_reference(payloads['elbow/command_line/builder.py'])
    from .cif_constructor_setup import native_setup_reference
    setup_reference=native_setup_reference(payloads['elbow/command_line/builder.py'])
    v=_values(source,code);elements,bonds,charges,_=_graph(v);_,xyz=_coordinates(v,source=True)
    orders={'SINGLE':1,'DOUBLE':2,'TRIPLE':3,'AROMATIC':1.5,'DELOCALIZED':1.5}
    if set(xyz)!=set(elements) or any(q is None or not q.is_integer() or abs(q)>4 for q in charges.values()) or set(bonds.values())-set(orders):raise ValueError('Require complete declared source state')
    representation_contract=None;worker=WORKER
    if bond_representation_policy is not None:
        from .cif_source_representation import generation_representation_contract,source_representation_worker,generation_representation_validation
        representation_contract=generation_representation_contract(source,code,bond_representation_policy)
        worker=source_representation_worker(WORKER)
    seed,_=_ideal_seed(source,code);output.mkdir(parents=True)
    for name,data in payloads.items():
        p=output/('api_sources/'+name+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    (output/'source.cif').write_bytes(original);(output/'source_ideal.pdb').write_text(seed);(output/'candidate_worker.py').write_text(worker)
    report={'schema_version':1,'policy_id':POLICY_ID,'component':code,'status':'FAILED','source_sha256':sha256(original).hexdigest(),
            'phenix_version':phenix_version,'sources':rows,'native_object_reference':reference,'native_setup_reference':setup_reference,
            'execution':{'status':'NOT_RUN','timeout_seconds':timeout_seconds},'candidate':None,'candidate_retained':False,
            'single_block_steps':single_block_steps,'native_backend':'EXPLICIT_NATIVE_CCTBX_PREPARATION; INSTALLED_OPT_DEFAULTS',
            'native_proxy_validation':'NOT_RUN','absolute_cip_assignment':'NOT_RUN','automatic_adoption':False,
            'requires_cif_review':False,'installed_phenix_edits':'NOT_RUN','model_editing':'NOT_RUN',
            'selection':'PENDING_NATIVE_USABILITY; OUTPUTS_PRESERVED_FOR_AUTOMATIC_FALLBACK'}
    if representation_contract is not None:
        report.update(policy_id='cif-source-native-complete-candidate-v2',bond_representation_policy=bond_representation_policy,
            source_representation_contract=representation_contract)
    started=time.monotonic()
    try:
        caps=_generator_capabilities(elbow_executable,output,environment,timeout_seconds,phenix_version);report['generator_capabilities']=caps
        if caps['status']!='SUPPORTED':raise ValueError('Installed generator options unsupported')
        flags=caps['selected_aliases'];definitions=caps['supported_option_definitions']
        step=next((s for s in ['--opt_steps','--opt-steps'] if definitions.get(s) is True),None)
        if step is None:raise ValueError('Installed generator lacks bounded optimization option')
        args=[f"{flags['id']}={code}",f"{flags['output']}=candidate",f"{flags['template']}=source_ideal.pdb",
              f"{flags['initial_geometry']}=source_ideal.pdb",f"{flags['add_hydrogens']}=False",
              f"{flags['source_state_preservation']}=low",f"{flags['chiral']}=retain",flags['opt'],f'{step}={single_block_steps}']
        spec={'component':code,'library':str(root/site),'installation_root':str(root),'arguments':args,
              'sources':[{'installed':str(root/r['path']),'sha256':r['sha256'],'module':name[:-3].replace('/','.')} for name,r in zip(SOURCE_PATHS,rows)],
              'declared_charge_control':{'component':code,'dialect':expected_dialect,'elements':elements,'coordinates':xyz,
                  'charges':{n:int(q) for n,q in charges.items()},'bonds':[{'atoms':list(p),'order':orders[o]} for p,o in bonds.items()]}}
        if representation_contract is not None:spec['source_representation_contract']=representation_contract
        (output/'candidate_spec.json').write_text(json.dumps(spec,indent=2)+'\n');report['arguments']=args
        with (output/'candidate_worker.log').open('xb') as log:
            process=subprocess.Popen([str(python_executable),'-B','candidate_worker.py','candidate_spec.json'],cwd=output,
                env={**environment,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            try:rc=process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _terminate_owned_group(process);report['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_terminate_owned_group(process);raise
            else:report['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
        if (output/'candidate_result.json').is_file():report['result']=json.loads((output/'candidate_result.json').read_text())
        if representation_contract is not None:
            report['representation_validation']=generation_representation_validation(report.get('result',{}),spec['declared_charge_control'],representation_contract)
        candidate=output/'candidate.cif'
        # Exit status/convergence do not erase an already written regular output.
        if candidate.is_file() and not candidate.is_symlink():
            data=candidate.read_bytes();report.update(candidate={'anchor':'candidate_directory','path':'candidate.cif','sha256':sha256(data).hexdigest(),'size':len(data)},candidate_retained=True)
            options={} if bond_representation_policy is None else {'bond_representation_policy':bond_representation_policy}
            assessment_source=output/'source.cif' if representation_contract is not None else source
            inspection=inspect_component_generation(assessment_source,candidate,code,**options);report['inspection']=inspection
            stereo=complete_candidate_stereo(assessment_source,candidate,code);report['finished_stereo']=stereo
            left=inspection['source_assessment']['components'];right=inspection['generated_assessment']['components']
            charges_preserved=(len(left)==len(right)==1 and bool(_explicit_formal_charges(left[0]))
                and _explicit_formal_charges(left[0])==_explicit_formal_charges(right[0]))
            report['formal_charges_preserved']=charges_preserved
            report['status']='REJECTED' if inspection['status']=='REJECTED' or not charges_preserved or stereo['stereochemistry']=='INVERTED' else 'CANDIDATE_REVIEW'
            if representation_contract is not None and report['representation_validation']['status']!='SOURCE_REPRESENTATION_PASS':report['status']='REJECTED'
        trajectory=audit_optimizer_log((output/'candidate_worker.log').read_text(errors='replace'))
        report['stopping']={'status':trajectory['stopping'],'convergence_claimed':False,'trajectory':trajectory}
    except (OSError,ValueError,KeyError,TypeError) as exc:report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
    report['source_preserved']=(source.read_bytes()==original and (output/'source.cif').read_bytes()==original
        and all(p.read_bytes()==d for p,d in dispatchers.items()))
    for row in rows:
        if _inside(root,row['path']).read_bytes()!=(output/row['snapshot']['path']).read_bytes():raise ValueError('Native builder source changed')
    if not report['source_preserved']:report.update(status='FAILED',error='Source/dispatcher changed')
    report['execution']['elapsed_seconds']=round(time.monotonic()-started,6)
    artifacts=[{'anchor':'candidate_directory','path':p.relative_to(output).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
        for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink()]
    report['outputs']=[r for r in artifacts if Path(r['path']).suffix not in {'.pickle','.pkl'}]
    report['excluded_serialized_outputs']=[r for r in artifacts if Path(r['path']).suffix in {'.pickle','.pkl'}]
    if any(p.is_symlink() for p in output.rglob('*')):report.update(status='FAILED',error='Unexpected candidate output symlink')
    report['diagnostic']=candidate_generation_diagnostic(report)
    (output/'source_candidate_receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');return report
