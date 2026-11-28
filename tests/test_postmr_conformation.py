"""Native-free ordinary construction conformation contracts."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import traceback

import pytest

from nasolve.postmr import MutationAction, PostMRPreparationError, _coot_script, _run_coot

SOURCE = Path(__file__).parent / "fixtures/public_ccd/PDU.cif"


class CootDouble:
    def __init__(self, code="PDU", expected=-150., after=None):
        self.code = code
        self.expected = expected
        self.chi = 53.
        self.after = expected if after is None else after
        self.overlap_chi = []
        self.matches = []
        self.measurement = None
        self.parent_code = "DG"

    def read_cif_dictionary(self, path):
        return 1

    def handle_read_draw_molecule(self, path):
        return 0

    def mutate_base(self, *args):
        self.parent_code = args[-1]
        return 1

    def write_pdb_file(self, imol, path):
        Path(path).write_text("END\n")

    def get_monomer_from_dictionary(self, code, flag):
        assert code == self.code
        return 1

    def get_torsion_py(self, imol, *specs):
        assert [s[3] for s in specs] == [" O4'", " C1'", " N1 ", " C2 "]
        if self.measurement is not None:
            return self.measurement
        return self.expected if imol == 0 else self.chi

    def match_ligand_torsions(self, ligand, parent, chain, resid):
        self.matches.append((ligand, parent, chain, resid))
        self.chi = self.after

    def overlap_ligands_py(self, *args):
        self.overlap_chi.append(self.chi)
        return True

    def add_ligand_delete_residue_copy_molecule(self, *args):
        return 2

    def residue_name(self, imol, *args):
        return self.parent_code if imol == 0 else self.code

    def delete_hydrogen_atoms(self, *args):
        return 0

    def coot_no_state_real_exit(self, status):
        assert status == 0


def case(tmp_path, monkeypatch, *, code="PDU", fake=None):
    fake = fake or CootDouble(code)
    monkeypatch.setitem(sys.modules, "coot", fake)
    def run(command, **kwargs):
        capture = StringIO()
        with redirect_stdout(capture):
            try:
                exec(compile(Path(command[-1]).read_text(), command[-1], "exec"), {})
            except Exception:
                traceback.print_exc(file=capture)
                return subprocess.CompletedProcess(command, 1, capture.getvalue())
        return subprocess.CompletedProcess(command, 0, capture.getvalue())
    monkeypatch.setattr("nasolve.postmr.subprocess.run", run)
    source = tmp_path / (code + ".cif")
    source.write_text(SOURCE.read_text().replace("PDU", code))
    model = tmp_path / "input.pdb"
    model.write_text("END\n")
    output = tmp_path / "output.pdb"
    directory = tmp_path / "Coot"
    directory.mkdir()
    action = MutationAction("A:12", "DC", code, "coot-parent-overlap", "DT")
    parents = {"A:12": directory / "parent_A_12_DT.pdb"}
    args = (model, output, (action,), tmp_path / "coot", directory, None,
            {code: source}, parents)
    return fake, args


@pytest.mark.parametrize("code", ["PDU", "ZZZ"])
def test_ordinary_overlap_preserves_parent_chi_before_fitting(tmp_path, monkeypatch, code):
    fake, args = case(tmp_path, monkeypatch, code=code)
    before = args[6][code].read_bytes()
    _run_coot(*args)
    assert fake.overlap_chi == [fake.expected]
    assert fake.matches == [(1, 0, "A", 12)]
    assert args[6][code].read_bytes() == before


@pytest.mark.parametrize("expected,after", [(0., 0.), (179.99, -180.01), (-179.99, 180.01)])
def test_native_chi_readback_accepts_zero_and_wrapped_equivalence(tmp_path, monkeypatch, expected, after):
    fake, args = case(tmp_path, monkeypatch, fake=CootDouble(expected=expected, after=after))
    _run_coot(*args)
    assert fake.overlap_chi == [after]


@pytest.mark.parametrize("capability", ["match_ligand_torsions", "get_torsion_py"])
def test_missing_native_conformation_capability_refuses_without_output(tmp_path, monkeypatch, capability):
    fake, args = case(tmp_path, monkeypatch)
    setattr(fake, capability, None)
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    assert not args[1].exists() and not fake.overlap_chi
    assert "Coot lacks" in (args[4] / "coot.log").read_text()


@pytest.mark.parametrize("value", [False, True, None, float("nan"), float("inf"), -float("inf"), [53.]])
def test_missing_or_nonfinite_native_measurement_never_counts_as_an_angle(tmp_path, monkeypatch, value):
    fake, args = case(tmp_path, monkeypatch)
    fake.get_torsion_py = lambda *a: value
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    assert not args[1].exists() and not fake.overlap_chi
    assert "could not measure" in (args[4] / "coot.log").read_text()


def test_unsuccessful_native_match_is_not_silently_accepted(tmp_path, monkeypatch):
    fake, args = case(tmp_path, monkeypatch, fake=CootDouble(after=53.))
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    assert fake.matches and not fake.overlap_chi and not args[1].exists()
    assert "did not preserve" in (args[4] / "coot.log").read_text()


def test_conformation_is_checked_again_after_overlap(tmp_path, monkeypatch):
    fake, args = case(tmp_path, monkeypatch)
    original = fake.overlap_ligands_py
    def damaged(*a):
        result = original(*a)
        fake.chi = 53.
        return result
    fake.overlap_ligands_py = damaged
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    assert fake.overlap_chi == [-150.] and not args[1].exists()
    assert "overlapped -150.0 53.0" in (args[4] / "coot.log").read_text()


@pytest.mark.parametrize("defect", ["renamed_anchor", "rna", "wrong_parent", "missing_source"])
def test_unsupported_graph_keeps_explicit_unassessed_legacy_behavior(tmp_path, monkeypatch, defect):
    fake, args = case(tmp_path, monkeypatch)
    source = args[6]["PDU"]
    if defect == "renamed_anchor":
        source.write_text(source.read_text().replace("N1", "NX"))
    elif defect == "rna":
        source.write_text(source.read_text().replace("DNA linking", "RNA linking"))
    elif defect == "wrong_parent":
        args = (*args[:2], (MutationAction("A:12", "DG", "PDU", "coot-parent-overlap", "DG"),), *args[3:])
    else:
        source.unlink()
    fake.match_ligand_torsions = None
    fake.get_torsion_py = None
    _run_coot(*args)
    assert fake.overlap_chi == [53.] and not fake.matches
    assert "NASOLVE_PARENT_CHI_UNASSESSED" in (args[4] / "coot.log").read_text()


def test_direct_canonical_mutation_needs_no_new_native_capabilities(tmp_path, monkeypatch):
    fake, args = case(tmp_path, monkeypatch)
    args = (*args[:2], (MutationAction("A:12", "DC", "DT", "coot-mutate-base"),), *args[3:6], {}, {})
    fake.match_ligand_torsions = None
    fake.get_torsion_py = None
    _run_coot(*args)
    assert args[1].exists() and not fake.matches and not fake.overlap_chi


def test_legacy_script_generation_does_not_reinterpret_historical_construction(tmp_path, monkeypatch):
    fake, args = case(tmp_path, monkeypatch)
    fake.match_ligand_torsions = None
    fake.get_torsion_py = None
    text = _coot_script(args[0], args[1], args[2], args[6], args[7])
    assert "nasolve_chi" not in text and "NASOLVE_PARENT_CHI" not in text
    exec(compile(text, "historical-script", "exec"), {})
    assert fake.overlap_chi == [53.]


@pytest.mark.parametrize("component,parent,anchor,last", [
    ("PDU", "DT", "N1", "C2"), ("5PC", "DC", "N1", "C2"),
    ("DP", "DG", "N9", "C4"),
])
def test_planning_uses_source_graphs_for_multiple_base_families(component, parent, anchor, last):
    from nasolve.postmr_conformation import parent_conformation_plan
    path = SOURCE.with_name(component + ".cif")
    if not path.is_file():
        path = Path(__file__).parents[1] / "src/nasolve/data/ligands" / (component + ".cif")
    before = path.read_bytes()
    plan = parent_conformation_plan(path, component, parent)
    assert plan["status"] == "MATCH_PARENT_CHI"
    assert plan["atoms"] == ["O4'", "C1'", anchor, last]
    assert path.read_bytes() == before


def test_source_change_during_planning_is_a_failure_not_unassessed_fallback(tmp_path, monkeypatch):
    import nasolve.postmr_conformation as module
    source = tmp_path / "PDU.cif"
    source.write_bytes(SOURCE.read_bytes())
    original = module.component_values
    def changed(path, code):
        result = original(path, code)
        path.write_text(path.read_text() + "\n# changed\n")
        return result
    monkeypatch.setattr(module, "component_values", changed)
    with pytest.raises(ValueError, match="Source changed"):
        module.parent_conformation_plan(source, "PDU", "DT")


def test_purine_graph_match_that_swaps_ring_roles_is_refused(tmp_path, monkeypatch):
    fake, args = case(tmp_path, monkeypatch)
    source = args[6]["PDU"]
    source.write_bytes((Path(__file__).parents[1] / "src/nasolve/data/ligands/DP.cif").read_bytes())
    args = (*args[:2], (MutationAction("A:12", "DC", "DP", "coot-parent-overlap", "DG"),),
            *args[3:6], {"DP": source}, args[7])
    fake.code = "DP"
    fake.after = 31.43
    def read(mol, *specs):
        assert [s[3] for s in specs] == [" O4'", " C1'", " N9 ", " C4 "]
        return fake.expected if mol == 0 else fake.chi
    fake.get_torsion_py = read
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    assert fake.matches and not fake.overlap_chi and not args[1].exists()


@pytest.mark.parametrize("message, expected", [
    ("NASOLVE_PARENT_MUTATE A:12 DT 1\nNASOLVE_MUTATION_IDENTITY A:12 DT DC\n",
     "requested DT at A:12, but Coot read back DC"),
    ("NASOLVE_RESULT A:12 DC\n", "requested PDU at A:12, but Coot read back DC"),
    ("NASOLVE_MUTATION_IDENTITY X:99 DT DC\n", "Coot exited with status 0 without writing"),
    ("NASOLVE_MUTATION_IDENTITY A:12 DT DT\n", "Coot exited with status 0 without writing"),
    ("", "Coot exited with status 0 without writing"),
])
def test_native_zero_exit_without_model_reports_the_verified_stage(tmp_path, monkeypatch, message, expected):
    _, args = case(tmp_path, monkeypatch)
    monkeypatch.setattr("nasolve.postmr.subprocess.run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, message))
    with pytest.raises(PostMRPreparationError, match=expected) as failure:
        _run_coot(*args)
    assert str(args[4] / "coot.log") in str(failure.value)
    assert (args[4] / "coot.log").read_text() == message
    assert not args[1].exists()


@pytest.mark.parametrize("method", ["coot-parent-overlap", "coot-mutate-base"])
@pytest.mark.parametrize("observed", ["PDU", "DC", "", None, True])
def test_native_success_with_wrong_canonical_identity_stops_before_use(tmp_path, monkeypatch, method, observed):
    fake, args = case(tmp_path, monkeypatch)
    # Match chi perfectly: residue identity must be checked independently.
    fake.chi = fake.expected
    fake.residue_name = lambda *a: observed
    if method == "coot-mutate-base":
        args = (*args[:2], (MutationAction("A:12", "DC", "DT", method),), *args[3:6], {}, {})
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    assert not args[1].exists()
    assert not fake.matches and not fake.overlap_chi
    assert not any(p.exists() for p in args[7].values())
    assert "Coot did not produce DT at A:12" in (args[4] / "coot.log").read_text()


def test_parent_identity_check_applies_when_graph_conformation_is_unassessed(tmp_path, monkeypatch):
    fake, args = case(tmp_path, monkeypatch)
    args[6]["PDU"].unlink()
    fake.residue_name = lambda *a: "PDU"
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    assert not fake.matches and not fake.overlap_chi and not args[1].exists()
    assert "Coot did not produce DT" in (args[4] / "coot.log").read_text()


@pytest.mark.parametrize("code", ["DP", "Q17"])
def test_named_source_fragment_recovers_failed_chi_without_changing_sugar(tmp_path, monkeypatch, code):
    from math import dist
    from nasolve.postmr_restoration import source_graph_fragment
    from nasolve.postmr_canonical_seed import _chi
    fake, args, xyz = named_monomer_case(tmp_path, monkeypatch, code)
    before = {n: tuple(p) for n,p in xyz.items()}
    graph = source_graph_fragment(args[6][code], code)
    _run_coot(*args)
    assert len(fake.edited) == 1 and fake.overlap_chi == [pytest.approx(fake.expected)]
    assert _chi(xyz, ["O4'", "C1'", "N9", "C4"]) == pytest.approx(fake.expected)
    assert all(tuple(xyz[n]) == before[n] for n in graph["scaffold_atoms"])
    attached = ["C1'", *graph["fragment_atoms"]]
    assert all(dist(xyz[n],xyz[m]) == pytest.approx(dist(before[n],before[m]), abs=1e-8)
               for n in attached for m in attached)
    assert set(fake.edited[0]).isdisjoint(graph["scaffold_atoms"])
    assert "H8" in fake.edited[0] and "N9" not in fake.edited[0]
    assert "NASOLVE_NAMED_CHI_RECOVERY" in (args[4] / "coot.log").read_text()


def named_monomer_case(tmp_path, monkeypatch, code):
    from nasolve.cif_stereochemistry_audit import _values, _graph, _coordinates
    from nasolve.postmr_canonical_seed import _chi
    fake, args = case(tmp_path, monkeypatch, code=code)
    source = args[6][code]
    template = Path(__file__).parents[1] / "src/nasolve/data/ligands/DP.cif"
    source.write_text(template.read_text().replace("DP", code))
    v = _values(source, code)
    elements = _graph(v)[0]
    _, xyz = _coordinates(v, source=False)
    names = ["O4'", "C1'", "N9", "C4"]
    fake.expected = (_chi(xyz,names) + 179.1 + 180) % 360 - 180
    action = MutationAction("B:4", "DG", code, "coot-parent-overlap", "DG")
    args = (*args[:2], (action,), *args[3:7], {"B:4": args[4] / "parent.pdb"})
    fake.get_torsion_py = lambda imol, *specs: fake.expected if imol == 0 else _chi(xyz,[s[3].strip() for s in specs])
    fake.residue_info_py = lambda *a: [[[n,""],[1.0,20.0,e,""],list(xyz[n]),i]
                                       for i,(n,e) in enumerate(elements.items())]
    fake.edited = []
    def edit(rows):
        fake.edited.append({row[4].strip() for row in rows})
        for imol,chain,resid,icode,atom,alt,axis,value in rows:
            assert (imol,chain,resid,icode,alt) == (1,"A",1,"","")
            xyz[atom.strip()]["xyz".index(axis)] = value
        return 0  # Actual Coot 1.3.3 reports 0 on a successful coordinate edit.
    fake.set_atom_attributes_py = edit
    def overlap(*a):
        fake.overlap_chi.append(_chi(xyz,names))
        return True
    fake.overlap_ligands_py = overlap
    return fake, args, xyz


@pytest.mark.parametrize("defect", ["extra", "missing-heavy", "wrong-element", "alternate", "duplicate", "silent-incomplete-write", "moved-sugar"])
def test_named_chi_recovery_refuses_incomplete_or_ambiguous_monomer(tmp_path, monkeypatch, defect):
    fake,args,xyz = named_monomer_case(tmp_path,monkeypatch,"DP")
    read,write = fake.residue_info_py,fake.set_atom_attributes_py
    def reader(*a):
        rows=read(*a)
        if defect=="extra":rows.append([["XX",""],[1.,20.,"C",""],[0.,0.,0.],-1])
        elif defect=="duplicate":rows.append(rows[-1])
        elif defect=="missing-heavy":rows=[r for r in rows if r[0][0]!="O6"]
        elif defect=="wrong-element":rows[0][1][2]="X"
        elif defect=="alternate":rows[0][0][1]="B"
        return rows
    def writer(rows):
        if defect=="silent-incomplete-write":return 1
        status=write(rows)
        if defect=="moved-sugar":xyz["O4'"][0]+=0.02
        return status
    fake.residue_info_py, fake.set_atom_attributes_py = reader, writer
    with pytest.raises(PostMRPreparationError):
        _run_coot(*args)
    expected_reason = {
        "missing-heavy": "missing source heavy atoms",
        "silent-incomplete-write": "did not realize the named rigid rotation",
        "moved-sugar": "moved a protected atom",
    }.get(defect, "differs from the source atoms")
    assert expected_reason in (args[4] / "coot.log").read_text()
    assert not fake.overlap_chi and not args[1].exists()
