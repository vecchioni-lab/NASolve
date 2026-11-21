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
from .input_archive import (pack_fdp_inputs, expanded_fdp_inputs, inspect_recorded_fdp,
                            _inspect_recorded_projection, archive_owner)
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


def inspect_published_fdp_batch(archive, publication, *, publication_id,
                                max_input_bytes=archive_owner.MAX_BYTES):
    """Read all named published attempts in one temporary archive context.

    Returns the same ordered inspection records as individual selection. All
    results must validate before anything is returned; no archive view escapes.
    Repeated requests retain their distinct trial identities and result records.
    """
    try:
        first = publication['attempts'][0]['trial_id']
    except (KeyError, TypeError, IndexError) as exc:
        raise RecipeError('Require a nonempty completed fdp publication') from exc
    _selection(publication, publication_id, first)
    selections = [_selection(publication, publication_id, a['trial_id'])
                  for a in publication['attempts']]
    reports = []
    with expanded_fdp_inputs(archive, publication['archive_sha256'],
            projection_id=publication['projection_id'], max_input_bytes=max_input_bytes) as (_, projection):
        for selected, parent in selections:
            report = _inspect_recorded_projection(projection, publication['archive_sha256'],
                projection_id=publication['projection_id'], trial_id=selected['trial_id'],
                expected_parent=parent)
            if report['record']['record_id'] != selected['record_id']:
                raise RecipeError('Published attempt belongs to a different recorded result')
            reports.append(report)
    return reports


# Audited children have a distinct source contract from numbered legacy trials.
# They share this publisher, durable records and the existing archive owner.
CHILD_KIND = 'metal-audited-child-publication'
CHILD_PROJECTION = 'metal-audited-child-projection'


def _store_reference(store,path,limit):
    from .storage import _state,_hash
    path=Path(path).absolute();relative=path.relative_to(store).as_posix()
    path=records.path_in(store,relative);state=_state(path)
    if state[2]>limit:raise RecipeError('Protected publication reference exceeds byte budget')
    return dict(anchor='publication_store',relative_path=relative,sha256=_hash(path,state),size=state[2])


def _store_read(store,ref,limit):
    if (not isinstance(ref,dict) or set(ref)!={'anchor','relative_path','sha256','size'}
            or ref['anchor']!='publication_store'):
        raise RecipeError('Require an explicit publication-store reference')
    checksum(ref['sha256'],'publication-store file')
    path=records.path_in(store,ref['relative_path'])
    if _store_reference(store,path,limit)!=ref:raise RecipeError('Protected publication file changed')
    return path


def _child_protection(store,parents,protected):
    from . import parent_archive,child_session
    for identity,ref in parents.items():
        checksum(identity,'protected parent manifest')
        path=_store_read(store,ref,parent_archive.MAX_MANIFEST_BYTES)
        if path.name!=parent_archive.MANIFEST or ref['sha256']!=identity:
            raise RecipeError('Protected parent reference does not select its pinned manifest')
        manifest=parent_archive._manifest(path.parent,identity)
        for part in manifest['parts']:parent_archive._part_bytes(path.parent,part)
    reports={}
    for identity,ref in protected.items():
        checksum(identity,'protected scientific review')
        path=_store_read(store,ref,MAX_PUBLICATION_BYTES)
        if path.name!='review.json':raise RecipeError('Require an explicit protected review')
        reports[identity]=child_session.inspect_audited_child(path.parent,review_id=identity)
    return reports


