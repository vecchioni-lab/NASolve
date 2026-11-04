"""Read-only source-bound selection of a complete repaired dictionary bundle.

Source/site preparation, native repair attribution and fixed-coordinate
numerics are independent gates. This adapter composes them; it does not run
native code, adopt coordinates or publish a C141/ordinary-runtime bundle.
"""
from hashlib import sha256
from pathlib import Path

from .cif_dictionary_bundle import read_dictionary_bundle, inspect_dictionary_bundle_native
from .cif_dictionary_sites import _bind_capture, _need, _read
from .cif_dictionary_store import resolve_dictionary_snapshot, _bytes
from .cif_component_runtime import _tree, MAX_FILES, MAX_BYTES
from .cif_linear_torsion_bundle import read_linear_torsion_bundle
from .cif_captured_linear_attribution import read_captured_linear_attribution
from .cif_captured_mixed_gradients import read_captured_mixed_gradients, _inputs
from .cif_native_monomers import POLICY_ID as MONOMER_POLICY, review_full_monomers
from .cif_doctor_selection import ComponentCandidate, select_component_candidate
from .cif_mixed_geometry import _ref

POLICY_ID = 'cif-source-bound-repaired-bundle-selection-v1'


def _gradient(directory, receipt, anchor):
    if directory is None:return dict(status='NOT_SUPPLIED',qualified=False)
    root=Path(directory);report=read_captured_mixed_gradients(root)
    _need(_read(root/'capture/native_receipt.json')==_read(receipt),
        'Derivative evidence belongs to a different native capture')
    return dict(status=report['status'],qualified=report['status']=='CAPTURED_MIXED_DERIVATIVES_PASS',
        report=_ref(root/'captured_mixed_gradients.json',root,anchor))


