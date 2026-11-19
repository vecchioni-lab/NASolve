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
V5_POLICY_ID = 'round-local-counted-execution-v5'
V6_POLICY_ID = 'round-local-counted-execution-v6'
V7_POLICY_ID = 'round-local-counted-execution-v7'
V8_POLICY_ID = 'round-local-counted-execution-v8'
V9_POLICY_ID = 'round-local-declared-sites-execution-v9'
_COUNTED_POLICIES = (V5_POLICY_ID, V6_POLICY_ID, V7_POLICY_ID, V8_POLICY_ID)
_WRITTEN_POLICIES = (V6_POLICY_ID, V7_POLICY_ID, V8_POLICY_ID)
_PAIR_GEOMETRY_POLICIES = (V7_POLICY_ID, V8_POLICY_ID)
POLICY_ID = V3_POLICY_ID  # Ordinary requests keep their existing default.
ADMISSION_REFUSAL_POLICY_ID = 'preflight-admission-refusal-v1'
# Filled from the qualified C297 checkpoint; historical readers keep these exact
# identities even when a future policy uses different native/helper sources.
_SOURCE_DIGESTS = {'cif_parallelity_kernel.py': '074c51faa384856f014631c72d97a14237ec3b7b6d833d405ca92aa02b507568', 'cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f', 'cif_refinement_runtime.py': '5b9329c988b3c07c9c3da4586ecce03c6751955fc02ccdf2f35b42088eaa2900', 'data/parallelity-native-profile.json': '5fe3c6657c78e2b85ea6bab3da68f4e79a3f91a2b1498f745be77f1080a2db28'}
_V2_SOURCE_DIGESTS = {'cif_parallelity_kernel.py': '074c51faa384856f014631c72d97a14237ec3b7b6d833d405ca92aa02b507568', 'cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f', 'cif_refinement_runtime.py': '78a7afd54b7f5ca835ad3e42f0a823aea3fb56eda59b1fe643716fec78593741', 'cif_refinement_output.py': '0e231d2d8502b3df7982688709bc9cc9322d2bde2becffcc7962250e9ebc08b5', 'data/parallelity-native-profile.json': '0b447a84abff9ef3efbe1d9481d918581a06299023ac0b6a1d78927c7cd7d3ee'}
_CURRENT_SOURCE_DIGESTS = {'cif_parallelity_kernel.py': '074c51faa384856f014631c72d97a14237ec3b7b6d833d405ca92aa02b507568', 'cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f', 'cif_refinement_runtime.py': '6698585c1da6225895dd1d639554321ccab695eda1b4366d243deb39106c3503', 'cif_refinement_output.py': 'd1b6ff5a6c47407626be27745f30fda0dcede6b56666b9f30abc334d023f4533', 'cif_refinement_sites.py': 'd690273cc3de2b54594d763674e9716177cf2c178f36ab55ca4d29686644a340', 'data/parallelity-native-profile.json': 'f7aa742b2f00026b6bfa63695702e2b74fb65d5e78b598aec654abcea249758b'}
_V4_SOURCE_DIGESTS = dict(_CURRENT_SOURCE_DIGESTS, **{'cif_refinement_runtime.py': '5611e658cb79e92996f24e92b1a13055e69bede04f1ab909a60216baea03b3e3', 'cif_refinement_output.py': '7f4220abd718b6396e3e196d72abea4343c6f5b45187aa51b1dc6efaa651fc21', 'cif_refinement_sites.py': '7643d29e113b487975a0a47ef21686bc19627693e7ec724cc627aa82d07baac8'})
_V5_SOURCE_DIGESTS = {'cif_counted_contribution.py': '7322edee9e78a027bbd47c0043e1acc35494d1d4ecce1e671cb9225f771086b9',
 'cif_counted_phase.py': '5659d00cb21e2d389f098bd4e878c8c03408ac72e0a12bb6385c83889104de5f',
 'cif_counted_refinement.py': 'a5d7c820e511fdb80188563cb746d70516a9601dde83a8a99398542cba27c6e7',
 'cif_gradient_audit.py': 'a4d6571512313ae7ce8522668bd152ea806c5478803b74e296822bc313f275cc',
 'cif_live_nonbonded_policy.py': '14aadda1bbd69ad89f66836610747e32797756b82f7c77d1479d6b7567869c58',
 'cif_parallelity_correction.py': '701af4a752e79aecedfa74627819d72d44dcfa6ef86fb20bcd73f9cba25d792f',
 'cif_parallelity_kernel.py': '074c51faa384856f014631c72d97a14237ec3b7b6d833d405ca92aa02b507568',
 'cif_refinement_output.py': '7f4220abd718b6396e3e196d72abea4343c6f5b45187aa51b1dc6efaa651fc21',
 'cif_refinement_runtime.py': '5611e658cb79e92996f24e92b1a13055e69bede04f1ab909a60216baea03b3e3',
 'cif_refinement_sites.py': '7643d29e113b487975a0a47ef21686bc19627693e7ec724cc627aa82d07baac8',
 'data/counted-native-profile.json': 'bf41896cc2269508a5ded1816ef4f5a4ed7bdee2fa5532bd94e38428d4715571',
 'data/nonbonded-native-profile.json': 'd35a0b61dd49a75132d16d3bb53b1c636eefbd30c21d19fe5d50a03d018e6ee6',
 'data/parallelity-native-profile.json': 'f7aa742b2f00026b6bfa63695702e2b74fb65d5e78b598aec654abcea249758b',
 'topostitch.py': '93a11d54897fac53454cd22f901e908d6e7ebfea46dbf759993ece5db74302bf',
 'topostitch_coordinates.py': '08d613f9dba70a7bf3bf8f265352e7f075e13282e356dfcf8a6565d2227e24ad',
 'topostitch_native_coverage.py': 'e90359fe08fac9497f99d0a829a5bd14c7af803b5f6015730e2143116854fd0f',
 'topostitch_native_recipe.py': '1739b2a7cf11d802bfa9293d7b79b9edcf7bb1ad868b53d4c1b1996b461d7748',
 'topostitch_packing.py': '646f7a59ecea07617e5f3ace0e3bf7be2668c18cb85a408efe4b60a2c6bcd288',
 'topostitch_pair_coverage.py': 'e342d7aa4d6277dac0cd4b90d63fe1501c74249927fe909e119680901c21f591',
 'topostitch_periodic.py': '971d91c0fb1c29619b85fe90829a650214e7560f069dd4bdb8ec50376e12a5ce',
 'topostitch_recipe.py': '73b735197560d8b0e0f0c343b4636fdf9e83b5acffa179aa7586367931293e76',
 'topostitch_transport.py': '8a641d8f067b594e8ea446156b0252583a0d6178c967148a6b86214f9f8cfbfc'}
