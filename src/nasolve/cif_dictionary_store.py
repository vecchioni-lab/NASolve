"""Immutable user-local component numerics with separate native qualifications.

Callers supply verified acquisition/native evidence. A cache hit precedes that
acquisition callback; consumer changes require requalification of saved bytes.
No model, site modifier, generator, optimizer or native process runs here.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile

POLICY_ID = 'cif-qualified-dictionary-store-v1'
_FILES = {'source':'source.cif', 'dictionary':'dictionary.cif',
          'qualification':'qualification.json', 'provenance':'provenance.json'}
_CHECKS = frozenset('source_chemistry_and_configuration native_completed no_native_fatal_or_unused '
    'exact_model_and_component native_coordinate_roundtrip one_complete_monomer exact_effective_definitions '
    'no_contradictory_native_formal_charges effective_declared_bond_orders no_competing_native_ss '
    'proxy_counts_complete finite_active_proxy_parameters exact_active_bonds exact_active_angles '
    'exact_active_torsions exact_active_planes exact_fixed_chirality_membership '
    'omitted_unoriented_volume_coverage energy_inventory finite_energy_and_gradient fixed_coordinate_repeats'.split())


class DictionaryStoreError(ValueError):
    """A reusable entry is incomplete, corrupt or bound to different evidence."""


def _need(value, message):
    if not value: raise DictionaryStoreError(message)


def _bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)+'\n').encode()


def _unique(pairs):
    value = {}
    for key, item in pairs:
        _need(key not in value, 'Duplicate dictionary-store JSON field')
        value[key] = item
    return value


def _json(data):
    return json.loads(data, object_pairs_hook=_unique,
        parse_constant=lambda value: (_ for _ in ()).throw(DictionaryStoreError('Nonfinite dictionary-store JSON')))


def _digest(value):
    return sha256(_bytes(value)).hexdigest()


def _hash(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _regular(path):
    path = Path(path)
    _need(not path.is_symlink() and path.is_file(), 'Dictionary-store artifact is not a regular file')
    return path.read_bytes()


def _identity(value):
    _need(isinstance(value, dict) and all(isinstance(value.get(k), str) and value[k].strip()
        for k in ('name','version')), 'Require explicit tool name and version')
    _bytes(value)
    return value


def _request_key(request):
    """Producer versions are provenance; their upgrade must not discard numerics.

    A different numerical backend or recipe is a different request. An updated
    builder of the same family can still consume an older usable dictionary;
    its native consumer/qualification policy is checked independently.
    """
    _identity(request['generator'])
    identity = {k:v for k,v in request.items() if k != 'generator'}
    identity['generator_family'] = request['generator']['name']
    return _digest(identity)


def default_dictionary_store(*, environ=None, home=None, platform=None):
    """Persistent application data, independent of checkout or current directory."""
    env = os.environ if environ is None else environ
    if env.get('NASOLVE_CIF_STORE'): return Path(env['NASOLVE_CIF_STORE']).expanduser()
    user = Path.home() if home is None else Path(home)
    system = sys.platform if platform is None else platform
    if system == 'darwin': return user/'Library'/'Application Support'/'NASolve'/'cif-dictionaries'/'v1'
    if system == 'win32': return Path(env.get('LOCALAPPDATA', user/'AppData'/'Local'))/'NASolve'/'cif-dictionaries'/'v1'
    return Path(env.get('XDG_DATA_HOME', user/'.local'/'share'))/'nasolve'/'cif-dictionaries'/'v1'


def make_dictionary_request(source, code, *, source_authority, recipe, generator):
    """Bind exact source/state/mapping and repair policy, excluding crystal XYZ."""
    from .cif_stereochemistry_audit import _values, _graph, reader_stereo_inventory
    source = Path(source); original = _regular(source)
    _need(isinstance(code, str) and re.fullmatch('[A-Za-z0-9]{1,3}', code), 'Unsupported component identity')
    _need(source_authority in {'CURATED','EXPLICIT','NATIVE','VERIFIED_SOURCE'}, 'Require declared source authority')
    _need(isinstance(recipe, dict) and isinstance(recipe.get('policy_id'), str) and recipe['policy_id'], 'Require repair policy identity')
    _identity(generator); _bytes(recipe)
    values = _values(source, code); elements, orders, charges, neighbors = _graph(values)
    stereo = reader_stereo_inventory(source, code)
    graph = {'atom_mapping': {n:n for n in sorted(elements)}, 'elements':elements,
        'bond_orders':[[list(edge), order] for edge,order in sorted(orders.items())],
        'formal_charges':charges, 'explicit_hydrogens':{n:sorted(neighbors[n]) for n,e in elements.items() if e in {'H','D'}},
        'atom_stereo':{n:r['declared_stereo'] for n,r in stereo['atoms'].items()},
        'signed_chirality':stereo['source_signed_chirality']}
    _need(_regular(source) == original, 'Source changed during dictionary request')
    request = {'schema_version':1, 'policy_id':POLICY_ID, 'component':code, 'source_authority':source_authority,
        'source_sha256':sha256(original).hexdigest(), 'source_size':len(original), 'declared_chemistry':graph,
        'recipe':recipe, 'generator':generator}
    return _json(_bytes(request))


def _payload(request, source, candidate, qualification, consumer, provenance, *, allow_stale_qualification=False):
    from .cif_candidate_usability import reassess_complete_candidate, POLICY_ID as qualification_policy
    _identity(consumer); _bytes(qualification); _bytes(provenance)
    fresh_request = make_dictionary_request(source, request['component'], **{
        k:request[k] for k in ('source_authority','recipe','generator')})
    _need(fresh_request == request, 'Source, state or request policy changed')
    source_data, candidate_data = _regular(source), _regular(candidate)
    q = qualification; assessment = q.get('source_assessment', {}); stereo = assessment.get('finished_stereo', {})
    current = q.get('policy_id') == qualification_policy
    stale = (allow_stale_qualification and isinstance(q.get('policy_id'),str)
        and re.fullmatch('cif-isolated-candidate-native-usability-v[1-9][0-9]*',q['policy_id']) is not None)
    _need(q.get('schema_version') == 1 and (current or stale)
        and q.get('status') == 'ISOLATED_NATIVE_USABILITY_PASS' and q.get('native_usable') is True
        and q.get('component') == request['component'] and q.get('scope') == 'ISOLATED_COMPONENT_ONLY'
        and q.get('candidate_sha256') == sha256(candidate_data).hexdigest()
        and stereo.get('source_sha256') == sha256(source_data).hexdigest()
        and stereo.get('candidate_sha256') == q['candidate_sha256']
        and stereo.get('stereochemistry') in {'PRESERVED','UNASSESSED'}
        and isinstance(q.get('checks'), dict) and bool(q['checks']) and (not current or _CHECKS <= q['checks'].keys())
        and all(value is True for value in q['checks'].values()), 'Require complete bound native usability evidence')
    fresh = reassess_complete_candidate(source, candidate, request['component'])
    _need(fresh['candidate_status'] == 'CANDIDATE_REVIEW'
        and fresh['finished_stereo']['stereochemistry'] == stereo['stereochemistry'], 'Dictionary no longer preserves declared chemistry')
    _need(isinstance(provenance, dict) and type(provenance.get('converged')) in {bool,type(None)}
        and isinstance(provenance.get('stopping'), str) and provenance['stopping']
        and isinstance(provenance.get('notes'), list) and all(isinstance(n,str) for n in provenance['notes']),
        'Require original stopping evidence and limitation notes')
    data = {'source':source_data, 'dictionary':candidate_data, 'qualification':_bytes(q), 'provenance':_bytes(provenance)}
    refs = {k:{'anchor':'dictionary_entry', 'path':_FILES[k], 'sha256':sha256(v).hexdigest(), 'size':len(v)} for k,v in data.items()}
    manifest = {'schema_version':1, 'policy_id':POLICY_ID, 'request':request, 'request_key':_request_key(request),
        'consumer':consumer, 'qualification_scope':'ISOLATED_COMPONENT_ONLY', 'artifacts':refs,
        'native_qualification_policy':q['policy_id'],
        'linked_context':'REQUALIFY_FOR_CURRENT_SITE', 'model_geometry':'ASSESS_FOR_NEW_MODEL'}
    return manifest, data


def _read_entry(directory, entry_id, request=None):
    directory = Path(directory)
    _need(_hash(entry_id) and not directory.is_symlink() and directory.is_dir(), 'Unsafe dictionary entry')
    _need({p.name for p in directory.iterdir()} == {*_FILES.values(), 'manifest.json'}, 'Incomplete dictionary entry inventory')
    raw = _regular(directory/'manifest.json')
    _need(sha256(raw).hexdigest() == entry_id, 'Dictionary entry manifest hash changed')
    manifest = _json(raw); r = manifest['request']
    _need(manifest.get('schema_version') == 1 and manifest.get('policy_id') == POLICY_ID
        and manifest.get('request_key') == _request_key(r)
        and (request is None or _request_key(r) == _request_key(request)), 'Dictionary entry request differs')
    data = {}
    for key, name in _FILES.items():
        ref = manifest['artifacts'][key]; content = _regular(directory/name)
        _need(ref == {'anchor':'dictionary_entry','path':name,'sha256':sha256(content).hexdigest(),'size':len(content)},
            'Dictionary entry artifact hash differs')
        data[key] = content
    q, p = _json(data['qualification']), _json(data['provenance'])
    recomputed, _ = _payload(r, directory/'source.cif', directory/'dictionary.cif', q, manifest['consumer'], p,
        allow_stale_qualification=True)
    _need(manifest == recomputed, 'Dictionary entry policy or qualification changed')
    from .cif_candidate_usability import POLICY_ID as qualification_policy
    return {'entry_id':entry_id, 'directory':directory, 'manifest':manifest, 'qualification':q, 'provenance':p,
        'qualification_current':q['policy_id'] == qualification_policy}


def _write(path, data):
    with path.open('xb') as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno())
    path.chmod(0o600)


def _write_payload(directory, manifest, data):
    directory.mkdir(mode=0o700)
    for key, content in data.items(): _write(directory/_FILES[key], content)
    _write(directory/'manifest.json', _bytes(manifest))


def _safe_directory(path):
    _need(not path.is_symlink(), 'Dictionary store cannot traverse a symlink')
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    _need(path.is_dir() and not path.is_symlink(), 'Dictionary store directory changed')


def publish_dictionary(root, request, source, candidate, qualification, *, consumer, provenance):
    """Publish one usable entry atomically; existing scientific bytes are immutable."""
    manifest, data = _payload(request, source, candidate, qualification, consumer, provenance)
    root = Path(root).expanduser().absolute(); _safe_directory(root)
    entries = root/'entries'; _safe_directory(entries)
    key_dir = entries/manifest['request_key']; _safe_directory(key_dir)
    pending = root/'pending'; _safe_directory(pending)
    entry_id = sha256(_bytes(manifest)).hexdigest(); destination = key_dir/entry_id
    if destination.exists() or destination.is_symlink(): return _read_entry(destination, entry_id, request)
    with tempfile.TemporaryDirectory(prefix='entry-', dir=pending) as temporary:
        staged = Path(temporary)/'entry'; _write_payload(staged, manifest, data)
        _read_entry(staged, entry_id, request)
        try: staged.rename(destination)
        except FileExistsError:
            return _read_entry(destination, entry_id, request)
    return _read_entry(destination, entry_id, request)


def lookup_dictionary(root, request, consumer):
    """Return compatible numerics or a requalification request; never generate."""
    from .cif_doctor_selection import ComponentCandidate, select_component_candidate
    _identity(consumer); _bytes(request)
    root = Path(root).expanduser().absolute(); entries = root/'entries'; key_dir = entries/_request_key(request)
    notes = []; found = []
    try:
        if any(p.is_symlink() for p in [root, entries, key_dir]) or not key_dir.is_dir():
            return {'status':'MISS', 'notes':notes}
        children = sorted(key_dir.iterdir())
        _need(len(children) <= 64, 'Dictionary request has more than 64 entries')
        for directory in children:
            try: found.append(_read_entry(directory, directory.name, request))
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                notes.append('A damaged or unsupported local dictionary entry was excluded.')
    except (OSError, ValueError):
        return {'status':'MISS', 'notes':['The persistent dictionary store is unavailable; verified acquisition remains available.']}
    if not found: return {'status':'MISS', 'notes':notes}
    compatible = [e for e in found if e['manifest']['consumer'] == consumer and e['qualification_current']]
    pool = compatible or found; rows = []
    for e in pool:
        q, p = e['qualification'], e['provenance']
        rows.append(ComponentCandidate(candidate_id=e['entry_id'], component=request['component'], source_priority=0,
            artifact_sha256=q['candidate_sha256'], chemistry_sha256=_digest(request['declared_chemistry']),
            integrity_verified=True, native_usable=True, chemistry_preserved=True, essential_restraints_present=True,
            finite_parameters=True, stereochemistry=q['source_assessment']['finished_stereo']['stereochemistry'],
            converged=p['converged'], warnings=tuple(p['notes'])))
    decision = select_component_candidate(rows)
    selected = next(e for e in pool if e['entry_id'] == decision['selected_candidate'])
    return {**selected, 'status':'HIT' if compatible else 'REQUALIFICATION_REQUIRED', 'decision':decision, 'notes':notes}


def _freeze(output, manifest, data, *, origin, persistent_store, notes):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    _need(not any(p.is_symlink() for p in output.parents), 'Snapshot output parent cannot traverse a symlink')
    output.parent.mkdir(parents=True, exist_ok=True)
    entry_id = sha256(_bytes(manifest)).hexdigest(); provenance = _json(data['provenance'])
    report = {'schema_version':1, 'policy_id':POLICY_ID, 'status':origin, 'entry_id':entry_id,
        'request_key':manifest['request_key'], 'component':manifest['request']['component'],
        'entry':{'anchor':'dictionary_resolution','path':'entry','manifest_sha256':entry_id},
        'persistent_store':persistent_store, 'converged':provenance['converged'], 'stopping':provenance['stopping'],
        'notes':list(dict.fromkeys([*provenance['notes'], *notes])), 'requires_cif_review':False,
        'linked_context':'REQUALIFY_FOR_CURRENT_SITE', 'model_geometry':'ASSESS_FOR_NEW_MODEL',
        'native_qualification':'INHERITED_VERIFIED_ISOLATED_EVIDENCE',
        'native_execution':'CALLER_ADAPTER_EVIDENCE; NO_PROCESS_EXECUTED_BY_STORE',
        'model_editing':'NOT_RUN', 'model_optimization':'NOT_RUN', 'production_adoption':'NOT_RUN',
        'report_text':f"{manifest['request']['component']}: usable numerical dictionary {'reused from local storage' if origin == 'REUSED' else 'retained locally'}. Site and model checks remain separate."}
    with tempfile.TemporaryDirectory(prefix='dictionary-snapshot-', dir=output.parent) as temporary:
        staged = Path(temporary)/'snapshot'; staged.mkdir(mode=0o700)
        _write_payload(staged/'entry', manifest, data); _write(staged/'resolution.json', _bytes(report))
        resolve_dictionary_snapshot(staged)
        staged.rename(output)
    return report


def resolve_dictionary_snapshot(output):
    """Read independently frozen bytes after cache/source removal or relocation."""
    root = Path(output)
    _need(not root.is_symlink() and root.is_dir(), 'Unsafe dictionary snapshot')
    r = _json(_regular(root/'resolution.json')); ref = r['entry']
    _need(r.get('schema_version') == 1 and r.get('policy_id') == POLICY_ID
        and ref == {'anchor':'dictionary_resolution','path':'entry','manifest_sha256':r['entry_id']}, 'Snapshot anchor differs')
    e = _read_entry(root/'entry', r['entry_id'])
    _need(r['request_key'] == e['manifest']['request_key'] and r['component'] == e['manifest']['request']['component']
        and r['converged'] is e['provenance']['converged'] and r['stopping'] == e['provenance']['stopping']
        and r.get('status') in {'REUSED','PREPARED_AND_FROZEN','REQUALIFIED_AND_FROZEN'}
        and r.get('requires_cif_review') is False and r.get('production_adoption') == 'NOT_RUN'
        and r.get('linked_context') == 'REQUALIFY_FOR_CURRENT_SITE' and r.get('model_geometry') == 'ASSESS_FOR_NEW_MODEL'
        and isinstance(r.get('notes'), list) and all(isinstance(n,str) for n in r['notes'])
        and all(n in r['notes'] for n in e['provenance']['notes']),
        'Snapshot provenance binding differs')
    return {**e, 'source':root/'entry/source.cif', 'dictionary':root/'entry/dictionary.cif', 'report':r}


def resolve_qualified_dictionary(source, code, store_root, output, *, source_authority, recipe, generator, consumer,
                                 acquire=None, requalify=None):
    """Consult reusable numerics first, then acquire or requalify via caller adapters.

    This is a component acquisition API, not authorization to adopt an isolated
    dictionary into a linked structure. Source precedence is chosen upstream and
    is part of the request. No crystal coordinates enter the reusable key.
    """
    output = Path(output)
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    store = Path(store_root).expanduser().resolve()
    destination = output.expanduser().resolve()
    _need(destination != store and destination not in store.parents and store not in destination.parents,
        'Run snapshots and the persistent store must be separate')
    request = make_dictionary_request(source, code, source_authority=source_authority, recipe=recipe, generator=generator)
    hit = lookup_dictionary(store_root, request, consumer); notes = hit['notes']
    origin = 'PREPARED_AND_FROZEN'; storage = 'AVAILABLE'
    if hit['status'] == 'HIT':
        e = hit; manifest = e['manifest']; data = {k:_regular(e['directory']/name) for k,name in _FILES.items()}
        return _freeze(output, manifest, data, origin='REUSED', persistent_store=storage, notes=notes)
    if hit['status'] == 'REQUALIFICATION_REQUIRED':
        if requalify is None:
            return {'schema_version':1, 'policy_id':POLICY_ID, 'status':'REQUALIFICATION_REQUIRED',
                'component':code, 'entry_id':hit['entry_id'], 'requires_cif_review':False,
                'regeneration':'NOT_RUN; REQUALIFY_SAVED_NUMERICS_FIRST', 'notes':notes}
        saved = hit['directory']; candidate = saved/'dictionary.cif'; before = _regular(candidate)
        qualification = requalify(Path(source), candidate, consumer)
        _need(_regular(candidate) == before, 'Native requalification changed saved dictionary bytes')
        acquired = {'candidate':candidate, 'qualification':qualification, 'provenance':hit['provenance']}
        # Requalification uses the old producer's numerical bytes. Record that
        # original producer, even if the caller now has an upgraded generator.
        request = hit['manifest']['request']
        origin = 'REQUALIFIED_AND_FROZEN'
    else:
        if acquire is None:
            return {'schema_version':1, 'policy_id':POLICY_ID, 'status':'MISS', 'component':code, 'notes':notes,
                'requires_cif_review':False}
        acquired = acquire()
    manifest, data = _payload(request, source, acquired['candidate'], acquired['qualification'], consumer, acquired['provenance'])
    try:
        publish_dictionary(store_root, request, source, acquired['candidate'], acquired['qualification'],
            consumer=consumer, provenance=acquired['provenance'])
    except (OSError, DictionaryStoreError):
        storage = 'UNAVAILABLE'
        notes = [*notes, 'The persistent store was unavailable; this run retains its verified dictionary and provenance.']
    return _freeze(output, manifest, data, origin=origin, persistent_store=storage, notes=notes)
