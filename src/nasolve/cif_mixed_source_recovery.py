"""Requalify an explicitly preserved candidate in a verified mixed context.

A fresh immutable diagnostic owns both source capsules. Historical programs are
never executed. No generation, optimization, runtime activation or inheritance
of the old objective's derivative/endpoint qualification takes place here.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .cif_mixed_runtime_source import MAX_ARCHIVE_BYTES, archive_members, verified_endpoint_source
from .cif_mixed_recovery import _safe
from .cif_postmr_cached_model import cached_preparation_replays

POLICY_ID = 'cif-mixed-preserved-source-recovery-v1'
ANCHOR = 'mixed_source_recovery_directory'
REPORT = 'mixed_source_recovery.json'


def _need(ok, message):
    if not ok:
        raise ValueError(message)


def _ref(path, root):
    path, root = Path(path), Path(root)
    name = path.relative_to(root).as_posix()
    _need(_safe(name) and path.is_file() and not any(p.is_symlink() for p in [path, *path.parents]),
          'Unsafe source recovery artifact')
    data = path.read_bytes()
    return {'anchor': ANCHOR, 'path': name, 'size': len(data), 'sha256': sha256(data).hexdigest()}


def _resolve(root, ref):
    _need(isinstance(ref, dict) and ref.get('anchor') == ANCHOR and _safe(ref.get('path')),
          'Unsafe source recovery reference')
    path = root/ref['path']
    _need(_ref(path, root) == ref, 'Changed source recovery artifact')
    return path


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(data)
    return path


def candidate_bytes(data, digest, source_member, candidate_member, current_source):
    """Select exact manifest-owned members, never a historical host path."""
    members = archive_members(data, digest)
    _need(_safe(source_member) and _safe(candidate_member) and source_member != candidate_member
          and source_member in members and candidate_member in members, 'Invalid explicit candidate members')
    _need(members[source_member] == current_source, 'Preserved candidate source differs from current source')
    return members[candidate_member]


def replacement_scope(rows, sites, code):
    """Cover every shared identity; prior modifiers need a separate policy."""
    _need(re.fullmatch(r'[A-Z0-9]{1,3}', code) is not None, 'Invalid component identity')
    _need(len(rows) == len({r['site'] for r in rows}), 'Ambiguous native sites')
    _need({r['site']: r['resname'].strip() for r in rows} == sites, 'Native and declared site scope differ')
    selected = [r for r in rows if r['resname'].strip() == code]
    _need(bool(selected), 'Selected component has no current model site')
    _need(all(r.get('chem_mod_ids') == {'status': 'RECORDED', 'ids': []} for r in selected),
          'Prior site modifiers require an explicit composition policy')
    return sorted(r['site'] for r in selected)


def _freeze(root, endpoint, archive, spec):
    """Copy only declared inputs from an already replayed current context."""
    from .cif_mixed_context import _resolve as context_path
    from .cif_mixed_linked_recovery import _contexts
    from .cif_triple_bond_audit import write_component_control_model
    context, parent, report = endpoint['context_view']
    code = spec['component']; inputs = report['inputs']
    sources = {c: context_path(context, parent, ref).read_bytes() for c, ref in inputs['sources'].items()}
    _need(code in sources, 'Selected component lacks an exact current source')
    candidate = candidate_bytes(archive, spec['candidate_archive_sha256'], spec['source_member'],
                                spec['candidate_member'], sources[code])
    plan = json.loads(context_path(context, parent, inputs['plan']).read_bytes())
    selected = replacement_scope(endpoint['native_readback']['monomer_mappings']['rows'], plan['target_site_components'], code)
    refs = {'resources': [], 'sources': {}, 'projections': {}}
    for i, (role, name, data) in enumerate(endpoint['resources']):
        p = _write(root/'inputs/runtime'/f'{i:03d}_{role}{Path(name).suffix}', data)
        refs['resources'].append({'role': role, 'artifact': _ref(p, root)})
    for c, data in sources.items():
        refs['sources'][c] = _ref(_write(root/'inputs/sources'/f'{c}.cif', data), root)
    refs['candidate'] = _ref(_write(root/'inputs/candidate.cif', candidate), root)
    for key in ['plan', 'disabled_policy', 'active_policy']:
        p = context_path(context, parent, inputs[key])
        refs[key] = _ref(_write(root/'inputs'/(key+p.suffix), p.read_bytes()), root)
    model = _resolve(root, refs['resources'][0]['artifact'])
    _need(refs['resources'][0]['role'] == 'model', 'Missing current coordinate selection')
    for site, row in report['bundle']['site_projections'].items():
        p = context_path(context, parent, row['dictionary'])
        refs['projections'][site] = {'component': row['component'], 'dictionary': _ref(
            _write(root/'inputs/projections'/(site.replace(':', '_')+'.cif'), p.read_bytes()), root)}
    # Source and candidate coordinate controls are regenerated from declared CIF
    # seeds. They are not experimental models or regenerated numerical targets.
    refs['models'] = {}
    for name, path in [('source_seed', _resolve(root, refs['sources'][code])),
                       ('candidate_seed', _resolve(root, refs['candidate']))]:
        target = root/'controls'/(name+'.pdb')
        write_component_control_model(path, code, target)
        refs['models'][name] = _ref(target, root)
    policy = b'pdb_interpretation {\n secondary_structure.enabled = False\n}\n'
    refs['isolated_policy'] = _ref(_write(root/'controls/isolated.phil', policy), root)
    return refs, _contexts(model, plan, [code])[code], selected


def _capture(root, ref, paths, *, isolated, timeout, version):
    """Use the maintained native readers, with this audit's owned root."""
    from .cif_mixed_linked_recovery import _capture as linked_capture, ANCHOR as linked_anchor
    from .cif_mixed_recovery import _verify_native, ANCHOR as isolated_anchor
    from .cif_mixed_native import _native_ok
    receipt = _resolve(root, ref)
    if isolated:
        value = json.loads(receipt.read_bytes())
        item = {'model': {**_ref(paths[0], root), 'anchor': isolated_anchor},
                'native': {'directory': {'anchor': isolated_anchor, 'path': receipt.parent.relative_to(root).as_posix()}, **value}}
        value = _verify_native(root, item, paths[1], paths[2])
    else:
        model, dictionaries, phils = paths
        value = linked_capture(root, {**ref, 'anchor': linked_anchor}, model, dictionaries, phils)
    _need(value.get('phenix_version') == version and value.get('execution', {}).get('timeout_seconds') == timeout,
          'Native version or deadline differs')
    _need(_native_ok(value), 'Native interpretation did not complete successfully')
    return value


