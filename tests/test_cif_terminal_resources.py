"""Installed resource inventory contracts use fake APIs, not native Phenix."""
import json
import os
from pathlib import Path
import sys

import pytest


def runtime(tmp_path):
    package=tmp_path/'fake/mmtbx/monomer_library';package.mkdir(parents=True)
    for directory in [package,package.parent]: (directory/'__init__.py').write_text('')
    (package/'cif_types.py').write_text('# Explicit fake row schema lives in server.py.\n')
    (package/'server.py').write_text('''from types import SimpleNamespace as NS
import os
class Row:
    def __init__(self,**values): self.__dict__.update(values)
    def cif_keywords(self): return list(self.__dict__)
class Component:
    def __init__(self,terminal=False):
        self.source_info=None
        self.chem_comp=Row(id='DG',group='DNA')
        self.atom_list=[Row(atom_id="O5'",type_symbol='O',type_energy='OH1' if terminal else 'O2')]
        if terminal:self.atom_list.append(Row(atom_id='HO5',type_symbol='H',type_energy='HOH1'))
        self.bond_list=[Row(atom_id_1="O5'",atom_id_2='HO5',value_dist=.96,value_dist_esd=.02)] if terminal else []
        self.angle_list=[];self.tor_list=[];self.chir_list=[];self.plane_atom_list=[]
    def get_classification(self):return 'undetermined' if len(self.atom_list)==2 else 'DNA'
class server:
    def __init__(self):
        if os.environ.get('RESOURCE_MODE')=='timeout':
            import time
            time.sleep(30)
        self.mod_mod_id_dict={'5*END':NS(source_info=None,chem_mod=Row(id='5*END'),
            atom_list=[Row(function='add',new_atom_id='HO5',new_type_symbol='H',new_type_energy='HOH1')],
            bond_list=[Row(function='add',atom_id_1="O5'",atom_id_2='HO5',new_value_dist=.96,new_value_dist_esd=.02)],
            angle_list=[],tor_list=[],chir_list=[],plane_atom_list=[])}
        if os.environ.get('RESOURCE_MODE')=='missing':self.mod_mod_id_dict={}
    def get_comp_comp_id_direct(self,comp_id):return Component()
    def get_comp_comp_id_mod(self,base,ids):return Component(True),list(ids)
''')
    exe=tmp_path/'phenix.python'
    exe.write_text('#!'+sys.executable+'\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name="__main__")\n');exe.chmod(0o755)
    return exe,{**os.environ,'PYTHONPATH':str(tmp_path/'fake')}


def test_inventory_keeps_native_targets_and_unknown_formal_charge(tmp_path):
    from nasolve.cif_terminal_resources import inspect_terminal_resources
    exe,env=runtime(tmp_path)
    r=inspect_terminal_resources(tmp_path/'out',exe,environment=env,phenix_version='fake-test')
    assert r['status']=='REVIEW' and r['execution']['returncode']==0
    native=r['native_resources']
    assert native['modifications']['5*END']['bonds'][0]['new_value_dist']==.96
    assert native['canonical_control']['base_preserved'] is True
    assert native['canonical_control']['effective']['formal_charge_readback']=='UNSUPPORTED'
    assert 'charge' not in native['canonical_control']['effective']['atoms'][0]
    assert r['model_editing']=='NOT_RUN' and r['automatic_adoption'] is False
    assert (Path(r['native_directory'])/'resources_receipt.json').is_file()


def test_missing_requested_native_resource_is_unsupported(tmp_path):
    from nasolve.cif_terminal_resources import inspect_terminal_resources
    exe,env=runtime(tmp_path);env['RESOURCE_MODE']='missing'
    r=inspect_terminal_resources(tmp_path/'out',exe,environment=env,phenix_version='fake-test')
    assert r['status']=='UNSUPPORTED'
    assert '5*END' in r['native_resources']['error']


def test_timeout_stops_owned_resource_worker(tmp_path):
    from nasolve.cif_terminal_resources import inspect_terminal_resources
    exe,env=runtime(tmp_path);env['RESOURCE_MODE']='timeout'
    r=inspect_terminal_resources(tmp_path/'out',exe,environment=env,phenix_version='fake-test',timeout_seconds=.1)
    assert r['status']=='FAILED' and r['execution']['status']=='TIMED_OUT'
    assert r['execution']['returncode'] is not None


@pytest.mark.parametrize('timeout',[0,-1,float('nan')])
def test_invalid_timeout_is_rejected_before_output(tmp_path,timeout):
    from nasolve.cif_terminal_resources import inspect_terminal_resources
    with pytest.raises(ValueError):
        inspect_terminal_resources(tmp_path/'out',tmp_path/'missing',environment={},phenix_version='fake',timeout_seconds=timeout)
    assert not (tmp_path/'out').exists()
