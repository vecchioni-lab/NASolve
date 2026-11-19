"""Explicit native repair execution for an acquired, source-prepared bundle.

Existing adapters own chemistry, native evidence, numerical qualification and
selection. This coordinator never resumes a directory or promotes missing proof
to a usable fallback. Whole-acquisition ownership/deadlines remain separate.
"""
from hashlib import sha256
from pathlib import Path
from time import monotonic
from tempfile import TemporaryDirectory

from .failure_reporting import add_failure_note
from .cif_component_runtime import _tree, prepare_repaired_component_runtime_bundle, prepare_original_component_runtime_bundle
from .cif_outer_context import OuterAllowance
from .cif_dictionary_store import _bytes, _snapshot_destination, resolve_dictionary_snapshot
from .cif_dictionary_bundle import read_dictionary_bundle, inspect_dictionary_bundle_native
from .cif_dictionary_bundle_repair import inspect_dictionary_bundle_repair, inspect_dictionary_bundle_original
from .cif_dictionary_sites import _model_inventory, _need, _read, _safe
from .cif_linear_torsion_bundle import prepare_linear_torsion_bundle
from .cif_native_validation import inspect_native_bundle
from .cif_captured_linear_attribution import audit_captured_linear_attribution
from .cif_captured_mixed_gradients import audit_captured_mixed_gradients
from .cif_postmr_cache import verify_current_consumer
from .cif_runtime_bundle import resolve_runtime_bundle
from .cif_repair_process import PreparedRepairProcesses
from .cif_prepared_repair_failure import inspect_prepared_native_failure, failure_policy_fields, FALLBACK_POLICY_ID

from .cif_plane_generation import read_owned_plane_support, prepare_owned_trigonal_plane_candidate
from .cif_plane_candidate import UnsupportedPlaneCompletion
from .cif_captured_plane_attribution import audit_captured_plane_attribution
from .cif_repair_chain import prepare_repair_chain
from .cif_energy_library import capture_energy_library, read_energy_library, qualify_energy_reference
from .cif_linear_bond_reference import (linear_bond_query, energy_library_linear_reference,
    compare_linear_bond_reference, prepare_linear_bond_candidate, _pair)
from .cif_captured_bond_attribution import audit_captured_bond_attribution
from .cif_prepared_bond_discovery import (bond_discovery_fields, prepared_bond_queries,
    bond_discovery_plan, validate_prepared_bond_discovery, REPORT as DISCOVERY_REPORT)

POLICY_ID = 'cif-prepared-bundle-repair-execution-v1'
PLANE_SUPPORT_POLICY = 'cif-prepared-owned-plane-support-v1'
BOND_TARGET_POLICY = 'cif-prepared-source-bond-targets-v1'


def compact_evidence_fields(value):
    _need(type(value) is bool, 'Require a boolean compact-evidence storage choice')
    return dict(compact_evidence=True) if value else {}


def _plane_support_snapshot(bundle, declarations):
    """Validate explicit stopped generation and capture it under declared paths."""
    if declarations is None: return None, {}
    prepared = read_dictionary_bundle(bundle)
    sources = {code:resolve_dictionary_snapshot(Path(bundle)/'components'/code/'snapshot')['source']
               for code in prepared['report']['components']}
    return _source_plane_support_snapshot(sources,declarations)


def _source_plane_support_snapshot(sources, declarations):
    """Use the same stopped-support contract before or after site preparation."""
    from .cif_component_runtime import MAX_FILES, MAX_BYTES
    from .cif_generation_attempt import inspect_source_generation_request
    if declarations is None: return None, {}
    _need(isinstance(declarations,dict) and 1 <= len(declarations) <= 16
          and declarations.keys() <= sources.keys()
          and all(isinstance(code,str) and _safe(code) and '/' not in code for code in declarations),
          'Plane support requires one to sixteen source-owned components')
    files = {}; directories = []; choices = {}; total_bytes = 0
    for code in sorted(declarations):
        row = declarations[code]
        _need(isinstance(row,dict) and set(row)=={'request_directory','attempt_number'},
              'Require an exact owned plane request and attempt')
        request = Path(row['request_directory']).absolute()
        source = sources[code]
        before = _tree(request)
        total_bytes += sum(map(len,before.values()))
        _need(len(files)+len(before) <= MAX_FILES and total_bytes <= MAX_BYTES,
              'Combined plane support exceeds frozen bounds')
        read_owned_plane_support(source,code,request,row['attempt_number'])
        state = inspect_source_generation_request(request)
        _need(all(a['state'] in {'STOPPED','STOPPED_UNFINISHED'} and a['activity'] is False
                  for a in state['attempts']), 'Plane support has active or unknown generation work')
        _need(_tree(request)==before, 'Plane support changed while freezing')
        files.update({code+'/'+name:data for name,data in before.items()})
        directories.extend([code,*[code+'/'+p.relative_to(request).as_posix()
            for p in request.rglob('*') if p.is_dir()]])
        choices[code] = row['attempt_number']
    config = dict(policy_id=PLANE_SUPPORT_POLICY,choices=choices,
        files={name:dict(size=len(data),sha256=sha256(data).hexdigest()) for name,data in files.items()},
        directories=sorted(directories))
    return config, files


