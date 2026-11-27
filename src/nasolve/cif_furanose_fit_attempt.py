"""Number and verify a local sugar fit without modifying its preparation or publishing a checkpoint."""
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .campaign_process import coordinator_alive, current_process_identity, exclusive_lock
from .campaign_records import _sync_directory, path_in, read_record, write_record
from .cif_acquisition_preparation import _freeze
from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _bytes, _hash
from .cif_furanose_bridge import read_fitted_furanose_model
from .cif_furanose_fit import read_furanose_fit_inputs
from .cif_generation_process import _valid_identity
from .cif_ordinary_postmr import _ordinary_request_directory
from .cif_postmr_cache import verify_current_consumer
from .cif_repair_process import _OwnedProcesses, _ProcessScope, _inspect_owned_processes
from .failure_reporting import add_failure_note
from .refinement_contact_geometry import read_refined_contacts


_SCOPE = _ProcessScope('cif-local-sugar-fit-process-v1', 'fit_directory', 'inputs', 'fit.json',
    'inputs', 'input_files', 'fit_sha256', r'geometry', 'ONE_SITE_GEOMETRY_ONLY',
    fixed_paths=(('geometry','native','native/geometry.log'),))
_TIMEOUT = 240
_GEOMETRY_NAMES = {'Bond':'bond', 'Bond angle':'angle', 'Dihedral angle':'dihedral',
                   'Chirality':'chirality', 'Planarity':'planarity', 'Parallelity':'parallelity'}


class _FitProcesses(_OwnedProcesses):
    _scope = _SCOPE


@dataclass(frozen=True)
class SugarFitResult:
    number: int
    model: Path
    report: Path
    observations: dict


def _parent(run, attempt):
    _need(type(attempt) is int and attempt > 0, 'Require an exact preparation attempt')
    root = _ordinary_request_directory(run).parents[2]
    return path_in(root, f'PostMR/SugarFit/preparation-{attempt:04d}')


def _inputs(plan):
    return {'source.pdb':plan.model,
            **{f'dictionary_{i:03d}.cif':d for i,d in enumerate(plan.dictionaries)},
            **{f'native_{i:03d}.phil':p for i,p in enumerate(plan.interpreted_phils)},
            'local.phil':plan.minimization_phil}


def _binding(plan, dispatcher):
    _need(_hash(dispatcher), 'Invalid geometry dispatcher fingerprint')
    return dict(policy_id='cif-local-sugar-geometry-v1', site=plan.site, component=plan.code,
                preparation_result_sha256=plan.result_sha256, native_receipt_sha256=plan.native_receipt_sha256,
                phenix_version=plan.consumer['version'], dispatcher=dict(anchor='phenix_installation',
                path='bin/phenix.geometry_minimization',sha256=dispatcher))


def _argv(files):
    return ['../inputs/'+name for name in files]


def _force_counts(geometry):
    observed = {}
    for label,count in re.findall(rb'^([^\r\n|]+?) \| User supplied \| restraints: (\d+)\s*$', geometry, re.M):
        kind = _GEOMETRY_NAMES.get(label.decode('ascii').strip())
        _need(kind is not None and kind not in observed, 'Unsupported or repeated printed local-fit restraint section')
        observed[kind] = int(count)
    return observed