def _isolated(root, inputs, spec, captures):
    from .cif_candidate_usability import qualify_candidate_native, covalent_proxy_signature
    source = _resolve(root, inputs['sources'][spec['component']]); candidate = _resolve(root, inputs['candidate'])
    qualifications = []; natives = []
    _need(set(captures) == set(inputs['models']), 'Require both isolated coordinate controls')
    names = ['source_seed', 'candidate_seed']
    for name in names:
        model = _resolve(root, inputs['models'][name])
        capture = _capture(root, captures[name], [model, candidate, _resolve(root, inputs['isolated_policy'])],
                           isolated=True, timeout=spec['timeout_seconds'], version=spec['phenix_version'])
        natives.append(capture['native_validation'])
        qualifications.append(qualify_candidate_native(source, candidate, model, spec['component'], natives[-1]))
    combined = deepcopy(qualifications[1])
    combined['checks'].update(source_seed_usable=qualifications[0]['native_usable'],
        same_fixed_covalent_proxies=covalent_proxy_signature(natives[0]) == covalent_proxy_signature(natives[1]))
    combined['native_usable'] = all(v is True for v in combined['checks'].values())
    combined['status'] = 'ISOLATED_NATIVE_USABILITY_PASS' if combined['native_usable'] else 'REVIEW'
    return {'coordinate_cases': dict(zip(names, qualifications)), 'combined': combined}