def _bond_target_choices(bundle, declarations):
    if declarations is None: return None
    prepared=read_dictionary_bundle(bundle)
    sources={code:resolve_dictionary_snapshot(Path(bundle)/'components'/code/'snapshot')['source']
             for code in prepared['report']['components']}
    return _source_bond_target_choices(sources,declarations)


def _bond_target_declarations(declarations):
    """Snapshot bounded explicit pairs; source eligibility is checked separately."""
    if declarations is None: return None
    _need(isinstance(declarations,dict) and 1 <= len(declarations) <= 16
          and all(isinstance(code,str) and _safe(code) and '/' not in code for code in declarations),
          'Bond targets require one to sixteen source-owned components')
    choices={}
    for code in sorted(declarations):
        selected=declarations[code]
        _need(isinstance(selected,(list,tuple)) and 1 <= len(selected) <= 64,
              'Require bounded explicit bond selections')
        pairs=[_pair(row) for row in selected]
        _need(len(set(pairs))==len(pairs), 'Target selection is duplicated')
        choices[code]=[list(pair) for pair in sorted(pairs)]
    return choices


def _source_bond_target_choices(sources, declarations):
    """Freeze explicit source-neighborhood choices without approving a target."""
    choices=_bond_target_declarations(declarations)
    if choices is None: return None
    _need(choices.keys() <= sources.keys(),
          'Bond targets require one to sixteen source-owned components')
    for code,pairs in choices.items():
        query=linear_bond_query(sources[code],code)
        _need({tuple(pair) for pair in pairs}<={tuple(row) for row in query['selected_bonds']},
              'Target selection is outside the source linear neighborhood')
    return dict(policy_id=BOND_TARGET_POLICY,choices=choices)


class PreparedRepairBudgetExceeded(TimeoutError):
    """No allowance remains for the next prepared-repair boundary/native job."""


