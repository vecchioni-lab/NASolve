"""Provenance transport over explicit synthetic stage/capture fixtures."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from tests.test_cif_construction_provenance import fixture_native, pdb

ROOT=Path(__file__).resolve().parents[1]


def template():
    spec=importlib.util.spec_from_file_location('construction_template',ROOT/'scripts/cif_construction_probe_template.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def inputs(tmp_path):
    from nasolve.cif_captured_geometry import review_captured_geometry
    module=template();run=tmp_path/'run'
    prepared=pdb(run/'PostMR/Model/prepared_model.pdb',distance=5.)
    pdb(run/'PostMR/Model/after_coot_raw.pdb');pdb(run/'PostMR/Model/after_coot_geometry.pdb',distance=5.)
    pdb(run/'PostMR/Coot/parent_Z_9_DG.pdb',distance=5.,code='DG')
    (run/'PostMR/Coot/mutate.py').write_text("import coot\ncoot.write_pdb_file(imol, '/old/run/PostMR/Coot/parent_Z_9_DG.pdb')\nprint('NASOLVE_OVERLAP', 'Z:9', overlap_status)\n")
    binding={'path':'PostMR/Model/prepared_model.pdb','sha256':hashlib.sha256(prepared.read_bytes()).hexdigest(),'size':prepared.stat().st_size}
    n=fixture_native();g=review_captured_geometry(n);data=json.dumps(n).encode();prefix=module.CAPTURE_PREFIX
    capture={'native_validation':n,'execution':{'status':'COMPLETED','returncode':0},'inputs':[],
             'outputs':[{'anchor':'native_directory','path':'native_validation.json','sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}]}
    entries={prefix+'/native_validation.json':data,prefix+'/native_receipt.json':json.dumps(capture).encode(),
             'captured_geometry_review.json':json.dumps(g).encode(),
             'probe_receipt.json':json.dumps({'kind':'cif-captured-geometry-review-probe','delivery_prefix':'15_Cedar',
                'status':'REVIEW','analysis_completed':True,'original_archive_preserved':True,'frozen_inputs_preserved':True,
                'geometry_summary':g['summary']}).encode()}
    entries.update({'padding/{:03d}.txt'.format(i):b'CHECK_EVERY_MEMBER' for i in range(51-len(entries))})
    protected=tmp_path/'protected';protected.mkdir();archive=protected/'review.zip';write(archive,entries)
    return archive,run,binding


def write(path,entries,defect=None):
    with zipfile.ZipFile(path,'w') as z:
        for name,data in entries.items():
            if defect=='symlink' and name=='padding/000.txt':
                info=zipfile.ZipInfo(name);info.external_attr=0o120777<<16;z.writestr(info,data)
            else:z.writestr(name,data)
        z.writestr('manifest.json',json.dumps({n:{'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()} for n,d in entries.items()}))
        if defect=='duplicate':
            with pytest.warns(UserWarning):z.writestr('padding/000.txt',b'other')


@pytest.mark.parametrize('defect',['changed_archive','unsafe','symlink','duplicate','unselected_member'])
def test_untrusted_capsules_are_rejected_before_original_run_access(tmp_path,defect):
    module=template();path,run,binding=inputs(tmp_path);expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if defect=='changed_archive':path.write_bytes(path.read_bytes()+b'changed')
    else:
        with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist() if n!='manifest.json'}
        if defect=='unsafe':entries['../escape']=entries.pop('padding/000.txt')
        write(path,entries,defect)
        if defect=='unselected_member':
            with zipfile.ZipFile(path) as z:entries={n:z.read(n) for n in z.namelist()}
            entries['padding/000.txt']=b'changed'
            with zipfile.ZipFile(path,'w') as z:
                for n,data in entries.items():z.writestr(n,data)
        expected=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):module._read_capsule(path,expected)


@pytest.mark.parametrize('changed',[False,True])
def test_cli_collects_stage_evidence_or_stops_at_the_original_binding(tmp_path,monkeypatch,changed):
    module=template();path,run,binding=inputs(tmp_path);original=path.read_bytes()
    module.BUNDLE={'delivery_prefix':'16_Cedar'};module.REVIEW_SHA256=hashlib.sha256(original).hexdigest()
    module.MODEL_BINDING=binding;module.HISTORICAL_RUN='/old/run'
    monkeypatch.setattr(module,'_runtime_members',lambda:{})
    monkeypatch.setattr(sys,'argv',['runner','--review-zip',str(path),'--run',str(run),'--output-parent',str(tmp_path/'out')])
    if changed:(run/binding['path']).write_text('replaced')
    before={p:p.read_bytes() for p in run.rglob('*') if p.is_file()}
    assert module.main()==2
    session=next((tmp_path/'out').iterdir());receipt=json.loads((session/'probe_receipt.json').read_text())
    assert receipt['analysis_completed'] is not changed and receipt['original_archive_preserved']
    assert receipt['native_execution']=='NOT_RUN' and receipt['model_editing']=='NOT_RUN'
    assert all(p.read_bytes()==data for p,data in before.items()) and path.read_bytes()==original
    if not changed:
        report=json.loads((session/'construction_provenance.json').read_text())
        assert report['first_observed_outlier_counts']=={'restored':1}
        assert report['threshold_crossing_count']==1 and report['root_cause']=='NOT_ESTABLISHED'


def test_source_bundled_runner_survives_deleted_builds_and_poisoned_imports(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from build_synthetic_dna_shuttle import build
    import restraints
    archive,run,binding=inputs(tmp_path);root=tmp_path/'build';nar=tmp_path/'nar'
    for relative in ['src','MR_frames/5W6W','docs/recipes']:
        shutil.copytree(ROOT/relative,root/relative,ignore=shutil.ignore_patterns('__pycache__'))
    (root/'scripts').mkdir();source=(ROOT/'scripts/cif_construction_probe_template.py').read_text();lines=source.splitlines(keepends=True)
    updates={'MODEL_BINDING':binding,'HISTORICAL_RUN':'/old/run','REVIEW_SHA256':hashlib.sha256(archive.read_bytes()).hexdigest()}
    nodes=[node for node in ast.parse(source).body if isinstance(node,ast.Assign)]
    for node in reversed(nodes):
        for target in node.targets:
            if isinstance(target,ast.Name) and target.id in updates:
                lines[node.lineno-1:node.end_lineno]=[target.id+' = '+repr(updates[target.id])+'\n']
    (root/'scripts/cif_construction_probe_template.py').write_text(''.join(lines))
    shutil.copytree(Path(restraints.__file__).resolve().parent,nar/'restraints',ignore=shutil.ignore_patterns('__pycache__'))
    for checkout in (root,nar):
        subprocess.run(['git','init',str(checkout)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(checkout),'-c','user.name=Test','-c','user.email=test@example.org','commit','-m','fixture'],check=True,capture_output=True)
    runner=tmp_path/'relocated/16_Cedar_probe_cif_construction.py'
    metadata=build(root,nar,runner,template_name='cif_construction_probe_template.py')
    assert metadata['kind']=='cif-construction-provenance-shuttle' and metadata['dependencies']==['Python >=3.10']
    shutil.rmtree(root);shutil.rmtree(nar)
    poison=tmp_path/'poison/nasolve';poison.mkdir(parents=True);(poison/'__init__.py').write_text('raise RuntimeError("poisoned import")\n')
    result=subprocess.run([sys.executable,'-B',str(runner),'--review-zip',str(archive),'--run',str(run),'--output-parent',str(tmp_path/'out')],capture_output=True,text=True,cwd=tmp_path,env={**os.environ,'PYTHONPATH':str(poison.parent)})
    assert result.returncode==2 and 'Diagnostic: REVIEW' in result.stdout and not result.stderr
    receipt=json.loads(next((tmp_path/'out').glob('*/probe_receipt.json')).read_text())
    assert receipt['analysis_completed'] and receipt['original_run_preserved'] and receipt['root_cause']=='NOT_ESTABLISHED'
