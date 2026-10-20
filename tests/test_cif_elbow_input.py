"""Legacy restraints project to a reader dialect without guessing chemistry."""
from pathlib import Path
from copy import deepcopy
import os,sys
import pytest
from nasolve.ligand_profiles import _blocks
from tests.test_cif_generation import write,program,HELP,component
from tests.test_cif_numerical_recovery import source_values


@pytest.mark.parametrize('code',['R17','DP'])
def test_reader_projection_translates_declared_bonds_and_keeps_unknown_atom_stereo(tmp_path,code):
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    from nasolve.cif_elbow_input import prepare_elbow_ccd_input
    source=write(tmp_path/'original.cif',source_values(code));graph=tmp_path/'graph/source.cif'
    prepare_graph_generation_source(source,code,graph);before=source.read_bytes(),graph.read_bytes()
    out=tmp_path/'consumer/source.cif';r=prepare_elbow_ccd_input(graph,code,out);v=_blocks(out)[0].values
    assert v['_chem_comp_bond.value_order']==['SING']*3
    assert v['_chem_comp_bond.pdbx_aromatic_flag']==['N']*3
    assert v['_chem_comp_atom.pdbx_aromatic_flag']==['?']*4
    assert v['_chem_comp_atom.pdbx_stereo_config']==['?']*4
    assert v['_chem_comp_atom.charge']==['0']*4
    assert r['known_chemical_declarations']=='PRESERVED' and r['stereochemistry_inferred'] is False
    assert (source.read_bytes(),graph.read_bytes())==before


@pytest.mark.parametrize('defect',['none','charge_conflict','order_conflict','aromatic_conflict','unsupported_order','stereo_conflict'])
def test_projection_preserves_known_values_and_refuses_ambiguous_dialects(tmp_path,defect):
    from nasolve.cif_elbow_input import prepare_elbow_ccd_input
    v=source_values('Q17');v['_chem_comp_atom.stereo_config']=['R','S','N','?'];v['_chem_comp_atom.aromatic']=['y','y','n','?']
    if defect=='charge_conflict':v['_chem_comp_atom.charge']=['1']*4
    if defect=='order_conflict':v['_chem_comp_bond.value_order']=['DOUB']*3
    if defect=='aromatic_conflict':v['_chem_comp_atom.pdbx_aromatic_flag']=['N']*4
    if defect=='unsupported_order':v['_chem_comp_bond.type'][0]='DELOC'
    if defect=='stereo_conflict':v['_chem_comp_atom.pdbx_stereo_config']=['S']*4
    p=write(tmp_path/'source.cif',v);out=tmp_path/'out/source.cif'
    if defect!='none':
        with pytest.raises(ValueError):prepare_elbow_ccd_input(p,'Q17',out)
        assert not out.exists()
    else:
        r=prepare_elbow_ccd_input(p,'Q17',out);fields=_blocks(out)[0].values
        assert fields['_chem_comp_atom.pdbx_stereo_config']==['R','S','N','?']
        assert fields['_chem_comp_atom.pdbx_aromatic_flag']==['Y','Y','N','?']
        assert r['known_chemical_declarations']=='PRESERVED'


def test_already_complete_public_graph_is_byte_identical(tmp_path):
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    from nasolve.cif_elbow_input import prepare_elbow_ccd_input
    source=Path(__file__).resolve().parent/'fixtures/public_ccd/PDU.cif';graph=tmp_path/'graph/source.cif';out=tmp_path/'consumer/source.cif'
    prepare_graph_generation_source(source,'PDU',graph);r=prepare_elbow_ccd_input(graph,'PDU',out)
    assert out.read_bytes()==graph.read_bytes() and r['added_fields']==[] and r['changed_fields']==[]


