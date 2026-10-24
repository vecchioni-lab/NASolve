"""Ordinary PostMR acquisition of exact-source, current-consumer component numerics.

Source chemistry remains authoritative for construction. This read-only cache
adapter supplies independently frozen numerical inputs for ordinary ReadySet;
it neither generates a dictionary nor certifies a new linked site or model.
"""
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re

POLICY_ID = 'cif-postmr-dictionary-reuse-v1'
REPAIR_POLICY = 'cif-source-native-complete-candidate-v1'
_API = ('iotbx/phil.py','mmtbx/command_line/pdb_interpretation.py',
    'mmtbx/monomer_library/server.py','mmtbx/monomer_library/pdb_interpretation.py',
    'cctbx/geometry_restraints/linking_class.py','cctbx/geometry_restraints/auto_linking_types.py',
    'mmtbx/secondary_structure/__init__.py','mmtbx/secondary_structure/nucleic_acids.py')
_ENERGY = tuple('cctbx/geometry_restraints/'+n+'.py' for n in ('flags','energies','manager'))


def _need(value, message):
    if not value: raise ValueError(message)


def _ref(path, root):
    data = path.read_bytes()
    return {'anchor':'postmr_dictionary_directory','path':path.relative_to(root).as_posix(),
            'sha256':sha256(data).hexdigest(),'size':len(data)}


def _entries(store, source, code, authority, notes):
    """Enumerate the declared store index, never search for scientific inputs."""
    from .cif_dictionary_store import _read_entry, _json, make_dictionary_request
    directory = Path(store).expanduser().absolute()/'entries'
    if any(p.is_symlink() for p in [directory,directory.parent]) or not directory.is_dir(): return []
    groups = sorted(directory.iterdir())
    _need(len(groups) <= 4096, 'Dictionary-store request index exceeds the bounded scan')
    result = []; data = source.read_bytes(); digest = sha256(data).hexdigest()
    for group in groups:
        if group.is_symlink() or not group.is_dir() or not re.fullmatch('[0-9a-f]{64}',group.name): continue
        children = sorted(group.iterdir())
        _need(len(children) <= 64, 'Dictionary-store request has too many entries')
        for child in children:
            try:
                path = child/'manifest.json'
                _need(not child.is_symlink() and not path.is_symlink(), 'Symlinked dictionary entry')
                manifest = _json(path.read_bytes()); req = manifest['request']
                if (req['component'] != code or req['source_authority'] != authority
                        or req['source_sha256'] != digest or req['source_size'] != len(data)): continue
                if (req['recipe'].get('policy_id') != REPAIR_POLICY
                        or req['recipe'].get('source_metadata_policy') != 'cif-source-declared-dna-metadata-v1'
                        or req['generator'].get('name') != 'Phenix eLBOW'):
                    notes.append('A saved repair uses a different recipe/backend; ordinary preparation is retained.'); continue
                fresh = make_dictionary_request(source,code,**{k:req[k] for k in ['source_authority','recipe','generator']})
                _need(fresh == req, 'Saved request no longer binds the selected chemistry')
                entry = _read_entry(child,child.name,fresh)
                _need(manifest['request_key'] == group.name, 'Dictionary entry is outside its request index')
                _need(entry['qualification_current'], 'Saved native policy requires requalification')
                result.append(entry)
            except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
                notes.append('A saved entry is unavailable for reuse: '+str(exc))
    return result


def verify_current_consumer(installation, ready_set_executable, consumer):
    """Bind a saved qualification to the selected live dispatcher and source files.

    Discovery supplies a fresh version. Exact implementation hashes are read
    from the configured installation, not imported from ambient Python. Energy
    library data and new site/model interpretation remain separate checks.
    """
    root = Path(installation.root).resolve(strict=True)
    _need(consumer.get('name') == 'Phenix/CCTBX' and installation.version not in {'','unknown'}
        and installation.version == consumer.get('version'), 'Current Phenix version differs or is unknown')
    ready = Path(ready_set_executable).resolve(strict=True)
    _need(Path(installation.executables['phenix.ready_set']).resolve(strict=True) == ready
          and ready.is_relative_to(root), 'Configured ReadySet differs from the selected consumer')
    executable = Path(installation.executables['phenix.python']).resolve(strict=True)
    _need(executable.is_relative_to(root) and sha256(executable.read_bytes()).hexdigest() == consumer['executable_sha256'],
          'Current native dispatcher differs')
    for field, required in [('api_sources',_API),('energy_sources',_ENERGY)]:
        rows = consumer[field]
        _need(len(rows) == len(required) and len({r['path'] for r in rows}) == len(required), 'Incomplete native implementation identity')
        suffixes = set()
        for ref in rows:
            relative = ref['path']; parts = PurePosixPath(relative)
            _need(ref.get('anchor') == 'phenix_installation' and isinstance(relative,str)
                  and not parts.is_absolute() and '\\' not in relative and ':' not in relative
                  and not any(p in {'','.','..'} for p in relative.split('/')), 'Unsafe native implementation anchor')
            matched = [name for name in required if relative.endswith('/site-packages/'+name)]
            _need(len(matched) == 1, 'Unexpected native implementation scope')
            suffixes.add(matched[0]); path = root/relative
            _need(not path.is_symlink() and path.resolve(strict=True).is_relative_to(root)
                  and sha256(path.read_bytes()).hexdigest() == ref['sha256'], 'Current native implementation differs')
        _need(suffixes == set(required), 'Native implementation scope is incomplete')
    return True


