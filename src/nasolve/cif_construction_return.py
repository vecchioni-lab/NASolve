"""Read-only replay of C62's fresh ordinary Coot construction controls.

The caller first validates the exact C61 parent capsule. Saved Python is parsed
only for literal historical paths, then compared with the maintained generator;
it is never imported or executed. This proves the recorded raw-site fallback,
not successful fragment transport or scientific geometry qualification.
"""
import ast
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re
from tempfile import TemporaryDirectory

from .cif_construction_provenance import _pdb_inventory
from .cif_postmr_construction import (ORDINARY_POSTMR_CONSTRUCTION_CONTROLS,
    POLICY_ID as CONSTRUCTION_POLICY_ID, _atoms, audit_postmr_construction)
from .cif_scaffold_return import _json, _need, _safe
from .postmr import MutationAction, _coot_script, _restore_shared_parent_coordinates
from .postmr_restoration import source_graph_fragment
from .synthetic_dna import prepare_free_five_prime_model

POLICY_ID = 'cif-saved-postmr-construction-replay-v1'
C62_SOURCE_COMMIT = '782672648934d22162de12375a1cb131d160f24a'
C62_RUNTIME_SHA256 = '2afbdb61614561add523fcd7622d92a6577a01ee206acdb47676676191e462c6'
C61_SHA256 = '73476fe624d7f951d7c0b6af8ff2da75c4caf7b9f19f1e1870610f1e383c8472'
C62_SOURCE_SHA256 = {
    'src/nasolve/postmr.py': '60739b061fc92df48ae9f2c79d552d609b65d72e36e4503c40cdc6a7a3677838',
    'src/nasolve/postmr_restoration.py': '766cc1f02bfb02d133c08ea5d15bb268afdc35c7a5dece2d86f924589d4398fe',
    'src/nasolve/cif_postmr_construction.py': 'bb6df59c5601f87259c0d63cd552a5ccd8973d3a2119b2ead96a8b45cca29a04',
    'src/nasolve/synthetic_dna.py': '0830b5e1e50d88cdbf4af3623a659af12095cee109f9f2eb1329667ab4d343b0',
}
CANONICAL_FRAME = 'MR_frames/5W6W/5W6W_noPO4.pdb'
CANONICAL_SHA256 = '61dfb0f46571eda7fa5b5c5375a4602f04ffb6721e60ed188efa2dc1b3b3a637'
PREFIX = 'postmr_construction'


def _reference(members, ref, *, expected_path=None):
    _need(ref.get('anchor') == 'construction_directory' and _safe(ref.get('path')),
        'Unsafe saved construction artifact reference')
    _need(expected_path is None or ref['path'] == expected_path, 'Saved construction artifact role/path differs')
    name = PREFIX + '/' + ref['path']; data = members[name]
    _need(type(data) is bytes and len(data) == ref['size'] and sha256(data).hexdigest() == ref['sha256'],
        'Saved construction artifact bytes differ')
    return data


def _source_candidates(members):
    """Follow declared parent scopes; never search dictionaries by basename."""
    prefix = 'inputs/review/'
    for delivery in ('61_Cedar', '60_Cedar', '59_Cedar', '58_Cedar', '57_Cedar'):
        receipt = _json(members, prefix + 'probe_receipt.json')
        _need(receipt.get('delivery_prefix') == delivery, 'Saved construction source lineage differs')
        if delivery == '57_Cedar': break
        prefix += 'inputs/review/'
    result = {}; references = {}
    for code in ('DP', 'PDU', '5PC'):
        row = receipt['source_classification_audit']['cases'][code]
        preparation = row['preparation']; directory = preparation['directory']; artifact = preparation['candidate']
        _need(directory.get('anchor') == 'probe_directory' and artifact.get('anchor') == 'candidate_directory'
            and _safe(directory.get('path')) and _safe(artifact.get('path'))
            and row['decision'].get('status') == 'CONTINUE_WITH_NOTES'
            and row['decision'].get('selected_candidate') == 'source_declared_dna',
            'Require the qualified source-declared numerical construction dictionary')
        name = prefix + directory['path'] + '/' + artifact['path']; data = members[name]
        _need(len(data) == artifact['size'] and sha256(data).hexdigest() == artifact['sha256'],
            'Qualified source numerical dictionary changed')
        result[code] = data
        # C62's report describes its input C61 capsule, one wrapper above here.
        references[code] = {'anchor': 'input_capsule', 'path': name.removeprefix('inputs/review/'),
            'sha256': sha256(data).hexdigest(), 'size': len(data)}
    return result, references


