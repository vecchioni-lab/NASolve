"""Explicit frozen one-or-more-component acquisition/preparation/repair requests.

No source rediscovery, automatic retry, ordinary adoption or chemistry policy is
implemented here. Existing child owners and scientific readers remain authoritative.
"""
from copy import deepcopy
import json
import math
from pathlib import Path
from time import monotonic
import uuid

from .failure_reporting import add_failure_note
from .campaign_process import CampaignProcessError, coordinator_alive, current_process_identity, exclusive_lock
from .campaign_records import _sync_directory, now, path_in, read_record, write_record
from . import cif_acquisition_attempt as acquisition
from . import cif_component_runtime as frozen_tree
from . import cif_repair_attempt as repair
from .cif_acquisition_preparation import _capture, _freeze, _terminal, prepare_acquired_dictionary_bundle, read_acquired_dictionary_bundle
from .cif_acquisition_sources import read_acquisition_sources
from .cif_component_runtime import _tree
from .cif_dictionary_bundle import _context
from .cif_dictionary_sites import _consumer, _links, _model_inventory, _need, _read, _safe
from .cif_dictionary_store import _bytes, _json, make_dictionary_request, recipe_representation_policy, resolve_dictionary_snapshot
from .cif_generation_acquisition import generation_dictionary_options
from .cif_generation_attempt import _attempt_identity
from .cif_generation_process import _valid_identity
from .cif_postmr_cache import verify_current_consumer
from .cif_repair_attempt import _root, _members, _inventory
from .cif_repair_process import _uuid
from .cif_runtime_bundle import resolve_runtime_bundle
from .cif_model_context import validate_prepared_model_context
from .postmr_lineage import read_postmr_construction, POLICY_ID as CONSTRUCTION_POLICY
from .cif_restraint_context import validate_restraint_context
from .cif_literal_na_inputs import resolve_literal_na_inputs
from .cif_explicit_na_policy import read_explicit_na_policy
from . import cif_runtime_continuation as continuation
from .cif_runtime_continuation_process import inspect_runtime_continuation_processes, POLICY_ID as CONTINUATION_PROCESS_POLICY

POLICY_ID = 'cif-complete-dictionary-request-v1'
ANCHOR = 'dictionary_request_directory'
_COMPILER_INPUTS = {'literal_na_inputs':'literal_na', 'explicit_na_policy':'explicit_na'}
_LIMITS = dict(native_timeout_seconds=600, component_timeout_seconds=3600,
               attribution_timeout_seconds=300, derivative_timeout_seconds=600,
               total_timeout_seconds=3600)
_STOPPED = {'STOPPED', 'STOPPED_UNFINISHED', 'NOT_CREATED'}
_OUTCOMES = {'NO_SUPPORTED_GRAPH_REPAIR; BUNDLE_USABILITY_NOT_ASSESSED',
             'SOURCE_PREPARATION_UNQUALIFIED', 'NO_USABLE_BUNDLE', 'QUALIFIED_DIAGNOSTIC_RUNTIME'}


def _same(left, right):
    return _bytes(left) == _bytes(right)


def _component_config(source, code, authority, consumer, declaration, retained, limits, maximum):
    inputs = {'source.cif': _read(source)}
    if retained is not None:
        saved = resolve_dictionary_snapshot(retained); tree = _tree(retained)
        _need(set(tree) == acquisition._SNAPSHOT_FILES, 'Unexpected retained snapshot members')
        prior = saved['manifest']['request']
        _need(make_dictionary_request(source, code, source_authority=authority,
            **{k:prior[k] for k in ('recipe','generator')}) == prior
            and recipe_representation_policy(prior['recipe']) == recipe_representation_policy(declaration['options']['recipe']),
            'Retained source/authority/representation permission differs')
        inputs.update({'retained/'+n:data for n,data in tree.items()})
    return acquisition._configuration(source, code, authority, declaration['options'], consumer,
        declaration['binding'], inputs, dict(native_timeout_seconds=limits['native_timeout_seconds'],
        total_timeout_seconds=limits['component_timeout_seconds']), maximum)


def _continuation_fields(options, limits):
    if options is None: return {}
    fields = {'readyset_timeout_seconds','restore_serialization'}
    policies = dict(execution_policy=continuation.POLICY_ID, process_policy=CONTINUATION_PROCESS_POLICY,
                    artifact_policy='cif-complete-continuation-artifacts-v1')
    _need(isinstance(options,dict) and set(options) in (fields,fields | policies.keys()),
          'Invalid complete-request continuation settings')
    _need(all(options.get(k,v) == v for k,v in policies.items()), 'Unsupported continuation policy')
    continuation._configuration(dict(native=limits['native_timeout_seconds'],
        readyset=options['readyset_timeout_seconds'],total=limits['total_timeout_seconds']),options['restore_serialization'])
    return dict(continuation=dict(**policies,**{k:options[k] for k in sorted(fields)}))


def _continuation_parameters(config):
    settings = config['continuation']; limits = config['limits']
    return dict(native_timeout_seconds=limits['native_timeout_seconds'],
        readyset_timeout_seconds=settings['readyset_timeout_seconds'],
        total_timeout_seconds=limits['total_timeout_seconds'],restore_serialization=settings['restore_serialization'])


