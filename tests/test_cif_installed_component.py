"""Fake native lookups exercise source ownership, substitution and integrity."""
from pathlib import Path
import os,sys
import pytest
from nasolve.cif_installed_component import capture_installed_component,verify_component_capture


@pytest.mark.parametrize('mode',['pass','missing','alias','no_source','outside','escaped_module','changed_api','changed_resource','timeout'])
def test_installed_lookup_captures_exact_selected_resource_without_generator(tmp_path,mode):
    root=tmp_path/'phenix';site=root/'lib/python3.11/site-packages'
    for name in ['mmtbx','mmtbx/monomer_library']:
        p=site/name;p.mkdir(parents=True);(p/'__init__.py').write_text('')
    resource=root/'monomers/q/Q17.cif';resource.parent.mkdir(parents=True);resource.write_text('data_Q17\n# EXPLICIT FAKE RESOURCE\n')
    if mode=='outside':resource=tmp_path/'outside.cif';resource.write_text('data_Q17\n')
    body='''from types import SimpleNamespace as NS
from pathlib import Path
class Row:
    def __init__(self,**kwargs):self.__dict__.update(kwargs)
    def cif_keywords(self):return list(vars(self))
class server:
    def get_comp_comp_id_and_atom_name_interpretation(self,residue_name,atom_names):
        assert residue_name=='Q17' and atom_names==[]
        if MODE=='timeout':
            import time;time.sleep(30)
        if MODE=='missing':return None,None
        if MODE=='changed_api':Path(__file__).write_text('# CHANGED')
        if MODE=='changed_resource':Path('installed_component.cif').write_text('CHANGED SNAPSHOT')
        comp=NS(chem_comp=Row(id='OTHER' if MODE=='alias' else 'Q17'),source_info='none' if MODE=='no_source' else 'file: '+RESOURCE)
        for field in ['atom_list','bond_list','angle_list','tor_list','chir_list','plane_atom_list']:setattr(comp,field,[])
        return comp,None
'''.replace('MODE',repr(mode)).replace('RESOURCE',repr(str(resource)))
    module=site/'mmtbx/monomer_library/server.py';module.write_text(body)
    (site/'mmtbx/monomer_library/cif_types.py').write_text('# FAKE API\n')
    if mode=='escaped_module':
        outside=tmp_path/'outside.py';outside.write_text(body);module.unlink();module.symlink_to(outside)
    exe=root/'bin/phenix.python';exe.parent.mkdir();exe.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');exe.chmod(0o755)
    api=[{'anchor':'phenix_installation','path':'lib/python3.11/site-packages/iotbx/phil.py'}]
    output=tmp_path/'capture'
    if mode in ['escaped_module','changed_api','timeout']:
        with pytest.raises(ValueError):capture_installed_component(root,exe,api,'Q17',output,environment=os.environ,
            timeout_seconds=.1 if mode=='timeout' else 30)
    else:
        r=capture_installed_component(root,exe,api,'Q17',output,environment=os.environ)
        assert r['result']['status']==('RECORDED' if mode=='pass' else 'FAILED' if mode=='changed_resource' else 'UNSUPPORTED')
        assert r['result']['dictionary_generation']=='NOT_RUN' and r['installed_sources_preserved']
        assert verify_component_capture(root,r,output)
        if mode=='pass':
            assert (output/'installed_component.cif').read_bytes()==resource.read_bytes()
            resource.write_text('CHANGED')
            with pytest.raises(ValueError):verify_component_capture(root,r,output)
