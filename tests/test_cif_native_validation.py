"""Native diagnostic transport and API contracts using explicit fake modules.

These tests execute the standalone worker, but they do not validate Phenix.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

import pytest

from nasolve.cif_native_validation import inspect_native_bundle


_FAKE_NATIVE = r'''
import json, os, re
from pathlib import Path
from types import SimpleNamespace as NS

class Definition:
    is_scope = False
    def __init__(self, name, value):
        self.name, self.words = name, [NS(value=value)]
    def as_str(self):
        return self.name + " = " + json.dumps(self.words[0].value) + "\n"

class Scope:
    is_scope = True
    def __init__(self, name="", objects=()):
        self.name, self.objects = name, list(objects)
    def as_str(self):
        inside = "".join(obj.as_str() for obj in self.objects)
        return self.name + " {\n" + inside + "}\n" if self.name else inside
    def all_definitions(self):
        rows = []
        def walk(scope, prefix=""):
            for obj in scope.objects:
                path = prefix + obj.name
                if obj.is_scope: walk(obj, path + ".")
                else: rows.append(NS(path=path, object=obj))
        walk(self)
        return rows
    def extract(self):
        requests=[NS(data_mod=row.object.words[0].value) for row in self.all_definitions()
                  if row.path=="pdb_interpretation.apply_cif_modification.data_mod"]
        return NS(pdb_interpretation=NS(marker="explicit interpretation parameters",apply_cif_modification=requests),
                  geometry_restraints=NS(edits=NS(marker="explicit edits"), remove=NS(marker="explicit removals")))

def parse(file_name=None, input_string=None, source_info=None):
    text = Path(file_name).read_text() if file_name else input_string
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|[{}=]|[^\s{}=]+', text)
    cursor = 0
    def scope(name=""):
        nonlocal cursor
        objects=[]
        while cursor < len(tokens) and tokens[cursor] != "}":
            key=tokens[cursor]; cursor+=1
            op=tokens[cursor]; cursor+=1
            if op == "{":
                child=scope(key); cursor+=1; objects.append(child)
            else:
                value=tokens[cursor]; cursor+=1
                if value.startswith('"'): value=json.loads(value)
                objects.append(Definition(key,value))
        return Scope(name,objects)
    return scope()

class Master:
    def fetch(self, sources, track_unused_definitions):
        assert track_unused_definitions is True
        objects=[]
        for source in sources: objects.extend(source.objects)
        work=Scope(objects=objects)
        unused=[row for row in work.all_definitions() if not row.path.startswith(("pdb_interpretation.", "geometry_restraints.edits.", "geometry_restraints.remove."))]
        return work, unused
def get_master_phil(): return Master()

def monomer(code):
    return NS(chem_comp=NS(id=code,group="DNA"), atom_list=[NS(atom_id=name) for name in ("C5", "C5'", "O4'")])
class server:
    def __init__(self): self.comp_comp_id_dict={}; self.mod_mod_id_dict={}
    def process_cif_object(self, cif_object, file_name, process_tor):
        assert process_tor is True
        self.comp_comp_id_dict["ZZZ"]=monomer("ZZZ")
        if "modification" in cif_object: self.mod_mod_id_dict["USER_MOD"]=object()
        # Match the reviewed native reader: the mod_ data block suffix is the
        # registry key; atom-loop mod_id values do not override it.
        for identifier in re.findall(r'^data_mod_(\S+)',cif_object,re.M):
            self.mod_mod_id_dict[identifier]=object()
class ener_lib:
    def process_cif_object(self, cif_object, file_name, process_tor): assert process_tor is False
def any_file(file_name): return NS(file_name=file_name,file_object=NS(model=lambda:Path(file_name).read_text()))

class Atom:
    def __init__(self, i, name):
        self.i_seq,self.name,self.element,self.occ=i,name,"C",1.
        self.xyz=(float(i+1),2.,3.)
    def fetch_labels(self):
        return NS(model_id="1",chain_id="A",resseq="1",icode="",resname="ZZZ",altloc="")
    def id_str(self): return "A:1:ZZZ:"+self.name

class BondCollection:
    def __init__(self):
        self.simple=[NS(i_seqs=(0,1),distance_ideal=1.5,weight=2500.,origin_id=0,rt_mx_ji=None)]
        self.asu=[NS(i_seq=1,j_seq=2,j_sym=2,distance_ideal=1.4,weight=1000.,origin_id=0)]
    def asu_mappings(self): return NS(get_rt_mx_ji=lambda pair:"x+1,y,z")
class Geometry:
    def __init__(self):
        self.angle_proxies=[1,2]; self.dihedral_proxies=[1]; self.const_dihedral_proxies=[]
        self.chirality_proxies=[1]; self.planarity_proxies=[1]; self.parallelity_proxies=None
        if os.environ.get("NATIVE_MODE")=="unsupported-count": del self.planarity_proxies
    def pair_proxies(self, sites_cart): return NS(bond_proxies=BondCollection())
class ChainProxies:
    def __init__(self):
        self.pdb_atoms=[Atom(i,name) for i,name in enumerate(("C5", "C5'", "O4'"))]
        mm=NS(pdb_residue_id_str="A:1",chainid="A",residue_name="ZZZ",monomer=monomer("ZZZ"),
              pdb_residue=NS(atoms=lambda:self.pdb_atoms),
              chem_mod_ids=["USER_MOD"],missing_non_hydrogen_atoms={"OP3":object()},
              missing_hydrogen_atoms={"H1":object()},unexpected_atoms={})
        if os.environ.get("NATIVE_MODE")=="decorated-monomer": mm.residue_name="ZZZ%USER_MOD"
        self.all_monomer_mappings=[mm]
    def fatal_problems_message(self): return "unknown native energy type" if os.environ.get("NATIVE_MODE")=="fatal" else None
    def sites_cart_exact(self): return [atom.xyz for atom in self.pdb_atoms]
class Processed:
    def __init__(self): self.all_chain_proxies=ChainProxies()
    def geometry_restraints_manager(self, params_edits, params_remove):
        assert params_edits.marker=="explicit edits" and params_remove.marker=="explicit removals"
        return Geometry()
def process(**kwargs):
    assert kwargs["keep_monomer_mappings"] and kwargs["strict_conflict_handling"]
    assert kwargs["params"].marker=="explicit interpretation parameters"
    for request in kwargs["params"].apply_cif_modification:
        if request.data_mod not in kwargs["mon_lib_srv"].mod_mod_id_dict:
            raise RuntimeError("Missing CIF modification: data_mod_"+request.data_mod)
    Path("native_calls.json").write_text(json.dumps({"model":kwargs["file_name"], "keep_monomer_mappings":kwargs["keep_monomer_mappings"]}))
    return Processed()
'''


def native_runtime(tmp_path):
    root = tmp_path / "fake_native"
    for package in ("iotbx", "mmtbx", "mmtbx/command_line", "mmtbx/monomer_library"):
        path=root/package
        path.mkdir(parents=True,exist_ok=True)
        (path/"__init__.py").write_text("")
    (root/"fake_native.py").write_text(_FAKE_NATIVE)
    for relative,names in {
        "iotbx/phil.py":"parse",
        "iotbx/file_reader.py":"any_file",
        "mmtbx/command_line/pdb_interpretation.py":"get_master_phil",
        "mmtbx/monomer_library/server.py":"server, ener_lib",
        "mmtbx/monomer_library/pdb_interpretation.py":"process",
    }.items(): (root/relative).write_text("from fake_native import "+names+"\n")
    executable=tmp_path/"bin/phenix.python"
    executable.parent.mkdir(exist_ok=True)
    executable.write_text("#!"+sys.executable+"\nimport runpy,sys\nsys.argv=sys.argv[1:]\nrunpy.run_path(sys.argv[0],run_name='__main__')\n")
    executable.chmod(0o755)
    return executable,{**os.environ,"PYTHONPATH":str(root)}


def files(tmp_path):
    root=tmp_path/"source"
    root.mkdir()
    model=root/"model.pdb"
    model.write_text("HETATM    1   C5 ZZZ A   1       1.000   2.000   3.000  1.00  0.00           C\nEND\n")
    dictionary=root/"component.cif"
    dictionary.write_text("data_ZZZ\n")
    modification=root/"modification.cif"
    modification.write_text("data_USER_MOD\n# modification\n")
    return model,[dictionary,modification]


def call(tmp_path,*,env_extra=None,phil_files=(),phil_namespace_policy="direct",**kwargs):
    model,dictionaries=files(tmp_path)
    executable,environment=native_runtime(tmp_path)
    environment.update(env_extra or {})
    receipt=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,
        environment=environment,phenix_version="2.2.1-fake-test",phil_files=phil_files,
        phil_namespace_policy=phil_namespace_policy,**kwargs)
    return receipt,model,dictionaries


def test_standalone_native_worker_records_exact_indices_asu_and_effective_monomers(tmp_path):
    receipt,model,dictionaries=call(tmp_path)
    assert receipt["status"]=="REVIEW"
    assert receipt["source_preserved"] and receipt["frozen_inputs_preserved"]
    native=receipt["native_validation"]
    assert native["status"]=="REVIEW"
    assert [atom["atom_id"] for atom in native["atoms"]]==["C5","C5'","O4'"]
    assert [atom["i_seq"] for atom in native["atoms"]]==[0,1,2]
    assert native["geometry"]["simple_bonds"][0]["i_seqs"]==[0,1]
    asu=native["geometry"]["asu_bonds"][0]
    assert asu["i_seqs"]==[1,2] and asu["j_sym"]==2
    assert asu["symmetry_operation"]=={"status":"RECORDED","operator":"x+1,y,z"}
    assert native["geometry"]["proxy_counts"]=={
        "bond_simple":1,"bond_asu":1,"angle":2,"dihedral":1,"const_dihedral":0,
        "chirality":1,"planarity":1,"parallelity":0}
    mapping=native["monomer_mappings"]["rows"][0]
    assert mapping["metadata"]["group"]=="DNA"
    assert mapping["missing_non_hydrogen_atoms"]["atom_ids"]==["OP3"]
    assert mapping["chem_mod_ids"]["ids"]==["USER_MOD"]
    assert native["dictionary_loading"][1]["modification_ids"]==["USER_MOD"]
    assert receipt["automatic_adoption"] is False
    assert receipt["scientific_approval"]=="NOT_RUN"
    work=Path(receipt["native_directory"])
    assert not list(work.glob("*.pdb"))
    assert json.loads((work/"native_receipt.json").read_text())==receipt
    for artifact in receipt["outputs"]:
        assert artifact["anchor"]=="native_directory"
        assert hashlib.sha256((work/artifact["path"]).read_bytes()).hexdigest()==artifact["sha256"]


@pytest.mark.parametrize('layout',['looped','legacy-scalars'])
def test_native_reader_contract_requires_a_component_list_loop(tmp_path,layout):
    """Explicit fake API control for convert_list_block's loop-only metadata."""
    import runpy
    from nasolve.cif_linked_preparation import prepare_linked_component
    from nasolve.ligand_profiles import _blocks,_emit
    fixture=runpy.run_path(str(Path(__file__).with_name('test_cif_linked_preparation.py')))['fixture']
    case=tmp_path/'case';case.mkdir()
    source,numerical,model,contexts=fixture(case)
    prepare_linked_component(source,numerical,model,contexts,case/'out',code='ZZZ')
    dictionary=case/'out/base_dictionary.cif'
    if layout=='legacy-scalars':
        metadata,definition=_blocks(dictionary)
        dictionary.write_text(_emit(metadata.values)+'\n'+definition.text)
    executable,environment=native_runtime(tmp_path)
    fake=tmp_path/'fake_native/fake_native.py'
    text=fake.read_text().replace('group="DNA"','group=LOADED_GROUP')
    text='LOADED_GROUP=None\n'+text
    text=text.replace('        self.comp_comp_id_dict["ZZZ"]=monomer("ZZZ")',r'''
        global LOADED_GROUP
        from Bio.PDB.MMCIF2Dict import MMCIF2Dict
        import io
        metadata=cif_object.split('data_comp_ZZZ')[0]
        if '\nloop_\n_chem_comp.' in metadata:
            LOADED_GROUP=MMCIF2Dict(io.StringIO(metadata))['_chem_comp.group'][0]
        self.comp_comp_id_dict["ZZZ"]=monomer("ZZZ")''')
    fake.write_text(text)
    result=inspect_native_bundle(model,[dictionary],tmp_path/'outputs',executable,
        environment=environment,phenix_version='fake-component-list-contract')
    assert result['status']=='REVIEW'
    native=result['native_validation']
    expected='DNA' if layout=='looped' else None
    assert native['dictionary_loading'][0]['component_metadata'][0]['group']==expected
    assert native['monomer_mappings']['rows'][0]['metadata']['group']==expected


