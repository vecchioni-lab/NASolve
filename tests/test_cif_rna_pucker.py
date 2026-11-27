"""Match a recorded RNA geometry adjustment to its explicit numerical table."""
from copy import deepcopy

import pytest


def _example():
    values = {"data_":"comp_TST", "_chem_comp.id":["TST"],
              "_chem_comp_plane_atom.atom_id":["X"]}
    table = {"data_":"mod_rna2p"}
    for category, atoms, field, start, end in (
        ("bond", ("AA","BB"), "value_dist", "1.51", "1.53"),
        ("angle", ("AA","BB","CC"), "value_angle", "110", "112"),
        ("tor", ("AA","BB","CC","DD"), "value_angle", "120", "117"),
    ):
        original, mod = "_chem_comp_"+category+".", "_chem_mod_"+category+"."
        for i, name in enumerate(atoms, 1):
            values[original+f"atom_id_{i}"]=[name]
            table[mod+f"atom_id_{i}"]=[name]
        values[original+field]=[start]
        values[original+field+"_esd"]=["0.03" if category=="bond" else "3"]
        table[mod+"mod_id"]=["rna2p"]
        table[mod+"function"]=["change"]
        table[mod+"new_"+field]=[end]
        table[mod+"new_"+field+"_esd"]=["0.02" if category=="bond" else "2"]
    values["_chem_comp_bond.type"]=["SINGLE"]
    table["_chem_mod_bond.new_type"]=["coval"]
    values["_chem_comp_tor.id"]=["original"]
    values["_chem_comp_tor.period"]=["3"]
    table["_chem_mod_tor.id"]=["library"]
    table["_chem_mod_tor.new_period"]=["1"]
    return values, table


def test_only_present_geometry_changes_and_original_orders_stay_available():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values, table = _example()
    original=deepcopy(values)
    projected, counts = project_pucker_targets(values,table)
    assert values==original
    assert projected["_chem_comp_bond.type"]==["coval"]
    assert projected["_chem_comp_tor.period"]==["1"]
    assert projected["_chem_comp_tor.id"]==["original"]
    assert projected["_chem_comp_plane_atom.atom_id"]==["X"]
    assert counts=={"bonds":1,"angles":1,"torsions":1}


@pytest.mark.parametrize("column,value", [
    ("_chem_mod_bond.function","delete"),("_chem_mod_bond.new_type","AROM"),
    ("_chem_mod_angle.new_value_angle","181"),("_chem_mod_tor.new_period","1.5"),
    ("_chem_mod_bond.new_value_dist","nan"),("_chem_mod_tor.new_value_angle_esd","0"),
    ("_chem_mod_angle.mod_id","rna3p"),("_chem_mod_atom.function","add"),
    ("_chem_mod_bond.new_value_dist_neutron","1.50")])
def test_unknown_or_nonphysical_adjustment_is_unexplained(column,value):
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    table[column]=[value]
    with pytest.raises(ValueError):
        project_pucker_targets(values,table)


def test_explicit_three_prime_table_requires_its_own_modifier_in_every_row():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values, table = _example()
    table["data_"] = "mod_rna3p"
    for key, column in table.items():
        if key.endswith(".mod_id"):
            column[0] = "rna3p"
    table["_chem_mod_bond.new_value_dist"] = ["1.529"]
    projected, counts = project_pucker_targets(values, table, modifier="rna3p")
    assert projected["_chem_comp_bond.value_dist"] == ["1.529"]
    assert counts == {"bonds":1, "angles":1, "torsions":1}
    with pytest.raises(ValueError):
        project_pucker_targets(values, table)
    table["_chem_mod_angle.mod_id"] = ["rna2p"]
    with pytest.raises(ValueError):
        project_pucker_targets(values, table, modifier="rna3p")


def test_coval_is_never_a_global_alias_for_single():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    values["_chem_comp_bond.type"]=["AROM"]
    with pytest.raises(ValueError,match="single"):
        project_pucker_targets(values,table)
    values["_chem_comp_bond.type"]=["single"]
    values["_chem_comp_bond.value_order"]=["DOUB"]
    with pytest.raises(ValueError,match="single"):
        project_pucker_targets(values,table)