def _inspect(bundle, baseline_receipt, attribution_directory, repaired_gradient_directory, original_gradient_directory):
    root=Path(bundle).absolute();attribution=Path(attribution_directory).absolute();baseline=Path(baseline_receipt).absolute()
    _need(baseline.name=='native_receipt.json','Require an exact preparation baseline receipt')
    roots={'prepared_bundle_directory':root,'preparation_baseline_directory':baseline.parent,
        'repair_attribution_directory':attribution}
    for name,p in [('repaired_gradient_directory',repaired_gradient_directory),('original_gradient_directory',original_gradient_directory)]:
        if p is not None:roots[name]=Path(p).absolute()
    snapshots={name:_tree(p) for name,p in roots.items()}
    _need(sum(len(v) for v in snapshots.values())<=MAX_FILES
        and sum(len(b) for v in snapshots.values() for b in v.values())<=MAX_BYTES,'Combined repair evidence exceeds supported bounds')
    prepared=read_dictionary_bundle(root);source=prepared['report']
    job=read_captured_linear_attribution(attribution);plan=read_linear_torsion_bundle(attribution/'bundle')
    steps=plan['steps'];_need(bool(steps),'No declared repair candidate')
    _need({p.name for p in (attribution/'captures').iterdir()}=={f'{i:03d}' for i in range(len(steps)+1)},'Unexpected repair stage')
    original=prepared['after_dictionaries'];final=[attribution/'bundle'/r['path'] for r in plan['final_dictionaries']]
    _need([_read(p) for p in original]==[_read(attribution/'bundle'/r['path']) for r in plan['inputs']],
        'Repair does not start from the exact ordered source-qualified dictionaries')
    _need(len(final)==len(original),'Repair changed dictionary membership')
    for step in steps:
        code=step['component'];index=step['dictionary_index']
        _need(code in source['components'] and type(index) is int and 0<=index<len(original)
            and original[index]==prepared['component_dictionaries'][code],
            'Repair component lacks its exact source-qualified owner')
    receipts=[];identity=None
    stages=[plan['inputs']]+[s['dictionaries_after'] for s in steps]
    for i,stage in enumerate(stages):
        parent=attribution/'captures'/f'{i:03d}';receipt=parent/'native_receipt.json'
        capture,model,dictionaries,phils,native,_=_inputs(parent)
        _need(capture.get('full_monomer_inventory_policy')==MONOMER_POLICY,'Require full native identities throughout repair')
        proof=review_full_monomers(native)
        if identity is None:identity=proof
        else:_need(_bytes(proof)==_bytes(identity),'Repair changed full native identities')
        _need(_read(model)==_read(prepared['model'])
            and [_read(p) for p in phils]==[_read(p) for p in prepared['after_phils']]
            and [_read(p) for p in dictionaries]==[_read(attribution/'bundle'/r['path']) for r in stage],
            'Repair capture differs from the prepared model, dictionary order or PHIL')
        _bind_capture(capture,source['consumer'],prepared['model'],dictionaries,prepared['after_phils'])
        receipts.append(receipt)
    initial=inspect_dictionary_bundle_native(root,baseline,receipts[0])
    source_usable=initial['diagnostic_continuation']['allowed'] is True
    repaired=_gradient(repaired_gradient_directory,receipts[-1],'repaired_gradient_directory')
    starting=_gradient(original_gradient_directory,receipts[0],'original_gradient_directory')
    attributed=(job['status']=='CAPTURED_LINEAR_ATTRIBUTION_PASS'
        and job['kernel_execution_authentication']=='MAINTAINED_FRESH_NATIVE_JOB')
    eligible={'repaired_prepared_bundle':source_usable and attributed and repaired['qualified'],
        'verified_prepared_bundle':source_usable and starting['qualified']}
    decisions={};sources={}
    for code in source['components']:
        saved=resolve_dictionary_snapshot(root/'components'/code/'snapshot')
        stereo=saved['qualification']['source_assessment']['finished_stereo']['stereochemistry']
        chemistry=sha256(_bytes(saved['manifest']['request']['declared_chemistry'])).hexdigest()
        index=original.index(prepared['component_dictionaries'][code])
        sources[code]=_ref(saved['source'],root,'prepared_bundle_directory')
        rows=[]
        for label,path in [('repaired_prepared_bundle',final[index]),('verified_prepared_bundle',original[index])]:
            rows.append(ComponentCandidate(candidate_id=label,component=code,source_priority=0,
                artifact_sha256=sha256(_read(path)).hexdigest(),chemistry_sha256=chemistry,
                integrity_verified=True,native_usable=eligible[label],chemistry_preserved=source_usable,
                essential_restraints_present=source_usable,finite_parameters=eligible[label],stereochemistry=stereo,
                warnings=('Source-bound diagnostic only; ordinary refinement and scientific qualification remain separate.',)))
        decisions[code]=select_component_candidate(rows)
    choices={d['selected_candidate'] for d in decisions.values()}
    _need(len(choices)==1,'Component choices cannot be combined into a new unchecked bundle')
    selected=choices.pop();resources=None;inputs=None
    if selected is not None:
        ds=final if selected=='repaired_prepared_bundle' else original
        inputs=dict(model=prepared['model'],dictionaries=ds,phils=prepared['after_phils'])
        resources=dict(model=_ref(inputs['model'],root,'prepared_bundle_directory'),
            dictionaries=[_ref(p,attribution,'repair_attribution_directory') if selected=='repaired_prepared_bundle'
                else _ref(p,root,'prepared_bundle_directory') for p in ds],
            phils=[_ref(p,root,'prepared_bundle_directory') for p in inputs['phils']])
    report=dict(schema_version=1,policy_id=POLICY_ID,
        status='REPAIRED_BUNDLE_DIAGNOSTIC_PASS' if selected=='repaired_prepared_bundle' else 'VERIFIED_PREPARED_FALLBACK' if selected else 'NO_USABLE_BUNDLE',
        decision=dict(status='CONTINUE_WITH_NOTES' if selected else 'NO_USABLE_BUNDLE',selected=selected,
            scope='SEPARATE_DIAGNOSTIC_PHASE_ONLY',requires_cif_review=False,automatic_adoption=False),
        component_decisions=decisions,source_qualification=initial,source_references=sources,
        preparation=_ref(root/'bundle_receipt.json',root,'prepared_bundle_directory'),
        baseline=_ref(baseline,baseline.parent,'preparation_baseline_directory'),
        attribution=_ref(attribution/'captured_linear_attribution.json',attribution,'repair_attribution_directory'),
        derivatives=dict(repaired=repaired,original=starting),resources=resources,
        full_monomer_inventory=identity,coordinate_selection='UNCHANGED_PREPARED_MODEL',
        source_protonation='NOT_ASSESSED',scientific_qualification='NOT_ASSESSED',automatic_adoption=False,
        new_native_calls=0,captured_code_execution='NOT_RUN',model_optimization='NOT_RUN',
        readyset_execution='NOT_RUN',refinement='NOT_RUN',runtime_publication='NOT_RUN',checkpoint_adoption='NOT_RUN')
    _need(all(_tree(roots[k])==v for k,v in snapshots.items()),'Evidence changed during repaired bundle inspection')
    return report,inputs


def inspect_dictionary_bundle_repair(bundle, baseline_receipt, attribution_directory, *,
        repaired_gradient_directory=None, original_gradient_directory=None):
    """Recompute the whole-bundle choice; absent proof grants no fallback.

    Valid failed/prepared numerical attempts remain unqualified alternatives.
    Contradictory or malformed evidence raises instead of being hidden as a
    routine failure. No geometry endpoint or different objective is ranked.
    """
    try:return _inspect(bundle,baseline_receipt,attribution_directory,repaired_gradient_directory,original_gradient_directory)[0]
    except (KeyError,TypeError,IndexError) as exc:raise ValueError('Incomplete source-bound repair evidence') from exc


def repaired_dictionary_bundle_inputs(bundle, baseline_receipt, attribution_directory, *,
        repaired_gradient_directory=None, original_gradient_directory=None):
    """Resolve one freshly verified model/ordered-CIF/PHIL selection together.

    Paths are valid for this read. A downstream owner must freeze/revalidate
    them before execution; this is not an immutable runtime publication.
    """
    try:report,inputs=_inspect(bundle,baseline_receipt,attribution_directory,repaired_gradient_directory,original_gradient_directory)
    except (KeyError,TypeError,IndexError) as exc:raise ValueError('Incomplete source-bound repair evidence') from exc
    _need(inputs is not None,'No usable source-bound dictionary bundle')
    return dict(**inputs,review=report)
