"""Bounded exact input transport for already audited frozen anomalous trials.

Use the shared archive/temporary-view owner. This retains compact result records
and executable input bytes, not complete parents or a new execution/retirement
contract. Captured plans and programs are data and are never executed here.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .. import cif_runtime_evidence as archive_owner
from . import compact
from .materialize import _json, _source
from .recipe import RecipeError, checksum, digest
from .storage import _integer, DEFAULT_MAX_BYTES

KIND = 'metal-fdp-input-archive'


def _budget(value):
    _integer(value, 'max_input_bytes', 1)
    if value > archive_owner.MAX_BYTES:
        raise RecipeError('Input archive cannot enlarge the shared expansion budget')


def _members(projection, max_input_bytes):
    """Transport consistency only; this is not a replacement freeze audit."""
    _budget(max_input_bytes)
    try:
        check=dict(projection)
        identifier=check.pop('projection_id')
        if (digest(check)!=identifier or projection['kind']!=compact.KIND
                or type(projection['schema_version']) is not int or projection['schema_version']!=1
                or projection['status']!='PROJECTION_REVIEW'
                or projection['scientific_acceptance']!='NOT_ASSESSED'
                or any(projection[k] is not False for k in (
                    'standalone_evidence','reuse_authorized','retirement_authorized',
                    'materialization_supported','automatic_checkpoint_selection'))):
            raise RecipeError('Require an unchanged review-only compact projection')
        compact._portable_references(projection)
        requests=projection['requests'];records=projection['records']
        if (not isinstance(requests,dict) or not 1<=len(requests)<=compact.MAX_TRIALS
                or not isinstance(records,list) or not 1<=len(records)<=compact.MAX_TRIALS
                or {row['input_id'] for row in records}!=set(requests)
                or len({row['trial_id'] for row in records})!=len(records)):
            raise RecipeError('Input archive requires every distinct attempt and referenced request')
        raw=compact.encode(projection)
        if len(raw)>compact.MAX_PROJECTION_BYTES:
            raise RecipeError('Projection exceeds input archive metadata budget')
        members={'projection.json':dict(sha256=sha256(raw).hexdigest(),size=len(raw))}
        for request_id,request in requests.items():
            checksum(request_id,'input request identity')
            if digest(request)!=request_id:
                raise RecipeError('Input request identity changed')
            files=request['input_files']
            if not isinstance(files,dict) or not {'plan.json','native-plan.json'}<=files.keys():
                raise RecipeError('Input archive requires complete recorded input plans')
            for name,ref in files.items():
                if (not isinstance(name,str) or not name or name in {'.','..'}
                        or Path(name).name!=name or '\\' in name
                        or not isinstance(ref,dict) or set(ref)!={'sha256','size'}):
                    raise RecipeError('Require explicit input names and exact content references')
                members[f'requests/{request_id}/{name}']=dict(ref)
        directories=sorted({str(parent) for name in members for parent in Path(name).parents if str(parent)!='.'})
        archive_owner._file_index(members,directories,max_files=archive_owner.MAX_FILES)
        if sum(ref['size'] for ref in members.values())>max_input_bytes:
            raise RecipeError('Input archive exceeds logical input byte budget')
        return members
    except (KeyError,TypeError,ValueError,OverflowError,RecursionError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Invalid input archive metadata: '+str(exc)) from exc


def pack_fdp_inputs(run, trials, output, *, max_trial_bytes=DEFAULT_MAX_BYTES,
                    max_input_bytes=archive_owner.MAX_BYTES):
    """Archive exact inputs and all compact records after existing full replay.

    Output must be fresh and outside the immutable run. Input/file/archive caps
    retain the shared owner's bounds. As with compact projection, upstream parent
    replay is not resource-bounded by these trial/input limits. No source retires.
    """
    _budget(max_input_bytes)
    run=Path(run).expanduser().resolve();output=Path(output).expanduser().absolute()
    if (output.exists() or output.is_symlink() or output.resolve().is_relative_to(run)
            or any(p.is_symlink() for p in output.parents)):
        raise RecipeError('Require a fresh input archive outside the source run')
    projection=compact.project_trials(run,trials,max_bytes=max_trial_bytes)
    expected=_members(projection,max_input_bytes)
    with TemporaryDirectory(prefix='metal-fdp-inputs-') as temporary:
        stage=Path(temporary).resolve()/'inputs';stage.mkdir()
        (stage/'projection.json').write_bytes(compact.encode(projection))
        for request_id,request in projection['requests'].items():
            row=next(row for row in projection['records'] if row['input_id']==request_id)
            manifest=_json(_source(row['source_manifest'],run))
            folder=stage/'requests'/request_id;folder.mkdir(parents=True)
            for name,ref in request['input_files'].items():
                raw=_source(manifest['files'][name],run)
                if len(raw)!=ref['size'] or sha256(raw).hexdigest()!=ref['sha256']:
                    raise RecipeError('Input bytes differ from the replayed request')
                (folder/name).write_bytes(raw)
        # Reuse scientific replay after materialization, before archive publication.
        compact.verify_projection(run,projection,max_bytes=max_trial_bytes)
        actual=archive_owner._tree(stage)
        if {name:dict(sha256=sha256(raw).hexdigest(),size=len(raw)) for name,raw in actual.items()}!=expected:
            raise RecipeError('Staged input inventory changed')
        packed=archive_owner.pack_runtime_evidence(stage,output)
    return dict(kind=KIND,schema_version=1,projection_id=projection['projection_id'],
        archive_sha256=packed['archive_sha256'],packing=packed,
        attempts=len(projection['records']),requests=len(projection['requests']),
        source_replay='FULL_FDP_REPLAY_BEFORE_INPUT_PACKING',
        complete_parent_evidence=False,software_environment_identity_complete=False,
        native_regeneration_tested=False,execution_authorized=False,
        retirement_authorized=False,scientific_acceptance='NOT_ASSESSED')


@contextmanager
def expanded_fdp_inputs(archive, archive_sha256, *, projection_id,
                        max_input_bytes=archive_owner.MAX_BYTES):
    """Yield (temporary input root, original projection), without source lookup.

    Both expected identities must come from the retained packing receipt. Exact
    transport is not independent scientific validation, cache eligibility or
    permission to execute a captured command. Paths expire on context exit.
    """
    _budget(max_input_bytes);checksum(projection_id,'expected projection identity')
    def decode(data,expected_sha256):
        index,objects,total=archive_owner._decode(data,expected_sha256)
        if total>max_input_bytes:
            raise RecipeError('Input archive exceeds logical input byte budget')
        ref=index['files'].get('projection.json')
        if ref is None or ref['size']>compact.MAX_PROJECTION_BYTES:
            raise RecipeError('Missing or oversized input archive projection')
        try:
            projection=_json(objects[ref['sha256']])
            if not isinstance(projection,dict) or projection.get('projection_id')!=projection_id:
                raise RecipeError('Input archive belongs to a different projection')
            expected=_members(projection,max_input_bytes)
        except (RecursionError,OverflowError) as exc:
            raise RecipeError('Invalid input archive projection') from exc
        if index['files']!=expected:
            raise RecipeError('Input archive payload differs from recorded requests')
        return index,objects,total
    # Keep the same bounded decoder/temporary owner, checking the tighter caller
    # allowance and recorded identities before temporary filesystem expansion.
    # Decoded objects in RAM retain the shared decoder's separate byte limits.
    with archive_owner._working_evidence(archive,archive_sha256,decoder=decode) as view:
        root=view/'evidence'
        projection=compact.read_projection(root/'projection.json')
        if projection.get('projection_id')!=projection_id:
            raise RecipeError('Input archive belongs to a different projection')
        expected=_members(projection,max_input_bytes)
        actual=archive_owner._tree(root)
        if {name:dict(sha256=sha256(raw).hexdigest(),size=len(raw)) for name,raw in actual.items()}!=expected:
            raise RecipeError('Input archive payload differs from recorded requests')
        yield root,projection