def test_bond_and_angle_match_both_directions_but_torsion_order_is_literal():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    for category,degree in (("bond",2),("angle",3),("tor",4)):
        cols=["_chem_mod_"+category+".atom_id_"+str(i) for i in range(1,degree+1)]
        for key,rev in zip(cols,[table[c] for c in reversed(cols)]):
            table[key]=rev
    p,counts=project_pucker_targets(values,table)
    assert counts=={"bonds":1,"angles":1,"torsions":0}
    assert p["_chem_comp_tor.period"]==["3"]


def test_duplicate_modifier_keys_are_refused():
    from nasolve.cif_rna_pucker import project_pucker_targets
    values,table=_example()
    for k in table:
        if k.startswith("_chem_mod_bond."):
            table[k] *= 2
    with pytest.raises(ValueError,match="uplicate"):
        project_pucker_targets(values,table)


@pytest.mark.parametrize("fault", ["none","unexplained-bond","plane-weight","chirality-sign","extra-order"])
def test_adjusted_read_keeps_the_other_native_requirements(tmp_path, fault):
    from nasolve.cif_candidate_usability import _check_native_targets, qualify_candidate_native
    from nasolve.cif_rna_pucker import project_pucker_targets
    from nasolve.cif_stereochemistry_audit import _values
    from tests.test_cif_candidate_usability import native_case
    source,candidate,model,native=native_case(tmp_path)
    values=_values(candidate,"Q17")
    _,table=_example()
    bond="_chem_mod_bond."
    left,right=values["_chem_comp_bond.atom_id_1"][0],values["_chem_comp_bond.atom_id_2"][0]
    table[bond+"atom_id_1"],table[bond+"atom_id_2"]=[left],[right]
    projected,_=project_pucker_targets(values,table)
    definition=native["monomer_mappings"]["rows"][0]["metadata"]["effective_definition"]
    bs=definition["bonds"][0]
    bs.update(type="coval",value_dist=1.53,value_dist_esd=.02)
    live=native["geometry"]["proxy_details"]
    live["bond_simple"][0].update(distance_ideal=1.53,weight=2500.)
    if fault=="unexplained-bond":
        live["bond_simple"][1]["distance_ideal"]+=.1
    if fault=="plane-weight":
        live["planarity"][0]["weights"][0]+=1
    if fault=="chirality-sign":
        live["chirality"][0]["volume_ideal"]*=-1
    if fault=="extra-order":
        definition["bonds"][1]["type"]="coval"
    strict=qualify_candidate_native(source,candidate,model,"Q17",native)
    adjusted=_check_native_targets(source,candidate,model,"Q17",native,
        bond_representation_policy=None,projected=projected)
    assert not strict["native_usable"]
    assert adjusted["native_usable"] is (fault=="none")


