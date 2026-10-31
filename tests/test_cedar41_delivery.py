"""Selected text and static code never become executed ReadySet evidence."""
from hashlib import sha256
import importlib.util,json
from pathlib import Path
import pytest


@pytest.mark.parametrize('defect',['none','worker','snapshot','adoption','generation','mapped_graph','static_execution','coverage','descriptor','ccd_path','numerics','unmatched_descriptor','result'])
def test_returned_selection_boundary_keeps_descriptor_and_static_scope_separate(defect):
    p=Path(__file__).resolve().parents[1]/'scripts/cif_numerical_recovery_probe_template.py'
    spec=importlib.util.spec_from_file_location('cedar41_template',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    members={};pre='readyset_sources';sources=[]
    for i in range(24):
        path='sources/ready_set.py.txt' if not i else 'sources/helper_'+str(i)+'.py.txt';data=('FAKE STATIC SOURCE '+str(i)).encode();members[pre+'/'+path]=data
        sources.append({'anchor':'phenix_installation','path':'lib/python3.11/site-packages/elbow/'+str(i)+'.py',
            'snapshot':{'anchor':'readyset_audit_directory','path':path},'size':len(data),'sha256':sha256(data).hexdigest()})
    worker=b'raise RuntimeError("CAPTURED WORKER MUST NOT EXECUTE")\n';members[pre+'/descriptor_worker.py']=worker;m.CEDAR40_WORKER_SHA256=sha256(worker).hexdigest()
    audit={'policy_id':'cif-readyset-source-and-descriptor-selection-v1','automatic_adoption':False,'sources':sources,
        **{k:'NOT_RUN' for k in ['readyset_execution','dictionary_generation','optimization','mapped_smiles_graph_comparison']},
        'numerical_restraints':'UNASSESSED','components':{},'static_readyset':{'sources':sources,
            'static_analysis_is_execution_proof':False,'readyset_execution':'NOT_RUN','coverage_complete':True,
            'entrypoint':{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/elbow/command_line/ready_set.py'}}}
    parent={'installed_source_catalogue':{'components':{}}};result={}
    for code in ['PDU','5PC']:
        d={'program':'FAKE','type':'SMILES_CANONICAL','descriptor':'CC#C'};path='lib/FAKE/'+code+'.cif'
        parent['installed_source_catalogue']['components'][code]={'resource':{'path':path},'comparison':{'descriptors':[d]}}
        audit['components'][code]={'status':'SELECTED_DESCRIPTOR_MATCH','selected_smiles':'CC#C','matching_descriptors':[d],
            'ccd_path':path,'mapped_smiles_graph_comparison':'NOT_RUN','numerical_restraints':'UNASSESSED'}
        result[code]={'ccd_path':path,'selected_smiles':'CC#C'}
    if defect=='worker':members[pre+'/descriptor_worker.py']=b'CHANGED'
    if defect=='snapshot':members[pre+'/sources/ready_set.py.txt']=b'CHANGED'
    if defect=='adoption':audit['automatic_adoption']=True
    if defect=='generation':audit['dictionary_generation']='COMPLETED'
    if defect=='mapped_graph':audit['mapped_smiles_graph_comparison']='PASS'
    if defect=='static_execution':audit['static_readyset']['static_analysis_is_execution_proof']=True
    if defect=='coverage':audit['static_readyset']['coverage_complete']=False
    if defect=='descriptor':audit['components']['PDU']['selected_smiles']='CCCC'
    if defect=='ccd_path':audit['components']['PDU']['ccd_path']='lib/OTHER.cif'
    if defect=='numerics':audit['components']['PDU']['numerical_restraints']='PASS'
    if defect=='unmatched_descriptor':audit['components']['PDU']['matching_descriptors']=[]
    if defect=='result':result['PDU']['selected_smiles']='CCCC'
    members[pre+'/readyset_source_receipt.json']=json.dumps(audit).encode();members[pre+'/descriptor_result.json']=json.dumps(result).encode()
    if defect=='none':m._check_readyset_source_return(members,{'readyset_source_audit':audit},parent)
    else:
        with pytest.raises(ValueError):m._check_readyset_source_return(members,{'readyset_source_audit':audit},parent)
