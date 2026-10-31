"""Curated phosphate evidence is bound to its actual sources and exact delta."""
from copy import deepcopy

import pytest

from nasolve.cif_postmr_construction import audit_construction_context
from nasolve.postmr import MutationAction
from tests.test_postmr_context_mixed import curated_phosphate_context


@pytest.mark.parametrize('defect', ['none', 'absent', 'source', 'parent', 'site', 'candidate', 'scope'])
def test_curated_context_auditor_binds_source_parent_and_deletion(tmp_path, defect):
    result, raw, parent = curated_phosphate_context(tmp_path, mixed=False)
    assert result['receipt']['status'] == 'CONTEXT_PREPARED'
    receipt = deepcopy(result['receipt'])
    if defect == 'absent':
        receipt.pop('curated_context')
    elif defect == 'source':
        receipt['curated_context']['source_graphs']['A:19']['source_sha256'] = '0'*64
    elif defect == 'parent':
        receipt['curated_context']['source_graphs']['A:19']['parent_model_sha256'] = '0'*64
    elif defect == 'site':
        receipt['curated_context']['sites'] = ['A:18']
    elif defect == 'candidate':
        receipt['curated_context']['candidate_sites'] = []
    elif defect == 'scope':
        receipt['curated_context']['scope'] = 'ALLOW_UNCHECKED_FINAL_COORDINATE_CHANGES'
    args = (parent, raw, result['model'],
            (MutationAction('A:19', 'DT', 'DF', 'coot-parent-overlap', parent_code='DT'),),
            {'DF': tmp_path/'DF.cif'}, receipt)
    kwargs = {'context_shadow': result['shadow'], 'parent_models': {'A:19': parent}}
    if defect == 'none':
        report = audit_construction_context(*args, **kwargs)
        assert report['status'] == 'CONSTRUCTION_CONTEXT_DELTA_PASS'
        assert report['curated_context']['status'] == 'CURATED_CONTEXT_BINDING_PASS'
        assert report['curated_context']['sites'] == ['A:19']
    else:
        with pytest.raises(ValueError, match='[Cc]urated'):
            audit_construction_context(*args, **kwargs)