@pytest.mark.parametrize(("states","fault","expected"), [
    (("rna3p","rna2p"), None, "SEED_TARGETS_EXPLAINED"),
    (("rna3p","rna3p"), None, "SEED_TARGETS_EXPLAINED"),
    (("rna3p","rna2p"), "plane", "REVIEW"),
    (("rna3p","rna3p"), "different_proxies", "REVIEW"),
    (("rna2p","rna2p"), None, "ADJUSTED_TARGETS_EXPLAINED"),
    (("rna3p","unknown"), None, None),
])
def test_each_seed_must_explain_its_own_numerical_targets(tmp_path, monkeypatch, states, fault, expected):
    from nasolve import cif_rna_pucker as p

    source, candidate = (tmp_path / name for name in ("source.cif", "candidate.cif"))
    source.write_text("source")
    candidate.write_text("candidate")
    models = [tmp_path / (name + ".pdb") for name in ("source", "candidate")]
    native = []
    phases = {}
    for i, state in enumerate(states):
        site = tmp_path / str(i)
        site.mkdir()
        (site / "native_receipt.json").write_text(state)
        phases[f"native-{i:03d}"] = {"job": {"cwd": {"path": str(i)}}}
        native.append({"mod":state, "i":i, "monomer_mappings":{"rows":[
            {"chem_mod_ids":{"status":"RECORDED","ids":[state]}}]}})
    protocol = {"component":"QT", "consumer":{"version":"example"}, "bond_representation_policy":None}
    monkeypatch.setattr(p, "_inputs", lambda root: (protocol,(source,candidate),models,None))
    monkeypatch.setattr(p, "_values", lambda *args: _example()[0])
    monkeypatch.setattr(p, "inspect_candidate_qualification_processes",
                        lambda root: {"state":"STOPPED","phases":phases})
    monkeypatch.setattr(p, "_owned_native_capture", lambda root, ref, i, *args: native[i])
    monkeypatch.setattr(p, "qualify_candidate_native", lambda *a, **k: {"checks":{"targets":False}})
    def checked(source, dictionary, model, code, receipt, *, projected, **options):
        target = "1.529" if receipt["mod"] == "rna3p" else "1.526"
        return {"checks":{"targets":projected["_chem_comp_bond.value_dist"] == [target],
                          "planes":fault != "plane" or receipt["i"] == 0}}
    monkeypatch.setattr(p, "_check_native_targets", checked)
    monkeypatch.setattr(p, "covalent_proxy_signature",
                        lambda n: (n["mod"], n["i"] if fault=="different_proxies" else 0))
    def block(path, pin, *, modifier):
        assert modifier == pin["modifier"]
        table = _example()[1]
        table["data_"] = "mod_" + modifier
        for name in table:
            if name.endswith(".mod_id"):
                table[name] = [modifier]
        table["_chem_mod_bond.new_value_dist"] = ["1.529" if modifier=="rna3p" else "1.526"]
        return table
    monkeypatch.setattr(p, "_pucker_block", block)
    monkeypatch.setattr(p, "table_bytes", lambda path, pin, *, modifier: None)
    def installed(modifier):
        return tmp_path / (modifier+".cif"), {"modifier":modifier}
    if expected is None:
        with pytest.raises(ValueError, match="recorded native"):
            p._review_observed(tmp_path, installed)
        return
    report = p._review_observed(tmp_path, installed)
    assert report["status"] == expected and report["qualification_unchanged"] is True
    if states == ("rna2p","rna2p"):
        assert report["policy_id"] == p.POLICY_ID and report["modifier"] == "rna2p"
        assert "tables" not in report and all("modifier" not in seed for seed in report["seeds"])
    else:
        assert list(s["modifier"] for s in report["seeds"]) == list(states)
        assert set(report["tables"]) == set(states)
        with pytest.raises(ValueError):
            p._review_default(tmp_path, *installed("rna2p"))


def test_cli_prints_observed_pucker_at_each_seed(tmp_path, monkeypatch, capsys):
    from nasolve import cli, cif_rna_pucker as p
    rows = {"bonds":10,"angles":12,"torsions":6}
    result = {"status":"SEED_TARGETS_EXPLAINED","component":"Q17","tables":{"rna2p":{},"rna3p":{}},
              "seeds":[{"seed":s,"modifier":m,"matched_rows":rows,"adjusted_checks_failed":[]}
                       for s,m in (("source","rna3p"),("candidate","rna2p"))]}
    monkeypatch.setattr(cli,"discover_phenix",lambda *a,**k:object())
    monkeypatch.setattr(p,"review_pucker_adjustment",lambda *a:result)
    assert cli.main(["cif-doctor","explain-pucker",str(tmp_path)]) == 0
    message = capsys.readouterr().out
    assert "source selected rna3p" in message and "candidate selected rna2p" in message


def test_cli_pucker_replay_keeps_qualification_unchanged(tmp_path, monkeypatch, capsys):
    from nasolve.cli import main
    from nasolve import cli, cif_rna_pucker
    result={"status":"ADJUSTED_TARGETS_EXPLAINED","component":"ZZ8","modifier":"rna2p",
            "seeds":[],"matched_rows":{"bonds":2,"angles":3,"torsions":1},"qualification_unchanged":True}
    monkeypatch.setattr(cli,"discover_phenix",lambda *a,**k: object())
    monkeypatch.setattr(cif_rna_pucker,"review_pucker_adjustment",lambda directory, installation:result)
    assert main(["cif-doctor","explain-pucker",str(tmp_path)])==0
    assert "Matched rows for bonds (2), angles (3) and torsions (1)" in capsys.readouterr().out
    assert list(tmp_path.iterdir())==[]