def _historical_root(script):
    paths = []
    for node in ast.walk(ast.parse(script)):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == 'coot'
                and node.func.attr == 'handle_read_draw_molecule'):
            _need(len(node.args) == 1 and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str), 'Nonliteral saved Coot input path')
            paths.append(node.args[0].value)
    _need(len(paths) == 1, 'Require one saved Coot construction input')
    path = PurePosixPath(paths[0])
    _need(path.is_absolute() and '..' not in path.parts and '\\' not in paths[0]
        and path.name == 'canonical_free_5oh.pdb' and path.parent.name == 'inputs'
        and path.parent.parent.name == PREFIX, 'Saved Coot input has an unexpected historical scope')
    return Path(path.parent.parent)


def replay_postmr_construction(members, *, runtime_sources=None):
    """Recompute C62 staging, generated script, raw fallback and independent audit.

    The full exact C61 parent is the caller's responsibility. Optional original
    runtime bytes are hash-checked as data only. The canonical packaged frame is
    loaded from that explicit mapping or this maintained runtime's MR resource.
    """
    try:
        receipt = _json(members, 'probe_receipt.json'); report = receipt['postmr_construction_audit']
        _need(receipt.get('delivery_prefix') == '62_Cedar'
            and report == _json(members, 'postmr_construction_audit.json'), 'Saved construction report differs')
        build = receipt['build']
        _need(build['nasolve_source'] == {'commit': C62_SOURCE_COMMIT, 'working_tree_has_changes': False}
            and build['runtime_archive_sha256'] == C62_RUNTIME_SHA256,
            'Saved construction source/runtime provenance differs')
        for name, digest in C62_SOURCE_SHA256.items():
            _need(build['runtime_files'][name]['sha256'] == digest, 'Saved C62 source hash differs: ' + name)
            if runtime_sources is not None:
                _need(type(runtime_sources.get(name)) is bytes and sha256(runtime_sources[name]).hexdigest() == digest,
                    'Original C62 runtime source bytes differ: ' + name)
        canonical = (runtime_sources[CANONICAL_FRAME] if runtime_sources is not None and CANONICAL_FRAME in runtime_sources
            else (Path(__file__).resolve().parents[2] / CANONICAL_FRAME).read_bytes())
        _need(sha256(canonical).hexdigest() == CANONICAL_SHA256
            and build['runtime_files'][CANONICAL_FRAME]['sha256'] == CANONICAL_SHA256
            and len(canonical) == build['runtime_files'][CANONICAL_FRAME]['size'],
            'Canonical construction frame differs')
        sources, source_refs = _source_candidates(members)
        _need(report['source_numerical_candidates'] == source_refs
            and report['qualified_runtime_input'] == {'delivery_prefix': '61_Cedar', 'sha256': C61_SHA256,
                'native_readback': 'PASS', 'native_checks': 15, 'selected_bundle': 'PRESERVED'},
            'Saved construction qualified input selection differs')
        controls = [asdict(MutationAction(r['site'], r['parent'], r['component'], 'coot-parent-overlap', parent_code=r['parent']))
            for r in ORDINARY_POSTMR_CONSTRUCTION_CONTROLS]
        _need(report['controls'] == controls, 'Saved construction actions differ')
        actions = tuple(MutationAction(**row) for row in controls)
        _need(set(report['dictionaries']) == set(sources) and set(report['parents']) == {a.site for a in actions}
            and set(report['outputs']) == {'model', 'raw_model', 'geometry_model', 'coot_log'},
            'Saved construction input/output roles differ')
        initial_bytes = _reference(members, report['input_model'], expected_path='inputs/canonical_free_5oh.pdb')
        staged, removed = prepare_free_five_prime_model(canonical)
        _need(staged == initial_bytes and removed == report['five_prime_phosphate_atoms_removed']
            and report['canonical_source_sha256'] == CANONICAL_SHA256, 'Saved canonical staging does not reproduce')
        artifact_bytes = {}
        for code, data in sources.items():
            saved = _reference(members, report['dictionaries'][code], expected_path='inputs/' + code + '.cif')
            _need(saved == data, 'Saved staged numerical dictionary differs from its qualified source')
            artifact_bytes[report['dictionaries'][code]['path']] = data
        for role, path in {'model': 'model/constructed_model.pdb', 'raw_model': 'model/constructed_model_raw.pdb',
                'geometry_model': 'model/constructed_model_geometry.pdb', 'coot_log': 'model/Coot/coot.log'}.items():
            artifact_bytes[path] = _reference(members, report['outputs'][role], expected_path=path)
        for action in actions:
            path = 'model/Coot/parent_' + action.site.replace(':', '_') + '_' + action.parent_code + '.pdb'
            artifact_bytes[path] = _reference(members, report['parents'][action.site], expected_path=path)
        coot = receipt['coot_runtime']
        _need(coot['version'] == '1.3.3' and isinstance(coot['executable'], str)
            and Path(coot['executable']).is_absolute() and coot['executable'].endswith('/bin/coot')
            and isinstance(coot.get('source'), str) and coot['source']
            and re.fullmatch('[0-9a-f]{64}', coot['sha256']) is not None,
            'Saved native Coot provenance is incomplete or differs')
        script = members[PREFIX + '/model/Coot/mutate.py'].decode('utf-8'); historical = _historical_root(script)
        expected_script = _coot_script(historical / report['input_model']['path'], historical / report['outputs']['raw_model']['path'], actions,
            {a.after: historical / report['dictionaries'][a.after]['path'] for a in actions},
            {site: historical / ref['path'] for site, ref in report['parents'].items()})
        _need(script == expected_script, 'Saved Coot script differs from the maintained ordinary generator')
        log = artifact_bytes[report['outputs']['coot_log']['path']].decode('utf-8')
        replacements = re.findall(r'^add_ligand_delete_residue_copy_molecule\(\) returns (\d+)$', log, re.M)
        _need(log.count('return gmi with success 1') == len(actions) and len(replacements) == len(actions)
            and all(int(i) >= 0 for i in replacements) and 'Traceback (most recent call last)' not in log
            and all('installing ' + a.after + '_from_dict into model ' in log for a in actions),
            'Saved native Coot log does not support all requested constructions')
        with TemporaryDirectory(prefix='nasolve-construction-return-') as temporary:
            folder = Path(temporary).resolve(); initial = folder / 'inputs/canonical_free_5oh.pdb'
            artifact_bytes[report['input_model']['path']] = initial_bytes
            atl_ref = report['atl_control']['source']; atl_bytes = _reference(members, atl_ref, expected_path='inputs/ATL.cif')
            _need(atl_bytes == members['component_controls/sources/ATL.cif']
                and sha256(atl_bytes).hexdigest() == build['runtime_files']['controls/ATL.cif']['sha256']
                and len(atl_bytes) == build['runtime_files']['controls/ATL.cif']['size'],
                'Staged ATL graph control differs from its captured public source')
            artifact_bytes[atl_ref['path']] = atl_bytes
            for name, data in artifact_bytes.items():
                path = folder / PurePosixPath(name); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            dictionaries = {code: folder / ref['path'] for code, ref in report['dictionaries'].items()}
            parents = {site: folder / ref['path'] for site, ref in report['parents'].items()}
            outputs = {role: folder / ref['path'] for role, ref in report['outputs'].items()}
            graph = {code: source_graph_fragment(path, code) for code, path in sorted(dictionaries.items())}
            _need(graph == report['source_graph_eligibility'], 'Saved source graph eligibility does not replay')
            inventory = _pdb_inventory(initial)
            for action in actions:
                _need(_atoms(_pdb_inventory(parents[action.site]), action.site) == _atoms(inventory, action.site),
                    'Frozen selected parent differs from the staged canonical input')
            replayed = folder / 'replayed_geometry.pdb'
            restoration = _restore_shared_parent_coordinates(outputs['raw_model'], replayed, actions, parents, dictionaries)
            _need(restoration == report['coordinate_restoration'] and replayed.read_bytes() == outputs['geometry_model'].read_bytes()
                and outputs['geometry_model'].read_bytes() == outputs['model'].read_bytes(),
                'Saved construction restoration/fallback does not replay')
            audit = audit_postmr_construction(initial, outputs['raw_model'], outputs['model'], actions, dictionaries, parents, restoration)
            _need(audit == report['audit'], 'Saved independent construction audit does not replay')
            atl = {'component': 'ATL', 'scope': 'PUBLIC_GRAPH_ELIGIBILITY_ONLY', 'coot_execution': 'NOT_RUN',
                'reason': 'No qualified numerical ATL dictionary is supplied for fresh Coot construction.', 'source': atl_ref}
            try: atl['graph_plan'] = source_graph_fragment(folder / atl_ref['path'], 'ATL')
            except ValueError as exc:
                atl.update(restoration_eligibility='RAW_SITE_RETAINED', reason=str(exc),
                    notes=["ATL's source graph is retained; unsupported source classification or sugar topology is not rebuilt as DNA."])
            else: atl['restoration_eligibility'] = 'GRAPH_FRAGMENT_ELIGIBLE'
            plan = {'policy_id': CONSTRUCTION_POLICY_ID, 'status': 'PREPARED', 'analysis_completed': False,
                'ordinary_construction_api': 'nasolve.postmr.construct_postmr_model', 'controls': controls,
                'source_graph_eligibility': graph, 'expected_restoration_context': {a.site: {
                    'dictionary_scaffold_atoms_absent_from_parent': sorted(set(graph[a.after]['scaffold_atoms']) - _atoms(inventory, a.site).keys()),
                    'unmatched_raw_scaffold_policy': 'RAW_SITE_RETAINED', 'actual_coot_composition': 'NOT_YET_OBSERVED'} for a in actions},
                'input_model': report['input_model'], 'dictionaries': report['dictionaries'], 'canonical_source_sha256': CANONICAL_SHA256,
                'five_prime_phosphate_atoms_removed': removed, 'atl_control': atl,
                'coot': {'execution': 'NOT_RUN', 'version': coot['version'], 'timeout_seconds': 600},
                'mr_execution': 'NOT_RUN', 'mtz_used': False, 'readyset_execution': 'NOT_RUN', 'phenix_execution': 'NOT_RUN',
                'optimization': 'NOT_RUN', 'refinement': 'NOT_RUN', 'user_cif_review_required': False,
                'scientific_geometry_qualification': 'NOT_ASSESSED'}
            _need(plan == _json(members, PREFIX + '/construction_plan.json'), 'Saved construction staging plan does not replay')
            completed = {**plan, 'status': audit['status'], 'analysis_completed': True,
                'coot': {**plan['coot'], 'execution': 'COMPLETED'}, 'audit': audit, 'coordinate_restoration': restoration,
                'outputs': report['outputs'], 'parents': report['parents'], 'source_inputs_preserved': True}
            _need(completed == _json(members, PREFIX + '/construction_report.json')
                and {**completed, 'source_numerical_candidates': source_refs, 'qualified_runtime_input': report['qualified_runtime_input']} == report,
                'Completed saved construction report has changed scope or unsupported claims')
            raw_inventory = _pdb_inventory(outputs['raw_model'])
            identical = outputs['raw_model'].read_bytes() == outputs['model'].read_bytes()
        return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'SAVED_POSTMR_CONSTRUCTION_REPLAY_PASS',
            'audit': audit, 'controls': controls, 'initial_atom_count': len(inventory), 'constructed_atom_count': len(raw_inventory),
            'raw_final_geometry_identical': identical, 'source_numerical_candidates': source_refs,
            'coot': {'version': coot['version'], 'executable_sha256': coot['sha256'], 'script_sha256': sha256(script.encode()).hexdigest(),
                'log_sha256': report['outputs']['coot_log']['sha256'], 'saved_execution': 'COMPLETED'},
            'scientific_geometry_qualification': 'NOT_ASSESSED', 'captured_code_execution': 'NOT_RUN',
            'new_native_execution': 'NOT_RUN', 'requires_cif_review': False, 'automatic_adoption': False}
    except (KeyError, TypeError, IndexError, OSError, OverflowError, SyntaxError, UnicodeError) as exc:
        raise ValueError('Incomplete saved PostMR construction evidence: ' + str(exc)) from exc
