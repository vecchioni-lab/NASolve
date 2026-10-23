"""Whole-model cached-dictionary readback; no chemistry or optimizer changes."""
from copy import deepcopy
from pathlib import Path

from .cif_candidate_usability import energy_inventory_checks
from .cif_construction_native import NATIVE_KINDS
from .cif_fixed_geometry import _fixed_policy
from .cif_fragment_restoration import _model
from .cif_linked_qualification import native_backbone_links
from .cif_terminal_qualification import _proxy_subset, PROXY_COMPARISON_POLICY

POLICY_ID='cif-postmr-cached-model-readback-v1'


def qualify_cached_model_roundtrip(before,after,before_model,after_model):
    """Compare every fixed named restraint, definition and backbone link.

    Both coordinate files must contain the same named heavy sites. Only native
    display padding is normalized by the shared structured-identity comparator;
    targets, weights, endpoint order, origins, symmetry and multiplicity stay exact.
    Finite repeated energies are required; this does not qualify derivatives or
    rank scientific geometry. Pairing/stacking is never guessed or added here.
    """
    from .cif_postmr_readyset import _atoms
    checks={}
    try:
        checks['unchanged_named_heavy_coordinates']=_atoms(Path(before_model))==_atoms(Path(after_model))
        for label,record,model in [('before',before,before_model),('after',after,after_model)]:
            _model(record,Path(model),coordinates_match=True)
            checks[label+':exact_native_model']=True
            checks[label+':complete_native_interpretation']=(record.get('status')=='REVIEW'
                and record.get('fatal_problems') is None and record.get('unused_definitions')==[]
                and record.get('unsupported_fields')==[] and record.get('inventory_detail')=='linked')
            checks[label+':fixed_secondary_structure_policy']=_fixed_policy(record)
            checks.update({label+':'+k:v for k,v in energy_inventory_checks(record).items()})
            details=record['geometry']['proxy_details']
            checks[label+':complete_proxy_inventory']=(set(details)==NATIVE_KINDS
                and all(record['geometry']['proxy_counts'].get(k)==len(v) for k,v in details.items()))
        def definitions(native):
            rows=deepcopy(native['monomer_mappings']['rows']);sites=[r['site'] for r in rows]
            if len(sites)!=len(set(sites)):raise ValueError('Duplicate native monomer site')
            for row in rows:
                # Display labels are provenance. Structured fields and every
                # chemical/missing-atom/modifier field remain in the comparison.
                row.pop('residue_label',None)
                for key in ['resname','chain_id','interpreted_residue_name']:
                    if key in row:row[key]=row[key].strip()
                if 'literal_identity' in row:
                    for key in ['model_id','chain_id','resseq','icode','resname','altloc']:
                        row['literal_identity'][key]=row['literal_identity'][key].strip()
            return {r['site']:r for r in rows}
        checks['exact_effective_site_definitions']=definitions(before)==definitions(after)
        checks['all_backbone_links_exact']=native_backbone_links(before)==native_backbone_links(after)
        checks['exact_explicit_requests']=before['geometry']['custom_proxy_requests']==after['geometry']['custom_proxy_requests']
        checks['same_native_policy']=before['restraint_policy']==after['restraint_policy']
        for kind in sorted(NATIVE_KINDS):
            checks['exact_named_proxies:'+kind]=_proxy_subset(before,set(),kind)==_proxy_subset(after,set(),kind)
        checks['same_installed_api_sources']=before['installed_api_sources']==after['installed_api_sources']
    except (KeyError,ValueError,TypeError,OSError,IndexError,StopIteration) as exc:
        checks['complete_roundtrip_evidence']=False
        error=type(exc).__name__+': '+str(exc)
    else:error=None
    return {'schema_version':1,'policy_id':POLICY_ID,'status':'CACHED_MODEL_NATIVE_ROUNDTRIP_PASS'
        if checks and all(v is True for v in checks.values()) else 'REVIEW',
        'mechanics_checks_pass':bool(checks) and all(v is True for v in checks.values()),'checks':checks,'error':error,
        'proxy_comparison':PROXY_COMPARISON_POLICY,'scientific_qualification':'NOT_ASSESSED',
        'policy_authority':'NARestraints','policy_recompilation':'NOT_RUN','requires_cif_review':False,'automatic_adoption':False}


def coordinate_decision(initial_usable,readyset_pass,endpoint_usable):
    """Retain a verified start when the optional roundtrip is unavailable."""
    endpoint=initial_usable is True and readyset_pass is True and endpoint_usable is True
    usable=initial_usable is True
    return {'status':'CONTINUE_WITH_NOTES' if usable else 'NO_USABLE_MODEL',
        'selected':'readyset_checked_model' if endpoint else 'verified_constructed_model' if usable else None,
        'requires_cif_review':False,'automatic_adoption':False,
        'notes':['Geometry/scientific qualification and the declared eight-pair live run remain separate.']
            +([] if endpoint else ['The optional ReadySet/native roundtrip was not selected; retain the verified constructed start.'] if usable else [])}


