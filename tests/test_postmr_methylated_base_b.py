"""A fresh, source-verified base can start at the scale of its own MR site."""
import shutil

import pytest

from nasolve.postmr import MutationAction, construct_postmr_model
from tests.test_postmr_ribose_parent import PUBLIC, SOURCE, TEMPLATE, frame


@pytest.mark.parametrize("condition,reason", [
    ("ordinary", None),
    ("occupancy", "occupancy"),
    ("nonuniform_seed", "atom-specific"),
    ("zero_host_b", "isotropic B"),
])
def test_construction_initializes_only_the_graph_matched_base(tmp_path, monkeypatch, condition, reason):
    model = tmp_path / "host.pdb"
    original = frame()
    if condition == "zero_host_b":
        original = b"".join(line[:60] + b"  0.00" + line[66:]
                            if line[12:16].strip() == b"N2" else line
                            for line in original.splitlines(keepends=True))
    model.write_bytes(original)
    action = MutationAction("A:1", "DG", "2MG", "coot-parent-overlap", parent_code="G")

    def coot(seed, raw, actions, executable, directory, environment, dictionaries, parents, **options):
        parents["A:1"].write_bytes(seed.read_bytes())
        rows = []
        for line in seed.read_text().splitlines(keepends=True):
            if line.startswith("ATOM") and line[21] == "A":
                line = line[:17] + "2MG" + line[20:60] + " 20.00" + line[66:]
                if line[12:16].strip() == "N2":
                    methyl = line[:6] + "  810 " + " CM2" + line[16:]
                    methyl = methyl[:76] + " C" + methyl[78:]
                    if condition == "occupancy":
                        methyl = methyl[:54] + "  0.25" + methyl[60:]
                    if condition == "nonuniform_seed":
                        methyl = methyl[:60] + " 37.50" + methyl[66:]
                    rows.append(methyl)
            rows.append(line)
        raw.write_text("".join(rows))
        return raw, directory / "coot.log"

    monkeypatch.setattr("nasolve.postmr._run_coot", coot)
    options = dict(coot_executable=tmp_path / "coot", inherit_scaffold_b=True,
                   canonical_seed_dictionaries={"A:1": (SOURCE, TEMPLATE)})

    from nasolve.postmr_lineage import begin_postmr_construction, finish_postmr_construction, read_postmr_construction

    def build(folder, **extra):
        run = tmp_path / folder
        models = run / "PostMR/Model"
        coot_dir = run / "PostMR/Coot"
        models.mkdir(parents=True)
        dictionary = coot_dir / "source_dictionaries/2MG.cif"
        dictionary.parent.mkdir(parents=True)
        shutil.copyfile(PUBLIC / "2MG.cif", dictionary)
        source = models / "mr_solution.pdb"
        shutil.copyfile(model, source)
        inputs = {"2MG": dictionary}
        started = begin_postmr_construction(run, source, source, inputs, (action,))
        result = construct_postmr_model(source, (action,), inputs, models / "after_coot.pdb",
                                        coot_directory=coot_dir, **options, **extra)
        prepared = models / "prepared_model.pdb"
        shutil.copyfile(result["model"], prepared)
        finish_postmr_construction(run, started, prepared, result)
        return result

    control = build("old")
    trial = build("new", initialize_methylated_base_b=True)
    site = trial["coordinate_restoration"]["A:1"]
    proof = site["base_displacement"]
    old = control["model"].read_text().splitlines(keepends=True)
    new = trial["model"].read_text().splitlines(keepends=True)
    (tmp_path / "new").rename(tmp_path / "relocated")
    assert read_postmr_construction(tmp_path / "old")["report"]["schema_version"] == 1
    reopened = read_postmr_construction(tmp_path / "relocated")["report"]
    assert reopened["schema_version"] == 2 and reopened["base_displacement"] == {"A:1": proof}
    assert len(old) == len(new)
    assert model.read_bytes() == original
    assert "base_displacement" not in control["coordinate_restoration"]["A:1"]
    if reason:
        assert proof["status"] == "RETAINED_SEED" and reason in proof["reason"]
        assert old == new
        return
    assert proof["status"] == "INITIALIZED_FROM_HOST"
    assert (proof["added_atom"], proof["attachment_atom"]) == ("CM2", "N2")
    assert all(a[:60] + a[66:] == b[:60] + b[66:] for a, b in zip(old, new, strict=True))
    source = {l[12:16].strip(): l[60:66] for l in model.read_text().splitlines() if l.startswith("ATOM") and l[21] == "A"}
    changed = set()
    for a, b in zip(old, new, strict=True):
        if a != b:
            name = b[12:16].strip()
            assert b[21] == "A" and a[60:66] == " 20.00"
            assert b[60:66] == source["N2" if name == "CM2" else name]
            changed.add(name)
    assert changed == set(site["fragment_atoms"]) and len(changed) == 12

    from nasolve.campaign_records import write_record
    from nasolve.postmr_lineage import RECORD_PATH
    reopened.pop("record_sha256")
    reopened["base_displacement"]["A:1"]["starting_b"]["CM2"] += 1
    write_record(tmp_path / "relocated" / RECORD_PATH, reopened, replace=True)
    with pytest.raises(ValueError, match="Base displacement decision"):
        read_postmr_construction(tmp_path / "relocated")


