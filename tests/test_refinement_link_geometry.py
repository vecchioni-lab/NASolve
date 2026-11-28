"""Phenix can supply genuine backbone and pairing contacts alongside an unwanted bond."""
import json

import pytest

from nasolve.refinement_link_geometry import read_refined_links


def setup_files(root):
    sites = [
        ("A", 1, "DG", "O3'", (0, 0, 0), "O"),
        ("A", 2, "DC", "P", (1.610, 0, 0), "P"),
        ("A", 2, "DC", "N4", (0, 5, 0), "N"),
        ("A", 2, "DC", "N3", (5, 5, 0), "N"),
        ("B", 4, "Z99", "C5T", (0, 6.436, 0), "C"),
        ("B", 4, "Z99", "N2T", (5, 7.800, 0), "N"),
    ]
    lines = [
        f"ATOM  {i:5} {name:>4} {code:>3} {chain}{site:4}    "
        f"{x:8.3f}{y:8.3f}{z:8.3f}{1:6.2f}{30:6.2f}          {element:>2}"
        for i, (chain, site, code, name, (x, y, z), element) in enumerate(sites, 1)
    ]
    model = root / "model.pdb"
    model.write_text("\n".join(lines) + "\nEND\n")
    phil = root / "frame.phil"
    phil.write_text("""refinement {
  pdb_interpretation.secondary_structure {
    enabled = False
  }
  geometry_restraints.edits {
    bond {
      action = add
      atom_selection_1 = chain A and resid 2 and name N3
      atom_selection_2 = chain B and resid 4 and name N2T
      distance_ideal = 2.8
      sigma = 0.4
    }
  }
}
""")
    return model, phil, [f'pdb="{line[12:27]}"' for line in lines]


def bond(labels, i, j, ideal, observed, sigma, weight, image=None):
    header = "ideal model delta sigma weight residual"
    values = f"{ideal} {observed} 0.000 {sigma} {weight} 0.00e+00"
    if image:
        header += " sym.op."
        values += " " + image
    return f"bond {labels[i]}\n     {labels[j]}\n  {header}\n  {values}\n"


def section(origin, *rows):
    return f"Bond | {origin} | restraints: {len(rows)}\nSorted by residual:\n" + "".join(rows) + "\n"


def geometry(root, extra=False):
    model, phil, labels = setup_files(root)
    backbone = bond(labels, 0, 1, "1.607", "1.610", "1.20e-02", "6.94e+03")
    pairing = bond(labels, 5, 3, "2.800", "2.800", "4.00e-01", "6.25e+00")
    auto = bond(labels, 2, 4, "1.430", "1.436", "1.00e-02", "1.00e+04")
    path = root / "final.geo"
    text = section("covalent geometry", backbone) + section("User supplied", pairing)
    path.write_text(text + (section("Misc.", auto) if extra else ""))
    return model, path, labels, dict(preparation_model=model, backbone_links=[("A:1", "A:2")], restraint_phils=[phil])


def test_geometry_declaration_can_match_while_achieved_distances_depart_both_ways(tmp_path):
    model, path, labels, intent = geometry(tmp_path)
    frame, = intent["restraint_phils"]
    first = frame.read_text().replace("distance_ideal = 2.8", "distance_ideal = 2.4")
    second = tmp_path / "second.phil"
    second.write_text(first.replace("name N3", "name N4").replace("name N2T", "name C5T")
                      .replace("distance_ideal = 2.4", "distance_ideal = 1.836").replace("sigma = 0.4", "sigma = 0.2"))
    frame.write_text(first)
    intent["restraint_phils"].append(second)
    backbone = bond(labels, 0, 1, "1.607", "1.610", "1.20e-02", "6.94e+03")
    extended = bond(labels, 5, 3, "2.400", "2.800", "4.00e-01", "6.25e+00")
    compressed = bond(labels, 2, 4, "1.836", "1.436", "2.00e-01", "2.50e+01")
    path.write_text(section("covalent geometry", backbone) + section("User supplied", extended, compressed))
    result = read_refined_links(model, path, **intent)
    fit = result["supplied_distance_fit"]
    assert result["status"] == "MATCH" and fit["count"] == 2 and fit["ambiguous"] == 0
    assert fit["most_compressed"]["signed_widths"] == pytest.approx(-2)
    assert fit["most_extended"]["signed_widths"] == pytest.approx(1)
    assert fit["most_compressed"]["endpoints"] == [["A:2", "DC", "N4"], ["B:4", "Z99", "C5T"]]
    assert fit["most_extended"]["model_A"] == 2.8
    assert read_refined_links(model, path)["supplied_distance_fit"] is None


