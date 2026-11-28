"""A native ferry must consume bounded verified data without executing it."""
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).parents[1]


def module():
    path = ROOT/'scripts/mixed_native_probe_template.py'
    spec = importlib.util.spec_from_file_location('mixed_native_ferry', path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def capsule(tmp_path, defect):
    data = {'probe_receipt.json': json.dumps({'kind':'mixed-eight-pair-construction-probe',
        'delivery_prefix':'81_Cedar','analysis_completed':True,
        'mixed_pair_fixture':{'status':'MIXED_PAIR_CONSTRUCTION_PASS'}}).encode(),
        'postmr_construction/mixed_pair_fixture.json':b'{}',
        'postmr_construction/model/constructed_model.pdb':b'EXACT MODEL\n',
        'postmr_construction/model/Coot/mutation.py':b'raise RuntimeError("CAPTURED_CODE")\n'}
    if defect == 'path':data['../outside'] = b'BAD'
    manifest = {n:{'sha256':sha256(d).hexdigest(),'bytes':len(d)} for n,d in data.items()}
    if defect == 'hash':manifest['postmr_construction/model/constructed_model.pdb']['sha256'] = '0'*64
    if defect == 'inventory':manifest.pop('probe_receipt.json')
    raw = io.BytesIO()
    with ZipFile(raw,'w') as z:
        for name,value in data.items():
            entry = ZipInfo(name)
            entry.external_attr = (0o120777 if defect=='symlink' and name.endswith('.pdb') else 0o100644)<<16
            z.writestr(entry,value)
        if defect == 'duplicate':
            with pytest.warns(UserWarning):z.writestr('probe_receipt.json',data['probe_receipt.json'])
        z.writestr('manifest.json',json.dumps(manifest))
    path=tmp_path/'review.zip';path.write_bytes(raw.getvalue())
    return path,sha256(raw.getvalue()).hexdigest(),data


@pytest.mark.parametrize('defect',['none','hash','inventory','path','symlink','duplicate','archive'])
def test_return_capsule_requires_exact_manifest_and_archive(tmp_path,defect):
    m=module();path,digest,data=capsule(tmp_path,defect)
    m.REVIEW_SHA256='0'*64 if defect=='archive' else digest
    if defect=='none':assert m._read_capsule(path)=={**data,'manifest.json':ZipFile(path).read('manifest.json')}
    else:
        with pytest.raises(ValueError):m._read_capsule(path)
    assert not (tmp_path/'outside').exists()


def test_scientific_materialization_does_not_make_captured_code_importable(tmp_path):
    m=module();path,digest,data=capsule(tmp_path,'none');m.REVIEW_SHA256=digest
    members=m._read_capsule(path)
    root=m._materialize_fixture(members,tmp_path/'fixture')
    assert (root/'model/constructed_model.pdb').read_bytes()==b'EXACT MODEL\n'
    assert not (root/'model/Coot/mutation.py').exists()
    assert not (root/'probe_receipt.json').exists()


def test_built_native_ferry_relocates_without_source_and_keeps_failure_capsule(tmp_path):
    import os
    import shutil
    import subprocess
    import sys
    import restraints
    from tests.test_synthetic_dna_shuttle import _initialize_git
    source=tmp_path/'source';nar=tmp_path/'nar'
    for relative in ['src/nasolve','MR_frames/5W6W']:
        shutil.copytree(ROOT/relative,source/relative,ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['docs/recipes/synthetic-dna-combined.toml','scripts/mixed_native_probe_template.py']:
        p=source/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,p)
    shutil.copytree(Path(restraints.__file__).parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    _initialize_git(source);_initialize_git(nar)
    spec=importlib.util.spec_from_file_location('mixed_native_builder',ROOT/'scripts/build_synthetic_dna_shuttle.py')
    builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    runner=tmp_path/'relocated/82_Cedar_probe_mixed_native.py'
    metadata=builder.build(source,nar,runner,template_name='mixed_native_probe_template.py')
    assert metadata['kind']=='mixed-eight-pair-native-shuttle' and metadata['delivery_prefix']=='82_Cedar'
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
    assert result.returncode==2 and 'REVIEW ZIP:' in result.stdout and 'exact verified C81' in result.stderr
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