_V6_SOURCE_DIGESTS = dict(_V5_SOURCE_DIGESTS, **{'cif_refinement_runtime.py': 'fba731d7d2a21301c1c11a84a6a0b515307e73665f2367e42bd2defa25eb1fc1', 'cif_refinement_output.py': 'f006c30fc139f5c52f328607025509d1dca7591ac9ab85c55ceaa3884bf258f2', 'cif_counted_phase.py': 'f9dcb633c6d3c274cb6f5176b603fb6834bb3ce240d138b3fcb86f2134e21cf9'})
_V7_SOURCE_DIGESTS = dict(_V6_SOURCE_DIGESTS, **{'cif_counted_refinement.py': 'f29753cfc5ef2383fd2dc85ade1444d85e9600e138776815afc1bf0f2ec055fc', 'cif_counted_phase.py': 'fe5fb0a90b6ac994da19b05195074ab069b611aa0f7e58f775cb59a3715b686b', 'cif_counted_geometry.py': 'ea0086acb6dfba48e1c7afecbf8fd38fc7f1c548f4cf031e2d4d1d10efaaa3c2'})
_V8_SOURCE_DIGESTS = dict(_V7_SOURCE_DIGESTS, **{'cif_counted_phase.py': '7aa1f76126fee30042909583e627f4c135292aaa9babee9de322818d3b4be206', 'cif_counted_refinement.py': '5ac9e9faff0b35f26455dc879977f441d093f9aebfb557efdc4192b214a460a0'})
_SOURCES = {LEGACY_POLICY_ID:_SOURCE_DIGESTS, V2_POLICY_ID:_V2_SOURCE_DIGESTS,
            V3_POLICY_ID:_CURRENT_SOURCE_DIGESTS, V4_POLICY_ID:_V4_SOURCE_DIGESTS, V5_POLICY_ID:_V5_SOURCE_DIGESTS, V6_POLICY_ID:_V6_SOURCE_DIGESTS, V7_POLICY_ID:_V7_SOURCE_DIGESTS, V8_POLICY_ID:_V8_SOURCE_DIGESTS}
