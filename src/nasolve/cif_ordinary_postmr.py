"""Ordinary construction/NAR input entry into the existing immutable request.

Construction, continuation and read-only result helpers share the existing
complete-request owner. Checked preparation is not refinement/checkpoint adoption.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .cif_acquisition_sources import freeze_acquisition_sources
from .cif_phenix_configuration import configure_dictionary_engine
from .cif_postmr_request import initialize_postmr_dictionary_request, prepare_postmr_literal_inputs
from .phenix_runtime import PhenixInstallation


@dataclass(frozen=True)
class PreparedPostMRRequest:
    """Live execution arguments; the existing request owns durable evidence.

    Generation settings contain the caller environment and must not be serialized.
    No completed execution, selected model or checkpoint is implied by this value.
    """
    run_directory: Path
    request_directory: Path
    request: dict
    generation: dict = field(repr=False)


def initialize_ordinary_postmr_request(run_directory, phenix: PhenixInstallation, *,
        expected_dialect, coot_executable=None, data_root=None, allow_mr_review=False,
        modified_pairs_only=False, restraint_scope=None, allow_unreviewed_backbone=False,
        narestraints_builder=None, modified_pair_builder=None, generation_options=None,
        continuation_options=None, **execution_limits) -> PreparedPostMRRequest:
    """Prepare ordinary inputs once and publish a fresh complete request.

    Configuration/chemical permissions remain explicit. Existing constructors,
    source authority, literal compiler and request context gates own their rules.
    The default CLI remains unchanged. No legacy modifiers, cache adapter, ReadySet
    or request execution runs on this route. Failure retains all partial outputs;
    an existing PostMR directory cannot be prepared again in place.
    """
    from .postmr import _prepare_postmr
    if generation_options is not None and not isinstance(generation_options,dict):
        raise ValueError('Require explicit generation options')
    options = dict(generation_options or {})
    allowed = {'single_block_steps','timeout_seconds','max_attempts','bond_representation_policy'}
    if set(options)-allowed:
        raise ValueError('Unsupported ordinary generation option')
    configured = configure_dictionary_engine(phenix,expected_dialect=expected_dialect,**options)
    def initialize(inputs):
        root = inputs.run_directory/'PostMR'/'DictionaryEngine'
        sources, literal, request = [root/name for name in ('sources','literal','request')]
        if root.exists() or root.is_symlink():raise FileExistsError(root)
        freeze_acquisition_sources(list(inputs.components),sources,data_root=data_root,
            ready_set_executable=configured.ready_set_executable)
        literal_inputs = None
        if inputs.supplementary_phils:
            prepare_postmr_literal_inputs(inputs.model_path,list(inputs.supplementary_phils),sources,literal,
                data_root=data_root,ready_set_executable=configured.ready_set_executable)
            literal_inputs = literal
        components = [dict(code=code,generation=configured.generation) for code in inputs.components]
        record = initialize_postmr_dictionary_request(inputs.model_path,inputs.run_report,components,None,request,
            consumer=configured.consumer,ready_set_executable=None,supplementary_phils=list(inputs.supplementary_phils),
            literal_na_inputs=literal_inputs,frozen_sources=sources,construction_inputs=inputs.run_directory,
            continuation_options=continuation_options,**execution_limits)
        return PreparedPostMRRequest(inputs.run_directory,request,record,
            {code:dict(configured.generation) for code in inputs.components})
    result = _prepare_postmr(run_directory,configured.ready_set_executable,phenix_installation=phenix,
        coot_executable=coot_executable,environment=phenix.environment,data_root=data_root,
        allow_mr_review=allow_mr_review,modified_pairs_only=modified_pairs_only,restraint_scope=restraint_scope,
        allow_unreviewed_backbone=allow_unreviewed_backbone,narestraints_builder=narestraints_builder,
        modified_pair_builder=modified_pair_builder,_dictionary_handler=initialize)
    if not isinstance(result,PreparedPostMRRequest):raise ValueError('Ordinary request boundary was not reached')
    return result


@dataclass(frozen=True)
class CheckedPostMRResult:
    """One verified attempt, expressed for ordinary callers without adoption claims.

    Paths come together from the existing exact-result reader. This live value is
    not a new saved schema; report_path points to the original immutable result.
    """
    run_directory: Path
    request_directory: Path
    attempt_number: int
    status: str
    message: str
    selected: str | None
    model_path: Path | None
    dictionary_paths: tuple[Path, ...]
    restraint_paths: tuple[Path, ...]
    readyset_status: str
    report_path: Path
    limitations: tuple[str, ...]
    refinement_ready: bool = field(default=False, init=False)


def _ordinary_request_directory(run_directory):
    from .cif_repair_attempt import _root
    return _root(run_directory)/'PostMR'/'DictionaryEngine'/'request'


def _read_ordinary_postmr_result(run_directory, *, attempt_number):
    """Read an exact completed preparation, without discovering or running tools.

    A failed/unqualified attempt cannot supply a model. A retained starting model
    requires the same independent verification as the underlying request reader;
    missing or changed evidence propagates as an error, never as a fallback.
    """
    from .cif_complete_request import read_dictionary_request_result
    from .cif_dictionary_sites import _need
    _need(type(attempt_number) is int and attempt_number >= 1, 'Require an exact positive attempt number')
    request = _ordinary_request_directory(run_directory)
    exact = read_dictionary_request_result(request, attempt_number)
    _need(exact.get('construction_inputs') is not None, 'Require recorded ordinary construction evidence')
    runtime = exact['runtime']
    continued = exact.get('continuation')
    selected = None if runtime is None else runtime['manifest']['decision']['selected']
    messages = {
        'readyset_checked_model': 'ReadySet supplied the checked model and matching restraints.',
        'readyset_ordered_checked_model': 'ReadySet supplied the checked model; atom ordering was restored and checked.',
        'verified_parent_runtime': 'The independently checked starting model and its restraints were retained; the ReadySet result was not selected.',
        'verified_prepared_bundle': 'The independently checked starting model and its restraints were retained.',
        'repaired_prepared_bundle': 'The model and repaired restraints passed the preparation checks; ReadySet was not run.',
    }
    _need(selected is None or selected in messages, 'Unsupported checked preparation selection')
    readyset_status = ('NOT_RUN' if continued is None else
                       continued['report']['phases'].get('readyset', 'NOT_RUN'))
    result = CheckedPostMRResult(
        run_directory=request.parents[2], request_directory=request, attempt_number=attempt_number,
        status=exact['result']['status'],
        message=messages.get(selected, 'Preparation did not establish a usable model/restraint combination.'),
        selected=selected, model_path=None if runtime is None else runtime['model'],
        dictionary_paths=() if runtime is None else tuple(runtime['dictionaries']),
        restraint_paths=() if runtime is None else tuple(runtime['phils']),
        readyset_status=readyset_status,
        report_path=request/'attempts'/f'attempt-{attempt_number:04d}'/'result.json',
        limitations=(
            'These preparation checks do not establish diffraction-refinement success; checkpoint adoption is a separate explicit action.',
            'General complete-plane repair still needs integration into this preparation route.',
        ),
    )

    return result, exact


def read_ordinary_postmr_result(run_directory, *, attempt_number) -> CheckedPostMRResult:
    """Read an exact preparation through the existing evidence reader once."""
    return _read_ordinary_postmr_result(run_directory, attempt_number=attempt_number)[0]


def prepare_checked_postmr(run_directory, phenix, *, store_root=None, **preparation_options) -> CheckedPostMRResult:
    """Construct once, execute one owned attempt, and return its exact checked result.

    This explicit route does not replace the default PostMR/campaign path yet.
    After interruption use continue_checked_postmr with the recorded attempt
    number; never call this constructor again on partial preparation.
    """
    from .cif_complete_request import execute_dictionary_request_attempt
    from .cif_dictionary_store import default_dictionary_store
    options = dict(preparation_options)
    options.setdefault('expected_dialect', 'CHEMICAL_COMPONENTS_CIF')
    options.setdefault('continuation_options', dict(readyset_timeout_seconds=120, restore_serialization=True))
    prepared = initialize_ordinary_postmr_request(run_directory, phenix, **options)
    result = execute_dictionary_request_attempt(prepared.request_directory, phenix,
        default_dictionary_store() if store_root is None else store_root,
        generation=prepared.generation, after_attempt=0)
    return read_ordinary_postmr_result(prepared.run_directory, attempt_number=result['attempt_number'])


def continue_checked_postmr(run_directory, phenix, *, after_attempt, store_root=None) -> CheckedPostMRResult:
    """Start one fresh attempt from the saved preparation, with no repeat Coot/NAR.

    after_attempt=0 executes a published request that has never started. Otherwise
    the exact last attempt must match and its processes must be known stopped.
    Recipe/options come from the frozen request; the existing executor verifies
    the current installation against every saved source/dispatcher binding under
    its own lock. This helper never grants retry permission or repairs history.
    """
    import json
    from .cif_complete_request import _request, execute_dictionary_request_attempt
    from .cif_dictionary_sites import _need
    from .cif_dictionary_store import default_dictionary_store
    _need(type(after_attempt) is int and after_attempt >= 0, 'Require an exact previous attempt number (zero before the first)')
    root = _ordinary_request_directory(run_directory)
    request = _request(root)
    config = request['configuration']
    _need('construction_inputs' in config, 'Require recorded ordinary construction evidence')
    generation = {}
    configured = {}
    for code, site in config['controls']['sites'].items():
        saved = site['generation']; recipe = saved['options']['recipe']; binding = saved['binding']
        _need(not recipe.get('multiple_planes', False), 'Ordinary preparation does not yet compose multiple-plane repairs')
        options = dict(expected_dialect=recipe['expected_dialect'], single_block_steps=recipe['single_block_steps'],
                       timeout_seconds=binding['timeout_seconds'], max_attempts=binding['max_attempts'],
                       bond_representation_policy=recipe.get('bond_representation_policy'))
        key = json.dumps(options, sort_keys=True, allow_nan=False)
        if key not in configured:
            configured[key] = configure_dictionary_engine(phenix, **options)
        generation[code] = dict(configured[key].generation)
    result = execute_dictionary_request_attempt(root, phenix,
        default_dictionary_store() if store_root is None else store_root,
        generation=generation, after_attempt=after_attempt)
    return read_ordinary_postmr_result(run_directory, attempt_number=result['attempt_number'])