@pytest.mark.parametrize('layout',['per-id','legacy-shared'])
def test_prepared_site_modifiers_resolve_through_native_reader_contract(tmp_path,layout):
    import runpy
    from nasolve.cif_linked_preparation import prepare_linked_component
    fixture=runpy.run_path(str(Path(__file__).with_name('test_cif_linked_preparation.py')))['fixture']
    case=tmp_path/'prepared';case.mkdir()
    source,numerical,prepared_model,contexts=fixture(case)
    prep=prepare_linked_component(source,numerical,prepared_model,contexts,case/'out',code='ZZZ')
    expected=sorted(site['modification_id'] for site in prep['sites'] if site['modification_id'])
    model,dictionaries=files(tmp_path)
    modifications=case/'out/site_modifications.cif';dictionaries.append(modifications)
    if layout=='legacy-shared':
        # Reproduce the returned failure without changing PHIL requests.
        from nasolve.ligand_profiles import _blocks,_emit
        blocks=_blocks(modifications);combined={'data_':'mod_linked_sites'}
        for block in blocks:
            for key,column in block.values.items():
                if key!='data_':combined.setdefault(key,[]).extend(column)
        modifications.write_text(_emit(combined))
    parameters=tmp_path/'source/requests.phil'
    parameters.write_text(''.join('refinement {\n pdb_interpretation {\n apply_cif_modification {\n'
                                ' data_mod = '+identifier+'\n residue_selection = "fixture"\n}\n}\n}\n'
                                for identifier in expected))
    executable,environment=native_runtime(tmp_path)
    result=inspect_native_bundle(model,dictionaries,tmp_path/'native',executable,
        environment=environment,phenix_version='fake-registration-only',phil_files=[parameters],
        phil_namespace_policy='refinement-root-to-interpreter-v1')
    assert result['status']==('REVIEW' if layout=='per-id' else 'FAILED')
    assert result['native_validation']['dictionary_loading'][-1]['modification_ids']==(expected if layout=='per-id' else ['linked_sites'])
    if layout=='legacy-shared':assert 'Missing CIF modification: data_mod_' in result['error']
    assert result['source_preserved'] and result['frozen_inputs_preserved']
    assert result['scientific_approval']=='NOT_RUN'