_SOURCES[V9_POLICY_ID] = _CURRENT_SOURCE_DIGESTS
_RUNTIME_POLICIES = {LEGACY_POLICY_ID:'explicit-native-parallelity-refinement-v1',
                     V2_POLICY_ID:'explicit-native-parallelity-refinement-v2',
                     V3_POLICY_ID:'explicit-native-parallelity-refinement-v3',
                     V4_POLICY_ID:'explicit-native-parallelity-refinement-v4',
                     V5_POLICY_ID:'explicit-native-parallelity-refinement-v4',
                     V6_POLICY_ID:'explicit-native-parallelity-refinement-v4', V7_POLICY_ID:'explicit-native-parallelity-refinement-v4', V8_POLICY_ID:'explicit-native-parallelity-refinement-v4'}
_RUNTIME_POLICIES[V9_POLICY_ID] = _RUNTIME_POLICIES[V3_POLICY_ID]
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

_COUNTED_ENTRY = b'''from pathlib import Path
import hashlib,json,sys,os,time
root=Path(__file__).resolve().parent
phase=sys.argv[1];expected=sys.argv[2]
if phase not in ('preflight','refine'):raise ValueError('Unknown counted phase')
raw=(root/'request.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Counted request changed')
request=json.loads(raw)
for name,ref in request['code'].items():
 parts=Path(name).parts
 if not parts or Path(name).is_absolute() or any(p in ('.','..') for p in parts):raise ValueError('Unsafe frozen code path')
 target=root
 for part in parts:
  target=target/part
  if target.is_symlink():raise ValueError('Linked frozen code')
 data=target.read_bytes()
 if len(data)!=ref['size'] or hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Frozen counted code changed')
for key,name in [('original_recipe','original-recipe.json'),('original_model','original-model.pdb'),('current_recipe','current-recipe.json')]:
 target=root/'intent'/name;ref=request['counted_intent'][key]
 if target.is_symlink() or target.parent.is_symlink():raise ValueError('Linked counted intent')
 data=target.read_bytes()
 if len(data)!=ref['size'] or hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Frozen intent changed')
admission=None;prepared_path=None
if phase=='preflight':
 arguments=sys.argv[3:]
 expected_arguments=['output.prefix=parallelity_runtime/preflight/native' if a=='output.prefix=refined' else a for a in request['command'][1:]]+['refinement.dry_run=True']
else:
 if (root/'execution.json').exists():raise ValueError('Counted attempt already finished')
 raw=(root/'admission.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=sys.argv[3]:raise ValueError('Counted admission changed')
 admission=json.loads(raw);prepared_path=sys.argv[4];arguments=sys.argv[5:]
 if admission['request']['sha256']!=expected or admission['checkpoint']!=request['checkpoint']:raise ValueError('Admission belongs to another request')
 expected_arguments=request['command'][1:]
if arguments!=expected_arguments:raise ValueError('Counted native arguments changed')
if phase=='refine':
 marker=dict(schema_version=1,checkpoint=request['checkpoint'],request_sha256=expected,
  admission_sha256=sys.argv[3],pid=os.getpid(),parent_pid=os.getppid(),created_ns=time.time_ns())
 with (root/'refinement-launch.json').open('x') as handle:
  json.dump(marker,handle,sort_keys=True);handle.write('\\n');handle.flush();os.fsync(handle.fileno())
 descriptor=os.open(root,os.O_RDONLY)
 try:os.fsync(descriptor)
 finally:os.close(descriptor)
sys.path.insert(0,str(root/'code'))
from _nasolve_refinement.cif_counted_phase import run_phase
run_phase(root,request,phase,arguments,admission=admission,prepared_path=prepared_path)
'''