@pytest.mark.parametrize("replay", [False, True])
def test_verify_pucker_cli_runs_or_reopens_the_requested_jobs(tmp_path, monkeypatch, capsys, replay):
    from nasolve import cli, cif_rna_pucker
    from nasolve.cli import main

    standard, literal = tmp_path / "default", tmp_path / "literal"
    install = object()
    calls = []
    def selected(first, second, installation=None, **options):
        assert options == ({} if replay else {"include_observed_states":True})
        calls.append((first, second, installation))
        return {"component": "ZZ8"}
    monkeypatch.setattr(cli, "discover_phenix", lambda *a, **k: install)
    name = "read_literal_pucker" if replay else "verify_literal_pucker"
    monkeypatch.setattr(cif_rna_pucker, name, selected)
    args = ["cif-doctor", "verify-pucker", str(standard), str(literal)]
    assert main(args + (["--replay"] if replay else [])) == 0
    assert calls == [(standard, literal, None if replay else install)]
    assert "ZZ8: both coordinate seeds" in capsys.readouterr().out


def test_archived_table_requires_exact_bounded_bytes(tmp_path):
    from hashlib import sha256
    from nasolve.cif_rna_pucker import table_bytes
    data=b"native numerical table"
    path=tmp_path/"rna2p.cif"
    path.write_bytes(data)
    pin=dict(anchor="phenix_installation",path="lib/python3/site-packages/chem_data/geostd/rna_dna/mod_rna2p.cif",
             size=len(data),sha256=sha256(data).hexdigest())
    assert table_bytes(path,pin)==data
    path.write_bytes(b"x"*len(data))
    with pytest.raises(ValueError,match="checksum"):
        table_bytes(path,pin)
    with pytest.raises(ValueError,match="pinned"):
        table_bytes(path,dict(pin,path="../mod_rna2p.cif"))


def test_three_prime_pin_cannot_stand_in_for_two_prime_table(tmp_path):
    from hashlib import sha256
    from nasolve.cif_rna_pucker import table_bytes
    path = tmp_path / "rna3p.cif"
    data = b"explicit three-prime table"
    path.write_bytes(data)
    pin = dict(anchor="phenix_installation",path="lib/python3/site-packages/chem_data/geostd/rna_dna/mod_rna3p.cif",
               size=len(data),sha256=sha256(data).hexdigest())
    assert table_bytes(path,pin,modifier="rna3p") == data
    with pytest.raises(ValueError,match="pinned"):
        table_bytes(path,pin)
    path.write_bytes(b"x"*len(data))
    with pytest.raises(ValueError,match="checksum"):
        table_bytes(path,pin,modifier="rna3p")


def test_only_legacy_pairs_fall_back_to_the_selected_installation(tmp_path,monkeypatch):
    from nasolve import cli, cif_rna_pucker as p
    sdk=object()
    calls=[]
    def read(a,b,installation=None):
        calls.append(installation)
        if installation is None:
            raise p.ArchivedPuckerTableUnavailable()
        return {"component":"XYZ"}
    monkeypatch.setattr(p,"read_literal_pucker",read)
    monkeypatch.setattr(cli,"discover_phenix",lambda *a,**k:sdk)
    args=["cif-doctor","verify-pucker",str(tmp_path/"default"),str(tmp_path/"literal"),"--replay"]
    assert cli.main(args)==0 and calls==[None,sdk]
    def corrupt(*a):
        raise ValueError("altered saved table")
    monkeypatch.setattr(p,"read_literal_pucker",corrupt)
    monkeypatch.setattr(cli,"discover_phenix",lambda *a:pytest.fail("must preserve the archived failure"))
    assert cli.main(args)==1


