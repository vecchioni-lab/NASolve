"""Round-local explicit native compatibility code and read-only evidence.

AutoRefine remains the executor and checkpoint owner. Native source validation
belongs to the frozen helper; saved records never execute Python or Phenix.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from .campaign_records import path_in, read_record, write_record
from .refinement_inputs import _directory, _bound_path
from .cif_parallelity_kernel import parallelity_parameters
from .cif_refinement_output import validate_output_observations

LEGACY_POLICY_ID = 'round-local-parallelity-execution-v1'
V2_POLICY_ID = 'round-local-parallelity-execution-v2'
V3_POLICY_ID = 'round-local-parallelity-execution-v3'
V4_POLICY_ID = 'round-local-parallelity-execution-v4'
POLICY_ID = V3_POLICY_ID  # Ordinary requests keep their existing default.
ADMISSION_REFUSAL_POLICY_ID = 'preflight-admission-refusal-v1'
# Filled from the qualified C297 checkpoint; historical readers keep these exact
# identities even when a future policy uses different native/helper sources.
_SOURCE_DIGESTS = {'cif_parallelity_kernel.py': '074c51faa384856f014631c72d97a14237ec3b7b6d833d405ca92aa02b507568', 'cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f', 'cif_refinement_runtime.py': '5b9329c988b3c07c9c3da4586ecce03c6751955fc02ccdf2f35b42088eaa2900', 'data/parallelity-native-profile.json': '5fe3c6657c78e2b85ea6bab3da68f4e79a3f91a2b1498f745be77f1080a2db28'}
_V2_SOURCE_DIGESTS = {'cif_parallelity_kernel.py': '074c51faa384856f014631c72d97a14237ec3b7b6d833d405ca92aa02b507568', 'cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f', 'cif_refinement_runtime.py': '78a7afd54b7f5ca835ad3e42f0a823aea3fb56eda59b1fe643716fec78593741', 'cif_refinement_output.py': '0e231d2d8502b3df7982688709bc9cc9322d2bde2becffcc7962250e9ebc08b5', 'data/parallelity-native-profile.json': '0b447a84abff9ef3efbe1d9481d918581a06299023ac0b6a1d78927c7cd7d3ee'}
_CURRENT_SOURCE_DIGESTS = {'cif_parallelity_kernel.py': '074c51faa384856f014631c72d97a14237ec3b7b6d833d405ca92aa02b507568', 'cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f', 'cif_refinement_runtime.py': '6698585c1da6225895dd1d639554321ccab695eda1b4366d243deb39106c3503', 'cif_refinement_output.py': 'd1b6ff5a6c47407626be27745f30fda0dcede6b56666b9f30abc334d023f4533', 'cif_refinement_sites.py': 'd690273cc3de2b54594d763674e9716177cf2c178f36ab55ca4d29686644a340', 'data/parallelity-native-profile.json': 'f7aa742b2f00026b6bfa63695702e2b74fb65d5e78b598aec654abcea249758b'}
_V4_SOURCE_DIGESTS = dict(_CURRENT_SOURCE_DIGESTS, **{'cif_refinement_runtime.py': '5611e658cb79e92996f24e92b1a13055e69bede04f1ab909a60216baea03b3e3', 'cif_refinement_output.py': '7f4220abd718b6396e3e196d72abea4343c6f5b45187aa51b1dc6efaa651fc21', 'cif_refinement_sites.py': '7643d29e113b487975a0a47ef21686bc19627693e7ec724cc627aa82d07baac8'})
_SOURCES = {LEGACY_POLICY_ID:_SOURCE_DIGESTS, V2_POLICY_ID:_V2_SOURCE_DIGESTS,
            V3_POLICY_ID:_CURRENT_SOURCE_DIGESTS, V4_POLICY_ID:_V4_SOURCE_DIGESTS}
_RUNTIME_POLICIES = {LEGACY_POLICY_ID:'explicit-native-parallelity-refinement-v1',
                     V2_POLICY_ID:'explicit-native-parallelity-refinement-v2',
                     V3_POLICY_ID:'explicit-native-parallelity-refinement-v3',
                     V4_POLICY_ID:'explicit-native-parallelity-refinement-v4'}
_V2_ENTRY = b'''from pathlib import Path
import sys
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'code'))
from _nasolve_refinement.cif_refinement_runtime import run_compatible_refinement
phase=sys.argv[1]
if phase not in ('preflight','refine'):raise ValueError('Unknown native execution phase')
run_compatible_refinement(sys.argv[2:],evidence_directory=root/phase)
'''
_ENTRY = b'''from pathlib import Path
import json,sys
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'code'))
from _nasolve_refinement.cif_refinement_runtime import run_compatible_refinement
phase=sys.argv[1]
if phase not in ('preflight','refine'):raise ValueError('Unknown native execution phase')
request=json.loads((root/'request.json').read_text())
sites=[{k:row[k] for k in ('site','component')} for row in request.get('chemistry_projections',[])]
run_compatible_refinement(sys.argv[2:],evidence_directory=root/phase,chemistry_sites=sites)
'''

_ENTRIES = {LEGACY_POLICY_ID:_V2_ENTRY, V2_POLICY_ID:_V2_ENTRY, V3_POLICY_ID:_ENTRY, V4_POLICY_ID:_ENTRY}
_CHEMISTRY_POLICIES = (V3_POLICY_ID, V4_POLICY_ID)


def _need(value, message='Invalid explicit parallelity execution evidence'):
    if not value: raise ValueError(message)


def _digest(data): return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def _root(checkpoint): return _directory(checkpoint)+'/parallelity_runtime'


def _code(policy=None):
    """Freeze qualified bytes; default v3 remains exact after a helper upgrade."""
    policy=POLICY_ID if policy is None else policy
    _need(isinstance(policy,str) and policy in (V3_POLICY_ID,V4_POLICY_ID),
          'Unsupported new native execution policy')
    package=Path(__file__).parent;frozen={}
    if policy==V3_POLICY_ID:
        frozen=json.loads((package/'data/refinement-runtime-v3-sources.json').read_text())
        _need(type(frozen) is dict and set(frozen)=={
            'cif_refinement_runtime.py','cif_refinement_output.py','cif_refinement_sites.py'}
            and all(type(value) is str for value in frozen.values()),
            'Invalid frozen v3 helper source set')
    expected=_SOURCES[policy]
    values={name:frozen[name].encode('utf-8') if name in frozen else (package/name).read_bytes()
            for name in expected}
    _need(all(_digest(value)==expected[name] for name,value in values.items()),
          'Helper differs from the qualified runtime policy')
    return {'entry.py':_ENTRIES[policy],'code/_nasolve_refinement/__init__.py':b'',
            **{'code/_nasolve_refinement/'+name:value for name,value in values.items()}}


def _expected_code(policy=None):
    policy=POLICY_ID if policy is None else policy
    _need(isinstance(policy,str) and policy in _SOURCES,'Unknown native execution policy')
    return {'entry.py':_digest(_ENTRIES[policy]),'code/_nasolve_refinement/__init__.py':_digest(b''),
            **{'code/_nasolve_refinement/'+n:h for n,h in _SOURCES[policy].items()}}


def read_execution_request(run, reference, *, checkpoint):
    root=_root(checkpoint)
    _need(isinstance(reference,dict) and reference.get('anchor')=='run'
          and reference.get('relative_path')==root+'/request.json')
    path=_bound_path(reference,'parallelity execution request',run)
    record=read_record(path)
    fields = set(record) - ({'chemistry_projections'} if record.get('policy_id') in _CHEMISTRY_POLICIES else set())
    _need(fields in ({'schema_version','policy_id','checkpoint','parent','inputs','command','code','record_sha256'}, {'schema_version','policy_id','checkpoint','parent','inputs','command','code','record_sha256','preflight_mode','macro_cycles'})
          and type(record['schema_version']) is int and record['schema_version']==1
          and isinstance(record['policy_id'],str) and record['policy_id'] in _SOURCES
          and record['checkpoint']==checkpoint
          and isinstance(record['parent'],str) and isinstance(record['inputs'],list)
          and record['inputs'] and isinstance(record['command'],list) and len(record['command'])>1
          and all(isinstance(a,str) and a for a in record['command'])
          and isinstance(record['code'],dict) and set(record['code'])==set(_expected_code(record['policy_id'])))
    if 'preflight_mode' in record:
        _need(record['preflight_mode'] in ('native-model-zero-cycle-v1','native-model-zero-cycle-isolated-v1')
              and type(record['macro_cycles']) is int and record['macro_cycles']>0)
    if record['policy_id']!=LEGACY_POLICY_ID:
        _need(record.get('preflight_mode')=='native-model-zero-cycle-isolated-v1',
              'Current native execution requires isolated zero-cycle preflight')
    if 'chemistry_projections' in record:
        from .refinement_chemistry import _projection_scope
        _need(bool(record['chemistry_projections']), 'Empty requested chemistry scope')
        _projection_scope(run,record['chemistry_projections'])
    path_in(run,reference['relative_path'])
    for item in record['inputs']:_bound_path(item,'parallelity refinement input',run)
    for name,digest in _expected_code(record['policy_id']).items():
        ref=record['code'][name]
        _need(isinstance(ref,dict) and ref.get('anchor')=='run'
              and ref.get('relative_path')==root+'/'+name and ref.get('sha256')==digest,
              'Frozen parallelity runtime code differs from its qualified policy')
        path_in(run,root+'/'+name)
        _bound_path(ref,'parallelity runtime code',run)
    return record


def prepare_execution(run, *, checkpoint, parent, inputs, command, python_executable, macro_cycles, chemistry_projections=None, runtime_policy=None):
    """Freeze only the small qualified helper; retain all original input files."""
    from .checkpoints import _file_reference
    policy=POLICY_ID if runtime_policy is None else runtime_policy
    _need(runtime_policy is None or (isinstance(policy,str) and policy in (V3_POLICY_ID,V4_POLICY_ID)),
          'Unsupported new native execution policy')
    _need(isinstance(command,list) and len(command)>1)
    inputs=[Path(p).expanduser().resolve() for p in inputs]
    _need(command[1:1+len(inputs)]==[str(p) for p in inputs],
          'Runtime input order differs from the native command')
    if chemistry_projections is not None:
        from .refinement_chemistry import _projection_scope
        _projection_scope(run,chemistry_projections)
    payload=_code() if runtime_policy is None else _code(policy)
    root=path_in(run,_root(checkpoint));root.mkdir()
    code={}
    for name,data in payload.items():
        target=path_in(root,name);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as handle:handle.write(data)
        code[name]=_file_reference(target,run)
    request=root/'request.json'
    write_record(request,dict(schema_version=1,policy_id=policy,checkpoint=checkpoint,
        parent=parent,preflight_mode='native-model-zero-cycle-isolated-v1',macro_cycles=macro_cycles,
        inputs=[_file_reference(Path(p),run) for p in inputs],
        command=list(command),code=code,
        **({'chemistry_projections':chemistry_projections} if chemistry_projections else {})))
    reference=_file_reference(request,run)
    prefix=[str(python_executable),'-B',str(root/'entry.py')]
    request_record=read_execution_request(run,reference,checkpoint=checkpoint)
    return reference,[*prefix,'preflight',*_preflight_arguments(request_record)],[*prefix,'refine',*command[1:]]


def _parameters(value):
    _need(isinstance(value,dict) and set(value)=={'site_count','proxies'}
          and isinstance(value['proxies'],list))
    try:
        rows=parallelity_parameters([SimpleNamespace(**p) for p in value['proxies']],site_count=value['site_count'])
    except (TypeError,AttributeError) as exc:raise ValueError('Malformed saved plane parameters') from exc
    _need(rows==value['proxies'])


def _preflight_arguments(request):
    arguments=list(request['command'][1:])
    if 'preflight_mode' not in request:return ['--dry_run',*arguments]
    if request['preflight_mode']=='native-model-zero-cycle-isolated-v1':
        _need(arguments.count('output.prefix=refined')==1,'Unknown refinement output-prefix contract')
        arguments=['output.prefix=parallelity_runtime/preflight/native' if a=='output.prefix=refined' else a for a in arguments]
    return [*arguments,'refinement.dry_run=True']


def validate_runtime_choice(enabled, python_executable):
    """Validate the explicit choice before either owner allocates work."""
    if type(enabled) is not bool:
        raise ValueError('Native parallelity correction must be explicitly enabled or disabled')
    if enabled and (python_executable is None or not Path(python_executable).is_file()):
        raise ValueError('Explicit plane-force correction requires the configured phenix.python')
    if enabled:
        try:_code()
        except OSError as exc:
            raise ValueError('Required qualified runtime source is unavailable: '+str(exc)) from exc


def require_runtime_continuation(registry, selected, enabled):
    if not enabled and requires_checked_plane_forces(registry, selected):
        raise ValueError(
            'This checkpoint descends from checked plane-force refinement; '
            'continue explicitly with --checked-plane-forces. No new round was started.')


def requires_checked_plane_forces(registry, selected):
    """Reuse established ancestry validation; manual edits retain their history."""
    items=registry.get('checkpoints',[])
    corrected={item.get('id') for item in items if isinstance(item,dict)
               and isinstance(item.get('outputs'),dict) and 'parallelity_execution' in item['outputs']}
    if not corrected:return False
    from .checkpoint_candidate import _lineage,CheckpointCandidateError
    try:return bool(corrected.intersection(_lineage(registry,selected)))
    except CheckpointCandidateError as exc:raise ValueError(str(exc)) from exc


def _phase(run, root, phase, code, request, *, require_complete):
    """Interpret already-hash-checked files, never launch the native consumer."""
    result_path=path_in(run,root+'/'+phase+'/result.json')
    if not result_path.is_file():
        _need(not require_complete,'Successful native execution lacks runtime evidence')
        return None
    result=json.loads(result_path.read_text())
    expected_arguments=_preflight_arguments(request) if phase=='preflight' else request['command'][1:]
    if phase=='preflight' and 'preflight_mode' not in request:
        _need(not require_complete,'Legacy argument-only preflight cannot qualify refinement')
    _need(isinstance(result,dict) and result.get('schema_version')==1
          and type(result.get('schema_version')) is int
          and type(result.get('pid')) is int and result['pid']>0
          and type(result.get('parent_pid')) is int and result['parent_pid']>=0
          and result.get('policy_id')==_RUNTIME_POLICIES[request['policy_id']]
          and result.get('arguments')==expected_arguments
          and result.get('scientific_approval')=='NOT_RUN')
    _need(result.get('status') in ('RUNNING','FAILED','COMPLETE'))
    if require_complete:
        _need(result['status']=='COMPLETE' and result.get('binding_restored') is True)
    if result['status']=='FAILED':
        error=result.get('error')
        _need(isinstance(error,dict) and set(error)=={'type','message'}
              and all(isinstance(v,str) for v in error.values()))
    if result['status']=='COMPLETE':
        _need(result.get('binding_restored') is True)
        stats=result.get('parent_kernel_statistics')
        keys={'successful_calls','gradient_calls','energy_only_calls','maximum_proxy_count'}
        _need(isinstance(stats,dict) and set(stats)==keys|{'policy_id'}
              and stats['policy_id']=='native-parallelity-kernel-adapter-v1'
              and all(type(stats[k]) is int and stats[k]>=0 for k in keys)
              and stats['successful_calls']==stats['gradient_calls']+stats['energy_only_calls'])
        profile_path=_bound_path(code['code/_nasolve_refinement/data/parallelity-native-profile.json'],
                                 'qualified native profile',run)
        _need(result.get('native_profile')==json.loads(profile_path.read_text()))
        _need(result.get('dry_run') is (phase=='preflight'))
        cycles=result.get('macro_cycles');_need(type(cycles) is int and (cycles==0 if phase=='preflight' else cycles==request.get('macro_cycles')))
        labels=result.get('atom_labels');_need(isinstance(labels,list) and all(isinstance(x,str) for x in labels))
        _parameters(dict(site_count=len(labels),proxies=result.get('parallelity_parameters')))
        if request['policy_id']!=LEGACY_POLICY_ID:
            _need(result.get('output_binding_restored') is True)
            validate_output_observations(result.get('output_synchronization'),
                dry_run=phase=='preflight',atom_count=len(labels))
        if request['policy_id'] in _CHEMISTRY_POLICIES:
            from .cif_refinement_sites import validate_phase_observation
            sites=[{k:row[k] for k in ('site','component')} for row in request.get('chemistry_projections',[])]
            validate_phase_observation(result,sites,dry_run=phase=='preflight',labels=labels)
        names=result.get('usage_observations');_need(isinstance(names,list) and all(isinstance(n,str) for n in names) and names==sorted(set(names)))
        files=sorted(p.name for p in path_in(run,root+'/'+phase+'/calls').iterdir())
        _need(files==names,'Runtime usage membership differs')
        parent_calls=0;final_observed=not result['parallelity_parameters']
        for name in names:
            row=json.loads(path_in(run,root+'/'+phase+'/calls/'+name).read_text())
            _need(isinstance(row,dict) and set(row)=={'pid','parent_pid','parameter_sha256','parameters'}
                  and type(row['pid']) is int and row['pid']>0
                  and type(row['parent_pid']) is int and row['parent_pid']>=0)
            _parameters(row['parameters']);digest=_digest(_canonical(row['parameters']))
            _need(row['parameter_sha256']==digest and name==str(row['pid'])+'-'+digest+'.json')
            parent_calls+=row['pid']==result['pid']
            final_observed|=(row['parameters']==dict(site_count=len(labels),proxies=result['parallelity_parameters']))
        _need(parent_calls<=stats['successful_calls'] and final_observed,
              'Completed native parameter state lacks usage evidence')
    return result


def validate_preflight(run, reference, *, checkpoint):
    request=read_execution_request(run,reference,checkpoint=checkpoint)
    return _phase(run,_root(checkpoint),'preflight',request['code'],request,require_complete=True)


def _refusal(value):
    """A stopped controller decision, never a native return code or permission."""
    _need(isinstance(value,dict) and set(value)=={'stage','error'}
          and value['stage']=='preflight_evidence'
          and isinstance(value['error'],dict) and set(value['error'])=={'type','message'}
          and all(isinstance(v,str) for v in value['error'].values())
          and bool(value['error']['type']), 'Invalid preflight admission refusal')
    return value


def _phase_paths(run, root, phase):
    """Inventory exact evidence even when its scientific content was refused."""
    folder=path_in(run,root+'/'+phase);files=[]
    if folder.exists():
        _need(folder.is_dir(),'Native runtime phase is not a directory')
        for p in sorted(folder.rglob('*')):
            _need(not p.is_symlink(),'Symbolic link in runtime evidence')
            if p.is_file():files.append(p)
    return files


def finish_execution(run, reference, *, checkpoint, preflight_returncode, refinement_returncode,
                     admission_refusal=None):
    """Seal stopped results; an explicit refusal preserves native success as zero.

    Only the execution owner calls this after its subprocess has stopped. This
    records a decision; it does not grant admission, authorize recovery or repair
    invalid preflight contents. Historical schema-1 outcomes retain their meaning.
    """
    from .checkpoints import _file_reference
    request=read_execution_request(run,reference,checkpoint=checkpoint);root=_root(checkpoint)
    _need(type(preflight_returncode) is int and (type(refinement_returncode) is int or refinement_returncode is None))
    refused=admission_refusal is not None
    if refused:
        _refusal(admission_refusal)
        _need(preflight_returncode==0 and refinement_returncode is None,
              'Admission refusal requires successful preflight and unlaunched refinement')
    else:
        _need((refinement_returncode is None)==(preflight_returncode!=0))
    phases=[]
    for phase,returncode in [('preflight',preflight_returncode),('refine',refinement_returncode)]:
        folder=path_in(run,root+'/'+phase)
        if returncode is None:_need(not folder.exists(),'Unrequested native refinement evidence exists')
        elif not refused:_phase(run,root,phase,request['code'],request,require_complete=returncode==0)
        phases.append(dict(name=phase,returncode=returncode,
                           files=[_file_reference(p,run) for p in _phase_paths(run,root,phase)]))
    target=path_in(run,root+'/execution.json')
    write_record(target,dict(schema_version=2 if refused else 1,
        policy_id=request['policy_id'],checkpoint=checkpoint,request=reference,phases=phases,
        **(dict(outcome_policy_id=ADMISSION_REFUSAL_POLICY_ID,
                refinement_status='NOT_LAUNCHED',admission_refusal=admission_refusal) if refused else {})))
    return _file_reference(target,run)


def validate_execution(run, reference, *, checkpoint, parent=None, usable=False):
    root=_root(checkpoint)
    _need(isinstance(reference,dict) and reference.get('anchor')=='run'
          and reference.get('relative_path')==root+'/execution.json')
    path_in(run,reference['relative_path'])
    record=read_record(_bound_path(reference,'parallelity execution receipt',run))
    refused=record.get('schema_version')==2
    fields={'schema_version','policy_id','checkpoint','request','phases','record_sha256'}
    if refused:
        fields|={'outcome_policy_id','refinement_status','admission_refusal'}
        _need(record.get('outcome_policy_id')==ADMISSION_REFUSAL_POLICY_ID
              and record.get('refinement_status')=='NOT_LAUNCHED',
              'Unknown preflight admission outcome policy')
        _refusal(record.get('admission_refusal'))
    _need(set(record)==fields
          and type(record['schema_version']) is int and record['schema_version'] in (1,2)
          and isinstance(record['policy_id'],str) and record['policy_id'] in _SOURCES
          and record['checkpoint']==checkpoint
          and isinstance(record['phases'],list) and len(record['phases'])==2)
    request=read_execution_request(run,record['request'],checkpoint=checkpoint)
    _need(record['policy_id']==request['policy_id'],'Native execution policies differ')
    if parent is not None:_need(request['parent']==parent,'Runtime parent checkpoint differs')
    codes=[]
    for expected,row in zip(('preflight','refine'),record['phases']):
        _need(isinstance(row,dict) and set(row)=={'name','returncode','files'} and row['name']==expected
              and (type(row['returncode']) is int or row['returncode'] is None) and isinstance(row['files'],list))
        codes.append(row['returncode']);names=[]
        prefix=root+'/'+expected+'/'
        for ref in row['files']:
            _need(isinstance(ref,dict) and ref.get('anchor')=='run' and isinstance(ref.get('relative_path'),str)
                  and ref['relative_path'].startswith(prefix))
            names.append(ref['relative_path']);path_in(run,ref['relative_path']);_bound_path(ref,'native parallelity observation',run)
        folder=path_in(run,root+'/'+expected)
        current=[p.relative_to(run).as_posix() for p in _phase_paths(run,root,expected)]
        _need(names==sorted(set(names))==current,'Runtime evidence file membership differs')
        if row['returncode'] is None:_need(not folder.exists())
        elif not refused:_phase(run,root,expected,request['code'],request,require_complete=row['returncode']==0)
    if refused:
        _need(type(codes[0]) is int and codes==[0,None],
              'Refused admission cannot represent a launched refinement')
    else:
        _need(type(codes[0]) is int and ((codes[1] is None)==(codes[0]!=0)))
    if usable:_need(codes==[0,0],'Usable checkpoint requires both native runtime stages to complete')
    return record


def validate_checkpoint_execution(run, item, registry):
    outputs=item.get('outputs')
    if isinstance(outputs,dict) and 'parallelity_execution' in outputs:
        record=validate_execution(run,outputs['parallelity_execution'],checkpoint=item.get('id'),
                                  parent=item.get('parent'),usable=item.get('usable') is True)
        request=read_execution_request(run,record['request'],checkpoint=item['id'])
        from .checkpoints import _ref_path
        from .refinement_inputs import validate_checkpoint_refinement_inputs
        parents=[p for p in registry['checkpoints'] if p.get('id')==item.get('parent')]
        _need(len(parents)==1,'Runtime parent checkpoint missing or ambiguous')
        paths=[_bound_path(ref,'runtime input',run) for ref in request['inputs']]
        expected=[_ref_path(item['observations'],'runtime observations',run),
                  _ref_path(parents[0]['model'],'runtime parent model',run)]
        restraints=[_ref_path(r,'runtime restraint',run) for r in item['restraints']]
        adaptation=validate_checkpoint_refinement_inputs(run,item)
        if adaptation:
            for row in adaptation['adaptations']:
                restraints[row['index']]=_ref_path(row['execution'],'runtime execution restraint',run)
        expected.extend(restraints)
        _need(paths[:len(expected)]==expected,'Runtime inputs differ from checkpoint ancestry or ordered restraints')
        tail=paths[len(expected):]
        parameter=path_in(run,_directory(item['id'])+'/autorefine.params')
        _need(tail==[parameter] or (item.get('phases') is not None and
              tail==[_ref_path(item['phases'],'runtime phase',run),parameter]),
              'Runtime parameter/phase inputs differ from their round')
        if (item.get('usable') is True and request['policy_id'] in _CHEMISTRY_POLICIES
                and request.get('chemistry_projections')):
            result=_phase(run,_root(item['id']),'refine',request['code'],request,require_complete=True)
            if result.get('chemistry_model') is not None:
                data=_ref_path(item['model'],'refinement model',run).read_bytes()
                _need(result['chemistry_model']==dict(sha256=_digest(data),size=len(data)),
                      'Observed native output differs from the checkpoint model')
        return record


def read_execution_chemistry(run, reference, *, checkpoint, parent, model):
    """Read sealed actual-manager evidence without launching or adopting anything."""
    record=validate_execution(run,reference,checkpoint=checkpoint,parent=parent,usable=True)
    request=read_execution_request(run,record['request'],checkpoint=checkpoint)
    if request['policy_id'] not in _CHEMISTRY_POLICIES or not request.get('chemistry_projections'):
        return None
    result=_phase(run,_root(checkpoint),'refine',request['code'],request,require_complete=True)
    from .refinement_chemistry import _projection_scope, _observed_readback
    _,projections=_projection_scope(run,request['chemistry_projections'])
    data=Path(model).read_bytes()
    if result['chemistry_observation']['status']=='OBSERVED':
        _need(result['chemistry_model']==dict(sha256=_digest(data),size=len(data)),
              'Observed native output differs from the checkpoint model')
    return _observed_readback(data,projections,result['chemistry_observation'])
