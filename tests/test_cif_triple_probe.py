"""Public controls are read at fixed isolated seeds without choosing NA roles."""
from pathlib import Path
import json
from nasolve.cif_triple_probe import run_triple_controls
from types import SimpleNamespace
from tests.test_cif_triple_bond_audit import fixture


def test_pdu_and_5pc_offline_control_reports_exact_distinct_triple_atoms(tmp_path):
    public=Path(__file__).resolve().parents[1]/'tests/fixtures/public_ccd'
    sources={c:public/(c+'.cif') for c in ['PDU','5PC']};before={c:p.read_bytes() for c,p in sources.items()}
    r=run_triple_controls(sources,{},tmp_path/'audit')
    assert r['native_execution']=='NOT_RUN' and r['dictionary_generation']=='NOT_RUN'
    for code,pair in [('PDU',['C5A','C5B']),('5PC',['C7','C8'])]:
        case=r['cases'][code];screen=case['offline']['public_source']
        assert screen['triple_bonds'][0]['atoms']==pair and screen['coordinate_screen']=='PASS'
        assert screen['target_screen']=='REVIEW' and case['native']=={}
        assert case['model_preparation']['experimental_model_used'] is False and sources[code].read_bytes()==before[code]
    assert json.loads((tmp_path/'audit/triple_control_receipt.json').read_text())==r


def test_native_cases_keep_same_fixed_model_and_explicit_lookup_selection(tmp_path,monkeypatch):
    import nasolve.cif_triple_probe as module
    folder=tmp_path/'input';folder.mkdir();source,v=fixture(folder);calls=[]
    def capture(root,exe,api,code,output,**kwargs):
        output.mkdir(parents=True);(output/'installed_component.cif').write_bytes(source.read_bytes())
        return {'result':{'status':'RECORDED'},'fixture':'FAKE_RESOURCE_CAPTURE'}
    monkeypatch.setattr(module,'capture_installed_component',capture)
    monkeypatch.setattr(module,'verify_component_capture',lambda *args:True)
    def inspect(model,paths,output,exe,**kwargs):
        output.mkdir(parents=True);work=output/'native';work.mkdir()
        calls.append((model.read_bytes(),kwargs['phil_files'][0].read_bytes(),[p.name for p in paths],kwargs['installed_library_only']))
        atoms=[{'i_seq':i,'atom_id':n,'element':'C','xyz':[float(v['_chem_comp_atom.pdbx_model_Cartn_'+a+'_ideal'][i]) for a in 'xyz'],
                'identity':{'resname':'Q17','chain_id':'A','resseq':'1'}} for i,n in enumerate(v['_chem_comp_atom.atom_id'])]
        return {'status':'REVIEW','native_directory':str(work),'native_validation':{'status':'REVIEW','atoms':atoms,
            'restraint_policy':{'secondary_structure_enabled':False},'monomer_mappings':{'rows':[{'metadata':{
                'effective_definition':{'bonds':[{'atom_id_1':'X','atom_id_2':'Y','type':'triple'}]}}}]},
            'geometry':{'proxy_details':{'bond_simple':[{'i_seqs':[1,2],'distance_ideal':1.2,'weight':2500.}],
                'bond_asu':[],'angle':[{'i_seqs':[0,1,2],'angle_ideal':180.,'weight':1/9},
                                    {'i_seqs':[1,2,3],'angle_ideal':180.,'weight':1/9}],'dihedral':[],'const_dihedral':[]}}}}
    monkeypatch.setattr(module,'inspect_native_bundle',inspect)
    phenix=SimpleNamespace(root=tmp_path/'phenix',executables={'phenix.python':tmp_path/'phenix/python'},environment={},version='FAKE')
    r=run_triple_controls({'Q17':source},{'Q17':source},tmp_path/'audit',phenix=phenix)
    assert len(calls)==3 and len({(c[0],c[1]) for c in calls})==1
    assert [(c[2],c[3]) for c in calls]==[([],True),(['installed_component.cif'],False),(['source.cif'],False)]
    case=r['cases']['Q17'];assert case['installed_lookup_snapshot_terms_match'] is True
    assert all(row['triple_screen']['status']=='TRIPLE_SCREEN_PASS' for row in case['native'].values())
    assert r['model_optimization']=='NOT_RUN' and r['dictionary_generation']=='NOT_RUN'