def _consumer_matches(record,consumer,installation):
    def matching(rows,pins):
        return len(rows)==len(pins) and all(sum(v['historical_path'].endswith('/'+p['path'])
            and v['sha256']==p['sha256'] for p in pins)==1 for v in rows) and all(sum(
            v['historical_path'].endswith('/'+p['path']) and v['sha256']==p['sha256'] for v in rows)==1 for p in pins)
    actual=record.get('native_validation',{})
    return (record.get('phenix_version')==consumer['version'] and record.get('executable_sha256')==consumer['executable_sha256']
        and len(consumer['api_sources'])==8 and len(consumer['energy_sources'])==3
        and matching(actual.get('installed_api_sources',[]),consumer['api_sources'])
        and matching(actual.get('energy_inventory',{}).get('installed_sources',[]),consumer['energy_sources']))


def audit_cached_model(reference_model,model,canonical_capture,resources,phenix,consumer,output,*,timeout_seconds=120):
    """One whole-model ReadySet control between two bounded fixed native reads.

    Resolve saved current-consumer dictionaries before calling this function.
    Explicit linked-site contexts and isolated source qualifications are required;
    no residue name, pair intent or chemistry is inferred here. The canonical
    comparison is a verified saved capture, with fresh matching implementation
    fingerprints required. The ordinary ReadySet arguments/kernels stay unchanged.
    """
    from hashlib import sha256
    import json,math
    from .cif_construction_native import prepare_constructed_native,qualify_constructed_native
    from .cif_native_validation import inspect_native_bundle
    from .cif_postmr_cache import verify_current_consumer
    from .cif_postmr_readyset import audit_readyset_bundle_consumption,read_readyset_consumption
    from .ligand_profiles import combine_dictionary_inputs
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=180:
        raise ValueError('Whole-model ReadySet deadline must be in (0,180] seconds')
    output=Path(output).absolute()
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):raise ValueError('Require fresh cached-model output')
    output.mkdir(parents=True)
    preparation=prepare_constructed_native(reference_model,model,resources,output/'prepared')
    refs=preparation['outputs'];root=output/'prepared';initial=root/refs['model']['path'];reference=root/refs['reference']['path']
    dictionaries=[root/r['path'] for r in refs['dictionaries']];phils=[root/r['path'] for r in refs['phils']]
    entries=[{'component':code,'context':context,'preparation':preparation['preparations'][code],
        'projected':root/refs['projections'][context['site']]['path']} for code,row in resources.items() for context in row['contexts']]
    inputs=output/'bundle_inputs';inputs.mkdir();combined=inputs/'dictionaries.cif';sources=inputs/'sources.cif'
    combine_dictionary_inputs([root/'preparations'/c/preparation['preparations'][c]['outputs']['dictionary']['path'] for c in sorted(resources)],combined)
    combine_dictionary_inputs([Path(resources[c]['source']) for c in sorted(resources)],sources)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'PREPARED_ONLY','preparation':preparation,
        'scope':'PRESERVED_CONSTRUCTED_WHOLE_MODEL; CACHED_NUMERICS_AND_EXPLICIT_LINKED_CONTEXTS',
        'components':sorted(resources),'before':{'status':'NOT_RUN'},'readyset':{'status':'NOT_RUN'},'after':{'status':'NOT_RUN'},
        'before_qualification':{'status':'NOT_RUN'},'after_qualification':{'status':'NOT_RUN'},'roundtrip':{'status':'NOT_RUN'},
        'new_native_calls':0,'new_readyset_calls':0,'requires_cif_review':False,'automatic_adoption':False,
        'canonical_reference':'VERIFIED_SAVED_CAPTURE; CURRENT_CONSUMER_MATCH_REQUIRED',
        'policy_authority':'NARestraints','policy_recompilation':'NOT_RUN','dictionary_generation_requested':False,
        'model_optimization_requested':False,'native_internals':'NOT_EXHAUSTIVELY_INSTRUMENTED',
        'production_checkpoint':'NOT_CREATED','scientific_qualification':'NOT_ASSESSED',
        'fallback':'VERIFIED_CONSTRUCTED_START; NO_STUDENT_CIF_APPROVAL',
        'remaining_work':['Explicit NARestraints pair/stack membership on the intended eight-pair live model.',
            'Ordinary end-to-end run, observations, refinement, solution PDF and scientific qualification.']}
    def capture(native):
        return {'directory':{'anchor':'cached_model_directory','path':Path(native['native_directory']).relative_to(output).as_posix()},**native}
    def interpret(path,cifs,name):
        native=inspect_native_bundle(path,cifs,output/name,phenix.executables['phenix.python'],environment=phenix.environment,
            phenix_version=phenix.version,timeout_seconds=min(timeout_seconds,60),phil_files=phils,
            phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',policy_inventory=True,energy_inventory=True)
        if 'returncode' in native.get('execution',{}):report['new_native_calls']+=1
        return native
    def usable(record):
        return (record.get('execution',{}).get('returncode')==0 and record['execution'].get('status')=='COMPLETED'
            and record.get('source_preserved') is True and record.get('frozen_inputs_preserved') is True
            and not record.get('symlink_outputs') and _consumer_matches(record,consumer,phenix))
    if phenix:
        verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer)
        if not _consumer_matches(canonical_capture,consumer,phenix):raise ValueError('Saved canonical reference consumer differs')
        before=interpret(initial,dictionaries,'native_before');report['before']=capture(before)
        if usable(before):
            report['before_qualification']=qualify_constructed_native(canonical_capture['native_validation'],before['native_validation'],reference,initial,entries)
    initial_usable=report['before_qualification'].get('mechanics_checks_pass') is True
    if phenix is None or initial_usable:
        control=audit_readyset_bundle_consumption(sources,combined,initial,sorted(resources),phenix,consumer,output/'readyset_consumption',timeout_seconds=timeout_seconds)
        report['readyset']={'directory':{'anchor':'cached_model_directory','path':'readyset_consumption'},**control}
        if 'returncode' in control['execution']:report['new_readyset_calls']+=1
        loaded=read_readyset_consumption(output/'readyset_consumption')
        if phenix and control['status']=='READYSET_CACHED_INPUT_PASS':
            final=output/'readyset_consumption'/control['readyset_model']['path']
            mods=[root/'preparations'/c/preparation['preparations'][c]['outputs']['modifications']['path'] for c in sorted(resources)]
            after=interpret(final,[loaded['dictionary'],*mods],'native_after');report['after']=capture(after)
            if usable(after):
                report['after_qualification']=qualify_constructed_native(canonical_capture['native_validation'],after['native_validation'],reference,final,entries)
                report['roundtrip']=qualify_cached_model_roundtrip(before['native_validation'],after['native_validation'],initial,final)
    endpoint_usable=(report['after_qualification'].get('mechanics_checks_pass') is True
        and report['roundtrip'].get('mechanics_checks_pass') is True)
    report['decision']=coordinate_decision(initial_usable,report['readyset']['status']=='READYSET_CACHED_INPUT_PASS',endpoint_usable)
    if phenix is None:report['decision']={'status':'NOT_ASSESSED','selected':None,'requires_cif_review':False,'automatic_adoption':False,'notes':['Prepared inputs only; no native process.']}
    report['status']='PREPARED_ONLY' if phenix is None else 'POSTMR_CACHED_MODEL_PASS' if endpoint_usable else 'REVIEW'
    if phenix:verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],consumer)
    report['outputs']=[]
    for path in sorted(output.rglob('*')):
        if path.is_symlink():raise ValueError('Unexpected cached-model output symlink')
        if path.is_file() and path.name!='cached_model.json':
            data=path.read_bytes();report['outputs'].append({'anchor':'cached_model_directory','path':path.relative_to(output).as_posix(),
                'size':len(data),'sha256':sha256(data).hexdigest()})
    (output/'cached_model.json').write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return report


def read_cached_model(directory):
    """Check frozen whole-model artifacts after relocation; no source host reads."""
    from hashlib import sha256
    import json
    root=Path(directory)
    if any(p.is_symlink() for p in [root,*root.parents]):raise ValueError('Unsafe cached-model directory')
    if (root/'cached_model.json').is_symlink():raise ValueError('Unsafe cached-model report')
    report=json.loads((root/'cached_model.json').read_bytes())
    if report.get('policy_id')!=POLICY_ID or report.get('requires_cif_review') is not False:raise ValueError('Cached-model policy differs')
    seen=set()
    for ref in report['outputs']:
        name=ref['path']
        if (ref.get('anchor')!='cached_model_directory' or not isinstance(name,str) or name.startswith('/')
                or '\\' in name or ':' in name or any(p in {'','.','..'} for p in name.split('/')) or name in seen):
            raise ValueError('Unsafe cached-model artifact reference')
        path=root/name
        if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('Symlinked cached-model artifact')
        data=path.read_bytes()
        if len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Cached-model artifact changed')
        seen.add(name)
    return report