@pytest.mark.parametrize('charge_readback',['supported','missing-attribute'])
def test_opt_in_details_record_effective_types_and_explicit_proxy_targets(tmp_path,charge_readback):
    model,dictionaries=files(tmp_path)
    executable,environment=native_runtime(tmp_path)
    module=tmp_path/'fake_native/fake_native.py'
    text=module.read_text().replace('edits=NS(marker="explicit edits")',
        'edits=NS(marker="explicit edits", bond=[NS(atom_selection_1="first",atom_selection_2="second",distance_ideal=1.5,sigma=.02,action="add")])')
    text += r'''
def monomer(code):
    return NS(chem_comp=NS(id=code,group="DNA"),
        classification="DNA",
        atom_list=[NS(atom_id=n,type_symbol="C",type_energy="CH1",charge="0",partial_charge=.1) for n in ("C5","C5'","O4'")],
        bond_list=[NS(atom_id_1="C5",atom_id_2="C5'",type="single",value_dist=1.5,value_dist_esd=.02,value_dist_neutron=1.51)],
        angle_list=[],tor_list=[NS(id="reviewed",atom_id_1="C5",atom_id_2="C5'",atom_id_3="O4'",atom_id_4="C5",value_angle=340.7,alt_value_angle="2.8",value_angle_esd=6.3,period=1)],
        chir_list=[],plane_atom_list=[])
class Geometry:
    def __init__(self):
        self.angle_proxies=[NS(i_seqs=(0,1,2),angle_ideal=110.,weight=100.,origin_id=0)]
        self.dihedral_proxies=[];self.const_dihedral_proxies=[];self.chirality_proxies=[]
        self.planarity_proxies=[NS(i_seqs=(0,1,2),weights=[100.,100.,100.],origin_id=1)]
        self.parallelity_proxies=[]
    def pair_proxies(self,sites_cart):return NS(bond_proxies=BondCollection())
ChainProxies.selection=lambda self,expression:NS(iselection=lambda:[0 if expression=="first" else 1])
'''
    module.write_text(text.replace('charge="0",','') if charge_readback=='missing-attribute' else text)
    result=inspect_native_bundle(model,dictionaries,tmp_path/'outputs',executable,
        environment=environment,phenix_version='fake-detail',inventory_detail='linked')
    assert result['status']=='REVIEW'
    readback=result['native_validation']['monomer_mappings']['rows'][0]['metadata']['formal_charge_readback']
    assert readback['status']==('SUPPORTED' if charge_readback=='supported' else 'UNSUPPORTED')
    assert bool(readback['missing_attribute_atoms'])==(charge_readback=='missing-attribute')
    native=result['native_validation']
    assert native['inventory_detail']=='linked'
    assert native['monomer_mappings']['rows'][0]['metadata']['classification']=={'status':'RECORDED','value':'DNA'}
    assert native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'][0]['type_energy']=='CH1'
    assert native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['bonds'][0]['value_dist_neutron']==1.51
    assert native['monomer_mappings']['rows'][0]['metadata']['effective_definition']['torsions'][0]['alt_value_angle']=='2.8'
    assert native['geometry']['proxy_details']['angle'][0]['angle_ideal']==110.
    request=native['geometry']['custom_proxy_requests'][0]
    assert request['atoms']==[row['label'] for row in native['atoms'][:2]]
    assert request['distance_ideal']==1.5 and request['weight']==2500.
    assert result['automatic_adoption'] is False


