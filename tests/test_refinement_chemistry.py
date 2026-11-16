"""Final chemistry reports retain exact lineage, evidence scope and negative results."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nasolve.checkpoints import append_checkpoint, _file_reference, initialize_registry, read_registry
from nasolve.refinement_chemistry import read_refinement_chemistry, _readback
from tests.test_cif_postmr_publication import setup, snapshot
from tests.test_cif_attachment_native import fixture as native_fixture, rebind, save, artifact
from tests.test_cif_triple_bond_audit import fixture as triple_fixture


def child(run, registry, parent, number=1):
    item = deepcopy(parent)
    item.update(id=f'refine-{number:03d}', parent=parent['id'], kind='refinement', status='REVIEW')
    item.pop('checked_preparation', None)
    item.pop('preparation_relation', None)
    model = run / f'final-{number}.pdb'; model.write_bytes(run.joinpath(parent['model']['relative_path']).read_bytes())
    item['model'] = _file_reference(model, run)
    append_checkpoint(run, registry, item, select=False)
    return item


def checked_run(tmp_path, monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    run, exact, calls = setup(tmp_path, monkeypatch)
    root = run/'PostMR/projection';root.mkdir()
    projection, _ = triple_fixture(root)
    exact['preparation'] = dict(bundle_directory=root, bundle=dict(
        projections={'A:1':(projection,'Q17')}, report=dict(files=[dict(path='source.cif',sha256=sha256(projection.read_bytes()).hexdigest())])))
    publish_checked_preparation(run, attempt_number=1)
    _, registry = read_registry(run)
    item = child(run, registry, registry['checkpoints'][0])
    calls.clear()
    return run, exact, calls, item


def test_missing_capture_is_unassessed_single_read_and_does_not_select(tmp_path, monkeypatch):
    run, exact, calls, item = checked_run(tmp_path, monkeypatch)
    before = snapshot(run)
    with patch('subprocess.Popen', side_effect=AssertionError('reporting cannot launch tools')):
        result = read_refinement_chemistry(run, checkpoint=item['id'])
    assert result['checkpoint'] == item['id'] and result['preparation_checkpoint'] == 'postmr'
    assert result['status'] == result['target_screen'] == result['coordinate_screen'] == 'UNASSESSED'
    assert result['actual_refinement_manager'] == 'NOT_ASSESSED'
    assert result['declared_sites']['A:1']['component'] == 'Q17'
    assert calls == [1] and snapshot(run) == before


def test_legacy_refinement_has_no_inferred_site_or_native_proof(tmp_path):
    from tests.test_checkpoints import make_checkpoint_run
    run = make_checkpoint_run(tmp_path); _, registry = initialize_registry(run)
    item = child(run, registry, registry['checkpoints'][0]); before = snapshot(run)
    result = read_refinement_chemistry(run, checkpoint=item['id'])
    assert result['status'] == 'UNASSESSED' and result['preparation_checkpoint'] is None
    with pytest.raises(ValueError, match='projections'):
        read_refinement_chemistry(run, checkpoint=item['id'],native_receipt=tmp_path/'absent')
    assert snapshot(run) == before


def test_explicit_refinement_required(tmp_path, monkeypatch):
    run, _, _, _ = checked_run(tmp_path, monkeypatch)
    for checkpoint in (None, '', 'postmr'):
        with pytest.raises(ValueError, match='refinement checkpoint'):
            read_refinement_chemistry(run, checkpoint=checkpoint)


def native_control(tmp_path, *, bent=False):
    # Full saved receipt authentication is real; the captured geometry is a small
    # synthetic native observation, never a claim of executed Phenix science.
    _, receipt = native_fixture(tmp_path)
    source, values = triple_fixture(tmp_path)
    r=json.loads(receipt.read_text()); n=r['native_validation']; root=receipt.parent
    names=['L','X','Y','R']; points=[[-1.4,.001,0.],[0.,0.,0.],[1.2,0.,0.],[2.6,.3 if bent else .001,0.]]
    atoms=[];lines=[]
    for i,(name,xyz) in enumerate(zip(names,points)):
        atoms.append(dict(i_seq=i,atom_id=name,label=str(i),element='C',xyz=xyz,occupancy=1.,
            identity=dict(chain_id='A',resseq='1',resname='Q17',icode='',altloc='',model_id='')))
        x,y,z=xyz
        lines.append(f'HETATM{i+1:5d} {name:>4s} Q17 A   1    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00           C\n')
    model=tmp_path/'final.pdb';model.write_text(''.join(lines)+'END\n');(root/'inputs/model.pdb').write_bytes(model.read_bytes())
    bond=dict(i_seqs=[1,2],atoms=['1','2'],distance_ideal=1.2,weight=2500.,symmetry_operation=None)
    angles=[dict(i_seqs=ids,atoms=[str(i) for i in ids],angle_ideal=180.,weight=1/9) for ids in ([0,1,2],[1,2,3])]
    details=dict(bond_simple=[bond],bond_asu=[],angle=angles,chirality=[],dihedral=[],const_dihedral=[],planarity=[],parallelity=[])
    n.update(atoms=atoms,atom_count=4,monomer_mappings=dict(status='RECORDED',rows=[dict(site='A:1',
        metadata=dict(effective_definition=dict(bonds=[dict(atom_id_1='X',atom_id_2='Y',type='triple')])))]),
        geometry=dict(status='RECORDED',sites_cart_exact=points,simple_bonds=[bond],asu_bonds=[],
            proxy_details=details,proxy_counts={k:len(v) for k,v in details.items()}))
    r['inputs']=[dict(artifact(root/'inputs/model.pdb',root),role='model',input_index=0)]
    save(receipt,r);rebind(receipt)
    return model, {'A:1':(source,'Q17')}, receipt


@pytest.mark.parametrize('bent',[False,True])
def test_exact_captured_model_distinguishes_targets_and_achieved_coordinates(tmp_path,bent):
    model,projections,receipt=native_control(tmp_path,bent=bent); before=snapshot(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        result=_readback(model,projections,[],[],receipt)
    assert result['target_screen']=='PASS'
    assert result['coordinate_screen']==('REVIEW' if bent else 'PASS')
    assert result['status']==('REVIEW' if bent else 'SCOPED_TRIPLE_SCREEN_PASS')
    assert result['actual_refinement_manager']=='NOT_ASSESSED'
    assert result['native_scope']=='SEPARATE_FINAL_MODEL_REINTERPRETATION'
    assert result['scientific_approval']=='NOT_RUN' and not result['automatic_adoption']
    assert snapshot(tmp_path)==before


@pytest.mark.parametrize('defect',['model','worker','hash','dictionary','phil','coordinates','count','failed'])
def test_damaged_or_differently_bound_capture_is_never_missing_or_pass(tmp_path,defect):
    model,projections,receipt=native_control(tmp_path)
    dictionaries=[];phils=[]
    if defect=='model':model.write_text(model.read_text().replace('   2.600','   2.700'))
    elif defect=='worker':(receipt.parent/'native_worker.py').write_text('raise Exception()');rebind(receipt)
    elif defect=='hash':(receipt.parent/'native.log').write_text('changed')
    elif defect in {'dictionary','phil'}:
        path=tmp_path/'extra';path.write_text('extra input')
        (dictionaries if defect=='dictionary' else phils).append(path)
    else:
        def change(r):
            if defect=='coordinates':r['native_validation']['geometry']['sites_cart_exact'][0][0]+=.2
            elif defect=='count':r['native_validation']['geometry']['proxy_counts']['angle']+=1
            else:r['execution']['returncode']=2
        rebind(receipt,change)
    before=snapshot(tmp_path)
    with pytest.raises(ValueError):_readback(model,projections,dictionaries,phils,receipt)
    assert snapshot(tmp_path)==before


def test_relocated_checked_report_does_not_consult_original_paths(tmp_path,monkeypatch):
    run,exact,calls,item=checked_run(tmp_path,monkeypatch)
    old=run.parents[1]; moved=tmp_path/'moved';old.rename(moved);newrun=moved/run.relative_to(old)
    def relocate(value):
        if isinstance(value,Path) and value.is_relative_to(old):return moved/value.relative_to(old)
        if isinstance(value,dict):return {k:relocate(v) for k,v in value.items()}
        if isinstance(value,list):return [relocate(v) for v in value]
        if isinstance(value,tuple):return tuple(relocate(v) for v in value)
        return value
    exact=relocate(exact)
    monkeypatch.setattr('nasolve.cif_complete_request.read_dictionary_request_result',lambda *a:exact)
    assert not old.exists();before=snapshot(moved)
    result=read_refinement_chemistry(newrun,checkpoint=item['id'])
    assert result['status']=='UNASSESSED' and snapshot(moved)==before

from tests.test_cif_postmr_publication import alternative_preparation


def add_projection(exact, directory, code):
    directory.mkdir()
    path,_=triple_fixture(directory,code)
    exact['preparation']=dict(bundle_directory=directory,bundle=dict(
        projections={'A:1':(path,code)},report=dict(files=[dict(path=path.name,sha256=sha256(path.read_bytes()).hexdigest())])))


def test_report_uses_ancestor_alternative_not_root_latest_or_current(alternative_preparation):
    publication,run,values,reads=alternative_preparation
    add_projection(values[1],run/'first-projection','Q17')
    add_projection(values[2],run/'second-projection','Z99')
    publication.publish_preparation_alternative(run,attempt_number=2)
    _,registry=read_registry(run)
    alternate=registry['checkpoints'][1]
    chosen=child(run,registry,alternate)
    other=child(run,registry,registry['checkpoints'][0],number=2)
    reads.clear();before=snapshot(run)
    result=read_refinement_chemistry(run,checkpoint=chosen['id'])
    assert result['preparation_checkpoint']=='prepare-002'
    assert result['declared_sites']['A:1']['component']=='Z99'
    assert reads==[(1,2)] and snapshot(run)==before
    assert read_refinement_chemistry(run,checkpoint=other['id'])['declared_sites']['A:1']['component']=='Q17'


def test_round_namespace_adapter_is_used_without_changing_inherited_phil(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    from nasolve.cif_native_monomers import FULL_MODEL_PHIL
    from nasolve.autorefine import execute_autorefine
    from tests.test_autorefine import make_refine,make_mtz_dump
    import nasolve.refinement_chemistry as chemistry
    run,exact,_=setup(tmp_path,monkeypatch)
    exact['runtime']['phils'][0].write_text(FULL_MODEL_PHIL)
    add_projection(exact,run/'projection','Q17')
    publish_checked_preparation(run,attempt_number=1)
    result=execute_autorefine(run,make_refine(tmp_path),make_mtz_dump(tmp_path,anomalous=False),
        macro_cycles=1,phenix_version='2.2.1-6174',environment={'PATH':'/usr/bin:/bin'})
    original=chemistry._readback;seen=[]
    def observe(model,projections,dictionaries,phils,receipt):
        seen.extend(phils)
        return original(model,projections,dictionaries,phils,receipt)
    monkeypatch.setattr(chemistry,'_readback',observe)
    before=snapshot(run)
    chemistry.read_refinement_chemistry(run,checkpoint=result.checkpoint_id)
    assert len(seen)==1 and seen[0].read_text()=='refinement {\n'+FULL_MODEL_PHIL+'}\n'
    assert seen[0]!=exact['runtime']['phils'][0] and snapshot(run)==before


def test_supplied_capture_reaches_public_report_with_exact_final_model(tmp_path,monkeypatch):
    from nasolve.cif_postmr_publication import publish_checked_preparation
    base=tmp_path/'capture-case';base.mkdir()
    model,projections,receipt=native_control(base,bent=True)
    run,exact,_=setup(tmp_path,monkeypatch)
    from nasolve.cif_model_context import derive_prepared_model_context
    from nasolve.campaign_records import write_record
    original=exact['runtime']['model'].read_text()
    extra=''.join(line[:21]+'C'+line[22:]+'\n' for line in original.splitlines() if line.startswith(('ATOM  ','HETATM')))
    model.write_text(model.read_text().replace('END\n','')+extra+'END\n')
    exact['runtime']['model'].write_bytes(model.read_bytes())
    request=run/'PostMR/DictionaryEngine/request/request.json'
    context=derive_prepared_model_context(model,json.loads((run/'report.json').read_text()),['DA'])
    write_record(request,dict(configuration=dict(model_context=context)),replace=True)
    r=json.loads(receipt.read_text());n=r['native_validation'];home=receipt.parent
    (home/'inputs/model.pdb').write_bytes(model.read_bytes())
    for line in extra.splitlines():
        i=len(n['atoms']);xyz=[float(line[j:j+8]) for j in (30,38,46)]
        n['atoms'].append(dict(i_seq=i,atom_id=line[12:16].strip(),label=str(i),element=line[76:78].strip(),
            xyz=xyz,occupancy=float(line[54:60]),identity=dict(chain_id='C',resseq=line[22:26].strip(),
            resname=line[17:20].strip(),icode='',altloc='',model_id='')))
        n['geometry']['sites_cart_exact'].append(xyz)
    n['atom_count']=len(n['atoms'])
    r['inputs']=[dict(artifact(home/'inputs/model.pdb',home),role='model',input_index=0)]
    spec=json.loads((home/'native_spec.json').read_text());spec.pop('installed_library_only')
    for role,paths in [('dictionary',exact['runtime']['dictionaries']),('phil',exact['runtime']['phils'])]:
        entries=[]
        for index,path in enumerate(paths):
            frozen=home/'inputs'/f'{role}-{index}{path.suffix}';frozen.write_bytes(path.read_bytes())
            entry=frozen.relative_to(home).as_posix();entries.append(entry)
            r['inputs'].append(dict(artifact(frozen,home),role=role,input_index=len(r['inputs'])))
        spec['dictionaries' if role=='dictionary' else 'phil_files']=entries
        n['dictionary_loading' if role=='dictionary' else 'phil_adaptations']=[dict(input=x,status='RECORDED') for x in entries]
    r['dictionary_source_policy']='EXPLICIT_DICTIONARIES'
    save(home/'native_spec.json',spec);save(receipt,r);rebind(receipt)
    source=projections['A:1'][0]
    exact['preparation']=dict(bundle_directory=base,bundle=dict(projections=projections,
        report=dict(files=[dict(path=source.name,sha256=sha256(source.read_bytes()).hexdigest())])))
    publish_checked_preparation(run,attempt_number=1)
    _,registry=read_registry(run);item=child(run,registry,registry['checkpoints'][0])
    before=snapshot(tmp_path)
    result=read_refinement_chemistry(run,checkpoint=item['id'],native_receipt=receipt)
    assert result['coordinate_screen']=='REVIEW' and result['target_screen']=='PASS'
    assert result['checkpoint']==item['id'] and snapshot(tmp_path)==before


@pytest.mark.parametrize('defect',['model','projection','restraint'])
def test_changes_between_verified_read_and_report_are_refused(tmp_path,monkeypatch,defect):
    import nasolve.refinement_chemistry as chemistry
    run,exact,_,item=checked_run(tmp_path,monkeypatch)
    original=chemistry._readback
    def changed(model,projections,dictionaries,phils,receipt):
        target={'model':model,'projection':projections['A:1'][0],'restraint':phils[0]}[defect]
        target.write_bytes(target.read_bytes()+b'\n')
        return original(model,projections,dictionaries,phils,receipt)
    monkeypatch.setattr(chemistry,'_readback',changed)
    with pytest.raises((ValueError,RuntimeError),match='changed'):
        chemistry.read_refinement_chemistry(run,checkpoint=item['id'])


def test_absent_triples_are_not_a_chemistry_pass(tmp_path):
    from nasolve.ligand_profiles import _emit
    model,projections,receipt=native_control(tmp_path)
    source,values=triple_fixture(tmp_path)
    values['_chem_comp_bond.value_order'][1]='SING';source.write_text(_emit(values))
    result=_readback(model,projections,[],[],receipt)
    assert result['status']==result['target_screen']==result['coordinate_screen']=='UNASSESSED'
    assert result['sites']['A:1']['triple_bonds']==[]
