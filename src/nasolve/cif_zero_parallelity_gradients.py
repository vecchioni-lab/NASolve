"""Captured derivative qualification when the native parallelity family is absent.

This adapter preserves the hash-pinned historical numerical cores. It audits all
eight families with the same finite differences, but records plane-order testing
as inapplicable instead of inventing a proxy or claiming plane-correction proof.
Absence describes the authenticated manager, not independent chemical intent.
"""
from hashlib import sha256
from pathlib import Path

from . import cif_mixed_gradient as numerical

POLICY_ID = 'cif-captured-zero-parallelity-gradient-v1'
ABSENCE_POLICY_ID = 'cif-native-parallelity-absent-v1'
_CORE_FILES = numerical._CORE_FILES


def _need(value):
    if not value:
        raise ValueError('Absent-parallelity derivative evidence does not reproduce')


def _zero(value):
    return type(value) in (int, float) and value == 0


def _zero_count(counts):
    value = counts['n_parallelity_proxies']
    _need(type(value) is int and value == 0)


def _absence(expected):
    geometry = expected['geometry']
    _need(geometry['proxy_details']['parallelity'] == []
        and type(geometry['proxy_counts']['parallelity']) is int
        and geometry['proxy_counts']['parallelity'] == 0)
    requests = geometry['custom_proxy_requests']
    _need(isinstance(requests, list) and all(row['kind'] != 'parallelity' for row in requests))
    for snapshot in expected['energy_inventory']['snapshots']:
        _zero_count(snapshot['proxy_counts'])
        _need(_zero(snapshot['terms']['parallelity_residual_sum']))
    return {'policy_id':ABSENCE_POLICY_ID, 'status':'NOT_APPLICABLE',
        'reason':'AUTHENTICATED_NATIVE_PARALLELITY_ABSENT',
        'native_proxy_count':0, 'evaluation_pairs':0, 'max_evaluation_pairs':0}


def _worker():
    # Three checked seams retain the unchanged manager bootstrap, evaluator,
    # eight-family audit, source fingerprints, deadlines and error handling.
    source = numerical._WORKER
    changes = {
        'from correction_core import evaluate_fixed_native':
            'POLICY_ID = '+repr(POLICY_ID)+'\nfrom correction_core import evaluate_fixed_native',
        "    planes=audit_plane_orders(plane_order_evaluator(gr,flex),{'initial':points},proxies,max_pairs=MAX_PAIRS)":
            "    if proxies:raise RuntimeError('Parallelity must remain absent')\n"
            "    planes="+repr({'policy_id':ABSENCE_POLICY_ID, 'status':'NOT_APPLICABLE',
                'reason':'AUTHENTICATED_NATIVE_PARALLELITY_ABSENT',
                'native_proxy_count':0, 'evaluation_pairs':0, 'max_evaluation_pairs':0}),
        "        if p==points:baselines[family].append(simple)":
            "        if family in ('all','parallelity'):\n"
            "            count=simple['proxy_counts']['n_parallelity_proxies']\n"
            "            if type(count) is not int or count!=0:raise RuntimeError('Unexpected native parallelity count')\n"
            "        if family=='parallelity' and (simple['target']!=0. or any(v!=0. for v in simple['gradient'])):\n"
            "            raise RuntimeError('Absent parallelity contributes energy or gradient')\n"
            "        if p==points:baselines[family].append(simple)",
    }
    for before, after in changes.items():
        _need(source.count(before) == 1)
        source = source.replace(before, after)
    return source


_WORKER = _worker()


def _prepare(root, model, dictionaries, phils, expected):
    # Keep legacy staging frozen for historical replay; this new policy stages
    # the same core files with zero plane comparisons and its own worker/spec.
    from .cif_native_validation import _NATIVE_WORKER, NATIVE_POLICY_ID
    from .cif_candidate_usability import native_energy_worker
    from .cif_gradient_audit import review_distance_groups
    from .cif_fixed_geometry import _fixed_policy
    from .cif_corrected_geometry import QUALIFIED_CORRECTION_SHA256
    _absence(expected)
    _need(_fixed_policy(expected))
    _need(sha256(Path(__file__).with_name('cif_parallelity_correction.py').read_bytes()).hexdigest()
        == QUALIFIED_CORRECTION_SHA256)
    plan = review_distance_groups(expected, expected['geometry']['sites_cart_exact'])
    work = root/'job'; (work/'inputs').mkdir(parents=True); inputs = []
    for i, path in enumerate([model, *dictionaries, *phils]):
        role = 'model' if i == 0 else 'dictionary' if i <= len(dictionaries) else 'phil'
        out = work/'inputs'/f'{i:03d}_{role}{path.suffix}'
        out.write_bytes(path.read_bytes())
        inputs.append({'role':role, 'input_index':i, 'artifact':numerical._ref(out, root)})
    native = {'policy_id':NATIVE_POLICY_ID, 'model':inputs[0]['artifact']['path'].removeprefix('job/'),
        'dictionaries':[v['artifact']['path'].removeprefix('job/') for v in inputs if v['role']=='dictionary'],
        'phil_files':[v['artifact']['path'].removeprefix('job/') for v in inputs if v['role']=='phil'],
        'phil_namespace_policy':'refinement-root-to-interpreter-v1', 'inventory_detail':'linked',
        'policy_inventory':True, 'energy_inventory':True}
    spec = {'policy_id':POLICY_ID, 'selected_indices':plan['selected_indices'],
        'expected_manager_sha256':numerical._manager_digest(expected),
        'expected_energy_sources':expected['energy_inventory']['installed_sources'],
        'max_energy_calls':numerical.MAX_CALLS, 'max_plane_pairs':0, 'required_plane_pairs':0,
        'correction_core_sha256':QUALIFIED_CORRECTION_SHA256}
    numerical._compact_dump(work/'native_spec.json', native)
    numerical._compact_dump(work/'gradient_spec.json', spec)
    numerical._compact_dump(root/'initial_probe_plan.json', plan)
    (work/'native_worker.py').write_text(native_energy_worker(_NATIVE_WORKER))
    (work/'gradient_worker.py').write_text(_WORKER)
    for name, source in _CORE_FILES.items():
        (work/name).write_bytes(Path(__file__).with_name(source).read_bytes())
    return {'inputs':inputs, 'native_spec':numerical._ref(work/'native_spec.json',root),
        'gradient_spec':numerical._ref(work/'gradient_spec.json',root),
        'probe_plan':numerical._ref(root/'initial_probe_plan.json',root),
        'selected_indices':plan['selected_indices'], 'required_plane_pairs':0,
        'cores':{name:numerical._ref(work/name,root) for name in _CORE_FILES},
        'worker':numerical._ref(work/'gradient_worker.py',root),
        'native_worker':numerical._ref(work/'native_worker.py',root)}


