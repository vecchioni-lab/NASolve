"""Explicit source-charge transfer on an isolated parsed native component.

These functions are embedded verbatim in the selected-installation worker.
No chemical perception, chiral constructor or optimizer is called here.
"""


def native_inventory(molecule):
    def scalar(value):
        if type(value) in (str,bool,int,float,type(None)):return value
        return 'UNSUPPORTED_NATIVE_TYPE:'+type(value).__name__
    return {'atoms':[{'atom':a.name.strip(),'element':a.symbol,'native_atom_charge':scalar(a.charge),
        'native_chiral_marker':scalar(getattr(a,'chiral',None)),
        'native_volume_sign':scalar(getattr(a,'volume_sign',None)),
        'xyz':[float(a.xyz.x),float(a.xyz.y),float(a.xyz.z)]} for a in molecule],
        'bonds':[{'atoms':sorted([a.name.strip() for a in b]),'native_order':scalar(b.order)} for b in molecule.bonds],
        'molecule_charge':scalar(molecule.charge)}


def control_declared_charges(molecule,expected):
    """Populate omitted charges only after exact source-graph preconditions.

    The caller must also verify the installed charge-API sources. A raw reader
    discrepancy stays separate from this explicit population control.
    """
    import math
    before=native_inventory(molecule);atoms=before['atoms'];bonds=before['bonds']
    observed={a['atom']:a for a in atoms};declared=expected['charges'];elements=expected['elements']
    orders={tuple(b['atoms']):b['native_order'] for b in bonds}
    target_orders={tuple(b['atoms']):b['order'] for b in expected['bonds']}
    identity=len(observed)==len(atoms)==len(elements) and set(observed)==set(elements)
    coordinates=expected['coordinates']
    checks={'reader_route':molecule.GetOriginalFormat()=={'MONOMER_LIBRARY_CIF':'CIF','CHEMICAL_COMPONENTS_CIF':'CHEMICAL COMPONENTS'}.get(expected['dialect']),
        'complete_integer_source_charges':set(declared)==set(elements) and all(type(q) is int and abs(q)<=4 for q in declared.values()),
        'atom_identities':identity,
        'atom_elements':identity and all(observed[n]['element'].upper()==e for n,e in elements.items()),
        'bond_orders':len(orders)==len(bonds)==len(target_orders)==len(expected['bonds']) and orders==target_orders
            and all(type(b['native_order']) in (int,float) for b in bonds),
        'coordinates':identity and set(coordinates)==set(elements) and all(len(coordinates[n])==3 and
            all(type(x) in (int,float) and math.isfinite(x) and math.isfinite(y) and math.isclose(x,y,abs_tol=1e-9,rel_tol=0)
                for x,y in zip(coordinates[n],observed[n]['xyz'])) for n in elements)}
    report={'policy_id':'cif-explicit-source-formal-charge-control-v1','status':'BLOCKED','action':'NOT_RUN',
        'preconditions':checks,'before':before,'dictionary_generation':'NOT_RUN','optimization':'NOT_REQUESTED',
        'independent_absolute_cip_validation':'NOT_RUN','automatic_adoption':False}
    if not all(checks.values()):return report
    total=sum(declared.values());report['source_total_charge']=total
    raw={n:a['native_atom_charge'] for n,a in observed.items()}
    valid=all(type(q) in (int,float) and math.isfinite(q) for q in raw.values()) and type(before['molecule_charge']) in (int,float)
    if valid and raw==declared and before['molecule_charge']==total:
        action='ALREADY_PRESERVED'
    elif (valid and expected['dialect']=='MONOMER_LIBRARY_CIF' and all(q==0 for q in raw.values()) and before['molecule_charge']==0):
        action='POPULATED_FROM_EXPLICIT_SOURCE'
        for atom in molecule:atom.charge=declared[atom.name.strip()]
        molecule.charge=total
    else:
        report['reason']='Native charge state conflicts or the selected reader is not the reviewed monomer omission path'
        return report
    after=native_inventory(molecule)
    def other_fields(snapshot):
        return {'atoms':[{k:v for k,v in a.items() if k!='native_atom_charge'} for a in snapshot['atoms']],
                'bonds':snapshot['bonds']}
    verified={'atom_charge_values':all(a['native_atom_charge']==declared[a['atom']] and type(a['native_atom_charge']) is int for a in after['atoms']),
        'molecule_total_charge':after['molecule_charge']==total and type(after['molecule_charge']) is int,
        'other_native_fields_preserved':other_fields(before)==other_fields(after)}
    report.update(status='DECLARED_CHARGE_CONTROL_PASS' if all(verified.values()) else 'REVIEW',action=action,
        checks=verified,after=after,changed_atoms=sorted(n for n,q in raw.items() if q!=declared[n]))
    return report