def test_unexpected_link_named_even_next_to_declared_bonds(tmp_path):
    model, path, _, intent = geometry(tmp_path, extra=True)
    report = read_refined_links(model, path, **intent)
    assert report["status"] == "REVIEW"
    assert report["matched_backbone"] == report["matched_supplied"] == 1
    assert not report["missing_backbone"] and not report["missing_supplied"]
    row, = [r for r in report["links"] if r["classification"] == "OUTSIDE_DECLARATION"]
    assert row["origin"] == "Misc."
    assert row["endpoints"] == [["A:2", "DC", "N4"], ["B:4", "Z99", "C5T"]]
    assert row["target_A"] == 1.430 and row["model_A"] == 1.436


def test_checked_bonds_match_and_without_authority_only_observed(tmp_path):
    model, path, _, intent = geometry(tmp_path)
    report = read_refined_links(model, path, **intent)
    assert report["status"] == "MATCH" and len(report["links"]) == 2
    informal = read_refined_links(model, path)
    assert report["supplied_distance_fit"] == dict(count=1, ambiguous=0, most_compressed=None, most_extended=None)
    assert informal["status"] == "OBSERVED" and informal["matched_supplied"] is None
    assert {r["classification"] for r in informal["links"]} == {"OBSERVED"}


@pytest.mark.parametrize("needle,replacement", [
    ("2.800 2.800", "2.900 2.800"), ("4.00e-01", "2.00e-01"),
    ("6.25e+00", "2.50e+01"), ("User supplied", "Misc."),
])
def test_endpoints_alone_do_not_exempt_an_edit(tmp_path, needle, replacement):
    model, path, _, intent = geometry(tmp_path)
    path.write_text(path.read_text().replace(needle, replacement))
    report = read_refined_links(model, path, **intent)
    assert report["status"] == "REVIEW" and report["matched_supplied"] == 0
    assert len(report["missing_supplied"]) == 1


def test_duplicate_edge_and_missing_backbone_remain_visible(tmp_path):
    model, path, labels, intent = geometry(tmp_path)
    row = bond(labels, 3, 5, "2.800", "2.800", "4.00e-01", "6.25e+00")
    path.write_text(section("User supplied", row, row))
    report = read_refined_links(model, path, **intent)
    assert report["status"] == "REVIEW" and report["matched_supplied"] == 1
    assert len(report["missing_backbone"]) == 1
    assert [r["classification"] for r in report["links"]].count("OUTSIDE_DECLARATION") == 1
    assert report["supplied_distance_fit"] == dict(count=0, ambiguous=1, most_compressed=None, most_extended=None)
    assert json.loads(json.dumps(report)) == report


def test_symmetry_even_between_same_site_atoms_requires_image_authority(tmp_path):
    model, path, labels, intent = geometry(tmp_path)
    path.write_text(path.read_text() + section("Misc.", bond(labels, 1, 1, "1.600", "1.606", "2.00e-02", "2.50e+03", "-x+y,-x,z")))
    report = read_refined_links(model, path, **intent)
    image, = [r for r in report["links"] if r["classification"] == "SYMMETRY_REVIEW"]
    assert image["image_of_second_atom"] == "-x+y,-x,z"
    assert image["endpoints"][0] == image["endpoints"][1]
    assert report["status"] == "REVIEW" and report["matched_backbone"] == 1


