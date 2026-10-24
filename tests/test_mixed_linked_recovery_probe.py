"""Bounded transport and separate linked-read evidence for the C83 capsule."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo
import pytest

ROOT=Path(__file__).parents[1]


def module():
    spec=importlib.util.spec_from_file_location('mixed_linked_recovery_ferry',ROOT/'scripts/mixed_linked_recovery_probe_template.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def capsule(tmp_path,defect='none'):
    main={'status':'MIXED_RECOVERY_ISOLATED_PASS','targets':['Q17']}
    header={'kind':'mixed-deficient-numerics-recovery-probe','delivery_prefix':'83_Cedar','analysis_completed':True,
            'mixed_recovery':{'directory':{'anchor':'probe_directory','path':'mixed_recovery'},**main}}
    members={'probe_receipt.json':json.dumps(header).encode(),'mixed_recovery/mixed_recovery.json':json.dumps(main).encode(),
        'mixed_recovery/inputs/model.pdb':b'EXACT SCIENTIFIC DATA\n',
        'mixed_recovery/native/captured.py':b'raise RuntimeError("CAPTURED_CODE_MUST_NOT_RUN")\n',
        'inputs/review/mixed_native/inputs/plan.json':b'{"frozen":true}\n'}
    if defect=='large':members['mixed_native/large_report.json']=b' '* (21*1024*1024)
    if defect=='oversize':members['mixed_native/oversize.json']=b' '* (33*1024*1024)
    if defect=='path':members['../outside']=b'BAD'
    if defect=='status':
        main['status']='REVIEW';members['mixed_recovery/mixed_recovery.json']=json.dumps(main).encode()
    if defect=='receipt':
        header['analysis_completed']=False;members['probe_receipt.json']=json.dumps(header).encode()
    manifest={n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in members.items()}
    if defect=='hash':manifest['mixed_recovery/inputs/model.pdb']['sha256']='0'*64
    if defect=='inventory':manifest.pop('probe_receipt.json')
    raw=io.BytesIO()
    with ZipFile(raw,'w') as z:
        for name,data in members.items():
            entry=ZipInfo(name);entry.external_attr=(0o120777 if defect=='symlink' and name.endswith('.pdb') else 0o100644)<<16
            z.writestr(entry,data)
        if defect=='duplicate':
            with pytest.warns(UserWarning):z.writestr('probe_receipt.json',members['probe_receipt.json'])
        z.writestr('manifest.json',json.dumps(manifest))
    path=tmp_path/'review.zip';path.write_bytes(raw.getvalue());return path,sha256(raw.getvalue()).hexdigest(),members


@pytest.mark.parametrize('defect',['none','large','oversize','path','hash','inventory','symlink','duplicate','archive','status','receipt'])
def test_capsule_bounds_and_exact_manifest_precede_scientific_reads(tmp_path,defect):
    m=module();path,digest,members=capsule(tmp_path,defect);m.REVIEW_SHA256='0'*64 if defect=='archive' else digest
    if defect in {'none','large'}:
        actual=m._read_capsule(path);assert {n:actual[n] for n in members}==members
    else:
        with pytest.raises(ValueError):m._read_capsule(path)
    assert not (tmp_path/'outside').exists()


def test_shallow_parent_view_keeps_captured_code_as_unexecuted_data(tmp_path):
    m=module();path,digest,members=capsule(tmp_path);m.REVIEW_SHA256=digest
    view,parent=m._materialize_parents(m._read_capsule(path),tmp_path/'parent')
    assert (parent/'inputs/plan.json').read_bytes()==members['inputs/review/mixed_native/inputs/plan.json']
    assert (view/'inputs/model.pdb').read_bytes()==members['mixed_recovery/inputs/model.pdb']
    assert (view/'native/captured.py').read_bytes()==members['mixed_recovery/native/captured.py']
    assert not (view/'probe_receipt.json').exists()


def test_built_recovery_ferry_relocates_without_source_and_keeps_failure_capsule(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import restraints
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source=tmp_path/'source';nar=tmp_path/'nar'
    for relative in ['src/nasolve','MR_frames/5W6W']:
        shutil.copytree(ROOT/relative,source/relative,ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml','scripts/mixed_linked_recovery_probe_template.py']:
        p=source/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,p)
    shutil.copytree(Path(restraints.__file__).parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source);_initialize_git(nar)
    spec=importlib.util.spec_from_file_location('mixed_linked_recovery_builder',ROOT/'scripts/build_synthetic_dna_shuttle.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    runner=tmp_path/'relocated/84_Cedar_probe_mixed_linked_recovery.py'
    metadata=builder.build(source,nar,runner,template_name='mixed_linked_recovery_probe_template.py')
    assert metadata['kind']=='mixed-linked-recovery-shuttle' and metadata['delivery_prefix']=='84_Cedar'
    assert not metadata['private_diffraction_included'] and not metadata['automatic_adoption']
    assert not any('review.zip' in name for name in metadata['runtime_files'])
    shutil.rmtree(source);shutil.rmtree(nar)
    result=subprocess.run([sys.executable,'-B',str(runner),'--help'],capture_output=True,text=True)
    assert result.returncode==0 and '--review-zip' in result.stdout and '--inspect-only' in result.stdout
    config=tmp_path/'config.json';original=b'{"workspace":{"run":"PRESERVE"}}\n';config.write_bytes(original)
    poison=tmp_path/'poison'
    for package in ['nasolve','restraints']:
        path=poison/package;path.mkdir(parents=True);(path/'__init__.py').write_text('raise RuntimeError("AMBIENT_IMPORT")\n')
    guard=tmp_path/'guard.py'
    guard.write_text('import runpy,subprocess,sys\ndef forbidden(*a,**k):raise AssertionError("NO_SDK")\nsubprocess.Popen=forbidden\np=sys.argv.pop(1)\nrunpy.run_path(p,run_name="__main__")\n')
    bad=tmp_path/'bad.zip';bad.write_bytes(b'NOT A VERIFIED RETURN')
    result=subprocess.run([sys.executable,'-B',str(guard),str(runner),'--inspect-only','--review-zip',str(bad),
        '--output-parent',str(tmp_path/'outputs')],capture_output=True,text=True,
        env={**os.environ,'PYTHONPATH':str(poison),'PYTHONDONTWRITEBYTECODE':'1','NASOLVE_CONFIG_FILE':str(config)})
    assert result.returncode==2 and 'REVIEW ZIP:' in result.stdout and 'exact verified C83' in result.stderr
    assert 'AMBIENT_IMPORT' not in result.stderr and 'NO_SDK' not in result.stderr
    assert config.read_bytes()==original
    archive=next((tmp_path/'outputs').glob('*/*_review.zip'))
    with ZipFile(archive) as z:
        report=json.loads(z.read('probe_receipt.json'))
        assert not report['analysis_completed'] and not report['requires_cif_review'] and not report['automatic_adoption']
        assert report['captured_code_execution']=='NOT_RUN' and report['production_checkpoint']=='NOT_CREATED'
        assert not any(n.startswith('runtime/') for n in z.namelist())
        manifest=json.loads(z.read('manifest.json'))
        assert set(manifest)==set(z.namelist())-{'manifest.json'}
        for name,ref in manifest.items():assert ref=={'bytes':len(z.read(name)),'sha256':sha256(z.read(name)).hexdigest()}