def prepare_postmr_dictionaries(codes, ready_set_executable, output, *, data_root=None,
                                 store_root=None, environment=None, installation=None):
    """Freeze ordinary sources and reuse eligible cached numerics before ReadySet.

    Cache absence, corruption or an unverified/changed consumer retains ordinary
    source preparation with notes. Missing curated sources retain their existing
    hard failure. This adapter never regenerates or rewrites a cache entry.
    """
    from .curated_ligands import ligand_source, validate_ligand_dictionary
    from .cif_dictionary_store import default_dictionary_store
    from .cif_source_reuse import resolve_ordinary_dictionary, read_ordinary_dictionary
    from .phenix_runtime import installation_from_candidate
    codes = list(codes)
    _need(len(codes) <= 64 and len(set(codes)) == len(codes)
          and all(isinstance(c,str) and re.fullmatch('[A-Za-z0-9]{1,3}',c) for c in codes), 'Invalid ordinary component selection')
    output = Path(output).absolute()
    _need(not output.exists() and not output.is_symlink() and not any(p.is_symlink() for p in output.parents), 'Unsafe or existing dictionary output')
    # Resolve every ordinary source before writing or consulting the cache.
    sources = {c:ligand_source(c,data_root,ready_set_executable=ready_set_executable) for c in codes}
    for c,s in sources.items(): validate_ligand_dictionary(c,s.path)
    output.mkdir(parents=True)
    store = default_dictionary_store(environ=environment) if store_root is None else store_root
    report = {'schema_version':1,'policy_id':POLICY_ID,'components':{},'requires_cif_review':False,
              'scope':'COMPONENT_NUMERICS_FOR_ORDINARY_PREPARATION; CURRENT_LINKS_AND_MODEL_CHECKS_REMAIN_REQUIRED',
              'dictionary_generation':'NOT_RUN','model_optimization':'NOT_RUN',
              'native_interpretation':'NOT_RUN','current_installation_discovery':'NOT_NEEDED',
              'energy_library_resource_files':'NOT_CAPTURED; CURRENT_SITE_NATIVE_CHECKS_REMAIN_REQUIRED'}
    discovered = installation; discovery_attempted = installation is not None; discovery_error = None
    for code, selected in sources.items():
        folder = output/code; folder.mkdir(); original = selected.path.read_bytes()
        source = folder/'source.cif'; source.write_bytes(original)
        row = {'status':'ORDINARY_SOURCE_FALLBACK','source_authority':selected.authority,'source_kind':selected.kind,
               'source':_ref(source,output),'dictionary':_ref(source,output),'numerics':None,'notes':[],
               'requalification':'NOT_REQUESTED','requires_cif_review':False,
               'linked_context':'REQUALIFY_FOR_CURRENT_SITE','model_geometry':'ASSESS_FOR_NEW_MODEL'}
        report['components'][code] = row
        try:
            entries = _entries(store,source,code,selected.authority,row['notes'])
            if entries and not discovery_attempted:
                discovery_attempted = True
                try: discovered = installation_from_candidate(ready_set_executable,base_environment=environment)
                except (OSError,ValueError,RuntimeError,KeyError) as exc: discovery_error = str(exc)
            if entries and discovered is None: raise ValueError('Current installation is unavailable: '+str(discovery_error))
            usable = []
            for entry in entries:
                try:
                    verify_current_consumer(discovered,ready_set_executable,entry['manifest']['consumer'])
                    usable.append(entry)
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    row['requalification'] = 'REQUIRED_BEFORE_CACHE_USE'
                    row['notes'].append('Saved numerics need current native requalification: '+str(exc))
            if usable:
                from .cif_doctor_selection import ComponentCandidate, select_component_candidate
                candidates = [ComponentCandidate(e['entry_id'],code,0,e['qualification']['candidate_sha256'],
                    sha256(original).hexdigest(),True,True,True,True,True,
                    e['qualification']['source_assessment']['finished_stereo']['stereochemistry'],
                    converged=e['provenance']['converged'],warnings=tuple(e['provenance']['notes'])) for e in usable]
                decision = select_component_candidate(candidates)
                entry = next(e for e in usable if e['entry_id'] == decision['selected_candidate'])
                req = entry['manifest']['request']; consumer = entry['manifest']['consumer']
                result = resolve_ordinary_dictionary(code,ready_set_executable,store,folder/'resolved',
                    data_root=data_root,consumer=consumer,**{k:req[k] for k in ['recipe','generator']})
                frozen = read_ordinary_dictionary(folder/'resolved')
                _need(result['status'] == 'REUSED' and frozen['source'].read_bytes() == original, 'Cache/source selection changed during acquisition')
                verify_current_consumer(discovered,ready_set_executable,consumer)
                row.update(status='REUSED',dictionary=_ref(frozen['dictionary'],output),
                    numerics=_ref(folder/'resolved/numerics/resolution.json',output),
                    converged=result['converged'],stopping=result['stopping'],notes=result['notes'],
                    current_consumer='VERSION_DISPATCHER_AND_ALL_ELEVEN_IMPLEMENTATION_SOURCES_VERIFIED',
                    requalification='NOT_NEEDED_FOR_MATCHING_ISOLATED_CONSUMER')
        except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError) as exc:
            row['requalification'] = 'REQUIRED_BEFORE_CACHE_USE'
            row['notes'].append('Ordinary source preparation retained: '+str(exc))
        _need(selected.path.read_bytes() == original and source.read_bytes() == original, 'Ordinary source changed during cache acquisition')
    if discovery_attempted: report['current_installation_discovery'] = 'CALLER_SELECTED_INSTALLATION' if installation is not None else 'FRESH_VERSION_DISCOVERY'
    report['status'] = 'POSTMR_DICTIONARIES_PREPARED_WITH_CACHE' if any(r['status']=='REUSED' for r in report['components'].values()) else 'ORDINARY_SOURCES_PREPARED'
    (output/'postmr_dictionaries.json').write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    read_postmr_dictionaries(output)
    return report


