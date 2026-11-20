"""Completed batch handoff for independently pinned historical fdp inspection.

Archive/source verification stays with its existing owners. The final receipt
shares parent identities, never opens them during selection, and grants no
execution, reuse, cleanup or scientific acceptance authority.
"""
from hashlib import sha256
from pathlib import Path

from .. import campaign_records as records
from ..cif_attempt_retention import _sync_archive
from . import compact
from .input_archive import pack_fdp_inputs, expanded_fdp_inputs, inspect_recorded_fdp, archive_owner
from .recipe import RecipeError, checksum, digest
from .storage import DEFAULT_MAX_BYTES

KIND = 'metal-fdp-review-publication'
MAX_PUBLICATION_BYTES = 1024 * 1024
_FALSE = ('execution_authorized', 'reuse_authorized', 'retirement_authorized')


def _selection(publication, publication_id, trial_id):
    checksum(publication_id, 'expected publication identity')
    checksum(trial_id, 'selected trial identity')
    try:
        fields = {'kind','schema_version','status','archive_sha256','projection_id',
                  'parents','attempts','source_replay','scientific_acceptance','record_sha256', *_FALSE}
        if not isinstance(publication, dict) or set(publication) != fields:
            raise RecipeError('Require an exact completed fdp publication receipt')
        body = dict(publication); recorded_id = body.pop('record_sha256')
        if (recorded_id != publication_id or sha256(records._canonical(body)).hexdigest() != publication_id
                or publication['kind'] != KIND or type(publication['schema_version']) is not int
                or publication['schema_version'] != 1 or publication['status'] != 'PUBLISHED_FDP_REVIEW'
                or publication['source_replay'] != 'FULL_FDP_REPLAY_BEFORE_INPUT_PACKING'
                or publication['scientific_acceptance'] != 'NOT_ASSESSED'
                or any(publication[k] is not False for k in _FALSE)):
            raise RecipeError('Changed, incomplete or unsupported fdp publication')
        if records.serialized_record_size(body) > MAX_PUBLICATION_BYTES:
            raise RecipeError('Publication exceeds metadata budget')
        checksum(publication['archive_sha256'], 'published archive identity')
        checksum(publication['projection_id'], 'published projection identity')
        parents = publication['parents']; attempts = publication['attempts']
        if (not isinstance(parents, dict) or not isinstance(attempts, list)
                or not 1 <= len(attempts) <= compact.MAX_TRIALS
                or set(parents) != {a['parent_id'] for a in attempts}
                or len({a['trial_id'] for a in attempts}) != len(attempts)):
            raise RecipeError('Require distinct attempts and their exact referenced parents')
        for key, parent in parents.items():
            if (digest(parent) != key or set(parent) not in ({'geometry_id','manifest'}, {'xyz_trial_id','manifest'})
                    or parent['manifest']['anchor'] != 'run'):
                raise RecipeError('Changed published parent identity')
            identity_key = 'geometry_id' if 'geometry_id' in parent else 'xyz_trial_id'
            checksum(parent[identity_key], 'published parent identity')
            compact._portable_references(parent)
        selected = None
        for attempt in attempts:
            if set(attempt) != {'trial_id','record_id','parent_id'}:
                raise RecipeError('Unsupported published attempt fields')
            checksum(attempt['trial_id'], 'published trial identity')
            checksum(attempt['record_id'], 'published result record identity')
            if attempt['trial_id'] == trial_id: selected = attempt
        if selected is None:
            raise RecipeError('Requested attempt is absent from publication')
        return selected, parents[selected['parent_id']]
    except (KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise RecipeError('Invalid fdp publication metadata: ' + str(exc)) from exc


def _write_publication(path, value):
    # Reuse the durable create-only campaign writer: sync a temporary record,
    # then publish its final name without overwriting an existing file.
    try:
        return records.write_record(path, value)
    except records.CampaignError as exc:
        raise RecipeError('Cannot publish fdp review receipt: ' + str(exc)) from exc


def publish_fdp_inputs(run, trials, archive, output, *, max_trial_bytes=DEFAULT_MAX_BYTES,
                       max_input_bytes=archive_owner.MAX_BYTES):
    """Publish a completed explicit batch's archive, then its selection receipt.

    Existing full source audits still run during packing. Index construction
    reads the newly packed, checksum-pinned archive and adds no source-parent
    replay. This is not automatic per-point packing or crash-safe retirement.
    """
    run = Path(run).expanduser().resolve()
    archive, output = (Path(p).expanduser().absolute() for p in (archive, output))
    if (archive.resolve() == output.resolve() or any(
            p.exists() or p.is_symlink() or not p.parent.is_dir()
            or p.resolve().is_relative_to(run) or any(a.is_symlink() for a in p.parents)
            for p in (archive, output))):
        raise RecipeError('Require distinct fresh publication files outside the source run')
    packed = pack_fdp_inputs(run, trials, archive,
        max_trial_bytes=max_trial_bytes, max_input_bytes=max_input_bytes)
    # Reuse only the shared fsync primitive, not the CIF-attempt schema or its
    # retirement policy. Archive bytes become durable before the receipt.
    _sync_archive(archive)
    parents, attempts = {}, []
    with expanded_fdp_inputs(archive, packed['archive_sha256'],
            projection_id=packed['projection_id'], max_input_bytes=max_input_bytes) as (_, projection):
        for row in projection['records']:
            parent = projection['bases'][row['basis_id']]['parent']
            parent_id = digest(parent); parents[parent_id] = parent
            attempts.append(dict(trial_id=row['trial_id'], record_id=row['record_id'], parent_id=parent_id))
    publication = dict(kind=KIND, schema_version=1, status='PUBLISHED_FDP_REVIEW',
        archive_sha256=packed['archive_sha256'], projection_id=packed['projection_id'],
        parents=parents, attempts=attempts, source_replay=packed['source_replay'],
        scientific_acceptance='NOT_ASSESSED', **{key: False for key in _FALSE})
    prospective = dict(publication, record_sha256=sha256(records._canonical(publication)).hexdigest())
    _selection(prospective, prospective['record_sha256'], attempts[0]['trial_id'])
    published = _write_publication(output, publication)
    if published != prospective or compact.read_projection(output, max_projection_bytes=MAX_PUBLICATION_BYTES) != prospective:
        raise RecipeError('Publication changed during completion readback')
    return published


def inspect_published_fdp(archive, publication, *, publication_id, trial_id,
                          max_input_bytes=archive_owner.MAX_BYTES):
    """Read one attempt using an independently retained publication identity."""
    selected, parent = _selection(publication, publication_id, trial_id)
    result = inspect_recorded_fdp(archive, publication['archive_sha256'],
        projection_id=publication['projection_id'], trial_id=trial_id,
        expected_parent=parent, max_input_bytes=max_input_bytes)
    if result['record']['record_id'] != selected['record_id']:
        raise RecipeError('Published attempt belongs to a different recorded result')
    return result