def execute_prepared_dictionary_repair(bundle, phenix, output, *, native_timeout_seconds=120,
        attribution_timeout_seconds=90, derivative_timeout_seconds=300,
        total_timeout_seconds=None, qualify_no_repair=False, optional_failure_policy=None, compact_evidence=False, plane_support=None, bond_targets=None, automatic_bond_targets=False, _attempt_identity=None, _remaining_seconds=None):
    """Run a bounded repair chain and freeze only an independently usable result.

    The input is the existing source/site bundle, including acquired component
    snapshots and exact ordered PHIL. A graph-only no-op creates no native job
    and makes no whole-bundle usability claim unless qualify_no_repair is enabled.
    That frozen mode independently checks and publishes the original without
    inventing repair attribution. Malformed proof still raises. Known negative numerical records
    go through the existing selector; malformed evidence or adapter exceptions
    stop the call with every partial output preserved. A selected runtime is
    diagnostic only and remains independently readable after this job is gone.
    An explicit optional-failure policy permits only exact, owned stopped native
    failures after original checks to reach the independent original gate.
    Corrupt evidence, unknown cleanup, interruptions and arbitrary exceptions raise.

    Explicit source-neighborhood bond choices capture one selected numerical
    library and try only requested target changes, leaving ESDs unchanged. Missing
    reference support or unchanged targets keep the existing qualification path;
    a stopped lookup failure requires the existing explicit optional-failure policy;
    no new scientific acceptance threshold is assigned. Optional automatic_bond_targets
    instead freezes source/library-discovered choices after earlier stages, using
    the same attribution/selection route. It cannot be combined with explicit pairs.
    Matching/unsupported proposals remain visible; omitted intent keeps old behavior.

    An optional integer total allowance (1-3600 seconds) begins before preflight.
    Each native job receives at most the whole seconds remaining. Local Python
    work and worker cleanup are cooperative boundaries, not forcibly interrupted;
    an overrun refuses later work/success and preserves all partial output. This
    does not own discovery, acquisition, recovery or an interrupted attempt. An
    optional enclosing allowance additionally clamps every native phase and
    publication boundary without changing the configured local limits.
    """
    # Explicit support is an already completed generation, never a new generator
    # or a permission to retry. The same owner runs all new native calculations.
    discovery_fields = bond_discovery_fields(automatic_bond_targets,bond_targets)
    storage_fields = compact_evidence_fields(compact_evidence)
    failure_fields = failure_policy_fields(optional_failure_policy)
    _need(type(qualify_no_repair) is bool, 'Require a boolean no-repair qualification mode')
    limits = {'native': native_timeout_seconds, 'attribution': attribution_timeout_seconds,
              'derivatives': derivative_timeout_seconds}
    _need(all(type(v) is int and 1 <= v <= (300 if k == 'attribution' else 600)
              for k, v in limits.items()), 'Require bounded native phase deadlines')
    _need(total_timeout_seconds is None or (type(total_timeout_seconds) is int
          and 1 <= total_timeout_seconds <= 3600), 'Require a bounded integer total repair allowance')
    from .cif_generation_process import _valid_attempt_identity
    _need(_attempt_identity is None or _valid_attempt_identity(_attempt_identity), 'Invalid prepared attempt identity')
    started = monotonic()
    outer = OuterAllowance(_remaining_seconds, monotonic, PreparedRepairBudgetExceeded)
    phase = 'PREFLIGHT'

    def check_budget(minimum=0, *, elapsed=None):
        cap = outer.remaining()
        if total_timeout_seconds is None:
            remaining = cap
        else:
            remaining = total_timeout_seconds - (monotonic() - started if elapsed is None else elapsed)
            if cap is not None: remaining = min(remaining, cap)
        if remaining is None:
            return None
        if remaining <= 0 or remaining < minimum:
            raise PreparedRepairBudgetExceeded(
                f'Prepared repair budget exhausted during {phase}; '
                f'{remaining:.6f}s remain, {minimum}s required; use no recovery inference')
        return remaining

    def phase_limit(kind):
        remaining = check_budget(1)
        return limits[kind] if remaining is None else min(limits[kind], int(remaining))

    original = Path(bundle).absolute()
    output = _snapshot_destination(output).resolve()
    _need(not original.resolve().is_relative_to(output) and not output.is_relative_to(original.resolve()),
          'Repair output and source bundle must be separate')
    installation = Path(phenix.root).resolve()
    _need(not output.is_relative_to(installation) and not installation.is_relative_to(output),
          'Repair output must be separate from the selected installation')
    before = _tree(original)
    prepared = read_dictionary_bundle(original)
    support_config, support_files = _plane_support_snapshot(original,plane_support)
    bond_config = _bond_target_choices(original,bond_targets)
    if support_config is not None:
        _need(all(not output.is_relative_to(Path(row['request_directory']).absolute())
                  and not Path(row['request_directory']).absolute().is_relative_to(output)
                  for row in plane_support.values()), 'Repair output must be separate from plane support')
    consumer = prepared['report']['consumer']
    _need(verify_current_consumer(phenix, phenix.executables['phenix.ready_set'], consumer),
          'Prepared bundle consumer differs from selected installation')
    _need(_tree(original) == before, 'Source bundle changed during preflight')
    check_budget()
    output.mkdir(parents=True, exist_ok=False)
    frozen = output/'bundle'
    for name, data in before.items():
        path = frozen/name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(data)
    if support_config is not None:
        for name in support_config['directories']:(output/'plane-support'/name).mkdir(parents=True,exist_ok=True)
        for name,data in support_files.items():
            path=output/'plane-support'/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as stream:stream.write(data)
    phase = 'PREPARATION'
    report = dict(schema_version=1, policy_id=POLICY_ID, status='RUNNING',
        phase_limits_seconds=limits, bundle={'anchor':'repair_directory','path':'bundle'},
        native_receipts=[], selection=None, runtime=None, automatic_adoption=False,
        whole_acquisition_ownership='NOT_IMPLEMENTED',
        total_deadline='NOT_CONFIGURED' if total_timeout_seconds is None else 'COOPERATIVE_PREPARED_REPAIR_BUDGET',
        total_timeout_seconds=total_timeout_seconds,
        retry='NOT_AUTHORIZED; USE_FRESH_OUTPUT', refinement='NOT_RUN', model_optimization='NOT_RUN')

    report.update(failure_fields); report.update(storage_fields)
    if support_config is not None: report['plane_support'] = support_config
    if bond_config is not None: report['bond_targets'] = bond_config
    report.update(discovery_fields)
    if qualify_no_repair: report['qualify_no_repair'] = True

    processes = PreparedRepairProcesses(output, attempt_identity=_attempt_identity)
    report['process_evidence'] = {'anchor':'repair_directory','path':'ownership/repair.json'}

    def event(state):
        # Append-only progress is diagnostic, not process ownership or a resumable
        # request. In particular, a RUNNING event never authorizes a new attempt.
        with (output/'progress.jsonl').open('ab') as stream:
            stream.write(_bytes(dict(phase=phase, state=state)))

    def unchanged():
        _need(_tree(original) == before and _tree(frozen) == before,
              'Source or frozen preparation changed during repair execution')
        if support_config is not None:
            checked, current = _plane_support_snapshot(original,plane_support)
            _need(checked == support_config and current == support_files
                  and _tree(output/'plane-support') == support_files,
                  'Plane support changed during repair execution')
        _need(_bond_target_choices(original,bond_targets)==bond_config,
              'Explicit bond target choices changed during execution')
        refs = [*report['native_receipts'], *report.get('plane_plans',[]), *report.get('bond_plans',[]),
                *([report['energy_library']] if 'energy_library' in report else []),
                *([report['bond_discovery']] if 'bond_discovery' in report else []),
                *([report['plan']] if 'plan' in report else [])]
        _need(all(reference(output/ref['path']) == ref for ref in refs),
              'Recorded execution reference changed during repair execution')
        if 'energy_library' in report: read_energy_library(output/'energy-library')
        check_budget()

    def reference(path):
        path = Path(path).absolute()
        _need(path.is_relative_to(output), 'Repair receipt escaped its owned output')
        data = _read(path)
        return dict(anchor='repair_directory', path=path.relative_to(output).as_posix(),
                    sha256=sha256(data).hexdigest(), size=len(data))

    def capture(label, dictionaries, phils):
        parent = output/'native'/label
        result = inspect_native_bundle(prepared['model'], dictionaries, parent,
            phenix.executables['phenix.python'], environment=phenix.environment,
            phenix_version=phenix.version, timeout_seconds=phase_limit('native'),
            phil_files=phils, phil_namespace_policy='refinement-root-to-interpreter-v1',
            inventory_detail='linked', policy_inventory=True, energy_inventory=True,
            **prepared['native_options'], _process_runner=processes.runner('native-'+label))
        receipt = Path(result['native_directory']).absolute()/'native_receipt.json'
        _need(receipt.is_relative_to(parent), 'Native capture returned another phase directory')
        report['native_receipts'].append(reference(receipt))
        unchanged()
        completed = result['execution']['status'] == 'COMPLETED' and result['execution']['returncode'] == 0
        if not completed and optional_failure_policy is not None and label not in {'baseline','000'}:
            report['optional_failure'] = inspect_prepared_native_failure(output,'native-'+label)
            _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer),
                  'Current consumer changed after optional native failure')
            return None
        _need(completed, 'Native capture did not complete; no selection is authorized')
        return receipt

    def finish(status):
        unchanged()
        report['status'] = status
        if automatic_bond_targets: validate_prepared_bond_discovery(output,report)
        elapsed = monotonic() - started
        check_budget(elapsed=elapsed)
        report['elapsed_seconds'] = elapsed
        with (output/'repair_execution.json').open('xb') as stream: stream.write(_bytes(report))
        event(status)
        _need(processes.finish('RETURNED'), 'Prepared native process cleanup remains unverified')
        return report

    proof_scratch = None
    try:
        event('STARTED'); unchanged()
        prepared = read_dictionary_bundle(frozen)
        # Attribution binds the complete native model, including components
        # supplied by the installed library rather than acquired dictionaries.
        # The existing planner marks those without an explicit provider unassessed.
        modeled = sorted({site['code'] for site in _model_inventory(prepared['model']).values()})
        plan = prepare_linear_torsion_bundle(prepared['after_dictionaries'], modeled, output/'plan')
        report['plan'] = reference(output/'plan/linear_torsion_bundle.json')
        discovered_codes = [code for code,row in prepared_bond_queries(frozen).items() if row['selected_bonds']] if automatic_bond_targets else []
        if not plan['steps'] and support_config is None and bond_config is None and not discovered_codes and not qualify_no_repair:
            return finish('NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED')
        phase = 'SOURCE_NATIVE'; event('STARTED')
        baseline = capture('baseline', prepared['before_dictionaries'], prepared['before_phils'])
        stages = [plan['inputs']] + [step['dictionaries_after'] for step in plan['steps']]
        receipts = [capture('000', [output/'plan'/r['path'] for r in stages[0]], prepared['after_phils'])]
        source_review = inspect_dictionary_bundle_native(frozen, baseline, receipts[0])
        report['source_qualification'] = source_review
        if source_review['diagnostic_continuation']['allowed'] is not True:
            return finish('SOURCE_PREPARATION_UNQUALIFIED')
        phase = 'ORIGINAL_DERIVATIVES'; event('STARTED')
        original_gradient = output/'original-gradient'
        audit_captured_mixed_gradients(receipts[0], phenix, original_gradient,
                                      timeout_seconds=phase_limit('derivatives'), _process_runner=processes.runner(original_gradient.name))
        unchanged()
        original_options = dict(bundle=frozen, baseline_receipt=baseline, candidate_receipt=receipts[0],
            original_gradient_directory=original_gradient)
        options = original_options
        selector = inspect_dictionary_bundle_original
        publisher = prepare_original_component_runtime_bundle
        if plan['steps']:
            phase = 'REPAIRED_NATIVE'; event('STARTED')
            for i, refs in enumerate(stages[1:], 1):
                receipt = capture(f'{i:03d}', [output/'plan'/r['path'] for r in refs], prepared['after_phils'])
                if receipt is None:break
                receipts.append(receipt)
            if 'optional_failure' not in report:
                phase = 'ATTRIBUTION'; event('STARTED')
                audit_captured_linear_attribution(output/'plan', receipts, phenix, output/'attribution',
                    timeout_seconds=phase_limit('attribution'), _process_runner=processes.runner('attribution'))
                unchanged()
        dictionaries = [output/'plan'/ref['path'] for ref in stages[-1]]
        plane_attributions = []; bond_attributions = []
        if support_config is not None and 'optional_failure' not in report:
            phase = 'PLANE_REPAIR'; event('STARTED'); report['plane_results'] = []; report['plane_plans'] = []
            for i, (code, number) in enumerate(support_config['choices'].items()):
                source = resolve_dictionary_snapshot(frozen/'components'/code/'snapshot')['source']
                request = output/'plane-support'/code
                index = prepared['after_dictionaries'].index(prepared['component_dictionaries'][code])
                candidate = output/'plane-candidates'/f'{i:03d}.cif'
                try:
                    proposal = prepare_owned_trigonal_plane_candidate(source,dictionaries[index],code,request,number,candidate)
                except UnsupportedPlaneCompletion as exc:
                    _need(not candidate.exists(), 'Unsupported plane completion left an unexpected candidate')
                    report['plane_results'].append(dict(component=code,status='NO_SUPPORTED_PLANE_COMPLETION',reason=str(exc)))
                    unchanged(); continue
                unchanged()
                changed = list(dictionaries); changed[index] = candidate
                stage = dict(schema_version=1,policy_id='cif-prepared-plane-stage-v1',component=code,
                    dictionary_index=index,attempt_number=number,native_number=len(receipts),
                    candidate=reference(candidate),proposal=proposal)
                stage_path=candidate.with_suffix('.json')
                with stage_path.open('xb') as stream:stream.write(_bytes(stage))
                report['plane_plans'].append(reference(stage_path))
                after = capture(f'{len(receipts):03d}',changed,prepared['after_phils'])
                if after is None:
                    report['plane_results'].append(dict(component=code,status='KNOWN_STOPPED_NATIVE_FAILURE',
                        candidate=reference(candidate),proposal=proposal))
                    break
                attribution = output/f'plane-attribution-{i:03d}'
                numerical = audit_captured_plane_attribution(source,code,request,number,receipts[-1],after,index,
                    phenix,attribution,timeout_seconds=phase_limit('attribution'),
                    compact_inventory=compact_evidence, _process_runner=processes.runner(attribution.name))
                report['plane_results'].append(dict(component=code,status=numerical['status'],
                    candidate=reference(candidate),proposal=proposal,
                    attribution=reference(attribution/'captured_plane_attribution.json')))
                plane_attributions.append(attribution); dictionaries = changed; receipts.append(after)
                unchanged()
        if (bond_config is not None or discovered_codes) and 'optional_failure' not in report:
            phase='BOND_REFERENCE';event('STARTED');report['bond_results']=[];report['bond_plans']=[]
            library=output/'energy-library'
            lookup=capture_energy_library(phenix,consumer,library,
                timeout_seconds=min(120,phase_limit('native')),
                _process_runner=processes.runner(library.name))
            report['energy_library']=reference(library/'energy_library_receipt.json');unchanged()
            _need(lookup['status']=='SELECTED_NATIVE_ENERGY_LIBRARY_CAPTURED' or optional_failure_policy is not None,
                  'Numerical library lookup failed without the explicit optional-failure policy')
            bond_choices = bond_config['choices'] if bond_config is not None else {code:[] for code in discovered_codes}
            if automatic_bond_targets:
                discovery = bond_discovery_plan(output,dictionaries)
                with (output/DISCOVERY_REPORT).open('xb') as stream:stream.write(_bytes(discovery))
                report['bond_discovery'] = reference(output/DISCOVERY_REPORT)
                if discovery['status']=='DISCOVERED': bond_choices=discovery['choices']
                unchanged()
            for i,(code,bonds) in enumerate(bond_choices.items()):
                if lookup['status']!='SELECTED_NATIVE_ENERGY_LIBRARY_CAPTURED':
                    report['bond_results'].append(dict(component=code,status='REFERENCE_UNAVAILABLE',
                        library=report['energy_library']));continue
                phase='BOND_REPAIR';event('STARTED')
                source=resolve_dictionary_snapshot(frozen/'components'/code/'snapshot')['source']
                index=prepared['after_dictionaries'].index(prepared['component_dictionaries'][code])
                numerical_reference=energy_library_linear_reference(source,dictionaries[index],code,library/'energy-library.cif')
                qualification=qualify_energy_reference(source,dictionaries[index],code,numerical_reference,library,consumer=consumer)
                comparison=compare_linear_bond_reference(source,dictionaries[index],code,numerical_reference)
                rows={tuple(row['atoms']):row for row in comparison['bonds']}
                _need(all(tuple(pair) in rows for pair in bonds),'Requested bond disappeared from source query')
                if any(rows[tuple(pair)]['reference_equilibrium_angstrom'] is None for pair in bonds):
                    report['bond_results'].append(dict(component=code,status='NO_SUPPORTED_BOND_REFERENCE',
                        requested_bonds=bonds));unchanged();continue
                if all(rows[tuple(pair)]['target_angstrom']==rows[tuple(pair)]['reference_equilibrium_angstrom'] for pair in bonds):
                    report['bond_results'].append(dict(component=code,status='NO_TARGET_CHANGE',requested_bonds=bonds))
                    unchanged();continue
                candidate=output/'bond-candidates'/f'{i:03d}.cif'
                proposal=prepare_linear_bond_candidate(source,dictionaries[index],code,numerical_reference,candidate,bonds=bonds)
                reference_path=candidate.with_suffix('.reference.json')
                with reference_path.open('xb') as stream:stream.write(_bytes(numerical_reference))
                stage=dict(schema_version=1,policy_id='cif-prepared-bond-stage-v1',component=code,
                    dictionary_index=index,requested_bonds=bonds,native_number=len(receipts),
                    candidate=reference(candidate),numerical_reference=reference(reference_path),
                    library=report['energy_library'],reference_qualification=qualification,proposal=proposal,
                    **({'discovery':report['bond_discovery']} if automatic_bond_targets else {}))
                stage_path=candidate.with_suffix('.json')
                with stage_path.open('xb') as stream:stream.write(_bytes(stage))
                report['bond_plans'].append(reference(stage_path));unchanged()
                changed=list(dictionaries);changed[index]=candidate
                after=capture(f'{len(receipts):03d}',changed,prepared['after_phils'])
                if after is None:
                    report['bond_results'].append(dict(component=code,status='KNOWN_STOPPED_NATIVE_FAILURE',
                        candidate=reference(candidate)));break
                attribution=output/f'bond-attribution-{i:03d}'
                numerical=audit_captured_bond_attribution(source,code,reference_path,receipts[-1],after,index,
                    phenix,attribution,bonds=bonds,timeout_seconds=phase_limit('attribution'),
                    _process_runner=processes.runner(attribution.name))
                report['bond_results'].append(dict(component=code,status=numerical['status'],
                    candidate=reference(candidate),attribution=reference(attribution/'captured_bond_attribution.json')))
                bond_attributions.append(attribution);dictionaries=changed;receipts.append(after);unchanged()
        if 'optional_failure' not in report and (plan['steps'] or plane_attributions or bond_attributions):
            attribution = output/'attribution'
            if plane_attributions or bond_attributions:
                # This chain only duplicates existing frozen native proofs. Keep
                # assembly temporary; publication freezes it before this closes.
                # Original/partial native outputs remain in their owned paths.
                proof_scratch = TemporaryDirectory(prefix='prepared-repair-proof-')
                attribution = Path(proof_scratch.name).resolve()/'repair-chain'
                prepare_repair_chain(plane_attributions,attribution,
                    linear_attribution=output/'attribution' if plan['steps'] else None,
                    **(dict(bond_attributions=bond_attributions,energy_library=output/'energy-library') if bond_attributions else {}))
            phase = 'REPAIRED_DERIVATIVES'; event('STARTED')
            repaired_gradient = output/'repaired-gradient'
            audit_captured_mixed_gradients(receipts[-1], phenix, repaired_gradient,
                timeout_seconds=phase_limit('derivatives'), _process_runner=processes.runner(repaired_gradient.name))
            unchanged()
            options = dict(bundle=frozen, baseline_receipt=baseline, attribution_directory=attribution,
                original_gradient_directory=original_gradient, repaired_gradient_directory=repaired_gradient,
                **(dict(repair_chain=True) if plane_attributions or bond_attributions else {}))
            selector = inspect_dictionary_bundle_repair
            publisher = prepare_repaired_component_runtime_bundle
        phase = 'SELECTION'; event('STARTED')
        selection = selector(**options)
        report['selection'] = selection
        if selection['decision']['selected'] is None:
            return finish('NO_USABLE_BUNDLE')
        phase = 'PUBLICATION'; event('STARTED')
        # Recheck before publication; changes cannot produce a successful output.
        unchanged()
        publisher(output=output/'runtime', **options, **storage_fields)
        saved = resolve_runtime_bundle(output/'runtime')
        _need(('evidence_storage' in saved['manifest']) == compact_evidence,
              'Published repair storage differs from the frozen choice')
        _need(saved['manifest']['decision']['selected'] == selection['decision']['selected'],
              'Published repair selection changed')
        report['runtime'] = reference(output/'runtime/runtime_bundle.json')
        return finish('QUALIFIED_DIAGNOSTIC_RUNTIME')
    except BaseException as exc:
        # Do not convert corrupt/contradictory evidence or interrupted jobs into
        # routine negative chemistry. Underlying adapters own their child cleanup.
        try:
            processes.finish('RAISED')
        except Exception as seal_error:
            add_failure_note(exc, 'Ownership completion could not be sealed', seal_error)
        state = 'BUDGET_EXHAUSTED' if isinstance(exc, PreparedRepairBudgetExceeded) else 'EXCEPTION'
        try:
            event(state + '; PARTIAL_OUTPUT_PRESERVED; NO_RECOVERY_AUTHORITY')
        except Exception as reporting_error:
            add_failure_note(exc, 'Failure progress could not be recorded', reporting_error)
        raise
    finally:
        if proof_scratch is not None:
            proof_scratch.cleanup()
