"""Bind exact completed acquisitions to the existing model/site bundle preparer.

This explicit preparation stage performs no native work or automatic retry. Its
copied request records are readback evidence, not new operational requests.
"""
import os
from pathlib import Path

from .campaign_records import _sync_directory, path_in, read_record, write_record
from .cif_acquisition_attempt import read_acquisition_result
from .cif_acquisition_sources import read_acquisition_sources
from .cif_component_runtime import _tree
from .cif_dictionary_bundle import prepare_dictionary_bundle, read_dictionary_bundle, _context
from .cif_dictionary_sites import _consumer, _need, _read, _resource, _safe, read_dictionary_sites
from .cif_dictionary_store import _bytes, _json
from .cif_repair_attempt import _root, _members, _inventory

POLICY_ID = 'cif-acquired-bundle-preparation-v1'
ANCHOR = 'acquisition_preparation_directory'


def _capture(root):
    return _tree(root), sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir())


def _freeze(root, files, directories):
    root.mkdir(parents=True, exist_ok=False)
    for name in directories:
        (root/name).mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = root/name; target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    for folder in sorted([root, *[p for p in root.rglob('*') if p.is_dir()]], key=lambda p:len(p.parts), reverse=True):
        _sync_directory(folder)
    _sync_directory(root.parent)


def _terminal(path, consumer):
    path = Path(path); record = _resource(path, consumer)
    files = {path.name: _read(path)}
    for ref in record['outputs']:
        name = ref['path']
        _need(ref['anchor'] == 'native_directory' and _safe(name) and name not in files,
            'Unsafe or duplicate terminal resource member')
        files[name] = _read(path.parent/name)
    return files


def _bindings(root, controls):
    _need(set(controls) == {'components','sites','consumer','expected_links','native_context','supplementary_phils'},
        'Unexpected acquired preparation controls')
    sources = read_acquisition_sources(root/'inputs/sources')
    codes = controls['components']
    _need(codes == sources['report']['components'] and 1 <= len(codes) <= 16
        and isinstance(controls['sites'], dict) and set(controls['sites']) == set(codes),
        'Acquisition/source component coverage differs')
    _consumer(controls['consumer']); _context(controls['native_context'])
    _members(root/'inputs', {'model.pdb'}, {'sources','acquisitions','resources','phils'})
    _members(root/'inputs/acquisitions', set(), set(codes))
    names = controls['supplementary_phils']
    _need(isinstance(names, list) and names == [f'inputs/phils/{i:03}.phil' for i in range(len(names))],
        'Supplementary PHIL order differs')
    allowed = {'model.pdb', *[name.removeprefix('inputs/') for name in names]}
    allowed.update('sources/'+name for name in _tree(root/'inputs/sources'))
    items = []; bindings = {}
    for code in codes:
        site = controls['sites'][code]
        _need(isinstance(site, dict) and set(site) == {'attempt_number','contexts','terminal_resource','phosphate_atom_policy'},
            'Unexpected component preparation controls')
        request = root/'inputs/acquisitions'/code
        number = site['attempt_number']; saved = read_acquisition_result(request, number)
        selected = sources['sources'][code]; manifest = saved['manifest']; recipe = manifest['request']
        _need(recipe['component'] == code and recipe['source_authority'] == selected['source_authority']
            and _read(saved['source']) == _read(selected['source'])
            and _bytes(manifest['consumer']) == _bytes(controls['consumer']) and saved['qualification_current'],
            'Acquisition source, authority or consumer differs from selected context')
        intent = read_record(request/'attempts'/f'attempt-{number:04d}'/'attempt.json')
        header = read_record(request/'request.json')
        bindings[code] = dict(request_sha256=header['record_sha256'], request_id=header['request_id'],
            attempt_number=number, attempt_sha256=intent['record_sha256'], attempt_id=intent['attempt_id'],
            entry_id=saved['entry_id'], request_directory=dict(anchor=ANCHOR,path=f'inputs/acquisitions/{code}'))
        item = dict(snapshot=saved['source'].parent.parent, contexts=site['contexts'],
            phosphate_atom_policy=site['phosphate_atom_policy'])
        resource = site['terminal_resource']
        if resource is not None:
            _need(_safe(resource) and resource.startswith(f'inputs/resources/{code}/'), 'Invalid terminal resource reference')
            item['terminal_resource'] = path_in(root,resource)
            files = _terminal(item['terminal_resource'], controls['consumer'])
            allowed.update(f'resources/{code}/'+name for name in files)
        allowed.update(f'acquisitions/{code}/'+name for name in _tree(request))
        items.append(item)
    _need(set(_tree(root/'inputs')) == allowed, 'Unrequested acquisition preparation input')
    return items, bindings


