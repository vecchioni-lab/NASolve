"""Native hook owners must not erase competing replacements on any exit."""
import json
import pytest
from tests.test_cif_refinement_runtime import runtime,output


@pytest.mark.parametrize('interrupted',[False,True])
def test_runtime_preserves_foreign_kernel_and_records_failed_ownership(tmp_path,monkeypatch,interrupted):
    module,gr,result,original=runtime(monkeypatch)
    foreign=lambda **kwargs:0.
    def program(args,observe):
        gr.parallelity_residual_sum=foreign
        if interrupted:raise RuntimeError('original native failure')
        output(result,observe)
        return result
    from tests.test_cif_parallelity_kernel import setup
    monkeypatch.setattr(module,'_native_runtime',lambda:(gr,setup()[3],program,{},lambda:None))
    error=RuntimeError if interrupted else ValueError
    message='original native failure' if interrupted else 'binding changed'
    with pytest.raises(error,match=message):
        module.run_compatible_refinement(['model.pdb'],evidence_directory=tmp_path/'native')
    assert gr.parallelity_residual_sum is foreign
    record=json.loads((tmp_path/'native/result.json').read_text())
    assert record['status']=='FAILED' and record['binding_restored'] is False


@pytest.mark.parametrize('interrupted',[False,True])
def test_output_owner_preserves_foreign_writer_and_reports_unrestored(interrupted):
    from nasolve.cif_refinement_output import synchronized_outputs
    class Driver:
        def write_after_run_outputs(self):return 'original'
    foreign=lambda self:'foreign';observed=[]
    error=RuntimeError if interrupted else ValueError
    message='original native failure' if interrupted else 'binding changed'
    with pytest.raises(error,match=message):
        with synchronized_outputs(Driver,lambda events,restored:observed.append(restored)):
            Driver.write_after_run_outputs=foreign
            if interrupted:raise RuntimeError('original native failure')
    assert Driver.write_after_run_outputs is foreign
    assert observed==[False]


@pytest.mark.parametrize('interrupted',[False,True])
def test_monomer_owner_preserves_foreign_summary(interrupted):
    from nasolve.cif_refinement_sites import observe_monomers
    class Mapping:
        def summary(self):return 'original'
    foreign=lambda self:'foreign'
    error=RuntimeError if interrupted else ValueError
    message='original native failure' if interrupted else 'binding changed'
    with pytest.raises(error,match=message):
        with observe_monomers(Mapping,[]):
            Mapping.summary=foreign
            if interrupted:raise RuntimeError('original native failure')
    assert Mapping.summary is foreign
