"""Selection wiring with explicitly synthetic upstream verifiers, not chemistry."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,shutil
import pytest


def fixture(tmp_path,monkeypatch):
    from nasolve import cif_dictionary_bundle_repair as m
    from nasolve.cif_native_monomers import capture_full_monomers,POLICY_ID
    root=tmp_path/'evidence';root.mkdir();b=root/'prepared';b.mkdir()
    (b/'model.pdb').write_text('EXPLICIT SYNTHETIC MODEL')
    (b/'0.cif').write_text('EXPLICIT SOURCE-BOUND AAA')
    (b/'1.cif').write_text('EXPLICIT SOURCE-BOUND BBB')
    (b/'0.phil').write_text('EXPLICIT POLICY')
    (b/'bundle_receipt.json').write_text('{}')
    for code in ['AAA','BBB']:
        p=b/'components'/code;p.mkdir(parents=True);(p/'source.cif').write_text('SOURCE '+code)
    a=root/'attribution';(a/'bundle').mkdir(parents=True)
    for i in range(2):shutil.copyfile(b/f'{i}.cif',a/'bundle'/f'{i}.cif')
    (a/'bundle/repaired.cif').write_text('EXPLICIT GRAPH-SELECTED REPAIR')
    ref=lambda p:dict(path=p,anchor='test',size=1,sha256='a'*64)
    plan=dict(modeled_components=['AAA','BBB'],inputs=[ref('0.cif'),ref('1.cif')],
        final_dictionaries=[ref('repaired.cif'),ref('1.cif')],steps=[dict(component='AAA',dictionary_index=0,dictionaries_after=[ref('repaired.cif'),ref('1.cif')])])
    (a/'bundle/linear_torsion_bundle.json').write_text(json.dumps(plan))
    (a/'captured_linear_attribution.json').write_text(json.dumps(dict(status='CAPTURED_LINEAR_ATTRIBUTION_PASS',kernel_execution_authentication='MAINTAINED_FRESH_NATIVE_JOB')))
    identities=[dict(model_id='',chain_id='A',resseq=str(i+1),icode='',resname=c,altloc='') for i,c in enumerate(['AAA','BBB'])]
    native=dict(atom_count=2,atoms=[dict(identity=x) for x in identities],monomer_mappings=dict(status='RECORDED',rows=[dict(resname=x['resname'],site='A:'+x['resseq'],chain_id='A',literal_identity=dict(status='RECORDED',**x)) for x in identities]))
    native['full_monomer_inventory']=capture_full_monomers(native,False)
    for stage in range(2):
        p=a/'captures'/f'{stage:03d}';p.mkdir(parents=True)
        shutil.copyfile(b/'model.pdb',p/'model.pdb');shutil.copyfile(b/'0.phil',p/'0.phil')
        for j,r in enumerate(plan['inputs'] if stage==0 else plan['final_dictionaries']):shutil.copyfile(a/'bundle'/r['path'],p/f'{j}.cif')
        (p/'native_receipt.json').write_text(json.dumps(dict(stage=stage,full_monomer_inventory_policy=POLICY_ID,native_validation=native)))
    base=root/'baseline';base.mkdir();(base/'native_receipt.json').write_text('{}')
    for name,stage in [('original',0),('repaired',1)]:
        g=root/name;g.mkdir();shutil.copytree(a/'captures'/f'{stage:03d}',g/'capture')
        (g/'captured_mixed_gradients.json').write_text(json.dumps(dict(status='CAPTURED_MIXED_DERIVATIVES_PASS')))
    state=dict(source_usable=True,stereo='PRESERVED')
    def prepared(path):
        p=Path(path)
        return dict(report=dict(components=['AAA','BBB'],consumer={'explicit':'TEST'}),model=p/'model.pdb',
            after_dictionaries=[p/'0.cif',p/'1.cif'],after_phils=[p/'0.phil'],component_dictionaries={c:p/f'{i}.cif' for i,c in enumerate(['AAA','BBB'])})
    def source_review(*args):
        return dict(diagnostic_continuation=dict(allowed=state['source_usable']),qualification=dict(checks=[dict(check='native_charge',status='UNSUPPORTED')]),native_checks=[dict(check='test',status='PASS')])
    def snapshot(path):
        code=Path(path).parent.name;return dict(source=Path(path).parent/'source.cif',manifest=dict(request=dict(declared_chemistry={'source':code})),qualification=dict(source_assessment=dict(finished_stereo=dict(stereochemistry=state['stereo']))))
    def inputs(p):
        p=Path(p);r=json.loads((p/'native_receipt.json').read_text());return r,p/'model.pdb',[p/'0.cif',p/'1.cif'],[p/'0.phil'],r['native_validation'],{}
    def bind(record,consumer,model,ds,phils):return None  # Explicit upstream capture verifier.
    monkeypatch.setattr(m,'read_dictionary_bundle',prepared);monkeypatch.setattr(m,'inspect_dictionary_bundle_native',source_review)
    monkeypatch.setattr(m,'resolve_dictionary_snapshot',snapshot);monkeypatch.setattr(m,'_inputs',inputs);monkeypatch.setattr(m,'_bind_capture',bind)
    monkeypatch.setattr(m,'read_linear_torsion_bundle',lambda p:json.loads((Path(p)/'linear_torsion_bundle.json').read_text()))
    monkeypatch.setattr(m,'read_captured_linear_attribution',lambda p:json.loads((Path(p)/'captured_linear_attribution.json').read_text()))
    monkeypatch.setattr(m,'read_captured_mixed_gradients',lambda p:json.loads((Path(p)/'captured_mixed_gradients.json').read_text()))
    args=dict(bundle=b,baseline_receipt=base/'native_receipt.json',attribution_directory=a,repaired_gradient_directory=root/'repaired',original_gradient_directory=root/'original')
    return m,root,args,state


@pytest.mark.parametrize('repaired,original,selected',[(True,True,'repaired_prepared_bundle'),(True,False,'repaired_prepared_bundle'),(False,True,'verified_prepared_bundle'),(False,False,None)])
def test_selects_only_numerically_qualified_whole_bundle(tmp_path,monkeypatch,repaired,original,selected):
    m,root,args,state=fixture(tmp_path,monkeypatch)
    for name,passed in [('repaired',repaired),('original',original)]:
        if not passed:(root/name/'captured_mixed_gradients.json').write_text(json.dumps(dict(status='REVIEW')))
    q=m.inspect_dictionary_bundle_repair(**args)
    assert q['decision']['selected']==selected and not q['automatic_adoption']
    assert q['coordinate_selection']=='UNCHANGED_PREPARED_MODEL' and q['scientific_qualification']=='NOT_ASSESSED'
    if selected:
        r=m.repaired_dictionary_bundle_inputs(**args)
        assert r['model'].read_bytes()==(root/'prepared/model.pdb').read_bytes()
        assert r['dictionaries'][0].read_bytes()==(root/('attribution/bundle/repaired.cif' if repaired else 'prepared/0.cif')).read_bytes()
    else:
        with pytest.raises(ValueError,match='No usable'):m.repaired_dictionary_bundle_inputs(**args)


@pytest.mark.parametrize('field',['repaired_gradient_directory','original_gradient_directory','both'])
def test_absent_proof_cannot_be_assumed_from_preserved_input(tmp_path,monkeypatch,field):
    m,root,args,state=fixture(tmp_path,monkeypatch)
    for key in ['repaired_gradient_directory','original_gradient_directory']:
        if field in (key,'both'):args[key]=None
    q=m.inspect_dictionary_bundle_repair(**args)
    expected=None if field=='both' else 'verified_prepared_bundle' if field=='repaired_gradient_directory' else 'repaired_prepared_bundle'
    assert q['decision']['selected']==expected


@pytest.mark.parametrize('defect',['source_unusable','attribution_unqualified','stereo_inverted','stereo_unassessed'])
def test_source_and_attribution_gates_do_not_turn_into_score_permissions(tmp_path,monkeypatch,defect):
    m,root,args,state=fixture(tmp_path,monkeypatch)
    if defect=='source_unusable':state['source_usable']=False
    if defect=='attribution_unqualified':(args['attribution_directory']/'captured_linear_attribution.json').write_text(json.dumps(dict(status='REVIEW',kernel_execution_authentication='NOT_RUN')))
    if defect=='stereo_inverted':state['stereo']='INVERTED'
    if defect=='stereo_unassessed':state['stereo']='UNASSESSED'
    q=m.inspect_dictionary_bundle_repair(**args)
    assert q['decision']['selected']==(None if defect in ['source_unusable','stereo_inverted'] else 'verified_prepared_bundle' if defect=='attribution_unqualified' else 'repaired_prepared_bundle')
    assert q['model_optimization']=='NOT_RUN' and q['new_native_calls']==0


@pytest.mark.parametrize('defect',['source_dictionary','source_model','source_phil','dictionary_order','unqualified_component','wrong_owner','missing_full_policy','missing_proof','changed_identity','repaired_wrong_capture','original_wrong_capture','extra_stage','bad_baseline_name'])
def test_wrong_source_or_native_context_refuses(tmp_path,monkeypatch,defect):
    m,root,args,state=fixture(tmp_path,monkeypatch);a=args['attribution_directory'];p=a/'bundle/linear_torsion_bundle.json';plan=json.loads(p.read_text())
    if defect in ['source_dictionary','source_model','source_phil']:(root/'prepared'/{'source_dictionary':'0.cif','source_model':'model.pdb','source_phil':'0.phil'}[defect]).write_text('OTHER SOURCE')
    if defect=='dictionary_order':plan['inputs'].reverse();p.write_text(json.dumps(plan))
    if defect=='unqualified_component':plan['steps'][0]['component']='ZZZ';p.write_text(json.dumps(plan))
    if defect=='wrong_owner':plan['steps'][0]['dictionary_index']=1;p.write_text(json.dumps(plan))
    if defect in ['missing_full_policy','missing_proof','changed_identity']:
        p=a/'captures/001/native_receipt.json';r=json.loads(p.read_text())
        if defect=='missing_full_policy':del r['full_monomer_inventory_policy']
        if defect=='missing_proof':del r['native_validation']['full_monomer_inventory']
        if defect=='changed_identity':r['native_validation']['atoms'][0]['identity']['chain_id']='X'
        p.write_text(json.dumps(r))
    if defect=='repaired_wrong_capture':shutil.copyfile(a/'captures/000/native_receipt.json',root/'repaired/capture/native_receipt.json')
    if defect=='original_wrong_capture':shutil.copyfile(a/'captures/001/native_receipt.json',root/'original/capture/native_receipt.json')
    if defect=='extra_stage':(a/'captures/999').mkdir()
    if defect=='bad_baseline_name':args['baseline_receipt']=root/'baseline/other.json';args['baseline_receipt'].write_text('{}')
    with pytest.raises(ValueError):m.inspect_dictionary_bundle_repair(**args)


def test_relocation_and_reads_preserve_evidence_and_never_execute(tmp_path,monkeypatch):
    m,root,args,state=fixture(tmp_path,monkeypatch);before={p.relative_to(root):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
    q=m.inspect_dictionary_bundle_repair(**args);moved=root.rename(tmp_path/'moved')
    args={k:moved/v.relative_to(root) for k,v in args.items()}
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('Read-only selection executed'))
    assert m.inspect_dictionary_bundle_repair(**args)==q
    assert all(((moved/p).read_bytes(),(moved/p).stat().st_mtime_ns)==v for p,v in before.items())


def test_reinspection_detects_source_change_during_derivative_read(tmp_path,monkeypatch):
    m,root,args,state=fixture(tmp_path,monkeypatch);original=m.read_captured_mixed_gradients
    def changed(path):
        q=original(path);(root/'prepared/0.cif').write_text('CHANGED DURING READ');return q
    monkeypatch.setattr(m,'read_captured_mixed_gradients',changed)
    with pytest.raises(ValueError):m.inspect_dictionary_bundle_repair(**args)


@pytest.mark.parametrize('defect',['copying','numeric_count','missing_stereo','unknown_stereo','caller_attested'])
def test_missing_or_weaker_proof_never_becomes_chemical_authority(tmp_path,monkeypatch,defect):
    m,root,args,state=fixture(tmp_path,monkeypatch)
    if defect in ['copying','numeric_count']:
        p=root/'attribution/captures/001/native_receipt.json';r=json.loads(p.read_text());proof=r['native_validation']['full_monomer_inventory']
        if defect=='copying':proof['use_ncs_to_build_restraints']=True
        else:proof['atom_count']=True
        p.write_text(json.dumps(r))
    if defect=='missing_stereo':
        old=m.resolve_dictionary_snapshot
        def missing(path):
            s=old(path);s['qualification']['source_assessment']['finished_stereo'].clear();return s
        monkeypatch.setattr(m,'resolve_dictionary_snapshot',missing)
    if defect=='unknown_stereo':state['stereo']='UNKNOWN'
    if defect=='caller_attested':
        p=root/'attribution/captured_linear_attribution.json';r=json.loads(p.read_text());r['kernel_execution_authentication']='CALLER_REQUIRED';p.write_text(json.dumps(r))
        assert m.inspect_dictionary_bundle_repair(**args)['decision']['selected']=='verified_prepared_bundle';return
    with pytest.raises(ValueError):m.inspect_dictionary_bundle_repair(**args)


def test_unchanged_bystander_and_policy_are_part_of_selected_bundle(tmp_path,monkeypatch):
    m,root,args,state=fixture(tmp_path,monkeypatch);seen=[];old=m.inspect_dictionary_bundle_native
    def checked(bundle,baseline,prepared):
        seen.append((Path(bundle),Path(baseline),Path(prepared)));return old(bundle,baseline,prepared)
    monkeypatch.setattr(m,'inspect_dictionary_bundle_native',checked)
    r=m.repaired_dictionary_bundle_inputs(**args)
    assert seen==[(args['bundle'],args['baseline_receipt'],args['attribution_directory']/'captures/000/native_receipt.json')]
    assert r['dictionaries'][1].read_bytes()==(args['bundle']/'1.cif').read_bytes()
    assert r['phils']==[args['bundle']/'0.phil']
    assert set(r['review']['component_decisions'])=={'AAA','BBB'}
    assert all(v['ranking']=='DECLARED_SOURCE_ORDER' and v['converged'] is None for v in r['review']['component_decisions'].values())


def test_renamed_component_uses_ownership_not_ligand_name(tmp_path,monkeypatch):
    m,root,args,state=fixture(tmp_path,monkeypatch)
    (args['bundle']/'components/AAA').rename(args['bundle']/'components/Q17')
    for path in root.rglob('*'):
        if path.is_file():path.write_bytes(path.read_bytes().replace(b'AAA',b'Q17'))
    read=m.read_dictionary_bundle
    def renamed(path):
        b=read(path);b['report']['components'][0]='Q17';b['component_dictionaries']['Q17']=b['component_dictionaries'].pop('AAA');return b
    monkeypatch.setattr(m,'read_dictionary_bundle',renamed)
    p=args['attribution_directory']/'bundle/linear_torsion_bundle.json';plan=json.loads(p.read_text());plan['steps'][0]['component']='Q17';p.write_text(json.dumps(plan))
    q=m.inspect_dictionary_bundle_repair(**args)
    assert q['decision']['selected']=='repaired_prepared_bundle' and 'Q17' in q['component_decisions']