@pytest.mark.parametrize("needle,replacement", [
    ("restraints: 1", "restraints: 2"),
    ("1.607 1.610", "1.607 1.650"),
    ("1.20e-02", "nan"),
    ("2.800 2.800", "3 3"),
    ("6.25e+00", "6e+00"),
    ('pdb="   P  DC', 'pdb="   X  DC'),
])
def test_incomplete_or_wrong_model_evidence_cannot_clear(tmp_path, needle, replacement):
    model, path, _, intent = geometry(tmp_path)
    old = path.read_text()
    assert needle in old
    path.write_text(old.replace(needle, replacement))
    with pytest.raises(ValueError):
        read_refined_links(model, path, **intent)


def test_absent_bond_sections_are_unavailable(tmp_path):
    model, path, _, intent = geometry(tmp_path)
    path.write_text("Geometry restraints\nBond angle | covalent geometry | restraints: 0\n")
    report = read_refined_links(model, path, **intent)
    assert report["status"] == "NOT_RECORDED" and report["matched_backbone"] is None


def nonbonded(a, b, actual, vdw, image=None):
    op = " sym.op." if image is not None else ""
    tail = " " + image if image is not None else ""
    return f"nonbonded {a}\n          {b}\n   model   vdw{op}\n   {actual} {vdw}{tail}\n"


def test_contact_environment_keeps_signed_gaps_and_images_of_the_second_atom(tmp_path):
    from nasolve.refinement_contact_geometry import read_refined_contacts

    model, path, labels, _ = geometry(tmp_path)
    local = nonbonded(labels[3], labels[5], "2.800", "2.690")
    mate = nonbonded(labels[4], labels[4], "3.500", "3.800", "x+1,y,z")
    distinct = nonbonded(labels[5], labels[2], "4.200", "4.500", "-x+y,-x,z")
    further_image = nonbonded(labels[3], labels[4], "4.700", "3.300", "x,y+1,z")
    with path.open("a") as fh:
        fh.write("Nonbonded | unspecified | interactions: 4\nSorted by model distance:\n" + local + mate + distinct + further_image)
    result = read_refined_contacts(model, path, ["B:4", "A:2"])
    assert result["status"] == "OBSERVED" and result["sections"] == {"unspecified": 4}
    b = result["sites"]["B:4"]["atoms"]
    assert (b["C5T"]["printed_contacts"], b["C5T"]["shorter_than_vdw"], b["C5T"]["image_contacts"]) == (2, 1, 2)
    assert b["C5T"]["largest_overlap_A"] == .300
    second = b["N2T"]["largest_contacts"][0]
    assert second["endpoints"] == [["B:4", "Z99", "N2T"], ["A:2", "DC", "N4"]]
    assert second["image_of_second_atom"] == "-x+y,-x,z"
    a = result["sites"]["A:2"]["atoms"]
    assert a["N3"]["largest_overlap_A"] == -.110 and a["N3"]["shorter_than_vdw"] == 0
    assert a["N3"]["largest_image_overlap_A"] == -1.4
    assert a["N3"]["largest_image_contacts"][0]["image_of_second_atom"] == "x,y+1,z"
    assert a["P"]["printed_contacts"] == 0 and a["P"]["largest_overlap_A"] is None
    assert result["scientific_approval"] == "NOT_ASSESSED"


