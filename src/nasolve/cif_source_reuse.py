"""Requalify unchanged saved numerics against the ordinary selected source.

Exact store keys remain strict. A source projection is a candidate relationship,
never a cache hit or permission to substitute chemistry or skip native checks.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

POLICY_ID='cif-ordinary-source-reuse-v1'


def _json(value):
    return json.loads(json.dumps(value,sort_keys=True,allow_nan=False))


def _need(value,message):
    if not value:raise ValueError(message)


def _ref(path,root):
    data=path.read_bytes()
    return {'anchor':'ordinary_dictionary_directory','path':path.relative_to(root).as_posix(),
        'sha256':sha256(data).hexdigest(),'size':len(data)}


def source_projection(source,code,authority,snapshot,*,recipe,generator):
    """Compare exact named declarations and complete finished configuration."""
    from .cif_dictionary_store import resolve_dictionary_snapshot,make_dictionary_request,recipe_representation_policy
    from .cif_candidate_usability import reassess_complete_candidate
    saved=resolve_dictionary_snapshot(snapshot);prior=saved['manifest']['request']
    _need(prior['component']==code,'Saved projection component differs')
    current=make_dictionary_request(source,code,source_authority=authority,recipe=recipe,generator=generator)
    checks={k:current['declared_chemistry'][k]==v for k,v in prior['declared_chemistry'].items()}
    checks['repair_recipe']=recipe==prior['recipe']
    checks['numerical_backend']=generator['name']==prior['generator']['name']
    assessment=reassess_complete_candidate(source,saved['dictionary'],code,
        bond_representation_policy=recipe_representation_policy(recipe))
    checks['complete_source_candidate_assessment']=assessment['candidate_status']=='CANDIDATE_REVIEW'
    checks['source_configuration_not_inverted']=assessment['finished_stereo']['stereochemistry']!='INVERTED'
    return {'schema_version':1,'policy_id':POLICY_ID,'component':code,
        'status':'SOURCE_PROJECTION_PASS' if all(checks.values()) else 'INCOMPATIBLE_PROJECTION',
        'checks':checks,'selected_request':current,'prior_entry_id':saved['entry_id'],
        'prior_request':prior,'candidate_sha256':saved['qualification']['candidate_sha256'],
        'source_relative_configuration':assessment['finished_stereo']['stereochemistry'],
        'scope':'DECLARED_SOURCE_RELATIONSHIP_ONLY; FRESH_NATIVE_QUALIFICATION_REQUIRED',
        'requires_cif_review':False,'automatic_adoption':False}


def resolve_ordinary_dictionary(code,ready_set_executable,store_root,output,*,recipe,generator,consumer,
                                data_root=None,saved_snapshot=None,qualify=None):
    """Select the ordinary source, reuse or requalify; retain source on failure.

    Caller adapters supply actual current native evidence. The adapter receives
    disposable copies, so a failed/mutating adapter cannot damage any source or
    prior cache entry. No generator or optimizer is called by this API.
    """
    from .curated_ligands import ligand_source,validate_ligand_dictionary
    from .cif_dictionary_store import (resolve_qualified_dictionary,resolve_dictionary_snapshot,
        make_dictionary_request)
    selected=ligand_source(code,data_root,ready_set_executable=ready_set_executable)
    validate_ligand_dictionary(code,selected.path)
    output=Path(output).absolute()
    _need(not output.exists() and not output.is_symlink(),'Ordinary dictionary output already exists')
    _need(not any(p.is_symlink() for p in output.parents),'Ordinary output cannot traverse a symlink')
    # Validate the request before writes, including authority, recipe and backend.
    request=make_dictionary_request(selected.path,code,source_authority=selected.authority,recipe=recipe,generator=generator)
    original=selected.path.read_bytes();output.mkdir(parents=True)
    source=output/'source.cif';source.write_bytes(original)
    _need(selected.path.read_bytes()==original,'Ordinary source changed while freezing')
    options=dict(source_authority=selected.authority,recipe=recipe,generator=generator,consumer=consumer)
    report={'schema_version':1,'policy_id':POLICY_ID,'component':code,
        'source':{'authority':selected.authority,'kind':selected.kind,'artifact':_ref(source,output),
            'historical_path':str(selected.path),'historical_path_role':'PROVENANCE_ONLY'},
        'request':request,'status':'ORDINARY_SOURCE_FALLBACK','decision':'CONTINUE_WITH_NOTES',
        'selected':'ordinary_source','numerics':None,'projection':None,'native_adapter_calls':0,
        'notes':[],'requires_cif_review':False,'dictionary_generation':'NOT_RUN',
        'model_optimization':'NOT_RUN','production_adoption':'NOT_RUN',
        'linked_context':'REQUALIFY_FOR_CURRENT_SITE','model_geometry':'ASSESS_FOR_NEW_MODEL'}
    def checked_qualify(a,b,current_consumer):
        _need(qualify is not None,'Current native qualification adapter is unavailable')
        directory=output/'qualification_inputs';directory.mkdir()
        x,y=directory/'source.cif',directory/'dictionary.cif'
        left,right=Path(a).read_bytes(),Path(b).read_bytes();x.write_bytes(left);y.write_bytes(right)
        report['native_adapter_calls']+=1
        result=qualify(x,y,current_consumer)
        _need(x.read_bytes()==left and y.read_bytes()==right,'Native adapter changed a qualification input')
        return result
    try:
        result=resolve_qualified_dictionary(source,code,store_root,output/'numerics',**options)
        if result['status']=='REQUALIFICATION_REQUIRED' and qualify is not None:
            result=resolve_qualified_dictionary(source,code,store_root,output/'numerics',
                requalify=checked_qualify,**options)
        if result['status']=='MISS' and saved_snapshot is not None:
            proof=source_projection(source,code,selected.authority,saved_snapshot,recipe=recipe,generator=generator)
            report['projection']=proof
            _need(proof['status']=='SOURCE_PROJECTION_PASS','Saved source projection is incompatible')
            _need(qualify is not None,'Matching source projection requires current native qualification')
            # Keep complete prior evidence inside the run, without changing it.
            saved=resolve_dictionary_snapshot(saved_snapshot)
            shutil.copytree(saved_snapshot,output/'prior_snapshot')
            frozen=resolve_dictionary_snapshot(output/'prior_snapshot')
            _need(frozen['entry_id']==saved['entry_id'],'Prior snapshot changed during freezing')
            qualification=checked_qualify(source,frozen['dictionary'],consumer)
            provenance=deepcopy(frozen['provenance']);provenance['source_projection']=proof
            # The original producer retains credit for the unchanged numerics.
            original_generator=frozen['manifest']['request']['generator']
            result=resolve_qualified_dictionary(source,code,store_root,output/'numerics',
                acquire=lambda:dict(candidate=frozen['dictionary'],qualification=qualification,provenance=provenance),
                **{**options,'generator':original_generator})
        if result['status'] in {'REUSED','PREPARED_AND_FROZEN','REQUALIFIED_AND_FROZEN'}:
            saved=resolve_dictionary_snapshot(output/'numerics')
            report.update(status='REUSED' if result['status']=='REUSED' else 'SOURCE_REQUALIFIED_AND_FROZEN',
                selected='qualified_dictionary',numerics=_ref(output/'numerics/resolution.json',output),
                notes=result['notes'],converged=result['converged'],stopping=result['stopping'])
        else:report['notes'].append('The selected source continues through ordinary preparation; current qualified numerics are unavailable.')
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError) as exc:
        # In particular, nonconvergence never enters this exception path by
        # itself. Rejected/unbound native evidence excludes only that candidate.
        report['notes'].append('Saved numerics were not selected: '+str(exc))
    if report['selected']=='ordinary_source':
        report['numerical_readiness']='STANDARD_PREPARATION_REQUIRED; SOURCE_IS_NOT_A_NATIVE_USABILITY_VERDICT'
    (output/'ordinary_dictionary.json').write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n')
    read_ordinary_dictionary(output)
    return _json(report)


def read_ordinary_dictionary(output):
    """Resolve a frozen result without its original installation or user cache."""
    from .cif_dictionary_store import resolve_dictionary_snapshot,make_dictionary_request
    root=Path(output);path=root/'ordinary_dictionary.json'
    _need(root.is_dir() and not root.is_symlink() and not path.is_symlink(),'Unsafe ordinary dictionary result')
    report=json.loads(path.read_text());source=root/'source.cif';ref=report['source']['artifact']
    _need(not source.is_symlink() and ref==_ref(source,root) and ref['path']=='source.cif','Ordinary source binding differs')
    _need(report['policy_id']==POLICY_ID and report['schema_version']==1
        and report['requires_cif_review'] is False and report['production_adoption']=='NOT_RUN'
        and report['linked_context']=='REQUALIFY_FOR_CURRENT_SITE'
        and report['model_geometry']=='ASSESS_FOR_NEW_MODEL','Ordinary result scope differs')
    request=report['request']
    _need(make_dictionary_request(source,report['component'],source_authority=report['source']['authority'],
        recipe=request['recipe'],generator=request['generator'])==request,'Frozen ordinary request differs')
    native=None;dictionary=source
    if report['status'] in {'REUSED','SOURCE_REQUALIFIED_AND_FROZEN'}:
        _need(report['selected']=='qualified_dictionary' and report['numerics']==_ref(root/'numerics/resolution.json',root),
            'Selected dictionary binding differs')
        native=resolve_dictionary_snapshot(root/'numerics');actual=native['manifest']['request']
        _need(all(actual[k]==v for k,v in request.items() if k!='generator')
            and actual['generator']['name']==request['generator']['name'],'Reused numerics bind another source or authority')
        dictionary=native['dictionary']
    else:
        _need(report['status']=='ORDINARY_SOURCE_FALLBACK' and report['selected']=='ordinary_source'
            and report['numerics'] is None,'Fallback binding differs')
    if report['projection'] is not None and report['selected']=='qualified_dictionary':
        expected=source_projection(source,report['component'],report['source']['authority'],root/'prior_snapshot',
            recipe=request['recipe'],generator=request['generator'])
        _need(expected==report['projection'] and expected['status']=='SOURCE_PROJECTION_PASS'
            and native['provenance'].get('source_projection')==expected,'Frozen source projection proof differs')
    return {'report':report,'source':source,'dictionary':dictionary,'numerics':native}