@pytest.mark.parametrize("defect",["none","foreign-table","other-consumer","missing-seed","same-native","other-source","different-default","wrong-site-control"])
@pytest.mark.parametrize("by_seed", [False, True])
def test_stored_rna_proof_requires_two_independent_reads_in_each_condition(defect, by_seed):
    from hashlib import sha256
    from nasolve.cif_dictionary_store import _digest
    from nasolve.cif_rna_pucker import POLICY_ID,validate_paired_qualification
    h=lambda s:sha256(s.encode()).hexdigest()
    def ref(path,label):
        return dict(anchor="qualification_directory",path=path,sha256=h(label),size=50)
    def seeds(condition):
        return [dict(seed=s,native_receipt=ref("native/%03d/reading/native_receipt.json"%i,condition+s))
                for i,s in enumerate(("source","candidate"))]
    ds,ls=seeds("default"),seeds("literal")
    for row in ds:
        row.update(literal_checks_failed=["exact_active_angles"],adjusted_checks_failed=[])
    consumer=dict(version="TEST",name="Phenix/CCTBX")
    pin=dict(anchor="phenix_installation",size=90,sha256=h("pucker"),
             path="lib/python3/site-packages/chem_data/geostd/rna_dna/mod_rna2p.cif")
    review=dict(policy_id=POLICY_ID,status="ADJUSTED_TARGETS_EXPLAINED",modifier="rna2p",component="XYZ",
                scope="ISOLATED_COMPONENT_ONLY",phenix_version="TEST",same_covalent_proxies=True,automatic_adoption=False,
                table=pin,seeds=ds,matched_rows=dict(bonds=2,angles=3,torsions=1),
                source=ref("inputs/source/source.cif","source"),candidate=ref("inputs/candidate/candidate.cif","candidate"))
    q=dict(literal_rna=dict(default_review_sha256=_digest(review),table=pin),
           paired_rna=dict(default=review,literal_seeds=ls,literal_report=ref("qualification_execution.json","literal report"),
                           consumer_sha256=_digest(consumer)))
    args=dict(code="XYZ",source_sha256=h("source"),candidate_sha256=h("candidate"),consumer=consumer,table=pin)
    if by_seed:
        from nasolve.cif_rna_pucker import ETHER_PUCKER_PERMISSION, ETHER_PAIRED_USABILITY, OBSERVED_POLICY_ID
        pins={"rna2p":pin, "rna3p":dict(pin,sha256=h("three"),path=pin["path"].replace("2p","3p"))}
        args["table"]={"policy_id":ETHER_PUCKER_PERMISSION,"tables":pins}
        counts=review.pop("matched_rows")
        review.pop("modifier");review.pop("table")
        review.update(policy_id=OBSERVED_POLICY_ID,status="SEED_TARGETS_EXPLAINED",tables=pins,
                      same_covalent_proxies=False)
        for row,modifier in zip(ds,("rna3p","rna2p")):
            row.update(modifier=modifier,matched_rows=dict(counts))
        q["policy_id"]=ETHER_PAIRED_USABILITY
        q["paired_rna"]["pucker_permission"]=args["table"]
        q["literal_rna"]=dict(default_review_sha256=_digest(review),tables=pins)
    if defect=="foreign-table":args["table"]=dict(pin,sha256=h("next build"))
    if defect=="other-consumer":args["consumer"]=dict(consumer,version="other")
    if defect=="missing-seed":ls.pop()
    if defect=="same-native":ls[0]["native_receipt"]["sha256"]=ds[0]["native_receipt"]["sha256"]
    if defect=="other-source":args["source_sha256"]=h("changed")
    if defect=="different-default":q["literal_rna"]["default_review_sha256"]=h("different basis")
    if defect=="wrong-site-control":
        ds[0]["literal_checks_failed"]=["exact_active_planes"]
        q["literal_rna"]["default_review_sha256"]=_digest(review)
    if defect=="none":
        validate_paired_qualification(q,**args)
    else:
        with pytest.raises(ValueError):validate_paired_qualification(q,**args)

def test_ether_table_selection_cannot_reuse_another_recipe_or_hide_an_unobserved_table():
    from hashlib import sha256
    from nasolve.cif_dictionary_store import same_qualification_permissions
    from nasolve.cif_rna_pucker import ETHER_PUCKER_PERMISSION, literal_tables_match, permitted_pucker_tables
    from nasolve.cif_purine_representation import POLICY_ID as representation

    def pin(modifier):
        return dict(anchor="phenix_installation",size=24,sha256=sha256(modifier.encode()).hexdigest(),
                    path=f"lib/site-packages/chem_data/geostd/rna_dna/mod_{modifier}.cif")

    pins = {m: pin(m) for m in ("rna2p", "rna3p")}
    permission = dict(policy_id=ETHER_PUCKER_PERMISSION, tables=pins)
    def recipe(value):
        return {"bond_representation_policy": representation, "rna_pucker_table": value}
    def mode(**fields):
        return {"default_review_sha256": "0"*64, **fields}

    assert same_qualification_permissions(recipe(permission), recipe(permission))
    assert not same_qualification_permissions(recipe(permission), recipe(pins["rna2p"]))
    assert literal_tables_match(mode(table=pins["rna2p"]), permission)
    assert literal_tables_match(mode(tables={"rna3p": pins["rna3p"]}), permission)
    assert not literal_tables_match(mode(tables={"rna3p": pins["rna2p"]}), permission)
    assert not literal_tables_match(mode(tables={}), permission)
    assert not literal_tables_match(mode(table=pins["rna2p"], tables=pins), permission)
    assert not literal_tables_match(mode(tables=pins), pins["rna2p"])
    with pytest.raises(ValueError, match="both identified"):
        permitted_pucker_tables(dict(permission, tables={"rna2p": pins["rna2p"]}))