@pytest.mark.parametrize('flag',['--opt_steps','--opt-steps',None])
@pytest.mark.parametrize('stopping',['unconverged','unreported'])
def test_explicit_step_control_is_help_checked_and_never_invents_convergence(tmp_path,flag,stopping):
    from nasolve.cif_generation import generate_elbow_candidate
    source=write(tmp_path/'source/component.cif',component('R17'));fixture=write(tmp_path/'fixture.cif',component('R17',numerical=True))
    body="""import os,shutil,sys
from pathlib import Path
assert any(x in sys.argv for x in ['--opt_steps=180','--opt-steps=180'])
shutil.copyfile(os.environ['CANDIDATE_FIXTURE'],'candidate.cif')
"""+('print("geometry not converged\\nstopping attempts")\n' if stopping=='unconverged' else 'print("trial complete without a convergence report")\n')
    help_text=HELP+(f'  {flag}=N          optimisation steps\n' if flag else '')
    exe=program(tmp_path,body,help_text=help_text)
    r=generate_elbow_candidate(source,'R17',tmp_path/'out',exe,environment={**os.environ,'CANDIDATE_FIXTURE':str(fixture)},phenix_version='test-only',single_block_steps=180)
    if flag is None:assert r['execution']['status']=='UNSUPPORTED_GENERATOR' and r['command'] is None
    else:
        assert f'{flag}=180' in r['command'] and r['status']=='CANDIDATE_REVIEW'
        assert r['optimization_stopping']['status']==('NOT_CONVERGED_REPORTED' if stopping=='unconverged' else 'NOT_REPORTED')
        assert r['optimization_stopping']['convergence_claimed'] is False
        assert r['optimization_control']['single_block_steps']==180


@pytest.mark.parametrize('steps',[True,0,-1,601,1.5])
def test_unsupported_step_request_refuses_before_execution(tmp_path,steps):
    from nasolve.cif_generation import generate_elbow_candidate
    p=write(tmp_path/'source.cif',component());exe=program(tmp_path)
    with pytest.raises(ValueError):generate_elbow_candidate(p,'ZZZ',tmp_path/'out',exe,environment=os.environ,phenix_version='test-only',single_block_steps=steps)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('mode',['default','one','three','wrong_steps','changed_source','changed_copy','unselected_module','unsupported_macro'])
def test_actual_option_parsing_must_prove_one_block_and_preserve_installed_source(tmp_path,mode):
    from nasolve.cif_elbow_contract import audit_single_block_options,verify_single_block_options
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages';package=site/'elbow/utilities'
    package.mkdir(parents=True);(package/'__init__.py').write_text('');(package.parent/'__init__.py').write_text('')
    macro={'one':'1','three':'3','unsupported_macro':'None'}.get(mode,'False')
    steps='179' if mode=='wrong_steps' else '180'
    module=package/'options_parser.py'
    module.write_text('from types import SimpleNamespace\nimport sys\ndef run():\n    assert "--opt_steps=180" in sys.argv\n    return SimpleNamespace(opt_steps='+steps+',opt_macro_steps='+macro+',opt_tol=False),[],""\n')
    python=root/'bin/phenix.python';python.parent.mkdir()
    python.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');python.chmod(0o755)
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    capabilities={'supported_option_definitions':{'--opt_steps':True},'selected_aliases':{
        'id':'--id','output':'--output','template':'--template','initial_geometry':'--initial_geometry',
        'add_hydrogens':'--add_hydrogens','source_state_preservation':'--pH','chiral':'--chiral','opt':'--opt'}}
    source=write(tmp_path/'source/component.cif',component('R17'));output=tmp_path/'audit'
    environment={**os.environ,'PYTHONPATH':str(site),'PYTHONDONTWRITEBYTECODE':'1'}
    if mode=='unselected_module':
        other=tmp_path/'other';p=other/'elbow/utilities';p.mkdir(parents=True)
        (p/'__init__.py').write_text('');(p.parent/'__init__.py').write_text('');(p/'options_parser.py').write_text(module.read_text());environment['PYTHONPATH']=str(other)
    if mode in {'three','wrong_steps','unselected_module','unsupported_macro'}:
        with pytest.raises(ValueError):audit_single_block_options(root,python,api,source,'R17',capabilities,output,environment=environment,steps=180)
    else:
        r=audit_single_block_options(root,python,api,source,'R17',capabilities,output,environment=environment,steps=180)
        assert r['effective_blocks']==1 and r['steps']==180 and r['optimization_execution']=='NOT_RUN'
        assert r['captured_code_execution']=='NOT_RUN' and r['tolerance'] is False
        if mode=='changed_source':module.write_text('CHANGED')
        if mode=='changed_copy':(output/'options_parser.py.txt').write_text('CHANGED')
        if mode in {'changed_source','changed_copy'}:
            with pytest.raises(ValueError):verify_single_block_options(root,r,output)
        else:assert verify_single_block_options(root,r,output)
