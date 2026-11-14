"""General linked-recovery contracts; artificial SDK evidence is not Phenix proof."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest


def _dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def _ref(path,root,anchor):
    data=path.read_bytes()
    return {'anchor':anchor,'path':path.relative_to(root).as_posix(),
        'sha256':sha256(data).hexdigest(),'size':len(data)}


def parents(tmp_path,monkeypatch,targets=('Q17',),*,defect=None):
    """Frozen artificial parent reports with real generic DNA CIF preparation."""
    from tests.test_cif_linked_usability_bridge import prepared_inputs
    from nasolve.cif_linked_preparation import component_values,_render
    from nasolve.cif_candidate_usability import reassess_complete_candidate,POLICY_ID
    from nasolve.cif_mixed_native import compare_effective_chemistry
    from nasolve.ligand_profiles import combine_dictionary_inputs
    native=tmp_path/'native';recovery=tmp_path/'recovery'
    native.mkdir();recovery.mkdir()
    native_anchor='mixed_native_directory';recovery_anchor='mixed_recovery_directory'
    sources={};candidates={};model_lines=[];sites={};edges=[]
    codes=(*targets,'V29','W42','U37')
    for number,code in enumerate(codes):
        case=tmp_path/('case_'+code);case.mkdir()
        source,numerical,model,_,_=prepared_inputs(case)
        source_text=source.read_text().replace('ZZZ',code)
        source=native/'inputs/sources'/f'{code}.cif';source.parent.mkdir(parents=True,exist_ok=True);source.write_text(source_text)
        candidate=recovery/'components'/code/'generation/candidate.cif';candidate.parent.mkdir(parents=True)
        candidate.write_text(numerical.read_text().replace('ZZZ',code))
        sources[code]=source;candidates[code]=candidate
        mapping={'A':chr(ord('A')+number*2),'B':chr(ord('B')+number*2)}
        for line in model.read_text().splitlines(keepends=True):
            if not line.startswith(('ATOM  ','HETATM')):continue
            line=line[:17]+code+line[20:21]+mapping[line[21]]+line[22:]
            model_lines.append(line)
            sites[line[21]+':'+line[22:26].strip()]=code
        edges.append([mapping['A']+':1',mapping['A']+':2'])
    model=native/'inputs/constructed.pdb';model.write_text(''.join(model_lines)+'END\n')
    if defect=='partial_phosphate':
        model.write_text(''.join(l for l in model.read_text().splitlines(keepends=True)
            if not (l.startswith('HETATM') and l[21]=='A' and l[22:26].strip()=='2' and l[12:16].strip()=='OP2')))
    plan={'target_site_components':sites,'stack_edges':edges,'all_pairs':[],
        'requested_pairs':[],'stack_count':len(edges),'pair_count':0}
    if defect=='missing_site':plan['target_site_components'].pop('A:2')
    if defect=='duplicate_incoming':plan['stack_edges'].append(['B:1','A:2'])
    if defect=='unknown_edge':plan['stack_edges'].append(['A:2','X:99'])
    plan_path=native/'inputs/plan.json';_dump(plan_path,plan)
    active=native/'inputs/active.phil';active.write_text('refinement {\n pdb_interpretation.secondary_structure {\n enabled = False\n }\n}\n')
    disabled=native/'inputs/disabled.phil';disabled.write_bytes(active.read_bytes())
    original=[]
    for code,path in candidates.items():
        values=component_values(path,code)
        if code in targets:values['_chem_comp_bond.value_dist'][0]='0.0'
        p=native/'inputs'/f'{code}_effective.cif';p.write_text(_render(values,code));original.append(p)
    effective=native/'inputs/effective.cif';combine_dictionary_inputs(original[:-1],effective)
    effective_files=[effective,original[-1]]
    input_refs={'model':_ref(model,native,native_anchor),'active_policy':_ref(active,native,native_anchor),
        'disabled_policy':_ref(disabled,native,native_anchor),'plan':_ref(plan_path,native,native_anchor),
        'sources':{c:_ref(p,native,native_anchor) for c,p in sources.items()}}
    parent={'policy_id':'cif-mixed-pair-native-membership-v1','status':'REVIEW','inputs':input_refs,
        'effective_dictionaries':[_ref(p,native,native_anchor) for p in effective_files],
        'source_authorities':{c:'EXPLICIT_FAKE_SOURCE' for c in codes},
        'required_modified_parameterization':{'components':sorted(codes),'missing':sorted(targets)},
        'chemical_comparisons':compare_effective_chemistry(sources,effective_files),
        'new_readyset_calls':1,'new_native_calls':0,'source_inputs_preserved':True,
        'readyset':{'execution':{'status':'COMPLETED','returncode':0},'model':input_refs['model'],
            'unchanged_named_heavy_coordinates':True}}
    _dump(native/'mixed_native.json',parent)
    frozen={}
    for name,path in [('model',model),('active_policy',active)]:
        p=recovery/'inputs'/path.name;p.parent.mkdir(exist_ok=True);p.write_bytes(path.read_bytes());frozen[name]=_ref(p,recovery,recovery_anchor)
    frozen['sources']={}
    for code,path in sources.items():
        p=recovery/'inputs/sources'/f'{code}.cif';p.parent.mkdir(exist_ok=True);p.write_bytes(path.read_bytes());frozen['sources'][code]=_ref(p,recovery,recovery_anchor)
    frozen['effective_dictionaries']=[]
    for i,path in enumerate(effective_files):
        p=recovery/f'inputs/effective/{i:03d}.cif';p.parent.mkdir(exist_ok=True);p.write_bytes(path.read_bytes())
        frozen['effective_dictionaries'].append(_ref(p,recovery,recovery_anchor))
    summary={'policy_id':parent['policy_id'],'status':'REVIEW','source_authorities':parent['source_authorities'],
        'required_modified_parameterization':parent['required_modified_parameterization'],
        'parent_input_bindings':input_refs,'parent_effective_bindings':parent['effective_dictionaries'],
        'parent_report_sha256':sha256((native/'mixed_native.json').read_bytes()).hexdigest(),
        'source_inputs_preserved':True,'readyset_named_heavy_coordinates_preserved':True,
        'readyset_execution':parent['readyset']['execution']}
    p=recovery/'inputs/parent_summary.json';_dump(p,summary);frozen['parent_summary']=_ref(p,recovery,recovery_anchor)
    components={}
    for code in targets:
        source=recovery/frozen['sources'][code]['path'];candidate=candidates[code]
        assessment=reassess_complete_candidate(source,candidate,code)
        q={'policy_id':POLICY_ID,'component':code,'native_usable':True,'scope':'ISOLATED_COMPONENT_ONLY',
            'candidate_sha256':sha256(candidate.read_bytes()).hexdigest(),'checks':{'explicit_fake_native_evidence':True},
            'source_assessment':assessment}
        components[code]={'source':frozen['sources'][code],
            'generation':{'status':'CANDIDATE_REVIEW','candidate_retained':True,
                'directory':{'anchor':recovery_anchor,'path':candidate.parent.relative_to(recovery).as_posix()},
                'candidate':_ref(candidate,candidate.parent,'candidate_directory')},
            'isolated_qualification':q,'candidate_numerical_capability':True,
            'decision':{'status':'CONTINUE_WITH_NOTES','scope':'ISOLATED_COMPONENT_ONLY',
                'continue_solving':True,'selected_candidate':'source_native_generated','selected_sha256':q['candidate_sha256']}}
    report={'policy_id':'cif-mixed-component-numerical-recovery-v1','status':'MIXED_RECOVERY_ISOLATED_PASS',
        'targets':list(targets),'inputs':frozen,'components':components,
        'source_inputs_preserved':True,'model_preserved':True,'unrelated_numerics_preserved':True,
        'scientific_qualification':'NOT_ASSESSED','requires_cif_review':False,'automatic_adoption':False,
        'new_native_calls':2*len(targets),'new_generator_calls':len(targets),'new_source_probe_calls':1}
    report['outputs']=[_ref(p,recovery,recovery_anchor) for p in sorted(recovery.rglob('*')) if p.is_file()]
    _dump(recovery/'mixed_recovery.json',report)
    monkeypatch.setattr('nasolve.cif_mixed_native.read_mixed_native',lambda p:json.loads((Path(p)/'mixed_native.json').read_bytes()))
    monkeypatch.setattr('nasolve.cif_mixed_recovery.read_mixed_recovery',lambda p:json.loads((Path(p)/'mixed_recovery.json').read_bytes()))
    return recovery,native,report,parent,plan


def test_generic_mixed_container_recovery_preserves_bystanders_and_relocates(tmp_path,monkeypatch):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery,read_mixed_linked_recovery
    from nasolve.cif_linked_preparation import component_values
    from nasolve.ligand_profiles import _blocks
    recovery,native,_,_,_=parents(tmp_path,monkeypatch)
    before={p:p.read_bytes() for root in [recovery,native] for p in root.rglob('*') if p.is_file()}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('inspect-only started an SDK process'))
    out=tmp_path/'result';report=audit_mixed_linked_recovery(recovery,native,None,out)
    assert report['status']=='PREPARED_ONLY' and report['targets']==['Q17']
    assert report['new_native_calls']==0 and not report['automatic_adoption'] and not report['requires_cif_review']
    bundle=report['bundle'];delta=bundle['resource_delta']
    assert delta[0]['removed_components']==['Q17'] and delta[0]['retained_components']==['V29','W42']
    assert delta[0]['unrelated_rows_preserved'] and delta[0]['unrelated_blocks_preserved']
    assert delta[0]['block_separator_policy']=='TRAILING_CR_LF_ONLY; ALL_OTHER_RETAINED_BLOCK_BYTES_EXACT'
    filtered=out/delta[0]['retained']['path']
    original=native/'inputs/effective.cif'
    def component_blocks(path):
        return {next(iter(codes)):block for block in _blocks(path)
            if (codes:=set(block.values.get('_chem_comp_atom.comp_id',[]))) & {'V29','W42'}}
    before_blocks,after_blocks=component_blocks(original),component_blocks(filtered)
    assert set(before_blocks)==set(after_blocks)=={'V29','W42'}
    for code in before_blocks:
        assert component_values(filtered,code)==component_values(original,code)
        assert before_blocks[code].values==after_blocks[code].values
        assert before_blocks[code].text.rstrip('\r\n')==after_blocks[code].text.rstrip('\r\n')
    # The first retained definition is intermediate, so the exclusion helper
    # inserts an extra block separator while every significant byte is fixed.
    assert before_blocks['V29'].text!=after_blocks['V29'].text
    assert delta[1]['exact_copy'] and (out/delta[1]['retained']['path']).read_bytes()==(native/'inputs/U37_effective.cif').read_bytes()
    plans={v['site']:v for v in bundle['contexts']['Q17']}
    assert plans['A:1']['five_prime_state']=='phosphate' and plans['A:2']['five_prime_state']=='linked'
    assert plans['B:1']['five_prime_state']==plans['B:1']['three_prime_state']=='free_OH'
    prep=bundle['preparations']['Q17']['receipt'];selected={v['site']:v for v in prep['sites']}
    assert selected['A:2']['deleted_atoms']==['OP3','leaveH'] and selected['A:2']['retained_op2_hydrogens']==['keepH']
    assert selected['A:1']['deleted_atoms']==['oddH'] and 'OP3' in selected['A:1']['expected_atoms']
    assert selected['B:1']['deleted_atoms']==['OP1','OP2','OP3','P','keepH','leaveH']
    assert all(p.read_bytes()==data for p,data in before.items())
    shutil.rmtree(recovery);shutil.rmtree(native)
    moved=tmp_path/'moved';out.rename(moved)
    assert read_mixed_linked_recovery(moved)==report


def test_multiple_renamed_targets_share_the_same_fixed_bundle(tmp_path,monkeypatch):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery
    recovery,native,_,_,_=parents(tmp_path,monkeypatch,targets=('X11','Y22'))
    report=audit_mixed_linked_recovery(recovery,native,None,tmp_path/'result')
    assert report['targets']==['X11','Y22']
    assert set(report['bundle']['preparations'])=={'X11','Y22'}
    assert set(report['bundle']['site_projections'])=={'A:1','A:2','B:1','C:1','C:2','D:1'}
    assert report['bundle']['resource_delta'][0]['removed_components']==['X11','Y22']


def test_compact_source_findings_ignore_derived_roundoff_but_bind_exact_input_bytes(tmp_path,monkeypatch):
    from tests.test_cif_linked_usability_bridge import prepared_inputs
    from nasolve.cif_mixed_linked_recovery import _compact_findings
    source,numerical,_,_,_=prepared_inputs(tmp_path)
    comparison={'ZZZ':{'status':'REJECTED','rejection_reasons':['generated-plane-angle-geometry-invalid-or-unassessed'],
        'generated_assessment':{'components':[{'findings':[{'measurements':{
            'determinant':0.013,'eigenvalues':[0.999999999999,1.0,1.000000000001]}}]}]}}}
    monkeypatch.setattr('nasolve.cif_mixed_native.compare_effective_chemistry',lambda *a,**k:deepcopy(comparison))
    original=_compact_findings({'ZZZ':source},[numerical])
    measurements=comparison['ZZZ']['generated_assessment']['components'][0]['findings'][0]['measurements']
    measurements['determinant']+=1e-14;measurements['eigenvalues'][0]+=1e-15
    assert _compact_findings({'ZZZ':source},[numerical])==original
    source.write_bytes(source.read_bytes()+b'\n# byte-bound source provenance\n')
    changed_source=_compact_findings({'ZZZ':source},[numerical])
    assert changed_source['ZZZ']['source_sha256']!=original['ZZZ']['source_sha256']
    assert changed_source['ZZZ']['effective_input_sha256']==original['ZZZ']['effective_input_sha256']
    numerical.write_bytes(numerical.read_bytes()+b'\n# byte-bound effective provenance\n')
    changed_effective=_compact_findings({'ZZZ':source},[numerical])
    assert changed_effective['ZZZ']['source_sha256']==changed_source['ZZZ']['source_sha256']
    assert changed_effective['ZZZ']['effective_input_sha256']!=changed_source['ZZZ']['effective_input_sha256']
    assert changed_effective['ZZZ']['status']==original['ZZZ']['status']
    assert changed_effective['ZZZ']['rejection_reasons']==original['ZZZ']['rejection_reasons']


@pytest.mark.parametrize('timeout',[0,61,True,1.5])
def test_invalid_bounds_stop_before_parent_reads(tmp_path,timeout):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery
    with pytest.raises(ValueError):audit_mixed_linked_recovery(tmp_path/'missing',tmp_path/'missing',None,tmp_path/'out',timeout_seconds=timeout)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',['missing_site','duplicate_incoming','unknown_edge','partial_phosphate'])
def test_unknown_link_or_terminal_inventory_is_not_guessed(tmp_path,monkeypatch,defect):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery
    recovery,native,_,_,_=parents(tmp_path,monkeypatch,defect=defect)
    with pytest.raises(ValueError):audit_mixed_linked_recovery(recovery,native,None,tmp_path/'result')


def test_parent_binding_cannot_be_replaced_by_a_stored_pass(tmp_path,monkeypatch):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery
    recovery,native,_,parent,_=parents(tmp_path,monkeypatch)
    parent['source_authorities']['Q17']='CHANGED';_dump(native/'mixed_native.json',parent)
    with pytest.raises(ValueError):audit_mixed_linked_recovery(recovery,native,None,tmp_path/'result')


@pytest.mark.parametrize('defect',['not_passed','selection','unusable','component','parent_hash'])
def test_bound_isolated_evidence_is_required_for_every_recovered_code(tmp_path,monkeypatch,defect):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery
    recovery,native,report,_,_=parents(tmp_path,monkeypatch)
    case=report['components']['Q17']
    if defect=='not_passed':report['status']='REVIEW'
    elif defect=='selection':case['decision']['selected_sha256']='0'*64
    elif defect=='unusable':case['isolated_qualification']['native_usable']=False
    elif defect=='component':case['isolated_qualification']['component']='V29'
    else:
        p=recovery/report['inputs']['parent_summary']['path'];summary=json.loads(p.read_bytes())
        summary['parent_report_sha256']='0'*64;_dump(p,summary)
        report['inputs']['parent_summary']=_ref(p,recovery,'mixed_recovery_directory')
        report['outputs']=[_ref(p,recovery,'mixed_recovery_directory') if r['path']==p.relative_to(recovery).as_posix() else r for r in report['outputs']]
    _dump(recovery/'mixed_recovery.json',report)
    with pytest.raises(ValueError):audit_mixed_linked_recovery(recovery,native,None,tmp_path/'result')


@pytest.mark.parametrize('defect',['status','count','model','extra','symlink',
    'decision_selection','decision_usability','model_claim','authority'])
def test_portable_reader_rejects_forged_native_success_and_modified_frozen_inputs(tmp_path,monkeypatch,defect):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery,read_mixed_linked_recovery,REPORT
    recovery,native,_,_,_=parents(tmp_path,monkeypatch)
    out=tmp_path/'result';report=audit_mixed_linked_recovery(recovery,native,None,out)
    if defect=='status':report['status']='MIXED_LINKED_RECOVERY_MECHANICS_PASS'
    elif defect=='count':report['new_native_calls']=2
    elif defect=='model':(out/'inputs/recovery/inputs/constructed.pdb').write_bytes(b'CHANGED')
    elif defect=='extra':(out/'unbound.txt').write_text('EXTRA')
    elif defect=='decision_selection':report['coordinate_decision']['selected']='unverified_geometry_endpoint'
    elif defect=='decision_usability':report['coordinate_decision']['native_usable']=True
    elif defect=='model_claim':report['model_preserved']=False
    elif defect=='authority':report['policy_authority']='UNVERIFIED_NATIVE_GUESS'
    else:
        p=out/'inputs/recovery/inputs/constructed.pdb';p.unlink();p.symlink_to(native/'inputs/constructed.pdb')
    _dump(out/REPORT,report)
    with pytest.raises(ValueError):read_mixed_linked_recovery(out)


def test_owned_failed_native_read_keeps_diagnostics_without_any_generator_retry(tmp_path,monkeypatch):
    from nasolve.cif_mixed_linked_recovery import audit_mixed_linked_recovery,read_mixed_linked_recovery,_capture,ANCHOR
    recovery,native,_,_,_=parents(tmp_path,monkeypatch)
    sdk=tmp_path/'fake-sdk';(sdk/'bin').mkdir(parents=True)
    python=sdk/'bin/phenix.python';python.write_text('#!/bin/sh\nexit 7\n');python.chmod(0o755)
    phenix=SimpleNamespace(root=sdk,executables={'phenix.python':python},environment=os.environ,version='EXPLICIT_FAKE_SDK')
    monkeypatch.setattr('nasolve.cif_source_candidate.generate_source_candidate',lambda *a,**k:pytest.fail('linked read retried generation'))
    monkeypatch.setattr('nasolve.postmr._run_readyset',lambda *a,**k:pytest.fail('linked read retried ReadySet'))
    out=tmp_path/'result';report=audit_mixed_linked_recovery(recovery,native,phenix,out,timeout_seconds=9)
    assert report['status']=='REVIEW' and 1<=report['new_native_calls']<=2
    captures=[json.loads(p.read_bytes()) for p in out.rglob('native_receipt.json')]
    assert len(captures)==report['new_native_calls']
    assert all(c['execution']['returncode']==7 and c['execution']['timeout_seconds']==9 for c in captures)
    assert report['coordinate_decision']['selected']=='verified_constructed_model'
    assert read_mixed_linked_recovery(out)==report
    # A stored native object cannot replace the exact worker-written result.
    # Rebind the changed receipt itself to exercise result-origin validation,
    # rather than merely triggering the unchanged top-level byte hash.
    receipt=out/report['native_baseline']['receipt']['path']
    assert not (receipt.parent/'native_validation.json').exists()
    changed=json.loads(receipt.read_bytes());changed['native_validation']={'status':'REVIEW'}
    _dump(receipt,changed)
    dictionaries=[out/r['path'] for r in report['bundle']['native_dictionaries']]
    phils=[out/report['inputs']['disabled_policy']['path'],
        *[out/r['path'] for r in report['bundle']['context_phils']]]
    with pytest.raises(ValueError,match='Native result.*missing'):
        _capture(out,_ref(receipt,out,ANCHOR),out/report['inputs']['model']['path'],dictionaries,phils)


@pytest.mark.parametrize('mode',['default','override','unknown_site','wrong_component','mixed_component'])
def test_optional_site_projection_keeps_default_and_binds_every_override(tmp_path,monkeypatch,mode):
    from tests.test_cif_linked_control_qualification import case
    from nasolve.cif_mixed_native import qualify_mixed_native
    before,after,model,_,projected=case(tmp_path)
    for native in [before,after]:
        native['geometry']['custom_proxy_requests']=[]
        native['installed_api_sources']=[{'module':'EXPLICIT_FAKE_NATIVE','sha256':'a'*64}]
    base=tmp_path/'base.cif';base.write_bytes(projected.read_bytes())
    active=tmp_path/'active.phil';active.write_text('refinement {\n pdb_interpretation.secondary_structure {\n enabled = False\n }\n}\n')
    plan={'all_pairs':[],'stack_edges':[['A:1','A:2'],['A:2','A:3']],
        'target_site_components':{'A:1':'DG','A:2':'ZZZ','A:3':'DG'}}
    observed=[]
    def projection_checks(native,projections):
        observed.append(projections)
        return [{'check':'EXPLICIT_FAKE_PROJECTION_CAPTURE','status':'PASS'}]
    monkeypatch.setattr('nasolve.cif_terminal_qualification.definition_projection_checks',projection_checks)
    kwargs={}
    if mode!='default':kwargs['site_projections']={'A:2':(projected,'ZZZ')}
    if mode=='unknown_site':kwargs['site_projections']={'X:99':(projected,'ZZZ')}
    if mode=='wrong_component':kwargs['site_projections']={'A:2':(projected,'AAA')}
    if mode=='mixed_component':
        mixed=tmp_path/'mixed.cif';mixed.write_text(projected.read_text()+projected.read_text().replace('ZZZ','AAA'))
        kwargs['site_projections']={'A:2':(mixed,'ZZZ')}
    result=qualify_mixed_native(before,after,model,active,plan,{'ZZZ':projected},[base],**kwargs)
    if mode in {'default','override'}:
        assert observed==[{'A:2':(base if mode=='default' else projected,'ZZZ')}]
        assert result['checks']['exact_explicit_effective_definitions']
        if mode=='default':assert 'explicit_site_projection_scope' not in result['checks']
        else:assert result['checks']['explicit_site_projection_scope']
    else:
        assert not observed and result['checks'].get('explicit_site_projection_scope') is not True
        assert result['status']=='REVIEW' and not result['mechanics_checks_pass']