def _compiler_input(kind, directory, selected_sources=None):
    """Resolve an existing compiler artifact; never compile or guess new intent."""
    if kind == 'literal_na_inputs':
        result=resolve_literal_na_inputs(directory)
        if selected_sources is not None:
            for code,ref in result['report'].get('source_components',{}).items():
                if code in selected_sources:
                    _need(_read(Path(directory)/ref['path'])==_read(selected_sources[code]['source']),
                          'Literal compiler source differs from selected acquisition source: '+code)
        return result
    _need(kind == 'explicit_na_policy', 'Unsupported compiler input kind')
    root = Path(directory); report = read_explicit_na_policy(root)
    if selected_sources is not None:
        for code, ref in report['inputs']['sources'].items():
            if code in selected_sources:
                _need(_read(root/ref['path']) == _read(selected_sources[code]['source']),
                      'Explicit compiler source differs from selected acquisition source: '+code)
    return dict(report=report,model=root/report['inputs']['model']['path'],
                phils=[root/report['compiled_phil']['path']])


def _compiler_references(literal_na_inputs, explicit_na_policy):
    chosen = {name:value for name,value in [('literal_na_inputs',literal_na_inputs),
              ('explicit_na_policy',explicit_na_policy)] if value is not None}
    _need(len(chosen) <= 1, 'Require at most one compiler provenance mode')
    return chosen


def _construction_input(directory, model, sources, model_context):
    value = read_postmr_construction(directory)
    _need(model_context is not None and _read(value['model']) == _read(model),
          'Construction lineage differs from the exact prepared model')
    controls = value['report']['controls']; plan = model_context['intent']['post_mr_plan']
    _need(controls['allow_op3_sites'] == sorted(plan['allow_op3_sites'])
          and controls['passthrough_sites'] == sorted(plan['backbone_policy']['experimental_passthrough_sites']),
          'Construction lineage differs from prepared phosphate/backbone intent')
    for code,path in value['dictionaries'].items():
        if code in sources:
            _need(_read(path) == _read(sources[code]['source']),
                  'Construction dictionary differs from selected acquisition source: '+code)
    return value


def _configuration(inputs, controls, limits, maximum, *, qualify_no_repair=False, optional_failure_policy=None, model_context=None, restraint_context=None, continuation_options=None, literal_na_inputs=None, explicit_na_policy=None, construction_inputs=None):
    _need(type(qualify_no_repair) is bool, "Require a boolean no-repair qualification mode")
    _need(set(limits) == set(_LIMITS) and all(type(v) is int and 1 <= v <= _LIMITS[k] for k,v in limits.items()),
          'Require bounded integer complete-request limits')
    _need(type(maximum) is int and 1 <= maximum <= 5, 'Require one to five outer attempts')
    _need(isinstance(controls,dict) and set(controls) == {'sites','consumer','expected_links','native_context','supplementary_phils'},
          'Unexpected complete-request controls')
    _consumer(controls['consumer']); _context(controls['native_context'])
    selected = read_acquisition_sources(inputs/'sources'); codes = selected['report']['components']
    _need(1 <= len(codes) <= 16 and isinstance(controls['sites'],dict) and set(controls['sites']) == set(codes),
          'Require complete selected component coverage')
    names = controls['supplementary_phils']
    _need(isinstance(names,list) and names == [f'phils/{i:03}.phil' for i in range(len(names))], 'Invalid shared PHIL order')
    allowed = {'model.pdb', *names, *('sources/'+n for n in _tree(inputs/'sources'))}
    model_sites = _model_inventory(inputs/'model.pdb'); all_contexts = []; components = {}
    for code in codes:
        site = controls['sites'][code]
        _need(isinstance(site,dict) and set(site) == {'contexts','generation','retained','terminal_resource','phosphate_atom_policy'},
              'Unexpected complete component declaration')
        contexts = site['contexts']
        _need(isinstance(contexts,list) and contexts and all(isinstance(c,dict) and isinstance(c.get('site'),str) for c in contexts)
              and len({c['site'] for c in contexts}) == len(contexts)
              and {c['site'] for c in contexts} == {s for s,r in model_sites.items() if r['code'] == code},
              'Require each selected model site exactly once')
        all_contexts.extend(contexts)
        _need(site['retained'] in (None, f'retained/{code}'), 'Invalid retained reference')
        retained = inputs/site['retained'] if site['retained'] is not None else None
        if retained is not None: allowed.update(f'retained/{code}/'+n for n in _tree(retained))
        generation = site['generation']
        _need(isinstance(generation,dict) and set(generation) == {'options','binding'}, 'Invalid generation declaration')
        choice = selected['sources'][code]
        components[code] = _component_config(choice['source'],code,choice['source_authority'],controls['consumer'],generation,retained,limits,maximum)
        resource = site['terminal_resource']
        if resource is not None:
            _need(_safe(resource) and resource.startswith(f'resources/{code}/') and len(resource.split('/')) == 3,
                  'Invalid terminal resource reference')
            allowed.update(f'resources/{code}/'+n for n in _terminal(inputs/resource,controls['consumer']))
    _need(_same(_links(inputs/'model.pdb',all_contexts,controls['expected_links']), controls['expected_links']), 'Model links differ')
    if model_context is not None:
        derived = validate_prepared_model_context(inputs/'model.pdb', model_context)
        if restraint_context is None:
            _need(not names and controls['native_context']['custom_restraints'] == 'absent',
                  'Prepared-model bridge requires explicit ownership for supplementary PHIL')
        _need(derived['components'] == codes
              and _same(derived['contexts'], {code: controls['sites'][code]['contexts'] for code in codes})
              and _same(derived['expected_links'], controls['expected_links']),
              'Complete request differs from derived model context')
    if restraint_context is not None:
        _need(model_context is not None and controls['native_context']['custom_restraints'] == 'required',
              'Explicit restraint ownership requires model context and required custom restraints')
        validate_restraint_context(inputs/'model.pdb', [inputs/n for n in names], restraint_context)
    compiler_refs = _compiler_references(literal_na_inputs,explicit_na_policy)
    for kind,reference in compiler_refs.items():
        folder = _COMPILER_INPUTS[kind]
        compiled = _compiler_input(kind,inputs/folder,selected['sources'])
        _need(reference == dict(anchor=ANCHOR,path='inputs/'+folder,policy_id=compiled['report']['policy_id'])
              and model_context is not None and restraint_context is not None,
              'Compiler provenance requires both owned contexts and its exact reference')
        _need(_read(compiled['model']) == _read(inputs/'model.pdb')
              and [_read(p) for p in compiled['phils']] == [_read(inputs/n) for n in names],
              'Compiler provenance differs from owned model or ordered restraints')
        if kind == 'literal_na_inputs':
            _need(_same(compiled['report']['restraint_context'],restraint_context),
                  'Literal compiler context differs from owned restraints')
        allowed.update(folder+'/'+n for n in _tree(inputs/folder))
    construction_ref = {}
    if construction_inputs is not None:
        reference = dict(anchor=ANCHOR,path='inputs/construction',policy_id=CONSTRUCTION_POLICY)
        _need(construction_inputs == reference, 'Invalid construction lineage reference')
        bound = _construction_input(inputs/'construction',inputs/'model.pdb',selected['sources'],model_context)
        allowed.update('construction/'+name for name in bound['files'])
        construction_ref['construction_inputs'] = reference
    files, directories = _capture(inputs)
    _need(set(files) == allowed, 'Unrequested complete-request input')
    expected_dirs = {str(p) for name in files for p in Path(name).parents if str(p) != '.'}
    _need(set(directories) == expected_dirs, 'Unrequested complete-request directory')
    return _json(_bytes(dict(controls=controls,limits=limits,max_attempts=maximum,components=components,
        input_files=_inventory(files),input_directories=directories,
        **({'model_context':model_context} if model_context is not None else {}),
        **({'restraint_context':restraint_context} if restraint_context is not None else {}),
        **compiler_refs, **construction_ref,
        **({'qualify_no_repair':True} if qualify_no_repair else {}),**repair.failure_policy_fields(optional_failure_policy),
        **_continuation_fields(continuation_options,limits))))


