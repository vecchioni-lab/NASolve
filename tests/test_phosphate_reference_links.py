"""Reference link chemistry comes from intact links with matching local definitions."""
from copy import deepcopy

import pytest


def capture():
    families = ("bond_simple", "bond_asu", "angle", "dihedral", "const_dihedral",
                "chirality", "planarity", "parallelity")
    details = {kind: [] for kind in families}
    mappings, atoms = [], []
    for number in range(1, 7):
        # 1→2 and 3→4 are intact links. The candidate is 5→6.
        code = "X93" if number % 2 else "Y42"
        names = ("C3'", "O3'") if number % 2 else ("P", "OP1")
        identity = dict(altloc="", icode="", model_id="", chain_id="A", resseq=str(number), resname=code)
        definition = dict(atoms=[{"atom_id": n} for n in names], bonds=[], angles=[], torsions=[],
                          chirality=[], plane_atoms=[])
        mappings.append(dict(site=f"A:{number}", resname=code, literal_identity=dict(identity, status="RECORDED"),
                             chem_mod_ids=dict(status="RECORDED", ids=[]),
                             metadata=dict(status="RECORDED", effective_definition=definition)))
        for name in names:
            atoms.append(dict(i_seq=len(atoms), atom_id=name, label=f"{number}/{name}", identity=identity,
                              element=name[0]))
    def term(kind, indices, **params):
        details[kind].append(dict(i_seqs=indices, atoms=[atoms[i]["label"] for i in indices], origin_id=0, **params))
    for i in (0, 4):
        term("bond_simple", [i+1, i+2], distance_ideal=1.61, weight=1000., symmetry_operation=None)
        term("angle", [i+1, i+2, i+3], angle_ideal=108., weight=.1)
        term("dihedral", [i, i+1, i+2, i+3], angle_ideal=170., periodicity=3, weight=.002)
    return dict(atoms=atoms, monomer_mappings=dict(status="RECORDED", rows=mappings), geometry=dict(
        proxy_details=details, proxy_counts={f:len(rows) for f,rows in details.items()},
        proxy_count_status={f:"RECORDED" for f in families if f not in ("bond_simple","bond_asu")}))


def read(native):
    from nasolve.cif_phosphate_reference import reference_link_terms
    return reference_link_terms(native, phosphate="A:6", o3="A:5")


def test_two_intact_references_retain_the_angles_and_signed_torsion():
    native = capture()
    before = deepcopy(native)
    report = read(native)
    assert report["status"] == "AGREEING_REFERENCES"
    group, = report["groups"]
    assert group["links"] == [["A:1","A:2"], ["A:3","A:4"]]
    assert sorted(t["kind"] for t in group["terms"]) == ["angle","bond_simple","dihedral"]
    torsion, = [t for t in group["terms"] if t["kind"] == "dihedral"]
    assert torsion["parameters"]["periodicity"] == 3 and torsion["parameters"]["angle_ideal"] == 170
    assert report["automatic_adoption"] is False and native == before


@pytest.mark.parametrize(("kind", "indices", "origin", "other"), [
    ("bond_simple", (2, 9), 4, ("A:5", "A:2")),   # same O3′, different phosphorus
    ("bond_asu", (5, 10), 0, ("A:3", "A:6")),    # same phosphorus, different O3′
    ("bond_simple", (2, 9), 2, None),               # a recognized hydrogen-bond restraint
    ("bond_simple", (9, 10), 0, None),              # the two requested atoms themselves
    ("bond_asu", (1, 6), 4, None),                  # both endpoints belong elsewhere
])
def test_native_bond_competing_for_one_registered_atom(kind, indices, origin, other):
    native = capture()
    native["restraint_policy"] = {"origin_ids": {"hydrogen bonds": 2}}
    rows = native["geometry"]["proxy_details"]
    extra = dict(rows["bond_simple"][0], i_seqs=list(indices), origin_id=origin,
                 atoms=[native["atoms"][i]["label"] for i in indices],
                 symmetry_operation="x+1,y,z" if kind == "bond_asu" else None)
    rows[kind].append(extra)
    native["geometry"]["proxy_counts"][kind] += 1
    result = read(native)
    if other is None:
        assert result["status"] == "AGREEING_REFERENCES"
        assert "competing_endpoint_bonds" not in result
    else:
        assert result["status"] == "COMPETING_ENDPOINT_BOND"
        assert result["reference_status"] == "AGREEING_REFERENCES"
        assert result["competing_endpoint_bonds"] == [list(other)]
        assert all(site in result["reason"] for site in (*other, "A:5", "A:6"))
        assert result["groups"][0]["links"] == [["A:1", "A:2"], ["A:3", "A:4"]]