@pytest.mark.parametrize("defect", [None, "rename-methyl", "charge", "carbonyl", "missing-H", "bridge", "ethyl"])
def test_methylated_ribose_requires_the_complete_neutral_methoxy_group(defect):
    from pathlib import Path
    from nasolve.cif_stereochemistry_audit import _graph, _values
    from nasolve.postmr_restoration import ribose_methyl_ether
    values = _values(Path(__file__).parent / "fixtures/public_ccd/UY1.cif", "UY1")
    elements, bonds, charges, neighbors = _graph(values)
    methyl, = neighbors["O2'"] - {"C2'"}
    hydrogens = sorted(neighbors[methyl] - {"O2'"})
    if defect == "rename-methyl":
        for key, column in values.items():
            if isinstance(column, list):
                values[key] = ["MEX" if a == methyl else a for a in column]
        elements, bonds, charges, neighbors = _graph(values)
    elif defect == "charge":
        charges[hydrogens[0]] = -1
    elif defect == "carbonyl":
        bonds[tuple(sorted((methyl, "O2'")))] = "DOUBLE"
    elif defect == "missing-H":
        neighbors[methyl].remove(hydrogens[0])
    elif defect in {"bridge", "ethyl"}:
        elements[hydrogens[0]] = "C"
        if defect == "bridge":
            neighbors[hydrogens[0]].add("C4'")
    graph = elements, bonds, charges, neighbors
    if defect in {None, "rename-methyl"}:
        assert ribose_methyl_ether(graph) == ("MEX" if defect else methyl)
    else:
        with pytest.raises(ValueError, match="methyl ether"):
            ribose_methyl_ether(graph)


@pytest.mark.parametrize("modifiers,authorized,projects", [
    (["targeted","rna2p"],True,True), (["targeted"],True,False),
    (["rna2p"],True,False), (["targeted","rna2p","extra"],True,False),
    (["rna2p","targeted"],True,False), (["targeted","rna2p"],False,False),
])
def test_linked_pucker_requires_site_modifier_and_paired_table(tmp_path,modifiers,authorized,projects):
    from hashlib import sha256
    from nasolve.cif_rna_pucker import linked_pucker_expectations
    from nasolve.ligand_profiles import _emit
    from nasolve.cif_linked_preparation import _render
    values,table=_example()
    values.update({'_chem_comp.group':['RNA'],'_chem_comp_atom.comp_id':['TST']*4,
        '_chem_comp_atom.atom_id':['AA','BB','CC','DD'],'_chem_comp_atom.type_symbol':['C']*4})
    path=tmp_path/"projected.cif"; path.write_text(_render(values,"TST"))
    template=tmp_path/"table.cif"; template.write_text(_emit(table))
    pin=dict(anchor="phenix_installation",path="lib/python3.11/site-packages/chem_data/geostd/rna_dna/mod_rna2p.cif",
        size=template.stat().st_size,sha256=sha256(template.read_bytes()).hexdigest())
    site="X:4"; native={"monomer_mappings":{"rows":[{"site":site,"chem_mod_ids":{"status":"RECORDED","ids":modifiers}}]}}
    prepared={"preparation":{"sites":[{"site":site,"modification_id":"targeted"}]},
        "projections":{site:(path,"TST")}, "rna_pucker_tables":{site:(template,pin)} if authorized else {}}
    adjusted=linked_pucker_expectations(prepared,native)
    assert bool(adjusted) is projects
    if projects:
        assert adjusted[site]["matched_rows"]=={"bonds":1,"angles":1,"torsions":1}
        assert adjusted[site]["table_sha256"]==pin["sha256"]
        assert adjusted[site]["values"]["_chem_comp_bond.value_dist"]==["1.53"]
        assert adjusted[site]["values"]["_chem_comp_plane_atom.atom_id"]==["X"]
        raw=template.read_bytes();template.write_bytes(b"X"+raw[1:])
        with pytest.raises(ValueError,match="checksum"):linked_pucker_expectations(prepared,native)