def _request(root):
    r = read_record(path_in(root,'request.json'))
    _need(set(r) == {'schema_version','policy_id','request_id','created_utc','inputs','configuration','record_sha256'}
          and type(r['schema_version']) is int and r['schema_version'] == 1 and r['policy_id'] == POLICY_ID
          and _uuid(r['request_id']) and r['inputs'] == dict(anchor=ANCHOR,path='inputs'), 'Invalid complete request')
    c = r['configuration']
    expected = _configuration(root/'inputs',c['controls'],c['limits'],c['max_attempts'],qualify_no_repair=c.get('qualify_no_repair',False),optional_failure_policy=c.get('optional_failure_policy'),model_context=c.get('model_context'),restraint_context=c.get('restraint_context'),continuation_options=c.get('continuation'),literal_na_inputs=c.get('literal_na_inputs'),explicit_na_policy=c.get('explicit_na_policy'),construction_inputs=c.get('construction_inputs'))
    _need(_same(c,expected), 'Frozen complete request changed')
    return r


def initialize_dictionary_request(source_selection, components, model, output, *, consumer,
        expected_links, native_context, supplementary_phils=(), native_timeout_seconds=90,
        component_timeout_seconds=600, attribution_timeout_seconds=90,
        derivative_timeout_seconds=300, total_timeout_seconds=900, max_attempts=2, qualify_no_repair=True, optional_failure_policy=repair.FALLBACK_POLICY_ID, model_context=None, restraint_context=None, continuation_options=None, literal_na_inputs=None, explicit_na_policy=None, construction_inputs=None):
    """Freeze all declared inputs before children exist. Require a fresh destination.

    One to sixteen component types declare code, contexts and generation settings, with optional
    retained_snapshot, terminal_resource and phosphate_atom_policy. Runtime SDK
    roots/environment are not saved as operational paths; execution supplies and
    revalidates them against the frozen recipe/pins/relative dispatchers. New
    requests independently qualify a no-repair original by default; historical
    requests without that frozen mode retain their original no-op behavior.
    An optional prepared-model context is rederived from frozen model/intent;
    supplementary PHIL additionally requires a frozen explicit restraint context.
    Its bounded grammar keeps the composer as the only site-modifier owner.
    New requests require parenthesized atom-name alternatives; historical reads
    preserve their frozen meaning but ambiguous records cannot start new attempts.
    Optional literal_na_inputs freezes original native/PHIL/compiler provenance
    and must reproduce the exact supplied model and ordered compiled PHIL.
    Alternatively explicit_na_policy retains an existing source-bound C80 artifact;
    overlapping source components must match the chosen acquisition bytes.
    The two provenance modes are mutually exclusive and never reselect relationships.
    Optional continuation_options freezes ReadySet timeout and lossless-serialization
    intent; the same outer attempt owns that child and its remaining allowance.
    Optional construction_inputs names an ordinary run carrying a C196 construction
    record. Freeze only its explicitly declared artifacts, never the whole run.
    Exact model, overlapping source bytes and site policy must match the request;
    this lineage is not scientific qualification and does not select a checkpoint.
    Omission preserves historical requests and results exactly.
    """
    root = _root(output)
    if root.exists(): raise FileExistsError(root)
    selected = read_acquisition_sources(source_selection); codes = selected['report']['components']
    _need(isinstance(components,(list,tuple)) and len(components) == len(codes), 'Incomplete component declarations')
    trees = {'sources':_root(source_selection)}; originals = {Path(model):_read(model)}
    files = {'model.pdb':originals[Path(model)]}; sites = {}; directories = set()
    compiler_refs = {}
    for kind,value in _compiler_references(literal_na_inputs,explicit_na_policy).items():
        folder = _COMPILER_INPUTS[kind]
        trees[folder] = _root(value)
        compiled = _compiler_input(kind,trees[folder],selected['sources'])
        compiler_refs[kind] = dict(anchor=ANCHOR,path='inputs/'+folder,policy_id=compiled['report']['policy_id'])
    for item in components:
        _need(isinstance(item,dict) and {'code','contexts','generation'} <= item.keys()
            and item.keys() <= {'code','contexts','generation','retained_snapshot','terminal_resource','phosphate_atom_policy'},
            'Unexpected component declaration')
        code = item['code']; _need(code in codes and code not in sites, 'Duplicate or unselected component')
        generation = item['generation']; retained = item.get('retained_snapshot'); resource = item.get('terminal_resource')
        if retained is not None: trees[f'retained/{code}'] = _root(retained)
        relative = None
        if resource is not None:
            resource = Path(resource); relative = f'resources/{code}/{resource.name}'
            data = _terminal(resource,consumer); files.update({f'resources/{code}/'+n:b for n,b in data.items()})
            originals.update({resource.parent/n:b for n,b in data.items()})
        sites[code] = dict(contexts=item['contexts'],generation=dict(options=generation_dictionary_options(generation),
            binding=acquisition._generation_binding(generation)),retained=None if retained is None else f'retained/{code}',
            terminal_resource=relative,phosphate_atom_policy=item.get('phosphate_atom_policy'))
    controls = _json(_bytes(dict(sites=sites,consumer=consumer,expected_links=expected_links,native_context=native_context,
        supplementary_phils=[f'phils/{i:03}.phil' for i in range(len(supplementary_phils))])))
    limits = dict(native_timeout_seconds=native_timeout_seconds,component_timeout_seconds=component_timeout_seconds,
        attribution_timeout_seconds=attribution_timeout_seconds,derivative_timeout_seconds=derivative_timeout_seconds,
        total_timeout_seconds=total_timeout_seconds)
    for i,p in enumerate(supplementary_phils): originals[Path(p)] = _read(p); files[f'phils/{i:03}.phil'] = originals[Path(p)]
    construction_ref = None
    if construction_inputs is not None:
        source_root = _root(construction_inputs)
        bound = _construction_input(source_root,model,selected['sources'],model_context)
        files.update({'construction/'+n:b for n,b in bound['files'].items()})
        originals.update({source_root/n:b for n,b in bound['files'].items()})
        directories.update(str(p) for n in bound['files'] for p in (Path('construction')/n).parents if str(p) != '.')
        construction_ref = dict(anchor=ANCHOR,path='inputs/construction',policy_id=CONSTRUCTION_POLICY)
    captured = {}
    for name,p in trees.items():
        _need(not p.is_relative_to(root) and not root.is_relative_to(p), 'Complete request overlaps input tree')
        captured[name] = _capture(p); tree,dirs = captured[name]
        files.update({name+'/'+n:b for n,b in tree.items()}); directories.update([name,*[name+'/'+n for n in dirs]])
    _need(all(not p.resolve().is_relative_to(root) for p in originals), 'Complete request overlaps input file')
    def unchanged():
        _need(all(_capture(p) == captured[name] for name,p in trees.items())
              and all(_read(p) == b for p,b in originals.items()), 'Complete request source changed while freezing')
    if restraint_context is not None:
        validate_restraint_context(model, supplementary_phils, restraint_context, require_scoped_names=True)
    unchanged(); root.mkdir(parents=True,exist_ok=False); _sync_directory(root.parent)
    _freeze(root/'inputs',files,sorted(directories))
    config = _configuration(root/'inputs',controls,limits,max_attempts,qualify_no_repair=qualify_no_repair,optional_failure_policy=optional_failure_policy,model_context=model_context,restraint_context=restraint_context,continuation_options=continuation_options,construction_inputs=construction_ref,**compiler_refs); unchanged()
    r = write_record(root/'request.json',dict(schema_version=1,policy_id=POLICY_ID,request_id=str(uuid.uuid4()),
        created_utc=now(),inputs=dict(anchor=ANCHOR,path='inputs'),configuration=config))
    _request(root)
    return r