def _child_members(projection,max_input_bytes):
    from . import child_process
    from .input_archive import _budget
    _budget(max_input_bytes)
    fields={'kind','schema_version','requests','parents','records','projection_id'}
    if (not isinstance(projection,dict) or set(projection)!=fields
            or projection['kind']!=CHILD_PROJECTION or type(projection['schema_version']) is not int
            or projection['schema_version']!=1):raise RecipeError('Unsupported audited-child projection')
    body=dict(projection);identity=body.pop('projection_id')
    if identity!=digest(body):raise RecipeError('Audited-child projection changed')
    rows=projection['records'];requests=projection['requests'];parents=projection['parents']
    if (not isinstance(rows,list) or not 1<=len(rows)<=compact.MAX_TRIALS
            or not isinstance(requests,dict) or not isinstance(parents,dict)
            or len({r['review_id'] for r in rows})!=len(rows)
            or {r['request_id'] for r in rows}!=set(requests)
            or {r['parent_id'] for r in rows}!=set(parents)):
        raise RecipeError('Require distinct audited children and their exact shared inputs/parents')
    for key,value in parents.items():
        if set(value)!={'manifest_sha256','context'} or digest(value)!=key:
            raise RecipeError('Changed compact parent context')
        checksum(value['manifest_sha256'],'compact parent manifest')
    for row in rows:
        if set(row)!={'review_id','request_id','parent_id','output_evidence_id','recorded_free_r','result','record_id'}:
            raise RecipeError('Unsupported compact audited result')
        unsigned=dict(row);identity=unsigned.pop('record_id')
        if digest(unsigned)!=identity:raise RecipeError('Compact audited result changed')
        for key in ('review_id','request_id','output_evidence_id'):checksum(row[key],'audited '+key)
        if (requests[row['request_id']]['parent_manifest_sha256']!=parents[row['parent_id']]['manifest_sha256']
                or row['result']['status']!='FDP_REVIEW' or row['result']['freeze_audit']!='PASS'):
            raise RecipeError('Compact result differs from an audited frozen child')
    raw=compact.encode(projection)
    if len(raw)>compact.MAX_PROJECTION_BYTES:raise RecipeError('Audited projection exceeds byte budget')
    members={'projection.json':dict(sha256=sha256(raw).hexdigest(),size=len(raw))}
    for key,request in requests.items():
        child_process._request(request,key)
        if request['schema_version']!=2 or set(request['files']).intersection(request['worker_files']):
            raise RecipeError('Require distinct helper-pinned executable inputs')
        for name,ref in {**request['files'],**request['worker_files']}.items():
            members[f'requests/{key}/{name}']=ref
    directories=sorted({p.as_posix() for n in members for p in Path(n).parents if str(p)!='.'})
    archive_owner._file_index(members,directories,max_files=archive_owner.MAX_FILES)
    if sum(r['size'] for r in members.values())>max_input_bytes:
        raise RecipeError('Audited publication exceeds logical input budget')
    return members


def _child_receipt(value,identity):
    checksum(identity,'independent audited publication')
    fields={'kind','schema_version','status','archive','projection_id','parents','protected_reviews',
        'attempts','request_count','source_replay','scientific_acceptance','record_sha256',*_FALSE}
    if not isinstance(value,dict) or set(value)!=fields:raise RecipeError('Unsupported audited publication')
    body=dict(value);recorded=body.pop('record_sha256')
    if (recorded!=identity or sha256(records._canonical(body)).hexdigest()!=identity
            or value['kind']!=CHILD_KIND or type(value['schema_version']) is not int or value['schema_version']!=1
            or value['status']!='PUBLISHED_FDP_REVIEW' or value['source_replay']!='AUDITED_CHILD_REPLAY_BEFORE_PUBLICATION'
            or value['scientific_acceptance']!='NOT_ASSESSED' or any(value[k] is not False for k in _FALSE)
            or records.serialized_record_size(body)>MAX_PUBLICATION_BYTES):
        raise RecipeError('Changed or incomplete audited publication')
    checksum(value['projection_id'],'audited projection identity')
    rows=value['attempts']
    if (not isinstance(rows,list) or not 1<=len(rows)<=compact.MAX_TRIALS
            or len({r['review_id'] for r in rows})!=len(rows)
            or not isinstance(value['parents'],dict) or not isinstance(value['protected_reviews'],dict)
            or set(value['parents'])!={r['parent_manifest_sha256'] for r in rows}
            or not set(value['protected_reviews'])<={r['review_id'] for r in rows}
            or type(value['request_count']) is not int or value['request_count']!=len({r['request_id'] for r in rows})):
        raise RecipeError('Incomplete audited publication dependencies')
    for row in rows:
        if set(row)!={'review_id','record_id','request_id','parent_manifest_sha256'}:
            raise RecipeError('Unsupported audited selection')
        for v in row.values():checksum(v,'audited selection identity')


def _child_selections(projection):
    return [dict(review_id=r['review_id'],record_id=r['record_id'],request_id=r['request_id'],
        parent_manifest_sha256=projection['parents'][r['parent_id']]['manifest_sha256']) for r in projection['records']]


