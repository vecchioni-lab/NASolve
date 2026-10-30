"""Opt-in complete monomer evidence from native full-model interpretation.

The native parameter is checked, never silently changed by the worker. Missing
copied-chain mappings must be interpreted afresh, not inferred from a master.
The helper is also embedded verbatim in the isolated native worker.
"""
from inspect import getsource
import json

POLICY_ID='cif-native-full-monomer-inventory-v1'
FULL_MODEL_PHIL='pdb_interpretation {\n  use_ncs_to_build_restraints = False\n}\n'


def capture_full_monomers(native, use_ncs_to_build_restraints):
    if use_ncs_to_build_restraints is not False:
        raise ValueError('Full monomer inventory requires explicit native restraint-copying policy False')
    fields=('model_id','chain_id','resseq','icode','resname','altloc')
    def identity(row):
        if not isinstance(row,dict) or any(not isinstance(row.get(k),str) for k in fields):
            raise ValueError('Incomplete native residue identity')
        key=tuple(row[k].strip() for k in fields)
        if not key[2] or not key[4]:raise ValueError('Blank native residue identity')
        return key
    atoms=native.get('atoms')
    if (not isinstance(atoms,list) or not atoms or type(native.get('atom_count')) is not int
            or native['atom_count']!=len(atoms)):
        raise ValueError('Missing complete native atom inventory')
    expected={identity(a.get('identity')) for a in atoms}
    mappings=native.get('monomer_mappings',{})
    if mappings.get('status')!='RECORDED' or not isinstance(mappings.get('rows'),list):
        raise ValueError('Missing complete native monomer mappings')
    actual=[]
    for row in mappings['rows']:
        literal=row.get('literal_identity',{})
        if literal.get('status')!='RECORDED':raise ValueError('Native monomer identity was not recorded')
        key=identity(literal)
        if (row.get('resname')!=key[4] or row.get('site')!=key[1]+':'+key[2]+key[3]
                or not isinstance(row.get('chain_id'),str) or row['chain_id'].strip()!=key[1]):
            raise ValueError('Inconsistent native monomer identity')
        actual.append(key)
    if len(actual)!=len(set(actual)) or set(actual)!=expected:
        raise ValueError('Native monomer identities do not cover the complete interpreted model exactly once')
    return dict(schema_version=1,policy_id='cif-native-full-monomer-inventory-v1',status='RECORDED',
        use_ncs_to_build_restraints=False,atom_count=len(atoms),residue_count=len(expected),
        mapping_count=len(actual),identities=[dict(zip(fields,key)) for key in sorted(expected)])


def review_full_monomers(native):
    proof=native.get('full_monomer_inventory')
    if not isinstance(proof,dict):raise ValueError('Missing full native monomer inventory proof')
    expected=capture_full_monomers(native,proof.get('use_ncs_to_build_restraints'))
    if json.dumps(proof,sort_keys=True,allow_nan=False)!=json.dumps(expected,sort_keys=True,allow_nan=False):
        raise ValueError('Full native monomer inventory proof differs from captured identities')
    return proof


def native_monomer_worker(base):
    header='try:\n    from iotbx import phil\n'
    process='    processed = pdb_interpretation.process(mon_lib_srv=mon_lib, ener_lib=energies,\n'
    check='    if report["fatal_problems"] is not None:\n'
    for token in (header,process,check):
        if base.count(token)!=1:raise ValueError('Unsupported native monomer worker structure')
    guard='''    if getattr(params.pdb_interpretation, "use_ncs_to_build_restraints", None) is not False:
        raise UnsupportedNativeAPI("Full monomer inventory requires explicit use_ncs_to_build_restraints=False")
'''
    capture='''    report["full_monomer_inventory"] = capture_full_monomers(
        report, params.pdb_interpretation.use_ncs_to_build_restraints)
    save()
'''
    return base.replace(header,getsource(capture_full_monomers)+'\n'+header).replace(
        process,guard+process).replace(check,capture+check)