def _intent(attempt, number, request):
    r = read_record(attempt/'attempt.json')
    _need(set(r) == {'request_sha256','number','attempt_id','coordinator','created_utc','record_sha256'}
        and r['request_sha256'] == request['record_sha256'] and type(r['number']) is int and r['number'] == number
        and _uuid(r['attempt_id']) and _valid_identity(r['coordinator']), 'Invalid outer attempt intent')
    return r


def _owned_identity(parent, coordinator, intent):
    _need(parent == _attempt_identity(intent)
        and all(coordinator.get(k) == intent['coordinator'].get(k) for k in ('pid','pgid','host','boot_id','start_marker')),
        'Child belongs to another outer attempt or coordinator')


def _owned(child, intent):
    r = child['intent']; _owned_identity(r.get('parent_attempt'),r['coordinator'],intent)


def _continuation_child(attempt, intent, config, repaired):
    work = path_in(attempt,'continuation')
    if not work.exists(): return dict(state='NOT_CREATED',activity=False),None
    state = inspect_runtime_continuation_processes(work); header = state.get('header')
    if header is None:
        # A reserved directory without its header cannot prove no worker launched.
        return dict(state='UNKNOWN',activity=None),None
    _owned_identity(header.get('attempt_owner'),header['coordinator'],intent)
    _need(repaired['state'] == 'STOPPED' and repaired['finished']['outcome'] == 'RETURNED',
          'Continuation requires the completed selected repair child')
    execution = attempt/'repair/attempts/attempt-0001/execution'
    _need(_json(_read(execution/'repair_execution.json'))['status'] == 'QUALIFIED_DIAGNOSTIC_RUNTIME'
          and _tree(work/'inputs/runtime') == _tree(execution/'runtime'),
          'Continuation did not freeze the exact selected repair result')
    params = _continuation_parameters(config)
    expected = continuation._configuration(dict(native=params['native_timeout_seconds'],
        readyset=params['readyset_timeout_seconds'],total=params['total_timeout_seconds']),params['restore_serialization'])
    _need(_same(_json(_read(work/'inputs/configuration.json')),expected), 'Continuation limits differ from frozen outer intent')
    for phase,evidence in state['phases'].items():
        if 'job' in evidence:
            limit = params['readyset_timeout_seconds' if phase == 'readyset' else 'native_timeout_seconds']
            _need(evidence['job']['timeout_seconds'] <= limit, 'Continuation worker exceeded frozen limit')
    return state,dict(header=header['record_sha256'],finished=state.get('finished',{}).get('record_sha256'))


