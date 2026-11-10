"""Source-replayed component selections through the existing public bundle API.

The model and ordered CIF/PHIL inputs are one selection. Frozen source trees are
data only: readers recheck the maintained qualification, never execute captured
programs or promote separate diagnostic readiness into production adoption.
"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_dictionary_sites import _need, _read, _safe
from .cif_dictionary_bundle import read_dictionary_bundle
from .cif_dictionary_bundle_readyset import inspect_dictionary_bundle_readyset, readyset_endpoint_inputs
from .cif_runtime_bundle import MANIFEST_FILE, _json_bytes, _load_json, _reference, _resolve_reference

POLICY_ID = 'cif-qualified-component-runtime-bundle-v1'
REPAIRED_POLICY_ID = 'cif-qualified-repaired-component-runtime-bundle-v1'
ORIGINAL_POLICY_ID = 'cif-qualified-prepared-component-runtime-bundle-v1'
CONTINUATION_POLICY_ID = 'cif-qualified-selected-runtime-readyset-bundle-v1'
MAX_FILES = 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_BYTES = 128 * 1024 * 1024
_FIXED = dict(schema_version=1, policy_id=POLICY_ID, manifest_file=MANIFEST_FILE,
    scope='PORTABLE_QUALIFIED_RUNTIME_BUNDLE', status='ACTIVATED_WITH_NOTES',
    native_evidence='VERIFIED_SOURCE_CAPTURE', requires_cif_review=False,
    automatic_adoption=False, scientific_approval='NOT_RUN', scientific_qualification='NOT_ASSESSED',
    production_consumption='PUBLIC_CIF_DOCTOR_BUNDLE_ASSESSMENT', checkpoint_adoption='NOT_RUN',
    automatic_acquisition='NOT_RUN', model_optimization='NOT_RUN', refinement='NOT_RUN',
    new_native_calls=0, captured_code_execution='NOT_RUN', diffraction_data='NOT_READ')


def _tree(root, *, manifest=False):
    return _bounded_tree(root,manifest=manifest,max_files=MAX_FILES,max_bytes=MAX_BYTES)


def _bounded_tree(root, *, max_files, max_bytes, manifest=False):
    # The complete continuation owner can inventory two separately bounded
    # children. Public/child artifacts continue through _tree's original caps.
    _need(type(max_files) is int and 0 < max_files <= 2*MAX_FILES
          and type(max_bytes) is int and 0 < max_bytes <= 2*MAX_BYTES, 'Invalid bounded tree envelope')
    root=Path(root).absolute()
    _need(root.is_dir() and not any(p.is_symlink() for p in (root,*root.parents)), 'Unsafe source tree')
    result={};total=0
    for p in sorted(root.rglob('*')):
        name=p.relative_to(root).as_posix()
        _need(_safe(name) and not p.is_symlink(), 'Unsafe frozen tree member')
        if p.is_dir():continue
        _need(p.is_file(), 'Nonregular frozen tree member')
        if manifest and name==MANIFEST_FILE:continue
        size=p.stat().st_size;total+=size
        _need(size<=MAX_FILE_BYTES and total<=max_bytes and len(result)<max_files, 'Frozen tree exceeds supported bounds')
        result[name]=_read(p)
    return result


def _controls(root, controls):
    _need(isinstance(controls,dict) and set(controls)=={'bundle','baseline_receipt','candidate_receipt','readyset_directory','endpoint_receipt','atom_order_directory'},
        'Incomplete source selection')
    fixed={'bundle':'evidence/bundle','readyset_directory':'evidence/readyset'}
    _need(all(controls[k]==v for k,v in fixed.items()), 'Source roots differ')
    names={'bundle','baseline','candidate','readyset'}
    for field,folder in [('baseline_receipt','baseline'),('candidate_receipt','candidate'),('endpoint_receipt','endpoint')]:
        name=controls[field]
        if field=='endpoint_receipt' and name is None:continue
        _need(_safe(name) and name.startswith('evidence/'+folder+'/') and len(name.split('/'))==3,
            'Unsafe native receipt reference')
        names.add(folder)
    _need(controls['atom_order_directory'] in (None,'evidence/atom-order'), 'Unsafe atom-order reference')
    if controls['atom_order_directory'] is not None:names.add('atom-order')
    evidence=root/'evidence'
    _need(evidence.is_dir() and {p.name for p in evidence.iterdir()}==names
        and all(p.is_dir() and not p.is_symlink() for p in evidence.iterdir()), 'Unexpected source evidence roots')
    return {k:root/v if v is not None else None for k,v in controls.items()}


def _selection(root, controls, *, policy_id=POLICY_ID):
    if policy_id == CONTINUATION_POLICY_ID:
        from .cif_runtime_readyset import selected_runtime_readyset_publication
        return selected_runtime_readyset_publication(root, controls)
    if policy_id == ORIGINAL_POLICY_ID:
        return _original_selection(root, controls)
    if policy_id == REPAIRED_POLICY_ID:
        return _repaired_selection(root, controls)
    args=_controls(root,controls)
    review=deepcopy(inspect_dictionary_bundle_readyset(**args))
    # Exception text can contain the current evidence root. Keep its declared
    # anchor in the saved diagnostic, never a temporary publication path.
    if isinstance(review.get('endpoint_error'), str):
        review['endpoint_error']=review['endpoint_error'].replace(str(root.absolute())+'/', 'runtime_bundle/')
    decision=deepcopy(review['decision']);selected=decision['selected']
    _need(decision.get('status')=='CONTINUE_WITH_NOTES' and decision.get('scope')=='SEPARATE_DIAGNOSTIC_PHASE_ONLY'
        and decision.get('automatic_adoption') is False and decision.get('requires_cif_review') is False
        and selected in {'verified_prepared_model','readyset_checked_model','readyset_ordered_checked_model'},
        'No qualified diagnostic selection')
    if selected=='verified_prepared_model':
        prepared=read_dictionary_bundle(args['bundle'])
        inputs=dict(model=prepared['model'],dictionaries=prepared['after_dictionaries'],phils=prepared['after_phils'])
    else:
        inputs=readyset_endpoint_inputs(args['bundle'],args['readyset_directory'],atom_order_directory=args['atom_order_directory'])
    unavailable=[{k:r[k] for k in ('check','status')} for r in review['initial']['qualification']['checks'] if r['status']!='PASS']
    notes=['Separate diagnostic continuation; scientific qualification and production adoption remain unassessed.']
    if unavailable:notes.append('Unavailable native evidence remains recorded; source chemical state is preserved.')
    if selected=='verified_prepared_model':notes.append('Optional ReadySet improvement was not selected; verified starting inputs were retained together.')
    decision['notes']=notes
    return review,decision,inputs,unavailable


def _repaired_selection(root, controls):
    # Import lazily: the decision adapter shares this module's bounded tree reader.
    from .cif_dictionary_bundle_repair import repaired_dictionary_bundle_inputs
    fixed = {'bundle':'evidence/bundle',
        'baseline_receipt':'evidence/baseline/native_receipt.json',
        'attribution_directory':'evidence/attribution'}
    optional = {'repaired_gradient_directory':'evidence/repaired-gradient',
        'original_gradient_directory':'evidence/original-gradient'}
    _need(isinstance(controls, dict) and set(controls) == set(fixed) | set(optional)
        and all(controls[k] == v for k,v in fixed.items())
        and all(controls[k] in (None,v) for k,v in optional.items()),
        'Incomplete or unsafe repaired source selection')
    names = {'bundle', 'baseline', 'attribution'} | {
        v.split('/')[-1] for k,v in optional.items() if controls[k] is not None}
    evidence = root/'evidence'
    _need(evidence.is_dir() and {p.name for p in evidence.iterdir()} == names
        and all(p.is_dir() and not p.is_symlink() for p in evidence.iterdir()),
        'Unexpected repaired source evidence roots')
    args = {k:root/v if v is not None else None for k,v in controls.items()}
    result = repaired_dictionary_bundle_inputs(**args)
    review = deepcopy(result['review']); decision = deepcopy(review['decision'])
    _need(decision.get('status') == 'CONTINUE_WITH_NOTES'
        and decision.get('scope') == 'SEPARATE_DIAGNOSTIC_PHASE_ONLY'
        and decision.get('automatic_adoption') is False
        and decision.get('requires_cif_review') is False
        and decision.get('selected') in {'repaired_prepared_bundle', 'verified_prepared_bundle'},
        'No qualified repaired diagnostic selection')
    unavailable = [{k:r[k] for k in ('check','status')}
        for r in review['source_qualification']['qualification']['checks'] if r['status'] != 'PASS']
    notes = ['Separate diagnostic continuation; scientific qualification and production adoption remain unassessed.']
    if unavailable: notes.append('Unavailable native evidence remains recorded; source chemical state is preserved.')
    if decision['selected'] == 'verified_prepared_bundle':
        notes.append('Repair was not selected; the independently verified starting bundle was retained.')
    decision['notes'] = notes
    return review, decision, {k:result[k] for k in ('model','dictionaries','phils')}, unavailable


def _original_selection(root, controls):
    from .cif_dictionary_bundle_repair import original_dictionary_bundle_inputs
    fixed={'bundle':'evidence/bundle','baseline_receipt':'evidence/baseline/native_receipt.json',
        'candidate_receipt':'evidence/candidate/native_receipt.json',
        'original_gradient_directory':'evidence/original-gradient'}
    _need(isinstance(controls,dict) and controls==fixed,'Incomplete or unsafe original source selection')
    evidence=root/'evidence'
    _need(evidence.is_dir() and {p.name for p in evidence.iterdir()}=={'bundle','baseline','candidate','original-gradient'}
        and all(p.is_dir() and not p.is_symlink() for p in evidence.iterdir()),'Unexpected original source evidence roots')
    result=original_dictionary_bundle_inputs(**{k:root/v for k,v in controls.items()})
    review=deepcopy(result['review']);decision=deepcopy(review['decision'])
    _need(decision.get('status')=='CONTINUE_WITH_NOTES' and decision.get('scope')=='SEPARATE_DIAGNOSTIC_PHASE_ONLY'
        and decision.get('automatic_adoption') is False and decision.get('requires_cif_review') is False
        and decision.get('selected')=='verified_prepared_bundle','No qualified original diagnostic selection')
    unavailable=[{k:r[k] for k in ('check','status')}
        for r in review['source_qualification']['qualification']['checks'] if r['status']!='PASS']
    decision['notes']=['Separate diagnostic continuation; scientific qualification and production adoption remain unassessed.',
        'The original model and dictionaries passed independent source/native and fixed-coordinate derivative checks.']
    if unavailable:decision['notes'].append('Unavailable native evidence remains recorded; source chemical state is preserved.')
    return review,decision,{k:result[k] for k in ('model','dictionaries','phils')},unavailable


def _resources(root, inputs, *, write=False):
    refs={'model':None,'dictionaries':[],'phils':[]}
    for key,folder,suffix,paths in [('model','model','.pdb',[inputs['model']]),
            ('dictionaries','dictionaries','.cif',inputs['dictionaries']),('phils','parameters','.phil',inputs['phils'])]:
        _need(bool(paths), 'Missing selected resources')
        for i,source in enumerate(paths):
            target=root/folder/('model.pdb' if key=='model' else f'{i:03d}{suffix}')
            data=_read(source)
            if write:target.parent.mkdir(exist_ok=True);target.write_bytes(data)
            _need(_read(target)==data, 'Runtime resource differs from verified selection')
            ref=_reference(target,root)
            if key=='model':refs[key]=ref
            else:refs[key].append(ref)
    return refs


def _manifest(root, controls, review, decision, resources, unavailable, *, policy_id=POLICY_ID):
    files=[_reference(root/name,root) for name in _tree(root,manifest=True)]
    return dict(**{**deepcopy(_FIXED), 'policy_id':policy_id},source_selection=controls,source_review=review,decision=decision,
        resources=resources,unavailable_native_checks=unavailable,files=files)


def prepare_component_runtime_bundle(bundle, baseline_receipt, candidate_receipt, readyset_directory, output,
        *, endpoint_receipt=None, atom_order_directory=None):
    """Freeze a fresh complete selection; failed improvements retain starting inputs.

    ReadySet may be absent (None). An existing failed attempt is frozen intact.
    A bad/unusable starting bundle refuses publication. No native process runs.
    """
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    _need(not any(p.is_symlink() for p in output.parents), 'Unsafe runtime destination')
    controls=dict(bundle='evidence/bundle',readyset_directory='evidence/readyset',
        baseline_receipt=None,candidate_receipt=None,endpoint_receipt=None,atom_order_directory=None)
    roots={'bundle':Path(bundle),'readyset':Path(readyset_directory) if readyset_directory is not None else None}
    for field,folder,supplied in [('baseline_receipt','baseline',baseline_receipt),('candidate_receipt','candidate',candidate_receipt),('endpoint_receipt','endpoint',endpoint_receipt)]:
        if supplied is None:
            _need(field=='endpoint_receipt','Missing starting native receipt');continue
        p=Path(supplied);_need(_safe(p.name),'Unsafe receipt filename');roots[folder]=p.parent
        controls[field]='evidence/'+folder+'/'+p.name
    if atom_order_directory is not None:
        roots['atom-order']=Path(atom_order_directory);controls['atom_order_directory']='evidence/atom-order'
    return _publish(output, roots, controls, POLICY_ID)


def prepare_repaired_component_runtime_bundle(bundle, baseline_receipt, attribution_directory, output,
        *, repaired_gradient_directory=None, original_gradient_directory=None):
    """Freeze the source-bound whole-bundle repair decision and every proof.

    All scientific checks are replayed by the existing decision adapter. A
    preserved original is eligible only with its own passing derivative proof.
    This explicit publication does not run tools or adopt experimental coordinates.
    """
    baseline = Path(baseline_receipt)
    _need(baseline.name == 'native_receipt.json', 'Require exact native baseline receipt')
    roots = {'bundle':Path(bundle), 'baseline':baseline.parent,
        'attribution':Path(attribution_directory)}
    controls = dict(bundle='evidence/bundle', baseline_receipt='evidence/baseline/native_receipt.json',
        attribution_directory='evidence/attribution', repaired_gradient_directory=None,
        original_gradient_directory=None)
    for key, folder, path in [('repaired_gradient_directory','repaired-gradient',repaired_gradient_directory),
            ('original_gradient_directory','original-gradient',original_gradient_directory)]:
        if path is not None:
            roots[folder] = Path(path); controls[key] = 'evidence/'+folder
    return _publish(Path(output).absolute(), roots, controls, REPAIRED_POLICY_ID)


def prepare_original_component_runtime_bundle(bundle, baseline_receipt, candidate_receipt, output, *, original_gradient_directory):
    """Freeze an independently qualified original through the shared publisher.

    No repair history is required or invented. Existing original evidence is
    replayed in full and frozen together before the output becomes visible.
    """
    baseline=Path(baseline_receipt);candidate=Path(candidate_receipt)
    _need(baseline.name==candidate.name=='native_receipt.json','Require exact original native receipts')
    roots={'bundle':Path(bundle),'baseline':baseline.parent,'candidate':candidate.parent,
        'original-gradient':Path(original_gradient_directory)}
    controls=dict(bundle='evidence/bundle',baseline_receipt='evidence/baseline/native_receipt.json',
        candidate_receipt='evidence/candidate/native_receipt.json',original_gradient_directory='evidence/original-gradient')
    return _publish(Path(output).absolute(),roots,controls,ORIGINAL_POLICY_ID)


def prepare_runtime_readyset_bundle(manifest, baseline_receipt, readyset_directory, output,
        *, endpoint_receipt=None, atom_order_directory=None):
    """Freeze selected-parent proof and an optional exact ReadySet continuation.

    Reuse the public source freezer; no recovery owner or checkpoint is created.
    A failed optional improvement preserves the complete qualified parent runtime.
    """
    from .cif_runtime_readyset import _parent
    parent = _parent(manifest); output = Path(output).absolute()
    controls = dict(runtime='evidence/runtime', readyset_directory='evidence/readyset',
        baseline_receipt=None, endpoint_receipt=None, atom_order_directory=None)
    roots = {'runtime':parent['manifest_path'].parent,
             'readyset':Path(readyset_directory) if readyset_directory is not None else None}
    for field,folder,supplied in [('baseline_receipt','baseline',baseline_receipt),
                                  ('endpoint_receipt','endpoint',endpoint_receipt)]:
        if supplied is not None:
            path = Path(supplied)
            _need(path.name == 'native_receipt.json', 'Require an exact selected-runtime native receipt')
            roots[folder] = path.parent; controls[field] = 'evidence/'+folder+'/'+path.name
    if atom_order_directory is not None:
        roots['atom-order'] = Path(atom_order_directory); controls['atom_order_directory'] = 'evidence/atom-order'
    return _publish(output, roots, controls, CONTINUATION_POLICY_ID)


def _publish(output, roots, controls, policy_id):
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    _need(not any(p.is_symlink() for p in output.parents), 'Unsafe runtime destination')
    snapshots={}
    for name,source in roots.items():
        if source is not None:
            source=source.absolute();_need(not output.resolve().is_relative_to(source.resolve()), 'Cannot publish inside source evidence')
            snapshots[name]=_tree(source)
        else:snapshots[name]={}
    _need(sum(len(s) for s in snapshots.values())<=MAX_FILES
        and sum(len(b) for s in snapshots.values() for b in s.values())<=MAX_BYTES, 'Combined source exceeds supported bounds')
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.component-runtime-',dir=output.parent) as temporary:
        root=Path(temporary)/'bundle';root.mkdir()
        for name,files in snapshots.items():
            dest=root/'evidence'/name;dest.mkdir(parents=True)
            for relative,data in files.items():
                target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        review,decision,inputs,unavailable=_selection(root,controls,policy_id=policy_id)
        resources=_resources(root,inputs,write=True)
        value=_manifest(root,controls,review,decision,resources,unavailable,policy_id=policy_id)
        (root/MANIFEST_FILE).write_bytes(_json_bytes(value))
        resolve_component_runtime_bundle(root/MANIFEST_FILE)
        _need(all(_tree(source)==snapshots[name] for name,source in roots.items() if source is not None), 'Source evidence changed during publication')
        _need(not output.exists() and not output.is_symlink(),'Runtime destination was reserved concurrently')
        root.rename(output)
    return value


def verify_component_runtime_resources(path, value):
    """Final byte/inventory check after a verified read, without repeating science."""
    path=Path(path);root=path.parent
    _need(path.name==MANIFEST_FILE and _json_bytes(_load_json(path))==_json_bytes(value), 'Runtime manifest changed')
    policy = value.get('policy_id')
    _need(policy in (POLICY_ID, REPAIRED_POLICY_ID, ORIGINAL_POLICY_ID, CONTINUATION_POLICY_ID), 'Unsupported component runtime policy')
    fixed = {**_FIXED, 'policy_id':policy}
    _need(all(type(value.get(k)) is type(v) and value.get(k)==v for k,v in fixed.items()), 'Unsupported component runtime policy')
    actual=[_reference(root/name,root) for name in _tree(root,manifest=True)]
    _need(_json_bytes(actual)==_json_bytes(value['files']), 'Frozen runtime inventory changed')
    refs=value['resources'];rows=[refs['model'],*refs['dictionaries'],*refs['phils']]
    _need(len(rows)==len({r['relative_path'] for r in rows}), 'Runtime resources alias')
    return [_resolve_reference(root,r) for r in rows]


def resolve_component_runtime_bundle(path, value=None):
    """Replay selected source/native evidence before exposing any runtime paths."""
    path=Path(path);value=_load_json(path) if value is None else value;root=path.parent
    try:
        verify_component_runtime_resources(path,value)
        review,decision,inputs,unavailable=_selection(root,value['source_selection'],policy_id=value['policy_id'])
        resources=_resources(root,inputs)
        expected=_manifest(root,value['source_selection'],review,decision,resources,unavailable,policy_id=value['policy_id'])
        _need(_json_bytes(value)==_json_bytes(expected), 'Runtime selection or evidence does not replay')
        verify_component_runtime_resources(path,value)
        return dict(model=_resolve_reference(root,resources['model']),
            dictionaries=[_resolve_reference(root,r) for r in resources['dictionaries']],
            phils=[_resolve_reference(root,r) for r in resources['phils']],manifest=value,manifest_path=path)
    except (KeyError,TypeError,IndexError,OSError) as exc:
        raise ValueError('Incomplete or changed component runtime bundle') from exc


def component_runtime_summary(value):
    selected=value['decision']['selected']
    label={'verified_parent_runtime':'the qualified parent model and its selected dictionaries',
        'verified_prepared_model':'the verified starting model',
        'readyset_checked_model':'the verified ReadySet model',
        'readyset_ordered_checked_model':'the verified order-restored ReadySet model',
        'repaired_prepared_bundle':'the source-verified model and repaired dictionaries',
        'verified_prepared_bundle':'the independently verified starting model and dictionaries'}[selected]
    return dict(text='NASolve prepared '+label+' with its exact checked restraint bundle for a separate diagnostic continuation. '
        +' '.join(value['decision']['notes'])+' CIF inspection is not required.',
        qualification_scope='SEPARATE_DIAGNOSTIC_PHASE_ONLY',scientific_qualification='NOT_ASSESSED',
        unavailable_native_checks=deepcopy(value['unavailable_native_checks']),automatic_adoption=False)
