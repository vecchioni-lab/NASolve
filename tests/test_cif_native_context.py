"""Explicit context must preserve chemistry and actual custom-restraint intent."""
from copy import deepcopy
from hashlib import sha256
import json
import shutil
from unittest.mock import patch

import pytest

CONTEXT={'policy_id':'cif-explicit-site-native-context-v1','custom_restraints':'required'}


def native_case(terminal=False):
    from tests.test_cif_linked_qualification import native_case as original
    from nasolve.cif_construction_native import NATIVE_KINDS
    before,after,plans,links,ends=original()
    plans[0]['sites'][0].update(component='IGU',incoming_site='A:1',outgoing_site='A:3',
        five_prime_state='linked',three_prime_state='linked')
    for native in [before,after]:
        native['restraint_policy']={'secondary_structure_enabled':False,'origin_ids':{
            'edits':4,'hydrogen bonds':2,'basepair stacking':6,'basepair parallelity':7,'basepair planarity':9}}
        details=native['geometry']['proxy_details']
        for kind in NATIVE_KINDS:details.setdefault(kind,[])
        for rows in details.values():
            for row in rows:row['origin_id']=0
        for request in native['geometry']['custom_proxy_requests']:
            request.update(action='add',selections=['synthetic selection '+str(i) for i in request['i_seqs']])
            kind='bond_simple' if request['kind']=='bond' else request['kind']
            for row in details[kind]:
                if row['i_seqs']==request['i_seqs']:
                    row['origin_id']=4
                    if kind=='parallelity':row.update(slack=0.,top_out=False)
        for a in native['atoms']:a['element']='P' if a['atom_id']=='P' else 'O'
        if terminal:
            for name in ['OP1','OP2','OP3',"O5'"]:
                index=len(native['atoms']);native['atoms'].append({'i_seq':index,'atom_id':name,
                    'label':str(index),'element':'O','xyz':[float(index),0.,0.],
                    'identity':{'model_id':'','chain_id':'A','resseq':'3','icode':'','resname':'DG','altloc':''}})
            row=native['monomer_mappings']['rows'][2]
            names=['P','OP1','OP2','OP3',"O5'"];row['metadata']['atom_ids']=names
            row['metadata']['effective_definition']={'atoms':[{'atom_id':n,'type_symbol':'P' if n=='P' else 'O',
                'type_energy':'X','charge':'0'} for n in names],
                'bonds':[{'atom_id_1':'P','atom_id_2':n} for n in names[1:]],
                'angles':[],'torsions':[],'chirality':[],'plane_atoms':[]}
    if terminal:
        # A separate strand end, with no incoming backbone link to its P.
        links=[('A:1','A:2')]
        for native in [before,after]:
            native['geometry']['simple_bonds']=[r for r in native['geometry']['simple_bonds'] if r['i_seqs']!=[2,3]]
            native['geometry']['proxy_details']['bond_simple']=native['geometry']['simple_bonds']
        plans[0]['sites'][0].update(outgoing_site=None,three_prime_state='free_OH')
        names=['P','OP1','OP2','OP3',"O5'"]
        plans.append({'sites':[{'site':'A:3','component':'DG','incoming_site':None,'outgoing_site':None,
            'five_prime_state':'phosphate','three_prime_state':'free_OH','expected_atoms':names,
            'expected_energy_types':{n:'X' for n in names},'expected_formal_charges':{n:'0' for n in names},
            'expected_hydrogen_attachments':{}}]})
    return before,after,plans,links,ends


def audit(values,context=CONTEXT):
    from nasolve.cif_linked_qualification import qualify_linked_bundle
    return qualify_linked_bundle(*values,native_context=context)


def failures(report):return [r['check'] for r in report['checks'] if r['status']!='PASS']


def test_explicit_terminal_phosphate_is_retained_while_legacy_gate_stays_conservative():
    from nasolve.cif_linked_qualification import qualify_linked_bundle
    values=native_case(terminal=True);frozen=deepcopy(values)
    assert qualify_linked_bundle(*values)['status']=='REVIEW'
    report=audit(values)
    assert report['status']=='LINKED_MECHANICS_PASS',failures(report)
    assert report['native_context']==CONTEXT and report['automatic_adoption'] is False
    assert values==frozen