def _binding(request, child):
    return dict(request_sha256=request['record_sha256'],number=child['number'],attempt_sha256=child['intent']['record_sha256'],
        attempt_id=child['intent']['attempt_id'],finished_sha256=child.get('finished',{}).get('record_sha256'))


def _children(root, attempt, intent, config, closed=None):
    states = {}; bindings = {}; identity = _attempt_identity(intent)
    for code, expected in config['components'].items():
        state = acquisition.inspect_acquisition_request(root/'acquisitions'/code)
        child = None; unknown = state['state'] not in {'NOT_RECORDED','RECORDED'}
        if state['state'] == 'RECORDED':
            _need(_same(state['request']['configuration'],expected), 'Component request differs from frozen outer intent')
            rows = [r for r in state['attempts'] if r.get('intent',{}).get('parent_attempt') == identity]
            _need(len(rows) <= 1, 'Multiple component children under one outer attempt')
            child = rows[0] if rows else None
            unknown = any('intent' not in r for r in state['attempts'])
        if child is not None:
            _owned(child,intent); states[code] = child; bindings[code] = _binding(state['request'],child)
        else:
            absent = not unknown or (closed is not None and closed.get(code) is None)
            states[code] = dict(state='NOT_CREATED' if absent else 'UNKNOWN',activity=False if absent else None)
            bindings[code] = None
    state = repair.inspect_prepared_repair_request(attempt/'repair')
    if state['state'] == 'RECORDED':
        expected = repair._configuration(_tree(attempt/'preparation/bundle'),_repair_limits(config),1,qualify_no_repair=config.get('qualify_no_repair',False),optional_failure_policy=config.get('optional_failure_policy'))
        _need(_same(state['request']['configuration'],expected) and len(state['attempts']) <= 1,
              'Prepared repair differs from enclosing input or limits')
        if state['attempts']:
            child = state['attempts'][0]
            if 'intent' in child:
                _owned(child,intent); bindings['repair'] = _binding(state['request'],child)
            else: bindings['repair'] = None
            states['repair'] = child
        else: states['repair'] = dict(state='NOT_CREATED',activity=False); bindings['repair'] = None
    else:
        states['repair'] = dict(state='NOT_CREATED' if state['state'] == 'NOT_RECORDED' else 'UNKNOWN',activity=False if state['state'] == 'NOT_RECORDED' else None)
        bindings['repair'] = None
    if 'continuation' in config:
        states['continuation'],bindings['continuation'] = _continuation_child(attempt,intent,config,states['repair'])
    return states,bindings


def _repair_limits(config):
    return {k:v for k,v in config['limits'].items() if k != 'component_timeout_seconds'}


def _attempt_files(attempt, *, with_continuation=False):
    if with_continuation:
        # Preserve both bounded evidence trees. Do not enlarge either child's
        # artifact contract merely because the outer owner inventories them.
        files = frozen_tree._bounded_tree(attempt,max_files=2*frozen_tree.MAX_FILES,max_bytes=2*frozen_tree.MAX_BYTES)
        dirs = sorted(p.relative_to(attempt).as_posix() for p in attempt.rglob('*') if p.is_dir())
        for nested in (False,True):
            rows = [data for name,data in files.items() if name.startswith('continuation/') == nested]
            _need(len(rows) <= frozen_tree.MAX_FILES and sum(map(len,rows)) <= frozen_tree.MAX_BYTES,
                  'Complete-request evidence partition exceeds frozen bounds')
    else: files,dirs = _capture(attempt)
    files.pop('finished.json',None)
    return dict(files=_inventory(files),directories=dirs)


def _outer_provenance_fields(config):
    # Compiler and construction evidence belong to the outer request. Child
    # preparation consumes the exact model/PHIL already joined by _configuration.
    return {name:config[name] for name in (*_COMPILER_INPUTS,'construction_inputs') if name in config}