def test_direct_phil_namespace_rejects_unconsumed_refinement_wrapper(tmp_path):
    phil=tmp_path/"parameters/user.phil"; phil.parent.mkdir()
    phil.write_text('refinement { geometry_restraints { edits { atom_selection = "chain A and name C5\'" } } }\n')
    receipt,_,_=call(tmp_path,phil_files=[phil])
    assert receipt["status"]=="UNSUPPORTED"
    assert receipt["native_validation"]["unused_definitions"]
    assert not (Path(receipt["native_directory"])/"native_calls.json").exists()


def test_native_parsed_namespace_adapter_preserves_every_definition_and_selection(tmp_path):
    phil=tmp_path/"parameters/user.phil"; phil.parent.mkdir()
    phil.write_text('refinement { geometry_restraints { edits { atom_selection = "chain A and name C5\'" } } }\npdb_interpretation { marker = True }\n')
    before=phil.read_bytes()
    receipt,_,_=call(tmp_path,phil_files=[phil],phil_namespace_policy="refinement-root-to-interpreter-v1")
    assert receipt["status"]=="REVIEW"
    adaptation=receipt["native_validation"]["phil_adaptations"][0]
    assert adaptation["definitions_preserved"]==2
    assert adaptation["field_mapping"][0]=={
        "source":"refinement.geometry_restraints.edits.atom_selection",
        "interpreter":"geometry_restraints.edits.atom_selection",
        "value_tokens":["chain A and name C5'"]}
    assert phil.read_bytes()==before
    work=Path(receipt["native_directory"])
    assert (work/"canonical_000.phil").is_file()
    assert (work/"native_effective.phil").is_file()


