"""Geometry libraries and CCD chemistry sources are distinct resource classes."""
from pathlib import Path
from hashlib import sha256
import json,os,sys
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_installed_ccd_comparison_records_descriptors_without_treating_text_as_graph_proof(tmp_path):
    from nasolve.cif_installed_source_catalogue import compare_installed_ccd
    public=ROOT/'tests/fixtures/public_ccd/PDU.cif';copy=tmp_path/'installed.cif';copy.write_bytes(public.read_bytes())
    before=public.read_bytes(),copy.read_bytes();r=compare_installed_ccd(public,copy,'PDU')
    assert r['chemical_declarations']=='EXACT_DECLARATIONS' and r['triple_bonds']==[['C5A','C5B']]
    assert r['descriptor_text_comparison']=='TEXT_IDENTICAL' and len(r['descriptors'])==4
    assert r['mapped_smiles_graph_comparison']=='NOT_RUN' and r['dictionary_parameterization']=='UNASSESSED'
    assert r['optimization']=='NOT_RUN' and before==(public.read_bytes(),copy.read_bytes())


@pytest.mark.parametrize('mode',['pass','missing_ccd','wrong_ccd','changed_bond','changed_descriptor','direct_only','missing_api','escape_source','changed_api','timeout'])
def test_selected_source_catalogue_freezes_exact_ccd_and_never_runs_generation(tmp_path,mode):
    from nasolve.cif_installed_source_catalogue import audit_installed_sources,verify_installed_sources
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages'
    for name in ['mmtbx','mmtbx/monomer_library','elbow','elbow/utilities']:
        p=site/name;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_text('')
    source=ROOT/'tests/fixtures/public_ccd/PDU.cif';ccd=site/'chem_data/chemical_components/p/data_PDU.cif';ccd.parent.mkdir(parents=True)
    data=source.read_bytes()
    if mode=='wrong_ccd':data=data.replace(b'PDU',b'QQQ')
    if mode=='changed_bond':data=data.replace(b'TRIP',b'SING')
    if mode=='changed_descriptor':data=data.replace(b'CC#C',b'CCCC')
    if mode!='missing_ccd':ccd.write_bytes(data)
    monomer=root/'mon_lib/p/PDU.cif';monomer.parent.mkdir(parents=True);monomer.write_text('data_PDU\n# FAKE MONOMER\n')
    server=site/'mmtbx/monomer_library/server.py'
    server.write_text('''from pathlib import Path
from types import SimpleNamespace as NS
class Row:
    def __init__(self,**kw):self.__dict__.update(kw)
    def cif_keywords(self):return list(vars(self))
class server:
    def __init__(self):self.root_path=ROOT+'/mon_lib';self.geostd_path=ROOT+'/geostd'
    def get_comp_comp_id_direct(self,comp_id):
        if MODE=='timeout':
            import time;time.sleep(30)
        if MODE=='changed_api':Path(__file__).write_text('# CHANGED')
        if MODE!='direct_only':return None
        return NS(chem_comp=Row(id=comp_id),source_info='file: '+MONOMER,
            atom_list=[],bond_list=[],angle_list=[],tor_list=[],chir_list=[],plane_atom_list=[])
    def get_comp_comp_id_and_atom_name_interpretation(self,residue_name,atom_names):
        assert atom_names==[]
        if residue_name in ['DG','DC']:
            return NS(chem_comp=Row(id=residue_name[-1]),source_info='canonical in-memory control'),None
        return None,None
'''.replace('ROOT',repr(str(root))).replace('MODE',repr(mode)).replace('MONOMER',repr(str(monomer))))
    proof=[]
    for name in ['mmtbx/monomer_library/server.py','mmtbx/monomer_library/cif_types.py','elbow/utilities/Utilities.py']:
        p=site/name
        if p!=server:p.write_text('# FAKE SELECTED SOURCE\n')
        proof.append({'anchor':'phenix_installation','path':p.relative_to(root).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size})
    for name in ['elbow/utilities/geostd_utils.py','elbow/utilities/mmtbx_utils.py','mmtbx/chemical_components/__init__.py']:
        p=site/name;p.parent.mkdir(exist_ok=True)
        if mode!='missing_api':p.write_text('raise RuntimeError("SOURCE CAPTURE MUST NOT EXECUTE")\n')
    if mode=='escape_source':
        p=site/'elbow/utilities/mmtbx_utils.py';p.unlink();outside=tmp_path/'outside.py';outside.write_text('# OUTSIDE');p.symlink_to(outside)
    exe=root/'bin/phenix.python';exe.parent.mkdir();exe.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');exe.chmod(0o755)
    ready=exe.with_name('phenix.ready_set');ready.write_text('raise RuntimeError("READYSET MUST NOT EXECUTE")\n')
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    call=lambda:audit_installed_sources(root,exe,ready,api,proof,{'PDU':source},tmp_path/'catalogue',environment=os.environ,
        timeout_seconds=.1 if mode=='timeout' else 30)
    if mode in ['escape_source','changed_api','timeout']:
        with pytest.raises(ValueError):call()
    else:
        r=call();case=r['components']['PDU']
        assert r['readyset_execution']=='NOT_RUN' and r['dictionary_generation']=='NOT_RUN' and r['optimization']=='NOT_RUN'
        assert r['native_resources']['lookups']['PDU']['wrapped']['status']=='MISSING'
        assert r['native_resources']['lookups']['PDU']['direct']['status']==('RECORDED' if mode=='direct_only' else 'MISSING')
        assert case['status']==('MISSING' if mode=='missing_ccd' else 'REVIEW' if mode=='wrong_ccd' else 'RECORDED')
        if mode not in ['missing_ccd','wrong_ccd']:
            comparison=case['comparison']
            assert comparison['chemical_declarations']==('REVIEW' if mode=='changed_bond' else 'EXACT_DECLARATIONS')
            assert comparison['descriptor_text_comparison']==('TEXT_DIFFERENT' if mode=='changed_descriptor' else 'TEXT_IDENTICAL')
        assert verify_installed_sources(root,r,tmp_path/'catalogue')
        (site/proof[-1]['path'].split('site-packages/')[1]).write_text('# CHANGED')
        with pytest.raises(ValueError):verify_installed_sources(root,r,tmp_path/'catalogue')