@pytest.mark.parametrize('defect',['internal','undeclared','missing_op3','wrong_element','alias',
    'duplicate_coordinate','definition_missing','definition_wrong_element','extra_neighbor','wrong_component','wrong_outgoing','wrong_three_prime'])
def test_terminal_permission_requires_exact_declared_native_chemistry(defect):
    values=native_case(terminal=True);before,after,plans,links,ends=values
    plan=plans[-1]['sites'][0];definition=after['monomer_mappings']['rows'][2]['metadata']['effective_definition']
    if defect=='internal':plan.update(incoming_site='A:2',five_prime_state='linked')
    if defect=='undeclared':plans.pop()
    if defect=='missing_op3':after['atoms']=[r for r in after['atoms'] if r['atom_id']!='OP3']
    if defect=='wrong_element':next(r for r in after['atoms'] if r['atom_id']=='OP3')['element']='S'
    if defect=='alias':next(r for r in after['atoms'] if r['atom_id']=='OP3')['atom_id']='O3P'
    if defect=='duplicate_coordinate':after['atoms'].append(deepcopy(next(r for r in after['atoms'] if r['atom_id']=='OP3')))
    if defect=='definition_missing':definition['atoms']=[r for r in definition['atoms'] if r['atom_id']!='OP3']
    if defect=='definition_wrong_element':next(r for r in definition['atoms'] if r['atom_id']=='OP3')['type_symbol']='S'
    if defect=='extra_neighbor':definition['bonds'].append({'atom_id_1':'P','atom_id_2':"O3'"})
    if defect=='wrong_component':plan['component']='DIFFERENT'
    if defect=='wrong_outgoing':plan['outgoing_site']='A:1'
    if defect=='wrong_three_prime':plan['three_prime_state']='linked'
    assert audit(values)['status']=='REVIEW'


@pytest.mark.parametrize('mode',['required','absent'])
def test_empty_custom_requests_need_explicit_absent_intent(mode):
    values=native_case()
    for n in values[:2]:
        n['geometry']['custom_proxy_requests']=[]
        for kind,rows in n['geometry']['proxy_details'].items():
            n['geometry']['proxy_details'][kind]=[r for r in rows if r['origin_id']!=4]
    report=audit(values,{**CONTEXT,'custom_restraints':mode})
    assert (report['status']=='LINKED_MECHANICS_PASS') is (mode=='absent'),failures(report)


@pytest.mark.parametrize('defect',['lost_request','all_requests_lost','duplicate_request','duplicate_proxy',
    'target','tiny_target_change','weight','wrong_origin','wrong_label','missing_second_plane',
    'changed_second_plane','changed_selection','delete_action','extra_edit','parallel_slack','parallel_top_out','absent_with_requests','unrecorded_origin','nonfinite','zero_weight'])
def test_requested_restraints_have_unique_exact_native_realization(defect):
    values=native_case();after=values[1];g=after['geometry'];context=CONTEXT
    if defect=='lost_request':g['custom_proxy_requests'].pop()
    if defect=='all_requests_lost':g['custom_proxy_requests']=[]
    if defect=='duplicate_request':g['custom_proxy_requests'].append(deepcopy(g['custom_proxy_requests'][0]))
    if defect=='duplicate_proxy':g['proxy_details']['planarity'].append(deepcopy(g['proxy_details']['planarity'][0]))
    if defect=='target':g['proxy_details']['bond_simple'][-1]['distance_ideal']+=.1
    if defect=='tiny_target_change':g['proxy_details']['bond_simple'][-1]['distance_ideal']+=1e-13
    if defect=='weight':g['proxy_details']['planarity'][0]['weights'][0]*=2
    if defect=='wrong_origin':g['proxy_details']['bond_simple'][-1]['origin_id']=0
    if defect=='wrong_label':g['custom_proxy_requests'][0]['atoms'][0]='wrong'
    if defect=='missing_second_plane':g['custom_proxy_requests'][-1].pop('j_seqs')
    if defect=='changed_second_plane':g['proxy_details']['parallelity'][0]['j_seqs']=[0,1,2]
    if defect=='changed_selection':g['custom_proxy_requests'][0]['selections'][0]='other selection'
    if defect=='delete_action':g['custom_proxy_requests'][0]['action']='delete'
    if defect=='extra_edit':
        row=deepcopy(g['proxy_details']['bond_simple'][0]);row['origin_id']=4;g['proxy_details']['bond_simple'].append(row)
    if defect=='parallel_slack':g['proxy_details']['parallelity'][0]['slack']=1.
    if defect=='parallel_top_out':g['proxy_details']['parallelity'][0]['top_out']=True
    if defect=='absent_with_requests':context={**CONTEXT,'custom_restraints':'absent'}
    if defect=='unrecorded_origin':g['proxy_details']['bond_simple'][-1]['origin_id']=None
    if defect=='nonfinite':g['custom_proxy_requests'][0]['weight']=float('nan')
    if defect=='zero_weight':g['custom_proxy_requests'][0]['weight']=0.
    assert audit(values,context)['status']=='REVIEW'


