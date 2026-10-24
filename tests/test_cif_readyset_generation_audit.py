"""Isolated ReadySet defaults preserve call provenance and failed generations."""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import os,sys
import pytest
from tests.test_cif_triple_bond_audit import fixture


def installed(tmp_path,mode):
    folder=tmp_path/'input';folder.mkdir();source,values=fixture(folder)
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages'
    for name in ['elbow','elbow/command_line','elbow/scripts']:
        p=site/name;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_text('')
    (site/'elbow/command_line/builder.py').write_text('''import optparse,sys
def run(**kwargs):
    if MODE=='nested_parser':
        parser=optparse.OptionParser()
        args=[('--'+x) if '=' in x and not x.startswith('--') else x for x in sys.argv[1:]]
        parser.parse_args(args)
    assert kwargs=={'chemical_component':'Q17','residue':'Q17','opt':False}
    if MODE=='builder_exception':raise RuntimeError('EXPLICIT FAKE BUILDER FAILURE')
    if MODE=='nonfinite':
        class Fake(list):
            bonds=[];charge=float('nan')
        return Fake()
    return None
'''.replace('MODE',repr(mode)))
    (site/'elbow/scripts/elbow_on_pdb_file.py').write_text('''def get_elbow_molecule_from_chemical_components(code):return None
''')
    ready=site/'elbow/command_line/ready_set.py'
    ready.write_text('''from pathlib import Path
from types import SimpleNamespace as NS
import os,time
from elbow.command_line import builder
from elbow.scripts import elbow_on_pdb_file as route

def run(args):
    assert 'READY_SET_LIGAND_CACHE_DIRECTORY' not in os.environ
    assert 'ready_set.actions.hydrogens=False' in args
    assert 'ready_set.actions.trust_residue_code_is_chemical_components_code=False' in args
    if MODE=='timeout':time.sleep(60)
    try:builder.run(chemical_component='Q17',residue='Q17',opt=False)
    except RuntimeError:route.get_elbow_molecule_from_chemical_components('Q17')
    if MODE=='changed_input':Path('source_seed.pdb').write_text('ALTERED')
    if MODE=='changed_source':Path(__file__).write_text('# ALTERED')
    if MODE in {'source_copy_exception','partial_exception'}:
        Path('Q17.cif').write_bytes(Path(SOURCE).read_bytes()+(b'\\n# partial output\\n' if MODE=='partial_exception' else b''))
        raise RuntimeError('EXPLICIT FAKE READYSET FAILURE')
    if MODE=='exception':raise RuntimeError('EXPLICIT FAKE READYSET FAILURE')
    if MODE!='no_candidate':
        Path('Q17.cif').write_bytes(b'INVALID NATIVE CANDIDATE' if MODE=='malformed' else Path(SOURCE).read_bytes())
        if MODE=='symlink':
            Path('Q17.cif').unlink();Path('Q17.cif').symlink_to(SOURCE)
    Path('ignored.pickle').write_bytes(b'NEVER LOAD OR COPY THIS SERIALIZED OBJECT')
    return ([],NS(ready_set=NS(actions=NS(**FLAGS))))
'''.replace('MODE',repr(mode)).replace('SOURCE',repr(str(source))).replace('FLAGS',repr({
    'hydrogens':False,'ligands':True,'optimise_ligand_geometry':False,'optimise_final_geometry_of_hydrogens':False,
    'trust_residue_code_is_chemical_components_code':False,'metals':False,'link_to_edits':False,'remove_waters':False})))
    exe=root/'bin/phenix.python';exe.parent.mkdir();exe.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');exe.chmod(0o755)
    proofs=[]
    for p in [ready,site/'elbow/command_line/builder.py',site/'elbow/scripts/elbow_on_pdb_file.py']:
        proofs.append({'anchor':'phenix_installation','path':p.relative_to(root).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size})
    if mode=='changed_proof':ready.write_text('# CHANGED BEFORE EXECUTION')
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    phenix=SimpleNamespace(root=root,executables={'phenix.python':exe},environment={**os.environ,'READY_SET_LIGAND_CACHE_DIRECTORY':'MUST_REMOVE'},version='EXPLICIT_FAKE')
    return source,phenix,api,proofs


