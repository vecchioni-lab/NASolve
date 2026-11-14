"""Saved construction is replayed as data through maintained ordinary helpers."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from nasolve.cif_construction_provenance import _pdb_inventory
from nasolve.cif_postmr_construction import (
    ORDINARY_POSTMR_CONSTRUCTION_CONTROLS, audit_postmr_construction,
    run_postmr_construction_controls,
)
from nasolve.postmr import MutationAction, _coot_script, _restore_shared_parent_coordinates
from tests.test_cif_fragment_restoration import SCAFFOLD
from tests.test_cif_postmr_construction import FRAME, dictionaries, dictionary


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def construction_case(tmp_path):
    """Public canonical frame plus synthetic dictionaries and Coot output."""
    from nasolve.cif_construction_return import C62_SOURCE_SHA256, C62_SOURCE_COMMIT, C62_RUNTIME_SHA256
    source_dir = tmp_path / 'sources'; source_dir.mkdir()
    sources = dictionaries(source_dir, op3=True)
    atl = dictionary(source_dir / 'ATL.cif', 'ATL', bridge=True)
    output = tmp_path / 'postmr_construction'
    staged = run_postmr_construction_controls(FRAME, sources, output,
        inspect_only=True, atl_dictionary=atl, coot_version='1.3.3')
    staged['status'] = 'PREPARED'; staged['coot']['execution'] = 'NOT_RUN'
    # C62 precedes production-context projection; its historical plan and
    # restoration remain replayable after newer ordinary construction evolves.
    for context in staged['expected_restoration_context'].values():
        context['unmatched_raw_scaffold_policy'] = 'RAW_SITE_RETAINED'
    (output / 'construction_plan.json').write_bytes(encoded({k: v for k, v in staged.items() if k != 'source_inputs_preserved'}))
    initial = output / staged['input_model']['path']
    actions = tuple(MutationAction(**row) for row in staged['controls'])
    model_dir = output / 'model'; coot_dir = model_dir / 'Coot'; coot_dir.mkdir(parents=True)
    parents = {a.site: coot_dir / ('parent_' + a.site.replace(':', '_') + '_' + a.parent_code + '.pdb') for a in actions}
    for path in parents.values(): shutil.copyfile(initial, path)
    inventory = _pdb_inventory(initial); replacements = {}
    for action in actions:
        chain, resid = action.site.split(':')
        atoms = {k[-1]: row['xyz'] for k, row in inventory.items() if k[:2] == (chain, resid)}
        points = {name: atoms[name] for name in SCAFFOLD}
        center = atoms["C1'"]
        points.update({name: [center[0]+i, center[1]+.2*i, center[2]+1.] for i, name in enumerate(('NX', 'C2', 'QZ'), 1)})
        points['OP3'] = [atoms['P'][0]+.3, atoms['P'][1]+.5, atoms['P'][2]+1.2]
        lines = []
        for serial, (name, xyz) in enumerate(points.items(), 9000):
            element = 'P' if name == 'P' else 'O' if name.startswith('O') else 'N' if name == 'NX' else 'C'
            lines.append(f'HETATM{serial:5d} {name:>4} {action.after:>3} {chain}{int(resid):4d}    '
                + ''.join(f'{v:8.3f}' for v in xyz) + f'  0.75 17.00          {element:>2}\n')
        replacements[action.site] = ''.join(lines)
    lines = []
    for line in initial.read_text().splitlines(keepends=True):
        site = line[21].strip()+':'+line[22:26].strip() if line.startswith(('ATOM  ', 'HETATM')) else None
        if site in replacements: lines.append(replacements.pop(site))
        elif site not in {a.site for a in actions}: lines.append(line)
    raw = model_dir / 'constructed_model_raw.pdb'; raw.write_text(''.join(lines))
    geometry = model_dir / 'constructed_model_geometry.pdb'
    dictionaries_in = {code: output / row['path'] for code, row in staged['dictionaries'].items()}
    restoration = _restore_shared_parent_coordinates(raw, geometry, actions, parents, dictionaries_in)
    final = model_dir / 'constructed_model.pdb'; shutil.copyfile(geometry, final)
    historical = Path('/explicit_fixture/62_Cedar_control/postmr_construction')
    script = _coot_script(historical / staged['input_model']['path'], historical / 'model/constructed_model_raw.pdb', actions,
        {a.after: historical / staged['dictionaries'][a.after]['path'] for a in actions},
        {site: historical / path.relative_to(output) for site, path in parents.items()})
    (coot_dir / 'mutate.py').write_text(script)
    log = ''.join('debug:: get_monomer_from_dictionary() installing '+a.after+'_from_dict into model 1\n'
        'DEBUG:: return gmi with success 1\nadd_ligand_delete_residue_copy_molecule() returns '+str(i)+'\n'
        for i, a in enumerate(actions, 2))
    (coot_dir / 'coot.log').write_text(log)
    def reference(path):
        data = path.read_bytes()
        return {'anchor': 'construction_directory', 'path': path.relative_to(output).as_posix(), 'sha256': sha256(data).hexdigest(), 'size': len(data)}
    report = deepcopy(staged)
    report.update(status='CONSTRUCTION_CONTROLS_PASS_WITH_NOTES', analysis_completed=True,
        coordinate_restoration=restoration, audit=audit_postmr_construction(initial, raw, final, actions, dictionaries_in, parents, restoration),
        outputs={k: reference(p) for k, p in {'model': final, 'raw_model': raw, 'geometry_model': geometry, 'coot_log': coot_dir / 'coot.log'}.items()},
        parents={site: reference(path) for site, path in parents.items()}, source_inputs_preserved=True)
    report['coot']['execution'] = 'COMPLETED'
    (output / 'construction_report.json').write_bytes(encoded(report))
    # An already validated C61 parent supplies four wrappers to the C57 source.
    members = {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in output.rglob('*') if path.is_file()}
    members['component_controls/sources/ATL.cif'] = atl.read_bytes()
    cases = {}; prefix = 'inputs/review/' * 5
    for code in ('DP', 'PDU', '5PC'):
        data = sources[code].read_bytes(); directory = 'source_classification/' + code
        ref = {'anchor': 'candidate_directory', 'path': 'candidate.cif', 'sha256': sha256(data).hexdigest(), 'size': len(data)}
        cases[code] = {'preparation': {'directory': {'anchor': 'probe_directory', 'path': directory}, 'candidate': ref},
            'decision': {'status': 'CONTINUE_WITH_NOTES', 'selected_candidate': 'source_declared_dna'}}
        members[prefix + directory + '/candidate.cif'] = data
    for i, delivery in enumerate(('61_Cedar', '60_Cedar', '59_Cedar', '58_Cedar', '57_Cedar'), 1):
        header = {'delivery_prefix': delivery}
        if delivery == '57_Cedar': header['source_classification_audit'] = {'cases': cases}
        members['inputs/review/' * i + 'probe_receipt.json'] = encoded(header)
    report['source_numerical_candidates'] = {code: {'anchor': 'input_capsule', 'path': 'inputs/review/' * 4 + 'source_classification/' + code + '/candidate.cif',
        'sha256': sha256(sources[code].read_bytes()).hexdigest(), 'size': sources[code].stat().st_size} for code in sources}
    report['qualified_runtime_input'] = {'delivery_prefix': '61_Cedar', 'sha256': '73476fe624d7f951d7c0b6af8ff2da75c4caf7b9f19f1e1870610f1e383c8472',
        'native_readback': 'PASS', 'native_checks': 15, 'selected_bundle': 'PRESERVED'}
    members['postmr_construction_audit.json'] = encoded(report)
    build = {'nasolve_source': {'commit': C62_SOURCE_COMMIT, 'working_tree_has_changes': False},
        'runtime_archive_sha256': C62_RUNTIME_SHA256, 'runtime_files': {name: {'sha256': digest} for name, digest in C62_SOURCE_SHA256.items()}}
    build['runtime_files']['MR_frames/5W6W/5W6W_noPO4.pdb'] = {'sha256': sha256(FRAME.read_bytes()).hexdigest(), 'size': FRAME.stat().st_size}
    build['runtime_files']['controls/ATL.cif'] = {'sha256': sha256(atl.read_bytes()).hexdigest(), 'size': atl.stat().st_size}
    receipt = {'delivery_prefix': '62_Cedar', 'build': build, 'postmr_construction_audit': report,
        'coot_runtime': {'executable': '/fixture/coot/1.3.3/bin/coot', 'sha256': 'a'*64, 'version': '1.3.3', 'source': 'explicit fixture'}}
    members['probe_receipt.json'] = encoded(receipt)
    return members, report


def reseal(members, report):
    """Coordinate saved hashes/receipts so failures reach substantive checks."""
    for section in ('outputs', 'parents'):
        for ref in report[section].values():
            name = 'postmr_construction/' + ref['path']
            if name not in members:
                continue
            data = members[name]
            ref.update(sha256=sha256(data).hexdigest(), size=len(data))
    standalone = {k: v for k, v in report.items() if k not in {'qualified_runtime_input', 'source_numerical_candidates'}}
    members['postmr_construction/construction_report.json'] = encoded(standalone)
    members['postmr_construction_audit.json'] = encoded(report)
    receipt = json.loads(members['probe_receipt.json']); receipt['postmr_construction_audit'] = report
    members['probe_receipt.json'] = encoded(receipt)


def test_saved_construction_replays_all_stages_without_processes_or_captured_python(tmp_path, monkeypatch):
    from nasolve.cif_construction_return import replay_postmr_construction
    members, _ = construction_case(tmp_path); before = dict(members)
    monkeypatch.setattr(subprocess, 'Popen', lambda *a, **k: pytest.fail('Replay started a native process'))
    report = replay_postmr_construction(members)
    assert report['status'] == 'SAVED_POSTMR_CONSTRUCTION_REPLAY_PASS'
    assert report['audit']['status'] == 'CONSTRUCTION_CONTROLS_PASS_WITH_NOTES'
    assert report['audit']['raw_fallback_sites'] == ['A:6', 'A:9', 'A:7']
    assert report['captured_code_execution'] == report['new_native_execution'] == 'NOT_RUN'
    assert report['raw_final_geometry_identical'] and not report['requires_cif_review']
    assert members == before


@pytest.mark.parametrize('defect', ['worker', 'worker_extra_call', 'source_hash', 'runtime', 'build_source', 'script_path',
    'native_log', 'native_version', 'native_executable_hash', 'source_decision', 'source_lineage', 'source_anchor',
    'source_dictionary', 'atl_source', 'graph_plan', 'plan_model', 'final_coordinate', 'raw_unselected_coordinate', 'raw_added_atom',
    'parent_coordinate', 'restoration_claim', 'audit_claim', 'reported_status', 'scientific_claim', 'artifact_anchor', 'artifact_path'])
def test_saved_construction_rejects_coordinated_evidence_mutations(tmp_path, defect):
    from nasolve.cif_construction_return import replay_postmr_construction
    members, report = construction_case(tmp_path)
    script = 'postmr_construction/model/Coot/mutate.py'
    receipt = json.loads(members['probe_receipt.json'])
    if defect == 'worker': members[script] += b'\n# modified\n'
    if defect == 'worker_extra_call': members[script] += b'\nexec("forbidden")\n'
    if defect == 'source_hash': receipt['build']['runtime_files']['src/nasolve/postmr.py']['sha256'] = '0'*64
    if defect == 'runtime': receipt['build']['runtime_archive_sha256'] = '0'*64
    if defect == 'build_source': receipt['build']['nasolve_source']['commit'] = '0'*40
    if defect == 'script_path': members[script] = members[script].replace(b'/inputs/DP.cif', b'/inputs/other.cif')
    if defect == 'native_log': members['postmr_construction/model/Coot/coot.log'] = b'No native evidence.\n'
    if defect == 'native_version': receipt['coot_runtime']['version'] = 'different'
    if defect == 'native_executable_hash': receipt['coot_runtime']['sha256'] = 'NOT_A_SHA256'
    if defect in {'source_decision', 'source_lineage', 'source_anchor'}:
        key = 'inputs/review/'*5 + 'probe_receipt.json'; row = json.loads(members[key])
        if defect == 'source_decision': row['source_classification_audit']['cases']['DP']['decision']['selected_candidate'] = 'UNQUALIFIED'
        if defect == 'source_lineage': row['delivery_prefix'] = '56_Cedar'
        if defect == 'source_anchor': row['source_classification_audit']['cases']['DP']['preparation']['candidate']['anchor'] = 'arbitrary'
        members[key] = encoded(row)
    if defect == 'source_dictionary': members['postmr_construction/inputs/DP.cif'] += b'\n# altered source\n'
    if defect == 'atl_source':
        key = 'postmr_construction/inputs/ATL.cif'; members[key] += b'\n# altered staged control\n'
        ref = report['atl_control']['source']; ref.update(sha256=sha256(members[key]).hexdigest(), size=len(members[key]))
        plan_key = 'postmr_construction/construction_plan.json'; plan = json.loads(members[plan_key])
        plan['atl_control'] = deepcopy(report['atl_control']); members[plan_key] = encoded(plan)
    if defect == 'graph_plan': report['source_graph_eligibility']['DP']['fragment_atoms'].pop()
    if defect == 'plan_model':
        key = 'postmr_construction/construction_plan.json'; plan = json.loads(members[key]); plan['canonical_source_sha256'] = '0'*64; members[key] = encoded(plan)
    if defect in {'final_coordinate', 'raw_unselected_coordinate', 'raw_added_atom', 'parent_coordinate'}:
        key = 'postmr_construction/' + report['outputs']['model']['path']
        if defect.startswith('raw_'): key = 'postmr_construction/' + report['outputs']['raw_model']['path']
        if defect == 'parent_coordinate': key = 'postmr_construction/' + report['parents']['A:6']['path']
        lines = members[key].decode().splitlines(keepends=True)
        if defect == 'raw_added_atom': lines.append(next(l for l in lines if l.startswith('HETATM')))
        else:
            index = next(i for i,l in enumerate(lines) if l.startswith(('ATOM  ', 'HETATM')) and
                ((l[21:26] == 'A   6') if defect == 'parent_coordinate' else (l[21:26] == 'A   1')))
            lines[index] = lines[index][:30] + f'{99.:8.3f}' + lines[index][38:]
        members[key] = ''.join(lines).encode()
    if defect == 'restoration_claim': report['coordinate_restoration']['A:6']['reason'] = 'Invented reason'
    if defect == 'audit_claim': report['audit']['sites'][0]['fragment_transport_tested'] = True
    if defect == 'reported_status': report['status'] = 'SCIENTIFICALLY_QUALIFIED'
    if defect == 'scientific_claim': report['refinement'] = 'COMPLETED'
    if defect == 'artifact_anchor': report['outputs']['model']['anchor'] = 'external'
    if defect == 'artifact_path': report['outputs']['model']['path'] = '../outside.pdb'
    members['probe_receipt.json'] = encoded(receipt)
    reseal(members, report)
    with pytest.raises(ValueError): replay_postmr_construction(members)


@pytest.mark.parametrize('defect', ['duplicate_json', 'nonfinite_json', 'runtime_source_bytes', 'canonical_bytes'])
def test_saved_construction_has_strict_data_and_optional_original_runtime_boundaries(tmp_path, defect):
    from nasolve.cif_construction_return import replay_postmr_construction, C62_SOURCE_SHA256, CANONICAL_FRAME
    members, _ = construction_case(tmp_path)
    kwargs = {}
    if defect == 'duplicate_json':
        members['probe_receipt.json'] = members['probe_receipt.json'].replace(b'{', b'{"delivery_prefix":"62_Cedar",', 1)
    if defect == 'nonfinite_json':
        members['probe_receipt.json'] = members['probe_receipt.json'].replace(b'{', b'{"not_a_finite_value":NaN,', 1)
    if defect == 'runtime_source_bytes':
        kwargs['runtime_sources'] = {name: b'raise AssertionError("captured source must never execute")' for name in C62_SOURCE_SHA256}
    if defect == 'canonical_bytes':
        # A deliberate empty pin mapping reaches the separate resource pin.
        import nasolve.cif_construction_return as module
        original = module.C62_SOURCE_SHA256
        module.C62_SOURCE_SHA256 = {}
        try:
            with pytest.raises(ValueError): replay_postmr_construction(members, runtime_sources={CANONICAL_FRAME: b'changed canonical frame'})
        finally:
            module.C62_SOURCE_SHA256 = original
        return
    with pytest.raises(ValueError): replay_postmr_construction(members, **kwargs)