def _inspect_audited_publication(store,publication,publication_id,max_input_bytes):
    from . import child_process
    from .materialize import _json
    store=child_process._root(store).resolve();_child_receipt(publication,publication_id)
    before=_child_protection(store,publication['parents'],publication['protected_reviews'])
    archive=_store_read(store,publication['archive'],archive_owner.MAX_ARCHIVE_BYTES)
    def decode(data,identity):
        index,objects,total=archive_owner._decode(data,identity)
        ref=index['files'].get('projection.json')
        if ref is None or ref['size']>compact.MAX_PROJECTION_BYTES:raise RecipeError('Missing audited projection')
        projection=_json(objects[ref['sha256']])
        if projection['projection_id']!=publication['projection_id'] or index['files']!=_child_members(projection,max_input_bytes):
            raise RecipeError('Audited archive differs from declared projection/inputs')
        return index,objects,total
    with archive_owner._working_evidence(archive,publication['archive']['sha256'],decoder=decode) as view:
        projection=_json((view/'evidence/projection.json').read_bytes())
        if _child_selections(projection)!=publication['attempts']:raise RecipeError('Audited selection changed')
        for key,request in projection['requests'].items():
            root=view/'evidence/requests'/key
            child_process._declared_plan(child_process._inputs(root,request['files']))
            child_process._worker_payload(root,request['worker_files'])
        for row in projection['records']:
            if row['review_id'] in before:
                report=before[row['review_id']]
                if (report['result']!=row['result'] or report['request_id']!=row['request_id']
                        or report['output_evidence_id']!=row['output_evidence_id']
                        or report['recorded_free_r']!=row['recorded_free_r']
                        or report['parent_context']!=projection['parents'][row['parent_id']]['context']):
                    raise RecipeError('Protected full evidence differs from compact result')
    if _child_protection(store,publication['parents'],publication['protected_reviews'])!=before:
        raise RecipeError('Protected evidence changed during reopening')
    _store_read(store,publication['archive'],archive_owner.MAX_ARCHIVE_BYTES)
    return dict(kind='metal-audited-publication-inspection',schema_version=1,publication_id=publication_id,
        records=projection['records'],parents=projection['parents'],request_count=publication['request_count'],
        protected_reviews_verified=list(publication['protected_reviews']),protected_parent_bytes_verified=True,
        scientific_audit_replayed_for_all_records=set(before)=={r['review_id'] for r in projection['records']},
        record_scope='RECORDED_RESULTS_AND_EXACT_INPUTS',
        new_native_calls=0,scientific_acceptance='NOT_ASSESSED',**{key:False for key in _FALSE})


