"""Chemical source and site-specific numerical CIFs retain their separate roles."""
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from nasolve.cif_complete_request import _construction_input
from nasolve.cif_model_context import derive_prepared_model_context
from nasolve.postmr_lineage import read_postmr_construction
from tests.test_postmr_projection_lineage import projection_case
from tests.test_cif_model_context import report
from tests.test_cif_complete_request import case


def bound_case(tmp_path):
    run,start,prepared,_=projection_case(tmp_path,distinct_dictionary=True)
    context=derive_prepared_model_context(prepared,report('A:1'),['ZZZ'])
    source=run/'PostMR/Coot/construction_projections/ZZZ/snapshot/entry/source.cif'
    numerical=run/start['inputs']['dictionaries']['ZZZ']['path']
    assert source.read_bytes()!=numerical.read_bytes()
    return run,prepared,context,source,numerical


def test_projected_construction_joins_original_source_without_relabelling_numerics(tmp_path):
    run,model,context,source,numerical=bound_case(tmp_path)
    before=read_postmr_construction(run)
    value=_construction_input(run,model,{'ZZZ':dict(source=source,source_authority='EXPLICIT')},context)
    assert value['files']==before['files']
    assert value['dictionaries']['ZZZ']==numerical
    assert value['projection_sources']['ZZZ']==dict(source=source,source_authority='EXPLICIT')


@pytest.mark.parametrize('defect',['source_bytes','numerical_as_source','authority','missing_authority'])
def test_wrong_projected_source_or_authority_does_not_borrow_qualification(tmp_path,defect):
    run,model,context,source,numerical=bound_case(tmp_path)
    choice=dict(source=source,source_authority='EXPLICIT')
    if defect=='source_bytes':
        wrong=tmp_path/'wrong-source.cif';wrong.write_bytes(source.read_bytes()+b'# different source\n');choice['source']=wrong
    elif defect=='numerical_as_source':choice['source']=numerical
    elif defect=='authority':choice['source_authority']='NATIVE'
    else:choice.pop('source_authority')
    with pytest.raises(ValueError,match='projection source'):_construction_input(run,model,{'ZZZ':choice},context)


def test_prepared_entry_preserves_distinct_source_and_numerics_after_relocation(case,tmp_path):
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources
    from nasolve.cif_postmr_request import initialize_postmr_dictionary_request
    complete,args,out,_,_,generations,calls=case
    parent=tmp_path/'original';parent.mkdir();run,model,context,source,numerical=bound_case(parent)
    selection=parent/'selection';freeze_acquisition_sources(['ZZZ'],selection,explicit_sources={'ZZZ':source})
    before=read_postmr_construction(run)['files']
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')):
        initialize_postmr_dictionary_request(model,context['intent'],
            [dict(code='ZZZ',generation=generations['ZZZ'])],None,out,
            consumer=args['consumer'],ready_set_executable=None,supplementary_phils=[],
            frozen_sources=selection,construction_inputs=run)
    shutil.rmtree(parent);moved=tmp_path/'relocated';out.rename(moved)
    stamps={str(p.relative_to(moved)):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
    with patch('subprocess.Popen',side_effect=AssertionError('No native execution')):
        result=complete.inspect_dictionary_request(moved)
    assert result['availability']=='AVAILABLE' and not result['attempts'] and not calls
    assert read_postmr_construction(moved/'inputs/construction')['files']==before
    assert stamps=={str(p.relative_to(moved)):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}
