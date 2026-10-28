"""Versioned source handoff: fake native programs test contracts, not Phenix."""
from copy import deepcopy
from hashlib import sha256
import json, os
from pathlib import Path
import pytest

from tests.test_cif_purine_representation import pair, POLICY, A, B
from tests.test_cif_stereochemistry_audit import write


def source_pair(tmp_path):
    v,g=pair()
    for d in (v,g):
        for i,axis in enumerate("xyz"):
            d[A+"pdbx_model_Cartn_"+axis+"_ideal"]=[str((n+1)*(i+1)/10) for n in range(len(d[A+"atom_id"]))]
    return write(tmp_path/"source.cif",v),write(tmp_path/"candidate-fixture.cif",g)


def expected(source):
    from nasolve.cif_stereochemistry_audit import _values,_graph,_coordinates
    v=_values(source,"Q17");elements,bonds,charges,_=_graph(v);_,xyz=_coordinates(v,source=True)
    return {"component":"Q17","dialect":"CHEMICAL_COMPONENTS_CIF","elements":elements,"charges":{n:int(q) for n,q in charges.items()},
        "coordinates":xyz,"bonds":[{"atoms":list(p),"order":{"SINGLE":1,"DOUBLE":2}[o]} for p,o in bonds.items()]}


def snapshot(e):
    return {"atoms":[{"atom":n,"element":element,"native_atom_charge":e["charges"][n],"native_chiral_marker":None,"native_volume_sign":None,"xyz":e["coordinates"][n]} for n,element in e["elements"].items()],
        "bonds":[{"atoms":r["atoms"],"native_order":r["order"]} for r in e["bonds"]],"molecule_charge":sum(e["charges"].values())}


@pytest.mark.parametrize("defect",["none","exact","partial","extra_edge","duplicate_edge","side_order","element","isotope","charge","total_charge","coordinates","nonfinite","unknown_atom"])
def test_native_representation_requires_whole_authorized_system_and_exact_state(tmp_path,defect):
    from nasolve.cif_source_representation import generation_representation_contract,native_representation_check
    source,_=source_pair(tmp_path);before=source.read_bytes();e=expected(source);n=snapshot(e)
    contract=generation_representation_contract(source,"Q17",POLICY)
    assert len(contract["allowed_systems"])==1
    allowed={tuple(edge) for edge in contract["allowed_systems"][0]}
    for row in n["bonds"]:
        if tuple(row["atoms"]) in allowed and defect!="exact":row["native_order"]=1.5
    if defect=="partial":n["bonds"][0]["native_order"]=e["bonds"][0]["order"]
    if defect=="extra_edge":n["bonds"].append({"atoms":["N1","N9"],"native_order":1})
    if defect=="duplicate_edge":n["bonds"].append(deepcopy(n["bonds"][0]))
    if defect=="side_order":next(r for r in n["bonds"] if tuple(r["atoms"]) not in allowed)["native_order"]=2
    if defect=="element":n["atoms"][0]["element"]="O"
    if defect=="isotope":next(r for r in n["atoms"] if r["element"]=="H")["element"]="D"
    if defect=="charge":n["atoms"][0]["native_atom_charge"]=1
    if defect=="total_charge":n["molecule_charge"]=1
    if defect=="coordinates":n["atoms"][0]["xyz"]=list(n["atoms"][0]["xyz"]);n["atoms"][0]["xyz"][0]+=0.01
    if defect=="nonfinite":n["atoms"][0]["xyz"]=[float("nan"),0,0]
    if defect=="unknown_atom":n["atoms"][0]["atom"]="missing"
    q=native_representation_check(n,e,contract,coordinates=True,charges=True)
    assert (q["status"]=="SOURCE_REPRESENTATION_PASS") is (defect in {"none","exact"})
    assert source.read_bytes()==before