_ENTRIES = {LEGACY_POLICY_ID:_V2_ENTRY, V2_POLICY_ID:_V2_ENTRY, V3_POLICY_ID:_ENTRY, V4_POLICY_ID:_ENTRY, V5_POLICY_ID:_COUNTED_ENTRY, V6_POLICY_ID:_COUNTED_ENTRY, V7_POLICY_ID:_COUNTED_ENTRY, V8_POLICY_ID:_COUNTED_ENTRY}
_ENTRIES[V9_POLICY_ID] = _ENTRY
_CHEMISTRY_POLICIES = (V3_POLICY_ID, V4_POLICY_ID, V9_POLICY_ID, *_COUNTED_POLICIES)


def _need(value, message='Invalid explicit parallelity execution evidence'):
    if not value: raise ValueError(message)


def _digest(data): return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def _root(checkpoint): return _directory(checkpoint)+'/parallelity_runtime'


def _code(policy=None):
    """Freeze qualified bytes; default v3 remains exact after a helper upgrade."""
    policy=POLICY_ID if policy is None else policy
    _need(isinstance(policy,str) and policy in (V3_POLICY_ID,V4_POLICY_ID,V9_POLICY_ID,*_COUNTED_POLICIES),
          'Unsupported new native execution policy')
    package=Path(__file__).parent;frozen={}
    if policy in (V3_POLICY_ID,V9_POLICY_ID):
        frozen=json.loads((package/'data/refinement-runtime-v3-sources.json').read_text())
        _need(type(frozen) is dict and set(frozen)=={
            'cif_refinement_runtime.py','cif_refinement_output.py','cif_refinement_sites.py'}
            and all(type(value) is str for value in frozen.values()),
            'Invalid frozen v3 helper source set')
    if policy in (V4_POLICY_ID, V5_POLICY_ID):
        frozen=json.loads((package/'data/refinement-runtime-v5-sources.json').read_text())
        _need(isinstance(frozen,dict) and set(frozen)=={
            'cif_refinement_runtime.py','cif_refinement_output.py','cif_counted_phase.py'}
            and all(isinstance(value,str) for value in frozen.values()),
            'Invalid frozen v4/v5 helper source set')
    if policy in (V5_POLICY_ID,V6_POLICY_ID):
        legacy=json.loads((package/'data/refinement-runtime-v6-sources.json').read_text())
        _need(isinstance(legacy,dict) and set(legacy)=={'cif_counted_phase.py','cif_counted_refinement.py'}
              and all(isinstance(value,str) for value in legacy.values()), 'Invalid frozen v6 helper source set')
        frozen.update(legacy if policy==V6_POLICY_ID else {'cif_counted_refinement.py':legacy['cif_counted_refinement.py']})
    if policy==V7_POLICY_ID:
        legacy=json.loads((package/'data/refinement-runtime-v7-sources.json').read_text())
        _need(isinstance(legacy,dict) and set(legacy)=={'cif_counted_phase.py','cif_counted_refinement.py'}
              and all(isinstance(value,str) for value in legacy.values()), 'Invalid frozen v7 helper source set')
        frozen.update(legacy)
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
    counted=record.get('policy_id') in _COUNTED_POLICIES
    fields = set(record) - ({'chemistry_projections'} if record.get('policy_id') in _CHEMISTRY_POLICIES else set()) - ({'counted_intent'} if counted else set())
    _need(fields in ({'schema_version','policy_id','checkpoint','parent','inputs','command','code','record_sha256'}, {'schema_version','policy_id','checkpoint','parent','inputs','command','code','record_sha256','preflight_mode','macro_cycles'})
          and type(record['schema_version']) is int and record['schema_version']==(2 if counted else 1)
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
    if counted:
        _need(record.get('macro_cycles')==1 and
              (record['policy_id'] in _WRITTEN_POLICIES or 'chemistry_projections' not in record),
              'Counted scope requires one cycle; v5 excludes chemistry projections')
        from .refinement_counted import read_intent
        read_intent(run,root,record)
    if 'chemistry_projections' in record:
        from .refinement_chemistry import _projection_scope
        _need(bool(record['chemistry_projections']), 'Empty requested chemistry scope')
        _projection_scope(run,record['chemistry_projections'],require_triple=record['policy_id']!=V9_POLICY_ID)
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


def prepare_execution(run, *, checkpoint, parent, inputs, command, python_executable, macro_cycles, chemistry_projections=None, runtime_policy=None, counted_pair_request=None):
    """Freeze only the small qualified helper; retain all original input files."""
    from .checkpoints import _file_reference
    policy=POLICY_ID if runtime_policy is None else runtime_policy
    _need(runtime_policy is None or (isinstance(policy,str) and policy in (V3_POLICY_ID,V4_POLICY_ID,V9_POLICY_ID,*_COUNTED_POLICIES)),
          'Unsupported new native execution policy')
    _need(isinstance(command,list) and len(command)>1)
    inputs=[Path(p).expanduser().resolve() for p in inputs]
    _need(command[1:1+len(inputs)]==[str(p) for p in inputs],
          'Runtime input order differs from the native command')
    if chemistry_projections is not None:
        from .refinement_chemistry import _projection_scope
        _projection_scope(run,chemistry_projections,require_triple=policy!=V9_POLICY_ID)
    payload=_code() if runtime_policy is None else _code(policy)
    intent_payload=None
    if policy in _COUNTED_POLICIES:
        _need(type(macro_cycles) is int and macro_cycles==1 and
              (policy in _WRITTEN_POLICIES or chemistry_projections is None),
              'Counted scope requires one cycle; v5 excludes chemistry projections')
        _need(isinstance(counted_pair_request,dict) and set(counted_pair_request)=={'recipe','source_model'}
              and len(inputs)>=2,'Require original pair recipe/source and current parent')
        from .refinement_counted import prepare_intent
        intent_payload=prepare_intent(counted_pair_request['recipe'],counted_pair_request['source_model'],inputs[1])
        from .checkpoints import _file_reference
        _need(all(_file_reference(p,run)['anchor'] in ('run','dataset','repository') for p in inputs),
              'Counted inputs require declared portable anchors')
    else:_need(counted_pair_request is None,'Counted intent requires an explicit counted policy')
    root=path_in(run,_root(checkpoint));root.mkdir()
    code={}
    for name,data in payload.items():
        target=path_in(root,name);target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as handle:handle.write(data)
        code[name]=_file_reference(target,run)
    intent=None
    if intent_payload is not None:
        from .refinement_counted import write_intent
        intent=write_intent(run,root,intent_payload)
    request=root/'request.json'
    write_record(request,dict(schema_version=2 if intent is not None else 1,policy_id=policy,checkpoint=checkpoint,
        parent=parent,preflight_mode='native-model-zero-cycle-isolated-v1',macro_cycles=macro_cycles,
        inputs=[_file_reference(Path(p),run) for p in inputs],
        command=list(command),code=code,
        **({'counted_intent':intent} if intent is not None else {}),
        **({'chemistry_projections':chemistry_projections} if chemistry_projections else {})))
    reference=_file_reference(request,run)
    prefix=[str(python_executable),'-B',str(root/'entry.py')]
    request_record=read_execution_request(run,reference,checkpoint=checkpoint)
    if policy in _COUNTED_POLICIES:
        return reference,[*prefix,'preflight',reference['sha256'],*_preflight_arguments(request_record)],None
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


def validate_runtime_choice(enabled, python_executable, *, runtime_policy=None):
    """Validate the explicit choice before either owner allocates work."""
    if type(enabled) is not bool:
        raise ValueError('Native parallelity correction must be explicitly enabled or disabled')
    if enabled and (python_executable is None or not Path(python_executable).is_file()):
        raise ValueError('Explicit plane-force correction requires the configured phenix.python')
    if enabled:
        try:_code() if runtime_policy is None else _code(runtime_policy)
        except OSError as exc:
            raise ValueError('Required qualified runtime source is unavailable: '+str(exc)) from exc


def require_runtime_continuation(registry, selected, enabled, *, run=None, allow_counted=False, observe_declared_sites=False):
    ancestors=_checked_ancestors(registry,selected)
    if run is not None:
        # Ordinary owners have already validated the registry. Read only the
        # pinned policy for this additional refusal; do not repeat native proof
        # expansion or create a weaker positive admission path.
        for item in ancestors:
            try:
                record=read_record(_bound_path(item['outputs']['parallelity_execution'],
                    'ancestor execution policy',run))
                policy=record.get('policy_id')
                _need(isinstance(policy,str) and policy in _SOURCES,'Unknown ancestor execution policy')
            except (OSError,ValueError,RuntimeError) as exc:raise ValueError(str(exc)) from exc
            if policy == V9_POLICY_ID and not observe_declared_sites:
                raise ValueError('This checkpoint retains declared-site chemistry observation; '
                                 'continue explicitly with observe_declared_sites=True. No new round was started.')
            if policy in _COUNTED_POLICIES and not allow_counted:
                raise ValueError(
                    'This checkpoint inherits counted pair restraints. Ordinary continuation '
                    'is not yet qualified; prepare a fresh explicit counted request preserving '
                    'the original recipe and current parent. No new round was started.')
    if not enabled and ancestors:
        raise ValueError(
            'This checkpoint descends from checked plane-force refinement; '
            'continue explicitly with --checked-plane-forces. No new round was started.')


def _checked_ancestors(registry, selected):
    items=registry.get('checkpoints',[])
    corrected={item.get('id') for item in items if isinstance(item,dict)
               and isinstance(item.get('outputs'),dict) and 'parallelity_execution' in item['outputs']}
    if not corrected:return []
    from .checkpoint_candidate import _lineage,CheckpointCandidateError
    try:lineage=corrected.intersection(_lineage(registry,selected))
    except CheckpointCandidateError as exc:raise ValueError(str(exc)) from exc
    return [item for item in items if item.get('id') in lineage]


def requires_checked_plane_forces(registry, selected):
    """Reuse established ancestry validation; manual edits retain their history."""
    return bool(_checked_ancestors(registry,selected))


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
        if request['policy_id'] in _WRITTEN_POLICIES:
            from .cif_refinement_output import validate_written_model
            _need('written_model' in result,'Missing requested native written-model observation')
            validate_written_model(result['written_model'],dry_run=phase=='preflight',
                                   output_observations=result['output_synchronization'])
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
    if request['policy_id'] in _COUNTED_POLICIES and phase=='refine' and require_complete:
        counted=json.loads(path_in(run,root+'/refine/counted.json').read_text())
        _need(isinstance(counted,dict) and set(counted)=={'policy_id','lifetime','admission_record_sha256','prepared_sha256',
              'compiled_binding_sha256','provider_selection_sha256','recipe_sha256','scope_sha256'}
              and counted['policy_id']=='counted-phase-observation-v1','Missing counted phase outcome')
        lifetime=counted['lifetime'];owner=lifetime.get('owner') if isinstance(lifetime,dict) else None
        scope_policy=('prepared-counted-refinement-cycle-v2' if request['policy_id']==V8_POLICY_ID
                      else 'prepared-counted-refinement-cycle-v1')
        _need(isinstance(lifetime,dict) and lifetime.get('policy_id')==scope_policy
              and lifetime.get('status')=='COMPLETE' and lifetime.get('binding_restored') is True
              and type(lifetime.get('driver_entries')) is int and lifetime['driver_entries']==1
              and isinstance(owner,dict) and owner.get('closed') is True and owner.get('poisoned') is False
              and type(owner.get('successful_calls')) is int and owner['successful_calls']>0,
              'Counted refinement did not complete its admitted lifetime')
        if request['policy_id'] in _PAIR_GEOMETRY_POLICIES:
            from .refinement_pair_geometry import read_pair_geometry
            read_pair_geometry(run,root,request)
    return result


def validate_preflight(run, reference, *, checkpoint):
    request=read_execution_request(run,reference,checkpoint=checkpoint)
    result=_phase(run,_root(checkpoint),'preflight',request['code'],request,require_complete=True)
    if request['policy_id'] in _COUNTED_POLICIES:
        from .refinement_counted import _observation
        _observation(run,_root(checkpoint),request)
    return result


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
                     admission_refusal=None, counted_admission=None):
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
    if request['policy_id'] in _COUNTED_POLICIES and refinement_returncode is not None:
        from .refinement_counted import read_admission
        admission=read_admission(run,reference,counted_admission,checkpoint=checkpoint)
        marker=path_in(run,root+'/refinement-launch.json')
        launch=_file_reference(marker,run) if marker.exists() else None
        from .refinement_counted import read_outcome_binding
        read_outcome_binding(run,root,request,admission,launch,complete=refinement_returncode==0)
    else:_need(counted_admission is None,'Unrequested counted admission')
    if request['policy_id'] in _PAIR_GEOMETRY_POLICIES and refinement_returncode==0:
        from .refinement_pair_geometry import seal_pair_geometry
        seal_pair_geometry(run,root,request,admission)
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
        **({'counted_admission':counted_admission,'counted_launch':launch} if counted_admission is not None else {}),
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
    if record.get('policy_id') in _COUNTED_POLICIES and 'counted_admission' in record:
        fields|={'counted_admission','counted_launch'}
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
    if request['policy_id'] in _COUNTED_POLICIES and codes[1] is not None:
        from .refinement_counted import read_admission
        admission=read_admission(run,record['request'],record.get('counted_admission'),checkpoint=checkpoint)
        from .refinement_counted import read_outcome_binding
        read_outcome_binding(run,root,request,admission,record.get('counted_launch'),complete=codes[1]==0)
    else:_need('counted_admission' not in record,'Unrequested counted admission')
    if usable:_need(codes==[0,0],'Usable checkpoint requires both native runtime stages to complete')
    return record


