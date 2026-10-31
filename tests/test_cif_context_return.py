"""Replay completed context/transport as data, including coordinated mutations."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from tests.test_cif_construction_return import construction_case, encoded
from nasolve.cif_postmr_construction import run_postmr_construction_controls


def context_case(tmp_path, monkeypatch):
    from nasolve.cif_construction_return import C63_SOURCE_COMMIT, C63_RUNTIME_SHA256, C63_SOURCE_SHA256
    from nasolve.postmr import _coot_script
    prior, old = construction_case(tmp_path)
    original = tmp_path / 'postmr_construction'
    source_dir = tmp_path / 'fresh_sources'; source_dir.mkdir()
    dictionaries = {}
    for code, ref in old['dictionaries'].items():
        path = source_dir / (code + '.cif'); path.write_bytes((original / ref['path']).read_bytes())
        dictionaries[code] = path
    atl = source_dir / 'ATL.cif'; atl.write_bytes((original / old['atl_control']['source']['path']).read_bytes())

    def saved_data(input_model, raw, actions, executable, directory, environment, dicts, parents, **kwargs):
        shutil.copyfile(original / old['outputs']['raw_model']['path'], raw)
        for site, target in parents.items(): shutil.copyfile(original / old['parents'][site]['path'], target)
        script = directory / 'mutate.py'
        script.write_text(_coot_script(input_model, raw, actions, dicts, parents))
        log = directory / 'coot.log'; log.write_bytes((original / old['outputs']['coot_log']['path']).read_bytes())
        return script, log

    monkeypatch.setattr('nasolve.postmr._run_coot', saved_data)
    out = tmp_path / 'fresh/postmr_construction'
    report = run_postmr_construction_controls(Path(__file__).parents[1] / 'MR_frames/5W6W/5W6W_noPO4.pdb',
        dictionaries, out, coot_executable=Path('EXPLICIT_FAKE_NOT_EXECUTED'), coot_version='1.3.3', atl_dictionary=atl)
    members = {'inputs/review/' + n: data for n, data in prior.items()}
    members.update({p.relative_to(out.parent).as_posix(): p.read_bytes() for p in out.rglob('*') if p.is_file()})
    members['component_controls/sources/ATL.cif'] = atl.read_bytes()
    report['source_numerical_candidates'] = {c: {**r, 'path': 'inputs/review/' + r['path']} for c, r in old['source_numerical_candidates'].items()}
    report['qualified_runtime_input'] = old['qualified_runtime_input']
    report['construction_prerequisite'] = {'delivery_prefix': '62_Cedar',
        'sha256': '1c78b4ceb12478b05fd968ec891822d237ed3be44fe46a9bf0184bbc9ff38996',
        'status': 'CONSTRUCTION_CONTROLS_PASS_WITH_NOTES', 'raw_fallback_sites': ['A:6', 'A:9', 'A:7'],
        'rigid_transport_exercised': False, 'coot_version': '1.3.3',
        'captured_code_execution': 'NOT_RUN', 'original_raw_models': 'PRESERVED'}
    build = deepcopy(json.loads(prior['probe_receipt.json'])['build'])
    build.update(nasolve_source={'commit': C63_SOURCE_COMMIT, 'working_tree_has_changes': False}, runtime_archive_sha256=C63_RUNTIME_SHA256)
    build['runtime_files'].update({n: {'sha256': h} for n, h in C63_SOURCE_SHA256.items()})
    receipt = {'delivery_prefix': '63_Cedar', 'build': build, 'postmr_construction_audit': report,
        'coot_runtime': json.loads(prior['probe_receipt.json'])['coot_runtime']}
    members['probe_receipt.json'] = encoded(receipt)
    members['postmr_construction_audit.json'] = encoded(report)
    return members, report


def reseal(members, report):
    for ref in report['outputs'].values():
        data = members['postmr_construction/' + ref['path']]
        ref.update(sha256=sha256(data).hexdigest(), size=len(data))
    members['postmr_construction/construction_report.json'] = encoded({k: v for k, v in report.items()
        if k not in {'source_numerical_candidates', 'qualified_runtime_input', 'construction_prerequisite'}})
    members['postmr_construction_audit.json'] = encoded(report)
    receipt = json.loads(members['probe_receipt.json']); receipt['postmr_construction_audit'] = report
    members['probe_receipt.json'] = encoded(receipt)


def test_completed_context_return_recomputes_every_stage_without_native(tmp_path, monkeypatch):
    from nasolve.cif_construction_return import replay_postmr_construction
    members, report = context_case(tmp_path, monkeypatch)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Saved replay executed a process'))
    before = dict(members)
    result = replay_postmr_construction(members)
    assert result['status'] == 'SAVED_POSTMR_CONSTRUCTION_REPLAY_PASS'
    assert result['audit']['status'] == 'CONSTRUCTION_CONTROLS_PASS'
    assert not result['audit']['raw_fallback_sites']
    assert result['context_replayed'] and not result['raw_final_geometry_identical']
    assert result['captured_code_execution'] == result['new_native_execution'] == 'NOT_RUN'
    assert members == before


@pytest.mark.parametrize('defect', ['context_xyz', 'shadow_xyz', 'shadow_sanitized', 'rechecked',
    'context_claim', 'serial_claim', 'deleted_claim', 'final_xyz', 'observed_claim', 'prerequisite',
    'source_commit', 'runtime', 'context_source', 'script', 'context_anchor', 'context_path',
    'plan', 'standalone_report'])
def test_context_return_rejects_resealed_substantive_changes(tmp_path, monkeypatch, defect):
    from nasolve.cif_construction_return import replay_postmr_construction
    members, report = context_case(tmp_path, monkeypatch)
    roles = {'context_xyz': 'restoration_input', 'shadow_xyz': 'context_shadow',
        'shadow_sanitized': 'context_sanitized_shadow', 'rechecked': 'context_rechecked_model', 'final_xyz': 'model'}
    if defect in roles:
        name = 'postmr_construction/' + report['outputs'][roles[defect]]['path']
        lines = members[name].decode().splitlines(keepends=True)
        i = next(i for i, l in enumerate(lines) if l.startswith(('ATOM  ', 'HETATM')))
        lines[i] = lines[i][:30] + f'{float(lines[i][30:38])+.5:8.3f}' + lines[i][38:]
        members[name] = ''.join(lines).encode()
    if defect == 'context_claim': report['context_receipt']['status'] = 'NO_CONTEXT_CHANGE'
    if defect == 'serial_claim': report['context_receipt']['serial_repairs'] = []
    if defect == 'deleted_claim': report['context_receipt']['removed_atoms'] = []
    if defect == 'observed_claim': report['expected_restoration_context']['A:6']['actual_coot_composition'] = 'NOT_YET_OBSERVED'
    if defect == 'prerequisite': report['construction_prerequisite']['rigid_transport_exercised'] = True
    if defect == 'context_anchor': report['outputs']['restoration_input']['anchor'] = 'OTHER'
    if defect == 'context_path': report['outputs']['restoration_input']['path'] = '../escape.pdb'; members['postmr_construction/../escape.pdb'] = b'bad'
    reseal(members, report)
    receipt = json.loads(members['probe_receipt.json'])
    if defect == 'source_commit': receipt['build']['nasolve_source']['commit'] = '0'*40
    if defect == 'runtime': receipt['build']['runtime_archive_sha256'] = '0'*64
    if defect == 'context_source': receipt['build']['runtime_files']['src/nasolve/postmr_context.py']['sha256'] = '0'*64
    members['probe_receipt.json'] = encoded(receipt)
    if defect == 'script': members['postmr_construction/model/Coot/mutate.py'] += b'\nexec("MUST_NOT_RUN")\n'
    if defect == 'plan': members['postmr_construction/construction_plan.json'] = b'{}'
    if defect == 'standalone_report': members['postmr_construction/construction_report.json'] = b'{}'
    with pytest.raises(ValueError): replay_postmr_construction(members)