def _prepare(root, inputs, spec, contexts, qualification):
    from .cif_linked_preparation import prepare_linked_component
    from .ligand_profiles import dictionary_component_codes
    code = spec['component']; model = _resolve(root, inputs['resources'][0]['artifact'])
    dictionaries = [_resolve(root, r['artifact']) for r in inputs['resources'] if r['role'] == 'dictionary']
    # This first replacement policy deliberately supports a dedicated component
    # file only. Shared dictionaries need an explicit block-preservation adapter.
    providers = [p for p in dictionaries if code in dictionary_component_codes(p)]
    _need(len(providers) == 1 and dictionary_component_codes(providers[0]) == {code},
          'Require one dedicated current component dictionary')
    out = root/'bundle/prepared'
    receipt = prepare_linked_component(_resolve(root, inputs['sources'][code]), _resolve(root, inputs['candidate']),
        model, contexts, out, code=code, native_qualification=qualification['combined'])
    replacement = out/receipt['outputs']['dictionary']['path']
    selected = [replacement if p == providers[0] else p for p in dictionaries]
    selected.append(out/receipt['outputs']['modifications']['path'])
    projections = deepcopy(inputs['projections'])
    for row in receipt['sites']:
        projections[row['site']] = {'component': code, 'dictionary': _ref(out/('projected_'+row['site'].replace(':', '_')+'.cif'), root)}
    phils = [_resolve(root, r['artifact']) for r in inputs['resources'] if r['role'] == 'phil']
    active = _resolve(root, inputs['active_policy'])
    matches = [i for i, p in enumerate(phils) if p.read_bytes() == active.read_bytes()]
    _need(len(matches) == 1, 'Require one exact declared active policy')
    phils.pop(matches[0])
    phils.append(out/receipt['outputs']['parameters']['path'])
    return {'preparations': {code: {'receipt': receipt}}, 'site_projections': projections,
            'native_dictionaries': [_ref(p, root) for p in selected], 'context_phils': [_ref(p, root) for p in phils],
            'replaced_dictionary': _ref(providers[0], root)}


def _qualification(root, inputs, spec, bundle, captures, old_native, selected):
    from .cif_mixed_linked_recovery import _qualify, ANCHOR as linked_anchor
    from .cif_terminal_qualification import _proxy_subset
    from .cif_construction_native import NATIVE_KINDS
    model = _resolve(root, inputs['resources'][0]['artifact'])
    dictionaries = [_resolve(root, r) for r in bundle['native_dictionaries']]
    contexts = [_resolve(root, r) for r in bundle['context_phils']]
    natives = []
    _need(set(captures) == {'baseline', 'active'}, 'Require both full-model native controls')
    for name in ['baseline', 'active']:
        policy = _resolve(root, inputs['disabled_policy' if name == 'baseline' else 'active_policy'])
        native = _capture(root, captures[name], [model, dictionaries, [policy, *contexts]], isolated=False,
                          timeout=spec['timeout_seconds'], version=spec['phenix_version'])
        natives.append(native['native_validation'])
    adapted = deepcopy(bundle)
    for row in adapted['site_projections'].values():
        row['dictionary']['anchor'] = linked_anchor
    result = _qualify(*natives, model, _resolve(root, inputs['active_policy']), json.loads(_resolve(root, inputs['plan']).read_bytes()),
        {c: _resolve(root, r) for c, r in inputs['sources'].items()}, dictionaries, adapted, root)
    unchanged = {kind: _proxy_subset(old_native, set(selected), kind) == _proxy_subset(natives[1], set(selected), kind)
                 for kind in sorted(NATIVE_KINDS)}
    result['unaffected_current_proxies'] = unchanged
    result['mechanics_checks_pass'] &= all(unchanged.values())
    result['status'] = 'MIXED_SOURCE_RECOVERY_MECHANICS_PASS' if result['mechanics_checks_pass'] else 'REVIEW'
    return result