def validate_checkpoint_execution(run, item, registry):
    outputs=item.get('outputs')
    if isinstance(outputs,dict) and 'parallelity_execution' in outputs:
        record=validate_execution(run,outputs['parallelity_execution'],checkpoint=item.get('id'),
                                  parent=item.get('parent'),usable=item.get('usable') is True)
        request=read_execution_request(run,record['request'],checkpoint=item['id'])
        if request['policy_id'] in _COUNTED_POLICIES:
            from .refinement_counted import validate_intent_lineage
            validate_intent_lineage(run,registry,item,request)
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
        if item.get('usable') is True and request['policy_id'] in _WRITTEN_POLICIES:
            result=_phase(run,_root(item['id']),'refine',request['code'],request,require_complete=True)
            data=_ref_path(item['model'],'counted refinement model',run).read_bytes()
            written=result['written_model']
            _need(written['sha256']==_digest(data) and written['size']==len(data),
                  'Published checkpoint model differs from the native written model')
        if (item.get('usable') is True and request['policy_id'] in _CHEMISTRY_POLICIES
                and request.get('chemistry_projections')):
            result=_phase(run,_root(item['id']),'refine',request['code'],request,require_complete=True)
            if result.get('chemistry_model') is not None:
                data=_ref_path(item['model'],'refinement model',run).read_bytes()
                _need(result['chemistry_model']==dict(sha256=_digest(data),size=len(data)),
                      'Observed native output differs from the checkpoint model')
        return record


