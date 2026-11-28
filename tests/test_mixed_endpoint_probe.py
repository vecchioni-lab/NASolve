"""Saved-endpoint ferry with exact opaque C91/C90/C89 review ancestry."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from tests.test_mixed_torsion_probe import capsule as geometry_capsule

ROOT = Path(__file__).parents[1]
TORSION = 'mixed_torsion/'
GEOMETRY = 'mixed_geometry/'
GRADIENT = 'mixed_gradient/'
CONTEXT = 'inputs/review/inputs/review/mixed_context/'
PARENT = 'inputs/review/inputs/review/inputs/review/inputs/review/inputs/review/mixed_linked_recovery/'


def module():
    spec = importlib.util.spec_from_file_location('mixed_endpoint_ferry', ROOT/'scripts/mixed_endpoint_probe_template.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def capsule(tmp_path, defect='none'):
    c90_defect = defect.removeprefix('c90_') if defect.startswith('c90_') else 'none'
    inner, inner_digest, inner_members, c89_digest, c89_members = geometry_capsule(tmp_path, c90_defect)
    inner_bytes = inner.read_bytes()
    geometry = json.loads(inner_members[GEOMETRY+'mixed_geometry_trial.json'])
    report = {'schema_version': 1, 'policy_id': 'cif-mixed-fixed-torsion-audit-v1',
        'status': 'MIXED_TORSION_AUDIT_COMPLETE', 'new_native_calls': 1, 'maximum_native_calls': 1,
        'parent_archive_sha256': inner_digest, 'automatic_adoption': False,
        'requires_cif_review': False, 'scientific_qualification': 'NOT_ASSESSED',
        'model_optimization': 'NOT_RUN', 'endpoint_requalification': 'NOT_RUN',
        'execution': {'status': 'COMPLETED', 'returncode': 0},
        'qualification': {'status': 'MIXED_TORSION_AUDIT_COMPLETE', 'endpoint_requalification': 'NOT_RUN',
            'automatic_adoption': False, 'summary': {'local_sampled_agreement': False}},
        'original_geometry_status': geometry['status'],
        'original_geometry_qualification': geometry['qualification'],
        'coordinate_decision': geometry['coordinate_decision']}
    mutations = {'policy': ('policy_id', 'OTHER'), 'status': ('status', 'PREPARED_ONLY'),
        'new_count': ('new_native_calls', 0), 'new_count_bool': ('new_native_calls', True),
        'max_count': ('maximum_native_calls', 2), 'max_count_bool': ('maximum_native_calls', True),
        'adoption': ('automatic_adoption', True), 'approval': ('requires_cif_review', True),
        'science': ('scientific_qualification', 'APPROVED'), 'optimization': ('model_optimization', 'RAN'),
        'endpoint_qualification': ('endpoint_requalification', 'PASS'),
        'parent_hash': ('parent_archive_sha256', '0'*64)}
    if defect in mutations: report[mutations[defect][0]] = mutations[defect][1]
    elif defect == 'execution': report['execution']['returncode'] = 2
    elif defect == 'execution_bool': report['execution']['returncode'] = False
    elif defect == 'execution_status': report['execution']['status'] = 'FAILED'
    elif defect == 'qualification': report['qualification']['status'] = 'REVIEW'
    elif defect == 'qualification_adoption': report['qualification']['automatic_adoption'] = True
    elif defect == 'qualification_endpoint': report['qualification']['endpoint_requalification'] = 'PASS'
    elif defect == 'unusable_original': report['coordinate_decision']['native_usable'] = False
    elif defect == 'decision_adoption': report['coordinate_decision']['automatic_adoption'] = True
    elif defect == 'decision_changed': report['coordinate_decision']['selected'] = 'qualified_geometry_endpoint'
    elif defect == 'original_status': report['original_geometry_status'] = 'PASS'
    elif defect == 'original_qualification': report['original_geometry_qualification'] = {'status': 'PASS'}
    rdata = json.dumps(report).encode()
    reference = {'directory': {'anchor': 'probe_directory', 'path': 'mixed_torsion'},
        'report_sha256': sha256(rdata).hexdigest(), 'report_size': len(rdata),
        'status': 'MIXED_TORSION_AUDIT_COMPLETE', 'new_native_calls': 1}
    parent_ref = {'anchor': 'probe_directory', 'path': 'inputs/parent_review.zip',
        'sha256': inner_digest, 'size': len(inner_bytes)}
    header = {'schema_version': 1, 'kind': 'mixed-torsion-probe', 'delivery_prefix': '91_Cedar',
        'analysis_completed': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'mixed_torsion': reference, 'parent_review': {'artifact': parent_ref,
            'payload_count': len(inner_members), 'preserved': True}, 'parent_review_preserved': True,
        'frozen_runtime_preserved': True, 'model_optimization_requested': False,
        'captured_code_execution': 'NOT_RUN'}
    if defect == 'kind': header['kind'] = 'OTHER'
    elif defect == 'prefix': header['delivery_prefix'] = 'OTHER'
    elif defect == 'incomplete': header['analysis_completed'] = False
    elif defect == 'header_approval': header['requires_cif_review'] = True
    elif defect == 'header_adoption': header['automatic_adoption'] = True
    elif defect == 'header_optimization': header['model_optimization_requested'] = True
    elif defect == 'header_captured': header['captured_code_execution'] = 'RAN'
    elif defect == 'runtime_preserved': header['frozen_runtime_preserved'] = False
    elif defect == 'report_hash': reference['report_sha256'] = '0'*64
    elif defect == 'report_size': reference['report_size'] += 1
    elif defect == 'report_path': reference['directory']['path'] = '../outside'
    elif defect == 'report_anchor': reference['directory']['anchor'] = 'unbound_location'
    elif defect == 'envelope_count_bool': reference['new_native_calls'] = True
    elif defect == 'parent_anchor': parent_ref['anchor'] = 'unbound_location'
    elif defect == 'parent_path': parent_ref['path'] = '../outside'
    elif defect == 'parent_size': parent_ref['size'] += 1
    elif defect == 'parent_count': header['parent_review']['payload_count'] += 1
    elif defect == 'parent_count_bool': header['parent_review']['payload_count'] = True
    elif defect == 'parent_preserved': header['parent_review']['preserved'] = False
    elif defect == 'parent_envelope_preserved': header['parent_review_preserved'] = False
    members = {'probe_receipt.json': json.dumps(header).encode(),
        TORSION+'mixed_torsion_audit.json': rdata,
        TORSION+'job/torsion_result.json': b'{"saved_fine_review":"BOUNDARY_EVIDENCE_RETAINED"}\n',
        TORSION+'job/captured.py': b'raise RuntimeError("CAPTURED_TORSION_CODE_MUST_NOT_RUN")\n',
        'inputs/parent_review.zip': inner_bytes,
        'unrelated/mixed_torsion_audit.json': b'DECOY_TORSION\n'}
    if defect == 'path': members['../outside'] = b'BAD'
    elif defect == 'large': members['saved/large.json'] = b' '*(21*1024*1024)
    elif defect == 'oversize': members['saved/oversize.json'] = b' '*(33*1024*1024)
    elif defect == 'entries': members.update({f'saved/extra/{i:04d}.txt': b'x' for i in range(1024)})
    manifest = {name: {'sha256': sha256(data).hexdigest(), 'bytes': len(data)} for name, data in members.items()}
    if defect == 'hash': manifest[TORSION+'mixed_torsion_audit.json']['sha256'] = '0'*64
    elif defect == 'inventory': manifest.pop(TORSION+'mixed_torsion_audit.json')
    raw = io.BytesIO()
    with ZipFile(raw, 'w') as archive:
        for name, data in members.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect == 'symlink' and name.endswith('.py') else 0o100644) << 16
            archive.writestr(entry, data)
        if defect == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('probe_receipt.json', members['probe_receipt.json'])
        archive.writestr('manifest.json', json.dumps(manifest))
    path = tmp_path/'torsion-review.zip';path.write_bytes(raw.getvalue())
    return path, sha256(raw.getvalue()).hexdigest(), members, inner_digest, inner_members, c89_digest, c89_members


def configure(ferry, digest, inner_digest, c89_digest):
    ferry.REVIEW_SHA256 = digest
    ferry.TORSION_PARENT_SHA256 = inner_digest
    ferry.GEOMETRY_PARENT_SHA256 = c89_digest


def test_completed_torsion_audit_with_remaining_fine_review_is_accepted_as_data(tmp_path):
    ferry = module();path,digest,members,inner_digest,_,c89_digest,_ = capsule(tmp_path)
    configure(ferry,digest,inner_digest,c89_digest)
    actual = ferry._read_capsule(path)
    assert {name:actual[name] for name in members} == members


def test_endpoint_inputs_use_only_five_declared_shallow_views(tmp_path):
    ferry = module();_,digest,members,inner_digest,c90,c89_digest,c89 = capsule(tmp_path)
    configure(ferry,digest,inner_digest,c89_digest)
    destination = tmp_path/'views'
    views = ferry._materialize_inputs(members,destination)
    assert tuple(p.name for p in views) == ('torsion','geometry','gradient','context','linked_parent')
    for source,prefix,view in [(members,TORSION,views[0]),(c90,GEOMETRY,views[1]),
            (c89,GRADIENT,views[2]),(c89,CONTEXT,views[3]),(c89,PARENT,views[4])]:
        assert {p.relative_to(view).as_posix():p.read_bytes() for p in view.rglob('*') if p.is_file()} == {
            name[len(prefix):]:data for name,data in source.items() if name.startswith(prefix)}
    assert not any(p.suffix=='.zip' for p in destination.rglob('*'))
    assert not any('unrelated' in p.parts for p in destination.rglob('*'))
    assert (views[0]/'job/captured.py').read_bytes().startswith(b'raise RuntimeError')


def test_endpoint_ferry_opaque_parent_is_preserved_once_without_flattening(tmp_path):
    ferry = module();path,digest,members,inner_digest,_,c89_digest,_ = capsule(tmp_path)
    configure(ferry,digest,inner_digest,c89_digest);ferry.BUNDLE={'delivery_prefix':'92_Cedar'}
    session=tmp_path/'92_Cedar_mixed-endpoint-owned';session.mkdir()
    original=path.read_bytes();ferry._write(session/'inputs/parent_review.zip',original)
    ferry._save_receipt(session,{'schema_version':1,'automatic_adoption':False})
    result=ferry._review_zip(session)
    with ZipFile(result) as z:files={n:z.read(n) for n in z.namelist()}
    assert files['inputs/parent_review.zip']==original
    assert set(files)=={'inputs/parent_review.zip','probe_receipt.json','manifest.json'}
    assert sum(data==original for data in files.values())==1


def test_endpoint_ferry_has_no_optimizer_cli(tmp_path,monkeypatch):
    ferry=module();monkeypatch.setattr(ferry,'_runtime_members',lambda:pytest.fail('optimizer argument read runtime'))
    monkeypatch.setattr('sys.argv',['endpoint-probe','--review-zip',str(tmp_path/'absent.zip'),'--max-iterations','1000'])
    with pytest.raises(SystemExit) as stopped:ferry.main()
    assert stopped.value.code==2


@pytest.mark.parametrize('defect', ['large','kind','prefix','incomplete','header_approval','header_adoption',
    'header_optimization','header_captured','runtime_preserved','policy','status','new_count','new_count_bool',
    'max_count','max_count_bool','adoption','approval','science','optimization','endpoint_qualification',
    'execution','execution_bool','execution_status','qualification','qualification_adoption','qualification_endpoint',
    'unusable_original','decision_adoption','decision_changed','original_status','original_qualification',
    'envelope_count_bool','report_hash','report_size','report_path','report_anchor','parent_hash',
    'parent_anchor','parent_path','parent_size','parent_count','parent_count_bool','parent_preserved',
    'parent_envelope_preserved','path','hash','inventory','symlink','duplicate','archive','oversize','entries'])
def test_endpoint_parent_bindings_and_outer_capsule_bounds_are_strict(tmp_path,defect):
    ferry=module();path,digest,members,inner_digest,_,c89_digest,_=capsule(tmp_path,defect)
    configure(ferry,'0'*64 if defect=='archive' else digest,inner_digest,c89_digest)
    original=path.read_bytes()
    if defect=='large':
        actual=ferry._read_capsule(path)
        assert {n:actual[n] for n in members}==members
    else:
        with pytest.raises(ValueError):ferry._read_capsule(path)
    assert path.read_bytes()==original and not (tmp_path/'outside').exists()


@pytest.mark.parametrize('defect',['hash','inventory','symlink','duplicate','path','oversize','entries'])
@pytest.mark.parametrize('level',['c90_','c90_inner_'])
def test_nested_geometry_and_gradient_capsules_are_verified_before_staging(tmp_path,defect,level):
    ferry=module();path,digest,_,inner_digest,_,c89_digest,_=capsule(tmp_path,level+defect)
    configure(ferry,digest,inner_digest,c89_digest);original=path.read_bytes()
    with pytest.raises(ValueError):ferry._read_capsule(path)
    assert path.read_bytes()==original and not (tmp_path/'outside').exists()


@pytest.mark.parametrize('level',['C90','C89'])
def test_exact_nested_archive_checksum_is_required(tmp_path,level):
    ferry=module();path,digest,_,inner_digest,_,c89_digest,_=capsule(tmp_path)
    configure(ferry,digest,'0'*64 if level=='C90' else inner_digest,'0'*64 if level=='C89' else c89_digest)
    with pytest.raises(ValueError):ferry._read_capsule(path)


def test_opaque_torsion_parent_must_fit_unchanged_outer_member_limit(tmp_path):
    ferry=module();_,_,members,inner_digest,_,c89_digest,_=capsule(tmp_path)
    payload=b'x'*(17*1024*1024);members.update({'bounded_one.bin':payload,'bounded_two.bin':payload})
    raw=_pack(members);path=tmp_path/'too-large-opaque-parent.zip';path.write_bytes(raw)
    configure(ferry,sha256(raw).hexdigest(),inner_digest,c89_digest)
    assert len(raw)>32*1024*1024
    with pytest.raises(ValueError):ferry._read_capsule(path)


def test_endpoint_input_views_refuse_existing_user_directory(tmp_path):
    ferry=module();_,digest,members,inner_digest,_,c89_digest,_=capsule(tmp_path)
    configure(ferry,digest,inner_digest,c89_digest)
    destination=tmp_path/'existing';destination.mkdir();sentinel=destination/'keep.txt';sentinel.write_bytes(b'KEEP USER DATA')
    with pytest.raises(FileExistsError):ferry._materialize_inputs(members,destination)
    assert sentinel.read_bytes()==b'KEEP USER DATA' and list(destination.iterdir())==[sentinel]


def _pack(members):
    raw=io.BytesIO()
    with ZipFile(raw,'w') as archive:
        for name,data in members.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json.dumps({n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}))
    return raw.getvalue()


@pytest.mark.parametrize('missing',[TORSION,GEOMETRY,GRADIENT,CONTEXT,PARENT])
def test_missing_explicit_torsion_or_ancestor_view_has_no_basename_fallback(tmp_path,missing):
    ferry=module();_,digest,members,inner_digest,c90,c89_digest,c89= capsule(tmp_path)
    if missing==TORSION:members={n:d for n,d in members.items() if not n.startswith(missing)}
    elif missing==GEOMETRY:
        c90={n:d for n,d in c90.items() if not n.startswith(missing)}
        original=_pack(c90);members['inputs/parent_review.zip']=original;inner_digest=sha256(original).hexdigest()
    else:
        c89={n:d for n,d in c89.items() if not n.startswith(missing)}
        original=_pack(c89);c90['inputs/parent_review.zip']=original;c89_digest=sha256(original).hexdigest()
        original=_pack(c90);members['inputs/parent_review.zip']=original;inner_digest=sha256(original).hexdigest()
    configure(ferry,digest,inner_digest,c89_digest)
    with pytest.raises((ValueError,KeyError)):ferry._materialize_inputs(members,tmp_path/'missing-view')


@pytest.mark.parametrize('inspect_only,seconds',[(True,None),(False,None),(True,1),(False,600)])
def test_endpoint_main_uses_five_views_and_preserves_one_exact_opaque_parent(tmp_path,monkeypatch,capsys,inspect_only,seconds):
    import nasolve,restraints,sys
    from types import SimpleNamespace
    ferry=module();path,digest,original_members,inner_digest,c90,c89_digest,c89=capsule(tmp_path)
    original_zip=path.read_bytes();runtime_members={'src/nasolve/__init__.py':b'# OWNED ARTIFICIAL RUNTIME\n',
        'restraints/__init__.py':b'# OWNED ARTIFICIAL NAR RUNTIME\n'}
    monkeypatch.setattr(ferry,'BUNDLE',{'delivery_prefix':'92_Cedar'})
    configure(ferry,digest,inner_digest,c89_digest)
    monkeypatch.setattr(ferry,'_runtime_members',lambda:runtime_members)
    def isolated_fixture(runtime,session,members):
        for name,data in members.items():ferry._write(runtime/name,data)
        monkeypatch.setattr(nasolve,'__file__',str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints,'__file__',str(runtime/'restraints/__init__.py'))
    executable=tmp_path/'selected-sdk/bin/phenix.python';executable.parent.mkdir(parents=True);executable.write_bytes(b'OWNED FAKE SDK; NEVER EXECUTED\n')
    sdk=SimpleNamespace(version='2.2.1',root=tmp_path/'selected-sdk',source='explicit',executables={'phenix.python':executable},environment={})
    discoveries,events,views=[],[],[]
    decision={'status':'CONTINUE_WITH_NOTES','selected':'verified_constructed_model','native_usable':True,'automatic_adoption':False,'requires_cif_review':False}
    result={'schema_version':1,'policy_id':'cif-mixed-saved-endpoint-qualification-v1',
        'status':'PREPARED_ONLY' if inspect_only else 'REVIEW','new_native_calls':0 if inspect_only else 1,'coordinate_decision':decision}
    def discovery(config,*,explicit,environ):
        assert not inspect_only and Path(explicit)==sdk.root;discoveries.append(explicit);return sdk
    def qualify(torsion,geometry,gradient,context,parent,phenix,output,*,parent_archive_sha256,timeout_seconds=120):
        assert not events and parent_archive_sha256==digest
        assert timeout_seconds==(120 if seconds is None else seconds) and phenix is (None if inspect_only else sdk)
        torsion,geometry,gradient,context,parent,output=map(Path,(torsion,geometry,gradient,context,parent,output))
        assert (torsion/'mixed_torsion_audit.json').read_bytes()==original_members[TORSION+'mixed_torsion_audit.json']
        assert (torsion/'job/torsion_result.json').read_bytes()==original_members[TORSION+'job/torsion_result.json']
        assert (geometry/'mixed_geometry_trial.json').read_bytes()==c90[GEOMETRY+'mixed_geometry_trial.json']
        assert (gradient/'mixed_initial_gradients.json').read_bytes()==c89[GRADIENT+'mixed_initial_gradients.json']
        assert (context/'mixed_context.json').read_bytes()==c89[CONTEXT+'mixed_context.json']
        assert (parent/'inputs/model.pdb').read_bytes()==b'EXACT SCIENTIFIC MODEL\n'
        assert (torsion/'job/captured.py').read_bytes().startswith(b'raise RuntimeError')
        assert all(not p.is_relative_to(output.parent) for p in [torsion,geometry,gradient,context,parent])
        assert (output.parent/'inputs/parent_review.zip').read_bytes()==original_zip
        views.extend([torsion,geometry,gradient,context,parent]);events.append('qualification')
        output.mkdir();(output/'mixed_endpoint_qualification.json').write_text(json.dumps(result));return result
    def read(output,*,torsion_directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory,parent_archive_sha256):
        assert events==['qualification'] and parent_archive_sha256==digest
        assert tuple(map(Path,(torsion_directory,geometry_directory,gradient_directory,context_directory,linked_parent_directory)))==tuple(views)
        assert all(p.is_dir() for p in views)
        assert json.loads((Path(output)/'mixed_endpoint_qualification.json').read_bytes())==result
        events.append('reader');return result
    def forbidden(*args,**kwargs):pytest.fail('endpoint ferry executed an unrequested subprocess')
    monkeypatch.setattr(ferry,'_isolate',isolated_fixture)
    monkeypatch.setattr('nasolve.phenix_runtime.discover_phenix',discovery)
    monkeypatch.setitem(sys.modules,'nasolve.cif_mixed_endpoint',SimpleNamespace(qualify_saved_mixed_endpoint=qualify,read_saved_mixed_endpoint=read))
    monkeypatch.setattr('subprocess.Popen',forbidden)
    args=['endpoint-probe','--review-zip',str(path),'--phenix-root',str(sdk.root),'--output-parent',str(tmp_path/'outputs')]
    if inspect_only:args.append('--inspect-only')
    if seconds is not None:args.extend(['--timeout-seconds',str(seconds)])
    monkeypatch.setattr('sys.argv',args)
    assert ferry.main()==2
    assert events==['qualification','reader'] and len(discoveries)==int(not inspect_only)
    assert all(not p.exists() for p in views)
    assert path.read_bytes()==original_zip
    text=capsys.readouterr().out
    assert 'Saved endpoint qualification:' in text and 'REVIEW ZIP:' in text
    assert 'Automatic coordinate decision: CONTINUE_WITH_NOTES ; selected: verified_constructed_model' in text
    archive=next((tmp_path/'outputs').glob('*/*_review.zip'))
    with ZipFile(archive) as captured:returned={n:captured.read(n) for n in captured.namelist()}
    assert returned['inputs/parent_review.zip']==original_zip
    assert not any(n.startswith(('parent_views/','inputs/review/')) for n in returned)
    receipt=json.loads(returned['probe_receipt.json']);report_data=returned['mixed_endpoint/mixed_endpoint_qualification.json']
    assert receipt['analysis_completed'] and receipt['parent_review_preserved'] and receipt['frozen_runtime_preserved']
    assert receipt['mixed_endpoint']=={'directory':{'anchor':'probe_directory','path':'mixed_endpoint'},
        'report_sha256':sha256(report_data).hexdigest(),'report_size':len(report_data),
        'status':result['status'],'new_native_calls':result['new_native_calls']}
    assert receipt['model_optimization_requested'] is False and receipt['requires_cif_review'] is False
    assert receipt['parent_review']['payload_count']==len(original_members)


def test_endpoint_ferry_build_relocates_without_sources_and_preserves_failure_capsule(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import restraints
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source, nar = tmp_path/'source', tmp_path/'nar'
    for relative in ['src/nasolve', 'MR_frames/5W6W']:
        shutil.copytree(ROOT/relative, source/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml', 'scripts/mixed_endpoint_probe_template.py']:
        path = source/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, path)
    shutil.copytree(Path(restraints.__file__).parent, nar/'restraints', ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source)
    _initialize_git(nar)
    spec = importlib.util.spec_from_file_location('torsion_builder', ROOT/'scripts/build_synthetic_dna_shuttle.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    runner = tmp_path/'relocated/92_Cedar_probe_mixed_endpoints.py'
    metadata = builder.build(source, nar, runner, template_name='mixed_endpoint_probe_template.py')
    assert metadata['kind'] == 'mixed-endpoint-shuttle' and metadata['delivery_prefix'] == '92_Cedar'
    assert not metadata['private_diffraction_included'] and not metadata['automatic_adoption']
    assert not any(name.endswith('.zip') for name in metadata['runtime_files'])
    shutil.rmtree(source)
    shutil.rmtree(nar)
    result = subprocess.run([sys.executable, '-B', str(runner), '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert all(name in result.stdout for name in ['--review-zip', '--inspect-only', '--timeout-seconds', '--phenix-root'])
    assert '--max-iterations' not in result.stdout
    wrapper_help = subprocess.run([sys.executable, '-B', str(ROOT/'scripts/build_mixed_endpoint_probe.py'), '--help'], capture_output=True, text=True)
    assert wrapper_help.returncode == 0 and '--local-artifact-checkout' in wrapper_help.stdout
    configuration = tmp_path/'config.json'
    original = b'{"workspace":{"run":"PRESERVE"}}\n'
    configuration.write_bytes(original)
    poison = tmp_path/'poison'
    for package in ['nasolve', 'restraints']:
        path = poison/package
        path.mkdir(parents=True)
        (path/'__init__.py').write_text('raise RuntimeError("AMBIENT_IMPORT")\n')
    guard = tmp_path/'guard.py'
    guard.write_text('import runpy,subprocess,sys\ndef forbidden(*a,**k):raise AssertionError("NO_SDK")\nsubprocess.Popen=forbidden\np=sys.argv.pop(1)\nrunpy.run_path(p,run_name="__main__")\n')
    bad = tmp_path/'bad.zip'
    bad.write_bytes(b'NOT A VERIFIED RETURN')
    result = subprocess.run([sys.executable, '-B', str(guard), str(runner), '--inspect-only',
        '--review-zip', str(bad), '--output-parent', str(tmp_path/'outputs')],
        capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(poison),
            'PYTHONDONTWRITEBYTECODE': '1', 'NASOLVE_CONFIG_FILE': str(configuration)})
    assert result.returncode == 2 and 'REVIEW ZIP:' in result.stdout and 'verified parent ZIP' in result.stderr
    assert 'AMBIENT_IMPORT' not in result.stderr and 'NO_SDK' not in result.stderr
    assert configuration.read_bytes() == original
    archive = next((tmp_path/'outputs').glob('*/*_review.zip'))
    with ZipFile(archive) as captured:
        returned = {name: captured.read(name) for name in captured.namelist()}
    receipt = json.loads(returned['probe_receipt.json'])
    assert not receipt['analysis_completed'] and not receipt['requires_cif_review'] and not receipt['automatic_adoption']
    assert receipt['captured_code_execution'] == 'NOT_RUN' and receipt['production_checkpoint'] == 'NOT_CREATED'
    assert receipt['model_optimization_requested'] is False
    assert not any(name.startswith('runtime/') for name in returned)
    manifest = json.loads(returned['manifest.json'])
    assert set(manifest) == set(returned)-{'manifest.json'}
    assert all(ref == {'bytes': len(returned[name]), 'sha256': sha256(returned[name]).hexdigest()}
               for name, ref in manifest.items())


@pytest.mark.parametrize('bound', ['single_member', 'entries', 'total_including_manifest'])
def test_endpoint_review_output_never_exceeds_unchanged_archive_bounds(tmp_path, monkeypatch, bound):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '92_Cedar'}
    session = tmp_path/'92_Cedar_mixed-endpoint-owned'
    session.mkdir()
    if bound == 'single_member':
        files = {'inputs/parent_review.zip': b'x'*(33*1024*1024)}
    elif bound == 'entries':
        files = {f'scientific/{i:04d}.bin': b'x' for i in range(1024)}
    else:
        payload = b'x'*(32*1024*1024)
        files = {f'scientific/{i}.bin': payload for i in range(4)}
    monkeypatch.setattr('nasolve.cif_review_transport.review_archive_files', lambda *args: files)
    with pytest.raises(ValueError, match='archive bounds'): ferry._review_zip(session)
    assert not list(session.glob('*.zip'))


def test_endpoint_oversized_output_keeps_parent_and_scientific_session_in_failure_capsule(tmp_path, monkeypatch):
    ferry = module()
    ferry.BUNDLE = {'delivery_prefix': '92_Cedar'}
    session = tmp_path/'92_Cedar_mixed-endpoint-owned'
    scientific = session/'mixed_endpoint/native.json'
    scientific.parent.mkdir(parents=True)
    original = b'COMPLETED SCIENTIFIC CAPTURE MUST REMAIN AVAILABLE\n'
    scientific.write_bytes(original)
    parent = session/'inputs/parent_review.zip'
    parent.parent.mkdir()
    parent_bytes = b'EXACT OPAQUE HISTORICAL PARENT\n'
    parent.write_bytes(parent_bytes)
    files = {'scientific/oversized.bin': b'x'*(33*1024*1024),
        'mixed_endpoint/native.json': original, 'inputs/parent_review.zip': parent_bytes}
    monkeypatch.setattr('nasolve.cif_review_transport.review_archive_files', lambda *args: files)
    receipt = {'schema_version': 1, 'analysis_completed': True,
        'automatic_adoption': False, 'requires_cif_review': False}
    archive = ferry._report_failure(session, receipt, ValueError('first native evidence failure'))
    assert archive.name.endswith('_failure_review.zip')
    assert scientific.read_bytes() == original and parent.read_bytes() == parent_bytes
    assert list(session.glob('*.zip')) == [archive]
    with ZipFile(archive) as captured:
        assert set(captured.namelist()) == {'probe_receipt.json', 'manifest.json'}
        data = captured.read('probe_receipt.json')
        result = json.loads(data)
        manifest = json.loads(captured.read('manifest.json'))
    assert result['analysis_completed'] is False
    assert result['error_type'] == 'ValueError' and result['error'] == 'first native evidence failure'
    assert 'archive bounds' in result['archive_collection_error']
    assert result['failure_archive_scope'] == 'RECEIPT_ONLY; OTHER_OUTPUTS_REMAIN_IN_SESSION'
    assert manifest == {'probe_receipt.json': {'bytes': len(data), 'sha256': sha256(data).hexdigest()}}