def test_unknown_phil_field_stays_unsupported_after_namespace_adaptation(tmp_path):
    phil=tmp_path/"parameters/user.phil"; phil.parent.mkdir()
    phil.write_text("refinement { imaginary_chemistry = True }\n")
    receipt,_,_=call(tmp_path,phil_files=[phil],phil_namespace_policy="refinement-root-to-interpreter-v1")
    assert receipt["status"]=="UNSUPPORTED"
    assert receipt["native_validation"]["unused_definitions"][0]["path"]=="imaginary_chemistry"
    assert receipt["automatic_adoption"] is False


def test_missing_optional_proxy_api_is_visible_not_fabricated_zero(tmp_path):
    receipt,_,_=call(tmp_path,env_extra={"NATIVE_MODE":"unsupported-count"})
    assert receipt["status"]=="REVIEW"
    geometry=receipt["native_validation"]["geometry"]
    assert geometry["proxy_counts"]["planarity"] is None
    assert geometry["proxy_count_status"]["planarity"]=="UNSUPPORTED"
    assert "planarity_proxies" in receipt["native_validation"]["unsupported_fields"]


def test_modified_monomer_name_is_separate_from_literal_model_identity(tmp_path):
    receipt,model,_=call(tmp_path,env_extra={"NATIVE_MODE":"decorated-monomer"})
    assert receipt["status"]=="REVIEW"
    mapping=receipt["native_validation"]["monomer_mappings"]["rows"][0]
    assert mapping["interpreted_residue_name"]=="ZZZ%USER_MOD"
    assert mapping["resname"]=="ZZZ"
    assert mapping["literal_identity"]["resname"]=="ZZZ"
    assert mapping["literal_identity"]["status"]=="RECORDED"
    assert mapping["site"]=="A:1"
    assert receipt["native_validation"]["atoms"][0]["identity"]["resname"]=="ZZZ"
    assert receipt["source_preserved"] and receipt["frozen_inputs_preserved"]
    assert "ZZZ%USER_MOD" not in model.read_text()


