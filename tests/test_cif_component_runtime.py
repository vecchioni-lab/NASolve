"""Public-reader integration using an explicit synthetic native verifier.

Real frozen-source/native/CLI controls are recorded separately. These fixtures
exercise selection/resource/provenance wiring, not scientific qualification.
"""
from copy import deepcopy
from pathlib import Path
import json,shutil
from unittest.mock import patch
import pytest


def fixture(tmp_path,monkeypatch,selected='readyset_ordered_checked_model'):
    from nasolve import cif_component_runtime as runtime
    from tests.test_cif_runtime_bundle import case
    model,cifs,phils,_,_,_=case(tmp_path/'original')
    extra=tmp_path/'original/second.phil';extra.write_text('# explicit second parameter input\n');phils.append(extra)
    base=tmp_path/'evidence';base.mkdir()
    for name in ['bundle','readyset','baseline','candidate','endpoint','atom-order']:
        (base/name).mkdir();(base/name/'data').write_text('FROZEN '+name)
    for name in ['baseline','candidate','endpoint']:(base/name/'native_receipt.json').write_text('{}')
    for name in ['bundle','readyset']:
        shutil.copyfile(model,base/name/'model.pdb')
        for i,p in enumerate(cifs):shutil.copyfile(p,base/name/f'{i}.cif')
        for i,p in enumerate(phils):shutil.copyfile(p,base/name/f'{i}.phil')
    (base/'readyset/0.cif').write_bytes((base/'readyset/0.cif').read_bytes()+b'# DISTINCT EFFECTIVE\n')
    state=dict(selected=selected)
    def inputs(root):
        root=Path(root);return dict(model=root/'model.pdb',dictionaries=[root/f'{i}.cif' for i in range(len(cifs))],phils=[root/f'{i}.phil' for i in range(len(phils))])
    def bundle(root):
        result=inputs(root);return dict(model=result['model'],after_dictionaries=result['dictionaries'],after_phils=result['phils'])
    def inspect(bundle,baseline_receipt,candidate_receipt,readyset_directory,endpoint_receipt=None,**kwargs):
        return dict(decision=dict(status='CONTINUE_WITH_NOTES' if state['selected'] else 'NO_USABLE_MODEL',selected=state['selected'],
            scope='SEPARATE_DIAGNOSTIC_PHASE_ONLY',automatic_adoption=False,requires_cif_review=False),
            initial=dict(qualification=dict(checks=[dict(check='charge',status='UNSUPPORTED')])),
            endpoint_error='Missing '+str(readyset_directory/'missing.json') if state['selected']=='verified_prepared_model' else None)
    monkeypatch.setattr(runtime,'read_dictionary_bundle',bundle)
    monkeypatch.setattr(runtime,'readyset_endpoint_inputs',lambda bundle,readyset,**k:inputs(readyset))
    monkeypatch.setattr(runtime,'inspect_dictionary_bundle_readyset',inspect)
    args=dict(bundle=base/'bundle',baseline_receipt=base/'baseline/native_receipt.json',candidate_receipt=base/'candidate/native_receipt.json',
        readyset_directory=base/'readyset',endpoint_receipt=base/'endpoint/native_receipt.json',atom_order_directory=base/'atom-order')
    return runtime,args,state


@pytest.mark.parametrize('selected',['readyset_ordered_checked_model','readyset_checked_model','verified_prepared_model'])
def test_public_reader_selects_model_and_exact_restraints_together(tmp_path,monkeypatch,selected):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle,assess_runtime_bundle
    runtime,args,state=fixture(tmp_path,monkeypatch,selected)
    expected=(args['bundle'] if selected=='verified_prepared_model' else args['readyset_directory'])/'0.cif'
    original=expected.read_bytes();out=tmp_path/'runtime'
    manifest=runtime.prepare_component_runtime_bundle(output=out,**args)
    files={p.relative_to(out):p.read_bytes() for p in out.rglob('*') if p.is_file()}
    resolved=resolve_runtime_bundle(out);assert resolved['dictionaries'][0].read_bytes()==original
    report=assess_runtime_bundle(out)['solution_report']
    assert report['selected_candidate']==selected and report['qualification_scope']=='SEPARATE_DIAGNOSTIC_PHASE_ONLY'
    assert report['checkpoint_adoption']=='NOT_RUN' and not report['requires_cif_review']
    assert ('starting model' in report['text'])==(selected=='verified_prepared_model')
    assert report['unavailable_native_checks']==[{'check':'charge','status':'UNSUPPORTED'}]
    assert files=={p.relative_to(out):p.read_bytes() for p in out.rglob('*') if p.is_file()}
    assert not manifest['automatic_adoption']