def _intent(root, controls):
    files, directories = _capture(root/'inputs')
    return dict(schema_version=1, policy_id=POLICY_ID, controls=controls,
        input_files=_inventory(files), input_directories=directories)


def _report(root, intent):
    items, bindings = _bindings(root, intent['controls']); controls = intent['controls']
    bundle = read_dictionary_bundle(root/'bundle'); r = bundle['report']
    _need(all(_bytes(r[k]) == _bytes(controls[k]) for k in ('components','consumer','expected_links','native_context'))
        and _read(bundle['model']) == _read(root/'inputs/model.pdb'), 'Prepared bundle model or context differs')
    for code, item in zip(controls['components'], items):
        child_root = root/'bundle/components'/code; child = read_dictionary_sites(child_root)
        site = controls['sites'][code]
        _need(_tree(child_root/'snapshot') == _tree(item['snapshot'])
            and _bytes(child['report']['contexts']) == _bytes(site['contexts'])
            and child['report'].get('phosphate_atom_policy') == site['phosphate_atom_policy'],
            'Prepared component differs from its exact acquisition or site declaration')
        if site['terminal_resource'] is not None:
            _need(_tree(child_root/'resources') == _terminal(item['terminal_resource'],controls['consumer']),
                'Prepared terminal resource differs')
    _need([_read(root/name) for name in controls['supplementary_phils']]
        == [_read(root/'bundle'/name) for name in r['supplementary_phils']], 'Prepared shared PHIL bytes differ')
    files, directories = _capture(root); files.pop('acquisition_preparation.json',None)
    report = dict(schema_version=1, policy_id=POLICY_ID, status='PREPARED_REVIEW',
        intent_sha256=intent['record_sha256'], selected_attempts=bindings,
        bundle=dict(anchor=ANCHOR,path='bundle'), files=_inventory(files), directories=directories,
        native_execution='NOT_RUN', scientific_qualification='NOT_ASSESSED', automatic_adoption=False,
        retry_authorized=False, copied_requests='READBACK_EVIDENCE_ONLY')
    return report, bundle


def read_acquired_dictionary_bundle(directory):
    """Revalidate copied exact-attempt evidence and source/site preparation offline.

    Existing bundle readers may use disposable derivation scratch outside the
    artifact. No artifact is changed, native job run, or retry authorized.
    """
    root = _root(directory)
    _members(root, {'preparation_intent.json','acquisition_preparation.json'}, {'inputs','bundle'})
    original = _capture(root)
    intent = read_record(root/'preparation_intent.json')
    _need(_bytes({k:v for k,v in intent.items() if k != 'record_sha256'}) == _bytes(_intent(root,intent['controls'])),
        'Frozen preparation intent differs')
    report = read_record(root/'acquisition_preparation.json')
    expected, bundle = _report(root,intent)
    _need(_bytes({k:v for k,v in report.items() if k != 'record_sha256'}) == _bytes(expected)
        and _capture(root) == original, 'Acquired preparation claims or files changed')
    return dict(report=report, bundle_directory=root/'bundle', bundle=bundle)


