"""Explicit native repair execution for an acquired, source-prepared bundle.

Existing adapters own chemistry, native evidence, numerical qualification and
selection. This coordinator never resumes a directory or promotes missing proof
to a usable fallback. Whole-acquisition ownership/deadlines remain separate.
"""
from hashlib import sha256
from pathlib import Path
from time import monotonic

from .cif_component_runtime import _tree, prepare_repaired_component_runtime_bundle
from .cif_dictionary_store import _bytes, _snapshot_destination
from .cif_dictionary_bundle import read_dictionary_bundle, inspect_dictionary_bundle_native
from .cif_dictionary_bundle_repair import inspect_dictionary_bundle_repair
from .cif_dictionary_sites import _need, _read
from .cif_linear_torsion_bundle import prepare_linear_torsion_bundle
from .cif_native_validation import inspect_native_bundle
from .cif_captured_linear_attribution import audit_captured_linear_attribution
from .cif_captured_mixed_gradients import audit_captured_mixed_gradients
from .cif_postmr_cache import verify_current_consumer
from .cif_runtime_bundle import resolve_runtime_bundle
from .cif_repair_process import PreparedRepairProcesses

POLICY_ID = 'cif-prepared-bundle-repair-execution-v1'


class PreparedRepairBudgetExceeded(TimeoutError):
    """No allowance remains for the next prepared-repair boundary/native job."""