def test_incompatible_chemistry_and_competing_targets_stay_distinct():
    native = capture()
    native["geometry"]["proxy_details"]["angle"][1]["angle_ideal"] = 107
    assert read(native)["status"] == "DIFFERENT_REFERENCES"
    native["monomer_mappings"]["rows"][3]["metadata"]["effective_definition"]["atoms"].append({"atom_id":"OP3"})
    report = read(native)
    assert report["status"] == "ONE_REFERENCE" and report["groups"][0]["links"] == [["A:1","A:2"]]
    native["monomer_mappings"]["rows"][1]["chem_mod_ids"]["ids"].append("terminal")
    assert read(native)["status"] == "NO_MATCHING_REFERENCE"


def test_image_bond_and_user_distance_cannot_nominate_an_intact_source():
    native = capture()
    first, second = native["geometry"]["proxy_details"]["bond_simple"]
    first["symmetry_operation"] = "x+1,y,z"
    second["origin_id"] = 4
    assert read(native)["status"] == "NO_MATCHING_REFERENCE"


def test_incomplete_family_and_misbound_atom_label_fail():
    native = capture()
    native["geometry"]["proxy_count_status"]["dihedral"] = "UNSUPPORTED"
    with pytest.raises(ValueError, match="famil"):
        read(native)
    native = capture()
    native["geometry"]["proxy_details"]["angle"][0]["atoms"].reverse()
    with pytest.raises(ValueError, match="labels"):
        read(native)


def test_additional_crosslink_and_missing_torsion_parameter_remain_visible():
    native = capture()
    details = native["geometry"]["proxy_details"]
    details["bond_asu"].append(dict(details["bond_simple"][0], symmetry_operation="x,y+1,z"))
    native["geometry"]["proxy_counts"]["bond_asu"] = 1
    result = read(native)
    assert result["status"] == "ONE_REFERENCE" and result["excluded_multiple_bonds"] == [["A:1","A:2"]]
    del details["dihedral"][1]["periodicity"]
    with pytest.raises(ValueError, match="periodicity"):
        read(native)


@pytest.mark.parametrize("kind", ["bond_simple", "bond_asu"])
@pytest.mark.parametrize("hydrogen_origin, expected", [(None, "ONE_REFERENCE"), (7, "ONE_REFERENCE"), (42, "AGREEING_REFERENCES")])
def test_extra_distance_needs_a_known_hydrogen_bond_origin_to_leave_a_reference_clean(kind, hydrogen_origin, expected):
    native = capture()
    if hydrogen_origin is not None:
        native["restraint_policy"] = {"origin_ids": {"hydrogen bonds": hydrogen_origin}}
    else:
        native["restraint_policy"] = None
    rows = native["geometry"]["proxy_details"]
    extra = dict(rows["bond_simple"][0], origin_id=42, i_seqs=[0, 3],
                 atoms=[native["atoms"][i]["label"] for i in (0, 3)],
                 symmetry_operation="x,y+1,z" if kind == "bond_asu" else None)
    rows[kind].append(extra)
    native["geometry"]["proxy_counts"][kind] += 1
    result = read(native)
    assert result["status"] == expected
    assert result["excluded_multiple_bonds"] == ([] if hydrogen_origin == 42 else [["A:1", "A:2"]])


