"""Explicit native execution must retain failure and restore process bindings."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS
import pytest
from tests.test_cif_parallelity_kernel import setup, Buffer


def runtime(monkeypatch, program=None, verify=None):
    from nasolve import cif_refinement_runtime as module
    points,p,gr,flex=setup()
    result=NS(model=NS(restraints_manager=NS(geometry=NS(
        parallelity_proxies=[p], site_symmetry_table=NS(special_position_indices=lambda:[]))),
        get_hierarchy=lambda:NS(atoms=lambda:[NS(id_str=lambda i=i:str(i)) for i in range(len(points))])),
        iparams=NS(refinement=NS(dry_run=True)),macro_cycle=1,
        params=NS(main=NS(number_of_macro_cycles=1)))
    def default(args):
        for _ in range(3):
            gr.parallelity_residual_sum(sites_cart=Buffer(points),proxies=[p],gradient_array=Buffer([(0.,0.,0.)]*len(points)))
        return result
    original=gr.parallelity_residual_sum
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,flex,program or default,dict(profile_id='test'),verify or (lambda:None)))
    return module,gr,result,original


def test_native_result_and_arguments_preserved_with_deduplicated_observations(tmp_path,monkeypatch):
    module,gr,result,original=runtime(monkeypatch)
    args=['model.pdb','target.params'];saved=list(args)
    actual=module.run_compatible_refinement(args,evidence_directory=tmp_path/'native')
    assert actual is result and args==saved and gr.parallelity_residual_sum==original
    record=json.loads((tmp_path/'native/result.json').read_text())
    assert record['status']=='COMPLETE' and record['binding_restored'] and record['dry_run']
    assert record['macro_cycles']==0 and len(record['usage_observations'])==1
    assert record['parent_kernel_statistics']['successful_calls']==3
    row=json.loads(next((tmp_path/'native/calls').glob('*.json')).read_text())
    assert row['parameters']['proxies']==record['parallelity_parameters']
    assert record['scientific_approval']=='NOT_RUN'


@pytest.mark.parametrize('failure',['native','verify','binding','special_position','mode','cycles'])
def test_failure_is_recorded_and_original_binding_restored(tmp_path,monkeypatch,failure):
    module,gr,result,original=runtime(monkeypatch)
    def program(args):
        if failure=='native':raise RuntimeError('native line search failed')
        if failure=='binding':gr.parallelity_residual_sum=lambda **kw:0.
        return result
    if failure=='special_position':result.model.restraints_manager.geometry.site_symmetry_table.special_position_indices=lambda:[0]
    if failure=='mode':result.iparams.refinement.dry_run=None
    if failure=='cycles':result.iparams.refinement.dry_run=False;result.macro_cycle=0
    def verify():
        if failure=='verify':raise ValueError('native sources changed')
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,setup()[3],program,dict(profile_id='test'),verify))
    with pytest.raises((RuntimeError,ValueError)):
        module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native')
    record=json.loads((tmp_path/'native/result.json').read_text())
    assert record['status']=='FAILED' and record['binding_restored']
    assert record['error']['message'] and gr.parallelity_residual_sum==original


def test_unqualified_runtime_never_calls_native_program(tmp_path,monkeypatch):
    from nasolve import cif_refinement_runtime as module
    def refused():raise ValueError('source profile mismatch')
    monkeypatch.setattr(module,'_native_runtime',refused)
    with pytest.raises(ValueError,match='source profile'):
        module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native')
    record=json.loads((tmp_path/'native/result.json').read_text())
    assert record['status']=='FAILED' and not record['binding_restored']


def test_existing_attempt_is_not_overwritten(tmp_path,monkeypatch):
    module,gr,result,original=runtime(monkeypatch)
    root=tmp_path/'native';root.mkdir();(root/'result.json').write_text('original partial')
    with pytest.raises(FileExistsError):module.run_compatible_refinement(['model.pdb'],evidence_directory=root)
    assert (root/'result.json').read_text()=='original partial' and gr.parallelity_residual_sum==original


def test_actual_cycle_count_is_required_and_recorded(tmp_path,monkeypatch):
    module,gr,result,original=runtime(monkeypatch);result.iparams.refinement.dry_run=False
    module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native')
    record=json.loads((tmp_path/'native/result.json').read_text())
    assert not record['dry_run'] and record['macro_cycles']==1


def test_parameter_changes_are_retained_instead_of_overwriting_prior_calls(tmp_path,monkeypatch):
    module,gr,result,original=runtime(monkeypatch)
    points,p,_,flex=setup()
    def program(args):
        for value in [1.4,2.7,1.4]:
            p.limit=value
            gr.parallelity_residual_sum(sites_cart=Buffer(points),proxies=[p],gradient_array=None)
        return result
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,flex,program,dict(profile_id='test'),lambda:None))
    module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native')
    rows=[json.loads(p.read_text()) for p in (tmp_path/'native/calls').glob('*.json')]
    assert len(rows)==2
    assert sorted(r['parameters']['proxies'][0]['limit'] for r in rows)==[1.4,2.7]