def _measure(plan, root, number, binding, state):
    _need(set(state['phases']) == {'geometry'}, 'Require exactly one local geometry invocation')
    phase=state['phases']['geometry']
    _need(phase['state'] == 'STOPPED' and 'identity' in phase and phase['finished']['status'] == 'COMPLETED'
          and phase['finished']['returncode'] == 0, 'Local geometry process did not finish successfully')
    reservation = _reservation(root,number,plan.result_sha256)
    _need(all(reservation['coordinator'][key] == state['header']['coordinator'][key]
              for key in ('pid','pgid','host')), 'Local-fit reservation and process owner differ')
    files = _inputs(plan)
    argv = phase['job']['argv_provenance']
    _need(Path(argv[0]).name == 'phenix.geometry_minimization' and argv[1:] == _argv(files)
          and phase['job']['timeout_seconds'] == _TIMEOUT, 'Recorded invocation differs from the local fit')
    expected = {**files,'binding.json':_bytes(binding)}
    _need(set(state['header']['input_files']) == set(expected) and all(
        _read(path_in(root, 'inputs/'+name)) == data for name,data in expected.items()),
        'Local fit inputs differ from the checked preparation')
    returned = path_in(root,'native/relaxed.pdb')
    geometry = path_in(root,'native/relaxed.geo')
    clean, coordinates = read_fitted_furanose_model(plan.seed_directory, returned)
    data = _read(geometry)
    counts = _force_counts(data)
    _need(counts == dict(plan.requested_restraints), 'Printed local-fit forces differ from the checked native request')
    contacts = read_refined_contacts(returned, geometry, [plan.site], minimum_overlap=0.4)
    _need(contacts['status'] == 'OBSERVED' and contacts['model_sha256'] == coordinates['return_sha256']
          and contacts['geometry_sha256'] == sha256(data).hexdigest(), 'Fit contact observations do not match returned files')
    record=dict(schema_version=1, **binding, fit_number=number, reservation_sha256=reservation['record_sha256'],
        process_sha256=phase['finished']['record_sha256'],
        status='GEOMETRY_FIT_FOR_REVIEW', refinement='NOT_RUN', checkpoint_published=False,
        native_parameters=plan.native_parameter_count, user_restraints=counts,
        coordinates=coordinates, geometry_sha256=contacts['geometry_sha256'], contact_screen=contacts['overlap_screen'])
    return clean, record


def _reservation(root, number, preparation_sha256):
    reservation = read_record(path_in(root,'reservation.json'))
    _need(type(reservation.get('number')) is int and reservation['number'] == number
          and reservation.get('preparation_result_sha256') == preparation_sha256
          and _valid_identity(reservation.get('coordinator')), 'Local-fit reservation differs from this preparation')
    return reservation


def _read_finished(plan, root, number):
    state = _inspect_owned_processes(root, _SCOPE)
    _need(state['state'] == 'STOPPED' and state['finished']['outcome'] == 'RETURNED',
          'Local fit is incomplete; its partial results remain in the numbered directory')
    saved = read_record(path_in(root,'result.json'))
    dispatcher = saved.get('dispatcher')
    _need(isinstance(dispatcher, dict), 'Local-fit dispatcher binding is missing')
    binding = _binding(plan, dispatcher.get('sha256'))
    clean, observed = _measure(plan, root, number, binding, state)
    model = path_in(root,'candidate.pdb')
    _need(_read(model) == clean and {k:v for k,v in saved.items() if k != 'record_sha256'} == observed,
          'Local-fit coordinates or scientific observations changed')
    return SugarFitResult(number,model,root/'result.json',observed)


def read_checked_sugar_fit(run, *, attempt_number, fit_number):
    """Reopen a specified fit without starting native tools or creating a directory."""
    _need(type(fit_number) is int and fit_number > 0, 'Require an exact local-fit number')
    parent=_parent(run, attempt_number)
    root=path_in(parent,f'fit-{fit_number:04d}')
    _need(root.is_dir(), 'Requested local fit does not exist')
    plan=read_furanose_fit_inputs(run, attempt_number=attempt_number)
    return _read_finished(plan, root, fit_number)


