"""Human progress IDs must remain distinct from code provenance and gate status."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('willow_roadmap_audit',ROOT/'scripts/audit_topostitch_roadmap.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


def ledger():return json.loads((ROOT/'docs/topostitch-roadmap.json').read_text())


def test_human_view_leads_with_number_and_links_exact_provenance():
    value=ledger();audit.validate(value);rendered=audit.render(value)
    assert f"Current update: W{value['human_updates']['current']}" in rendered
    assert f"Next: W{value['human_updates']['next']}" in rendered
    assert 'at code `' not in rendered
    item=dict(code_commit='a'*40,human_update=value['human_updates']['current'])
    assert audit.human_audit(item)==f"[W{item['human_update']}](https://github.com/vecchioni-lab/NASolve/commit/{'a'*40})"
    assert 'earlier history is not renumbered' in rendered


@pytest.mark.parametrize('fault',['duplicate','gap','next','boolean','unknown_reference','unfinished_history','unbound_record'])
def test_invalid_or_ambiguous_progress_numbers_are_rejected(fault):
    value=ledger();updates=value['human_updates'];entries=updates['entries']
    if fault=='duplicate':entries.append(deepcopy(entries[-1]))
    elif fault=='gap':entries[-1]['number']+=1
    elif fault=='next':updates['next']+=1
    elif fault=='boolean':entries[-1]['number']=True
    elif fault=='unknown_reference':value['milestones'][0]['last_audit']['human_update']=updates['next']
    elif fault=='unbound_record':entries[-1].update(state='RECORDED',code_commit=None)
    else:
        entries[0].update(state='IN_PROGRESS',code_commit=None)
        entries.append(dict(number=updates['next'],title='Later update',state='RECORDED',code_commit='b'*40))
        updates['current']+=1;updates['next']+=1
    with pytest.raises(ValueError):audit.validate(value)