@pytest.mark.parametrize("defect", ["unchanged", "different_charge", "changed_bond", "lost_hydrogen", "isotope"])
def test_source_mapping_requires_only_one_hydrogen_replaced_by_methyl(tmp_path, defect):
    from nasolve.cif_stereochemistry_audit import _values
    from nasolve.ligand_profiles import _emit
    from nasolve.model_assessment import file_sha256
    from nasolve.postmr_base_displacement import _methyl_mapping, _read_base

    values = _values(PUBLIC / "2MG.cif", "2MG")
    # A different component code follows the same chemical rule.
    for tag in values:
        if tag == "_chem_comp.id" or tag.endswith(".comp_id"):
            values[tag] = ["Z9G"] * len(values[tag])
    atoms = values["_chem_comp_atom.atom_id"]
    if defect == "different_charge":
        values["_chem_comp_atom.charge"][atoms.index("N3")] = "1"
    if defect == "changed_bond":
        edges = list(zip(values["_chem_comp_bond.atom_id_1"], values["_chem_comp_bond.atom_id_2"]))
        i = next(i for i, e in enumerate(edges) if set(e) == {"N3", "C4"})
        values["_chem_comp_bond.value_order"][i] = "DOUB"
    if defect == "lost_hydrogen":
        values["_chem_comp_atom.type_symbol"][atoms.index("HM21")] = "F"
    if defect == "isotope":
        values["_chem_comp_atom.pdbx_mass_number"] = [("13" if n == "CM2" else ".") for n in atoms]
    target = tmp_path / "new.cif"
    target.write_text(_emit(values))
    host = _read_base(TEMPLATE, "G", "N9", file_sha256(TEMPLATE))
    if defect == "unchanged":
        new = _read_base(target, "Z9G", "N9", file_sha256(target))
        assert _methyl_mapping(host, new) == ("CM2", "N2", [])
    else:
        with pytest.raises(ValueError):
            _methyl_mapping(host, _read_base(target, "Z9G", "N9", file_sha256(target)))


def test_alternate_six_ring_requires_both_sources_and_conserved_valence():
    from collections import Counter
    from dataclasses import replace
    from nasolve.postmr_base_displacement import _Base, _shared_bond_orders

    names = list("ABCDEF")
    edges = [tuple(sorted((a, b))) for a, b in zip(names, names[1:] + names[:1])]
    bonds = {edge: ("DOUBLE" if i % 2 else "SINGLE") for i, edge in enumerate(edges)}
    host = _Base(dict.fromkeys(names, "C"), Counter(), bonds, set(edges))
    opposite = {edge: ("SINGLE" if order == "DOUBLE" else "DOUBLE") for edge, order in bonds.items()}
    alternative = replace(host, bonds=opposite)
    assert _shared_bond_orders(host, alternative) == [list(edge) for edge in sorted(edges)]
    with pytest.raises(ValueError, match="aromatic"):
        _shared_bond_orders(host, replace(alternative, aromatic_edges=set(edges[1:])))
    with pytest.raises(ValueError):
        _shared_bond_orders(host, replace(alternative, bonds={**opposite, edges[0]: bonds[edges[0]]}))
