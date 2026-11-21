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