def test_contact_cutoff_keeps_weaker_neighbours_once_in_printed_atom_order(tmp_path):
    from nasolve.refinement_contact_geometry import read_refined_contacts

    model, path, labels, _ = geometry(tmp_path)
    pairs = [
        nonbonded(labels[3], labels[5], "2.800", "3.200"),
        nonbonded(labels[5], labels[2], "4.200", "4.800", "-x+y,-x,z"),
        nonbonded(labels[5], labels[4], "3.501", "3.900", "x+1,y,z"),
    ]
    with path.open("a") as f:
        f.write("Nonbonded | unspecified | interactions: 3\n" + "".join(pairs))
    sites = ["A:2", "B:4"]
    old = read_refined_contacts(model, path, sites)
    assert "overlap_screen" not in old
    result = read_refined_contacts(model, path, sites, minimum_overlap=.4)
    assert old["sites"] == result["sites"]
    assert result["sites"]["B:4"]["atoms"]["N2T"]["largest_overlap_A"] == .6
    screen = result["overlap_screen"]
    assert screen["minimum_overlap_A"] == .4
    assert [(r["overlap_A"], r["image_of_second_atom"]) for r in screen["contacts"]] == [
        (.6, "-x+y,-x,z"), (.4, None)]
    assert screen["contacts"][0]["endpoints"] == [["B:4", "Z99", "N2T"], ["A:2", "DC", "N4"]]
    assert screen["contacts"][1]["endpoints"] == [["A:2", "DC", "N3"], ["B:4", "Z99", "N2T"]]
    assert read_refined_contacts(model, path, sites, minimum_overlap=.61)["overlap_screen"]["contacts"] == []

    path.write_text(path.read_text().replace("interactions: 3", "interactions: 4"))
    invalid = read_refined_contacts(model, path, sites, minimum_overlap=.4)
    assert invalid["status"] == "UNASSESSED" and invalid["overlap_screen"]["contacts"] is None
    for cutoff in (float("nan"), float("inf"), -0.1, True):
        with pytest.raises(ValueError, match="overlap"):
            read_refined_contacts(model, path, sites, minimum_overlap=cutoff)


@pytest.mark.parametrize("change", ["missing", "empty", "truncated", "wrong-distance", "wrong-label", "bad-image"])
def test_contact_environment_distinguishes_omitted_empty_and_invalid_tables(tmp_path, change):
    from nasolve.refinement_contact_geometry import read_refined_contacts

    model, path, labels, _ = geometry(tmp_path)
    row = nonbonded(labels[3], labels[5], "2.800", "3.000")
    if change == "wrong-distance":
        row = row.replace("2.800", "1.000")
    elif change == "wrong-label":
        row = row.replace(labels[3], 'pdb=" unknown label"')
    elif change == "bad-image":
        row = nonbonded(labels[5], labels[5], "2.800", "3.000", "unknown")
    if change != "missing":
        count = {"empty": 0, "truncated": 2}.get(change, 1)
        with path.open("a") as fh:
            fh.write(f"Nonbonded | unspecified | interactions: {count}\n" + ("" if change == "empty" else row))
    result = read_refined_contacts(model, path, ["B:4"])
    if change == "empty":
        assert result["status"] == "OBSERVED" and result["sites"]["B:4"]["atoms"]["C5T"]["printed_contacts"] == 0
    else:
        assert result["status"] == ("NOT_RECORDED" if change == "missing" else "UNASSESSED")
        assert result["sites"] is None
    with pytest.raises(ValueError, match="site"):
        read_refined_contacts(model, path, ["A:88"])


def test_verified_parent_pins_bind_the_frame_used_for_comparison(tmp_path, monkeypatch):
    from nasolve.model_assessment import file_sha256
    from nasolve.refinement_link_geometry import read_checkpoint_link_geometry

    model, geo, _, intent = geometry(tmp_path)
    phil, = intent["restraint_phils"]
    files = [{"path": p.name, "sha256": file_sha256(p)} for p in (model, phil)]
    bundle = {"model": model, "report": {"expected_links": intent["backbone_links"],
              "supplementary_phils": [phil.name], "files": files}}
    acquisition = {"bundle": bundle, "bundle_directory": tmp_path}
    monkeypatch.setattr("nasolve.refinement_chemistry._preparation_context",
                        lambda *_: (acquisition, "prepare-003", {}))
    got = read_checkpoint_link_geometry(tmp_path, {}, {}, {}, model, geo)
    assert got["preparation_checkpoint"] == "prepare-003" and got["status"] == "MATCH"
    files[1]["sha256"] = "0"*64
    with pytest.raises(ValueError, match="differ from the checked preparation"):
        read_checkpoint_link_geometry(tmp_path, {}, {}, {}, model, geo)