def _next_fit(parent, after_fit, preparation_sha256):
    paths = [p for p in parent.iterdir() if p.name != 'fit.lock']
    numbers = []
    for path in paths:
        match = re.fullmatch(r'fit-(\d{4,})',path.name)
        _need(match and not path.is_symlink() and path.is_dir(), 'Unexpected local-fit directory member')
        numbers.append(int(match[1]))
    _need(sorted(numbers) == list(range(1,len(numbers)+1))
          and all((parent/f'fit-{n:04d}').is_dir() for n in numbers), 'Numbered local fits are not contiguous')
    last=len(numbers)
    if after_fit is None and last:
        return last, False
    _need(after_fit is None or (type(after_fit) is int and 0 < after_fit == last),
          'A fresh fit requires the exact preceding fit number')
    if last:
        previous=parent/f'fit-{last:04d}'
        state=_inspect_owned_processes(previous, _SCOPE)
        stopped=state['state'] in {'STOPPED','STOPPED_UNFINISHED'} and state['activity'] is False
        if not stopped and not (previous/'ownership'/_SCOPE.header).exists():
            # A power loss can precede the native owner's header. Reservation
            # preceded publication of this numbered folder and any worker.
            reservation=_reservation(previous,last,preparation_sha256)
            stopped=(not path_in(previous,'ownership/phases').exists()
                     and coordinator_alive(reservation['coordinator']) is False)
        _need(stopped, 'Previous local fit has no proof its processes stopped')
        _need(state.get('finished',{}).get('outcome') != 'RETURNED', 'A completed fit is already available for this preparation')
    return last+1, True


def fit_checked_sugar(run, discover_phenix, *, attempt_number, after_fit=None):
    """Run one site-only geometry fit; a completed exact fit reopens by default."""
    parent=_parent(run, attempt_number)
    plan=read_furanose_fit_inputs(run, attempt_number=attempt_number)
    parent.mkdir(parents=True,exist_ok=True)
    with exclusive_lock(parent/'fit.lock'):
        number,fresh=_next_fit(parent,after_fit,plan.result_sha256)
        root=path_in(parent,f'fit-{number:04d}')
        if not fresh:
            return _read_finished(plan,root,number)
        phenix = discover_phenix()
        verify_current_consumer(phenix, phenix.executables['phenix.ready_set'], plan.consumer)
        exe=(Path(phenix.root)/'bin/phenix.geometry_minimization').resolve(strict=True)
        _need(exe.is_relative_to(Path(phenix.root).resolve(strict=True)) and os.access(exe,os.X_OK)
              and exe.name=='phenix.geometry_minimization', 'Require the selected Phenix geometry dispatcher')
        binding=_binding(plan,sha256(exe.read_bytes()).hexdigest())
        files=_inputs(plan)
        with TemporaryDirectory(prefix='.reserve-sugar-fit-', dir=parent.parent) as temporary:
            stage=Path(temporary)
            write_record(stage/'reservation.json', dict(number=number, preparation_result_sha256=plan.result_sha256,
                                                       coordinator=current_process_identity()))
            stage.rename(root)
            _sync_directory(parent)
        _freeze(root/'inputs',{**files,'binding.json':_bytes(binding)},[])
        native=root/'native'
        native.mkdir()
        owner=_FitProcesses(root)
        try:
            code=owner.runner('geometry')([str(exe),*_argv(files)],cwd=native,log_path=native/'geometry.log',
                environment=dict(phenix.environment,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1'),
                timeout_seconds=_TIMEOUT)
            _need(code == 0, f'Phenix geometry fit failed; see {native/"geometry.log"}')
            _need(sha256(exe.read_bytes()).hexdigest() == binding['dispatcher']['sha256'],
                  'Geometry dispatcher changed during the fit')
            clean, record=_measure(plan,root,number,binding,_inspect_owned_processes(root,_SCOPE))
            with (root/'candidate.pdb').open('xb') as handle:
                handle.write(clean)
                handle.flush()
                os.fsync(handle.fileno())
            write_record(root/'result.json',record)
            _need(owner.finish('RETURNED'), 'Local geometry worker cleanup is unresolved')
        except BaseException as exc:
            if not (root/'ownership/finished.json').exists():
                try:
                    owner.finish('RAISED')
                except Exception as seal_error:
                    add_failure_note(exc,'Local geometry cleanup could not be verified',seal_error)
            raise
        return _read_finished(plan,root,number)