def test_native_fatal_energy_message_blocks_geometry_inventory(tmp_path):
    receipt,_,_=call(tmp_path,env_extra={"NATIVE_MODE":"fatal"})
    assert receipt["status"]=="FAILED"
    assert receipt["native_validation"]["fatal_problems"]=="unknown native energy type"
    assert receipt["native_validation"]["geometry"]["status"]=="NOT_RUN"


def test_missing_native_installation_is_reported_without_importing_nasolve(tmp_path):
    model,dictionaries=files(tmp_path)
    executable,environment=native_runtime(tmp_path)
    environment["PYTHONPATH"]=str(tmp_path/"empty")
    receipt=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,
        environment=environment,phenix_version="fake-missing-runtime")
    assert receipt["status"]=="UNSUPPORTED"
    assert receipt["native_validation"]["status"]=="UNSUPPORTED"
    assert receipt["source_preserved"]


def test_fresh_native_directories_do_not_overwrite_previous_receipts(tmp_path):
    model,dictionaries=files(tmp_path)
    executable,environment=native_runtime(tmp_path)
    kwargs=dict(environment=environment,phenix_version="fake")
    first=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,**kwargs)
    preserved={path.relative_to(Path(first["native_directory"])).as_posix():path.read_bytes()
               for path in Path(first["native_directory"]).rglob("*") if path.is_file()}
    second=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,**kwargs)
    assert first["native_directory"]!=second["native_directory"]
    assert preserved=={path.relative_to(Path(first["native_directory"])).as_posix():path.read_bytes()
               for path in Path(first["native_directory"]).rglob("*") if path.is_file()}


