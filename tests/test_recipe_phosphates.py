"""Recipe chemistry is explicit, site-scoped and frozen before execution."""
from pathlib import Path

from nasolve.automr_input import AutoMRIntent, resolve_automr_input
from .helpers import make_dataset



import copy
import json
import shutil
import pytest
from dataclasses import replace
from nasolve.automr_input import read_intent, format_intent, AutoMRInputError
from nasolve.automr import prepare_automr, _post_mr_plan
from nasolve.phosphate import (
    requested_op3_sites, PhosphateError, sanitize_phosphates,
    validate_phosphate_intent, phosphate_intent_summary,
)
from nasolve.presets import load_preset, PresetError
from nasolve.campaigns import plan_campaign, campaign_status, _validate_plan, CampaignError
from nasolve.campaign_stages import _frozen_selection
from nasolve.cli import main
from .helpers import make_mtz_dump, make_ready_set
from .test_phosphate import phosphate
from .test_postmr import postmr_model_text
from nasolve.postmr import prepare_postmr


ROOT = Path(__file__).parents[1]

def test_w_recipe_declares_d1_phosphate_before_postmr(tmp_path):
    dataset = make_dataset(tmp_path / 'ED', include_model=False)
    resolved = resolve_automr_input(
        dataset, AutoMRIntent(mode='standard', frame='W', pair='E:D'),
        frames_dir=ROOT / 'MR_frames', environ={},
    )
    assert resolved.allow_op3_sites == ('D:1',)
    assert resolved.phosphate_intent['source'] == 'recipe'
    assert resolved.phosphate_intent['recipe']['id'] == '5w6w'


def resolve(tmp_path, settings='', *, frame='W', recipe=None):
    dataset = make_dataset(tmp_path / 'dataset', include_model=False)
    config = dataset / 'nasolve.txt'
    config.write_text(f'[automr]\nframe = {frame}\npair = C:G\n{settings}')
    return resolve_automr_input(dataset, read_intent(config), frames_dir=ROOT / 'MR_frames',
                                environ={}, recipe=recipe)


@pytest.mark.parametrize('alias', ['W', '5W6W', 'w', '5w6w'])
def test_frame_aliases_and_cli_selection_use_recipe_card(tmp_path, alias):
    dataset = make_dataset(tmp_path / 'dataset', include_model=False)
    resolved = resolve_automr_input(dataset, AutoMRIntent(), frame_override=alias,
        pair_override='C:G', frames_dir=ROOT / 'MR_frames', environ={})
    assert resolved.allow_op3_sites == ('D:1',)
    record = resolved.phosphate_intent
    assert record['recipe'] == load_preset().phosphate_declaration()
    assert 'recipe 5w6w@1.1.0' in phosphate_intent_summary(resolved.allow_op3_sites, record)


@pytest.mark.parametrize('settings,sites', [
    ('allow_op3_sites = A:1\n', ('A:1',)),
    ('allow_op3_sites = D:1, A:1\n', ('D:1','A:1')),
    ('allow_op3_sites =\n', ()),
])
def test_dataset_setting_overrides_whole_recipe_list_including_empty(tmp_path, settings, sites):
    resolved = resolve(tmp_path, settings)
    assert resolved.allow_op3_sites == sites
    assert resolved.phosphate_intent['source'] == 'dataset'
    assert resolved.phosphate_intent['recipe']['terminal_phosphate_sites'] == ['D:1']
    assert requested_op3_sites({'post_mr_plan': _post_mr_plan(resolved)}) == sites


def test_effective_empty_snapshot_cannot_adopt_later_recipe_defaults(tmp_path):
    resolved = resolve(tmp_path, 'allow_op3_sites =\n')
    snapshot = tmp_path / 'snapshot.txt'
    snapshot.write_text(format_intent(resolved))
    intent = read_intent(snapshot)
    assert intent.op3_sites_explicit
    again = resolve_automr_input(resolved.dataset.root, intent, frames_dir=ROOT / 'MR_frames', environ={})
    assert again.allow_op3_sites == ()


def test_nonstandard_and_other_frames_receive_no_w_permission(tmp_path):
    dataset = make_dataset(tmp_path / 'nonstandard')
    nonstandard = resolve_automr_input(dataset, AutoMRIntent(mode='nonstandard'))
    assert nonstandard.allow_op3_sites == ()
    assert nonstandard.phosphate_intent['source'] == 'none'
    other = make_dataset(tmp_path / 'other', include_model=False)
    other = resolve_automr_input(other, AutoMRIntent(frame='3GBI', pair='C:C'), frames_dir=ROOT / 'MR_frames')
    assert other.allow_op3_sites == ()
    assert other.phosphate_intent['recipe'] is None


@pytest.mark.parametrize('value', ['true', '"D:1"', '["D:1", "D:1"]', '["*"]', '[1]', '["D:1", ""]'])
def test_recipe_flag_validates_exact_sites_not_blanket_boolean(tmp_path, value):
    path=tmp_path/'recipe.toml'
    path.write_text('schema_version=1\nid="test"\nversion="1"\n[chemistry]\n'
                    f'terminal_phosphate_sites={value}\n')
    with pytest.raises(PresetError, match='chemistry.terminal_phosphate_sites'):
        load_preset(path)