@pytest.mark.parametrize("observed, qualified", [("rna2p", ("rna2p","rna3p")),
    ("rna3p", ("rna2p","rna3p")), ("rna3p", ("rna2p",))])
def test_linked_methyl_ether_uses_only_its_observed_and_verified_table(tmp_path, observed, qualified):
    from hashlib import sha256
    from nasolve.cif_rna_pucker import linked_pucker_expectations
    from nasolve.cif_linked_preparation import _render
    from nasolve.ligand_profiles import _emit

    values, template = _example()
    values.update({"_chem_comp.group":["RNA"], "_chem_comp_atom.comp_id":["TST"]*4,
                   "_chem_comp_atom.atom_id":["AA","BB","CC","DD"], "_chem_comp_atom.type_symbol":["C"]*4})
    projection = tmp_path/"projected.cif"; projection.write_text(_render(values,"TST"))
    permitted = {}
    for modifier in qualified:
        table = deepcopy(template)
        table["data_"] = "mod_"+modifier
        for key in table:
            if key.endswith(".mod_id"):
                table[key] = [modifier]
        table["_chem_mod_bond.new_value_dist"] = ["1.53" if modifier=="rna2p" else "1.51"]
        path = tmp_path/(modifier+".cif"); path.write_text(_emit(table))
        pin = dict(anchor="phenix_installation",size=path.stat().st_size,sha256=sha256(path.read_bytes()).hexdigest(),
                   path=f"lib/site-packages/chem_data/geostd/rna_dna/mod_{modifier}.cif")
        permitted[modifier] = (path,pin)
    site="A:2"; mods=["site-reaction",observed]
    native={"monomer_mappings":{"rows":[{"site":site,"chem_mod_ids":{"status":"RECORDED","ids":mods}}]}}
    prepared={"preparation":{"sites":[{"site":site,"modification_id":"site-reaction"}]},
              "projections":{site:(projection,"TST")}, "rna_pucker_tables":{site:permitted}}
    adjusted=linked_pucker_expectations(prepared,native)
    if observed in permitted:
        entry=adjusted[site]
        assert entry["modifier"]==observed and entry["table_sha256"]==permitted[observed][1]["sha256"]
        assert entry["values"]["_chem_comp_bond.value_dist"]==["1.53" if observed=="rna2p" else "1.51"]
    else:
        assert adjusted=={}


@pytest.mark.parametrize("defect", ["none","dictionary-only","force-only","other-bond","ring-force"])
def test_linked_pucker_checks_definition_and_active_forces_separately(tmp_path,defect):
    from nasolve.cif_linked_control import _heavy_proxy_checks
    from nasolve.cif_linked_preparation import component_values
    from nasolve.cif_terminal_qualification import definition_projection_checks
    from tests.test_cif_linked_control_qualification import case
    _,native,_,_,projection=case(tmp_path)
    values=component_values(projection,"ZZZ")
    values["_chem_comp_bond.type"][0]="coval"
    values["_chem_comp_bond.value_dist"][0]="1.53"
    site="A:2"; files={site:(projection,"ZZZ")}; overlay={site:{"values":values}}
    definition=native["monomer_mappings"]["rows"][1]["metadata"]["effective_definition"]
    forces=native["geometry"]["proxy_details"]
    if defect!="force-only":
        definition["bonds"][0].update(type="coval",value_dist="1.53")
    if defect!="dictionary-only":
        forces["bond_simple"][0]["distance_ideal"]=1.53
    if defect=="other-bond":forces["bond_simple"][1]["distance_ideal"]+=0.1
    if defect=="ring-force":forces["planarity"].append({"i_seqs":[1,2,3,4],"weights":[2500.0]*4})
    compared=definition_projection_checks(native,files,pucker=overlay)
    assert all(r["status"]=="PASS" for r in compared) is (defect!="force-only")
    active=_heavy_proxy_checks(native,projection,"ZZZ",site,minimum_plane_atoms=4,projected_values=values)
    assert all(active.values()) is (defect in {"none","force-only"})
    assert active["exact-heavy-planes"] is (defect!="ring-force")