def test_relocated_native_inputs_work_after_originals_disappear(tmp_path):
    original=tmp_path/"original"; original.mkdir()
    model,dictionaries=files(original)
    executable,environment=native_runtime(original)
    relocated=tmp_path/"relocated"
    shutil.copytree(original,relocated); shutil.rmtree(original)
    receipt=inspect_native_bundle(relocated/"source/model.pdb",
        [relocated/"source/component.cif",relocated/"source/modification.cif"],tmp_path/"outputs",
        relocated/"bin/phenix.python",environment={**environment,"PYTHONPATH":str(relocated/"fake_native")},phenix_version="fake")
    assert receipt["status"]=="REVIEW" and not original.exists()


@pytest.mark.skipif(os.name!="posix",reason="Owned process group timeout is POSIX")
def test_native_timeout_kills_descendants_and_preserves_inputs(tmp_path):
    model,dictionaries=files(tmp_path)
    executable=tmp_path/"phenix.python"
    executable.write_text("#!"+sys.executable+"\n"+"""
import os, subprocess, sys, time
subprocess.Popen([sys.executable,'-c','import os,time; from pathlib import Path; time.sleep(.4); Path(os.environ["SENTINEL"]).write_text("survived")'])
print('native diagnostic started',flush=True)
time.sleep(5)
""")
    executable.chmod(0o755)
    sentinel=tmp_path/"descendant"
    receipt=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,
        environment={**os.environ,"SENTINEL":str(sentinel)},phenix_version="fake",timeout_seconds=.15)
    assert receipt["status"]=="FAILED" and receipt["execution"]["status"]=="TIMED_OUT"
    time.sleep(.4); assert not sentinel.exists()
    assert receipt["source_preserved"] and receipt["frozen_inputs_preserved"]


def test_source_input_race_invalidates_native_receipt(tmp_path):
    model,dictionaries=files(tmp_path)
    executable=tmp_path/"phenix.python"
    executable.write_text("#!"+sys.executable+"\n"+"""
import json,os
from pathlib import Path
Path(os.environ['MUTATE']).write_text('external input mutation')
Path('native_validation.json').write_text(json.dumps({'status':'REVIEW'}))
""")
    executable.chmod(0o755)
    receipt=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,
        environment={**os.environ,"MUTATE":str(model)},phenix_version="fake")
    assert receipt["status"]=="FAILED" and receipt["source_preserved"] is False
    assert receipt["frozen_inputs_preserved"] is True


def test_incomplete_native_json_cannot_claim_a_recorded_manager(tmp_path):
    model,dictionaries=files(tmp_path)
    executable=tmp_path/"phenix.python"
    executable.write_text("#!"+sys.executable+"\n"+"""
import json
from pathlib import Path
Path('native_validation.json').write_text(json.dumps({'status':'REVIEW'}))
""")
    executable.chmod(0o755)
    receipt=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,
        environment=os.environ,phenix_version="fake")
    assert receipt["status"]=="FAILED"
    assert "unsupported diagnostic receipt schema" in receipt["error"]
    assert receipt["source_preserved"] and receipt["frozen_inputs_preserved"]


def test_frozen_input_removal_is_recorded_without_losing_failure_receipt(tmp_path):
    model,dictionaries=files(tmp_path)
    executable=tmp_path/"phenix.python"
    executable.write_text("#!"+sys.executable+"\n"+"""
from pathlib import Path
Path('inputs/000_model.pdb').unlink()
print('native backend removed a frozen input')
""")
    executable.chmod(0o755)
    receipt=inspect_native_bundle(model,dictionaries,tmp_path/"outputs",executable,
        environment=os.environ,phenix_version="fake")
    assert receipt["status"]=="FAILED"
    assert receipt["source_preserved"] is True
    assert receipt["frozen_inputs_preserved"] is False
    assert (Path(receipt["native_directory"])/"native_receipt.json").exists()


@pytest.mark.parametrize("policy",["guess","refinement"])
def test_unknown_namespace_policy_rejected_before_output_allocation(tmp_path,policy):
    model,dictionaries=files(tmp_path)
    with pytest.raises(ValueError,match="namespace"):
        inspect_native_bundle(model,dictionaries,tmp_path/"outputs",Path(sys.executable),
            environment=os.environ,phenix_version="fake",phil_namespace_policy=policy)
    assert not (tmp_path/"outputs").exists()
