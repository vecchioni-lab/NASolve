"""Separate recovery of unusable mixed-fixture component numerics.

Select hard capability failures from actual effective rows, retain every parent
input, and reuse the source-native complete builder and isolated qualifier.
No construction, ReadySet retry, linked adoption or native mechanics change.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import ast
import json
import math
import os
from pathlib import Path
import subprocess

POLICY_ID = 'cif-mixed-component-numerical-recovery-v1'
ANCHOR = 'mixed_recovery_directory'
REPORT = 'mixed_recovery.json'


def _safe(name):
    return (isinstance(name,str) and bool(name) and not name.startswith('/')
        and '\\' not in name and ':' not in name and not any(ord(c)<32 or ord(c)==127 for c in name)
        and all(p not in {'','.','..'} for p in name.split('/')))


def _ref(path, root):
    path,root=Path(path),Path(root)
    if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Recovery artifact traverses a symlink')
    name=path.relative_to(root).as_posix()
    if not _safe(name):raise ValueError('Unsafe recovery artifact')
    data=path.read_bytes()
    return {'anchor':ANCHOR,'path':name,'sha256':sha256(data).hexdigest(),'size':len(data)}


def _resolve(root,ref):
    if not isinstance(ref,dict) or ref.get('anchor')!=ANCHOR or not _safe(ref.get('path')):
        raise ValueError('Unsafe recovery reference')
    p=root/ref['path']
    if _ref(p,root)!=ref:raise ValueError('Recovery artifact bytes differ')
    return p


def _dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as handle:json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def _targets(required, missing, sources, dictionaries):
    from .ligand_profiles import _parameterized_codes, dictionary_component_codes
    from .cif_mixed_native import CANONICAL
    if (not isinstance(required,list) or len(required)!=len(set(required)) or set(required)!=(set(sources)-CANONICAL)
            or not isinstance(missing,list) or len(missing)!=len(set(missing))):
        raise ValueError('Invalid parent numerical scope')
    actual=set().union(*(_parameterized_codes(p) for p in dictionaries)) if dictionaries else set()
    selected=sorted(set(required)-actual)
    definitions=set().union(*(dictionary_component_codes(p) for p in dictionaries)) if dictionaries else set()
    if selected!=sorted(missing) or not 1<=len(selected)<=4 or not set(selected)<=definitions:
        raise ValueError('Require one to four actual hard numerical capability failures with exact parent evidence')
    return selected


ANCHOR_WORKER = r'''from pathlib import Path
from hashlib import sha256
import json,sys
from iotbx import phil
spec=json.loads(Path(sys.argv[1]).read_text())
root=Path(spec['installation_root']).resolve(strict=True)
path=Path(phil.__file__).resolve(strict=True)
if not path.is_relative_to(root) or not path.as_posix().endswith('/iotbx/phil.py'):
 raise ValueError('Selected interpreter did not provide the expected installed library anchor')
data=path.read_bytes()
row={'anchor':'phenix_installation','path':path.relative_to(root).as_posix(),'sha256':sha256(data).hexdigest(),'size':len(data)}
Path('source_probe_result.json').write_text(json.dumps({'api_sources':[row]},indent=2)+'\n')
'''


def capture_candidate_sources(phenix, output, *, timeout_seconds=30):
    """Fresh selected-interpreter anchor, then four bounded static source copies."""
    from .cif_generation import _terminate_owned_group
    from .cif_source_candidate import SOURCE_PATHS
    from .cif_elbow_chirality import _library_anchor
    from .cif_elbow_contract import _inside,MAX_SOURCE_BYTES
    output=Path(output);output.mkdir(parents=True)
    root=Path(phenix.root).resolve(strict=True)
    executable=Path(phenix.executables['phenix.python']).resolve(strict=True)
    if not executable.is_relative_to(root):raise ValueError('Source probe interpreter is outside selected Phenix')
    original=executable.read_bytes()
    (output/'source_probe_worker.py').write_text(ANCHOR_WORKER)
    spec={'installation_root':str(root)};_dump(output/'source_probe_spec.json',spec)
    result={'status':'FAILED','historical_root':str(root),'api_sources':[],'sources':[],
        'execution':{'status':'NOT_RUN','timeout_seconds':min(timeout_seconds,30)},'new_source_probe_calls':0,
        'captured_code_execution':'NOT_RUN','source_policy':'FRESH_SELECTED_INSTALLATION; NOT_A_REUSED_NATIVE_QUALIFICATION',
        'executable_sha256':sha256(original).hexdigest()}
    try:
        with (output/'source_probe.log').open('xb') as log:
            process=subprocess.Popen([str(executable),'-B','source_probe_worker.py','source_probe_spec.json'],cwd=output,
                env={**phenix.environment,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
            result['new_source_probe_calls']=1
            try:rc=process.wait(timeout=min(timeout_seconds,30))
            except subprocess.TimeoutExpired:
                _terminate_owned_group(process);result['execution'].update(status='TIMED_OUT',returncode=process.returncode)
            except BaseException:_terminate_owned_group(process);raise
            else:result['execution'].update(status='COMPLETED' if rc==0 else 'FAILED',returncode=rc)
        if result['execution']['status']!='COMPLETED':raise ValueError('Selected library-anchor probe did not complete')
        data=json.loads((output/'source_probe_result.json').read_bytes());api=data['api_sources']
        site=_library_anchor(api)
        for row in api:
            payload=_inside(root,row['path']).read_bytes()
            if len(payload)!=row['size'] or sha256(payload).hexdigest()!=row['sha256']:raise ValueError('Installed anchor changed')
            p=output/'api_sources/iotbx/phil.py.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(payload)
            row['snapshot']='api_sources/iotbx/phil.py.txt'
        result['api_sources']=api
        for name in SOURCE_PATHS:
            relative=(site/name).as_posix();payload=_inside(root,relative).read_bytes()
            if len(payload)>MAX_SOURCE_BYTES:raise ValueError('Oversized installed candidate source')
            ast.parse(payload)
            p=output/'sources'/(name+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(payload)
            result['sources'].append({'anchor':'phenix_installation','path':relative,'sha256':sha256(payload).hexdigest(),
                'size':len(payload),'snapshot':p.relative_to(output).as_posix()})
        if executable.read_bytes()!=original:raise ValueError('Selected source-probe interpreter changed')
        result['status']='FRESH_CANDIDATE_SOURCES_CAPTURED'
    except (OSError,ValueError,KeyError,TypeError) as exc:result['error']=type(exc).__name__+': '+str(exc)
    _dump(output/'source_capture.json',result)
    return result


def _verify_source_capture(root, capture):
    from .cif_source_candidate import SOURCE_PATHS
    from .cif_elbow_chirality import _library_anchor
    folder=_resolve(root,capture['receipt']).parent
    record=json.loads((folder/'source_capture.json').read_bytes())
    if record!=capture['record']:raise ValueError('Fresh source capture receipt differs')
    if (folder/'source_probe_worker.py').read_text()!=ANCHOR_WORKER:raise ValueError('Source-probe worker differs')
    if record['status']=='FRESH_CANDIDATE_SOURCES_CAPTURED':
        if record['execution'].get('status')!='COMPLETED' or record['execution'].get('returncode')!=0:
            raise ValueError('Incomplete source probe execution')
        api=record['api_sources'];site=_library_anchor(api)
        if len(api)!=1 or len(record['sources'])!=len(SOURCE_PATHS):raise ValueError('Incomplete fresh source scope')
        expected={(site/n).as_posix() for n in SOURCE_PATHS}
        if {r['path'] for r in record['sources']}!=expected:raise ValueError('Fresh source paths differ')
        for row in [*api,*record['sources']]:
            if row.get('anchor')!='phenix_installation' or not _safe(row.get('snapshot')):raise ValueError('Unsafe fresh source snapshot')
            data=(folder/row['snapshot']).read_bytes()
            if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:raise ValueError('Fresh source snapshot differs')
        bare=[{k:v for k,v in r.items() if k!='snapshot'} for r in api]
        if json.loads((folder/'source_probe_result.json').read_bytes())!={'api_sources':bare}:
            raise ValueError('Fresh interpreter result differs')
        if json.loads((folder/'source_probe_spec.json').read_bytes())!={'installation_root':record['historical_root']}:
            raise ValueError('Fresh source probe specification differs')
    return record


def _publish(output,report):
    if any(p.is_symlink() for p in output.rglob('*')):raise ValueError('Recovery output contains a symlink')
    report['outputs']=[_ref(p,output) for p in sorted(output.rglob('*')) if p.is_file() and p!=output/REPORT and p.suffix not in {'.pickle','.pkl','.pyc'}]
    _dump(output/REPORT,report);read_mixed_recovery(output);return report


def _native_ok(capture):
    from .cif_mixed_native import _native_ok as valid
    return valid(capture)


def _candidate_assessment(source,candidate,code):
    from .cif_candidate_usability import reassess_complete_candidate
    from .ligand_profiles import _parameterized_codes
    try:
        return reassess_complete_candidate(source,candidate,code),code in _parameterized_codes(candidate)
    except (ValueError,OSError,KeyError,TypeError,IndexError,ZeroDivisionError,OverflowError) as exc:
        return {'candidate_status':'REJECTED','assessment_status':'ASSESSMENT_FAILED',
            'error':type(exc).__name__+': '+str(exc)},False


def _combined_decision(source,candidate,code,cases,stopping):
    from .cif_candidate_usability import isolated_candidate_decision,covalent_proxy_signature,reassess_complete_candidate
    completed=[cases[k] for k in ['source_seed','generated_output'] if cases.get(k,{}).get('qualification')]
    if len(completed)==2:
        stable=covalent_proxy_signature(completed[0]['native']['native_validation'])==covalent_proxy_signature(completed[1]['native']['native_validation'])
        combined=deepcopy(completed[1]['qualification']);combined['checks'].update(
            source_seed_usable=completed[0]['qualification']['native_usable'],same_fixed_covalent_proxies=stable)
        combined['native_usable']=all(combined['checks'].values())
    else:
        combined={'native_usable':False,'candidate_sha256':sha256(candidate.read_bytes()).hexdigest(),
            'source_assessment':reassess_complete_candidate(source,candidate,code),
            'checks':{'both_native_coordinate_cases_completed':False,'finite_active_proxy_parameters':False}}
        stable=None
    return combined,isolated_candidate_decision(source,candidate,code,combined,stopping),stable


def audit_mixed_recovery(parent_directory,phenix,output,*,single_block_steps=180,timeout_seconds=600):
    """Generate only hard-invalid component candidates; keep the model fixed."""
    from .cif_mixed_native import read_mixed_native,_resolve as parent_resolve
    from .cif_generation import _ideal_seed
    from .cif_numerical_recovery import prepare_graph_generation_source
    from .cif_elbow_input import prepare_elbow_source_dialect_input
    from .cif_source_candidate import generate_source_candidate
    from .cif_candidate_usability import reassess_complete_candidate,qualify_candidate_native
    from .cif_native_validation import inspect_native_bundle
    from .cif_triple_bond_audit import write_component_control_model
    from .ligand_profiles import _parameterized_codes
    if (type(single_block_steps) is not int or not 1<=single_block_steps<=600
            or type(timeout_seconds) is not int or not 1<=timeout_seconds<=600):
        raise ValueError('Require integer optimization steps and deadlines from 1 to 600')
    parent_directory,output=Path(parent_directory),Path(output).absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents) or output.resolve().is_relative_to(parent_directory.resolve()):
        raise ValueError('Require a fresh recovery output outside the parent')
    parent=read_mixed_native(parent_directory)
    if (parent.get('status')!='REVIEW' or parent.get('new_readyset_calls')!=1 or parent.get('new_native_calls')!=0
            or parent.get('source_inputs_preserved') is not True
            or parent.get('readyset',{}).get('execution',{}).get('status')!='COMPLETED'
            or parent['readyset']['execution'].get('returncode')!=0
            or parent['readyset'].get('unchanged_named_heavy_coordinates') is not True):
        raise ValueError('Require preserved completed ReadySet evidence stopped before native reads')
    sources={c:parent_resolve(parent_directory,r) for c,r in parent['inputs']['sources'].items()}
    dictionaries=[parent_resolve(parent_directory,r) for r in parent['effective_dictionaries']]
    required=parent['required_modified_parameterization']
    targets=_targets(required['components'],required['missing'],sources,dictionaries)
    # Validate all selected complete seeds before writing any candidate inputs.
    seeds={c:_ideal_seed(sources[c],c) for c in targets}
    model=parent_resolve(parent_directory,parent['inputs']['model']);active=parent_resolve(parent_directory,parent['inputs']['active_policy'])
    checked=parent_resolve(parent_directory,parent['readyset']['model'])
    from .cif_postmr_readyset import _atoms
    if _atoms(model)!=_atoms(checked):raise ValueError('Preserved ReadySet coordinates differ')
    originals={p:p.read_bytes() for p in [model,active,*sources.values(),*dictionaries]}
    output.mkdir(parents=True);inputs=output/'inputs';inputs.mkdir()
    def copy(path,name):
        p=inputs/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(originals[path]);return _ref(p,output)
    refs={'model':copy(model,'constructed.pdb'),'active_policy':copy(active,'active_policy.phil'),
        'sources':{c:copy(p,'sources/'+c+'.cif') for c,p in sorted(sources.items())},
        'effective_dictionaries':[copy(p,f'effective/{i:03d}.cif') for i,p in enumerate(dictionaries)]}
    summary={'policy_id':parent['policy_id'],'status':parent['status'],'required_modified_parameterization':required,
        'source_authorities':parent['source_authorities'],'source_inputs_preserved':True,
        'readyset_execution':parent['readyset']['execution'],'readyset_named_heavy_coordinates_preserved':True,
        'parent_input_bindings':parent['inputs'],'parent_effective_bindings':parent['effective_dictionaries'],
        'parent_report_sha256':sha256((parent_directory/'mixed_native.json').read_bytes()).hexdigest(),
        'scope':'COMPACT_PARENT_BINDINGS; FULL_PARENT_CAPSULE_PRESERVED_SEPARATELY'}
    _dump(inputs/'parent_summary.json',summary);refs['parent_summary']=_ref(inputs/'parent_summary.json',output)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','targets':targets,'inputs':refs,
        'single_block_steps':single_block_steps,'timeout_seconds':timeout_seconds,'components':{},
        'source_capture':{'status':'NOT_RUN'},'new_source_probe_calls':0,'new_generator_calls':0,'new_native_calls':0,
        'coot_execution':'NOT_RUN','readyset_execution':'NOT_RUN','refinement':'NOT_RUN','model_optimization_requested':False,
        'linked_adoption':'NOT_RUN','cache_writes':'NOT_RUN','production_checkpoint':'NOT_CREATED','mtz_used':False,
        'requires_cif_review':False,'automatic_adoption':False,'policy_authority':'NARestraints',
        'scientific_qualification':'NOT_ASSESSED','captured_code_execution':'NOT_RUN',
        'source_inputs_preserved':True,'model_preserved':True,'unrelated_numerics_preserved':True,
        'deadlines':{'source_probe_seconds':min(timeout_seconds,30),'each_generator_seconds':timeout_seconds,'each_native_seconds':min(timeout_seconds,60),
            'maximum_generator_calls':len(targets),'maximum_native_calls':2*len(targets)},
        'coordinate_decision':{'status':'CONTINUE_WITH_NOTES','selected':'verified_constructed_model',
            'scope':'PRESERVED_CONSTRUCTION_ONLY; NATIVE_FULL_MODEL_USABILITY_PENDING','requires_cif_review':False}}
    for code in targets:
        folder=output/'components'/code;folder.mkdir(parents=True)
        preparation_folder=inputs/'recovery'/code;preparation_folder.mkdir(parents=True)
        source=_resolve(output,refs['sources'][code]);graph=preparation_folder/'graph.cif';consumer=preparation_folder/'consumer.cif'
        graph_preparation=prepare_graph_generation_source(source,code,graph)
        preparation=prepare_elbow_source_dialect_input(source,graph,code,consumer)
        report['components'][code]={'source':refs['sources'][code],'consumer':_ref(consumer,output),
            'graph':_ref(graph,output),'graph_preparation':graph_preparation,'consumer_preparation':preparation,
            'source_seed':seeds[code][1],'generation':{'status':'NOT_RUN'},'coordinate_cases':{},
            'decision':{'status':'NOT_RUN'},'isolated_qualification':{'status':'NOT_RUN'}}
    if phenix is None:return _publish(output,report)
    try:
        capture=capture_candidate_sources(phenix,output/'fresh_sources',timeout_seconds=min(timeout_seconds,30))
        report['new_source_probe_calls']=capture['new_source_probe_calls']
        report['source_capture']={'receipt':_ref(output/'fresh_sources/source_capture.json',output),'record':capture}
        if capture['status']!='FRESH_CANDIDATE_SOURCES_CAPTURED':raise ValueError('Fresh native source capture did not complete')
        report['phenix_version']=phenix.version
        for code in targets:
            case=report['components'][code];folder=output/'components'/code
            source=_resolve(output,case['source']);consumer=_resolve(output,case['consumer'])
            generation=generate_source_candidate(phenix.root,phenix.executables['phenix.python'],phenix.executables['phenix.elbow'],
                capture['api_sources'],consumer,code,folder/'generation',environment=phenix.environment,
                expected_dialect=case['consumer_preparation']['consumer_reader_dialect'],prior_sources=capture['sources'],
                phenix_version=phenix.version,single_block_steps=single_block_steps,timeout_seconds=timeout_seconds)
            case['generation']={'directory':{'anchor':ANCHOR,'path':(folder/'generation').relative_to(output).as_posix()},**generation}
            if 'returncode' in generation.get('execution',{}):report['new_generator_calls']+=1
            if not generation.get('candidate_retained') or not generation.get('candidate'):continue
            candidate=folder/'generation'/generation['candidate']['path']
            case['assessment'],case['candidate_numerical_capability']=_candidate_assessment(source,candidate,code)
            if case['assessment']['candidate_status']!='CANDIDATE_REVIEW' or not case['candidate_numerical_capability']:continue
            models=folder/'models';models.mkdir();seed=models/'source_seed.pdb'
            case['source_seed_preparation']=write_component_control_model(source,code,seed)
            generated=folder/'generation/candidate.pdb'
            if not generated.is_file() or generated.is_symlink():
                case['error']='Complete builder did not retain its exact generated-output PDB';continue
            policy=models/'isolated.phil';policy.write_text('pdb_interpretation {\n secondary_structure.enabled = False\n}\n')
            case['isolated_policy']=_ref(policy,output)
            for name,coordinate_model in [('source_seed',seed),('generated_output',generated)]:
                native=inspect_native_bundle(coordinate_model,[candidate],folder/'native'/name,phenix.executables['phenix.python'],
                    environment=phenix.environment,phenix_version=phenix.version,timeout_seconds=min(timeout_seconds,60),
                    phil_files=[policy],inventory_detail='linked',policy_inventory=True,energy_inventory=True)
                if 'returncode' in native.get('execution',{}):report['new_native_calls']+=1
                item={'model':_ref(coordinate_model,output),'native':{'directory':{'anchor':ANCHOR,
                    'path':Path(native['native_directory']).relative_to(output).as_posix()},**native}}
                case['coordinate_cases'][name]=item
                if _native_ok(native):item['qualification']=qualify_candidate_native(source,candidate,coordinate_model,code,native['native_validation'])
            combined,decision,stable=_combined_decision(source,candidate,code,case['coordinate_cases'],generation.get('stopping',{}).get('status','NOT_REPORTED'))
            case.update(isolated_qualification=combined,decision=decision,same_fixed_covalent_proxies=stable)
        report['status']='MIXED_RECOVERY_ISOLATED_PASS' if all(c['decision'].get('continue_solving') is True for c in report['components'].values()) else 'REVIEW'
    except (ValueError,OSError,KeyError,TypeError) as exc:report.update(status='REVIEW',error=type(exc).__name__+': '+str(exc))
    report['source_inputs_preserved']=all(p.read_bytes()==data for p,data in originals.items())
    if not report['source_inputs_preserved']:raise ValueError('Recovery changed a parent scientific input')
    return _publish(output,report)


def _verify_native(root,item,candidate,policy):
    from .cif_native_validation import _NATIVE_WORKER,NATIVE_POLICY_ID
    from .cif_candidate_usability import native_energy_worker
    capture=item['native'];directory=capture['directory']
    if directory.get('anchor')!=ANCHOR or not _safe(directory.get('path')):raise ValueError('Unsafe isolated native directory')
    folder=root/directory['path']
    if (json.loads((folder/'native_receipt.json').read_bytes())!={k:v for k,v in capture.items() if k!='directory'}
            or (folder/'native_worker.py').read_bytes()!=native_energy_worker(_NATIVE_WORKER).encode()):
        raise ValueError('Isolated native receipt or maintained worker differs')
    expected=[('model',_resolve(root,item['model'])),('dictionary',candidate),('phil',policy)];refs=capture.get('inputs',[])
    if len(refs)!=len(expected):raise ValueError('Incomplete isolated native input scope')
    for i,((role,path),ref) in enumerate(zip(expected,refs)):
        if ref.get('anchor')!='native_directory' or not _safe(ref.get('path')) or ref.get('role')!=role or ref.get('input_index')!=i:
            raise ValueError('Isolated native input role differs')
        data=(folder/ref['path']).read_bytes()
        if data!=path.read_bytes() or len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256']:
            raise ValueError('Isolated native input bytes differ')
    spec={'policy_id':NATIVE_POLICY_ID,'model':refs[0]['path'],'dictionaries':[refs[1]['path']],'phil_files':[refs[2]['path']],
        'phil_namespace_policy':'direct','inventory_detail':'linked','policy_inventory':True,'energy_inventory':True}
    if json.loads((folder/'native_spec.json').read_bytes())!=spec:raise ValueError('Isolated native specification differs')
    if (folder/'native_validation.json').is_file() and json.loads((folder/'native_validation.json').read_bytes())!=capture.get('native_validation'):
        raise ValueError('Isolated native validation differs')
    return capture


def _verify_preparation(root,case,source,code,graph,consumer):
    from tempfile import TemporaryDirectory
    from .cif_numerical_recovery import prepare_graph_generation_source
    from .cif_elbow_input import prepare_elbow_source_dialect_input
    from .cif_postmr_cached_model import cached_preparation_replays
    with TemporaryDirectory(prefix='cif-recovery-reader-') as temporary:
        folder=Path(temporary).resolve();g=folder/'graph.cif';c=folder/'consumer.cif'
        a=prepare_graph_generation_source(source,code,g)
        b=prepare_elbow_source_dialect_input(source,g,code,c)
        if (g.read_bytes()!=graph.read_bytes() or c.read_bytes()!=consumer.read_bytes()
                or not cached_preparation_replays(case['graph_preparation'],a)
                or not cached_preparation_replays(case['consumer_preparation'],b)):
            raise ValueError('Recovery source-reader preparation does not reproduce')


def _verify_generation_spec(root,report,case,folder,consumer,code):
    from .cif_source_candidate import SOURCE_PATHS
    from .cif_stereochemistry_audit import _values,_graph,_coordinates
    from .cif_elbow_chirality import _library_anchor
    from .cif_generation import _ideal_seed
    generation=case['generation']
    if generation.get('component')!=code or generation.get('source_sha256')!=sha256(consumer.read_bytes()).hexdigest():
        raise ValueError('Complete builder component/source binding differs')
    capture=report['source_capture'].get('record',{})
    if capture.get('status')!='FRESH_CANDIDATE_SOURCES_CAPTURED':raise ValueError('Generator lacks fresh selected source evidence')
    if (generation.get('single_block_steps')!=report['single_block_steps']
            or generation.get('phenix_version')!=report.get('phenix_version')
            or generation.get('execution',{}).get('timeout_seconds')!=report['timeout_seconds']):
        raise ValueError('Complete builder budget or version differs')
    pins=capture['sources'];site=_library_anchor(capture['api_sources'])
    by_path={r['path']:r for r in pins}
    if len(pins)!=len(SOURCE_PATHS) or len(by_path)!=len(pins):raise ValueError('Ambiguous generator source pins')
    for name in SOURCE_PATHS:
        path=(site/name).as_posix();row=by_path[path]
        if (folder/('api_sources/'+name+'.txt')).read_bytes()!=(root/report['source_capture']['receipt']['path']).parent.joinpath(row['snapshot']).read_bytes():
            raise ValueError('Complete builder sources differ from fresh capture')
    if (folder/'source_ideal.pdb').read_text()!=_ideal_seed(consumer,code)[0]:raise ValueError('Complete builder seed differs')
    spec_path=folder/'candidate_spec.json'
    if spec_path.is_file():
        caps=generation['generator_capabilities'];flags=caps['selected_aliases'];definitions=caps['supported_option_definitions']
        step=next((v for v in ['--opt_steps','--opt-steps'] if definitions.get(v) is True),None)
        args=[f"{flags['id']}={code}",f"{flags['output']}=candidate",f"{flags['template']}=source_ideal.pdb",
            f"{flags['initial_geometry']}=source_ideal.pdb",f"{flags['add_hydrogens']}=False",
            f"{flags['source_state_preservation']}=low",f"{flags['chiral']}=retain",flags['opt'],f'{step}={report["single_block_steps"]}']
        v=_values(consumer,code);elements,bonds,charges,_=_graph(v);_,xyz=_coordinates(v,source=True)
        order={'SINGLE':1,'DOUBLE':2,'TRIPLE':3,'AROMATIC':1.5,'DELOCALIZED':1.5}
        installed_root=Path(capture['historical_root'])
        expected={'component':code,'library':str(installed_root/site),'installation_root':str(installed_root),'arguments':args,
            'sources':[{'installed':str(installed_root/(site/name)),'sha256':by_path[(site/name).as_posix()]['sha256'],
                'module':name[:-3].replace('/','.')} for name in SOURCE_PATHS],
            'declared_charge_control':{'component':code,'dialect':case['consumer_preparation']['consumer_reader_dialect'],
                'elements':elements,'coordinates':xyz,'charges':{n:int(q) for n,q in charges.items()},
                'bonds':[{'atoms':list(p),'order':order[o]} for p,o in bonds.items()]}}
        expected=json.loads(json.dumps(expected))
        if step is None or generation.get('arguments')!=args or json.loads(spec_path.read_bytes())!=expected:
            raise ValueError('Complete builder source-object specification differs')
    elif generation.get('candidate') or 'returncode' in generation.get('execution',{}):
        raise ValueError('Complete builder execution lacks its source-object specification')


def _verify_coordinate_models(root,case,source,code,generation_folder,policy):
    from tempfile import TemporaryDirectory
    from .cif_triple_bond_audit import write_component_control_model
    cases=case['coordinate_cases']
    if policy.read_text()!='pdb_interpretation {\n secondary_structure.enabled = False\n}\n':raise ValueError('Isolated policy differs')
    if _resolve(root,cases['generated_output']['model'])!=generation_folder/'candidate.pdb':raise ValueError('Generated coordinate origin differs')
    with TemporaryDirectory(prefix='cif-recovery-seed-reader-') as temporary:
        seed=Path(temporary).resolve()/'source_seed.pdb';preparation=write_component_control_model(source,code,seed)
        if preparation!=case['source_seed_preparation'] or seed.read_bytes()!=_resolve(root,cases['source_seed']['model']).read_bytes():
            raise ValueError('Source-seed isolated model differs')


def read_mixed_recovery(directory):
    """Read standalone frozen evidence; never consult or execute captured sources."""
    from .cif_postmr_cached_model import cached_preparation_replays
    from .cif_candidate_usability import reassess_complete_candidate,qualify_candidate_native
    from .cif_generation import _ideal_seed
    from .cif_source_candidate import WORKER,SOURCE_PATHS
    from .ligand_profiles import _parameterized_codes
    root=Path(directory)
    if any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('Unsafe recovery directory')
    report=json.loads((root/REPORT).read_bytes())
    if (report.get('policy_id')!=POLICY_ID or report.get('status') not in {'PREPARED_ONLY','REVIEW','MIXED_RECOVERY_ISOLATED_PASS'}
            or report.get('automatic_adoption') is not False or report.get('requires_cif_review') is not False
            or any(report.get(k)!='NOT_RUN' for k in ['coot_execution','readyset_execution','refinement','linked_adoption','cache_writes','captured_code_execution'])
            or report.get('model_optimization_requested') is not False or report.get('scientific_qualification')!='NOT_ASSESSED'
            or report.get('production_checkpoint')!='NOT_CREATED' or report.get('mtz_used') is not False):
        raise ValueError('Recovery claims unsupported scope')
    outputs=report['outputs']
    if len(outputs)!=len({r['path'] for r in outputs}):raise ValueError('Duplicate recovery artifact')
    for ref in outputs:_resolve(root,ref)
    actual=set()
    for p in root.rglob('*'):
        if p.is_symlink():raise ValueError('Recovery contains a symlink')
        if p.is_file() and p!=root/REPORT and p.suffix not in {'.pickle','.pkl','.pyc'}:actual.add(p.relative_to(root).as_posix())
    if actual!={r['path'] for r in outputs}:raise ValueError('Recovery artifact inventory differs')
    refs=report['inputs'];summary=json.loads(_resolve(root,refs['parent_summary']).read_bytes())
    def bound(a,b):return a.get('sha256')==b.get('sha256') and a.get('size')==b.get('size')
    if (not bound(refs['model'],summary['parent_input_bindings']['model'])
            or not bound(refs['active_policy'],summary['parent_input_bindings']['active_policy'])
            or set(refs['sources'])!=set(summary['parent_input_bindings']['sources'])
            or any(not bound(r,summary['parent_input_bindings']['sources'][c]) for c,r in refs['sources'].items())
            or len(refs['effective_dictionaries'])!=len(summary['parent_effective_bindings'])
            or any(not bound(a,b) for a,b in zip(refs['effective_dictionaries'],summary['parent_effective_bindings']))):
        raise ValueError('Recovery parent bindings differ')
    sources={c:_resolve(root,r) for c,r in refs['sources'].items()};dictionaries=[_resolve(root,r) for r in refs['effective_dictionaries']]
    required=summary['required_modified_parameterization'];targets=_targets(required['components'],required['missing'],sources,dictionaries)
    if report['targets']!=targets or set(report['components'])!=set(targets):raise ValueError('Recovery target scope differs')
    for code,case in report['components'].items():
        if case['source']!=refs['sources'][code] or case['source_seed']!=_ideal_seed(sources[code],code)[1]:raise ValueError('Recovery source seed differs')
        consumer=_resolve(root,case['consumer']);graph=_resolve(root,case['graph'])
        _verify_preparation(root,case,sources[code],code,graph,consumer)
        generation=case['generation']
        if 'directory' not in generation:
            if generation!={'status':'NOT_RUN'} or case['coordinate_cases'] or case['decision']!={'status':'NOT_RUN'}:
                raise ValueError('Recovery has unexplained component evidence')
            continue
        directory=generation['directory']
        if directory.get('anchor')!=ANCHOR or not _safe(directory.get('path')):raise ValueError('Unsafe generation directory')
        folder=root/directory['path'];record=json.loads((folder/'source_candidate_receipt.json').read_bytes())
        if record!={k:v for k,v in generation.items() if k!='directory'} or (folder/'candidate_worker.py').read_text()!=WORKER:
            raise ValueError('Complete candidate receipt or maintained worker differs')
        if 'diagnostic' in generation:
            from .cif_source_candidate import candidate_generation_diagnostic
            if generation['diagnostic']!=candidate_generation_diagnostic(generation):
                raise ValueError('Complete candidate diagnostic differs')
        if (folder/'source.cif').read_bytes()!=consumer.read_bytes():raise ValueError('Complete builder source differs')
        _verify_generation_spec(root,report,case,folder,consumer,code)
        if generation.get('candidate'):
            ref=generation['candidate']
            if ref.get('anchor')!='candidate_directory' or not _safe(ref.get('path')):raise ValueError('Unsafe generated candidate reference')
            candidate=folder/ref['path'];data=candidate.read_bytes()
            if len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Generated candidate differs')
            assessment,capability=_candidate_assessment(sources[code],candidate,code)
            if not cached_preparation_replays(case['assessment'],assessment) or case['candidate_numerical_capability']!=capability:
                raise ValueError('Recovered candidate reassessment differs')
            if case['coordinate_cases']:
                if set(case['coordinate_cases'])!={'source_seed','generated_output'}:raise ValueError('Incomplete isolated coordinate scope')
                policy=_resolve(root,case['isolated_policy'])
                _verify_coordinate_models(root,case,sources[code],code,folder,policy)
                for item in case['coordinate_cases'].values():
                    native=_verify_native(root,item,candidate,policy)
                    if _native_ok(native):
                        q=qualify_candidate_native(sources[code],candidate,_resolve(root,item['model']),code,native['native_validation'])
                        if not cached_preparation_replays(item.get('qualification'),q):raise ValueError('Isolated qualification does not reproduce')
                    elif 'qualification' in item:raise ValueError('Incomplete native capture claims qualification')
                combined,decision,stable=_combined_decision(sources[code],candidate,code,case['coordinate_cases'],generation.get('stopping',{}).get('status','NOT_REPORTED'))
                if (not cached_preparation_replays(case['isolated_qualification'],combined) or case['decision']!=decision
                        or case['same_fixed_covalent_proxies']!=stable):raise ValueError('Isolated candidate decision does not reproduce')
    if report['source_capture'].get('record'):_verify_source_capture(root,report['source_capture'])
    actual_generator=sum('returncode' in c['generation'].get('execution',{}) for c in report['components'].values())
    actual_native=sum('returncode' in v['native'].get('execution',{}) for c in report['components'].values() for v in c['coordinate_cases'].values())
    actual_probe=report['source_capture'].get('record',{}).get('new_source_probe_calls',0)
    if (report['new_generator_calls']!=actual_generator or report['new_native_calls']!=actual_native or report['new_source_probe_calls']!=actual_probe):
        raise ValueError('Recovery execution counters differ from their evidence')
    if report['status']=='PREPARED_ONLY' and (any(report[k]!=0 for k in ['new_source_probe_calls','new_generator_calls','new_native_calls'])
            or report['source_capture']!={'status':'NOT_RUN'} or any(c['generation']!={'status':'NOT_RUN'} for c in report['components'].values())):
        raise ValueError('Prepared recovery claims native execution')
    if report['status']=='MIXED_RECOVERY_ISOLATED_PASS' and (report['source_capture'].get('record',{}).get('status')!='FRESH_CANDIDATE_SOURCES_CAPTURED'
            or report['new_source_probe_calls']!=1 or report['new_native_calls']!=2*len(targets) or report['new_generator_calls']!=len(targets)
            or not all(set(c['coordinate_cases'])=={'source_seed','generated_output'}
                and all(_native_ok(v['native']) and v.get('qualification',{}).get('native_usable') is True for v in c['coordinate_cases'].values())
                and c['decision'].get('continue_solving') is True and c['isolated_qualification'].get('native_usable') is True for c in report['components'].values())):
        raise ValueError('Incomplete isolated recovery PASS evidence')
    return report