def prepare_acquired_dictionary_bundle(source_selection, components, model, output, *,
        consumer, expected_links, native_context, supplementary_phils=()):
    """Prepare a fresh bundle from exact successful attempts, preserving input evidence.

    Every selected source must have one explicit completed attempt. Copied
    acquisition histories are evidence only; this function neither retries them
    nor owns a complete multi-component acquisition/repair request.
    """
    root = _root(output)
    if root.exists():raise FileExistsError(root)
    _consumer(consumer); _context(native_context)
    source_selection = _root(source_selection); selected = read_acquisition_sources(source_selection)
    codes = selected['report']['components']
    _need(isinstance(components,(list,tuple)) and 1 <= len(components) <= 16, 'Require one to sixteen acquired components')
    trees = {'sources':source_selection}; sites = {}; resources = {}; originals = {Path(model):_read(model)}
    for item in components:
        _need(isinstance(item,dict) and {'code','request_directory','attempt_number','contexts'} <= item.keys()
            and item.keys() <= {'code','request_directory','attempt_number','contexts','terminal_resource','phosphate_atom_policy'},
            'Unknown acquired component request')
        code = item['code']; _need(code in codes and code not in sites, 'Duplicate or unselected acquisition component')
        request = _root(item['request_directory']); saved = read_acquisition_result(request,item['attempt_number'])
        _need(saved['manifest']['request']['component'] == code
            and saved['manifest']['request']['source_authority'] == selected['sources'][code]['source_authority']
            and _read(saved['source']) == _read(selected['sources'][code]['source'])
            and _bytes(saved['manifest']['consumer']) == _bytes(consumer), 'Acquisition source/authority/consumer mismatch')
        trees['acquisitions/'+code] = request
        resource = item.get('terminal_resource'); relative = None
        if resource is not None:
            resource = Path(resource); files = _terminal(resource,consumer); relative = f'inputs/resources/{code}/{resource.name}'
            resources.update({f'resources/{code}/'+name:data for name,data in files.items()})
            originals.update({resource.parent/name:data for name,data in files.items()})
        sites[code] = dict(attempt_number=item['attempt_number'], contexts=item['contexts'], terminal_resource=relative,
            phosphate_atom_policy=item.get('phosphate_atom_policy'))
    _need(set(sites) == set(codes), 'Complete selected-source coverage is required')
    controls = _json(_bytes(dict(components=codes, sites=sites, consumer=consumer, expected_links=expected_links,
        native_context=native_context, supplementary_phils=[f'inputs/phils/{i:03}.phil' for i in range(len(supplementary_phils))])))
    files = {'model.pdb':originals[Path(model)], **resources}; directories = set()
    for i,p in enumerate(supplementary_phils):originals[Path(p)] = _read(p); files[f'phils/{i:03}.phil'] = originals[Path(p)]
    captured = {}
    for name,path in trees.items():
        _need(not path.is_relative_to(root) and not root.is_relative_to(path), 'Preparation output overlaps source evidence')
        captured[name] = _capture(path); tree, dirs = captured[name]
        files.update({name+'/'+n:data for n,data in tree.items()}); directories.update([name,*[name+'/'+n for n in dirs]])
    def unchanged():
        _need(all(_capture(path) == captured[name] for name,path in trees.items())
            and all(_read(path) == data for path,data in originals.items()), 'Preparation source changed during freezing')
    unchanged(); root.mkdir(parents=True,exist_ok=False); _sync_directory(root.parent)
    _freeze(root/'inputs',files,sorted(directories))
    intent = write_record(root/'preparation_intent.json',_intent(root,controls))
    items, _ = _bindings(root,controls)
    prepare_dictionary_bundle(items,root/'inputs/model.pdb',root/'bundle',consumer=controls['consumer'],
        expected_links=controls['expected_links'],native_context=controls['native_context'],
        supplementary_phils=[root/name for name in controls['supplementary_phils']])
    unchanged()
    report, _ = _report(root,intent)
    write_record(root/'acquisition_preparation.json',report)
    return read_acquired_dictionary_bundle(root)['report']