@pytest.mark.parametrize('defect',['model','dictionary','phil','source','decision','scope','adoption','order','alias','traversal','bool_size','rehash','extra','symlink','review'])
def test_forged_export_cannot_replace_verified_selection(tmp_path,monkeypatch,defect):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    runtime,args,state=fixture(tmp_path,monkeypatch);out=tmp_path/'runtime'
    m=runtime.prepare_component_runtime_bundle(output=out,**args);p=out/'runtime_bundle.json'
    if defect in ['model','dictionary','phil']:
        ref=m['resources']['model'] if defect=='model' else m['resources']['dictionaries' if defect=='dictionary' else 'phils'][0]
        (out/ref['relative_path']).write_text('changed')
    elif defect=='source':(out/'evidence/bundle/data').write_text('changed')
    elif defect=='decision':m['decision']['selected']='verified_prepared_model'
    elif defect=='scope':m['decision']['scope']='ORDINARY_REFINEMENT'
    elif defect=='adoption':m['automatic_adoption']=True
    elif defect=='order':m['resources']['phils'].reverse()
    elif defect=='alias':m['resources']['phils'][0]=deepcopy(m['resources']['dictionaries'][0])
    elif defect=='traversal':m['source_selection']['baseline_receipt']='../outside'
    elif defect=='bool_size':m['resources']['model']['size']=True
    elif defect=='rehash':
        from hashlib import sha256
        ref=m['resources']['dictionaries'][0];q=out/ref['relative_path'];q.write_bytes(q.read_bytes()+b'# changed\n')
        ref.update(size=q.stat().st_size,sha256=sha256(q.read_bytes()).hexdigest())
        for row in m['files']:
            if row['relative_path']==ref['relative_path']:row.update(ref)
    elif defect=='extra':(out/'unexpected').write_text('extra')
    elif defect=='symlink':q=out/'evidence/bundle/data';q.unlink();q.symlink_to(args['bundle']/'data')
    elif defect=='review':m['source_review']['initial']['qualification']['checks']=[]
    p.write_text(json.dumps(m))
    with pytest.raises(ValueError):resolve_runtime_bundle(out)


def test_cold_relocation_and_public_json_do_not_execute_native_programs(tmp_path,monkeypatch,capsys):
    from nasolve.cli import main
    runtime,args,_=fixture(tmp_path,monkeypatch);out=tmp_path/'runtime';runtime.prepare_component_runtime_bundle(output=out,**args)
    shutil.rmtree(tmp_path/'evidence');shutil.rmtree(tmp_path/'original');moved=out.rename(tmp_path/'moved')
    with patch('subprocess.Popen',side_effect=AssertionError('No external tools')):
        assert main(['cif-doctor','assess','--bundle',str(moved),'--json']) in (0,2)
    report=json.loads(capsys.readouterr().out)['solution_report']
    assert report['selected_candidate']=='readyset_ordered_checked_model' and report['native_selection_executed'] is False


def test_no_usable_start_is_not_materialized(tmp_path,monkeypatch):
    runtime,args,_=fixture(tmp_path,monkeypatch,None)
    with pytest.raises(ValueError):runtime.prepare_component_runtime_bundle(output=tmp_path/'runtime',**args)
    assert not (tmp_path/'runtime').exists()


@pytest.mark.parametrize('defect',['source_symlink','output_exists','file_budget','byte_budget'])
def test_snapshot_is_bounded_and_destination_exclusive(tmp_path,monkeypatch,defect):
    runtime,args,_=fixture(tmp_path,monkeypatch);out=tmp_path/'runtime'
    if defect=='source_symlink':(args['bundle']/'link').symlink_to(args['bundle']/'data')
    elif defect=='output_exists':out.mkdir();(out/'owned').write_text('preserved')
    elif defect=='file_budget':monkeypatch.setattr(runtime,'MAX_FILES',1)
    else:monkeypatch.setattr(runtime,'MAX_BYTES',1)
    with pytest.raises((ValueError,FileExistsError)):runtime.prepare_component_runtime_bundle(output=out,**args)
    if defect=='output_exists':assert (out/'owned').read_text()=='preserved'


def test_assessment_rechecks_changed_evidence(tmp_path,monkeypatch):
    from nasolve.cif_runtime_bundle import assess_runtime_bundle
    from nasolve import cif_doctor
    runtime,args,_=fixture(tmp_path,monkeypatch);out=tmp_path/'runtime';runtime.prepare_component_runtime_bundle(output=out,**args)
    original=cif_doctor.assess_dictionaries
    def changed(*a,**k):
        result=original(*a,**k);(out/'evidence/bundle/data').write_text('changed');return result
    monkeypatch.setattr(cif_doctor,'assess_dictionaries',changed)
    with pytest.raises(ValueError):assess_runtime_bundle(out)


def test_absent_readyset_error_remains_portable_after_publication(tmp_path,monkeypatch):
    from nasolve.cif_runtime_bundle import resolve_runtime_bundle
    runtime,args,_=fixture(tmp_path,monkeypatch,'verified_prepared_model')
    args['readyset_directory']=None;args['endpoint_receipt']=None
    out=tmp_path/'runtime';manifest=runtime.prepare_component_runtime_bundle(output=out,**args)
    assert manifest['source_review']['endpoint_error']=='Missing runtime_bundle/evidence/readyset/missing.json'
    moved=out.rename(tmp_path/'relocated')
    assert resolve_runtime_bundle(moved)['manifest']==manifest
