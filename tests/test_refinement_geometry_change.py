"""Tell a change of coordinates from a change of Phenix's chemical target."""
import json

from nasolve.cli import main
from nasolve.model_assessment import file_sha256
from .test_cif_doctor_run import _snapshot
from .test_refinement_residue_geometry import command, with_angle


def reference_comparison(directory):
    reference, ref_geo = with_angle(directory)
    model = directory / "refined.pdb"
    lines = reference.read_text().splitlines()
    for n in (2, 3):
        lines[n] = lines[n][:30] + f"{1.728:8.3f}{1.408:8.3f}" + lines[n][46:]
    model.write_text("\n".join(lines) + "\n")
    final = directory / "refined.geo"
    text = ref_geo.read_text().replace("108.00 90.00", "108.00 99.99")
    # Phenix can print the same angle with its endpoints reversed.
    rows = text.splitlines()
    i = next(i for i, line in enumerate(rows) if line.startswith("angle "))
    rows[i], rows[i + 2] = "angle " + rows[i + 2].strip(), "      " + rows[i][6:]
    final.write_text("\n".join(rows) + "\n")
    args = command(model, final, "B:4") + ["--reference-pdb", str(reference), "--reference-geometry", str(ref_geo)]
    return args, reference, ref_geo, model, final


def test_same_angle_reversed_in_print_does_not_look_like_new_chemistry(tmp_path, capsys):
    args, ref, ref_geo, model, final = reference_comparison(tmp_path)
    before = _snapshot(tmp_path)
    assert main(args) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["status"] == "OBSERVED" and d["matched"] == {"bonds": 3, "angles": 1}
    assert d["reference"]["model_sha256"] == file_sha256(ref) and d["reference"]["geometry_sha256"] == file_sha256(ref_geo)
    assert d["current"]["model_sha256"] == file_sha256(model) and d["current"]["geometry_sha256"] == file_sha256(final)
    row, = (r for r in d["changes"] if r["kind"] == "angles")
    assert row["reference"] == 90.0 and 99.98 < row["current"] < 100.01
    assert -5.01 < row["change_in_absolute_widths"] < -4.98 and not d["unmatched"]
    assert main([a for a in args if a != "--json"]) == 0
    assert "toward" in capsys.readouterr().out.lower() and _snapshot(tmp_path) == before


def test_target_or_weight_change_is_explained_without_scoring_it_as_motion(tmp_path, capsys):
    args, _, _, _, final = reference_comparison(tmp_path)
    final.write_text(final.read_text().replace("108.00 99.99", "100.00 99.99")
                     .replace("1.00e-02 1.00e+04", "2.00e-02 2.50e+03"))
    assert main(args) == 2
    d = json.loads(capsys.readouterr().out)
    assert d["matched"] == {"angles": 0, "bonds": 2}
    assert {r["status"] for r in d["unmatched"]} == {"CHANGED_RESTRAINT"}
    e, = (r for r in d["unmatched"] if r["kind"] == "angles")
    assert e["reference"][0]["target"] == 108 and e["current"][0]["target"] == 100
    assert all(r["kind"] != "angles" for r in d["changes"])


def test_reference_arguments_are_paired_and_stale_geometry_never_looks_clean(tmp_path, capsys):
    args, _, _, _, final = reference_comparison(tmp_path)
    assert main(args[:-2]) == 1 and "reference" in capsys.readouterr().err.lower()
    final.write_text(final.read_text().replace("108.00 99.99", "108.00 60.00"))
    assert main(args) == 2
    d = json.loads(capsys.readouterr().out)
    assert d["matched"]["angles"] == 0
    assert any(r.get("current_status") == "UNASSESSED" for r in d["unmatched"])



def test_missing_sites_changed_components_and_ambiguous_terms_are_named(tmp_path):
    from copy import deepcopy
    from nasolve.refinement_geometry_change import geometry_change
    from nasolve.refinement_residue_geometry import inspect_residue_geometry

    model, geo = with_angle(tmp_path)
    one = inspect_residue_geometry(model, None, geometry=geo)
    two = deepcopy(one)
    bonds = two["sites"][0]["bonds"]["rows"]
    bonds.pop()
    bonds.append(deepcopy(bonds[0]))
    two["sites"][0]["angles"]["other_image_count"] = 1
    extra = dict(deepcopy(two["sites"][0]), site="K:7")
    two["sites"].append(extra)
    d = geometry_change(one, two)
    assert d["status"] == "PARTIAL" and d["matched"] == {"bonds": 1, "angles": 1}
    assert {r["status"] for r in d["unmatched"]} == {"AMBIGUOUS_RESTRAINT", "REMOVED_RESTRAINT", "SITE_CHANGED"}
    assert d["other_image_rows"] == [dict(site="B:4", component="X", kind="angles", reference=0, current=1)]
    rev = geometry_change(two, one)
    assert any(row["status"] == "ADDED_RESTRAINT" for row in rev["unmatched"])
    extra["site"] = "B:5"
    two["sites"][0]["component"] = "Y"
    d = geometry_change(one, two)
    assert not sum(d["matched"].values())
    assert {r["site"] for r in d["unmatched"]} == {"B:4", "B:5"}
