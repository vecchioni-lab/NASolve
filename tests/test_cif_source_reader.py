"""Fake selected-installation reads test integrity, never native qualification."""
import json,os,sys
import pytest
from tests.test_cif_stereochemistry_audit import tetrahedron,write
from nasolve.cif_source_reader import audit_source_reader,verify_source_reader_capture,SOURCE_PATHS,CHARGE_SOURCE_PATHS


@pytest.mark.parametrize('mode',['pass','single_list','multiple_list','monomer','charge','coordinates','bond','element','wrong_route','exception','changed_input','changed_source','changed_snapshot','escaped_module',
                                'control_pass','control_conflict','control_bond','control_proof'])
def test_native_source_reader_preserves_scope_and_keeps_readback_disagreements(tmp_path,mode):
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages'
    for name in ['elbow','elbow/chemistry','elbow/formats']:
        p=site/name;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_text('')
    module=site/SOURCE_PATHS[0];other=site/SOURCE_PATHS[1];other.write_text('# FAKE_INSTALLED_MONOMER_READER\n')
    v,_=tetrahedron();control=mode.startswith('control_')
    if control:v['_chem_comp_atom.charge'][1]='-1'
    source=write(tmp_path/'input/source.cif',v)
    if mode=='monomer' or control:
        from nasolve.cif_linked_preparation import _render
        source.write_text(_render(v,'Q17'))
    atoms=[{'name':n,'symbol':e,'charge':1 if (mode=='charge' and i==0 or mode=='control_conflict' and i==1) else 0,
            'xyz':{axis:float(v['_chem_comp_atom.pdbx_model_Cartn_'+axis+'_ideal'][i])+(1 if mode=='coordinates' and axis=='x' else 0) for axis in 'xyz'},
            'chiral':'R' if i==0 else ''} for i,(n,e) in enumerate(zip(v['_chem_comp_atom.atom_id'],v['_chem_comp_atom.type_symbol']))]
    if mode=='element':atoms[1]['symbol']='S'
    body='''from types import SimpleNamespace
from pathlib import Path
class Bond(list):order=ORDER
class Molecule(list):
    charge=0
    def GetOriginalFormat(self):return FORMAT
    def Chiralise(self,*a,**k):raise RuntimeError('CHIRAL CONSTRUCTOR MUST NOT RUN')
def is_chemical_components_file(data):return DISPATCH
def any_chemical_format_reader(data,simple=True,return_all_restraints=True,do_not_check_for_smiles=False):
    assert simple and return_all_restraints and do_not_check_for_smiles
    if MODE=='exception':raise ValueError('fake parser failure')
    if MODE=='changed_input':Path(data).write_text('CHANGED')
    if MODE=='changed_source':Path(__file__).write_text('# CHANGED')
    if MODE=='changed_snapshot':Path('elbow/formats/monomer_library_cif_parser.py.txt').write_text('# CHANGED')
    rows=ATOMS
    m=Molecule(SimpleNamespace(**{**r,'xyz':SimpleNamespace(**r['xyz'])}) for r in rows)
    m.bonds=[Bond([m[0],n]) for n in m[1:]]
    if MODE=='single_list':return [m]
    if MODE=='multiple_list':return [m,m]
    return m
'''.replace('ORDER',repr(2 if mode in ['bond','control_bond'] else 1)).replace('FORMAT',repr('CIF' if mode in ['wrong_route','monomer'] or control else 'CHEMICAL COMPONENTS')).replace('MODE',repr(mode)).replace('ATOMS',repr(atoms)).replace('DISPATCH',repr(mode!='monomer' and not control))
    module.write_text(body)
    if mode=='escaped_module':
        outside=tmp_path/'outside.py';outside.write_text(body);module.unlink();module.symlink_to(outside)
    python=root/'bin/phenix.python';python.parent.mkdir(parents=True)
    python.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');python.chmod(0o755)
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    proof=[]
    if control:
        from hashlib import sha256
        for name in CHARGE_SOURCE_PATHS:
            path=site/name;path.parent.mkdir(exist_ok=True);(path.parent/'__init__.py').touch()
            data=b'# EXPLICIT FAKE INSTALLED CHARGE API\n';path.write_bytes(data)
            proof.append({'anchor':'phenix_installation','path':path.relative_to(root).as_posix(),'sha256':sha256(data).hexdigest(),'size':len(data)})
        if mode=='control_proof':proof[0]['sha256']='0'*64
    options={'declared_charge_control':True,'charge_source_proof':proof} if control else {}
    out=tmp_path/'read';env={**os.environ,'PYTHONPATH':str(site),'PYTHONDONTWRITEBYTECODE':'1'}
    if mode.startswith('changed_') or mode in ['escaped_module','control_proof']:
        with pytest.raises(ValueError):audit_source_reader(root,python,api,source,'Q17',out,environment=env,expected_dialect='CHEMICAL_COMPONENTS_CIF',**options)
    else:
        r=audit_source_reader(root,python,api,source,'Q17',out,environment=env,expected_dialect='MONOMER_LIBRARY_CIF' if mode=='monomer' or control else 'CHEMICAL_COMPONENTS_CIF',**options)
        assert r['status']==('READER_ROUTE_AND_INVENTORY_PASS' if mode in ['pass','single_list','monomer'] else 'REVIEW')
        assert r['chiral_constructor']=='NOT_REQUESTED' and r['whole_molecule_optimization']=='NOT_REQUESTED'
        assert r['parser_internal_operations']=='NOT_INSTRUMENTED'
        assert r['signed_stereo_native_qualification']=='NOT_RUN' and r['native_formal_charge_semantics']=='REQUIRES_CAPTURED_PARSER_REVIEW'
        assert verify_source_reader_capture(root,r,out)
        if control:
            assert r['declared_charge_qualification']['status']==('DECLARED_CHARGE_CONTROL_PASS' if mode=='control_pass' else 'REVIEW')
            assert r['result']['atoms'][1]['native_atom_charge']==(1 if mode=='control_conflict' else 0)
            if mode=='control_pass':
                assert r['declared_charge_control']['after']['atoms'][1]['native_atom_charge']==-1
                assert all(r['declared_charge_qualification']['checks'].values())
        if mode in ['exception','multiple_list']:assert r['result']['exception_type']=='ValueError'
        else:assert r['result']['execution']=='COMPLETED'
        if mode=='single_list':assert r['result']['component_container']=='SINGLETON_LIST'
        (out/(SOURCE_PATHS[0]+'.txt')).write_text('CHANGED')
        with pytest.raises(ValueError):verify_source_reader_capture(root,r,out)