def test_missing_origin_cannot_identify_a_reference_bond():
    native = capture()
    native["geometry"]["proxy_details"]["bond_simple"][0]["origin_id"] = False
    with pytest.raises(ValueError, match="bond origin"):
        read(native)

def test_written_restraints_use_the_registered_image_and_the_intact_links(tmp_path):
    pytest.importorskip("gemmi")
    from hashlib import sha256
    from nasolve.cif_phosphate_reference import measure_written_phosphate
    from .test_phosphate_restraints import inspection

    row = inspection()
    row.update(cell=[20., 20., 20., 90., 90., 90.], space_group="P 1", o3_image="x-1,y,z")
    row["registered_continuation"]["oxygen_operator_xyz"] = row["o3_image"]
    donor = {"O3'": (1., 0., 0.), "C3'": (1., 1., 0.), "C4'": (1., 1., -1.)}
    acceptor = {"P": (2.5, 0., 0.), "OP1": (3., 1., -.5), "OP2": (2.8, -1., -.3),
                "O5'": (2.5, .6, 1.), "C5'": (3.2, 1., 1.8)}
    links = [(row["o3"][0], row["phosphate"][0]), *row["native_reference_links"]["groups"][0]["links"]]
    lines = ["CRYST1   20.000   20.000   20.000  90.00  90.00  90.00 P 1           1"]
    for i, (left, right) in enumerate(links):
        for site, code, sites in ((left, "RX9", donor), (right, "Q2", acceptor)):
            chain, number = site.split(":")
            for name, (x, y, z) in sites.items():
                if i == 0 and site == left:
                    x += 20.
                if i == 1 and name == "C4'":
                    z *= -1.
                occupancy = 0. if i == 2 and name == "OP2" else 1.
                lines.append(f"ATOM  {len(lines):5} {name:>4} {code:>3} {chain}{int(number):4}    "
                             f"{x:8.3f}{y+i*4:8.3f}{z:8.3f}{occupancy:6.2f}{30:6.2f}          {name[0]:>2}")
    model = tmp_path / "written.pdb"
    model.write_text("\n".join([*lines, "END", ""]))
    digest = sha256(model.read_bytes()).hexdigest()
    report = measure_written_phosphate(model, row, model_sha256=digest)
    assert report["written_model_sha256"] == digest
    terms = {tuple(atom for role, atom in t["atoms"]): t for t in report["terms"]}
    assert len(terms) == 8
    bond = terms["O3'", "P"]
    assert bond["written"]["value"] == pytest.approx(1.5)
    assert bond["written"]["delta_in_widths"] == pytest.approx((1.5 - 1.593) / .02)
    torsion = terms["C4'", "C3'", "O3'", "P"]
    assert torsion["periodicity"] == 2
    assert torsion["written"]["value"] == pytest.approx(90)
    assert torsion["written"]["delta"] == pytest.approx(34)
    peers = torsion["ordinary_links"]
    assert [[t["o3_site"], t["phosphate_site"]] for t in peers] == links[1:]
    assert [t["value"] for t in peers] == pytest.approx([-90, 90])
    assert "periodic_response" not in torsion["written"]
    response = measure_written_phosphate(model, row, model_sha256=digest, torsion_response=True)
    measured = next(t for t in response["terms"] if t["atoms"] == torsion["atoms"])
    for sample in [measured["written"], *measured["ordinary_links"]]:
        observed = sample["periodic_response"]
        assert observed["status"] == "MEASURED"
        assert observed["fraction_of_peak_slope"] == pytest.approx(0.9271838546)
        assert observed["fraction_of_barrier"] == pytest.approx(0.3126967033)
        assert observed["degrees_to_nearest_maximum"] == pytest.approx(56.)
    only_bond, = [t for t in response["terms"] if t["kind"] == "bond_simple"]
    assert "periodic_response" not in only_bond["written"]
    missing = terms["O3'", "P", "OP2"]["ordinary_links"][1]
    assert missing["value"] is None and "OP2" in missing["reason"]
    assert all(t["value"] is not None for t in bond["ordinary_links"])
    collinear = [line[:30] + f"{1.:8.3f}{6.:8.3f}{0.:8.3f}" + line[54:]
                 if line.startswith("ATOM") and line[21] == "K" and line[12:16].strip() == "C4'" else line
                 for line in lines]
    straight = tmp_path / "collinear.pdb"
    straight.write_text("\n".join([*collinear, "END", ""]))
    changed = measure_written_phosphate(straight, row, model_sha256=sha256(straight.read_bytes()).hexdigest(), torsion_response=True)
    undefined = next(t for t in changed["terms"] if t["atoms"] == torsion["atoms"])["ordinary_links"][0]
    assert undefined["value"] is None and "Collinear" in undefined["reason"]
    assert undefined["periodic_response"]["status"] == "UNASSESSED"
    with pytest.raises(ValueError, match="checksum"):
        measure_written_phosphate(model, row, model_sha256="0"*64)
    with pytest.raises(ValueError, match="crystal frame"):
        measure_written_phosphate(model, dict(row, space_group="P -1"), model_sha256=digest)