def _report(spec, inputs, contexts, selected, isolated, bundle, qualification, captures, endpoint):
    return {'schema_version': 1, 'policy_id': POLICY_ID, 'status': qualification['status'], 'specification': spec,
        'inputs': inputs, 'contexts': contexts, 'selected_sites': selected, 'isolated_qualification': isolated,
        'bundle': bundle, 'qualification': qualification, 'native_captures': captures, 'new_native_calls': 4,
        'prior_source_state_review': endpoint['source_state_review'], 'source_inputs_preserved': True,
        'model_preserved': True, 'automatic_adoption': False, 'requires_cif_review': False,
        'scientific_qualification': 'NOT_ASSESSED', 'derivative_qualification': 'NOT_RUN_FOR_CHANGED_OBJECTIVE',
        'endpoint_qualification': 'NOT_INHERITED_FROM_PREVIOUS_OBJECTIVE', 'runtime_activation': 'NOT_PERFORMED',
        'dictionary_generation': 'NOT_RUN', 'model_optimization': 'NOT_RUN', 'production_checkpoint': 'NOT_CREATED',
        'baseline_scope': 'SAME_REPAIRED_BUNDLE_WITH_DECLARED_NA_POLICY_DISABLED'}


def _same_interpreter(root, captures):
    bindings = []
    for scope, expected in [('isolated', {'source_seed', 'candidate_seed'}), ('linked', {'baseline', 'active'})]:
        _need(set(captures[scope]) == expected, 'Incomplete native capture scope')
        for ref in captures[scope].values():
            receipt = json.loads(_resolve(root, ref).read_bytes())
            digest = receipt.get('executable_sha256')
            _need(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest) is not None,
                  'Unbound selected native interpreter')
            bindings.append((digest, receipt.get('phenix_version')))
    _need(len(set(bindings)) == 1, 'Native controls used different selected interpreters')


def _inventory(root):
    _need(not any(p.is_symlink() for p in [root, *root.parents, *root.rglob('*')]),
          'Recovery inventory traverses a symlink')
    return [_ref(p, root) for p in sorted(root.rglob('*')) if p.is_file() and p != root/REPORT]


def audit_mixed_source_recovery(endpoint_capsule, candidate_archive, output, phenix, *, endpoint_sha256,
        candidate_archive_sha256, component, source_member, candidate_member, timeout_seconds=60):
    """Run four bounded native controls in a fresh, separately owned diagnostic."""
    from .cif_native_validation import inspect_native_bundle
    from .cif_candidate_usability import reassess_complete_candidate
    root = Path(output).absolute(); original_paths = [Path(endpoint_capsule), Path(candidate_archive)]
    _need(type(timeout_seconds) is int and 1 <= timeout_seconds <= 60, 'Require a bounded integer native deadline')
    _need(not root.exists() and not any(p.is_symlink() for p in [root, *root.parents])
          and all(not root.resolve().is_relative_to(p.resolve().parent) for p in original_paths), 'Require fresh separate recovery output')
    _need(all(not any(p.is_symlink() for p in [path, *path.parents]) for path in original_paths), 'Unsafe capsule path')
    _need(all(p.is_file() and p.stat().st_size <= MAX_ARCHIVE_BYTES for p in original_paths), 'Oversized or missing source capsule')
    originals = [p.read_bytes() for p in original_paths]
    archive_members(originals[1], candidate_archive_sha256)
    spec = {'component': component, 'source_member': source_member, 'candidate_member': candidate_member,
            'endpoint_sha256': endpoint_sha256, 'candidate_archive_sha256': candidate_archive_sha256,
            'phenix_version': phenix.version, 'timeout_seconds': timeout_seconds}
    root.mkdir(parents=True)
    capsule = _write(root/'capsules/endpoint.zip', originals[0]); archive = _write(root/'capsules/candidate.zip', originals[1])
    with verified_endpoint_source(capsule, endpoint_sha256, include_context=True) as endpoint:
        inputs, contexts, selected = _freeze(root, endpoint, archive.read_bytes(), spec)
        assessment = reassess_complete_candidate(_resolve(root, inputs['sources'][component]), _resolve(root, inputs['candidate']), component)
        _need(assessment['candidate_status'] == 'CANDIDATE_REVIEW', 'Candidate contradicts current complete source state')
        captures = {'isolated': {}, 'linked': {}}
        def execute(label, model, dictionaries, phils, isolated):
            receipt = inspect_native_bundle(model, dictionaries, root/'native'/label, phenix.executables['phenix.python'],
                environment=phenix.environment, phenix_version=phenix.version, timeout_seconds=timeout_seconds,
                phil_files=phils, inventory_detail='linked', policy_inventory=True, energy_inventory=True,
                phil_namespace_policy='direct' if isolated else 'refinement-root-to-interpreter-v1')
            return _ref(Path(receipt['native_directory'])/'native_receipt.json', root)
        for name, ref in inputs['models'].items():
            captures['isolated'][name] = execute(name, _resolve(root, ref), [_resolve(root, inputs['candidate'])],
                                                [_resolve(root, inputs['isolated_policy'])], True)
        isolated = _isolated(root, inputs, spec, captures['isolated'])
        _need(isolated['combined']['native_usable'], 'Preserved candidate failed fresh isolated qualification; partial output retained')
        bundle = _prepare(root, inputs, spec, contexts, isolated)
        model = _resolve(root, inputs['resources'][0]['artifact'])
        dictionaries = [_resolve(root, r) for r in bundle['native_dictionaries']]
        phils = [_resolve(root, r) for r in bundle['context_phils']]
        for name, policy in [('baseline', 'disabled_policy'), ('active', 'active_policy')]:
            captures['linked'][name] = execute(name, model, dictionaries, [_resolve(root, inputs[policy]), *phils], False)
        qualification = _qualification(root, inputs, spec, bundle, captures['linked'], endpoint['native_readback'], selected)
        report = _report(spec, inputs, contexts, selected, isolated, bundle, qualification, captures, endpoint)
    _need(all(p.read_bytes() == data for p, data in zip(original_paths, originals)), 'Changed original source capsule')
    _same_interpreter(root, captures)
    report['outputs'] = _inventory(root)
    _write(root/REPORT, (json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+'\n').encode())
    read_mixed_source_recovery(root)
    return report