@pytest.mark.parametrize('mode',['pass','builder_exception','exception','no_candidate','timeout','changed_input','changed_source','changed_proof','symlink','nonfinite','malformed'])
def test_readyset_call_trace_and_timeouts_never_promote_failed_or_missing_results(tmp_path,monkeypatch,mode):
    import nasolve.cif_readyset_generation_audit as m
    source,phenix,api,proofs=installed(tmp_path,mode)
    native=[]
    def inspect(model,cifs,output,executable,**kw):
        native.append((model.read_bytes(),[p.name for p in cifs],kw))
        assert kw['phil_files'][0].read_text().find('secondary_structure.enabled = False')>=0
        return {'status':'FAILED','native_validation':{'status':'FAILED'},'native_directory':str(output)}
    monkeypatch.setattr(m,'inspect_native_bundle',inspect)
    before=source.read_bytes()
    call=lambda:m.audit_readyset_controls({'Q17':source},tmp_path/'audit',phenix=phenix,api_sources=api,source_proofs=proofs,
        timeout_seconds=.1 if mode=='timeout' else 30)
    if mode in {'changed_input','changed_source','changed_proof','symlink'}:
        with pytest.raises(ValueError):call()
    else:
        r=call();case=r['cases']['Q17'];g=case['generation']
        assert r['experimental_model_changes']=='NOT_RUN' and r['automatic_adoption'] is False
        assert source.read_bytes()==before and case['model_preparation']['experimental_model_used'] is False
        if mode=='timeout':assert g['execution']['status']=='TIMED_OUT' and not native
        elif mode=='exception':assert g['result']['execution']=='EXCEPTION' and not native
        else:
            calls=g['trace']['events'];assert calls[0]['kwargs']=={'chemical_component':'Q17','residue':'Q17','opt':False}
            assert calls[0]['status']==('EXCEPTION' if mode=='builder_exception' else 'RETURNED')
            if mode=='builder_exception':assert len(calls)==2 and calls[1]['api']=='CCD_TEMPLATE'
            if mode=='nonfinite':assert calls[0]['molecule']['molecule_charge']=={'nonfinite_native_float':'nan'}
            if mode=='malformed':assert case['dictionary_triple_screen']['status']=='REVIEW' and not native
            elif mode=='no_candidate':assert g['candidate']['status']=='MISSING' and not native
            else:
                assert g['candidate']['status']=='RECORDED' and len(native)==1
                assert case['native_triple_screen']['status']=='NOT_RUN'
                assert any(p['path'].endswith('.pickle') for p in g['excluded_serialized_outputs'])
                assert not any(p['path'].endswith('.pickle') for p in g['outputs'])


def test_offline_readyset_plan_keeps_complete_and_heavy_source_seed_models(tmp_path):
    from nasolve.cif_readyset_generation_audit import audit_readyset_controls
    public=Path(__file__).resolve().parents[1]/'tests/fixtures/public_ccd/PDU.cif'
    r=audit_readyset_controls({'PDU':public},tmp_path/'audit')
    case=r['cases']['PDU'];assert r['native_execution']=='NOT_RUN' and case['generation']['execution']['status']=='NOT_RUN'
    full=(tmp_path/'audit/models/PDU/complete_source_seed.pdb').read_text();heavy=(tmp_path/'audit/models/PDU/source_seed.pdb').read_text()
    assert len(full.splitlines())>len(heavy.splitlines()) and all(line[76:78].strip() not in {'H','D','T'} for line in heavy.splitlines() if line.startswith('HETATM'))
    assert case['model_preparation']['hydrogen_policy']=='EXPLICIT_HEAVY_ATOMS_ONLY'