def test_preflight_uses_the_entrance_model_and_its_sealed_geometry_after_move(tmp_path, monkeypatch):
    from hashlib import sha256
    from pathlib import Path
    import subprocess
    from nasolve.checkpoints import CheckpointError
    from nasolve.cif_doctor_run import assess_run
    from .test_refinement_parallelity import completed

    root = tmp_path / "original"
    root.mkdir()
    original_run = subprocess.run
    def write_distinct_model(command, *args, **kwargs):
        result = original_run(command, *args, **kwargs)
        if Path(command[0]).name == "phenix.refine" and "--dry_run" not in command:
            output = Path(kwargs["cwd"]) / "refined_001.pdb"
            with output.open("a") as handle:
                handle.write("REMARK distinct final model\n")
        return result
    monkeypatch.setattr(subprocess, "run", write_distinct_model)
    run, _, registry, child, _, _ = completed(root, monkeypatch)
    parent = next(row for row in registry["checkpoints"] if row["id"] == child["parent"])
    moved = tmp_path / "moved"
    root.rename(moved)
    run = moved / run.relative_to(root)
    assert not root.exists()
    result = assess_run(run, checkpoint=child["id"], refined_links=True)
    initial = result["preflight_links"]
    assert initial["status"] == "NOT_RECORDED"
    assert initial["model_sha256"] == parent["model"]["sha256"]
    assert initial["model_sha256"] != child["model"]["sha256"]
    assert initial["geometry_sha256"] == sha256(b"preflight geometry preserved").hexdigest()
    assert initial["preparation_checkpoint"] is None
    assert assess_run(run, checkpoint=child["parent"], refined_links=True)["preflight_links"] is None
    sealed = run / "AutoRefine/round_001/parallelity_runtime/preflight/native_001.geo"
    sealed.write_text("changed after admission")
    with pytest.raises((CheckpointError, ValueError), match="checksum|changed|size"):
        assess_run(run, checkpoint=child["id"], refined_links=True)


