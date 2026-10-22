"""Separate source-declared DNA headers and native-equivalence decisions.

Only classification metadata changes. Numerical/chemical rows and every native
kernel stay fixed. This isolated diagnostic does not adopt a linked dictionary.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

from .cif_linked_preparation import component_values,_render
from .cif_candidate_usability import (reassess_complete_candidate,qualify_candidate_native,
    covalent_proxy_signature,_close)

POLICY_ID='cif-source-declared-dna-metadata-v1'
_FIELDS={'_chem_comp.group','_chem_comp.type'}
_UNKNOWN={'','.','?'}


def _source_declarations(source,code):
    raw=component_values(source,code)
    def one(key):
        column=raw.get(key,[])
        if len(column)>1:raise ValueError('Ambiguous source classification')
        return str(column[0]).strip().upper() if column else ''
    group,kind=one('_chem_comp.group'),one('_chem_comp.type')
    if (group not in _UNKNOWN|{'DNA'} or kind not in _UNKNOWN|{'DNA LINKING'}
            or (group!='DNA' and kind!='DNA LINKING')):raise ValueError('Require explicit consistent source DNA classification')
    return {k:raw[k] for k in _FIELDS if k in raw}


def _same_rows(a,b):
    allowed=_FIELDS|{'data_'}
    return {k:v for k,v in a.items() if k not in allowed}=={k:v for k,v in b.items() if k not in allowed}


def prepare_source_dna_metadata(source,numerical,code,output_directory):
    """Translate explicit DNA group/type declarations; never infer from atoms."""
    source,numerical=Path(source),Path(numerical);before=source.read_bytes(),numerical.read_bytes()
    out=Path(output_directory)
    if out.exists() or out.is_symlink():raise FileExistsError(out)
    if any(p.is_symlink() for p in out.parents):raise ValueError('Output parent cannot traverse a symlink')
    if any(out.resolve()==p.resolve() or p.parent.resolve() in out.resolve().parents for p in [source,numerical]):
        raise ValueError('Output must be separate from preserved input directories')
    declarations=_source_declarations(source,code);values=component_values(numerical,code)
    assessment=reassess_complete_candidate(source,numerical,code)
    if assessment['candidate_status']!='CANDIDATE_REVIEW':raise ValueError('Require a source-preserving complete candidate')
    after=deepcopy(values);after.update({'_chem_comp.group':['DNA'],'_chem_comp.type':['DNA LINKING']})
    changes=[{'field':k,'before':values.get(k),'after':after[k]} for k in sorted(_FIELDS) if values.get(k)!=after[k]]
    payload=_render(after,code).encode() if changes else before[1]
    out.mkdir(parents=True);candidate=out/'candidate.cif'
    with candidate.open('xb') as f:f.write(payload)
    restored=component_values(candidate,code)
    if not _same_rows(restored,values) or any(restored.get(k)!=after[k] for k in _FIELDS):raise ValueError('Metadata serialization changed preserved rows')
    if before!=(source.read_bytes(),numerical.read_bytes()):raise ValueError('Metadata preparation changed an input')
    receipt={'schema_version':1,'policy_id':POLICY_ID,'component':code,'status':'SEPARATE_METADATA_CANDIDATE',
        'source_sha256':sha256(before[0]).hexdigest(),'base_candidate_sha256':sha256(before[1]).hexdigest(),
        'source_declarations':declarations,'metadata_changes':changes,'numerical_and_chemical_rows_preserved':True,
        'candidate':{'anchor':'candidate_directory','path':'candidate.cif','sha256':sha256(payload).hexdigest(),'size':len(payload)},
        'source_assessment':assessment,'native_equivalence':'NOT_RUN','linked_context':'NOT_RUN',
        'automatic_adoption':False,'requires_cif_review':False}
    with (out/'metadata_receipt.json').open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    return receipt


def qualify_source_dna_metadata(source,base,prepared,model,code,original,native):
    """Require the source-declared header and identical isolated mechanics."""
    _source_declarations(source,code)
    baseline=qualify_candidate_native(source,base,model,code,original)
    if not baseline['native_usable']:raise ValueError('Require an independently usable saved baseline')
    candidate=qualify_candidate_native(source,prepared,model,code,native)
    values=component_values(prepared,code);checks={
        'header_only_definition_change':_same_rows(component_values(base,code),values),
        'source_classification_header':values.get('_chem_comp.group')==['DNA'] and values.get('_chem_comp.type')==['DNA LINKING'],
        'candidate_native_usable':candidate['native_usable']}
    rows=native.get('monomer_mappings',{}).get('rows',[])
    meta=rows[0].get('metadata',{}) if len(rows)==1 else {}
    checks['native_group_dna']=meta.get('group')=='DNA'
    checks['native_classification_dna']=meta.get('classification')=={'status':'RECORDED','value':'DNA'}
    checks['same_fixed_covalent_proxies']=candidate['native_usable'] and covalent_proxy_signature(original)==covalent_proxy_signature(native)
    same=False
    if candidate['native_usable']:
        def named(n):
            gradient=n['energy_inventory']['snapshots'][0]['gradient']
            return {a['atom_id']:gradient[3*a['i_seq']:3*a['i_seq']+3] for a in n['atoms']}
        a,b=named(original),named(native)
        same=(a.keys()==b.keys() and _close(original['energy_inventory']['snapshots'][0]['target'],native['energy_inventory']['snapshots'][0]['target'])
            and all(_close(x,y) for name in a for x,y in zip(a[name],b[name])))
    checks['same_full_target_and_named_gradient']=same
    return {'schema_version':1,'policy_id':POLICY_ID,'component':code,'checks':checks,
        'status':'SOURCE_DNA_METADATA_NATIVE_PASS' if all(checks.values()) else 'REVIEW','native_equivalent':all(checks.values()),
        'baseline_qualification':baseline,'candidate_qualification':candidate,'linked_context':'NOT_RUN',
        'nonbonded_pair_identity_equivalence':'NOT_ASSESSED','automatic_adoption':False,'requires_cif_review':False}


def classification_decision(base,prepared,code,original_decision,new_native_usable):
    """Prefer verified source metadata, with the qualified original as fallback."""
    from .cif_doctor_selection import ComponentCandidate,select_component_candidate
    base=Path(base);old=original_decision
    if (old.get('continue_solving') is not True or old.get('scope')!='ISOLATED_COMPONENT_ONLY'
            or old.get('selected_sha256')!=sha256(base.read_bytes()).hexdigest()):raise ValueError('Require the verified isolated fallback decision')
    shared=dict(component=code,source_priority=0,chemistry_sha256=old['chemistry_sha256'],integrity_verified=True,
        stereochemistry=old['selected_stereochemistry'],converged=old.get('converged'))
    convergence='The bounded component optimization did not converge; a usable saved candidate was retained.'
    notes=tuple(dict.fromkeys(v for v in old.get('notes',[]) if v!=convergence))
    rows=[]
    if prepared is not None:
        rows.append(ComponentCandidate(candidate_id='source_declared_dna',artifact_sha256=sha256(Path(prepared).read_bytes()).hexdigest(),
            native_usable=new_native_usable,chemistry_preserved=new_native_usable,essential_restraints_present=new_native_usable,
            finite_parameters=new_native_usable,warnings=notes+('Source-declared DNA metadata retained with verified isolated mechanical equivalence; linked qualification remains separate.',),**shared))
    rows.append(ComponentCandidate(candidate_id='verified_generated_fallback',artifact_sha256=old['selected_sha256'],native_usable=True,
        chemistry_preserved=True,essential_restraints_present=True,finite_parameters=True,
        warnings=notes+('Source metadata candidate was not qualified; the verified generated dictionary was retained.',),**shared))
    result=select_component_candidate(rows)
    result.update(scope='ISOLATED_COMPONENT_ONLY',linked_adoption='NOT_RUN',production_pipeline='UNCHANGED',metadata_policy_id=POLICY_ID)
    return result
