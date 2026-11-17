"""Frozen canonical recipes must not silently lose atoms or image identity."""
from hashlib import sha256
import json

import pytest

from nasolve.topostitch_coordinates import ResidueSite
from nasolve.topostitch_recipe import PairImage, prepare_pair_recipe, recipe_digest
from .helpers import pdb_record
from .test_topostitch_periodic import cryst1


def fixture(codes=("DA", "DT")):
    names = {
        "DA": "N9 C8 N7 C5 C6 N6 N1 C2 N3 C4 C1'",
        "DT": "N1 C2 O2 N3 C4 O4 C5 C6 C7 C1'",
        "DG": "N9 C8 N7 C5 C6 O6 N1 C2 N2 N3 C4 C1'",
        "DC": "N1 C2 O2 N3 C4 N4 C5 C6 C1'",
    }
    lines = [cryst1((40,40,60,90,90,90), "P 43")]
    serial = 1
    for side, code in enumerate(codes):
        for i, atom in enumerate(names[code].split()):
            lines.append(pdb_record("ATOM", serial, atom, code, "AB"[side], 1,
                x=4+side*7+(i%4), y=3+(i//4), z=5+side*.3+(i%3)*.02, element=atom[0]))
            serial += 1
    return "".join(lines)+"END\n"


def pair(**changes):
    values = dict(pair_id="chosen", source=ResidueSite("A",1), target=ResidueSite("B",1),
                  target_operator_xyz="y,-x,z+1/4", purpose="selected")
    values.update(changes)
    return PairImage(**values)


def prepare(tmp_path, text=None, requests=None):
    p=tmp_path/"model.pdb";p.write_text(fixture() if text is None else text)
    before=p.read_bytes()
    result=prepare_pair_recipe(p, requests or [pair()], expected_sha256=sha256(before).hexdigest())
    assert p.read_bytes()==before
    return result


def test_complete_recipe_keeps_library_planes_and_exact_images(tmp_path):
    recipe=prepare(tmp_path)
    p,=recipe["pairs"]
    assert p["expected_counts"]=={"bond":2,"angle":2,"planarity":1,"parallelity":1}
    assert "sigma = 0.176" in p["phil"] and "sigma = 0.027" in p["phil"]
    assert "name N7" in p["phil"] and "name C7" in p["phil"]
    assert p["target_operator_xyz"]=="y,-x,z+1/4"
    assert p["sites"]==[{"chain":"A","residue_number":1,"insertion_code":""},
                        {"chain":"B","residue_number":1,"insertion_code":""}]
    assert p["role_indices"]["L"]==list(range(11))
    assert p["role_indices"]["R"]==list(range(11,21))
    assert recipe["policy"]["native_bonded_tables_changed"] is False
    assert recipe["policy"]["normalization"]=="UNNORMALIZED_ADDITIVE_PAIR_ENERGY"
    assert recipe["scientific_acceptance"] is False
    assert str(tmp_path) not in json.dumps(recipe)
    assert len(recipe_digest(recipe))==64


def test_gc_and_reversed_orientation_use_actual_library_recipe(tmp_path):
    recipe=prepare(tmp_path,fixture(("DC","DG")))
    p,=recipe["pairs"]
    assert p["recipe"]=="GC"
    assert p["expected_counts"]=={"bond":3,"angle":6,"planarity":1,"parallelity":1}
    assert "chain R and resid 1 and name N2" in p["phil"]


def test_missing_plane_only_atom_is_not_silently_omitted(tmp_path):
    text="".join(l for l in fixture().splitlines(keepends=True) if l[12:16].strip()!="N7")
    with pytest.raises(ValueError,match="complete.*N7"):
        prepare(tmp_path,text)


@pytest.mark.parametrize("change", ["partial_occupancy","alternate","duplicate","unsupported"])
def test_ambiguous_or_unsupported_selected_residues_fail(tmp_path,change):
    lines=fixture().splitlines(keepends=True)
    i=next(i for i,l in enumerate(lines) if l.startswith("ATOM"))
    if change=="partial_occupancy":lines[i]=lines[i][:54]+"  0.50"+lines[i][60:]
    elif change=="alternate":lines[i]=lines[i][:16]+"A"+lines[i][17:]
    elif change=="duplicate":lines.insert(i,lines[i])
    else:lines=[l[:17]+"ADE"+l[20:] if l.startswith("ATOM") and l[21]=="A" else l for l in lines]
    with pytest.raises(ValueError):prepare(tmp_path,"".join(lines))


@pytest.mark.parametrize("requests", [
    [pair(),pair(pair_id="duplicate")],
    [pair(),pair(pair_id="reverse",source=ResidueSite("B",1),target=ResidueSite("A",1),target_operator_xyz="-y,x,z-1/4")],
    [pair(),pair(pair_id="chosen",target_operator_xyz="x,y,z")],
])
def test_duplicate_and_reciprocal_edges_are_not_double_weighted(tmp_path,requests):
    with pytest.raises(ValueError,match="uplicate"):
        prepare(tmp_path,requests=requests)


def test_distinct_lattice_images_are_not_collapsed(tmp_path):
    r=prepare(tmp_path,requests=[pair(),pair(pair_id="other",target_operator_xyz="y+1,-x,z+1/4")])
    assert r["pairs"][0]["target_operator_xyz"]!=r["pairs"][1]["target_operator_xyz"]
    assert r["connection_capacity_validated"] is False


def test_incompatible_operator_and_stale_source_fail(tmp_path):
    with pytest.raises(ValueError,match="belong"):
        prepare(tmp_path,requests=[pair(target_operator_xyz="-x,-y,-z")])
    p=tmp_path/"model.pdb"
    with pytest.raises(ValueError,match="checksum"):
        prepare_pair_recipe(p,[pair()],expected_sha256="0"*64)


def test_changed_mapping_binds_actual_atoms_and_changes_fingerprint(tmp_path,monkeypatch):
    from restraints import residue_library
    before=prepare(tmp_path)
    original=residue_library.load_residue_records
    def renamed():
        rows=original()
        for row in rows:
            if row.get("Ligand code")=="DA":row["N7"]="Q7"
        return rows
    monkeypatch.setattr(residue_library,"load_residue_records",renamed)
    after=prepare(tmp_path,fixture().replace("  N7 ","  Q7 "))
    assert "name Q7" in after["pairs"][0]["phil"]
    assert before["library"]["effective_sha256"]!=after["library"]["effective_sha256"]


def test_explicit_model_path_survives_relocation(tmp_path):
    old=tmp_path/"old";old.mkdir();before=prepare(old)
    moved=tmp_path/"moved";old.rename(moved);assert not old.exists()
    after=prepare_pair_recipe(moved/"model.pdb",[pair()],expected_sha256=before["source_model_sha256"])
    assert before==after


def test_request_types_and_finite_json_are_strict():
    with pytest.raises(ValueError):pair(source={"chain":"A"})
    with pytest.raises(ValueError):pair(purpose="automatic")
    with pytest.raises(ValueError):pair(pair_id="")
    with pytest.raises(ValueError):recipe_digest({"bad":float("nan")})


def test_virtual_role_labels_support_blank_chain_and_insertion_codes(tmp_path):
    lines=[]
    for line in fixture().splitlines(keepends=True):
        if line.startswith("ATOM"):
            chain=" " if line[21]=="A" else "'"
            line=line[:21]+chain+line[22:26]+"B"+line[27:]
        lines.append(line)
    request=pair(source=ResidueSite("",1,"B"),target=ResidueSite("'",1,"B"))
    result=prepare(tmp_path,"".join(lines),[request])
    text=result["pairs"][0]["phil"]
    assert "chain L and resid 1" in text and "chain R and resid 1" in text
    assert result["pairs"][0]["sites"][0]["insertion_code"]=="B"


def test_library_partial_plane_behavior_is_explicitly_guarded(tmp_path):
    from restraints.phenix import PairResidue, generate_pair_restraints
    # The formatter intentionally accepts partial maps for other clients. This
    # native binding scope promises a complete recipe, so omission is an error.
    a={name:name for name in "N9 C8 C5 C6 N6 N1 C2 N3 C4".split()}
    t={name:name for name in "N1 C2 O2 N3 C4 O4 C5 C6 C7".split()}
    emitted=generate_pair_restraints(PairResidue("L","1",a,"A"),PairResidue("R","1",t,"T"))
    assert "planarity {" in emitted and "name N7" not in emitted
    text="".join(l for l in fixture().splitlines(keepends=True) if l[12:16].strip()!="N7")
    with pytest.raises(ValueError,match="complete.*N7"):prepare(tmp_path,text)


def attribution_fixture(core=1.,selected=5.):
    from nasolve.topostitch_native_recipe import _pair_term_summary
    from nasolve.topostitch_recipe import POLICY
    rows=[]
    for pair,purpose,value in [('retained','core',core),('connection','selected',selected)]:
        for kind,measurement in [('bond','distance_angstrom'),('angle','angle_degrees'),
                ('planarity','rms_distance_angstrom'),('parallelity','native_delta_degrees')]:
            rows.append(dict(number=len(rows)+1,definition=dict(pair_id=pair,purpose=purpose,kind=kind,
                sigma=.2,i_seqs=[0,1],ideal=1.),native_residual=value,measurement={measurement:1.}))
    return dict(schema_version=1,kind='topostitch-native-pair-attribution',binding_sha256='a'*64,
        points_sha256='b'*64,terms=rows,**_pair_term_summary(rows),normalization=POLICY['normalization'],
        native_container_sum_verified=True,runtime_authority=False,scientific_acceptance=False)


def test_improving_total_keeps_a_worsened_core_pair_visible():
    from nasolve.topostitch_native_recipe import compare_pair_attribution
    before=attribution_fixture();after=attribution_fixture(core=2,selected=1)
    after['points_sha256']='c'*64
    report=compare_pair_attribution(before,after)
    assert report['target_change']==-12
    assert report['purposes']['core']['increased_pair_ids']==['retained']
    assert report['purposes']['selected']['increased_pair_ids']==[]
    assert report['purposes']['core']['target_change']==4
    assert report['source_points_sha256']!=report['endpoint_points_sha256']
    assert not report['runtime_authority'] and not report['scientific_acceptance']


@pytest.mark.parametrize('change',['binding','definition','summary','missing_family','number','negative','nonfinite','purpose','measurement','claim','digest'])
def test_incomplete_or_changed_pair_attribution_cannot_be_compared(change):
    from nasolve.topostitch_native_recipe import compare_pair_attribution,_pair_term_summary
    before=attribution_fixture();after=attribution_fixture()
    if change=='binding':after['binding_sha256']='d'*64
    elif change=='definition':
        after['terms'][0]['definition']['sigma']=.3
        after.update(_pair_term_summary(after['terms']))
    elif change=='summary':after['target']+=1
    elif change=='missing_family':after['terms'].pop()
    elif change=='number':after['terms'][0]['number']=2
    elif change=='negative':after['terms'][0]['native_residual']=-1
    elif change=='nonfinite':after['terms'][0]['native_residual']=float('nan')
    elif change=='purpose':after['terms'][0]['definition']['purpose']='selected'
    elif change=='measurement':after['terms'][0]['measurement']['distance_angstrom']=float('inf')
    elif change=='claim':after['scientific_acceptance']=True
    else:after['binding_sha256']=before['binding_sha256']=None
    with pytest.raises(ValueError):compare_pair_attribution(before,after)



def test_rebind_preserves_frozen_chemistry_and_images_without_regeneration(tmp_path, monkeypatch):
    from copy import deepcopy
    from nasolve import topostitch_recipe as recipes
    packet=prepare(tmp_path,requests=[pair(),pair(pair_id="image",target_operator_xyz="y+1,-x,z+1/4")])
    source=(tmp_path/"model.pdb").read_bytes();before=deepcopy(packet)
    lines=source.decode().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line.startswith("ATOM"):
            lines[i]=line[:30]+f"{float(line[30:38])+.5:8.3f}"+line[38:60]+" 31.00"+line[66:]
    moved=("REMARK changed coordinates and ADP\n"+"".join(lines)).encode()
    monkeypatch.setattr(recipes,'_library',lambda:pytest.fail('Frozen chemistry must not be regenerated'))
    rebound=recipes.rebind_pair_recipe(packet,source,moved,
        expected_recipe_sha256=recipe_digest(packet),expected_model_sha256=sha256(moved).hexdigest())
    expected=deepcopy(packet);expected['source_model_sha256']=sha256(moved).hexdigest()
    assert rebound==expected and packet==before
    rebound['pairs'][0]['purpose']='core'
    assert packet==before


@pytest.mark.parametrize('change', ['element','charge','occupancy','name','residue','chain',
    'reorder','missing','added','cell','group','internal_ter','blank_element','invalid_occupancy'])
def test_rebind_refuses_changed_identity_chemistry_or_frame(tmp_path,change):
    from nasolve.topostitch_recipe import rebind_pair_recipe
    packet=prepare(tmp_path);source=(tmp_path/'model.pdb').read_bytes()
    lines=source.decode().splitlines(keepends=True);i=1;line=lines[i]
    if change=='element':lines[i]=line[:76]+' C'+line[78:]
    elif change=='blank_element':lines[i]=line[:76]+'  '+line[78:]
    elif change=='charge':lines[i]=line.rstrip('\n').ljust(78)+'1+\n'
    elif change=='occupancy':lines[i]=line[:54]+'  0.50'+line[60:]
    elif change=='invalid_occupancy':lines[i]=line[:54]+'   nan'+line[60:]
    elif change=='name':lines[i]=line[:12]+'  NX'+line[16:]
    elif change=='residue':lines[i]=line[:17]+' DG'+line[20:]
    elif change=='chain':lines[i]=line[:21]+'Z'+line[22:]
    elif change=='reorder':lines[1],lines[2]=lines[2],lines[1]
    elif change=='missing':del lines[i]
    elif change=='added':lines.insert(-1,pdb_record('HETATM',99,'O','HOH','W',1,element='O'))
    elif change=='cell':lines[0]=cryst1((41,41,60,90,90,90),'P 43')
    elif change=='group':lines[0]=cryst1((40,40,60,90,90,90),'P 41')
    elif change=='internal_ter':lines.insert(2,'TER\n')
    changed=''.join(lines).encode()
    with pytest.raises(ValueError):
        rebind_pair_recipe(packet,source,changed,expected_recipe_sha256=recipe_digest(packet),
                           expected_model_sha256=sha256(changed).hexdigest())


@pytest.mark.parametrize('change',['packet_digest','source_bytes','destination_digest','packet_source','packet_atoms','packet_frame','authority'])
def test_rebind_refuses_unbound_original_or_destination(tmp_path,change):
    from nasolve.topostitch_recipe import rebind_pair_recipe
    packet=prepare(tmp_path);source=(tmp_path/'model.pdb').read_bytes();target=source
    if change=='packet_source':packet['source_model_sha256']='0'*64
    elif change=='packet_atoms':packet['atom_identities'].reverse()
    elif change=='packet_frame':packet['crystal']['cell_parameters'][0]=41.
    elif change=='authority':packet['runtime_authority']=True
    expected=recipe_digest(packet)
    if change=='packet_digest':expected='0'*64
    elif change=='source_bytes':source+=b'REMARK changed original\n'
    target_digest='0'*64 if change=='destination_digest' else sha256(target).hexdigest()
    with pytest.raises(ValueError):
        rebind_pair_recipe(packet,source,target,expected_recipe_sha256=expected,
                           expected_model_sha256=target_digest)


def test_rebind_accepts_equivalent_frame_spelling_and_chain_end_ter(tmp_path):
    from nasolve.topostitch_recipe import rebind_pair_recipe
    packet=prepare(tmp_path);source=(tmp_path/'model.pdb').read_bytes()
    lines=source.decode().splitlines(keepends=True)
    lines[0]=cryst1((40,40,60,90,90,90),'P43')
    at=next(i for i,line in enumerate(lines) if line.startswith('ATOM') and line[21]=='B')
    lines.insert(at,'TER\n');target=''.join(lines).encode()
    result=rebind_pair_recipe(packet,source,target,expected_recipe_sha256=recipe_digest(packet),
                             expected_model_sha256=sha256(target).hexdigest())
    assert result['crystal']==packet['crystal'] and result['pairs']==packet['pairs']



def test_rebind_detaches_before_reading_models(tmp_path,monkeypatch):
    from copy import deepcopy
    from nasolve import topostitch_recipe as recipes
    packet=prepare(tmp_path);source=(tmp_path/'model.pdb').read_bytes();before=deepcopy(packet)
    original=recipes.model_atom_rows
    def read(data):
        packet['pairs'][0]['phil']='changed by caller'
        return original(data)
    monkeypatch.setattr(recipes,'model_atom_rows',read)
    result=recipes.rebind_pair_recipe(packet,source,source,
        expected_recipe_sha256=recipe_digest(before),expected_model_sha256=sha256(source).hexdigest())
    assert result==before