def test_a_stationary_periodic_torsion_can_be_at_the_minimum_or_the_barrier():
    from nasolve.cif_phosphate_reference import _periodic_response
    for delta, barrier in ((0., 0.), (-60., 1.)):
        sample = dict(value=delta, delta=delta, near_collinear_review=False)
        result = _periodic_response(sample, 3)
        assert result["fraction_of_peak_slope"] == pytest.approx(0, abs=1e-14)
        assert result["fraction_of_barrier"] == pytest.approx(barrier)
    sample["near_collinear_review"] = True
    assert _periodic_response(sample, 3)["status"] == "UNASSESSED"


@pytest.mark.parametrize(("kind", "indices", "native_image", "expected"), [
    ("bond_asu", [10, 9], {"status": "RECORDED", "operator": "-x+y,-x,z"}, None),
    ("bond_asu", [9, 10], {"status": "RECORDED", "operator": "-y,x-y,z"}, None),
    ("bond_asu", [10, 9], {"status": "RECORDED", "operator": "-x+y,-x,z+1"}, "-x+y,-x,z+1"),
    ("bond_asu", [9, 10], {"status": "RECORDED", "operator": "-x+y,-x,z"}, "-y,x-y,z"),
    ("bond_simple", [9, 10], None, "x,y,z"),
    ("bond_asu", [10, 9], {"status": "UNSUPPORTED"}, "unresolved"),
])
def test_compare_the_same_phosphate_atoms_in_the_actual_native_image(kind, indices, native_image, expected):
    pytest.importorskip("gemmi")
    from nasolve.cif_phosphate_reference import reference_link_terms
    native = capture()
    details = native["geometry"]["proxy_details"]
    extra = dict(details["bond_simple"][0], i_seqs=indices, origin_id=4,
                 atoms=[native["atoms"][i]["label"] for i in indices], symmetry_operation=native_image)
    details[kind].append(extra)
    native["geometry"]["proxy_counts"][kind] += 1
    old = read(native)
    actual = reference_link_terms(native, phosphate="A:6", o3="A:5", o3_image="-x+y,-x,z")
    assert actual["groups"] == old["groups"] and old["status"] == "AGREEING_REFERENCES"
    if expected is None:
        assert actual == old
    elif expected == "unresolved":
        assert actual["status"] == "UNRESOLVED_ENDPOINT_IMAGE" and "unresolved" in actual["reason"].lower()
    else:
        assert actual["status"] == "COMPETING_ENDPOINT_BOND"
        assert actual["existing_o3_images"] == [expected] and actual["requested_o3_image"] == "-x+y,-x,z"
        assert expected in actual["reason"]
    extra["origin_id"] = 2
    native["restraint_policy"] = {"origin_ids": {"hydrogen bonds": 2}}
    assert reference_link_terms(native, phosphate="A:6", o3="A:5", o3_image="-x+y,-x,z") == read(native)