def read_mixed_source_recovery(directory):
    """Rebuild decisions from owned inputs and saved captures without a process."""
    path = Path(directory)
    _need(not any(p.is_symlink() for p in [path, *path.parents]), 'Recovery directory traverses a symlink')
    root = path.resolve(strict=True)
    report = json.loads((root/REPORT).read_bytes()); spec = report['specification']
    _need(report.get('schema_version') == 1 and report.get('policy_id') == POLICY_ID, 'Unsupported recovery report')
    _need(report.get('outputs') == _inventory(root), 'Recovery output inventory changed')
    _same_interpreter(root, report['native_captures'])
    _need(type(spec.get('timeout_seconds')) is int and 1 <= spec['timeout_seconds'] <= 60, 'Invalid recorded native deadline')
    with verified_endpoint_source(root/'capsules/endpoint.zip', spec['endpoint_sha256'], include_context=True) as endpoint:
        with TemporaryDirectory(prefix='mixed-source-recovery-reader-') as temporary:
            replay = Path(temporary).resolve()
            inputs, contexts, selected = _freeze(replay, endpoint, (root/'capsules/candidate.zip').read_bytes(), spec)
            _need(inputs == report['inputs'], 'Source recovery inputs do not reproduce')
            isolated = _isolated(root, inputs, spec, report['native_captures']['isolated'])
            _need(isolated['combined']['native_usable'], 'Recorded candidate is not independently usable')
            bundle = _prepare(replay, inputs, spec, contexts, isolated)
            _need(cached_preparation_replays(bundle, report['bundle']), 'Linked preparation does not reproduce')
            for path in replay.rglob('*'):
                if not path.is_file():
                    continue
                saved = root/path.relative_to(replay)
                if path.name == 'preparation_receipt.json':
                    _need(cached_preparation_replays(json.loads(saved.read_bytes()), json.loads(path.read_bytes())), 'Preparation receipt differs')
                else:
                    _need(path.read_bytes() == saved.read_bytes(), 'Prepared recovery bytes differ')
        qualification = _qualification(root, inputs, spec, report['bundle'], report['native_captures']['linked'], endpoint['native_readback'], selected)
        fresh = _report(spec, inputs, contexts, selected, isolated, report['bundle'], qualification, report['native_captures'], endpoint)
        _need(cached_preparation_replays({k: v for k, v in report.items() if k != 'outputs'}, fresh), 'Recovery qualification does not replay')
    return report