def _selected_chemistry_observation(run, reference, *, checkpoint, parent, model):
    """Use one existing validation path for explicit selected-site readers."""
    record=validate_execution(run,reference,checkpoint=checkpoint,parent=parent,usable=True)
    request=read_execution_request(run,record['request'],checkpoint=checkpoint)
    if request['policy_id'] not in _CHEMISTRY_POLICIES or not request.get('chemistry_projections'):
        return None
    result=_phase(run,_root(checkpoint),'refine',request['code'],request,require_complete=True)
    from .refinement_chemistry import _projection_scope
    _,projections=_projection_scope(run,request['chemistry_projections'],require_triple=request['policy_id']!=V9_POLICY_ID)
    data=Path(model).read_bytes()
    if result['chemistry_observation']['status']=='OBSERVED':
        _need(result['chemistry_model']==dict(sha256=_digest(data),size=len(data)),
              'Observed native output differs from the checkpoint model')
    return data,projections,result['chemistry_observation']


def _declared_chemistry_sources(run, reference, *, checkpoint):
    """Recheck the sealed request and its source hashes at report completion."""
    record = read_record(_bound_path(reference, 'selected chemistry execution', run))
    request = read_execution_request(run, record['request'], checkpoint=checkpoint)
    return {row['site']: dict(component=row['component'], projection_sha256=row['projection']['sha256'])
            for row in request['chemistry_projections']}