@pytest.mark.parametrize(("initial", "final", "outcome"), [
    ("extra", "match", "REVIEW"), ("match", "extra", "REVIEW"),
    ("match", "match", "SUCCESS"), ("unknown", "match", "REVIEW"),
])
def test_checked_autorefine_retains_a_model_and_accounts_for_both_native_tables(
        tmp_path, monkeypatch, initial, final, outcome):
    import subprocess
    from pathlib import Path
    from nasolve.model_assessment import file_sha256
    from . import test_refinement_parallelity as harness

    definition = tmp_path / "checked"
    definition.mkdir()
    model, geo, labels, intent = geometry(definition)
    matched = geo.read_bytes()
    unexpected = section("Misc.", bond(labels, 2, 4, "1.430", "1.436", "1.00e-02", "1.00e+04")).encode()
    tables = {"match": matched, "extra": matched + unexpected,
              "unknown": matched.replace(b"1.610", b"6.610")}
    phil, = intent["restraint_phils"]
    report = {"expected_links": intent["backbone_links"], "supplementary_phils": [phil.name],
              "files": [{"path": p.name, "sha256": file_sha256(p)} for p in (model, phil)]}
    acquisition = {"bundle": {"model": model, "report": report}, "bundle_directory": definition}
    monkeypatch.setattr("nasolve.refinement_chemistry._preparation_context",
                        lambda *args: (acquisition, "postmr", {}))
    monkeypatch.setattr("nasolve.refinement_chemistry.prepare_chemistry_scope", lambda *args, **kwargs: [])
    original_inputs = harness.inputs

    def inputs(root):
        run, policy, executable, dump = original_inputs(root)
        source = run / "report.json"
        record = json.loads(source.read_bytes())
        Path(record["postmr"]["prepared_model"]).write_bytes(model.read_bytes())
        record["postmr"]["mutation_actions"] = []
        record["postmr"]["anomalous"]["candidates"] = []
        source.write_text(json.dumps(record))
        return run, policy, executable, dump

    original_run = subprocess.run

    def produce_tables(command, *args, **kwargs):
        result = original_run(command, *args, **kwargs)
        if Path(command[0]).name == "phenix.refine":
            folder = Path(kwargs["cwd"])
            if "--dry_run" in command:
                (folder / "parallelity_runtime/preflight/native_001.geo").write_bytes(tables[initial])
            else:
                (folder / "refined_001_final.geo").write_bytes(tables[final])
        return result

    monkeypatch.setattr(harness, "inputs", inputs)
    monkeypatch.setattr(subprocess, "run", produce_tables)
    run, result, registry, child, _, commands = harness.completed(tmp_path, monkeypatch, declared_sites=True)
    assert commands == ["preflight", "refine"] and child["usable"] and child["status"] == outcome
    assert registry["current"] == (child["id"] if outcome == "SUCCESS" else "postmr")
    saved = json.loads(result.report_path.read_bytes())
    report = saved["statistics"]["inter_residue_bonds"]
    assert report == result.statistics["inter_residue_bonds"]
    assert report["preparation_checkpoint"] == "postmr"
    assert saved["acceptance"]["inter_residue_bond_review"] is (outcome == "REVIEW")
    from nasolve.refine_doctor import _candidate
    ranked = _candidate(child["id"], "test", result.statistics, accepted=outcome == "SUCCESS")
    assert ranked["eligible_for_inspection"] is (outcome == "SUCCESS")
    assert ranked["inter_residue_bond_review"] is (outcome == "REVIEW")
    for stage, test in (("preflight", initial), ("refined", final)):
        result = report[stage]
        assert result["status"] == {"extra": "REVIEW", "match": "MATCH", "unknown": "UNASSESSED"}[test]
        if test == "extra":
            assert result["outside_declaration"] == 1 and result["first_issue"]["endpoints"] == [
                ["A:2", "DC", "N4"], ["B:4", "Z99", "C5T"]]
        if test == "unknown":
            assert "written coordinates" in result["reason"]
        assert "links" not in result

    from nasolve import cif_doctor_run
    from nasolve.checkpoints import CheckpointError

    cold = cif_doctor_run.assess_run(run, checkpoint=child["id"], refined_links=True)
    assert cold["preflight_links"]["status"] == report["preflight"]["status"]
    assert cold["refined_links"]["status"] == report["refined"]["status"]
    assert (cold["refined_links"]["supplied_distance_fit"] is None) is (final == "unknown")
    assert (cold["preflight_links"]["supplied_distance_fit"] is None) is (initial == "unknown")
    if initial == "unknown":
        assert cold["preflight_links"]["reason"] == report["preflight"]["reason"]
    if outcome == "SUCCESS":
        altered = dict(report, requires_review=0)
        original_resolve = cif_doctor_run.resolve_checkpoint
        def changed_summary(registry, checkpoint):
            original = original_resolve(registry, checkpoint)
            return dict(original, metrics=dict(original["metrics"], inter_residue_bonds=altered))
        monkeypatch.setattr(cif_doctor_run, "resolve_checkpoint", changed_summary)
        with pytest.raises(CheckpointError, match="bond summary"):
            cif_doctor_run.assess_run(run, checkpoint=child["id"], refined_links=True)


def test_numerical_ranking_requires_a_boolean_verdict_when_bond_evidence_is_recorded():
    from nasolve.refine_doctor import _candidate
    numerical = {"r_work": .2, "r_free": .23}
    assert _candidate("old", "test", numerical)["eligible_for_inspection"]
    for incomplete in (None, {}, {"requires_review": 0}):
        result = _candidate("new", "test", dict(numerical, inter_residue_bonds=incomplete))
        assert result["inter_residue_bond_review"] and not result["eligible_for_inspection"]
