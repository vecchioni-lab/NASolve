"""ReadySet source capture and descriptor selection never imply generation."""
from pathlib import Path
from hashlib import sha256
import json,os,sys
import pytest

ROOT=Path(__file__).resolve().parents[1]


def fake_install(tmp_path,mode='pass',code='PDU'):
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages'
    for name in ['mmtbx','mmtbx/chemical_components','elbow','elbow/command_line','elbow/scripts']:
        p=site/name;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_text('')
    entry=site/'elbow/command_line/ready_set.py'
    entry.write_text('from elbow.scripts import ready_set\nraise RuntimeError("READYSET MUST NOT EXECUTE")\n')
    (site/'elbow/scripts/ready_set.py').write_text('import elbow.scripts.helper\nraise RuntimeError("READYSET HELPER MUST NOT EXECUTE")\n')
    (site/'elbow/scripts/helper.py').write_text('raise RuntimeError("STATIC HELPER MUST NOT EXECUTE")\n')
    ccd=site/'chem_data/chemical_components'/code[0].lower()/('data_'+code+'.cif');ccd.parent.mkdir(parents=True)
    ccd.write_bytes((ROOT/'tests/fixtures/public_ccd/PDU.cif').read_bytes().replace(b'PDU',code.encode()))
    source=site/'mmtbx/chemical_components/__init__.py'
    smiles='CC#CC';selected='CCCC' if mode=='different_selection' else smiles
    source.write_text('''from pathlib import Path
loaded_cifs={}
def get_cif_filename(code):return CCD
def get_smiles(code):
    if MODE=='timeout':
        import time;time.sleep(30)
    if MODE=='changed_api':Path(__file__).write_text('# CHANGED')
    return SELECTED
'''.replace('CCD',repr(str(ccd))).replace('MODE',repr(mode)).replace('SELECTED',repr(selected)))
    if mode=='outside_ccd':source.write_text(source.read_text().replace(str(ccd),str(tmp_path/'outside.cif')));(tmp_path/'outside.cif').write_text('OUTSIDE')
    if mode=='missing_api':source.write_text('loaded_cifs={}\n')
    exe=root/'bin/phenix.python';exe.parent.mkdir();exe.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');exe.chmod(0o755)
    ready=exe.with_name('phenix.ready_set');ready.write_text('exec "$LIBTBX_PYEXE" "$LIBTBX_PREFIX/lib/python3.11/site-packages/elbow/command_line/ready_set.py" "$@"\n')
    def record(p):return {'anchor':'phenix_installation','path':p.relative_to(root).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
    cat={'sources':[record(source)],'readyset_dispatcher':record(ready),'components':{code:{'status':'RECORDED','resource':record(ccd),
        'comparison':{'descriptors':[{'type':'SMILES_CANONICAL','program':'CACTVS','program_version':'TEST','descriptor':smiles}]}}}}
    return root,site,exe,ready,cat


@pytest.mark.parametrize('defect',['none','unknown','escape','ambiguous','symlink'])
def test_exact_dispatcher_target_and_static_imports_are_captured_without_execution(tmp_path,defect):
    from nasolve.cif_readyset_source_audit import capture_readyset_sources
    root,site,exe,ready,cat=fake_install(tmp_path)
    if defect=='unknown':ready.write_text('exec python -m unknown\n')
    if defect=='escape':ready.write_text('exec "$LIBTBX_PYEXE" "$LIBTBX_PREFIX/../outside.py"\n')
    if defect=='ambiguous':ready.write_text(ready.read_text()+'"$LIBTBX_PREFIX/lib/python3.11/site-packages/elbow/another.py"\n')
    if defect=='symlink':
        p=site/'elbow/scripts/helper.py';p.unlink();outside=tmp_path/'outside.py';outside.write_text('raise RuntimeError("OUTSIDE")');p.symlink_to(outside)
    cat['readyset_dispatcher'].update(sha256=sha256(ready.read_bytes()).hexdigest(),size=ready.stat().st_size)
    output=tmp_path/'capture'
    if defect!='none':
        with pytest.raises(ValueError):capture_readyset_sources(root,site.relative_to(root),cat['readyset_dispatcher'],output)
    else:
        r=capture_readyset_sources(root,site.relative_to(root),cat['readyset_dispatcher'],output)
        assert r['entrypoint']['path'].endswith('elbow/command_line/ready_set.py')
        names={s['path'] for s in r['sources']}
        assert any(n.endswith('elbow/scripts/ready_set.py') for n in names)
        assert any(n.endswith('elbow/scripts/helper.py') for n in names)
        assert r['readyset_execution']=='NOT_RUN' and r['static_analysis_is_execution_proof'] is False
        for row in r['sources']:assert sha256((output/row['snapshot']['path']).read_bytes()).hexdigest()==row['sha256']
        with pytest.raises(ValueError):capture_readyset_sources(root,site.relative_to(root),cat['readyset_dispatcher'],output)


def test_static_source_budget_records_incomplete_coverage(tmp_path):
    from nasolve.cif_readyset_source_audit import capture_readyset_sources
    root,site,exe,ready,cat=fake_install(tmp_path)
    r=capture_readyset_sources(root,site.relative_to(root),cat['readyset_dispatcher'],tmp_path/'capture',max_files=1)
    assert len(r['sources'])==1 and r['coverage_complete'] is False
    assert any(e['status']=='FILE_BUDGET' for e in r['imports'])


@pytest.mark.parametrize('mode',['pass','different_selection','outside_ccd','missing_api','changed_api','timeout'])
@pytest.mark.parametrize('code',['PDU','Q77'])
def test_selected_native_descriptor_is_anchored_and_not_a_graph_or_restraint_verdict(tmp_path,mode,code):
    from nasolve.cif_readyset_source_audit import audit_readyset_sources,verify_readyset_sources
    root,site,exe,ready,cat=fake_install(tmp_path,mode,code)
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    out=tmp_path/'audit'
    call=lambda:audit_readyset_sources(root,exe,api,cat,out,environment=os.environ,timeout_seconds=.1 if mode=='timeout' else 30)
    if mode in {'outside_ccd','missing_api','changed_api','timeout'}:
        with pytest.raises(ValueError):call()
    else:
        r=call();c=r['components'][code]
        assert c['status']==('SELECTED_DESCRIPTOR_MATCH' if mode=='pass' else 'REVIEW')
        assert c['selected_smiles']==('CC#CC' if mode=='pass' else 'CCCC')
        assert c['mapped_smiles_graph_comparison']=='NOT_RUN' and c['numerical_restraints']=='UNASSESSED'
        assert all(r[k]=='NOT_RUN' for k in ['readyset_execution','dictionary_generation','optimization'])
        assert verify_readyset_sources(root,r,out)
        (site/'elbow/command_line/ready_set.py').write_text('# CHANGED')
        with pytest.raises(ValueError):verify_readyset_sources(root,r,out)