def _result(root, attempt, intent, config, children, bindings):
    report = read_record(attempt/'result.json'); elapsed = report.get('elapsed_seconds')
    _need(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0 <= elapsed < config['limits']['total_timeout_seconds'],
          'Invalid complete request elapsed allowance')
    _need(all(r['state'] == 'STOPPED' and r['finished']['outcome'] == 'RETURNED' for name,r in children.items() if name != 'continuation'),
          'Complete request has an unsuccessful child')
    prepared = read_acquired_dictionary_bundle(attempt/'preparation'); controls = config['controls']
    selection = {code:bindings[code]['number'] for code in config['components']}
    pc = read_record(attempt/'preparation/preparation_intent.json')['controls']
    sites = {code:dict(attempt_number=selection[code],contexts=site['contexts'],phosphate_atom_policy=site['phosphate_atom_policy'],
        terminal_resource=None if site['terminal_resource'] is None else 'inputs/'+site['terminal_resource']) for code,site in controls['sites'].items()}
    expected = dict(components=sorted(selection),sites=sites,consumer=controls['consumer'],expected_links=controls['expected_links'],
        native_context=controls['native_context'],supplementary_phils=['inputs/'+n for n in controls['supplementary_phils']])
    _need(_same(pc,expected), 'Prepared controls differ from complete frozen intent')
    outer_only = ('retained/',) + (('construction/',) if 'construction_inputs' in config else ()) + tuple(folder+'/' for name,folder in _COMPILER_INPUTS.items() if name in config)
    for name,data in _tree(root/'inputs').items():
        if not name.startswith(outer_only):
            _need(_read(attempt/'preparation/inputs'/name) == data, 'Prepared input differs from frozen outer intent')
    for code,chosen in prepared['report']['selected_attempts'].items():
        bound = bindings[code]
        _need(all(chosen[k] == bound[k] for k in ('request_sha256','attempt_sha256','attempt_id'))
            and chosen['attempt_number'] == bound['number'], 'Preparation selected another component attempt')
    execution = _json(_read(attempt/'repair/attempts/attempt-0001/execution/repair_execution.json'))
    _need(execution.get('status') in _OUTCOMES, 'Unsupported prepared-repair outcome')
    runtime = None
    if execution['status'] == 'QUALIFIED_DIAGNOSTIC_RUNTIME':
        runtime = resolve_runtime_bundle(attempt/'repair/attempts/attempt-0001/execution/runtime')
    continued = None; continuation_fields = {}
    if 'continuation' in config:
        child = children['continuation']
        if runtime is None:
            _need(child['state'] == 'NOT_CREATED', 'Unusable repair must not start continuation')
        else:
            _need(child['state'] == 'STOPPED' and child['finished']['outcome'] == 'RETURNED',
                  'Qualified repair lacks its completed continuation')
            continued = continuation.read_runtime_continuation(attempt/'continuation')
            runtime = continued['runtime']
        continuation_fields = dict(continuation=None if continued is None else dict(anchor='attempt_directory',path='continuation'))
    expected = dict(schema_version=1,policy_id=POLICY_ID,attempt_sha256=intent['record_sha256'],selected_attempts=selection,
        preparation=dict(anchor='attempt_directory',path='preparation'),repair=dict(anchor='attempt_directory',path='repair'),
        status=execution['status'],automatic_adoption=False,elapsed_seconds=elapsed,**continuation_fields,**_outer_provenance_fields(config))
    _need(_same({k:v for k,v in report.items() if k != 'record_sha256'},expected), 'Complete request result claims differ')
    return dict(result=report,preparation=prepared,execution=execution,runtime=runtime,
        **{name:_compiler_input(name,root/'inputs'/folder) for name,folder in _COMPILER_INPUTS.items() if name in config},
        **({'construction_inputs':read_postmr_construction(root/'inputs/construction')} if 'construction_inputs' in config else {}),
        **({'continuation':continued} if 'continuation' in config else {}))


def _attempt_state(root, attempt, number, request):
    _members(attempt,{'attempt.json','result.json','finished.json'},
             {'preparation','repair'} | ({'continuation'} if 'continuation' in request['configuration'] else set()))
    if not (attempt/'attempt.json').exists():
        _need(not any(attempt.iterdir()), 'Outer output has no intent')
        return dict(number=number,state='UNKNOWN',activity=None)
    intent = _intent(attempt,number,request)
    finished = read_record(attempt/'finished.json') if (attempt/'finished.json').exists() else None
    caller = coordinator_alive(intent['coordinator']) if finished is None else None
    children,bindings = _children(root,attempt,intent,request['configuration'],None if finished is None else finished.get('children'))
    result = dict(number=number,intent=intent,children=children)
    if finished is not None:
        _need(set(finished) == {'attempt_sha256','outcome','error_type','stopped_verified','finished_utc','children','artifacts','record_sha256'}
            and finished['attempt_sha256'] == intent['record_sha256'] and finished['outcome'] in {'RETURNED','RAISED'}
            and finished['stopped_verified'] is True and _same(finished['children'],bindings)
            and _same(finished['artifacts'],_attempt_files(attempt,**({'with_continuation':True} if 'continuation' in request['configuration'] else {})))
            and all(r['state'] in {'STOPPED','NOT_CREATED'} for r in children.values()), 'Outer completion does not bind stopped children/files')
        if finished['outcome'] == 'RETURNED': _result(root,attempt,intent,request['configuration'],children,bindings)
        return dict(result,state='STOPPED',activity=False,finished=finished)
    safe = caller is False and all(r['state'] in _STOPPED for r in children.values())
    live = caller is True or any(r.get('activity') is True for r in children.values())
    return dict(result,state='STOPPED_UNFINISHED' if safe else 'LIVE' if live else 'UNKNOWN',activity=False if safe else True if live else None)