def read_execution_chemistry(run, reference, *, checkpoint, parent, model):
    """Read the historical triple report through its unchanged sealed evidence."""
    selected=_selected_chemistry_observation(run,reference,checkpoint=checkpoint,parent=parent,model=model)
    if selected is None:return None
    from .refinement_chemistry import _observed_readback
    result = _observed_readback(*selected)
    _need(result['declared_sites'] == _declared_chemistry_sources(run, reference, checkpoint=checkpoint),
          'Chemistry report sources differ from the sealed request')
    return result


def read_execution_chemistry_sites(run, reference, *, checkpoint, parent, model):
    """Read authenticated selected-site atoms and effective intra-site terms.

    This preserves the capture's heavy-atom, same-site scope. It does not supply
    missing hydrogen/cross-site/symmetry neighborhoods or approve the chemistry.
    """
    selected=_selected_chemistry_observation(run,reference,checkpoint=checkpoint,parent=parent,model=model)
    if selected is None:return None
    data,projections,observation=selected
    declared = _declared_chemistry_sources(run, reference, checkpoint=checkpoint)
    _need(set(declared)==set(projections), 'Selected chemistry scope changed during read')
    return dict(schema_version=1,policy_id='refinement-declared-sites-observation-v1',
        model_sha256=_digest(data),declared_sites=declared,
        observation=observation,scientific_approval='NOT_RUN',automatic_adoption=False)