def test_custom_recipe_declares_its_own_sites_and_not_w_defaults(tmp_path):
    path=tmp_path/'recipe.toml'
    path.write_text('schema_version=1\nid="variant"\nversion="2"\n'
                    '[chemistry]\nterminal_phosphate_sites=["A:1"]\n')
    selected = resolve(tmp_path, recipe=load_preset(path))
    assert selected.allow_op3_sites == ('A:1',)
    assert selected.phosphate_intent['recipe']['id'] == 'variant'
    path.write_text('schema_version=1\nid="legacy"\nversion="1"\n')
    second=resolve(tmp_path, recipe=load_preset(path))
    assert second.allow_op3_sites == ()


def test_preflight_freezes_card_and_exact_sites_without_rewriting_existing_input(tmp_path):
    resolved = resolve(tmp_path)
    before = resolved.config_source.read_bytes()
    result = prepare_automr(resolved.dataset.root, frames_dir=ROOT/'MR_frames',
                            mtz_dump_executable=make_mtz_dump(tmp_path))
    report=json.loads(result.report_path.read_text())
    assert report['post_mr_plan']['phosphate_intent']==resolved.phosphate_intent
    assert requested_op3_sites(report) == ('D:1',)
    assert 'allow_op3_sites = D:1' in (result.run_directory/'nasolve.input.txt').read_text()
    assert 'recipe 5w6w@1.1.0' in result.phosphate_summary
    assert resolved.config_source.read_bytes() == before


@pytest.mark.parametrize('change', ['sites', 'recipe', 'hash', 'source', 'none', 'null'])
def test_malformed_frozen_recipe_intent_cannot_authorize_phosphate(tmp_path, change):
    resolved=resolve(tmp_path)
    record=copy.deepcopy(resolved.phosphate_intent)
    if change=='sites': record['allow_op3_sites']=['A:1']
    if change=='recipe': record['recipe']['terminal_phosphate_sites']=['A:1']
    if change=='hash': record['recipe']['sha256']='bad'
    if change=='source': record['source']=[]
    if change=='none': record['source']='none'
    if change=='null': record=None
    with pytest.raises(PhosphateError):
        requested_op3_sites({'post_mr_plan': {'allow_op3_sites':['D:1'], 'phosphate_intent':record}})


def test_recipe_permission_never_permits_internal_or_other_terminal_op3(tmp_path):
    allowed=resolve(tmp_path).allow_op3_sites
    source=tmp_path/'model.pdb'
    source.write_text(''.join(phosphate(chain='D', number=1, previous=0)))
    with pytest.raises(PhosphateError, match='conflicts with an internal'):
        sanitize_phosphates(source, tmp_path/'out.pdb', allow_op3_sites=allowed)
    source.write_text(''.join([*phosphate(chain='D',number=1,terminal=True), 'TER\n',
        *phosphate(chain='C', number=1, terminal=True, shift=40)]))
    with pytest.raises(PhosphateError, match='unrequested terminal'):
        sanitize_phosphates(source, tmp_path/'out.pdb', allow_op3_sites=allowed)


def test_declared_site_must_exist_and_is_not_built(tmp_path):
    resolved=resolve(tmp_path)
    model=tmp_path/'model.pdb'
    # Using a model without D:1 is not evidence for skipping its declared chemistry.
    model.write_text(postmr_model_text('DC','DG'))
    changed=replace(resolved, model=model)
    with pytest.raises(AutoMRInputError, match='D:1 does not exist'):
        prepare_automr(resolved.dataset.root, resolved_input=changed,
                       mtz_dump_executable=make_mtz_dump(tmp_path))


def plan(tmp_path):
    root=tmp_path/'campaign'; dataset=make_dataset(root/'ED', include_model=False)
    (dataset/'nasolve.txt').write_text('[automr]\npair = C:G\n')
    payload=plan_campaign(root, frames_directory=ROOT/'MR_frames')
    return root, payload


def test_campaign_freezes_and_reports_recipe_sites_surviving_relocation(tmp_path, monkeypatch, capsys):
    root,payload=plan(tmp_path)
    entry=payload['datasets'][0]
    assert entry['effective_config']['allow_op3_sites']==['D:1']
    frozen=copy.deepcopy(entry['effective_config']['phosphate_intent'])
    old_plan=(root/'NASolveCampaign/plan.json').read_bytes()
    new=tmp_path/'relocated'; shutil.copytree(root,new); shutil.rmtree(root)
    # Neither today's recipe card nor original model catalogue may be consulted.
    import nasolve.automr_input as inputs
    monkeypatch.setattr(inputs,'load_preset',lambda *a, **k: pytest.fail('live recipe consulted'))
    attempt=new/'attempt';attempt.mkdir()
    selected=_frozen_selection(new,entry,attempt)
    assert selected.phosphate_intent==frozen
    assert selected.allow_op3_sites==('D:1',)
    tools=tmp_path/'tools';tools.mkdir()
    result=prepare_automr(new/'ED', resolved_input=selected,
                         mtz_dump_executable=make_mtz_dump(tools))
    report=json.loads(result.report_path.read_text())
    assert report['post_mr_plan']['phosphate_intent']==frozen
    assert requested_op3_sites(report)==('D:1',)
    assert campaign_status(new)['integrity']=='OK'
    assert (new/'NASolveCampaign/plan.json').read_bytes()==old_plan
    assert main(['campaign','status',str(new)])==0
    assert "5'-phosphate/OP3 sites: D:1 (recipe 5w6w@1.1.0)" in capsys.readouterr().out