def test_completed_candidate_has_independent_dictionary_and_active_native_triple_screens(tmp_path,monkeypatch):
    import nasolve.cif_readyset_generation_audit as m
    source,phenix,api,proofs=installed(tmp_path,'pass')
    atoms=[{'i_seq':i,'atom_id':n,'element':'C','xyz':xyz,'identity':{'resname':'Q17','chain_id':'A','resseq':'1'}}
        for i,(n,xyz) in enumerate(zip(['L','X','Y','R'],[[-1.4,.001,0],[0,0,0],[1.2,0,0],[2.6,.001,0]]))]
    native={'status':'REVIEW','atoms':atoms,'restraint_policy':{'secondary_structure_enabled':False},
        'monomer_mappings':{'rows':[{'metadata':{'effective_definition':{'bonds':[{'atom_id_1':'X','atom_id_2':'Y','type':'triple'}]}}}]},
        'geometry':{'proxy_details':{'bond_simple':[{'i_seqs':[1,2],'distance_ideal':1.2,'weight':2500.}],
            'bond_asu':[],'angle':[{'i_seqs':[0,1,2],'angle_ideal':180.,'weight':1/9},{'i_seqs':[1,2,3],'angle_ideal':180.,'weight':1/9}],
            'dihedral':[],'const_dihedral':[]}}}
    monkeypatch.setattr(m,'inspect_native_bundle',lambda *a,**k:{'status':'REVIEW','native_validation':native,'native_directory':str(a[2])})
    r=m.audit_readyset_controls({'Q17':source},tmp_path/'audit',phenix=phenix,api_sources=api,source_proofs=proofs,timeout_seconds=30)
    c=r['cases']['Q17']
    assert c['dictionary_triple_screen']['target_screen']=='PASS' and c['native_triple_screen']['target_screen']=='PASS'
    assert c['native_triple_screen']['triple_bonds'][0]['distance']['membership_count']==1
    assert r['status']=='REVIEW' and r['scientific_approval']=='NOT_RUN' and r['automatic_adoption'] is False


def test_explicit_readyset_api_arguments_do_not_leak_into_nested_elbow_parser(tmp_path,monkeypatch):
    import nasolve.cif_readyset_generation_audit as m
    source,phenix,api,proofs=installed(tmp_path,'nested_parser')
    monkeypatch.setattr(m,'inspect_native_bundle',lambda *a,**k:{'status':'FAILED','native_validation':{'status':'FAILED'}})
    case=m.audit_readyset_controls({'Q17':source},tmp_path/'audit',phenix=phenix,api_sources=api,source_proofs=proofs)['cases']['Q17']
    g=case['generation']
    assert g['execution']['status']=='COMPLETED'
    assert g['result']['execution']=='COMPLETED',g['result']
    assert g['trace']['events'][0]['kwargs']=={'chemical_component':'Q17','residue':'Q17','opt':False}
    assert all(len(event['process_argv'])==1 for event in g['trace']['events'])
    assert 'ready_set.input.output_file_name=readyset_candidate' in g['arguments']


@pytest.mark.parametrize('mode,classification',[('pass','UNCHANGED_SOURCE_COPY'),('source_copy_exception','UNCHANGED_SOURCE_COPY'),('partial_exception','PARTIAL_OR_UNQUALIFIED_OUTPUT')])
def test_source_copy_and_partial_files_do_not_become_completed_generation_claims(tmp_path,monkeypatch,mode,classification):
    import nasolve.cif_readyset_generation_audit as m
    source,phenix,api,proofs=installed(tmp_path,mode);native=[]
    def inspect(*a,**kw):
        native.append(True);return {'status':'FAILED','native_validation':{'status':'FAILED'}}
    monkeypatch.setattr(m,'inspect_native_bundle',inspect)
    case=m.audit_readyset_controls({'Q17':source},tmp_path/'audit',phenix=phenix,api_sources=api,source_proofs=proofs)['cases']['Q17']
    g=case['generation'];assert g['candidate']['status']=='RECORDED'
    assert g['candidate']['classification']==classification
    assert g['candidate']['generation_claim']=='NOT_ESTABLISHED'
    assert g['candidate']['source_bytes_match']==(mode!='partial_exception')
    assert bool(native)==(mode=='pass')
    if mode!='pass':assert g['result']['execution']=='EXCEPTION' and case['native_triple_screen']['status']=='NOT_RUN'
