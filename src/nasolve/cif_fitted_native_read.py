"""Obtain one owned, fixed-coordinate Phenix reading of a completed sugar fit."""
from hashlib import sha256
from pathlib import Path

from .campaign_process import exclusive_lock
from .campaign_records import _sync_directory, path_in, read_record, write_record
from .cif_dictionary_sites import _need, _read
from .cif_furanose_fit_attempt import _reservation, next_sugar_job, reserve_sugar_job
from .cif_native_validation import inspect_native_bundle
from .cif_postmr_cache import verify_current_consumer
from .cif_repair_process import _OwnedProcesses, _ProcessScope, _inspect_owned_processes
from .failure_reporting import add_failure_note


_SCOPE = _ProcessScope('cif-fitted-sugar-native-read-v1', 'read_directory', 'inputs', 'read.json',
    'inputs', 'input_files', 'read_sha256', 'native-fitted', 'FIXED_COORDINATE_INTERPRETATION')
_BINDING = 'fit_result_sha256'
_TIMEOUT = 160


class _ReadProcesses(_OwnedProcesses):
    _scope = _SCOPE


def _input_binding(checked, plan, fit):
    def digest(path):
        return sha256(_read(path)).hexdigest()
    return dict(policy_id=_SCOPE.policy_id, preparation_result_sha256=plan.result_sha256,
                parent_native_sha256=plan.native_receipt_sha256, fit_result_sha256=digest(fit.report),
                model_sha256=digest(fit.model), dictionaries=[digest(p) for p in checked.dictionary_paths],
                phils=[digest(p) for p in checked.restraint_paths])


def _receipt_from_job(root, number, binding, state):
    reservation = _reservation(root, number, binding[_BINDING], _BINDING)
    coordinator = state['header']['coordinator']
    _need(all(coordinator[k] == reservation['coordinator'][k] for k in ('pid','pgid','host')),
          'Fitted native read and its reservation have different owners')
    saved_binding = read_record(root/'inputs/binding.json')
    _need(set(state['header']['input_files']) == {'binding.json'} and
          {k:v for k,v in saved_binding.items() if k!='record_sha256'} == binding,
          'Fitted native read was reserved for different coordinates or restraints')
    _need(set(state['phases']) == {'native-fitted'}, 'Require exactly one fitted native reading')
    phase = state['phases']['native-fitted']
    _need(phase['state']=='STOPPED' and 'identity' in phase and phase['finished']['status']=='COMPLETED'
          and phase['finished']['returncode']==0 and phase['job']['timeout_seconds']==_TIMEOUT,
          'The fitted native worker did not finish successfully')
    work = path_in(root, phase['job']['cwd']['path'])
    return work/'native_receipt.json'


def acquire_fit_read(run, checked, plan, fit, *, discover, after, verify):
    """Get verified receipt bytes. An interrupted publication can reuse a finished native job."""
    parent = path_in(run, f'PostMR/FittedNativeReads/preparation-{checked.attempt_number:04d}/fit-{fit.number:04d}')
    binding = _input_binding(checked, plan, fit)
    parent.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(parent/'read.lock'):
        number, fresh = next_sugar_job(parent, after, binding[_BINDING], kind='read', scope=_SCOPE, field=_BINDING)
        root = path_in(parent, f'read-{number:04d}')
        if not fresh:
            state = _inspect_owned_processes(root, _SCOPE)
            _need(state.get('finished',{}).get('outcome') == 'RETURNED',
                  f'Fitted native read {number} is incomplete. Preserve it. After its processes stop, use --after-native-read {number}.')
            receipt = _receipt_from_job(root, number, binding, state)
            saved = read_record(root/'result.json')
            files = verify(receipt)
            _need(saved['receipt_sha256'] == sha256(files[receipt]).hexdigest() and saved[_BINDING] == binding[_BINDING],
                  'Fitted native reading changed after completion')
            return receipt, files

        installation = discover()
        verify_current_consumer(installation, installation.executables['phenix.ready_set'], plan.consumer)
        reserve_sugar_job(root, number, binding[_BINDING], _BINDING)
        (root/'inputs').mkdir()
        write_record(root/'inputs/binding.json', binding)
        owner = _ReadProcesses(root)
        try:
            observation = inspect_native_bundle(fit.model, checked.dictionary_paths, root/'native/fitted',
                installation.executables['phenix.python'], environment=installation.environment,
                phenix_version=installation.version, timeout_seconds=_TIMEOUT, phil_files=checked.restraint_paths,
                phil_namespace_policy='refinement-root-to-interpreter-v1', inventory_detail='linked',
                policy_inventory=True, energy_inventory=True, full_monomer_inventory=True,
                _process_runner=owner.runner('native-fitted'))
            _need(observation.get('status')=='REVIEW' and observation.get('execution',{}).get('returncode')==0,
                  f'Phenix could not read the fitted model. Preserve native read {number}.')
            state = _inspect_owned_processes(root, _SCOPE)
            receipt = _receipt_from_job(root, number, binding, state)
            _need(receipt.parent == Path(observation['native_directory']) and
                  state['phases']['native-fitted']['job']['argv_provenance'] == observation['command'],
                  'Fitted native receipt differs from the owned worker')
            files = verify(receipt)
            write_record(root/'result.json', {_BINDING:binding[_BINDING], 'receipt_sha256':sha256(files[receipt]).hexdigest()})
            _need(owner.finish('RETURNED'), 'Fitted native worker cleanup is unresolved')
        except BaseException as exc:
            if not (root/'ownership/finished.json').exists():
                try:
                    owner.finish('RAISED')
                except Exception as seal_error:
                    add_failure_note(exc, 'Fitted native worker cleanup could not be verified', seal_error)
            raise
        return receipt, files


def compact_verified_read(receipt, originals, archive_files, archive_root, archive_ref):
    """Release an owned read's duplicate files only after exact archived bytes have been reopened."""
    source = receipt.parent
    for path, data in originals.items():
        archived = archive_root/path.relative_to(source)
        _need(archive_files.get(archived) == data, 'Compact fitted native copy differs from its source')
    for path, data in originals.items():
        _need(_read(path) == data, 'Owned native reading changed before compaction')
    write_record(source/'archived_read.json', dict(archive=archive_ref, files=len(originals),
                                                  receipt_sha256=sha256(originals[receipt]).hexdigest()))
    for path in originals:
        path.unlink()
    _sync_directory(source)
