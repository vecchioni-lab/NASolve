"""Read selected owned generation as support for the narrow plane-only operation.

Saved native code is never executed; request/attempt records detect corruption,
not hostile forgery. Native inventory, mechanics and adoption remain separate.
"""
from hashlib import sha256
import json
from pathlib import Path

from .campaign_records import path_in
from .cif_dictionary_store import _regular
from .cif_generation_attempt import _root, _pins, inspect_source_generation_request
from .cif_generation_process import inspect_generation_process
from .cif_source_representation import read_multiple_plane_candidate, read_multiple_plane_execution_failure
from .cif_plane_candidate import prepare_trigonal_plane_candidate

POLICY_ID = "cif-owned-trigonal-plane-completion-v1"
SUPPORT_POLICY_ID = "cif-owned-multiple-plane-support-v1"


def _need(value, message):
    if not value:
        raise ValueError(message)


def read_owned_plane_support(source, code, request_directory, attempt_number):
    """Bind one explicit sealed attempt; never select latest or authorize retry."""
    return _read_owned_plane_generation(source,code,request_directory,attempt_number)


def inspect_owned_plane_generation_failure(source, code, request_directory, attempt_number):
    """Bind one known stopped negative native execution, never a usable candidate."""
    return _read_owned_plane_generation(source,code,request_directory,attempt_number,failure=True)


