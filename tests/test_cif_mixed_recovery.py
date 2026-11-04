"""Bounded recovery uses artificial components; no Phenix qualification here."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest


def parent_fixture(tmp_path, monkeypatch, codes=('Q17','R18'), invalid=('Q17',)):
    from tests.test_cif_stereochemistry_audit import tetrahedron, write
    from nasolve.cif_mixed_native import _ref
    from nasolve.cif_generation import _ideal_seed
    root=tmp_path/'parent';(root/'inputs').mkdir(parents=True)
    sources={};definitions=[];lines=[]
    for number,code in enumerate(codes,1):
        v,g=tetrahedron(code)
        g.update({'_chem_comp_atom.type_energy':['C','O','N','C','H'],
            '_chem_comp_bond.value_dist':['0.0' if code in invalid else '1.5','1.5','1.5','1.5'],
            '_chem_comp_bond.value_dist_esd':['0.02']*4})
        source=write(root/'inputs'/f'{code}.cif',v);sources[code]=_ref(source,root)
        part=write(root/'inputs'/f'{code}_bad.cif',g);definitions.append(part.read_text())
        seed,_=_ideal_seed(source,code)
        lines.extend(l[:22]+f'{number:4d}'+l[26:] for l in seed.splitlines(keepends=True) if l.startswith('HETATM'))
    model=root/'inputs/constructed.pdb';model.write_text(''.join(lines)+'END\n')
    active=root/'inputs/active.phil';active.write_text('refinement {\n pdb_interpretation.secondary_structure {\n enabled = False\n }\n}\n')
    effective=root/'inputs/effective.cif';effective.write_text('\n'.join(definitions))
    report={'policy_id':'cif-mixed-pair-native-membership-v1','status':'REVIEW',
        'inputs':{'model':_ref(model,root),'active_policy':_ref(active,root),'sources':sources},
        'source_authorities':{code:'ARTIFICIAL_SOURCE' for code in codes},
        'effective_dictionaries':[_ref(effective,root)],
        'required_modified_parameterization':{'components':list(codes),'missing':list(invalid)},
        'new_readyset_calls':1,'new_native_calls':0,
        'readyset':{'execution':{'status':'COMPLETED','returncode':0},'unchanged_named_heavy_coordinates':True,
                   'model':_ref(model,root)},'source_inputs_preserved':True}
    (root/'mixed_native.json').write_text(json.dumps(report))
    monkeypatch.setattr('nasolve.cif_mixed_native.read_mixed_native',lambda p:deepcopy(report))
    return root,report,effective


def test_general_selection_keeps_valid_bystander_and_relocates_without_parent(tmp_path,monkeypatch):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery,read_mixed_recovery
    parent,old,effective=parent_fixture(tmp_path,monkeypatch)
    before=effective.read_bytes()
    monkeypatch.setattr('subprocess.Popen',lambda *a,**k:pytest.fail('inspect-only started an SDK process'))
    report=audit_mixed_recovery(parent,None,tmp_path/'recovery')
    assert report['status']=='PREPARED_ONLY' and report['targets']==['Q17']
    assert set(report['inputs']['sources'])=={'Q17','R18'}
    assert report['new_generator_calls']==report['new_native_calls']==0
    assert effective.read_bytes()==before and not report['automatic_adoption'] and not report['requires_cif_review']
    shutil.rmtree(parent);moved=tmp_path/'moved';(tmp_path/'recovery').rename(moved)
    assert read_mixed_recovery(moved)==report


def test_multiple_renamed_invalid_components_are_selected_from_actual_rows(tmp_path,monkeypatch):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery
    parent,_,_=parent_fixture(tmp_path,monkeypatch,codes=('X11','Y22','Z33'),invalid=('X11','Y22'))
    report=audit_mixed_recovery(parent,None,tmp_path/'result')
    assert report['targets']==['X11','Y22'] and set(report['components'])=={'X11','Y22'}


def test_parent_scope_cannot_hide_another_invalid_modified_source(tmp_path,monkeypatch):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery
    parent,report,_=parent_fixture(tmp_path,monkeypatch,invalid=('Q17','R18'))
    report['required_modified_parameterization']={'components':['Q17'],'missing':['Q17']}
    monkeypatch.setattr('nasolve.cif_mixed_native.read_mixed_native',lambda p:deepcopy(report))
    with pytest.raises(ValueError,match='parent numerical scope'):
        audit_mixed_recovery(parent,None,tmp_path/'result')
    assert not (tmp_path/'result').exists()


def test_fresh_anchor_failure_publishes_notes_without_generation_or_native_calls(tmp_path,monkeypatch):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery,read_mixed_recovery
    parent,_,_=parent_fixture(tmp_path,monkeypatch)
    root=tmp_path/'fake-phenix';(root/'bin').mkdir(parents=True)
    python=root/'bin/phenix.python';python.write_text('#!/bin/sh\nexit 7\n');python.chmod(0o755)
    phenix=SimpleNamespace(root=root,executables={'phenix.python':python},environment=os.environ,version='EXPLICIT_FAKE')
    monkeypatch.setattr('nasolve.cif_source_candidate.generate_source_candidate',lambda *a,**k:pytest.fail('failed anchor reached generator'))
    monkeypatch.setattr('nasolve.cif_native_validation.inspect_native_bundle',lambda *a,**k:pytest.fail('failed anchor reached native reader'))
    report=audit_mixed_recovery(parent,phenix,tmp_path/'result',timeout_seconds=10)
    assert report['status']=='REVIEW' and report['source_capture']['record']['execution']['returncode']==7
    assert report['new_source_probe_calls']==1 and report['new_generator_calls']==report['new_native_calls']==0
    assert report['coordinate_decision']['selected']=='verified_constructed_model'
    assert read_mixed_recovery(tmp_path/'result')==report


def test_unreadable_retained_candidate_is_rejected_without_losing_the_original(tmp_path):
    from nasolve.cif_mixed_recovery import _candidate_assessment
    from tests.test_cif_stereochemistry_audit import tetrahedron,write
    source=write(tmp_path/'source.cif',tetrahedron()[0]);before=source.read_bytes()
    candidate=tmp_path/'retained.cif';candidate.write_bytes(b'not a complete CIF dictionary')
    assessment,capability=_candidate_assessment(source,candidate,'Q17')
    assert assessment['candidate_status']=='REJECTED' and not capability
    assert source.read_bytes()==before and candidate.read_bytes()==b'not a complete CIF dictionary'


def fake_builder_installation(tmp_path,candidate):
    """Explicit fake SDK exercises process/binding mechanics, never native chemistry."""
    from tests.test_cif_constructor_backend import installation
    from tests.test_cif_source_candidate import REFERENCE
    from tests.test_cif_generation import HELP,program
    root,python,site,_,_=installation(tmp_path,'correct')
    reader=site/'elbow/chemistry/any_chemical_format_reader.py'
    reader.write_text(reader.read_text().replace("['constructor_worker.py']","['source_candidate_worker.py']"))
    native=site/'elbow/chemistry/SimpleMoleculeClass.py'
    native.write_text(native.read_text()+''' def Setup(self):
  for a in self:a.input_xyz=a.xyz
''')
    folder=site/'elbow/command_line';folder.mkdir();(folder/'__init__.py').write_text('')
    (folder/'builder.py').write_text(REFERENCE+'''
def parser():raise RuntimeError('PREPARED OBJECT MUST BYPASS FILE PARSER')
def post_process(molecule,options):
 import os,shutil
 shutil.copyfile(os.environ['CANDIDATE_FIXTURE'],'candidate.cif')
 shutil.copyfile('source_ideal.pdb','candidate.pdb')
 print('geometry not converged')
 return molecule
''')
    iotbx=site/'iotbx';iotbx.mkdir();(iotbx/'__init__.py').write_text('')
    (iotbx/'phil.py').write_text('# EXPLICIT_FAKE_LIBRARY_ANCHOR\n')
    elbow=program(tmp_path,help_text=HELP+'  --opt_steps=COUNT  Step count\n')
    selected=root/'bin/phenix.elbow';selected.write_bytes(elbow.read_bytes());selected.chmod(0o755)
    return SimpleNamespace(root=root,executables={'phenix.python':python,'phenix.elbow':selected},
        environment={**os.environ,'PYTHONPATH':str(site),'CANDIDATE_FIXTURE':str(candidate)},version='EXPLICIT_FAKE_SDK')


def test_real_owned_builder_boundary_rejects_bad_numerics_and_replays_specs(tmp_path,monkeypatch):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery,read_mixed_recovery,_ref
    parent,_,_=parent_fixture(tmp_path,monkeypatch)
    phenix=fake_builder_installation(tmp_path,parent/'inputs/Q17_bad.cif')
    monkeypatch.setattr('nasolve.cif_native_validation.inspect_native_bundle',lambda *a,**k:pytest.fail('zero bond reached native reader'))
    out=tmp_path/'result';report=audit_mixed_recovery(parent,phenix,out,timeout_seconds=10)
    assert report['status']=='REVIEW' and report['new_source_probe_calls']==report['new_generator_calls']==1
    assert report['new_native_calls']==0
    case=report['components']['Q17']
    assert case['generation']['candidate_retained'] and not case['candidate_numerical_capability']
    assert case['generation']['stopping']['status']=='NOT_CONVERGED_REPORTED'
    assert not case['coordinate_cases'] and report['source_inputs_preserved']
    shutil.rmtree(parent);shutil.rmtree(phenix.root)
    assert read_mixed_recovery(out)==report
    # Changing a bounded builder instruction cannot be hidden by refreshing its
    # top-level byte hash: the maintained reader reconstructs the exact spec.
    spec_path=out/case['generation']['directory']['path']/'candidate_spec.json'
    original_spec=spec_path.read_bytes()
    spec=json.loads(original_spec);spec['arguments'][-1]='--opt_steps=181'
    spec_path.write_text(json.dumps(spec))
    changed=deepcopy(report)
    changed['outputs']=[_ref(spec_path,out) if r['path']==spec_path.relative_to(out).as_posix() else r for r in report['outputs']]
    (out/'mixed_recovery.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='source-object specification'):
        read_mixed_recovery(out)
    # An empty native-case mapping must never become a PASS through stored
    # booleans and advertised counters alone.
    spec_path.write_bytes(original_spec)
    changed=deepcopy(report);changed['status']='MIXED_RECOVERY_ISOLATED_PASS';changed['new_native_calls']=2
    changed['components']['Q17']['decision']={'continue_solving':True}
    changed['components']['Q17']['isolated_qualification']={'native_usable':True}
    (out/'mixed_recovery.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError,match='execution counters'):
        read_mixed_recovery(out)


def test_usable_candidate_runs_both_bounded_isolated_reads_and_keeps_failure_notes(tmp_path,monkeypatch):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery,read_mixed_recovery
    from tests.test_cif_candidate_usability import component
    from tests.test_cif_stereochemistry_audit import write
    parent,_,_=parent_fixture(tmp_path,monkeypatch)
    candidate=write(tmp_path/'valid-candidate.cif',component())
    phenix=fake_builder_installation(tmp_path,candidate)
    # The explicit fake SDK supports the source builder but lacks a native
    # manager. Both owned reads must still be bounded, recorded and replayable.
    report=audit_mixed_recovery(parent,phenix,tmp_path/'result',timeout_seconds=10)
    case=report['components']['Q17']
    assert report['status']=='REVIEW' and case['candidate_numerical_capability']
    assert case['assessment']['candidate_status']=='CANDIDATE_REVIEW'
    assert report['new_generator_calls']==1 and report['new_native_calls']==2
    assert set(case['coordinate_cases'])=={'source_seed','generated_output'}
    assert all(v['native']['execution']['timeout_seconds']==10 for v in case['coordinate_cases'].values())
    assert not case['isolated_qualification']['native_usable'] and not case['decision']['continue_solving']
    assert report['coordinate_decision']['selected']=='verified_constructed_model'
    assert read_mixed_recovery(tmp_path/'result')==report


@pytest.mark.parametrize('defect',['empty','false_summary','too_many'])
def test_missing_summary_cannot_replace_actual_capability_evidence(tmp_path,monkeypatch,defect):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery
    codes=('A11','A12','A13','A14','A15') if defect=='too_many' else ('Q17','R18')
    invalid=codes if defect=='too_many' else () if defect=='empty' else ('Q17',)
    parent,report,_=parent_fixture(tmp_path,monkeypatch,codes=codes,invalid=invalid)
    if defect=='false_summary':report['required_modified_parameterization']['missing']=['R18']
    monkeypatch.setattr('nasolve.cif_mixed_native.read_mixed_native',lambda p:deepcopy(report))
    with pytest.raises(ValueError):audit_mixed_recovery(parent,None,tmp_path/'result')
    assert not (tmp_path/'result').exists()


@pytest.mark.parametrize('steps,timeout',[(0,600),(601,600),(True,600),(180,0),(180,601),(180,True),(180,1.5)])
def test_invalid_bounds_stop_before_reading_parent(tmp_path,steps,timeout):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery
    with pytest.raises(ValueError):audit_mixed_recovery(tmp_path/'absent',None,tmp_path/'result',single_block_steps=steps,timeout_seconds=timeout)
    assert not (tmp_path/'result').exists()


@pytest.mark.parametrize('defect',['status','source','model','extra','escape','symlink'])
def test_reader_rejects_incomplete_success_and_modified_inputs(tmp_path,monkeypatch,defect):
    from nasolve.cif_mixed_recovery import audit_mixed_recovery,read_mixed_recovery
    parent,_,_=parent_fixture(tmp_path,monkeypatch);out=tmp_path/'result'
    report=audit_mixed_recovery(parent,None,out)
    if defect=='status':report['status']='MIXED_RECOVERY_ISOLATED_PASS'
    elif defect=='source':(out/report['inputs']['sources']['Q17']['path']).write_bytes(b'CHANGED')
    elif defect=='model':(out/report['inputs']['model']['path']).write_bytes(b'CHANGED')
    elif defect=='extra':(out/'extra.txt').write_text('UNBOUND')
    elif defect=='escape':report['inputs']['sources']['Q17']['path']='../outside.cif'
    else:
        p=out/report['inputs']['sources']['Q17']['path'];p.unlink();p.symlink_to(parent/'inputs/Q17.cif')
    (out/'mixed_recovery.json').write_text(json.dumps(report))
    with pytest.raises(ValueError):read_mixed_recovery(out)