def inspect_published_audited_results(store,publication,*,publication_id,max_input_bytes=archive_owner.MAX_BYTES):
    """Cold comparison with exact inputs and mandatory declared protection checks.

    Only explicitly protected full reviews are scientifically re-audited. Other
    rows are recorded results, not a native-array replay or retirement authority.
    """
    try:return _inspect_audited_publication(store,publication,publication_id,max_input_bytes)
    except (OSError,ValueError,KeyError,TypeError,OverflowError,RecursionError,records.CampaignError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot reopen audited publication: '+str(exc)) from exc


def _publish_audited_results(store,children,archive,output,parent_archives,protected_reviews,max_input_bytes):
    from tempfile import TemporaryDirectory
    from . import child_process,child_session,parent_archive
    from .materialize import _json
    store=child_process._root(store).resolve()
    if (not isinstance(children,(list,tuple)) or not 1<=len(children)<=compact.MAX_TRIALS
            or any(set(c)!={'directory','review_id'} for c in children)
            or len({c['review_id'] for c in children})!=len(children)
            or not isinstance(parent_archives,dict) or not isinstance(protected_reviews,(list,tuple))
            or len(set(protected_reviews))!=len(protected_reviews)
            or not set(protected_reviews)<={c['review_id'] for c in children}):
        raise RecipeError('Require distinct explicit children, parents and protected selections')
    roots=[child_process._root(c['directory']).resolve() for c in children]
    parent_refs={identity:_store_reference(store,Path(root)/parent_archive.MANIFEST,parent_archive.MAX_MANIFEST_BYTES)
                 for identity,root in parent_archives.items()}
    protected={c['review_id']:_store_reference(store,root/'review.json',MAX_PUBLICATION_BYTES)
               for c,root in zip(children,roots) if c['review_id'] in protected_reviews}
    archive,output=(Path(p).absolute() for p in (archive,output))
    for path in (archive,output):
        records.path_in(store,path.relative_to(store).as_posix())
        if (path.exists() or path.is_symlink() or not path.parent.is_dir()
                or any(path.is_relative_to(root) for root in [*roots,*(Path(root).resolve() for root in parent_archives.values())])):
            raise RecipeError('Require fresh publication files outside all source/protected nodes')
    if archive==output:raise RecipeError('Publication archive and receipt must differ')
    protection=_child_protection(store,parent_refs,protected)
    requests={};parents={};rows=[];payloads={};reports=[]
    for c,root in zip(children,roots):
        report=child_session.inspect_audited_child(root,review_id=c['review_id']);reports.append(report)
        request=child_process._request(_json((root/'attempt/inputs/request.json').read_bytes()),report['request_id'])
        key=request['request_id'];requests[key]=request
        parent=dict(manifest_sha256=request['parent_manifest_sha256'],context=report['parent_context'])
        parent_id=digest(parent);parents[parent_id]=parent
        row=dict(review_id=c['review_id'],request_id=key,parent_id=parent_id,output_evidence_id=report['output_evidence_id'],
            recorded_free_r=report['recorded_free_r'],result=report['result']);row['record_id']=digest(row);rows.append(row)
        if key not in payloads:
            payloads[key]={**child_process._inputs(root/'attempt/inputs',request['files']),
                **child_process._worker_payload(root/'attempt/inputs',request['worker_files'])}
        if sum(len(raw) for values in payloads.values() for raw in values.values())>max_input_bytes:
            raise RecipeError('Audited publication exceeds logical input budget')
    if set(parent_refs)!={v['manifest_sha256'] for v in parents.values()}:
        raise RecipeError('Require exactly the used protected parent archives')
    projection=dict(kind=CHILD_PROJECTION,schema_version=1,requests=requests,parents=parents,records=rows)
    projection['projection_id']=digest(projection);members=_child_members(projection,max_input_bytes)
    with TemporaryDirectory(prefix='metal-audited-publication-') as temporary:
        stage=Path(temporary).resolve()/'inputs';stage.mkdir()
        (stage/'projection.json').write_bytes(compact.encode(projection))
        for key,values in payloads.items():
            folder=stage/'requests'/key;folder.mkdir(parents=True)
            for name,raw in values.items():(folder/name).write_bytes(raw)
        if {n:dict(sha256=sha256(b).hexdigest(),size=len(b)) for n,b in archive_owner._tree(stage).items()}!=members:
            raise RecipeError('Staged audited inputs changed')
        packed=archive_owner.pack_runtime_evidence(stage,archive)
    _sync_archive(archive)
    for c,root,report in zip(children,roots,reports):
        if child_session.inspect_audited_child(root,review_id=c['review_id'])!=report:
            raise RecipeError('Audited child changed before publication')
    if _child_protection(store,parent_refs,protected)!=protection:raise RecipeError('Protected evidence changed before publication')
    value=dict(kind=CHILD_KIND,schema_version=1,status='PUBLISHED_FDP_REVIEW',
        archive=_store_reference(store,archive,archive_owner.MAX_ARCHIVE_BYTES),projection_id=projection['projection_id'],
        parents=parent_refs,protected_reviews=protected,attempts=_child_selections(projection),request_count=len(requests),
        source_replay='AUDITED_CHILD_REPLAY_BEFORE_PUBLICATION',scientific_acceptance='NOT_ASSESSED',**{key:False for key in _FALSE})
    prospective=dict(value,record_sha256=sha256(records._canonical(value)).hexdigest())
    _child_receipt(prospective,prospective['record_sha256'])
    published=_write_publication(output,value)
    if published!=prospective or compact.read_projection(output,max_projection_bytes=MAX_PUBLICATION_BYTES)!=published:
        raise RecipeError('Audited publication changed during completion')
    inspect_published_audited_results(store,published,publication_id=published['record_sha256'],max_input_bytes=max_input_bytes)
    return published


def publish_audited_results(store,children,archive,output,*,parent_archives,protected_reviews=(),
                            max_input_bytes=archive_owner.MAX_BYTES):
    """Publish exact shared inputs and compact results; preserve every source.

    Parents and explicitly protected full reviews must already live under the
    caller's declared store. This adapter never selects, copies or retires them.
    No implicit protection registry, dependency discovery or native run follows.
    """
    try:return _publish_audited_results(store,children,archive,output,parent_archives,protected_reviews,max_input_bytes)
    except (OSError,ValueError,KeyError,TypeError,OverflowError,RecursionError,records.CampaignError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot publish audited results: '+str(exc)) from exc