def inspect_dictionary_request(directory):
    """Read advisory state without locks, signals, writes or retry authority."""
    root = _root(directory)
    result = dict(schema_version=1,policy_id=POLICY_ID,state='NOT_RECORDED',availability='BLOCKED',attempts=[],retry_authorized=False)
    if not root.exists(): return result
    _members(root,{'request.json','request.lock'},{'inputs','acquisitions','attempts'})
    if not (root/'request.json').exists(): return dict(result,state='UNKNOWN')
    request = _request(root); config = request['configuration']; rows = []
    if (root/'attempts').exists():
        for number,p in enumerate(sorted((root/'attempts').iterdir()),1):
            _need(p.is_dir() and not p.is_symlink() and p.name == f'attempt-{number:04d}', 'Outer attempts must be consecutive immutable directories')
            rows.append(_attempt_state(root,p,number,request))
    _need(len(rows) <= config['max_attempts'], 'Outer attempt allowance exceeded')
    unknown = False
    if (root/'acquisitions').exists(): _members(root/'acquisitions',set(),set(config['components']))
    owners = {_bytes(_attempt_identity(r['intent'])):r['intent'] for r in rows if 'intent' in r}
    for code,expected in config['components'].items():
        state = acquisition.inspect_acquisition_request(root/'acquisitions'/code)
        if state['state'] == 'RECORDED':
            _need(_same(state['request']['configuration'],expected), 'Operational component request changed')
            # Shared generation can be unresolved outside the numbered child
            # rows. Preserve the component owner's full conservative verdict.
            if state['availability'] == 'BLOCKED': unknown = True
            for child in state['attempts']:
                if 'intent' not in child: unknown = True; continue
                key = _bytes(child['intent'].get('parent_attempt'))
                _need(key in owners, 'Component child has no recorded enclosing owner'); _owned(child,owners[key])
        elif state['state'] != 'NOT_RECORDED': unknown = True
    safe = not unknown and all(r['state'] in {'STOPPED','STOPPED_UNFINISHED'} for r in rows)
    return dict(result,state='RECORDED',request=request,attempts=rows,
        availability='BLOCKED' if not safe else 'EXHAUSTED' if len(rows) == config['max_attempts'] else 'AVAILABLE')


def _seal(root, attempt, intent, request, outcome, error=None, remaining=None):
    children,bindings = _children(root,attempt,intent,request['configuration'])
    if any(r['state'] not in {'STOPPED','NOT_CREATED'} for r in children.values()):
        raise CampaignProcessError('Complete request has unresolved child ownership')
    if outcome == 'RETURNED': _result(root,attempt,intent,request['configuration'],children,bindings)
    composed = 'continuation' in request['configuration']
    artifacts = _attempt_files(attempt,**({'with_continuation':True} if composed else {}))
    # Scientific readback and inventory can be expensive; include them in the
    # final cooperative deadline check, leaving only atomic publication after it.
    completion = dict(attempt_sha256=intent['record_sha256'],outcome=outcome,error_type=error,
        stopped_verified=True,finished_utc=now(),children=bindings,artifacts=artifacts)
    # write_record adds one 64-character digest and a final newline. Reserve
    # that complete record too, so successful publication stays readable.
    encoded = json.dumps(dict(completion,record_sha256='0'*64),indent=2,sort_keys=True,allow_nan=False).encode('utf-8')
    completion_size = len(encoded)+1
    partition = {n:r for n,r in artifacts['files'].items() if not composed or not n.startswith('continuation/')}
    _need(len(partition)+1 <= frozen_tree.MAX_FILES
          and completion_size <= frozen_tree.MAX_FILE_BYTES
          and sum(r['size'] for r in partition.values())+completion_size <= frozen_tree.MAX_BYTES,
          'Outer completion exceeds frozen artifact bounds')
    if remaining is not None: remaining()
    write_record(attempt/'finished.json',completion)


def read_dictionary_request_result(directory, attempt_number):
    """Read one exact successfully returned attempt; diagnostic status is retained."""
    root = _root(directory); state = inspect_dictionary_request(root)
    _need(type(attempt_number) is int and 1 <= attempt_number <= len(state['attempts']), 'Require an exact outer attempt number')
    row = state['attempts'][attempt_number-1]
    _need(row['state'] == 'STOPPED' and row['finished']['outcome'] == 'RETURNED', 'Outer attempt did not return successfully')
    attempt = root/'attempts'/f'attempt-{attempt_number:04d}'
    children,bindings = _children(root,attempt,row['intent'],state['request']['configuration'],row['finished']['children'])
    return _result(root,attempt,row['intent'],state['request']['configuration'],children,bindings)


