"""Inspect the covalent targets Phenix printed at exact sites of a written model."""
import json

from nasolve.cli import main
from nasolve.model_assessment import file_sha256
from .test_checkpoints import make_checkpoint_run
from .test_cif_doctor_run import _child, _reference, _snapshot
from .test_refinement_component_bonds import inputs


def with_angle(directory):
    _, model, geo = inputs(directory)
    labels = [f'pdb="{line[12:27]}"' for line in model.read_text().splitlines() if line.startswith("ATOM")]
    angle = (f"Bond angle | covalent geometry | restraints: 1\nSorted by residual:\nangle {labels[0]}\n"
             f"      {labels[1]}\n      {labels[2]}\n ideal model delta sigma weight residual\n"
             " 108.00 90.00 18.00 2.00e+00 2.50e-01 81.0\n")
    geo.write_text(geo.read_text() + angle)
    return model, geo


def command(model, geo, *sites):
    return ["cif-doctor", "residue-geometry", str(model), "--geometry", str(geo),
            *(v for site in sites for v in ("--site", site)), "--json"]


def test_final_coordinates_are_scored_against_their_native_targets(tmp_path, capsys):
    model, geo = with_angle(tmp_path)
    original = _snapshot(tmp_path)
    assert main(command(model, geo, "B:4")) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "OBSERVED"
    assert (report["model_sha256"], report["geometry_sha256"]) == (file_sha256(model), file_sha256(geo))
    site, = report["sites"]
    assert (site["site"], site["component"]) == ("B:4", "X")
    bonds, angles = site["bonds"], site["angles"]
    assert len(bonds["rows"]) == 3 and len(angles["rows"]) == 1
    first = bonds["rows"][0]
    assert first["origin"] == "User supplied" and abs(first["signed_widths"] + 12.7) < 1e-9
    assert angles["rows"][0]["signed_widths"] == -9 and angles["rows"][0]["measured"] == 90
    assert _snapshot(tmp_path) == original


def test_absent_sections_stale_geometry_and_other_images_are_visible(tmp_path, capsys):
    model, geo = with_angle(tmp_path)
    good = geo.read_text()
    original = good.split("Bond angle |")[0]
    for altered, status in ((original, "NOT_RECORDED"), (good.replace("108.00 90.00", "108.00 91.00"), "UNASSESSED"),
                            (good.replace("Bond angle | covalent geometry | restraints: 1",
                                          "Bond angle | covalent geometry | restraints: 2"), "UNASSESSED")):
        geo.write_text(altered)
        assert main(command(model, geo, "B:4")) == 2
        site, = json.loads(capsys.readouterr().out)["sites"]
        assert site["angles"]["status"] == status and site["bonds"]["status"] == "OBSERVED"
        assert site["angles"]["rows"] is None
    rows = good.splitlines()
    i = next(i for i, line in enumerate(rows) if line.startswith("angle "))
    rows[i] += " -x,-y,z"
    geo.write_text("\n".join(rows) + "\n")
    assert main(command(model, geo, "B:4")) == 2
    section = json.loads(capsys.readouterr().out)["sites"][0]["angles"]
    assert section["status"] == "NO_SAME_IMAGE_ROWS" and section["other_image_count"] == 1
    assert section["rows"] == []


def test_unprinted_missing_or_ambiguous_sites_are_distinct(tmp_path, capsys):
    model, geo = with_angle(tmp_path)
    for sites, message in ((("A:2",), "absent"), (("B:4", "B:4"), "distinct")):
        assert main(command(model, geo, *sites)) == 1
        assert message in capsys.readouterr().err
    geo.write_text("# no printed geometry\n")
    assert main(command(model, geo, "B:4")) == 2
    assert json.loads(capsys.readouterr().out)["sites"][0]["bonds"]["rows"] is None