def _read_owned_plane_generation(source, code, request_directory, attempt_number, *, failure=False):
    _need(type(attempt_number) is int and attempt_number > 0, "Require an explicit positive attempt number")
    root = _root(request_directory)
    original = _regular(Path(source))
    state = inspect_source_generation_request(root)
    _need(state['state'] == 'RECORDED' and len(state['attempts']) >= attempt_number,
          "Selected generation attempt is not recorded")
    request = state['request']; config = request['configuration']
    selected = state['attempts'][attempt_number-1]
    _need(selected['state'] == 'STOPPED' and selected['finished']['outcome'] == 'RETURNED',
          "Selected generation attempt is not a sealed returned call")
    _need(config['component'] == code and _regular(path_in(root, 'inputs/source.cif')) == original,
          "Selected generation source/component differs")
    recipe, generator = config['recipe'], config['generator']
    _need(recipe.get('multiple_planes') is True, "Selected request lacks multiple-plane choice")
    name = f'attempts/attempt-{attempt_number:04d}/generation'
    work = path_in(root, name)
    report = (read_multiple_plane_execution_failure if failure else read_multiple_plane_candidate)(work)
    spec = json.loads(_regular(path_in(work, 'candidate_spec.json')))
    # C170 keeps the request ceiling frozen while a parent may grant less time.
    # The completed receipt and both owned phases must bind that same grant.
    effective_timeout = report['execution']['timeout_seconds']
    _need(_regular(path_in(work, 'source.cif')) == original and report['component'] == code
          and report['source_sha256'] == config['source']['sha256'], "Native generation source binding differs")
    _need(report.get('bond_representation_policy') == recipe.get('bond_representation_policy')
          and spec['declared_charge_control']['dialect'] == recipe['expected_dialect']
          and report['single_block_steps'] == recipe['single_block_steps']
          and 0 < effective_timeout <= recipe['timeout_seconds']
          and report['phenix_version'] == generator['phenix_version']
          and _pins(report['sources']) == generator['prior_sources'], "Native generation recipe/producer differs")
    owner = {k: selected['intent'][k] for k in ('attempt_id', 'request_sha256')}
    owner['attempt_sha256'] = selected['intent']['record_sha256']
    context = dict(component=code, source_sha256=config['source']['sha256'],
        candidate_policy_id=report['policy_id'], multiple_planes=True,
        phenix_version=generator['phenix_version'], single_block_steps=recipe['single_block_steps'],
        total_timeout_seconds=effective_timeout, attempt_owner=owner)
    historical = Path(spec['installation_root'])  # Compare strings only; never open SDK.
    commands = {
        'capabilities': [str(historical/generator['dispatchers']['elbow']['path']), '--help'],
        'candidate': [str(historical/generator['dispatchers']['python']['path']), '-B',
                      'candidate_worker.py', 'candidate_spec.json'],
    }
    _need(report['generator_capabilities']['command'] == commands['capabilities'],
          "Generation help dispatcher differs from request")
    for phase in ('capabilities', 'candidate'):
        evidence = inspect_generation_process(work, phase)
        _need(evidence['state'] == 'STOPPED', "Generation phase is not sealed")
        job, finished = evidence['job'], evidence['finished']
        completed = (finished['status'] == 'COMPLETED' and type(finished['returncode']) is int
                     and finished['returncode'] == 0)
        if failure and phase == 'candidate':
            completed = ('identity' in evidence and finished['status'] in {'FAILED','TIMED_OUT'}
                         and type(finished['returncode']) is int and finished['returncode'] != 0
                         and finished['status'] == report['execution']['status']
                         and finished['returncode'] == report['execution']['returncode'])
        _need(job['context'] == context and job['argv_provenance'] == commands[phase]
              and job['timeout_seconds'] <= effective_timeout and completed,
              "Generation phase command/recipe/completion differs")
    candidate = report['candidate']
    after = inspect_source_generation_request(root)
    _need(after['request'] == request and after['attempts'][attempt_number-1] == selected
          and _regular(Path(source)) == original, "Selected generation evidence changed during replay")
    if failure:
        return dict(schema_version=1,policy_id='cif-owned-plane-generation-failure-v1',
            status='KNOWN_STOPPED_GENERATION_FAILURE',component=code,source_sha256=report['source_sha256'],
            attempt_number=attempt_number,request_sha256=request['record_sha256'],
            attempt_sha256=selected['intent']['record_sha256'],finished_sha256=selected['finished']['record_sha256'],
            receipt={**selected['finished']['candidate_receipt'],'anchor':'request_directory',
                     'path':name+'/source_candidate_receipt.json'},
            failure_kind=report['execution']['status'],returncode=report['execution']['returncode'],
            recipe=recipe,generator=generator,stopped_verified=True,exact_inputs=True,
            partial_outputs='PRESERVED; NOT_QUALIFIED',candidate_qualification='NOT_ASSESSED',
            new_native_calls=0,fallback_authorized=False,retry_authorized=False)
    return dict(schema_version=1, policy_id=SUPPORT_POLICY_ID, status='OWNED_SUPPORT_REPLAY_PASS',
        component=code, source_sha256=report['source_sha256'], attempt_number=attempt_number,
        request_sha256=request['record_sha256'], attempt_sha256=selected['intent']['record_sha256'],
        finished_sha256=selected['finished']['record_sha256'],
        receipt={**selected['finished']['candidate_receipt'], 'anchor':'request_directory',
                 'path':name+'/source_candidate_receipt.json'},
        support={**candidate, 'anchor':'request_directory', 'path':name+'/candidate.cif'},
        recipe=recipe, generator=generator, stopping=report['stopping'],
        scope='COMPLETED_OWNED_GENERATION_SUPPORT; NOT_CONVERGENCE_OR_NATIVE_USABILITY',
        scientific_approval='NOT_RUN', automatic_adoption=False)


def prepare_owned_trigonal_plane_candidate(source, dictionary, code, request_directory,
                                          attempt_number, output):
    """Transfer only supported missing rows; retain failed/partial fresh outputs."""
    root = _root(request_directory)
    support = read_owned_plane_support(source, code, root, attempt_number)
    candidate = prepare_trigonal_plane_candidate(source, dictionary,
        path_in(root, support['support']['path']), code, output)
    _need(read_owned_plane_support(source, code, root, attempt_number) == support,
          "Selected plane support changed during candidate preparation")
    _need(candidate['corroborating_dictionary_sha256'] == support['support']['sha256']
          and candidate['source_sha256'] == support['source_sha256'], "Plane candidate support binding differs")
    return dict(schema_version=1, policy_id=POLICY_ID, status='CANDIDATE_REVIEW', component=code,
        plane_candidate=candidate, support_generation=support,
        candidate_sha256=sha256(_regular(Path(output))).hexdigest(),
        native_qualification='NOT_RUN', scientific_approval='NOT_RUN', automatic_adoption=False)