def execute_prepared_dictionary_repair(bundle, phenix, output, *, native_timeout_seconds=120,
        attribution_timeout_seconds=90, derivative_timeout_seconds=300,
        total_timeout_seconds=None):
    """Run a bounded repair chain and freeze only an independently usable result.

    The input is the existing source/site bundle, including acquired component
    snapshots and exact ordered PHIL. A graph-only no-op creates no native job
    and makes no whole-bundle usability claim. Known negative numerical records
    go through the existing selector; malformed evidence or adapter exceptions
    stop the call with every partial output preserved. A selected runtime is
    diagnostic only and remains independently readable after this job is gone.

    An optional integer total allowance (1-3600 seconds) begins before preflight.
    Each native job receives at most the whole seconds remaining. Local Python
    work and worker cleanup are cooperative boundaries, not forcibly interrupted;
    an overrun refuses later work/success and preserves all partial output. This
    does not own discovery, acquisition, recovery or an interrupted attempt.
    """
    limits = {'native': native_timeout_seconds, 'attribution': attribution_timeout_seconds,
              'derivatives': derivative_timeout_seconds}
    _need(all(type(v) is int and 1 <= v <= (300 if k == 'attribution' else 600)
              for k, v in limits.items()), 'Require bounded native phase deadlines')
    _need(total_timeout_seconds is None or (type(total_timeout_seconds) is int
          and 1 <= total_timeout_seconds <= 3600), 'Require a bounded integer total repair allowance')
    started = monotonic()
    phase = 'PREFLIGHT'

    def check_budget(minimum=0, *, elapsed=None):
        if total_timeout_seconds is None:
            return None
        remaining = total_timeout_seconds - (monotonic() - started if elapsed is None else elapsed)
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
    phase = 'PREPARATION'
    report = dict(schema_version=1, policy_id=POLICY_ID, status='RUNNING',
        phase_limits_seconds=limits, bundle={'anchor':'repair_directory','path':'bundle'},
        native_receipts=[], selection=None, runtime=None, automatic_adoption=False,
        whole_acquisition_ownership='NOT_IMPLEMENTED',
        total_deadline='NOT_CONFIGURED' if total_timeout_seconds is None else 'COOPERATIVE_PREPARED_REPAIR_BUDGET',
        total_timeout_seconds=total_timeout_seconds,
        retry='NOT_AUTHORIZED; USE_FRESH_OUTPUT', refinement='NOT_RUN', model_optimization='NOT_RUN')

    processes = PreparedRepairProcesses(output)
    report['process_evidence'] = {'anchor':'repair_directory','path':'ownership/repair.json'}

    def event(state):
        # Append-only progress is diagnostic, not process ownership or a resumable
        # request. In particular, a RUNNING event never authorizes a new attempt.
        with (output/'progress.jsonl').open('ab') as stream:
            stream.write(_bytes(dict(phase=phase, state=state)))

    def unchanged():
        _need(_tree(original) == before and _tree(frozen) == before,
              'Source or frozen preparation changed during repair execution')
        refs = [*report['native_receipts'], *([report['plan']] if 'plan' in report else [])]
        _need(all(reference(output/ref['path']) == ref for ref in refs),
              'Recorded execution reference changed during repair execution')
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
            full_monomer_inventory=True, _process_runner=processes.runner('native-'+label))
        receipt = Path(result['native_directory']).absolute()/'native_receipt.json'
        _need(receipt.is_relative_to(parent), 'Native capture returned another phase directory')
        report['native_receipts'].append(reference(receipt))
        unchanged()
        _need(result['execution']['status'] == 'COMPLETED' and result['execution']['returncode'] == 0,
              'Native capture did not complete; no selection is authorized')
        return receipt

    def finish(status):
        unchanged()
        elapsed = monotonic() - started
        check_budget(elapsed=elapsed)
        report['status'] = status
        report['elapsed_seconds'] = elapsed
        with (output/'repair_execution.json').open('xb') as stream: stream.write(_bytes(report))
        event(status)
        _need(processes.finish('RETURNED'), 'Prepared native process cleanup remains unverified')
        return report

    try:
        event('STARTED'); unchanged()
        prepared = read_dictionary_bundle(frozen)
        plan = prepare_linear_torsion_bundle(prepared['after_dictionaries'],
            prepared['report']['components'], output/'plan')
        report['plan'] = reference(output/'plan/linear_torsion_bundle.json')
        if not plan['steps']:
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
        phase = 'REPAIRED_NATIVE'; event('STARTED')
        for i, refs in enumerate(stages[1:], 1):
            receipts.append(capture(f'{i:03d}', [output/'plan'/r['path'] for r in refs], prepared['after_phils']))
        phase = 'ATTRIBUTION'; event('STARTED')
        audit_captured_linear_attribution(output/'plan', receipts, phenix, output/'attribution',
                                         timeout_seconds=phase_limit('attribution'), _process_runner=processes.runner('attribution'))
        unchanged()
        phase = 'REPAIRED_DERIVATIVES'; event('STARTED')
        repaired_gradient = output/'repaired-gradient'
        audit_captured_mixed_gradients(receipts[-1], phenix, repaired_gradient,
                                      timeout_seconds=phase_limit('derivatives'), _process_runner=processes.runner(repaired_gradient.name))
        unchanged()
        phase = 'SELECTION'; event('STARTED')
        options = dict(bundle=frozen, baseline_receipt=baseline, attribution_directory=output/'attribution',
            original_gradient_directory=original_gradient, repaired_gradient_directory=repaired_gradient)
        selection = inspect_dictionary_bundle_repair(**options)
        report['selection'] = selection
        if selection['decision']['selected'] is None:
            return finish('NO_USABLE_BUNDLE')
        phase = 'PUBLICATION'; event('STARTED')
        # Recheck before publication; changes cannot produce a successful output.
        unchanged()
        prepare_repaired_component_runtime_bundle(output=output/'runtime', **options)
        saved = resolve_runtime_bundle(output/'runtime')
        _need(saved['manifest']['decision']['selected'] == selection['decision']['selected'],
              'Published repair selection changed')
        report['runtime'] = reference(output/'runtime/runtime_bundle.json')
        return finish('QUALIFIED_DIAGNOSTIC_RUNTIME')
    except PreparedRepairBudgetExceeded as exc:
        try:
            processes.finish('RAISED')
        except Exception as seal_error:
            exc.add_note(f'Ownership completion could not be sealed: {seal_error}')
        event('BUDGET_EXHAUSTED; PARTIAL_OUTPUT_PRESERVED; NO_RECOVERY_AUTHORITY')
        raise
    except BaseException as exc:
        # Do not convert corrupt/contradictory evidence or interrupted jobs into
        # routine negative chemistry. Underlying adapters own their child cleanup.
        try:
            processes.finish('RAISED')
        except Exception as seal_error:
            exc.add_note(f'Ownership completion could not be sealed: {seal_error}')
        event('EXCEPTION; PARTIAL_OUTPUT_PRESERVED; NO_RECOVERY_AUTHORITY')
        raise
