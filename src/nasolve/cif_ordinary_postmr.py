"""Ordinary construction/NAR input entry into the existing immutable request.

Construction, continuation and result helpers share the existing complete-request
owner. Optional publication uses the ordinary review-checkpoint contract;
preparation does not establish successful diffraction refinement.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .cif_acquisition_sources import freeze_acquisition_sources, read_acquisition_sources
from .cif_phenix_configuration import configure_dictionary_engine
from .cif_postmr_request import initialize_postmr_dictionary_request, prepare_postmr_literal_inputs
from .cif_prepared_repair_execution import _bond_target_declarations
from .cif_prepared_bond_discovery import bond_discovery_fields
from .phenix_runtime import PhenixInstallation


def _capture_registered_sources(declaration):
    """Validate explicit graph inputs before construction; retain their bytes."""
    from .cif_registered_preparation_input import FILES
    from .cif_dictionary_sites import _need, _read
    from .cif_phosphate_continuation import inspect_registered_backbone
    _need(isinstance(declaration, dict) and set(declaration) == set(FILES),
          'Require exact registered preparation source roles')
    paths = {key: Path(declaration[key]).absolute() for key in FILES}
    originals = {path: _read(path) for path in paths.values()}
    observations = inspect_registered_backbone(paths['registration_model'], paths['registration'],
                                               paths['discovery'], paths['continuations'])
    _need(bool(observations) and all(row['registered_continuation']['measurement_status'] == 'MEASURED'
                                    for row in observations),
          'Registered preparation requires measured explicit continuations')

    def unchanged():
        _need(all(_read(path) == raw for path, raw in originals.items()),
              'Registered preparation source changed during ordinary construction')
    unchanged()
    return paths, unchanged


def _read_construction_inputs(frozen_sources, choices, consumer):
    """Bind existing source/projection owners, without inventing a stored record."""
    from collections.abc import Mapping
    from .cif_acquisition_sources import read_acquisition_sources
    from .cif_acquisition_preparation import _capture
    from .cif_dictionary_sites import read_dictionary_sites, CONSTRUCTION_POLICY_ID, _need, _read
    from .cif_dictionary_store import _bytes
    from .cif_repair_attempt import _root
    if frozen_sources is None and choices is None:
        return None
    _need(frozen_sources is not None and isinstance(choices, Mapping) and bool(choices),
          'Explicit construction requires frozen sources and nonempty projection/parent choices')
    root = _root(frozen_sources); selected = read_acquisition_sources(root)
    _need(set(choices) <= selected['sources'].keys(), 'Construction choice lacks its frozen chemical source')
    captured = _capture(root); projected = {}
    for code, choice in choices.items():
        _need(isinstance(choice, (tuple, list)) and len(choice) == 2
              and isinstance(choice[1], str), 'Construction choice requires (projection directory, canonical parent)')
        directory = _root(choice[0]); saved = read_dictionary_sites(directory); report = saved['report']
        _need(report['policy_id'] == CONSTRUCTION_POLICY_ID and report['component'] == code,
              'Require the selected component canonical-input projection')
        original = saved['snapshot']; source = selected['sources'][code]
        _need(_read(original['source']) == _read(source['source'])
              and original['manifest']['request']['source_authority'] == source['source_authority'],
              'Construction projection differs from frozen source/authority')
        _need(_bytes(report['consumer']) == _bytes(consumer), 'Construction projection has a different selected consumer')
        projected[code] = dict(parent=choice[1], directory=directory, report=report, captured=_capture(directory))
    _need(read_acquisition_sources(root)['report'] == selected['report'], 'Frozen source selection changed during intake')
    return dict(selection=selected, captured=captured, choices=projected)


def _stage_construction_inputs(inputs, run):
    """Copy only already validated source/projection closures into existing roles."""
    from .cif_acquisition_preparation import _freeze
    from .cif_acquisition_sources import read_acquisition_sources
    from .cif_dictionary_sites import read_dictionary_sites, _need, _read
    from .cif_dictionary_store import _bytes
    root = run/'PostMR'; source_root = root/'DictionaryEngine/sources'
    _freeze(source_root, *inputs['captured'])
    selected = read_acquisition_sources(source_root)
    _need(_bytes(selected['report']) == _bytes(inputs['selection']['report']), 'Staged source selection differs')
    projections = {}; dictionaries = {}; sites = {}
    for code, choice in inputs['choices'].items():
        destination = root/'Coot/construction_projections'/code
        _freeze(destination, *choice['captured'])
        saved = read_dictionary_sites(destination)
        _need(_bytes(saved['report']) == _bytes(choice['report']), 'Staged construction projection differs')
        projections[code] = destination
        dictionaries[code] = saved['snapshot']['dictionary']
        for site, (path, component) in saved['projections'].items():
            _need(site not in sites and component == code, 'Overlapping construction projection sites')
            sites[site] = path
    names = {site: f'{i:03d}.cif' for i,site in enumerate(sorted(sites))}
    site_root = root/'Coot/site_dictionaries'
    _freeze(site_root, {names[site]: _read(path) for site,path in sites.items()}, [])
    copies = {site: site_root/name for site,name in names.items()}
    return dict(sources=selected['sources'], dictionaries=dictionaries,
                construction_projections=projections, site_dictionary_paths=copies)


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
        continuation_options=None, automatic_plane_support=False, bond_targets=None, automatic_bond_targets=False,
        frozen_sources=None, construction_choices=None, furanose_substitution=None,
        locked_sugar_site=None, store_root=None, registered_preparation=None,
        **execution_limits) -> PreparedPostMRRequest:
    """Prepare ordinary inputs once and publish a fresh complete request.

    Configuration/chemical permissions remain explicit. Existing constructors,
    source authority, literal compiler and request context gates own their rules.
    The site-only construction can acquire its isolated dictionary before Coot.
    The whole-model request is frozen here and executed by its caller. Failure retains all partial outputs;
    an existing PostMR directory cannot be prepared again in place. The explicit
    automatic_plane_support choice is frozen by the complete owner; continuation
    reads that saved choice rather than accepting a new override. Optional explicit
    bond_targets follows the same owner. Alternatively automatic_bond_targets asks
    that owner to freeze source/library-discovered choices in each fresh attempt.
    Optional frozen_sources plus construction_choices={code: (projection, parent)}
    reuse exact existing canonical-input projections before Coot. Source, consumer,
    model/actions and phosphate intent must agree; no catalogue/pairing role is
    fabricated. Original source composition and each numerical choice are retained
    in the existing run/request owners. This route still does not execute the
    complete request or enable automatic mutation/selection. An explicit
    furanose_substitution binds one internal site to its qualified component,
    host dictionary and NARestraints workbook before the restraint builder runs.
    Alternatively, locked_sugar_site reads that site's target from the frozen
    run. After PostMR has reserved its directory, its usual isolated acquisition
    owner reuses or qualifies the original component before Coot runs.
    Optional registered_preparation supplies the four explicit registered graph
    inputs. They are validated before tool configuration and must remain unchanged
    through construction and request freezing. This preserves image-link roles;
    it does not authorize execution of the resulting registered request.
    """
    from .postmr import _prepare_postmr
    bond_discovery_fields(automatic_bond_targets,bond_targets)
    bond_targets = _bond_target_declarations(bond_targets)
    if type(automatic_plane_support) is not bool:
        raise ValueError('automatic_plane_support must be a boolean')
    if generation_options is not None and not isinstance(generation_options,dict):
        raise ValueError('Require explicit generation options')
    options = dict(generation_options or {})
    if locked_sugar_site is not None and (furanose_substitution is not None or frozen_sources is not None
                                         or construction_choices is not None):
        raise ValueError('Select either an ordinary locked-sugar site or explicit construction sources')
    select_representation = options.pop("select_source_representation", False)
    if type(select_representation) is not bool or (select_representation and "bond_representation_policy" in options):
        raise ValueError("Require one unambiguous source representation selection")
    allowed = {'single_block_steps','timeout_seconds','max_attempts','bond_representation_policy','source_input_policy','multiple_planes'}
    if set(options)-allowed:
        raise ValueError('Unsupported ordinary generation option')
    registered = None if registered_preparation is None else _capture_registered_sources(registered_preparation)
    configured = configure_dictionary_engine(phenix,expected_dialect=expected_dialect,**options)
    construction = (None if frozen_sources is None and construction_choices is None else
                    _read_construction_inputs(frozen_sources, construction_choices, configured.consumer))
    furanose = None
    if locked_sugar_site is not None:
        from .cif_dictionary_store import default_dictionary_store
        from .postmr_furanose import plan_catalogue_substitution
        store = default_dictionary_store() if store_root is None else store_root
        furanose = plan_catalogue_substitution(run_directory,locked_sugar_site,configured,phenix,store,data_root,
                                               execution_limits)
    if furanose_substitution is not None:
        from .postmr_furanose import capture_substitution
        furanose = capture_substitution(furanose_substitution, configured.consumer)
        if construction is None:
            from .curated_ligands import ligand_source
            current = ligand_source(furanose.code, data_root, ready_set_executable=configured.ready_set_executable)
            furanose.verify_source(current.path, current.authority)
        else:
            chosen = construction['selection']['sources'].get(furanose.code)
            if chosen is None:
                raise ValueError('Furanose target is absent from the frozen acquisition sources')
            furanose.verify_source(chosen['source'], chosen['source_authority'])
    def initialize(inputs):
        if registered is not None:
            registered[1]()
        root = inputs.run_directory/'PostMR'/'DictionaryEngine'
        sources, literal, request = [root/name for name in ('sources','literal','request')]
        if construction is None:
            if root.exists() or root.is_symlink():raise FileExistsError(root)
            freeze_acquisition_sources(list(inputs.components),sources,data_root=data_root,
                ready_set_executable=configured.ready_set_executable)
        else:
            from .cif_dictionary_sites import _need
            _need(not root.is_symlink() and {p.name for p in root.iterdir()} == {'sources'},
                  'Unexpected preconstruction source owner members')
        if construction is not None or select_representation or furanose is not None:
            selected = read_acquisition_sources(sources)
        if construction is not None:
            from .cif_dictionary_store import _bytes
            _need(selected['report']['components'] == sorted(inputs.components)
                  and _bytes(selected['report']) == _bytes(construction['selection']['report']),
                  'Prepared components differ from the captured source selection')
        literal_inputs = None
        if inputs.supplementary_phils and inputs.explicit_na_policy is None:
            prepare_postmr_literal_inputs(inputs.model_path,list(inputs.supplementary_phils),sources,literal,
                data_root=data_root,ready_set_executable=configured.ready_set_executable)
            literal_inputs = literal
        generation = {code:dict(configured.generation) for code in inputs.components}
        if select_representation:
            from .cif_generation_input import source_selected_generation
            frozen = selected["sources"]
            generation = {code:source_selected_generation(frozen[code]["source"], code, settings)
                          for code, settings in generation.items()}
        if locked_sugar_site is not None:
            generation[furanose.code] = dict(furanose.generation)
        elif furanose is not None and 'bond_representation_policy' not in generation[furanose.code]:
            from .cif_generation_input import source_selected_generation
            generation[furanose.code] = source_selected_generation(
                selected['sources'][furanose.code]['source'], furanose.code, generation[furanose.code])
        components = [dict(code=code,generation=generation[code]) for code in inputs.components]
        if construction is not None:
            from .cif_dictionary_sites import read_dictionary_sites
            for item in components:
                code = item['code']
                if code in construction['choices']:
                    projected = inputs.run_directory/'PostMR/Coot/construction_projections'/code
                    saved = read_dictionary_sites(projected)
                    item['retained_snapshot'] = projected/'snapshot'
                    if saved['report']['terminal_resource'] is not None:
                        item['terminal_resource'] = projected/saved['report']['terminal_resource']
        if furanose is not None:
            from .postmr_furanose import DIRECTORY, read_substitution
            stage = inputs.run_directory/DIRECTORY
            built = read_substitution(stage)
            source = selected['sources'][furanose.code]
            furanose.verify_source(source['source'], source['source_authority'])
            if built['snapshot']['entry_id'] != inputs.furanose_entry_id:
                raise ValueError('Furanose construction retained a different dictionary entry')
            item, = [c for c in components if c['code'] == furanose.code]
            item.update(retained_snapshot=stage/'snapshot',
                        furanose_reaction=dict(workbook=built['workbook'], contexts=[built['context']]))
        record = initialize_postmr_dictionary_request(inputs.model_path,inputs.run_report,components,None,request,
            consumer=configured.consumer,ready_set_executable=None,supplementary_phils=list(inputs.supplementary_phils),
            literal_na_inputs=literal_inputs,frozen_sources=sources,construction_inputs=inputs.run_directory,
            **({'explicit_na_policy': inputs.explicit_na_policy} if inputs.explicit_na_policy is not None else {}),
            **({"select_anionic_phosphate":True} if select_representation else {}),
            continuation_options=continuation_options,
            **({'automatic_plane_support':True} if automatic_plane_support else {}),
            **({'bond_targets':bond_targets} if bond_targets is not None else {}),
            **({'registered_preparation':registered[0]} if registered is not None else {}),
            **({'automatic_bond_targets':True} if automatic_bond_targets else {}),**execution_limits)
        if registered is not None:
            registered[1]()
        return PreparedPostMRRequest(inputs.run_directory,request,record,generation)
    result = _prepare_postmr(run_directory,configured.ready_set_executable,phenix_installation=phenix,
        coot_executable=coot_executable,environment=phenix.environment,data_root=data_root,
        allow_mr_review=allow_mr_review,modified_pairs_only=modified_pairs_only,restraint_scope=restraint_scope,
        allow_unreviewed_backbone=allow_unreviewed_backbone,narestraints_builder=narestraints_builder,
        modified_pair_builder=modified_pair_builder,_dictionary_handler=initialize,
        **({'_furanose_input':furanose} if furanose is not None else {}),
        **({"_construction_inputs":construction} if construction is not None else {}))
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


def _plane_support_limitations(report, execution=None):
    """Describe already replayed generation outcomes, never infer final adoption."""
    if 'plane_generation' not in report:
        return ('This preparation has no recorded automatic plane-generation outcome; these notes do not establish complete plane coverage.',)
    notes = ['Plane-support generation does not establish final plane adoption in the selected restraints; repair and ReadySet qualification still govern selection.']
    unfilled = {row['component'] for row in (execution or {}).get('plane_results', [])
                if row['status'] == 'NO_SUPPORTED_PLANE_COMPLETION'}
    for code,row in sorted(report['plane_generation']['components'].items()):
        status = row['status']; centres = ', '.join(row['missing_centres'])
        if status == 'NO_GENERATION_NEEDED':
            notes.append(f'{code}: no missing planes were found within the supported source-graph screen; other chemistry is not assessed by that screen.')
        elif status == 'OWNED_SUPPORT_READY' and code in unfilled:
            notes.append(f'{code}: existing plane membership was retained at {centres}; the available evidence did not support a plane addition.')
        elif status == 'OWNED_SUPPORT_READY':
            notes.append(f'{code}: generated source-checked support for review of screened centres {centres}.')
        elif status == 'KNOWN_GENERATION_FAILURE':
            reason = {'TIMED_OUT':'timed out','REJECTED_CANDIDATE':'was chemically rejected',
                      'FINAL_BOND_ORDERS_REJECTED':'ended with bond orders outside the declared chemistry'}.get(row['proof']['failure_kind'],'failed')
            notes.append(f'{code}: optional plane generation {reason}; generated output was not used. Initially missing screened centres: {centres}.')
        else:
            raise ValueError('Unsupported checked plane-generation outcome')
    return tuple(notes)


def _selected_plane_limitations(exact):
    """Project selected-CIF coverage from the existing verified request read."""
    from .cif_dictionary_sites import _need
    from .cif_plane_coverage import audit_selected_trigonal_planes
    generated = exact['result'].get('plane_generation')
    runtime = exact['runtime']
    if generated is None or runtime is None:
        return ()
    prepared = exact.get('preparation')
    resources = runtime['manifest'].get('resources')
    if prepared is None or resources is None:
        return ('Selected dictionary plane coverage was not assessed: source-bound input references are unavailable in this reader result.',)
    plan = generated['components']
    _need(set(plan) == set(prepared['report']['selected_attempts']) and all(
        isinstance(c, str) and c.isascii() and c.isalnum() for c in plan),
        'Selected plane screen differs from prepared component ownership')
    refs = resources['dictionaries']
    _need(len(refs) == len(runtime['dictionaries']), 'Selected dictionary references differ')
    sources = {code:dict(path=Path(prepared['bundle_directory'])/'components'/code/'snapshot/entry/source.cif',
                        sha256=row['source_sha256']) for code,row in plan.items()}
    dictionaries = [dict(path=path,sha256=ref['sha256']) for path,ref in zip(runtime['dictionaries'],refs)]
    policies = {}
    for site in prepared.get('bundle', {}).get('preparations', []):
        binding = site.get('preparation_qualification')
        if binding is None:
            continue
        code = site['component']
        _need(code in plan and code not in policies and binding['component'] == code
              and binding['source_sha256'] == plan[code]['source_sha256']
              and binding['candidate_sha256'] == plan[code]['dictionary_sha256'],
              'Selected plane policy differs from the acquired source or numerical dictionary')
        policies[code] = binding['bond_representation_policy']
    report = audit_selected_trigonal_planes(sources, dictionaries, representation_policies=policies)
    notes = ['Selected dictionary coverage is scoped to explicit source-graph planes; native modifications, alternative restraints, achieved geometry and diffraction refinement are not assessed by this screen.']
    for code, row in report['components'].items():
        if row['status'] == 'UNASSESSED':
            notes.append(f"{code}: selected dictionary plane coverage is unassessed: {row['reason']}")
        elif row['missing_explicit_planes']:
            notes.append(f"{code}: selected dictionary lacks explicit planes at screened centres {', '.join(row['missing_explicit_planes'])}; alternative restraints may still contribute.")
        else:
            notes.append(f"{code}: selected dictionary has explicit planes for screened centres {', '.join(c['centre'] for c in row['centres'])}; this is scoped coverage, not refinement qualification.")
    return tuple(notes)


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
    return _ordinary_result_from_exact(request, attempt_number, exact)


def _read_ordinary_postmr_results(run_directory, attempt_numbers):
    """Project several named choices from one verified complete-history read."""
    from .cif_complete_request import read_dictionary_request_results
    request = _ordinary_request_directory(run_directory)
    return {number:_ordinary_result_from_exact(request, number, exact)
            for number,exact in read_dictionary_request_results(request, attempt_numbers).items()}


def _ordinary_result_from_exact(request, attempt_number, exact):
    from .cif_dictionary_sites import _need
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
            'These preparation checks do not establish diffraction-refinement success.',
            *_plane_support_limitations(exact['result'], exact.get('execution')),
            *_selected_plane_limitations(exact),
        ),
    )

    return result, exact


def read_ordinary_postmr_result(run_directory, *, attempt_number) -> CheckedPostMRResult:
    """Read an exact preparation through the existing evidence reader once."""
    return _read_ordinary_postmr_result(run_directory, attempt_number=attempt_number)[0]


def _execute_ordinary_postmr(run_directory, phenix, *, store_root=None, **preparation_options):
    """Construct once, execute one owned attempt, and return its run and attempt ID.

    This explicit route does not replace the default PostMR/campaign path yet.
    After interruption use continue_checked_postmr with the recorded attempt
    number; never call this constructor again on partial preparation.
    """
    from .cif_complete_request import execute_dictionary_request_attempt
    from .cif_dictionary_store import default_dictionary_store
    options = dict(preparation_options)
    options.setdefault('expected_dialect', 'CHEMICAL_COMPONENTS_CIF')
    options.setdefault('continuation_options', dict(readyset_timeout_seconds=120, restore_serialization=True))
    if options.get('locked_sugar_site') is not None:
        options['store_root'] = store_root
    prepared = initialize_ordinary_postmr_request(run_directory, phenix, **options)
    result = execute_dictionary_request_attempt(prepared.request_directory, phenix,
        default_dictionary_store() if store_root is None else store_root,
        generation=prepared.generation, after_attempt=0)
    return prepared.run_directory, result['attempt_number']


def prepare_checked_postmr(run_directory, phenix, *, store_root=None, **preparation_options) -> CheckedPostMRResult:
    """Construct/execute once and read the diagnostic result without adoption."""
    run, attempt = _execute_ordinary_postmr(run_directory, phenix,
        store_root=store_root, **preparation_options)
    return read_ordinary_postmr_result(run, attempt_number=attempt)


def _retire_new_preparation(request_directory, attempt_number):
    """Compact a newly published result before a campaign freezes its file list.

    Historical publication and inspection do not call this helper. The existing
    retention owner decides eligibility and preserves failed/uncertain work.
    Storage trouble is optional only while the original exact result still reads;
    damaged scientific evidence must not be hidden by a cleanup warning.
    """
    from .campaign_records import read_record
    from .campaigns import CampaignError
    from .cif_attempt_retention import ARTIFACT_POLICY, retire_attempt_working_files
    from .cif_complete_request import CAPTURE_ARTIFACT_POLICY, STAGED_ARTIFACT_POLICY, read_dictionary_request_result
    try:
        request = read_record(request_directory/'request.json')
        if request['configuration'].get('artifact_policy') not in {ARTIFACT_POLICY, CAPTURE_ARTIFACT_POLICY, STAGED_ARTIFACT_POLICY}:
            return None  # Other layouts retain their original storage contract.
        retire_attempt_working_files(request_directory, attempt_number)
    except (OSError, ValueError, CampaignError) as exc:
        exact = read_dictionary_request_result(request_directory, attempt_number)
        if exact['runtime'] is None:
            raise ValueError('Published preparation is no longer independently usable') from exc
        return ('Optional working-file cleanup did not complete; the exact checked '
                f'result remains readable and remaining evidence is preserved. {type(exc).__name__}: {exc}')
    return ('Successful preparation working copies were archived; public models '
            'and restraints remain in place.')


def prepare_published_postmr(run_directory, phenix, **preparation_options):
    """Use the same owner, then publish its exact result as an ordinary review root.

    Publication performs the complete proof read once. Do not first call the
    diagnostic reader and repeat its expensive replay just to obtain an attempt ID.
    New successful working evidence is retired before returning to campaign capture;
    optional storage errors retain a usable result only after an exact reread.
    An optional native failure may retain a qualified result; absence of one never
    triggers a second, unchecked preparation route.
    """
    from .cif_postmr_publication import publish_checked_preparation_with_notes
    from .checkpoints import _required_file, _ref_path
    from .postmr import PostMRResult
    run, attempt = _execute_ordinary_postmr(run_directory, phenix, **preparation_options)
    record, notes = publish_checked_preparation_with_notes(run, attempt_number=attempt)
    storage_note = _retire_new_preparation(_ordinary_request_directory(run), attempt)
    if storage_note is not None:
        notes = (*notes, storage_note)
    return PostMRResult(status=record['status'], message=record['message'],
        run_directory=run, postmr_directory=run/'PostMR', report_path=run/'PostMR/report.json',
        model_path=_required_file(record['prepared_model'], 'published model', run),
        readyset_log=None, readyset_status=record['readyset']['status'], preparation_notes=notes,
        restraint_paths=tuple(_ref_path(ref, 'published restraint', run) for ref in record['refinement_restraints']))


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
        if 'source_input_policy' in recipe:
            options['source_input_policy']=recipe['source_input_policy']
        key = json.dumps(options, sort_keys=True, allow_nan=False)
        if key not in configured:
            configured[key] = configure_dictionary_engine(phenix, **options)
        generation[code] = dict(configured[key].generation)
    result = execute_dictionary_request_attempt(root, phenix,
        default_dictionary_store() if store_root is None else store_root,
        generation=generation, after_attempt=after_attempt)
    return read_ordinary_postmr_result(run_directory, attempt_number=result['attempt_number'])