def read_postmr_dictionaries(output):
    """Resolve independent run copies without the installation or shared cache."""
    from .cif_source_reuse import read_ordinary_dictionary
    root = Path(output)
    _need(root.is_dir() and not root.is_symlink(), 'Unsafe PostMR dictionary directory')
    path = root/'postmr_dictionaries.json'
    _need(not path.is_symlink(), 'Unsafe PostMR dictionary report')
    report = json.loads(path.read_bytes())
    _need(report['policy_id'] == POLICY_ID and report['schema_version'] == 1 and report['requires_cif_review'] is False, 'PostMR dictionary policy differs')
    result = {}
    for code,row in report['components'].items():
        _need(re.fullmatch('[A-Za-z0-9]{1,3}',code) and row['requires_cif_review'] is False
              and row['linked_context'] == 'REQUALIFY_FOR_CURRENT_SITE' and row['model_geometry'] == 'ASSESS_FOR_NEW_MODEL', 'PostMR component scope differs')
        def resolve(ref):
            relative = ref['path']
            _need(isinstance(relative,str) and relative.startswith(code+'/') and '\\' not in relative
                  and ':' not in relative and not any(p in {'','.','..'} for p in relative.split('/')), 'Unsafe PostMR dictionary reference')
            p = root/relative
            _need(not any(v.is_symlink() for v in [p,*p.parents]) and _ref(p,root) == ref, 'PostMR dictionary artifact differs')
            return p
        source,dictionary = resolve(row['source']),resolve(row['dictionary']); numerics = None
        _need(row['source']['path'] == code+'/source.cif', 'Ordinary source reference differs')
        if row['status'] == 'REUSED':
            frozen = read_ordinary_dictionary(root/code/'resolved'); numerics = frozen['numerics']
            _need(resolve(row['numerics']) == root/code/'resolved/numerics/resolution.json'
                  and frozen['report']['source']['authority'] == row['source_authority']
                  and frozen['source'].read_bytes() == source.read_bytes() and frozen['dictionary'] == dictionary
                  and frozen['report']['converged'] is row['converged'] and frozen['report']['stopping'] == row['stopping']
                  and frozen['report']['notes'] == row['notes'], 'PostMR reuse binding differs')
        else:
            _need(row['status'] == 'ORDINARY_SOURCE_FALLBACK' and dictionary == source and row['numerics'] is None, 'PostMR fallback binding differs')
        result[code] = {'source':source,'dictionary':dictionary,'numerics':numerics,'report':row}
    return result