def execute_dictionary_request_attempt(directory, phenix, store_root, *, generation):
    """Execute one explicit fresh attempt from frozen intent; never retry in place.

    generation maps each code to its explicit runtime SDK/environment settings.
    These must reproduce frozen recipe/pins/relative dispatchers. All callers for
    a logical request must share its directory; the cache is an explicit binding.
    """
    started = monotonic(); root = _root(directory); store = _root(store_root); sdk = _root(phenix.root)
    _need(not store.is_relative_to(root) and not root.is_relative_to(store)
          and not root.is_relative_to(sdk) and not sdk.is_relative_to(root), 'Complete request overlaps cache or SDK')
    request = _request(root); config = request['configuration']; controls = config['controls']; limits = config['limits']
    if 'restraint_context' in config:
        validate_restraint_context(root/'inputs/model.pdb',
            [root/'inputs'/name for name in controls['supplementary_phils']],
            config['restraint_context'], require_scoped_names=True)
    generation = deepcopy(generation)
    _need(isinstance(generation,dict) and set(generation) == set(config['components']), 'Require every runtime generation binding')
    def remaining():
        value = limits['total_timeout_seconds'] - (monotonic()-started)
        if value <= 0: raise TimeoutError('Complete dictionary request allowance exhausted; preserve partial output')
        return value
    for code,g in generation.items():
        installed = _root(g['installation_root'])
        _need(not root.is_relative_to(installed) and not installed.is_relative_to(root), 'Complete request overlaps generator')
        _need(_same(dict(options=generation_dictionary_options(g),binding=acquisition._generation_binding(g)),controls['sites'][code]['generation']),
              'Runtime generation identity differs from frozen request')
    _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],controls['consumer']), 'Complete request consumer differs')
    remaining()
    with exclusive_lock(root/'request.lock'):
        state = inspect_dictionary_request(root)
        _need(state['request']['record_sha256'] == request['record_sha256'], 'Complete request changed before reservation')
        if state['availability'] != 'AVAILABLE': raise CampaignProcessError('Complete request is '+state['availability'])
        remaining(); number = len(state['attempts'])+1
        attempt = root/'attempts'/f'attempt-{number:04d}'; attempt.mkdir(parents=True,exist_ok=False)
        _sync_directory(attempt.parent); _sync_directory(root)
        intent = write_record(attempt/'attempt.json',dict(request_sha256=request['record_sha256'],number=number,
            attempt_id=str(uuid.uuid4()),coordinator=current_process_identity(),created_utc=now()))
        parent = _attempt_identity(intent)
        try:
            selected = read_acquisition_sources(root/'inputs/sources'); components = []
            for code in config['components']:
                remaining(); site = controls['sites'][code]; choice = selected['sources'][code]
                child = acquisition.acquire_dictionary_attempt(choice['source'],code,store,root/'acquisitions'/code,
                    source_authority=choice['source_authority'],consumer=controls['consumer'],generation=generation[code],phenix=phenix,
                    retained_snapshot=None if site['retained'] is None else root/'inputs'/site['retained'],
                    native_timeout_seconds=limits['native_timeout_seconds'],total_timeout_seconds=limits['component_timeout_seconds'],
                    max_attempts=config['max_attempts'],_parent_attempt_identity=parent,_remaining_seconds=remaining)
                components.append(dict(code=code,request_directory=root/'acquisitions'/code,attempt_number=child['attempt_number'],
                    contexts=site['contexts'],phosphate_atom_policy=site['phosphate_atom_policy'],
                    **({'terminal_resource':root/'inputs'/site['terminal_resource']} if site['terminal_resource'] is not None else {})))
            remaining()
            prepare_acquired_dictionary_bundle(root/'inputs/sources',components,root/'inputs/model.pdb',attempt/'preparation',
                consumer=controls['consumer'],expected_links=controls['expected_links'],native_context=controls['native_context'],
                supplementary_phils=[root/'inputs'/n for n in controls['supplementary_phils']])
            remaining()
            child = repair.execute_prepared_dictionary_repair_attempt(attempt/'preparation/bundle',phenix,attempt/'repair',
                **_repair_limits(config),max_attempts=1,_parent_attempt_identity=parent,_remaining_seconds=remaining,
                **({'qualify_no_repair':True} if config.get('qualify_no_repair',False) else {}),
                **repair.failure_policy_fields(config.get('optional_failure_policy')))
            continuation_fields = {}
            if 'continuation' in config:
                qualified = child['execution']['status'] == 'QUALIFIED_DIAGNOSTIC_RUNTIME'
                if qualified:
                    remaining()
                    continuation.execute_runtime_continuation(attempt/'repair/attempts/attempt-0001/execution/runtime',
                        phenix,attempt/'continuation',**_continuation_parameters(config),
                        _attempt_identity=parent,_remaining_seconds=remaining)
                continuation_fields = dict(continuation=dict(anchor='attempt_directory',path='continuation') if qualified else None)
            _need(_same(_request(root),request), 'Frozen complete intent changed during execution')
            remaining(); elapsed = monotonic()-started
            result = write_record(attempt/'result.json',dict(schema_version=1,policy_id=POLICY_ID,attempt_sha256=intent['record_sha256'],
                selected_attempts={c['code']:c['attempt_number'] for c in components},preparation=dict(anchor='attempt_directory',path='preparation'),
                repair=dict(anchor='attempt_directory',path='repair'),status=child['execution']['status'],automatic_adoption=False,elapsed_seconds=elapsed,
                **continuation_fields,**_outer_provenance_fields(config)))
            children,bindings = _children(root,attempt,intent,config); _result(root,attempt,intent,config,children,bindings)
            remaining(); _seal(root,attempt,intent,request,'RETURNED',remaining=remaining)
        except BaseException as exc:
            try: _seal(root,attempt,intent,request,'RAISED',type(exc).__name__)
            except Exception as error:
                add_failure_note(exc, 'Outer completion could not be sealed', error)
            raise
        return dict(request_id=request['request_id'],attempt_id=intent['attempt_id'],attempt_number=number,result=result)
