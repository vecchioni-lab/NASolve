"""C93 accepts the exact C92 parent, keeps ancestry opaque and stages six views."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

import pytest

from tests.test_mixed_endpoint_probe import capsule as c91_capsule

ROOT=Path(__file__).parents[1]


def module():
    spec=importlib.util.spec_from_file_location('endpoint_window_ferry',ROOT/'scripts/mixed_endpoint_window_probe_template.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def pack(members,defect='none'):
    manifest={n:{'bytes':len(d),'sha256':sha256(d).hexdigest()} for n,d in members.items()}
    if defect=='hash':manifest['probe_receipt.json']['sha256']='0'*64
    elif defect=='inventory':manifest.pop('probe_receipt.json')
    raw=io.BytesIO()
    with ZipFile(raw,'w',ZIP_DEFLATED) as z:
        for n,d in members.items():
            info=ZipInfo(n);info.external_attr=(0o120777 if defect=='symlink' and n.endswith('.py') else 0o100644)<<16
            z.writestr(info,d,compress_type=ZIP_DEFLATED)
        if defect=='duplicate':
            with pytest.warns(UserWarning):z.writestr('probe_receipt.json',members['probe_receipt.json'])
        z.writestr('manifest.json',json.dumps(manifest))
    return raw.getvalue()


def capsule(tmp_path,defect='none'):
    inner_defect=defect[4:] if defect.startswith('c91_') else 'none'
    c91,c91sha,c91members,c90sha,_,c89sha,_=c91_capsule(tmp_path,inner_defect)
    decision=deepcopy(json.loads(c91members['mixed_torsion/mixed_torsion_audit.json'])['coordinate_decision'])
    decision.update(native_usable=True,endpoint_usable=False,continue_solving=True,selected='verified_constructed_model')
    report={'schema_version':1,'policy_id':'cif-mixed-saved-endpoint-qualification-v1','status':'REVIEW',
        'maximum_native_calls':2,'new_native_calls':1,'parent_archive_sha256':c91sha,
        'automatic_adoption':False,'requires_cif_review':False,'scientific_qualification':'NOT_ASSESSED',
        'execution':{'status':'COMPLETED','returncode':0},'qualification':{'status':'REVIEW'},
        'native_readback':{'status':'NOT_RUN'},'coordinate_decision':decision,'original_coordinate_decision':deepcopy(decision),
        **{k:'NOT_RUN' for k in ['model_optimization','dictionary_generation','readyset_execution','coot_execution',
            'refinement','cache_writes','captured_code_execution']}}
    mutations={'policy':('policy_id','OTHER'),'status':('status','MIXED_ENDPOINT_QUALIFIED'),
        'new_count':('new_native_calls',2),'new_count_bool':('new_native_calls',True),'max_count_bool':('maximum_native_calls',True),
        'adoption':('automatic_adoption',True),'approval':('requires_cif_review',True),'optimizer':('model_optimization','RAN'),
        'cache':('cache_writes','RAN'),'science':('scientific_qualification','APPROVED'),'parent_sha':('parent_archive_sha256','0'*64)}
    if defect in mutations:report[mutations[defect][0]]=mutations[defect][1]
    elif defect=='returncode_bool':report['execution']['returncode']=False
    elif defect=='returncode':report['execution']['returncode']=2
    elif defect=='qualification':report['qualification']['status']='PASS'
    elif defect=='readback':report['native_readback']={'status':'PASS'}
    elif defect=='decision':report['coordinate_decision']['selected']='qualified_geometry_endpoint'
    elif defect=='unusable':report['coordinate_decision']['native_usable']=False;report['original_coordinate_decision']['native_usable']=False
    rdata=json.dumps(report).encode()
    header={'schema_version':1,'kind':'mixed-endpoint-probe','delivery_prefix':'92_Cedar','analysis_completed':True,
        'automatic_adoption':False,'requires_cif_review':False,'parent_review_preserved':True,'frozen_runtime_preserved':True,
        'model_optimization_requested':False,'captured_code_execution':'NOT_RUN',
        'mixed_endpoint':{'directory':{'anchor':'probe_directory','path':'mixed_endpoint'},'report_sha256':sha256(rdata).hexdigest(),
            'report_size':len(rdata),'status':'REVIEW','new_native_calls':1},
        'parent_review':{'artifact':{'anchor':'probe_directory','path':'inputs/parent_review.zip','sha256':c91sha,'size':c91.stat().st_size},
            'payload_count':len(c91members),'preserved':True}}
    if defect=='header_kind':header['kind']='OTHER'
    elif defect=='header_prefix':header['delivery_prefix']='91_Cedar'
    elif defect=='incomplete':header['analysis_completed']=False
    elif defect=='header_approval':header['requires_cif_review']=True
    elif defect=='header_count_bool':header['mixed_endpoint']['new_native_calls']=True
    elif defect=='report_hash':header['mixed_endpoint']['report_sha256']='0'*64
    elif defect=='parent_anchor':header['parent_review']['artifact']['anchor']='UNKNOWN'
    elif defect=='parent_size':header['parent_review']['artifact']['size']+=1
    elif defect=='parent_count_bool':header['parent_review']['payload_count']=True
    elif defect=='parent_count':header['parent_review']['payload_count']+=1
    members={'probe_receipt.json':json.dumps(header).encode(),'inputs/parent_review.zip':c91.read_bytes(),
        'mixed_endpoint/mixed_endpoint_qualification.json':rdata,
        'mixed_endpoint/job/captured.py':b'raise RuntimeError("CAPTURED_C92_CODE_MUST_NOT_EXECUTE")\n',
        'unrelated/mixed_endpoint_qualification.json':b'DECOY'}
    if defect=='path':members['../outside']=b'BAD'
    elif defect=='oversize':members['saved/large.txt']=b'X'*(33*1024*1024)
    elif defect=='entries':members.update({f'saved/{i}.txt':b'X' for i in range(1024)})
    data=pack(members,defect);p=tmp_path/'c92-review.zip';p.write_bytes(data)
    ferry=module();ferry.REVIEW_SHA256=sha256(data).hexdigest();ferry.SCIENCE_PARENT_SHA256=c91sha
    ferry.TORSION_PARENT_SHA256=c90sha;ferry.GEOMETRY_PARENT_SHA256=c89sha
    return ferry,p,members,report


def test_exact_c92_archive_and_only_six_explicit_data_views_are_used(tmp_path):
    ferry,path,members,_=capsule(tmp_path);actual=ferry._read_capsule(path)
    views=ferry._materialize_inputs(actual,tmp_path/'views')
    assert tuple(p.name for p in views)==('previous_endpoint','torsion','geometry','gradient','context','linked_parent')
    assert (views[0]/'job/captured.py').read_bytes()==members['mixed_endpoint/job/captured.py']
    assert (views[1]/'job/captured.py').read_bytes().startswith(b'raise RuntimeError')
    assert not any(p.suffix=='.zip' for p in (tmp_path/'views').rglob('*'))
    assert not any('unrelated' in p.parts for p in (tmp_path/'views').rglob('*'))
    before={p:p.read_bytes() for view in views for p in view.rglob('*') if p.is_file()}
    with pytest.raises(FileExistsError):ferry._materialize_inputs(actual,tmp_path/'views')
    assert all(p.read_bytes()==d for p,d in before.items())


@pytest.mark.parametrize('defect',['hash','inventory','duplicate','symlink','path','oversize','entries',
    'header_kind','header_prefix','incomplete','header_approval','header_count_bool','report_hash','parent_anchor',
    'parent_size','parent_count_bool','parent_count','policy','status','new_count','new_count_bool','max_count_bool',
    'adoption','approval','optimizer','cache','science','parent_sha','returncode_bool','returncode','qualification',
    'readback','decision','unusable','c91_hash','c91_inventory','c91_symlink','c91_c90_hash','c91_c90_inner_hash'])
def test_rebound_bad_prior_evidence_or_nested_archives_cannot_reach_staging(tmp_path,defect):
    ferry,path,_,_=capsule(tmp_path,defect)
    with pytest.raises((ValueError,KeyError)):ferry._read_capsule(path)


def test_outer_c92_checksum_is_required(tmp_path):
    ferry,path,_,_=capsule(tmp_path);ferry.REVIEW_SHA256='a'*64
    with pytest.raises(ValueError):ferry._read_capsule(path)


@pytest.mark.parametrize('inspect_only',[True,False])
def test_main_replays_c92_science_then_runs_separate_window_and_keeps_one_opaque_parent(tmp_path,monkeypatch,capsys,inspect_only):
    import nasolve,restraints,sys
    import nasolve.cif_mixed_endpoint as old
    import nasolve.cif_mixed_endpoint_window as current
    ferry,path,_,prior=capsule(tmp_path);ferry.BUNDLE={'delivery_prefix':'93_Cedar'}
    runtime_members={'src/nasolve/__init__.py':b'', 'restraints/__init__.py':b''}
    monkeypatch.setattr(ferry,'_runtime_members',lambda:runtime_members)
    def isolated(runtime,session,members):
        for n,d in members.items():ferry._write(runtime/n,d)
        monkeypatch.setattr(nasolve,'__file__',str(runtime/'src/nasolve/__init__.py'))
        monkeypatch.setattr(restraints,'__file__',str(runtime/'restraints/__init__.py'))
    monkeypatch.setattr(ferry,'_isolate',isolated)
    order=[]
    def previous(root,**kwargs):
        order.append('verified_C92');assert root.name=='previous_endpoint'
        assert kwargs['parent_archive_sha256']==ferry.SCIENCE_PARENT_SHA256
        return prior
    monkeypatch.setattr(old,'read_saved_mixed_endpoint',previous)
    def qualify(*args,parent_archive_sha256,timeout_seconds):
        order.append('new_C93');assert order==['verified_C92','new_C93']
        assert [p.name for p in args[:5]]==['torsion','geometry','gradient','context','linked_parent']
        assert parent_archive_sha256==ferry.SCIENCE_PARENT_SHA256 and timeout_seconds==120
        report={'status':'PREPARED_ONLY' if inspect_only else 'REVIEW','new_native_calls':0,
            'coordinate_decision':{'status':'CONTINUE_WITH_NOTES','selected':'verified_constructed_model'}}
        ferry._write(args[-1]/current.REPORT,report);return report
    monkeypatch.setattr(current,'qualify_saved_mixed_endpoint',qualify)
    if not inspect_only:
        import nasolve.phenix_runtime
        monkeypatch.setattr(nasolve.phenix_runtime,'discover_phenix',lambda *a,**k:SimpleNamespace(version='EXPLICIT_FAKE',root=tmp_path,source='fixture',executables={}))
    monkeypatch.setattr(subprocess_module(),'Popen',lambda *a,**k:pytest.fail('ferry launched an unrequested process'))
    argv=['window','--review-zip',str(path),'--output-parent',str(tmp_path/'output')]
    if inspect_only:argv.append('--inspect-only')
    monkeypatch.setattr(sys,'argv',argv)
    assert ferry.main()==2
    assert order==['verified_C92','new_C93']
    archives=list((tmp_path/'output').glob('*/*_review.zip'));assert len(archives)==1
    with ZipFile(archives[0]) as z:
        names=z.namelist();assert z.read('inputs/parent_review.zip')==path.read_bytes()
        assert names.count('inputs/parent_review.zip')==1
        assert not any('previous_endpoint' in n or n.startswith('runtime/') for n in names)
        receipt=json.loads(z.read('probe_receipt.json'))
        assert receipt['analysis_completed'] and receipt['previous_endpoint_replay']['status']=='VERIFIED'
        assert receipt['mixed_endpoint_window']['directory']['path']=='mixed_endpoint_window'
        assert receipt['parent_review']['artifact']['sha256']==ferry.REVIEW_SHA256
    assert 'REVIEW ZIP:' in capsys.readouterr().out


def subprocess_module():
    import subprocess
    return subprocess


def test_window_probe_has_no_optimizer_cli(tmp_path,monkeypatch):
    import sys
    ferry=module();monkeypatch.setattr(ferry,'_runtime_members',lambda:pytest.fail('optimizer flag reached runtime'))
    monkeypatch.setattr(sys,'argv',['window','--review-zip',str(tmp_path/'absent'),'--max-iterations','1000'])
    with pytest.raises(SystemExit) as stopped:ferry.main()
    assert stopped.value.code==2
