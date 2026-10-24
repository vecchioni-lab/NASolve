"""Exercise persistent component reuse with verified inputs and owned controls."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile

POLICY_ID = 'cif-qualified-dictionary-reuse-controls-v1'


def exercise_dictionary_reuse(resources, store_root, output):
    """Seed/reuse through the shared API; retain original limits and frozen copies.

    This test writes only immutable store entries and separate run snapshots.
    The simulated consumer-version change does not execute a native process.
    An owned cache copy tests removal/relocation without deleting user entries.
    """
    from .cif_dictionary_store import (make_dictionary_request, lookup_dictionary,
        resolve_qualified_dictionary, resolve_dictionary_snapshot)
    if not 1 <= len(resources) <= 4 or any(not isinstance(code,str) or re.fullmatch('[A-Za-z0-9]{1,3}',code) is None for code in resources):
        raise ValueError('Require one to four explicitly named component reuse controls')
    output = Path(output); store_root = Path(store_root).expanduser().absolute()
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    if any(p.is_symlink() for p in output.parents):raise ValueError('Reuse output parent cannot traverse a symlink')
    output.mkdir(parents=True)
    originals = {Path(item[k]):Path(item[k]).read_bytes() for item in resources.values() for k in ('source','numerical')}
    cases = {}
    for code, item in sorted(resources.items()):
        folder = output/code; folder.mkdir()
        options = {k:deepcopy(item[k]) for k in ('source_authority','recipe','generator','consumer')}
        source, numerical = Path(item['source']), Path(item['numerical'])
        request = make_dictionary_request(source, code, **{k:v for k,v in options.items() if k != 'consumer'})
        acquired = []
        def acquire():
            acquired.append('VERIFIED_SAVED_CANDIDATE_ADAPTER')
            return {'candidate':numerical,'qualification':item['qualification'],'provenance':item['provenance']}
        first = resolve_qualified_dictionary(source, code, store_root, folder/'first', acquire=acquire, **options)
        def snapshot_reference(path):
            receipt = path/'resolution.json'; data = receipt.read_bytes()
            return {'anchor':'dictionary_reuse_directory','path':receipt.relative_to(output).as_posix(),
                'sha256':sha256(data).hexdigest(),'size':len(data)}
        row = {'first':first, 'acquisition_adapter_calls':len(acquired), 'checks':{},
            'first_snapshot':snapshot_reference(folder/'first'),
            'consumer_identity_scope':'VERIFIED_SAVED_NATIVE_FINGERPRINTS; NO_INSTALLED_RUNTIME_REPROBE'}
        cases[code] = row; checks = row['checks']
        selected = resolve_dictionary_snapshot(folder/'first')
        checks['persistent_store_available'] = first['persistent_store'] == 'AVAILABLE'
        checks['independent_first_snapshot'] = selected['manifest']['request'] == request
        if not checks['persistent_store_available']:
            row['repeat'] = {'status':'NOT_RUN; OPTIONAL_PERSISTENT_STORE_UNAVAILABLE'}
            continue
        def forbidden():
            raise AssertionError('A reuse control attempted another acquisition or generator')
        repeated = resolve_qualified_dictionary(source, code, store_root, folder/'repeat', acquire=forbidden, **options)
        row['repeat'] = repeated
        row['repeat_snapshot'] = snapshot_reference(folder/'repeat')
        loaded = resolve_dictionary_snapshot(folder/'repeat')
        checks['repeat_reuses_same_entry'] = repeated['status'] == 'REUSED' and repeated['entry_id'] == first['entry_id']
        checks['repeat_exact_numerical_bytes'] = loaded['dictionary'].read_bytes() == selected['dictionary'].read_bytes()
        checks['original_stopping_and_notes_preserved'] = (loaded['provenance'] == selected['provenance']
            and repeated['converged'] is first['converged'] and all(n in repeated['notes'] for n in first['notes']))
        # Exact-source identity changes even when a nonchemical comment is all
        # that changed. Charge/order/stereo variants are separate unit regressions.
        variant = folder/'source_hash_control.cif'; variant.write_bytes(source.read_bytes()+b'\n# REUSE CONTROL: DISTINCT SOURCE BYTES\n')
        other = make_dictionary_request(variant, code, **{k:v for k,v in options.items() if k != 'consumer'})
        changed = lookup_dictionary(store_root, other, options['consumer'])
        checks['different_source_is_not_a_hit'] = changed['status'] == 'MISS'
        authority = dict(options); authority['source_authority'] = 'CURATED' if options['source_authority'] != 'CURATED' else 'EXPLICIT'
        other = make_dictionary_request(source, code, **{k:v for k,v in authority.items() if k != 'consumer'})
        checks['source_authority_is_not_overridden'] = lookup_dictionary(store_root, other, options['consumer'])['status'] == 'MISS'
        consumer = deepcopy(options['consumer']); consumer['version'] += ';NONCHEMICAL_VERSION_CONTROL'
        other = resolve_qualified_dictionary(source, code, store_root, folder/'changed_consumer',
            acquire=forbidden, **{**options,'consumer':consumer})
        row['changed_consumer'] = other
        checks['changed_consumer_requalifies_before_generation'] = (other['status'] == 'REQUALIFICATION_REQUIRED'
            and not (folder/'changed_consumer').exists())
        # Copy just this immutable entry to a disposable cache, freeze it, then
        # destroy only that owned copy. The user's persistent entry is untouched.
        hit = lookup_dictionary(store_root, request, options['consumer'])
        with tempfile.TemporaryDirectory(prefix='nasolve-reuse-removal-') as temporary:
            isolated = Path(temporary).resolve()/'store'
            target = isolated/'entries'/first['request_key']/first['entry_id']
            target.parent.mkdir(parents=True); shutil.copytree(hit['directory'], target)
            independent = resolve_qualified_dictionary(source, code, isolated, folder/'before_relocation', acquire=forbidden, **options)
            (folder/'before_relocation').rename(folder/'relocated_snapshot')
        independent = resolve_dictionary_snapshot(folder/'relocated_snapshot')
        row['standalone_snapshot'] = snapshot_reference(folder/'relocated_snapshot')
        checks['snapshot_survives_cache_removal_and_relocation'] = (independent['dictionary'].read_bytes() == loaded['dictionary'].read_bytes()
            and independent['provenance'] == loaded['provenance'])
        checks['site_and_model_evidence_remain_separate'] = (repeated['linked_context'] == 'REQUALIFY_FOR_CURRENT_SITE'
            and repeated['model_geometry'] == 'ASSESS_FOR_NEW_MODEL' and repeated['production_adoption'] == 'NOT_RUN')
        row['selected_dictionary_sha256'] = sha256(loaded['dictionary'].read_bytes()).hexdigest()
        row['scope'] = 'REUSABLE_ISOLATED_NUMERICS; NO_NEW_LINKED_OR_MODEL_QUALIFICATION'
    preserved = all(path.read_bytes() == data for path,data in originals.items())
    passes = bool(cases) and preserved and all(all(r['checks'].values()) for r in cases.values())
    result = {'schema_version':1, 'policy_id':POLICY_ID, 'status':'QUALIFIED_DICTIONARY_REUSE_PASS' if passes else 'REVIEW',
        'cases':cases, 'source_inputs_preserved':preserved, 'persistent_store_location':str(store_root),
        'persistent_store_location_role':'HISTORICAL_PROVENANCE_ONLY; FROZEN_COPIES_ARE_OPERATIONAL',
        'new_native_calls':0, 'dictionary_generation':'NOT_RUN', 'model_optimization':'NOT_RUN',
        'model_editing':'NOT_RUN', 'readyset_execution':'NOT_RUN', 'refinement':'NOT_RUN',
        'policy_recompilation':'NOT_RUN', 'production_adoption':'NOT_RUN', 'requires_cif_review':False,
        'scientific_geometry_qualification':'NOT_ASSESSED',
        'pipeline_boundary':'Shared component resolver API implemented; ordinary PostMR acquisition/adoption orchestration remains separate.'}
    (output/'dictionary_reuse.json').write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n')
    return result


def replay_dictionary_reuse(members, output):
    """Reproduce the exact closed C66 parent with current code and owned storage."""
    from pathlib import PurePosixPath
    from .cif_dictionary_store import resolve_dictionary_snapshot
    report=json.loads(members['dictionary_reuse_audit.json'])
    expected={k:v for k,v in report.items() if k not in {'directory','source_resources'}}
    if expected!=json.loads(members['dictionary_reuse/dictionary_reuse.json']):raise ValueError('Reuse report copies differ')
    output=Path(output);output.mkdir(parents=True,exist_ok=False);resources={}
    def safe(name):
        return isinstance(name,str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(p not in {'','.','..'} for p in name.split('/'))
    for code,row in report['cases'].items():
        loaded=[]
        for field in ['first_snapshot','repeat_snapshot','standalone_snapshot']:
            ref=row[field]
            if ref.get('anchor')!='dictionary_reuse_directory' or not safe(ref.get('path')):raise ValueError('Unsafe returned reuse snapshot')
            name='dictionary_reuse/'+ref['path'];data=members[name]
            if len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Reuse snapshot reference differs')
            prefix=PurePosixPath(name).parent.as_posix()+'/'
            folder=output/'captured'/code/field
            for n,d in members.items():
                if n.startswith(prefix):
                    relative=n.removeprefix(prefix)
                    if not safe(relative):raise ValueError('Unsafe returned entry member')
                    path=folder/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(d)
            loaded.append(resolve_dictionary_snapshot(folder))
        first=loaded[0]
        if any(e['entry_id']!=first['entry_id'] or e['dictionary'].read_bytes()!=first['dictionary'].read_bytes() for e in loaded):
            raise ValueError('Returned reuse entries differ')
        for kind,key in [('source','source'),('numerical','dictionary')]:
            ref=report['source_resources'][code][kind]
            if ref.get('anchor')!='input_capsule' or not safe(ref.get('path')):raise ValueError('Unsafe reuse source reference')
            data=members['inputs/review/'+ref['path']]
            if len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256'] or data!=first[key].read_bytes():
                raise ValueError('Reuse source binding differs')
        request=first['manifest']['request']
        resources[code]={'source':first['source'],'numerical':first['dictionary'],
            'qualification':first['qualification'],'provenance':first['provenance'],
            'consumer':first['manifest']['consumer'],**{k:request[k] for k in ['source_authority','recipe','generator']}}
    actual=exercise_dictionary_reuse(resources,output/'owned_store',output/'replayed')
    if {k:v for k,v in actual.items() if k!='persistent_store_location'}!={k:v for k,v in expected.items() if k!='persistent_store_location'}:
        raise ValueError('Maintained C66 controls differ')
    files={p.relative_to(output/'replayed').as_posix():p for p in (output/'replayed').rglob('*') if p.is_file()}
    if set(files)!={n.removeprefix('dictionary_reuse/') for n in members if n.startswith('dictionary_reuse/')}:
        raise ValueError('Maintained reuse inventory differs')
    for name,path in files.items():
        if name!='dictionary_reuse.json' and path.read_bytes()!=members['dictionary_reuse/'+name]:raise ValueError('Maintained reuse payload differs')
    return True