@pytest.mark.parametrize('context',[{},True,{'policy_id':'unknown','custom_restraints':'required'},
    {**CONTEXT,'custom_restraints':False},{**CONTEXT,'custom_restraints':[]},
    {**CONTEXT,'custom_restraints':{}},{**CONTEXT,'extra':'permission'}])
def test_unknown_or_partial_native_context_cannot_relax_old_gates(context):
    with pytest.raises(ValueError):audit(native_case(),context)


@pytest.mark.parametrize('mode',['required','absent'])
def test_context_is_frozen_replayed_and_cannot_be_relabelled(tmp_path,mode):
    from tests.test_cif_dictionary_sites import inputs
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites,read_dictionary_sites
    args=inputs(tmp_path);context={**CONTEXT,'custom_restraints':mode};out=tmp_path/'sites'
    result=prepare_dictionary_sites(output=out,native_context=context,**args)
    assert result['policy_id']=='cif-stored-dictionary-sites-v2' and result['native_context']==context
    frozen={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    moved=tmp_path/'moved';out.rename(moved)
    for name in ['inputs','resources','store','snapshot']:shutil.rmtree(tmp_path/name)
    with patch('subprocess.Popen',side_effect=AssertionError('read-only')):read=read_dictionary_sites(moved)
    assert read['report']==result
    assert all(((moved/p).read_bytes(),(moved/p).stat().st_mtime_ns)==v for p,v in frozen.items())
    record=json.loads((moved/'site_receipt.json').read_text());record['policy_id']='cif-stored-dictionary-sites-v1'
    (moved/'site_receipt.json').write_text(json.dumps(record))
    with pytest.raises(ValueError):read_dictionary_sites(moved)


def test_legacy_site_receipt_keeps_native_context_absent(tmp_path):
    from tests.test_cif_dictionary_sites import inputs
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites,read_dictionary_sites
    r=prepare_dictionary_sites(output=tmp_path/'sites',**inputs(tmp_path))
    assert r['policy_id']=='cif-stored-dictionary-sites-v1' and 'native_context' not in r
    assert read_dictionary_sites(tmp_path/'sites')['report']==r


def test_explicit_context_survives_incomplete_inventory_report():
    values=native_case();values[1]['inventory_detail']='summary'
    report=audit(values)
    assert report['status']=='REVIEW' and report['native_context']==CONTEXT


@pytest.mark.parametrize('defect',['context_removed','invalid_context','unknown_policy'])
def test_v2_reader_requires_the_complete_frozen_native_context(tmp_path,defect):
    from tests.test_cif_dictionary_sites import inputs
    from nasolve.cif_dictionary_sites import prepare_dictionary_sites,read_dictionary_sites
    out=tmp_path/'sites';prepare_dictionary_sites(output=out,native_context=CONTEXT,**inputs(tmp_path))
    p=out/'site_receipt.json';r=json.loads(p.read_text())
    if defect=='context_removed':r.pop('native_context')
    if defect=='invalid_context':r['native_context']['custom_restraints']='guess'
    if defect=='unknown_policy':r['policy_id']='cif-stored-dictionary-sites-v99'
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError):read_dictionary_sites(out)