def _validate_result(result, expected, selected_indices):
    """Replay every finite difference and prove the absent family stays zero."""
    from .cif_parallelity_correction import ORDER_CORRECTION_ID
    try:
        r = result; points = expected['geometry']['sites_cart_exact']; count = expected['atom_count']
        _need(type(r['schema_version']) is int and r['schema_version']==1 and r['policy_id']==POLICY_ID
            and r['status']=='REVIEW' and r['scientific_qualification']=='NOT_ASSESSED'
            and r['analysis_completed'] is True and r['normalization'] is False
            and r['model_optimization']=='NOT_RUN' and r['automatic_adoption'] is False
            and r['correction_policy_id']==ORDER_CORRECTION_ID
            and r['selected_indices']==list(selected_indices) and 1<=len(selected_indices)<=6
            and len(set(selected_indices))==len(selected_indices)
            and all(type(i) is int and 0<=i<count for i in selected_indices))
        digest = r['constraint_signature_before']
        _need(isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest)
            and digest==r['constraint_signature_after'])
        _need(numerical._numeric_equal(r['plane_order_audit'], _absence(expected))
            and r['native_parallelity_proxies']==[])
        stats = r['correction_statistics']; audit = r['gradient_audit']
        _need(_zero(stats['max_energy_change']) and _zero(stats['max_plane_residual_difference'])
            and type(audit['evaluation_calls']) is int and 0<audit['evaluation_calls']<=numerical.MAX_CALLS
            and audit['max_evaluation_calls']==numerical.MAX_CALLS
            and type(stats['correction_evaluations']) is int
            and stats['correction_evaluations']==audit['evaluation_calls'])
        raw = r['raw_snapshot']; reference = expected['energy_inventory']['snapshots'][0]
        _need(numerical._numeric_equal(raw, reference))
        # With no plane contribution there is no justified gradient correction.
        # Preserve C129's exact raw target/vector/count binding, not just energy.
        baseline = {k:raw[k] for k in ('target', 'gradient', 'proxy_counts')}
        _need(numerical._numeric_equal(r['baseline_evaluations']['all'][0], baseline))
        complete = numerical._gradient_replay(audit, points, r['baseline_evaluations'], list(selected_indices))
        case = audit['cases']['initial']
        for family in ('all', 'parallelity'):
            for baseline in r['baseline_evaluations'][family]:
                _zero_count(baseline['proxy_counts'])
                if family=='parallelity':
                    _need(_zero(baseline['target']) and all(_zero(v) for v in baseline['gradient']))
            for direction in case['families'][family]['directions']:
                for sample in direction['samples']:
                    for sign in ('plus', 'minus'):
                        _zero_count(sample[sign+'_proxy_counts'])
                        if family=='parallelity':_need(_zero(sample[sign+'_target']))
        for sample in case['descent_profile']:_zero_count(sample['proxy_counts'])
        _need(numerical._close(case['families']['all']['baseline']['target'], raw['target']))
        checks = {'complete_initial_sampled_derivatives':complete,
            'authenticated_parallelity_absence':True, 'absent_family_zero_throughout_audit':True,
            'unchanged_native_energy':True, 'unchanged_static_constraint_signature':True,
            'captured_raw_snapshot':True}
        passed = all(v is True for v in checks.values())
        return {'policy_id':POLICY_ID, 'status':'MIXED_INITIAL_DERIVATIVES_PASS' if passed else 'REVIEW',
            'sampled_derivatives_pass':passed, 'checks':checks,
            'plane_order_qualification':'NOT_APPLICABLE',
            'scientific_qualification':'NOT_ASSESSED', 'automatic_adoption':False}
    except (KeyError, TypeError, IndexError, ZeroDivisionError, OverflowError, AssertionError) as exc:
        raise ValueError('Incomplete absent-parallelity derivative evidence') from exc
