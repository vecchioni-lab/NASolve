"""Reconcile descriptive aliases only when every operational atom role agrees."""
from copy import deepcopy

ANNOTATION_COLUMNS = {'C5-mod', 'C7-mod'}
_METADATA = {'Ligand code','Name','Abbreviation','Base Analog','Phosphate','Sugar Type','SugarType',
    'Saenger','Notes','Ref','Entries','Function','Source sheet','Glycosidic atom'}
_CONTEXT = ('Base Analog','Phosphate','Sugar Type','SugarType','Saenger','Function','Source sheet','Glycosidic atom')


def role_signature(record):
    return {'context':{k:record.get(k) for k in _CONTEXT},
        'atom_roles':{k:str(v).strip() for k,v in record.items()
            if k not in _METADATA|ANNOTATION_COLUMNS and v not in (None,'')}}


def resolve_component_record(records, code):
    """Return one unchanged operational mapping; never choose among conflicts."""
    matches=[r for r in records if str(r.get('Ligand code'))==code]
    signatures=[role_signature(r) for r in matches]
    if not matches or any(s!=signatures[0] for s in signatures):
        raise ValueError('Require one unambiguous NARestraints operational record for '+code)
    selected=deepcopy({k:v for k,v in matches[0].items() if k not in ANNOTATION_COLUMNS})
    return selected,{'resolution':'EQUIVALENT_ROLE_RECORDS' if len(matches)>1 else 'UNIQUE_RECORD',
        'matching_records':len(matches),'operational_role_signature':deepcopy(signatures[0]),
        'source_policy_records':deepcopy(matches)}
