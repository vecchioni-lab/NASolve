"""Explicit native execution must retain failure and restore process bindings."""
from copy import deepcopy
import json
from types import SimpleNamespace as NS
import pytest
from tests.test_cif_parallelity_kernel import setup, Buffer


def output_row(count):
    return dict(policy_id='native-refinement-output-state-v1',status='SYNCHRONIZED',
        atom_count=count,changed_adp_atoms=count,scattering_sha256='a'*64,
        hierarchy_before_sha256='b'*64,hierarchy_after_sha256='c'*64,fcalc_sha256='d'*64,
        scattering_unchanged=True,geometry_owner_unchanged=True,write_completed=True)


def output(result, observe):
    observe([] if result.iparams.refinement.dry_run else
            [output_row(len(result.model.get_hierarchy().atoms()))],True)


def runtime(monkeypatch, program=None, verify=None):
    from nasolve import cif_refinement_runtime as module
    points,p,gr,flex=setup()
    result=NS(model=NS(restraints_manager=NS(geometry=NS(
        parallelity_proxies=[p], site_symmetry_table=NS(special_position_indices=lambda:[]))),
        get_hierarchy=lambda:NS(atoms=lambda:[NS(id_str=lambda i=i:str(i)) for i in range(len(points))])),
        iparams=NS(refinement=NS(dry_run=True)),macro_cycle=1,
        params=NS(main=NS(number_of_macro_cycles=1)))
    def default(args,observe):
        for _ in range(3):
            gr.parallelity_residual_sum(sites_cart=Buffer(points),proxies=[p],gradient_array=Buffer([(0.,0.,0.)]*len(points)))
        output(result,observe)
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
    def program(args,observe):
        if failure=='native':raise RuntimeError('native line search failed')
        if failure=='binding':gr.parallelity_residual_sum=lambda **kw:0.
        output(result,observe)
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
    def program(args,observe):
        for value in [1.4,2.7,1.4]:
            p.limit=value
            gr.parallelity_residual_sum(sites_cart=Buffer(points),proxies=[p],gradient_array=None)
        output(result,observe)
        return result
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,flex,program,dict(profile_id='test'),lambda:None))
    module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native')
    rows=[json.loads(p.read_text()) for p in (tmp_path/'native/calls').glob('*.json')]
    assert len(rows)==2
    assert sorted(r['parameters']['proxies'][0]['limit'] for r in rows)==[1.4,2.7]


@pytest.mark.parametrize('defect',['missing','repeated','unfinished','binding'])
def test_actual_refinement_requires_completed_output_synchronization(tmp_path,monkeypatch,defect):
    module,gr,result,original=runtime(monkeypatch);result.iparams.refinement.dry_run=False
    def program(args,observe):
        rows=[output_row(len(result.model.get_hierarchy().atoms()))]
        if defect=='missing':rows=[]
        if defect=='repeated':rows*=2
        if defect=='unfinished':rows[0]['write_completed']=False
        observe(rows,defect!='binding')
        return result
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,setup()[3],program,dict(profile_id='test'),lambda:None))
    with pytest.raises(ValueError):module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native')
    assert json.loads((tmp_path/'native/result.json').read_text())['status']=='FAILED'
    assert gr.parallelity_residual_sum == original


@pytest.mark.parametrize('dry_run',[False,True])
@pytest.mark.parametrize('defect',[None,'missing_definition','changed_export','missing_output'])
def test_optional_selected_observation_preserves_native_result_and_exact_written_serial(tmp_path,monkeypatch,dry_run,defect):
    from tests.test_cif_refinement_sites import model,SITES
    from nasolve.cif_refinement_output import _digest,_hierarchy
    from hashlib import sha256
    module,gr,result,original=runtime(monkeypatch)
    m,klass,selected,other,atoms=model();summary=klass.summary
    m.restraints_manager.geometry.site_symmetry_table=NS(special_position_indices=lambda:[])
    result.model=m;result.iparams.refinement.dry_run=dry_run
    result.ofm=NS(serial=1)
    result.ofm.get_file_name=lambda ext:str(tmp_path/f'written_{result.ofm.serial:03d}{ext}')
    monkeypatch.setattr(module,'_monomer_mapping_class',lambda:klass)
    def program(args,observe,observe_final):
        m._all_monomer_mappings=[selected.summary(),other.summary()]
        if defect=='missing_definition':m._all_monomer_mappings=[]
        if not dry_run:
            row=output_row(len(atoms));row['hierarchy_after_sha256']=_digest(_hierarchy(m))
            observe([row],False)
            observe_final(result,False)
            if defect!='missing_output':Path(result.ofm.get_file_name('.pdb')).write_bytes(b'exact native model')
            result.ofm.serial+=1  # Native .def writer advances before program return.
            if defect=='changed_export':atoms[0].xyz=(99.,98.,97.)
            observe_final(result,True)
            observe([row],True)
        else:observe([],True)
        return result
    from pathlib import Path
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,setup()[3],program,dict(profile_id='test'),lambda:None))
    returned=module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native',chemistry_sites=SITES)
    assert returned is result and klass.summary is summary and gr.parallelity_residual_sum == original
    record=json.loads((tmp_path/'native/result.json').read_text())
    assert record['status']=='COMPLETE' and record['chemistry_binding_restored']
    missing=defect=='missing_definition' or (not dry_run and defect is not None)
    assert record['chemistry_observation']['status']==('UNASSESSED' if missing else 'OBSERVED')
    assert record['chemistry_model']==(None if dry_run or missing else dict(sha256=sha256(b'exact native model').hexdigest(),size=18))


def test_selected_observation_interruption_restores_both_native_bindings(tmp_path,monkeypatch):
    from tests.test_cif_refinement_sites import model,SITES
    module,gr,result,original=runtime(monkeypatch);m,klass,*_=model();summary=klass.summary
    monkeypatch.setattr(module,'_monomer_mapping_class',lambda:klass)
    def interrupted(*args):raise KeyboardInterrupt('stop')
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,setup()[3],interrupted,dict(profile_id='test'),lambda:None))
    with pytest.raises(KeyboardInterrupt):module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native',chemistry_sites=SITES)
    assert gr.parallelity_residual_sum == original and klass.summary is summary
    record=json.loads((tmp_path/'native/result.json').read_text())
    assert record['status']=='FAILED' and record['chemistry_binding_restored']
