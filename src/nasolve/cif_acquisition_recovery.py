"""Source-bound evidence for a fresh eLBOW acquisition after an unlisted bond."""
from hashlib import sha256
import math

from .campaign_records import path_in, read_record
from .cif_connected_atom_order import _ordered_values, unlisted_builder_bond
from .cif_dictionary_store import _bytes, _hash, _json, _regular
from .cif_generation_input import CONNECTED_INPUT_POLICY, POLICY_ID as SOURCE_INPUT_POLICY, generation_source
from .cif_source_representation import read_representation_candidate
from .cif_stereochemistry_audit import _graph, _values

POLICY_ID = 'cif-unlisted-builder-bond-recovery-v1'
EVIDENCE = 'connected_order_failure.json'


def _fingerprint(record):
    return sha256(_bytes(record)).hexdigest()


def select_failure(selection, generation, root, store):
    from .cif_repair_attempt import _root

    if not isinstance(selection, (tuple, list)) or len(selection) != 2:
        raise ValueError('Require a previous acquisition directory and exact attempt number')
    prior = _root(selection[0])
    number = selection[1]
    if any(prior.is_relative_to(p) or p.is_relative_to(prior) for p in (root, store)):
        raise ValueError('Previous acquisition overlaps recovery outputs or store')
    if generation.get('source_input_policy') != SOURCE_INPUT_POLICY:
        raise ValueError('Connected-order recovery requires the original ordinary source-reader recipe')
    proof = read_connected_order_failure(prior, number)
    if proof is None or proof['attempt'] != number:
        raise ValueError('Selected acquisition did not record an eligible unlisted native bond')
    return prior, number, proof


def validate_connected_order_failure(proof, source, request, consumer):
    """Verify the recovery's source, recipe and compact historical references."""
    pins = {'acquisition_request', 'acquisition_attempt', 'acquisition_completion',
            'generation_attempt', 'generation_completion', 'generation_receipt'}
    if (not isinstance(proof, dict) or set(proof) !=
            {'policy_id', 'component', 'previous_dictionary_request', 'consumer', 'attempt', 'records', 'bond'}
            or proof['policy_id'] != POLICY_ID or proof['component'] != request['component']
            or request['recipe'].get('source_input_policy') != CONNECTED_INPUT_POLICY
            or not request['recipe'].get('bond_representation_policy') or request['recipe'].get('multiple_planes')
            or type(proof['attempt']) is not int or not 1 <= proof['attempt'] <= 5
            or not isinstance(proof['records'], dict) or set(proof['records']) != pins
            or not all(_hash(digest) for digest in proof['records'].values())):
        raise ValueError('Invalid connected-order recovery evidence')
    previous = dict(request, recipe=dict(request['recipe'], source_input_policy=SOURCE_INPUT_POLICY))
    if (proof['previous_dictionary_request'] != _fingerprint(previous)
            or proof['consumer'] != _fingerprint(consumer)
            or sha256(_regular(source)).hexdigest() != request['source_sha256']):
        raise ValueError('Connected-order recovery differs from the original source, authority, recipe or consumer')
    values = _values(source, request['component'])
    _, before, after = _ordered_values(values, request['component'])
    if before == after:
        raise ValueError('Connected-order recovery would repeat the same atom order')
    elements, bonds, _, _ = _graph(values)
    bond = proof['bond']
    if not isinstance(bond, dict) or set(bond) != {'atoms', 'native_length_angstrom', 'source_bonds_matched'}:
        raise ValueError('Invalid recorded extra bond')
    pair = bond['atoms']
    if (not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(n, str) for n in pair)
            or pair[0] >= pair[1] or tuple(pair) in bonds
            or any(elements.get(n) in {None, 'H', 'D', 'T'} for n in pair)
            or type(bond['source_bonds_matched']) is not int or bond['source_bonds_matched'] != len(bonds)
            or type(bond['native_length_angstrom']) not in (float, int)
            or not math.isfinite(bond['native_length_angstrom']) or bond['native_length_angstrom'] <= 0):
        raise ValueError('Recorded extra bond is inconsistent with the original source')


def read_connected_order_failure(directory, attempt_number):
    """Return the verified reason for reordering, or None for an unrelated completed outcome."""
    from .cif_acquisition_attempt import inspect_acquisition_request
    from .cif_repair_attempt import _root

    root = _root(directory)
    state = inspect_acquisition_request(root)
    if (state['state'] != 'RECORDED' or state['availability'] == 'BLOCKED'
            or type(attempt_number) is not int or not 1 <= attempt_number <= len(state['attempts'])):
        raise ValueError('Require an exact stopped acquisition and known process ownership')
    row = state['attempts'][attempt_number - 1]
    if row['state'] != 'STOPPED':
        raise ValueError('Selected acquisition has no sealed completion')
    config = state['request']['configuration']
    request = config['dictionary_request']
    gen = row['children']['generation']
    if (row['finished']['outcome'] != 'RAISED' or gen['state'] != 'STOPPED'
            or gen['finished']['outcome'] != 'RETURNED' or row['children']['qualification']['state'] != 'NOT_CREATED'
            or request['recipe'].get('source_input_policy') != SOURCE_INPUT_POLICY
            or not request['recipe'].get('bond_representation_policy') or request['recipe'].get('multiple_planes')):
        return None
    work = path_in(root, f"generation/attempts/attempt-{gen['number']:04d}/generation")
    reference = gen['finished']['candidate_receipt']
    if reference is None:
        return None
    header = _json(_regular(work/'source_candidate_receipt.json'))
    if (header.get('status') != 'FAILED' or header.get('candidate_retained') is not False
            or (header.get('diagnostic') or {}).get('blocking_stage') != 'NATIVE_BUILDER'):
        return None
    report = read_representation_candidate(work)
    generation = read_record(root/'generation/request.json')['configuration']
    filename, native, _ = generation_source(generation)
    if (report['source_sha256'] != native['sha256']
            or _regular(work/'source.cif') != _regular(path_in(root/'generation/inputs', filename))
            or report['component'] != request['component']
            or report['bond_representation_policy'] != request['recipe']['bond_representation_policy']):
        raise ValueError('Failed native input differs from its acquisition')
    if (report['execution']['status'] != 'COMPLETED' or report['execution']['returncode'] != 0
            or report['representation_validation']['status'] != 'SOURCE_REPRESENTATION_PASS'):
        return None
    source = path_in(root, 'inputs/source.cif')
    bond = unlisted_builder_bond(_values(source, request['component']), request['component'],
                                report['diagnostic'], _regular(work/'candidate_worker.log').decode(errors='replace'))
    if bond is None:
        return None
    after = inspect_acquisition_request(root)
    if (after['request'] != state['request'] or after['attempts'][attempt_number-1] != row
            or after['availability'] == 'BLOCKED'):
        raise ValueError('Acquisition changed during connected-order review')
    proof = dict(policy_id=POLICY_ID, component=request['component'], attempt=attempt_number,
        previous_dictionary_request=_fingerprint(request), consumer=_fingerprint(config['consumer']), bond=bond,
        records=dict(acquisition_request=state['request']['record_sha256'],
            acquisition_attempt=row['intent']['record_sha256'], acquisition_completion=row['finished']['record_sha256'],
            generation_attempt=gen['intent']['record_sha256'], generation_completion=gen['finished']['record_sha256'],
            generation_receipt=reference['sha256']))
    recovered = dict(request, recipe=dict(request['recipe'], source_input_policy=CONNECTED_INPUT_POLICY))
    validate_connected_order_failure(proof, source, recovered, config['consumer'])
    return proof