def read_execution_scalar_geometry(run, reference, *, checkpoint, parent, model):
    """Describe bonds, angles and ordered volumes from authenticated final sites.

    Reuse C15 scalar arithmetic; selected heavy-atom evidence does not become a
    whole-model inventory, native energy or scientific acceptance gate.
    """
    selected = _selected_chemistry_observation(run, reference,
        checkpoint=checkpoint, parent=parent, model=model)
    if selected is None:
        return None
    data, projections, observation = selected
    from .refinement_chemistry import _observed_scalar_geometry
    result = dict(_observed_scalar_geometry(projections, observation), model_sha256=_digest(data))
    _need(result['declared_sites'] == _declared_chemistry_sources(run, reference, checkpoint=checkpoint),
          'Scalar report sources differ from the sealed request')
    return result


def read_execution_trigonal_geometry(run, reference, *, checkpoint, parent, model):
    """Explicit source-selected shape/plane report; no native run or adoption.

    Existing workers capture only their declared chemistry sites. This reader
    neither enlarges that scope nor changes historical triple reports.
    """
    selected=_selected_chemistry_observation(run,reference,checkpoint=checkpoint,parent=parent,model=model)
    if selected is None:return None
    data,projections,observation=selected
    from .cif_plane_geometry import _observed_trigonal_geometry
    result = dict(_observed_trigonal_geometry(projections,observation),model_sha256=_digest(data))
    _need(result['declared_sites'] == _declared_chemistry_sources(run, reference, checkpoint=checkpoint),
          'Trigonal report sources differ from the sealed request')
    return result


def read_execution_plane_geometry(run, reference, *, checkpoint, parent, model):
    """Measure recorded local planes and their linear continuations on the exact model."""
    selected = _selected_chemistry_observation(run, reference, checkpoint=checkpoint, parent=parent, model=model)
    if selected is None:
        return None
    from .refinement_plane_departures import describe_planes
    model_bytes, projections, observation = selected
    if observation["status"] == "OBSERVED":
        from .refinement_chemistry import _source_checked_atoms
        _source_checked_atoms(projections, observation)
    report = describe_planes(observation)
    declared = _declared_chemistry_sources(run, reference, checkpoint=checkpoint)
    expected = [dict(site=site, component=source["component"]) for site, source in sorted(declared.items())]
    _need(set(projections) == set(declared) and observation["sites"] == expected,
          "Plane report sites differ from the sealed request")
    return dict(report, model_sha256=_digest(model_bytes), declared_sites=declared)


def read_execution_pair_geometry(run,reference,*,checkpoint,parent,model):
    record=validate_execution(run,reference,checkpoint=checkpoint,parent=parent,usable=True)
    if record['policy_id'] not in _PAIR_GEOMETRY_POLICIES:return None
    request=read_execution_request(run,record['request'],checkpoint=checkpoint)
    root=_root(checkpoint);native=json.loads(path_in(run,root+'/refine/result.json').read_text())
    data=Path(model).read_bytes();written=native['written_model']
    _need(len(data)==written['size'] and _digest(data)==written['sha256'],
          'Pair geometry belongs to a different written model')
    from .refinement_pair_geometry import read_pair_geometry
    return read_pair_geometry(run,root,request)