def test_old_frozen_campaign_and_report_do_not_adopt_new_recipe_permissions(tmp_path):
    root,payload=plan(tmp_path)
    entry=payload['datasets'][0]
    entry['effective_config'].pop('phosphate_intent')
    entry['effective_config']['allow_op3_sites']=[]
    attempt=root/'attempt';attempt.mkdir()
    selected=_frozen_selection(root,entry,attempt)
    assert selected.allow_op3_sites==()
    assert selected.phosphate_intent is None
    assert requested_op3_sites({'frame':{'name':'W'},'post_mr_plan':{}})==()
    assert requested_op3_sites({'frame':{'name':'W'},'post_mr_plan':{'allow_op3_sites':['D:1']}})==('D:1',)
    assert 'allow_op3_sites = \n' in format_intent(selected)


def test_campaign_recipe_identity_and_effective_sites_must_agree(tmp_path):
    root,payload=plan(tmp_path)
    payload['datasets'][0]['effective_config']['phosphate_intent']['recipe']['version']='changed'
    with pytest.raises(CampaignError, match='recipe identity disagree'):
        _validate_plan(payload)


def test_recipe_and_override_visible_in_preset_and_campaign_checks(tmp_path,capsys):
    assert main(['preset','check','5w6w'])==0
    assert "Recipe 5'-phosphate/OP3 sites: D:1" in capsys.readouterr().out
    root=tmp_path/'campaign'; dataset=make_dataset(root/'ED',include_model=False)
    (dataset/'nasolve.txt').write_text('[automr]\npair=C:G\nallow_op3_sites =\n')
    payload=plan_campaign(root,frames_directory=ROOT/'MR_frames')
    config=payload['datasets'][0]['effective_config']
    assert config['allow_op3_sites']==[]
    assert config['phosphate_intent']['source']=='dataset'
    assert main(['campaign','status',str(root)])==0
    assert "5'-phosphate/OP3 sites: none (explicit dataset override)" in capsys.readouterr().out


def test_automatic_w_preflight_to_postmr_readyset_keeps_declared_terminal(tmp_path):
    """Synthetic structure and fake tools; exercises real NASolve orchestration."""
    dataset=make_dataset(tmp_path/'dataset',include_model=False)
    frames=tmp_path/'frames'; cat=frames/'5W6W'; cat.mkdir(parents=True)
    template=postmr_model_text('DC','DG').replace('END\n','')+'TER\n'+''.join(
        phosphate(chain='D',number=1,residue='DC',start=100,shift=50,terminal=True))+'END\n'
    (cat/'C_G.pdb').write_text(template)
    tools=tmp_path/'tools';tools.mkdir()
    pre=prepare_automr(dataset,frame_override='W',pair_override='C:G',frames_dir=frames,
                       mtz_dump_executable=make_mtz_dump(tools))
    run=pre.run_directory; phaser=run/'Phaser';phaser.mkdir()
    solution=phaser/'mr_solution.pdb';solution.write_text(template)
    report=json.loads(pre.report_path.read_text())
    report.update(stage='phaser',status='MR_SUCCESS',execution={'phaser':{'solution_pdb':str(solution)}})
    pre.report_path.write_text(json.dumps(report))
    def builder(model,pairs,out): out.write_text('geometry_restraints.edits {}\n')
    post=prepare_postmr(run,make_ready_set(tools),narestraints_builder=builder)
    assert post.status=='POSTMR_READY'
    final=json.loads((run/'report.json').read_text())
    assert requested_op3_sites(final)==('D:1',)
    assert final['post_mr_plan']['phosphate_intent']['source']=='recipe'
    assert final['postmr']['phosphate_policy']['allow_op3_sites']==['D:1']
    retained=final['postmr']['phosphate_cleanup']['after_readyset']['retained']
    assert [i['site'] for i in retained]==['D:1']
    assert solution.read_text()==template
    assert 'OP3' in post.model_path.read_text()


@pytest.mark.parametrize('name', ['A_T.pdb', 'C_C.pdb', 'C_G.pdb', 'G_C.pdb', 'T_A.pdb', 'T_T.pdb'])
def test_existing_w_catalogue_matches_the_explicit_recipe_declaration(name):
    """Read-only audit of existing reference fixtures, not a Phenix execution."""
    from nasolve.phosphate import audit_phosphates
    model=ROOT/'MR_frames'/'5W6W'/name
    audit=audit_phosphates(model, allow_op3_sites=load_preset().terminal_phosphate_sites)
    assert [item['site'] for item in audit['retained']]==['D:1']
    assert audit['removed']==[]
