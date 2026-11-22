"""Read-only explanations for one explicit audited-session reservation.

Saved receipts describe evidence, not current process liveness. This diagnostic
never probes historical PIDs, manufactures stop records, retries or settles.
The existing settlement API remains the only release authority.
"""
import argparse
import json
import stat

from .. import campaign_records as records
from ..campaign_process import exclusive_lock
from ..campaigns import CampaignError
from . import storage_budget as budget
from .recipe import RecipeError, checksum

MAX_RECEIPT_BYTES = 1024 * 1024
_ERRORS = (OSError, ValueError, KeyError, TypeError, CampaignError)


def diagnose_session_reservation(directory, *, budget_id, reservation_id, failure_id=None):
    """Explain a pinned grant without changing files or its held allowance.

    A separate failure pin is needed to report a ready failed-settlement path.
    Even that result is only a point-in-time observation: settlement must repeat
    its ordinary proof. Missing/ambiguous evidence stays held. A published review
    is directed to the existing successful-review path, not validated here.
    """
    root = budget._root(directory)
    checksum(reservation_id, 'session reservation identity')
    if failure_id is not None:
        checksum(failure_id, 'independent failure identity')
    lock = records.path_in(root, budget.LOCK)
    budget._need(lock.is_file() and stat.S_ISREG(lock.stat().st_mode),
                 'Existing budget lock required for a read-only diagnosis')
    with exclusive_lock(lock):
        _, ledger = budget._read(root, budget_id)
        item = ledger['reservations'].get(reservation_id)
        budget._need(item is not None and item['grant'].get('scope_type') == 'audited_session',
                     'Require an exact audited-session reservation')
        grant = item['grant']
        session = budget._grant_path(root, grant)
        prefix = grant['session']
        result = dict(kind='metal-session-reservation-diagnosis', schema_version=1,
            budget_id=budget_id, reservation_id=reservation_id,
            ledger_sha256=ledger['record_sha256'], request_id=grant['request_id'],
            session=dict(anchor='store', relative_path=prefix),
            status='HELD_BLOCKED', outstanding_allowance_bytes=grant['allowance_bytes'],
            observed_failure_id=None, failure_pin_matched=False, failure_stage=None,
            blockers=[], observed_receipts={}, new_native_calls=0, process_queries=0,
            verification_scope='POINT_IN_TIME_DIAGNOSIS_ONLY', release_authorized=False,
            retry_authorized=False, retirement_authorized=False, scientific_acceptance='NOT_ASSESSED')
        if item['settlement'] is not None:
            result.update(status='ALREADY_SETTLED', outstanding_allowance_bytes=0,
                          recorded_settlement=item['settlement'])
            return result

        def block(code, relative, detail, *, phase=None):
            row = dict(code=code, reference=dict(anchor='store', relative_path=prefix+'/'+relative),
                       detail=detail, action='Preserve outputs and keep the allowance held; inspect the named evidence.')
            if phase is not None:
                row['phase'] = phase
            result['blockers'].append(row)

        def receipt(relative, *, phase=None):
            try:
                path = records.path_in(session, relative)
                value = budget._record(path, MAX_RECEIPT_BYTES)
                result['observed_receipts'][prefix+'/'+relative] = value['record_sha256']
                return value
            except FileNotFoundError:
                block('MISSING_RECEIPT', relative, 'The saved receipt is absent; absence does not establish a stopped process.', phase=phase)
            except _ERRORS:
                block('INVALID_RECEIPT', relative, 'The receipt is malformed, changed, nonregular or outside its byte bound.', phase=phase)
            return None

        def present(relative):
            # Refuse symbolic links, including dangling links, before inspecting.
            return records.path_in(session, relative).exists()

        def owner(relative, header_name, phases):
            receipt(relative+'/ownership/'+header_name)
            seal_path = relative+'/ownership/finished.json'
            seal = receipt(seal_path)
            phase_root = records.path_in(session, relative+'/ownership/phases')
            names = set()
            if phase_root.exists():
                budget._need(phase_root.is_dir(), 'Process phase inventory is not a directory')
                # Fixed known phase namespaces; refuse additional entries without opening them.
                for entry in phase_root.iterdir():
                    names.add(entry.name)
                    if len(names) > len(phases):
                        break
                if not names <= phases:
                    block('UNEXPECTED_PHASES', relative+'/ownership/phases', 'Phase inventory differs from the supported process scope.')
            if seal is not None:
                declared = seal.get('phases')
                if not isinstance(declared, dict) or not set(declared) <= phases:
                    block('INVALID_RECEIPT', seal_path, 'The outer completion receipt has an unsupported phase inventory.')
                else:
                    names |= set(declared)
            for phase in sorted(names & phases):
                base = relative+'/ownership/phases/'+phase
                receipt(base+'/job.json', phase=phase)
                stopped = receipt(base+'/finished.json', phase=phase)
                if present(base+'/process.json'):
                    receipt(base+'/process.json', phase=phase)
                elif stopped is None:
                    block('MISSING_PROCESS_IDENTITY', base+'/process.json',
                          'No saved process identity or completion proof is available for this phase.', phase=phase)

        if receipt('storage-admission.json') is not None:
            try:
                budget._session_admission(session, grant, reservation_id)
            except _ERRORS:
                block('BINDING_NOT_VERIFIED', 'storage-admission.json', 'The admission does not bind this exact reservation and grant.')
        declaration = receipt('request.json')
        if declaration is not None and declaration.get('storage_reservation') != dict(budget_id=budget_id, reservation_id=reservation_id):
            block('BINDING_NOT_VERIFIED', 'request.json', 'The session declaration does not bind this exact reservation.')
        failure = receipt('failure.json')
        if failure is not None:
            stage = failure.get('stage')
            if not isinstance(stage, str):
                block('INVALID_RECEIPT', 'failure.json', 'The failure has no valid stage label.')
                stage = None
            result.update(observed_failure_id=failure['record_sha256'], failure_stage=stage,
                          failure_pin_matched=failure_id == failure['record_sha256'])
            if failure_id is None:
                block('FAILURE_PIN_REQUIRED', 'failure.json', 'Supply the independently retained failure identity before checking the failed-settlement route.')
            elif failure_id != failure['record_sha256']:
                block('FAILURE_PIN_MISMATCH', 'failure.json', 'The supplied failure identity differs from the observed receipt.')
            if not isinstance(failure.get('process_stop_evidence'), dict):
                block('FAILURE_STOP_PROOF_ABSENT', 'failure.json', 'This failure did not capture a recoverable stop proof; later absence of a process does not replace it.')
        if present('review.json'):
            block('REVIEW_PRESENT', 'review.json', 'A review is present; use the successful-review inspection/settlement path if it validates. This diagnostic does not validate that review.')
        from .preflight_process import PHASES
        owner('preflight', 'preflight.json', PHASES)
        stage = result['failure_stage']
        if stage == 'FRESH_INPUT_INSPECTION':
            if present('attempt'):
                block('UNEXPECTED_MAIN_CHILD', 'attempt', 'A preflight-only failure cannot prove that no main child began when an attempt is present.')
        elif stage in {'OWNED_NATIVE_CHILD', 'SCIENTIFIC_AUDIT', 'REVIEW_PUBLICATION'} or present('attempt'):
            receipt('owned-preflight.json')
            receipt('preflight/inspection.json')
            owner('attempt', 'child.json', {'native-fdp'})
            receipt('attempt/outcome.json')

        if not result['blockers']:
            try:
                budget._failed_session_review(root, ledger, grant, reservation_id, failure_id)
            except _ERRORS as exc:
                # This is the unchanged authoritative reader, not a second stop policy.
                detail = str(exc) if isinstance(exc, (RecipeError, CampaignError)) else type(exc).__name__
                block('RELEASE_PROOF_NOT_VERIFIED', 'failure.json', 'Existing failed-settlement reader refused: '+detail[:500])
            else:
                result['status'] = 'HELD_READY_FOR_EXPLICIT_SETTLEMENT'
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Explain one held metal session; never release, retry or delete.')
    parser.add_argument('store')
    parser.add_argument('--budget-id', required=True)
    parser.add_argument('--reservation-id', required=True)
    parser.add_argument('--failure-id')
    args = parser.parse_args(argv)
    try:
        report = diagnose_session_reservation(args.store, budget_id=args.budget_id,
            reservation_id=args.reservation_id, failure_id=args.failure_id)
    except _ERRORS as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