def test_checkpoint_uses_only_its_own_checked_geometry_after_relocation(tmp_path, capsys):
    original = tmp_path / "original"
    run = make_checkpoint_run(original)
    model, geo = with_angle(tmp_path)
    pdb = run / "PostMR/Model/readyset_model.pdb"
    pdb.write_bytes(model.read_bytes())
    report_path = run / "report.json"
    report = json.loads(report_path.read_bytes())
    report["postmr"]["prepared_sha256"] = file_sha256(pdb)
    report_path.write_text(json.dumps(report))
    _child(run)
    registry_path = run / "AutoRefine/checkpoints.json"
    registry = json.loads(registry_path.read_bytes())
    registry["current"] = "postmr"
    child = registry["checkpoints"][-1]
    final = (run / child["model"]["relative_path"]).with_suffix(".geo")
    final.write_bytes(geo.read_bytes())
    child.update(kind="refinement", outputs={"final_geometry": _reference(final, run)})
    registry_path.write_text(json.dumps(registry))
    shifted = tmp_path / "relocated"
    original.rename(shifted)
    run = shifted / run.relative_to(original)
    args = ["cif-doctor", "residue-geometry", str(run), "--site", "B:4", "--json"]
    before = _snapshot(shifted)
    assert main(args) == 1 and "checkpoint" in capsys.readouterr().err
    assert main([*args, "--checkpoint", "postmr"]) == 2
    missing = json.loads(capsys.readouterr().out)
    assert missing["status"] == "NOT_RECORDED" and missing["geometry_sha256"] is None
    args.extend(["--checkpoint", "first-refinement"])
    assert main(args) == 0
    read = json.loads(capsys.readouterr().out)
    assert read["checkpoint"]["id"] == child["id"] and read["geometry_sha256"] == file_sha256(geo)
    assert main([*args, "--geometry", str(geo)]) == 1 and "recorded" in capsys.readouterr().err
    assert _snapshot(shifted) == before
    assert main([*args, "--reference-checkpoint", "first-refinement"]) == 0
    same = json.loads(capsys.readouterr().out)
    assert same["reference"]["checkpoint"]["id"] == same["current"]["checkpoint"]["id"] == child["id"]
    assert same["matched"] == {"angles": 1, "bonds": 3} and not same["changes"]
    assert main([*args, "--reference-checkpoint", "postmr"]) == 2
    partial = json.loads(capsys.readouterr().out)
    assert partial["reference"]["geometry_sha256"] is None and partial["status"] == "PARTIAL"
    assert _snapshot(shifted) == before
    tampered = run / child["outputs"]["final_geometry"]["relative_path"]
    tampered.write_bytes(tampered.read_bytes() + b"\n")
    assert main(args) == 1 and "changed after it was frozen" in capsys.readouterr().err


def test_whole_model_includes_partial_sites_and_single_atom_metals(tmp_path, capsys):
    model, geo = with_angle(tmp_path)
    lines = model.read_text().splitlines()
    metal = "HETATM   80   AG  AG M  40       9.000  10.000  11.000  1.00 20.00          AG"
    missing = [line[:21] + "K" + line[22:] for line in lines if line.startswith("ATOM")]
    model.write_text("\n".join([*lines[:-1], *missing, metal, "END"]) + "\n")
    args = ["cif-doctor", "residue-geometry", str(model), "--geometry", str(geo), "--all-sites"]
    assert main([*args, "--json"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["site_selection"] == "all_model_sites"
    sites = {r["site"]: r for r in report["sites"]}
    assert list(sites) == ["B:4", "K:4", "M:40"]
    assert sites["K:4"]["bonds"]["status"] == "NO_SITE_ROWS"
    assert sites["M:40"]["bonds"]["status"] == sites["M:40"]["angles"]["status"] == "TOO_FEW_ATOMS"
    assert report["coverage"]["angles"] == {"OBSERVED": 1, "NO_SITE_ROWS": 1, "TOO_FEW_ATOMS": 1}
    assert main(args) == 2
    human = capsys.readouterr().out
    assert "B:4" in human and "K:4" in human and "User supplied" in human
    model.write_text("\n".join([*lines[:-1], metal, "END"]) + "\n")
    assert main([*args, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["coverage"]["bonds"] == {"OBSERVED": 1, "TOO_FEW_ATOMS": 1}


def test_same_image_angles_and_bond_slack_remain_interpretable(tmp_path, capsys):
    model, geo = with_angle(tmp_path)
    lines = geo.read_text().splitlines()
    k = next(i for i, line in enumerate(lines) if line.startswith("angle "))
    for i in range(k, k + 3):
        lines[i] += " -x,-y,z"
    i = next(i for i, line in enumerate(lines) if line.split()[:2] == ["ideal", "model"])
    fields, values = lines[i].split(), lines[i+1].split()
    fields.insert(2, "slack")
    values.insert(2, "0.080")
    lines[i], lines[i+1] = " ".join(fields), " ".join(values)
    geo.write_text("\n".join(lines) + "\n")
    assert main(command(model, geo, "B:4")) == 0
    site = json.loads(capsys.readouterr().out)["sites"][0]
    assert site["angles"]["rows"][0]["measured"] == 90 and site["angles"]["other_image_count"] == 0
    edited = site["bonds"]["rows"][0]
    assert edited["slack"] == .08 and abs(edited["signed_widths"] + 12.7) < 1e-9


def test_unweighted_printed_angle_is_visible_in_the_human_reading(tmp_path, capsys):
    model, geo = with_angle(tmp_path)
    geo.write_text(geo.read_text().replace("2.50e-01 81.0", "0.00e+00 0.0"))
    assert main(command(model, geo, "B:4")[:-1]) == 0
    assert "zero weight" in capsys.readouterr().out
