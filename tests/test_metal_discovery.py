"""Source-backed single-site placement; synthetic native files, no refinement."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nasolve.metal import Recipe, RecipeError
from nasolve.metal.context import load_run_context, _reference
from nasolve.metal.materialize import build_hypothesis, verify_hypothesis
from .test_metal_materialize import control, atom


def scene(tmp_path, *, xyz=(42., 0., 0.), two_sites=False, heavy_cell=40.):
    pytest.importorskip('cctbx')
    from cctbx import crystal, miller
    from cctbx.array_family import flex
    from iotbx import reflection_file_reader  # Load native libraries before no-process assertions.
    from nasolve.autosol import _pdb_atoms
    context, recipe, original = control(tmp_path)
    run=context.run
    ref=lambda p:_reference(p,run)
    symmetry=crystal.symmetry(unit_cell=(40,40,40,90,90,90),space_group_symbol='P 1')
    indices=miller.set(crystal_symmetry=symmetry,
        indices=flex.miller_index([(0,0,1),(0,1,0),(1,0,0)]),anomalous_flag=False)
    fo=miller.array(indices,data=flex.double([8,10,12]),sigmas=flex.double([1,2,3])).set_observation_type_xray_amplitude()
    flags=miller.array(indices,data=flex.int([1,0,1]))
    anomalous=fo.generate_bijvoet_mates().set_observation_type_xray_intensity()
    data=run.parent.parent/'observations.mtz'
    mtz=fo.as_mtz_dataset(column_root_label='F');mtz.add_miller_array(flags,column_root_label='FreeR_flag')
    mtz.add_miller_array(anomalous,column_root_label='I');mtz.mtz_object().write(str(data))
    folder=run/'external';folder.mkdir()
    phases=folder/'phases.mtz'
    miller.array(indices,data=flex.hendrickson_lattman([(1,2,3,4),(5,6,7,8),(9,10,11,12)])).as_mtz_dataset(column_root_label='HL').mtz_object().write(str(phases))
    mr=run/'Phaser/mr_solution.pdb';mr.parent.mkdir();mr.write_bytes((run/'model.pdb').read_bytes())
    sequence=run/'sequence.txt';sequence.write_text('>DNA\nACGT\n')
    report_path=run/'report.json';report=json.loads(report_path.read_text())
    report['inputs'].update(reflections_sha256=ref(data)['sha256'],frame_sequence=ref(sequence))
    report_path.write_text(json.dumps(report))
    heavy=folder/'heavy.pdb'
    header=(run/'model.pdb').read_text().splitlines()[0]
    header=header[:6]+f'{heavy_cell:9.3f}'+header[15:]
    heavy.write_text(header+'\n'+atom(1,'HG','HG','Z',1,xyz,'HG',1.6,72.95)
        +(atom(2,'HG','HG','Z',2,(43,2,1),'HG',.4,90) if two_sites else '')+'END\n')
    parameters=folder/'autosol.eff'
    parameters.write_text('''autosol {
 data = "/old/data.mtz"
 seq_file = "/old/sequence.txt"
 atom_type = "Hg"
 lambda = 0.920085
 labels = "I(+) SIGI(+) I(-) SIGI(-)"
 sites = None
 phasing {
  input_partpdb_file = "/old/mr.pdb"
  mad_ha_add_list = None
 }
 model_building {
  build = False
  phase_improve_and_build = False
 }
 general {
  nproc = 2
 }
}
''')
    command=['/historical/phenix.autosol','autosol.data=/old/data.mtz','autosol.seq_file=/old/sequence.txt',
        'autosol.atom_type=Hg','autosol.lambda=0.920085','autosol.labels=I(+) SIGI(+) I(-) SIGI(-)',
        'autosol.phasing.input_partpdb_file=/old/mr.pdb','autosol.model_building.build=False',
        'autosol.model_building.phase_improve_and_build=False','autosol.general.nproc=2']
    producer=folder/'producer.json'
    producer.write_text(json.dumps(dict(status='AUTOSOL_OUTPUTS_CAPTURED_NOT_ADOPTED',
        production_phase_adoption=False,phenix_version_output='Synthetic fixture, not a native execution',
        autosol=dict(adoption='EXPERIMENT_ONLY',exit_code=0,primary_species='Hg',additional_species=None,
          wavelength=.920085,sites_argument=None,input_model_sha256=ref(mr)['sha256'],
          input_reflections_sha256=ref(data)['sha256'],sequence_sha256=ref(sequence)['sha256'],
          refinement_data_sha256=ref(phases)['sha256'],heavy_atom_sha256=ref(heavy)['sha256'],
          command=command,effective=dict(build=False,phase_improve_and_build=False,sites=None,nproc=2),
          observation_labels=['I(+)','SIGI(+)','I(-)','SIGI(-)'],sites=_pdb_atoms(heavy),
          discovered_site_count=2 if two_sites else 1))))
    declaration=dict(policy_id='external-autosol-rehearsal-source-v1',element='Hg',wavelength_A=.920085,
        phase_labels=['HLA','HLB','HLC','HLD'],sources={k:ref(p) for k,p in dict(producer=producer,
        parameters=parameters,mr_model=mr,sequence=sequence,observations=data,phases=phases,heavy_atoms=heavy).items()})
    context=load_run_context(run,records=context.roles.records())
    site={k:v for k,v in original['sites'][0].items() if k!='xyz'}
    site.update(occupancy=.65,b_iso=220.,formal_charge=2,source_note='Explicit initial state, not measured Q/B')
    return SimpleNamespace(context=context,recipe=recipe,site=site,external=declaration,run=run,heavy=heavy)


def plan(case, **kwargs):
    from nasolve.metal.discovery import plan_autosol_site
    return plan_autosol_site(case.context,case.recipe,external_autosol=case.external,
        anchor_nodes=kwargs.pop('anchor_nodes',['d1','d2']),site=case.site,**kwargs)


def snapshot(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_displaced_discovery_builds_only_a_numbered_unselected_hypothesis(tmp_path):
    case=scene(tmp_path);before=snapshot(case.run);raw=(case.run/'model.pdb').read_bytes()
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')):
        proposal=plan(case)
        assert snapshot(case.run)==before
        result=build_hypothesis(case.context,case.recipe,proposal)
        directory=(case.run/result['files']['model']['relative_path']).parent
        assert verify_hypothesis(case.run,directory)==result
    assert proposal['schema_version']==2
    review=proposal['discovery']['review']
    assert review['selected_image']['operator_xyz']=='x-1,y,z'
    assert proposal['sites'][0]['xyz']==pytest.approx([2,0,0])
    assert review['source_site']['occupancy']==1.6
    assert result['sites'][0]['occupancy']==.65 and result['sites'][0]['b_iso']==220.
    assert not review['geometry_accepted'] and not review['ordinary_autosol_approval']
    output=(directory/'model.pdb').read_bytes()
    retained=b''.join(line for line in output.splitlines(keepends=True)
        if not(line.startswith(b'HETATM') and line[21:22]==b'M'))
    assert retained==raw
    assert all((case.run/p).read_bytes()==data for p,data in before.items())
    assert not (case.run/'AutoRefine/checkpoints.json').exists()


def test_saved_discovery_relocates_without_build_source_or_current_report(tmp_path):
    case=scene(tmp_path);proposal=plan(case)
    result=build_hypothesis(case.context,case.recipe,proposal)
    relative=Path(result['files']['model']['relative_path']).parent
    old=tmp_path/'dataset';moved=tmp_path/'moved';shutil.move(old,moved)
    run=moved/'AutoMR/run_001';assert not old.exists()
    rp=run/'report.json';report=json.loads(rp.read_text());report['later_status']='unchanged scientific inputs'
    rp.write_text(json.dumps(report))
    before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('No native process')):
        assert verify_hypothesis(run,run/relative)==result
    assert snapshot(moved)==before


@pytest.mark.parametrize('change',['xyz','raw_Q','review','operator','anchor','extra','policy'])
def test_changed_plan_refuses_before_allocation(tmp_path,change):
    case=scene(tmp_path);proposal=plan(case)
    if change=='xyz':proposal['sites'][0]['xyz'][0]+=.1
    elif change=='raw_Q':proposal['sites'][0]['occupancy']=1.6
    elif change=='review':proposal['discovery']['review']['source_site']['occupancy']=.65
    elif change=='operator':proposal['discovery']['review']['selected_image']['operator_xyz']='x,y,z'
    elif change=='anchor':proposal['discovery']['anchor_nodes']=['m1']
    elif change=='extra':proposal['discovery']['accept_geometry']=True
    else:proposal['discovery']['policy_id']='trust-coordinates'
    before=snapshot(case.run)
    with pytest.raises((RecipeError,ValueError)):
        build_hypothesis(case.context,case.recipe,proposal)
    assert not (case.run/'Metal').exists() and snapshot(case.run)==before


@pytest.mark.parametrize('kwargs,message',[
    ({'xyz':(20,0,0)},'Ambiguous'),
    ({'xyz':(22,0,0)},'different metal images'),
    ({'two_sites':True},'exactly one discovered'),
    ({'heavy_cell':41},'crystal frames differ'),
])
def test_unresolved_or_incompatible_site_context_refuses(tmp_path,kwargs,message):
    case=scene(tmp_path,**kwargs);before=snapshot(case.run)
    with pytest.raises((RecipeError,ValueError),match=message):plan(case)
    assert snapshot(case.run)==before


@pytest.mark.parametrize('kwargs',[
    {'max_image_tests':1},{'max_image_tests':True},{'max_image_tests':2_000_001},
    {'image_ambiguity_tolerance_A':float('nan')},{'anchor_nodes':[]},
    {'anchor_nodes':['d1','d1']},{'anchor_nodes':['unknown']},
    {'atoms':[]},
])
def test_bounded_explicit_input_refuses_without_writes(tmp_path,kwargs):
    case=scene(tmp_path);before=snapshot(case.run)
    with pytest.raises((RecipeError,ValueError)):plan(case,**kwargs)
    assert snapshot(case.run)==before


def test_source_recheck_precedes_new_allocation_and_saved_replay(tmp_path):
    case=scene(tmp_path);proposal=plan(case)
    result=build_hypothesis(case.context,case.recipe,proposal)
    directory=(case.run/result['files']['model']['relative_path']).parent
    case.heavy.write_bytes(case.heavy.read_bytes()+b'REMARK changed\n')
    before=snapshot(case.run)
    with pytest.raises((RecipeError,ValueError)):build_hypothesis(case.context,case.recipe,proposal)
    with pytest.raises((RecipeError,ValueError)):verify_hypothesis(case.run,directory)
    assert snapshot(case.run)==before and not (case.run/'Metal/hypothesis_002').exists()


def test_multiple_recipe_metals_cannot_split_an_unresolved_cluster(tmp_path):
    case=scene(tmp_path);doc=case.recipe.to_dict()
    doc['nodes'].append(dict(id='m2',kind='metal',element='Hg'));case.recipe=Recipe(doc)
    with pytest.raises(RecipeError,match='clusters require'):plan(case)


def test_two_anchor_labels_cannot_double_count_one_atom(tmp_path):
    case=scene(tmp_path);doc=case.recipe.to_dict()
    doc['nodes'] += [dict(id='a1',kind='atom'),dict(id='a2',kind='atom')]
    case.recipe=Recipe(doc);key=case.context.imported.snapshot.atoms[0].key.to_dict()
    with pytest.raises(RecipeError,match='distinct parent atoms'):
        plan(case,anchor_nodes=['a1','a2'],atoms={'a1':key,'a2':key})


def test_planning_checks_the_imported_atoms_against_the_source_bytes(tmp_path):
    from nasolve.metal.context import MetalContext, parse_pdb
    case=scene(tmp_path)
    raw=(case.run/'model.pdb').read_bytes().replace(b'   0.000   0.000   0.000',b'   0.100   0.000   0.000',1)
    changed=parse_pdb(raw,checkpoint_id='postmr')
    case.context=MetalContext(case.run,changed,case.context.roles,case.context._document)
    with pytest.raises(RecipeError,match='Parent inventory'):
        plan(case)


def test_discovery_change_during_writing_cannot_publish_a_manifest(tmp_path,monkeypatch):
    from nasolve.metal import materialize
    case=scene(tmp_path);proposal=plan(case);original=materialize._sources
    def changed(context,**kwargs):
        result=original(context,**kwargs)
        if (case.run/'Metal/hypothesis_001/model.pdb').exists():
            case.heavy.write_bytes(case.heavy.read_bytes()+b'REMARK changed during build\n')
        return result
    monkeypatch.setattr(materialize,'_sources',changed)
    with pytest.raises(RecipeError):build_hypothesis(case.context,case.recipe,proposal)
    directory=case.run/'Metal/hypothesis_001'
    assert (directory/'failure.json').exists() and not (directory/'manifest.json').exists()