def fake_generation(tmp_path,mode="none",opt_in=True,source_name="source.cif"):
    from tests.test_cif_constructor_backend import installation
    from tests.test_cif_source_candidate import REFERENCE
    from tests.test_cif_generation import program,HELP
    from nasolve.cif_source_candidate import generate_source_candidate,SOURCE_PATHS
    root,python,site,_,api=installation(tmp_path,"correct")
    source,fixture=source_pair(tmp_path/"inputs")
    if source_name!=source.name:source=source.rename(source.with_name(source_name))
    native=site/"elbow/chemistry/SimpleMoleculeClass.py"
    native.write_text("""import json
from pathlib import Path
from types import SimpleNamespace
class SimpleMoleculeClass(list):
 def __init__(self):
  e=json.loads(Path('candidate_spec.json').read_text())['declared_charge_control'];self.charge=sum(e['charges'].values())
  super().__init__([SimpleNamespace(name=n,symbol=v,charge=e['charges'][n],xyz=SimpleNamespace(**dict(zip('xyz',e['coordinates'][n])))) for n,v in e['elements'].items()])
  index={a.name:a for a in self}
  class Bond(list):pass
  self.bonds=[]
  for row in e['bonds']:
   b=Bond([index[n] for n in row['atoms']]);b.order=1.5 if set(row['atoms'])<=set(['N1','C2','N3','C4','C5','C6','N7','C8','N9']) else row['order'];self.bonds.append(b)
 def GetOriginalFormat(self):return 'CHEMICAL COMPONENTS'
 def SetCCTBX(self,value):self.cctbx=value
 def Setup(self):self.setup_calls=getattr(self,'setup_calls',0)+1
 def Chiralise(self,chiral_treatment):pass
""")
    reader=site/"elbow/chemistry/any_chemical_format_reader.py"
    reader.write_text("""from .SimpleMoleculeClass import SimpleMoleculeClass
def any_chemical_format_reader(*args,**kw):return SimpleMoleculeClass()
def is_chemical_components_file(text):return True
def return_molecule_class(molecule,simple=False):
 CHANGE
 return molecule
""".replace("CHANGE",{"conversion_edge":"molecule.bonds[0].order=1","conversion_coordinates":"molecule[0].xyz.x+=0.01","conversion_stereo":"molecule[0].chiral=1"}.get(mode,"pass")))
    folder=site/"elbow/command_line";folder.mkdir();(folder/"__init__.py").write_text("")
    builder=folder/"builder.py"
    builder.write_text(REFERENCE+"""
def parser():raise RuntimeError('FILE PARSER MUST NOT RUN')
def post_process(molecule,options):
 import os,shutil
 assert molecule.setup_calls==1
 assert sum(b.order==1.5 for b in molecule.bonds)==10
 BEFORE
 shutil.copyfile(os.environ['CANDIDATE_FIXTURE'],'candidate.cif')
 AFTER
 return molecule
""".replace("BEFORE","import time;time.sleep(4)" if mode=="timeout" else "pass").replace("AFTER",{"finished_charge":"molecule[0].charge=1","finished_edge":"molecule.bonds[0].order=1","exception_after":"raise RuntimeError('FAKE AFTER OUTPUT')"}.get(mode,"pass")))
    elbow=program(tmp_path,help_text=HELP+'  --opt_steps=COUNT  Step count\n');selected=root/'bin/phenix.elbow';selected.write_bytes(elbow.read_bytes());selected.chmod(0o755)
    pins=[{'anchor':'phenix_installation','path':(p:=site/name).relative_to(root).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for name in SOURCE_PATHS]
    out=tmp_path/'generation';options={'bond_representation_policy':POLICY} if opt_in else {}
    r=generate_source_candidate(root,python,selected,api,source,'Q17',out,environment={**os.environ,'CANDIDATE_FIXTURE':str(fixture)},expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=pins,phenix_version='FAKE',single_block_steps=12,timeout_seconds=0.5 if mode=='timeout' else 10,**options)
    return out,r


@pytest.mark.parametrize("mode",["none","conversion_edge","conversion_coordinates","conversion_stereo","finished_charge","finished_edge","exception_after","timeout"])
def test_owned_worker_preserves_aromatic_orders_and_retained_outputs(tmp_path,mode):
    from nasolve.cif_source_representation import read_representation_candidate
    out,r=fake_generation(tmp_path,mode)
    assert r['policy_id']=='cif-source-native-complete-candidate-v2'
    assert r['source_preserved'] and not r['automatic_adoption']
    if mode in {'none','exception_after'}:assert r['status']=='CANDIDATE_REVIEW'
    elif mode.startswith('finished'):assert r['status']=='REJECTED' and r['candidate_retained']
    else:assert r['candidate'] is None
    assert read_representation_candidate(out)['status']==r['status']


def test_legacy_worker_and_receipt_remain_default(tmp_path):
    from nasolve.cif_source_candidate import WORKER
    out,r=fake_generation(tmp_path,opt_in=False)
    assert sha256(WORKER.encode()).hexdigest()=='a43dd5c166926cb2d2ff0506c24fb77ea7c9f0668dfde61d0300961d8a9b1a6e'
    assert (out/'candidate_worker.py').read_text()==WORKER
    assert r['candidate'] is None and r['policy_id']=='cif-source-native-complete-candidate-v1'
    assert 'source_representation_contract' not in r


@pytest.mark.parametrize('defect',['contract','worker','source','spec','candidate','summary','conversion','extra_file','nested_receipt','scope'])
def test_cold_reader_rejects_tampered_generation_evidence(tmp_path,defect):
    from nasolve.cif_source_representation import read_representation_candidate
    out,r=fake_generation(tmp_path)
    assert r['status']=='CANDIDATE_REVIEW'
    if defect in {'worker','source','candidate'}:
        p=out/({'worker':'candidate_worker.py','source':'source.cif','candidate':'candidate.cif'}[defect]);p.write_text(p.read_text()+'\n')
    elif defect=='extra_file':(out/'unexpected.txt').write_text('extra')
    elif defect=='nested_receipt':
        (out/'hidden').mkdir();(out/'hidden/source_candidate_receipt.json').write_text('{}')
    else:
        p=out/('candidate_spec.json' if defect=='spec' else 'source_candidate_receipt.json');d=json.loads(p.read_text())
        if defect=='contract':d['source_representation_contract']['allowed_systems']=[]
        if defect=='spec':d['source_representation_contract']['allowed_systems']=[]
        if defect=='summary':d['status']='FAILED'
        if defect=='scope':d['native_backend']='UNQUALIFIED_BACKEND'
        if defect=='conversion':d['result']['representation_conversion']['status']='BLOCKED'
        p.write_text(json.dumps(d))
    with pytest.raises(ValueError):read_representation_candidate(out)


@pytest.mark.parametrize("defect",["charge_proof","stage_proof","builder_before","builder_after"])
def test_replay_recomputes_rebound_stage_evidence(tmp_path,defect):
    from nasolve.cif_source_representation import read_representation_candidate
    out,r=fake_generation(tmp_path)
    result=json.loads((out/'candidate_result.json').read_text())
    if defect=="charge_proof":result['charge_control']['before']['atoms'][0]['native_atom_charge']=1
    elif defect=='stage_proof':result['representation_conversion']['checks']['source_formal_charges']=False
    else:result['builder']['before' if defect=='builder_before' else 'after']['atoms'][0]['native_atom_charge']=1
    p=out/'candidate_result.json';p.write_text(json.dumps(result));r['result']=result
    for row in r['outputs']:
        if row['path']==p.name:row.update(sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
    (out/'source_candidate_receipt.json').write_text(json.dumps(r))
    with pytest.raises(ValueError):read_representation_candidate(out)


def test_generation_uses_frozen_source_identity_when_original_basename_differs(tmp_path):
    from nasolve.cif_source_representation import read_representation_candidate
    out,r=fake_generation(tmp_path,source_name="original CCD source.cif")
    assert r['status']=='CANDIDATE_REVIEW'
    assert r['inspection']['source_assessment']['inputs'][0]['name']=='source.cif'
    moved=out.rename(tmp_path/'relocated');assert not out.exists()
    assert read_representation_candidate(moved)==r


def test_unknown_policy_fails_before_any_native_path_or_output_access(tmp_path):
    from nasolve.cif_source_candidate import generate_source_candidate
    with pytest.raises(ValueError,match="representation policy"):
        generate_source_candidate(tmp_path/'absent',tmp_path/'absent',tmp_path/'absent',[],tmp_path/'absent','Q17',tmp_path/'out',environment={},expected_dialect='CHEMICAL_COMPONENTS_CIF',prior_sources=[],phenix_version='fake',bond_representation_policy='guess')
    assert not (tmp_path/'out').exists()
