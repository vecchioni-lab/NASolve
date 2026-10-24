"""Preserve the distinction between installed CCD source and numerical evidence."""
from copy import deepcopy
from hashlib import sha256
import importlib.util,json
from pathlib import Path
import pytest


def template():
    p=Path(__file__).resolve().parents[1]/'scripts/cif_numerical_recovery_probe_template.py'
    spec=importlib.util.spec_from_file_location('cedar40_template',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


@pytest.mark.parametrize('defect',['none','generation','readyset','adoption','missing_lookup_pass','canonical_missing',
    'source_worker','snapshot','snapshot_anchor','candidate_source','reader_worker','reader_constructor','reader_orders','numerical_pass','smiles_graph_pass'])
def test_returned_catalogue_scope_cannot_promote_source_text_to_numerical_or_readyset_evidence(defect):
    m=template();members={};cat={'policy_id':'cif-installed-monomer-ccd-source-catalogue-v1',
        'automatic_adoption':False,'route_helpers':'STATIC_SOURCE_CAPTURE_ONLY_NOT_EXECUTED',
        **{k:'NOT_RUN' for k in ['readyset_execution','dictionary_generation','optimization','mapped_smiles_graph_comparison']},
        'sources':[],'components':{},'native_resources':{'lookups':{},'canonical_controls':{'DG':{'status':'RECORDED'},'DC':{'status':'RECORDED'}},
            'automatic_adoption':False,**{k:'NOT_RUN' for k in ['readyset','dictionary_generation','optimization']}}}
    def artifact(prefix,name,data,anchor):
        members[prefix+'/'+name]=data
        return {'anchor':'phenix_installation','path':'lib/python/site/'+name,'sha256':sha256(data).hexdigest(),'size':len(data),
            'snapshot':{'anchor':anchor,'path':name}}
    pre='installed_source_catalogue';cat['readyset_dispatcher']=artifact(pre,'dispatcher.txt',b'FAKE DISPATCHER','catalogue_directory')
    worker=b'raise RuntimeError("CAPTURED WORKER MUST NOT EXECUTE")\n';members[pre+'/source_catalogue_worker.py']=worker;m.CEDAR39_CATALOGUE_WORKER_SHA256=sha256(worker).hexdigest()
    readers={};m.CEDAR39_CCD_SHA256={}
    for code in ['PDU','5PC']:
        data=('FAKE CCD '+code).encode();resource=artifact(pre,code+'.cif',data,'catalogue_directory');m.CEDAR39_CCD_SHA256[code]=resource['sha256']
        cat['components'][code]={'status':'RECORDED','resource':resource,'comparison':{
            'chemical_declarations':'EXACT_DECLARATIONS','descriptor_text_comparison':'TEXT_IDENTICAL','mapped_smiles_graph_comparison':'NOT_RUN','dictionary_parameterization':'UNASSESSED'}}
        cat['native_resources']['lookups'][code]={'direct':{'status':'MISSING'},'wrapped':{'status':'MISSING'}}
        rp='installed_ccd_readers/'+code
        row={'directory':{'anchor':'probe_directory','path':rp},'result':{'fixture':'FAKE_READER'},'status':'READER_ROUTE_AND_INVENTORY_PASS',
            'source_sha256':resource['sha256'],'automatic_adoption':False,'chiral_constructor':'NOT_REQUESTED','expected_dialect':'CHEMICAL_COMPONENTS_CIF',
            'sources':[],'checks':{k:True for k in ['atom_identities','atom_elements','atom_charge_values','source_coordinates','declared_bond_orders','reader_route']},
            **{k:'NOT_RUN' for k in ['dictionary_generation','installed_phenix_edits','captured_code_execution','pickle_loading']}}
        readers[code]=row;members[rp+'/source.cif']=data;members[rp+'/reader_worker.py']=worker;m.CEDAR37_WORKER_SHA256=sha256(worker).hexdigest()
    if defect=='generation':cat['dictionary_generation']='COMPLETED'
    if defect=='readyset':cat['readyset_execution']='COMPLETED'
    if defect=='adoption':cat['automatic_adoption']=True
    if defect=='missing_lookup_pass':cat['native_resources']['lookups']['PDU']['direct']['status']='PASS'
    if defect=='canonical_missing':cat['native_resources']['canonical_controls']['DG']['status']='MISSING'
    if defect=='source_worker':members[pre+'/source_catalogue_worker.py']=b'CHANGED'
    if defect=='snapshot':members[pre+'/dispatcher.txt']=b'CHANGED'
    if defect=='snapshot_anchor':cat['readyset_dispatcher']['snapshot']['anchor']='outside'
    if defect=='candidate_source':members['installed_ccd_readers/PDU/source.cif']=b'CHANGED'
    if defect=='reader_worker':members['installed_ccd_readers/PDU/reader_worker.py']=b'CHANGED'
    if defect=='reader_constructor':readers['PDU']['chiral_constructor']='COMPLETED'
    if defect=='reader_orders':readers['PDU']['checks']['declared_bond_orders']=False
    if defect=='numerical_pass':cat['components']['PDU']['comparison']['dictionary_parameterization']='PASS'
    if defect=='smiles_graph_pass':cat['components']['PDU']['comparison']['mapped_smiles_graph_comparison']='PASS'
    for code,row in readers.items():
        rp=row['directory']['path'];members[rp+'/reader_result.json']=json.dumps(row['result']).encode()
        members[rp+'/reader_receipt.json']=json.dumps({k:v for k,v in row.items() if k!='directory'}).encode()
    members[pre+'/source_catalogue_receipt.json']=json.dumps(cat).encode();members[pre+'/source_catalogue_result.json']=json.dumps(cat['native_resources']).encode()
    receipt={'installed_source_catalogue':cat,'installed_ccd_reader_audits':readers}
    if defect=='none':m._check_catalogue_return(members,receipt)
    else:
        with pytest.raises(ValueError):m._check_catalogue_return(members,receipt)
