"""Fake installed readers test isolation; they do not qualify native chemistry."""
import json,os,sys
import pytest
from nasolve.cif_elbow_chirality import audit_installed_chirality,verify_chirality_sources,SOURCE_PATHS
from tests.test_cif_stereochemistry_audit import tetrahedron,write


@pytest.mark.parametrize('mode',['known','unknown','constructor_error','wrong_marker','changed_source','changed_snapshot','changed_input','wrong_module'])
def test_installed_reader_control_checks_scope_markers_and_immutable_inputs(tmp_path,mode):
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages';out=tmp_path/'controls'
    for package in ['elbow','elbow/utilities','elbow/chemistry']:
        p=site/package;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_text('')
    for name in SOURCE_PATHS:
        p=site/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# EXPLICIT_FAKE_INSTALLED_SOURCE\n')
    markers=['?']*5 if mode=='unknown' else ['S' if mode=='wrong_marker' else 'R',False,False,False,False]
    extra=""
    if mode=='changed_source':extra="\n    Path(__file__).write_text('# CHANGED')"
    if mode=='changed_snapshot':extra="\n    Path('elbow/chemistry/ChiralClass.py.txt').write_text('# CHANGED')"
    if mode=='changed_input':extra="\n    Path(filename).write_text('CHANGED')"
    body='''from types import SimpleNamespace
from pathlib import Path
class Molecule(list):
    bonds=[None]*4
def get_elbow_molecule_from_chemical_components(code,filename=None,chirals=False):
    if chirals and MODE in ['unknown','constructor_error']:raise AssertionError('fake constructor failure')
    result=Molecule(SimpleNamespace(name=n,chiral=m) for n,m in zip(['CTR','O','N','C','H'],MARKERS))
    EXTRA
    return result
'''.replace('MODE',repr(mode)).replace('MARKERS',repr(markers)).replace('    EXTRA',extra)
    (site/SOURCE_PATHS[0]).write_text(body)
    python=root/'bin/phenix.python';python.parent.mkdir(parents=True)
    preload='import elbow.utilities.Utilities\n' if mode=='wrong_module' else ''
    python.write_text('#!'+sys.executable+'\nimport runpy,sys\n'+preload+'sys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');python.chmod(0o755)
    v,_=tetrahedron()
    if mode=='unknown':v['_chem_comp_atom.pdbx_stereo_config']=['?']*5
    source=write(tmp_path/'input/source.cif',v)
    env={**os.environ,'PYTHONPATH':str(site),'PYTHONDONTWRITEBYTECODE':'1'}
    if mode=='wrong_module':
        other=tmp_path/'other';import shutil;shutil.copytree(site/'elbow',other/'elbow');env['PYTHONPATH']=str(other)
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    if mode.startswith('changed_') or mode=='wrong_module':
        with pytest.raises(ValueError):audit_installed_chirality(root,python,api,source,'Q17',out,environment=env)
    else:
        r=audit_installed_chirality(root,python,api,source,'Q17',out,environment=env)
        assert r['optimization_execution']=='NOT_RUN' and r['dictionary_generation']=='NOT_RUN'
        assert r['captured_code_execution']=='NOT_RUN' and r['pickle_loading']=='NOT_RUN'
        assert r['status']==('READER_MARKERS_PASS' if mode=='known' else 'REVIEW')
        if mode=='unknown':assert len(r['unknown_inputs_marked_chiral'])==5
        assert verify_chirality_sources(root,r,out)
        assert json.loads((out/'chirality_receipt.json').read_text())==r
        assert all(row['snapshot']['path'].endswith('.py.txt') for row in r['sources'])
        (out/(SOURCE_PATHS[-1]+'.txt')).write_text('CHANGED')
        with pytest.raises(ValueError):verify_chirality_sources(root,r,out)


@pytest.mark.parametrize('defect',['source_escape','output_inside','symlink_output','missing_anchor'])
def test_native_stereo_evidence_refuses_unsafe_source_or_output_locations(tmp_path,defect):
    root=tmp_path/'phenix';root.mkdir();python=root/'python';python.write_text('FAKE_NOT_EXECUTED')
    v,_=tetrahedron();src=write(tmp_path/'input/source.cif',v);out=tmp_path/'out'
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    if defect=='output_inside':out=root/'out'
    elif defect=='symlink_output':out.symlink_to(tmp_path/'uncreated')
    elif defect=='missing_anchor':api=[]
    else:
        target=tmp_path/'outside.py';target.write_text('raise RuntimeError("MUST NOT EXECUTE")')
        p=root/'lib/python3.11/site-packages'/SOURCE_PATHS[0];p.parent.mkdir(parents=True);p.symlink_to(target)
    with pytest.raises((ValueError,FileNotFoundError)):
        audit_installed_chirality(root,python,api,src,'Q17',out,environment=os.environ)
