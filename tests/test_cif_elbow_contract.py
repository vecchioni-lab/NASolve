"""Reader metadata and installed input checks do not qualify generated chemistry."""
from hashlib import sha256
import json, os
from pathlib import Path
from types import SimpleNamespace
import pytest
from nasolve.ligand_profiles import _blocks
from tests.test_cif_generation import HELP, program, write
from tests.test_cif_numerical_recovery import source_values


@pytest.mark.parametrize('code',['R17','DP'])
@pytest.mark.parametrize('aliases',[None,['N-alt','C-alt','C2-alt','C3-alt']])
def test_graph_export_supplies_missing_reader_aliases_without_renaming_atoms(tmp_path,code,aliases):
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    values=source_values(code)
    if aliases is not None:values['_chem_comp_atom.alt_atom_id']=aliases
    source=write(tmp_path/'original.cif',values);before=source.read_bytes();output=tmp_path/'graph/source.cif'
    receipt=prepare_graph_generation_source(source,code,output)
    fields=_blocks(output)[0].values
    # This is the installed reader's independent object-attribute access, not
    # the Doctor's case-normalized lookup or an assertion on emitted text.
    atom=SimpleNamespace(**{k.split('.',1)[1]:v[0] for k,v in fields.items() if k.startswith('_chem_comp_atom.')})
    assert atom.alt_atom_id==(aliases[0] if aliases else 'NQ')
    assert fields['_chem_comp_atom.atom_id']==values['_chem_comp_atom.atom_id']
    assert receipt['atom_alias_metadata']['policy']=='MISSING_COLUMN_USES_EXACT_PRIMARY_ATOM_IDS'
    assert receipt['atom_alias_metadata']['synthesized'] is (aliases is None)
    assert receipt['chemical_comparison']['status']=='EXACT_DECLARATIONS' and source.read_bytes()==before


def installation(tmp_path):
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages'
    from nasolve.cif_elbow_contract import SOURCE_PATHS
    for name in SOURCE_PATHS:
        p=site/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('def get_elbow_molecule_from_chemical_components(item):\n    return item.alt_atom_id, item.pdbx_model_Cartn_x_ideal\n')
    return root,[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py','sha256':'0'*64}]


@pytest.mark.parametrize('defect',['none','escape','changed','copy_changed','oversize','missing','ambiguous_anchor'])
def test_source_capture_is_anchored_bounded_and_checks_both_copies(tmp_path,defect):
    from nasolve.cif_elbow_contract import capture_elbow_sources,verify_elbow_source_capture,SOURCE_PATHS
    root,api=installation(tmp_path);target=root/'lib/python3.11/site-packages'/SOURCE_PATHS[0]
    if defect=='escape':
        other=tmp_path/'outside.py';other.write_text('OUTSIDE');target.unlink();target.symlink_to(other)
    if defect=='oversize':target.write_bytes(b'x'*(1024*1024+1))
    if defect=='missing':target.unlink()
    if defect=='ambiguous_anchor':api.append(dict(api[0]))
    output=tmp_path/'capture'
    if defect in {'escape','oversize','missing','ambiguous_anchor'}:
        with pytest.raises((ValueError,OSError)):capture_elbow_sources(root,api,output,phenix_version='test-only')
    else:
        report=capture_elbow_sources(root,api,output,phenix_version='test-only')
        assert report['status']=='CAPTURED_NOT_QUALIFIED' and len(report['sources'])==4
        assert report['reader_item_attribute_accesses']==['alt_atom_id','pdbx_model_Cartn_x_ideal']
        assert report['installed_phenix_edits']=='NOT_RUN'
        if defect=='changed':target.write_text('CHANGED')
        if defect=='copy_changed':(output/SOURCE_PATHS[0]).write_text('CHANGED')
        if defect=='none':assert verify_elbow_source_capture(root,report,output) is True
        else:
            with pytest.raises(ValueError):verify_elbow_source_capture(root,report,output)


@pytest.mark.parametrize('mode',['pass','parser_error','no_flag','timeout','mutate_source','optimizer_ran'])
def test_native_read_only_check_never_requests_optimization_or_adopts_a_dictionary(tmp_path,mode):
    from nasolve.cif_elbow_contract import audit_elbow_input
    from nasolve.cif_numerical_recovery import prepare_graph_generation_source
    source=write(tmp_path/'original.cif',source_values('R17'));graph=tmp_path/'graph/source.cif'
    prepare_graph_generation_source(source,'R17',graph);before=graph.read_bytes()
    body="""import json,time
from pathlib import Path
args=__import__('sys').argv[1:]
assert '--read_only' in args and '--opt' not in args and not any(x.startswith('--opt_steps') for x in args)
assert '--pH=low' in args and '--add-hydrogens=False' in args and '--chiral=retain' in args
Path('argv.json').write_text(json.dumps(args))
"""
    body+= {'pass':"print('Input format is CHEMICAL COMPONENTS')\n",'parser_error':"raise AttributeError('missing reader field')\n",'no_flag':"raise RuntimeError('MUST NOT RUN')\n",'timeout':"time.sleep(10)\n",'mutate_source':"Path('source.cif').write_text('CHANGED')\n",'optimizer_ran':"print('** Optimisation Manager **')\n"}[mode]
    help_text=HELP+('  --read_only          read the input without processing\n' if mode!='no_flag' else '')
    exe=program(tmp_path,body,help_text=help_text)
    r=audit_elbow_input(graph,'R17',tmp_path/'out',exe,environment=os.environ,phenix_version='test-only',timeout_seconds=.3 if mode=='timeout' else 5)
    assert r['status']==('PARSER_READ_ONLY_PASS' if mode=='pass' else 'REVIEW')
    assert r['dictionary_generation']==r['model_optimization']=='NOT_RUN' and r['automatic_adoption'] is False
    assert graph.read_bytes()==before
    if mode=='no_flag':assert r['execution']['status']=='UNSUPPORTED_READ_ONLY_OPTION' and r['command'] is None
    if mode=='timeout':assert r['execution']['status']=='TIMED_OUT'
    if mode=='mutate_source':assert r['source_preserved'] and not r['frozen_source_preserved']
    if mode=='optimizer_ran':assert r['unexpected_processing_detected']
    assert all(row['anchor']=='contract_directory' for row in r['outputs'])
