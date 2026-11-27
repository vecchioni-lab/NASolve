"""Review the ordinary Coot construction, its real terminal phosphate and its declared images."""
import json

import pytest

from nasolve.cli import main
from nasolve.construct_registration import build_construct_registration
from nasolve.model_assessment import file_sha256, inspect_pdb
from nasolve.postmr_lineage import begin_postmr_construction, finish_postmr_construction
from .test_cif_model_context import model, report
from .test_cif_repair_attempt import inventory
from .test_construct_registration import target


def put(path, value):
    path.write_text(json.dumps(value))
    return path


def construction(root, damage=None, *, native_fixture=False):
    run = root / "run with spaces"
    models = run / "PostMR/Model"
    models.mkdir(parents=True)
    (run / "PostMR/Coot").mkdir()
    chains = tuple((chain, "DC" if native_fixture else code) for chain, code in (("A", "DC"), ("B", "DA"), ("D", "DT")))
    terminal = ("A:1", "B:1", "D:1") if damage == "local" else ("D:1",)
    prepared = model(models / "prepared_model.pdb", chains=chains)
    lines = ["CRYST1   20.000  160.000   90.000  90.00  90.00  90.00 P 1           1\n"]
    for line in prepared.read_text().splitlines(keepends=True):
        site = line[21:22] + ":" + line[22:26].strip()
        atom = line[12:16].strip()
        if atom == "OP3" and site not in terminal:
            continue
        if damage == "length" and (site, atom) == ("B:1", "OP1"):
            line = line[:30] + f"{9.:8.3f}" + line[38:]
        if damage == "extra" and (site, atom) == ("D:9", "OP1"):
            lines.append(line[:12] + " OP3" + line[16:])
        if native_fixture and atom == "C5'":
            line = line[:38] + f"{float(line[38:46]) + .6:8.3f}" + line[46:]
        if native_fixture and atom == "C3'" and not (damage == "missing reference torsion" and site == "D:1"):
            x, y, z = (float(line[i:i+8]) for i in (30, 38, 46))
            lines.append(line[:6] + f"{int(line[6:11]) + 2000:5d}" + line[11:12] + " C4'" + line[16:30] +
                         f"{x+.3:8.3f}{y+.7:8.3f}{z+.9:8.3f}" + line[54:])
        lines.append(line)
    prepared.write_text("".join(lines))
    original = models / "mr_solution.pdb"
    returned = models / "after_coot.pdb"
    for copy in (original, returned):
        copy.write_bytes(prepared.read_bytes())
    start = begin_postmr_construction(run, original, original, {}, [], allow_op3_sites=terminal)
    finish_postmr_construction(run, start, prepared, dict(model=returned, raw_model=None, coot_log=None))
    put(run / "report.json", dict(workflow="automr", **report(*terminal)))
    return run, prepared


def registration(root, prepared, *, occupied_donor=False):
    from nasolve.cif_linked_preparation import _model_inventory
    rows = [(site, info["code"]) for site, info in _model_inventory(prepared).items()]
    sites = {site: site for site, _ in rows}
    reg = put(root / "registration.json", build_construct_registration(
        inspect_pdb(prepared), target(*rows), {"copy": sites}, source="two declared seams"))
    routes = [[f"{c}:1", f"{c}:9"] for c in "ABD"]
    if occupied_donor:
        routes = [["A:1"], ["A:9"], *routes[1:]]
    discovery = put(root / "discovery.json", dict(schema_version=1, kind="topostitch-end-discovery-input",
        model_sha256=file_sha256(prepared), registration_sha256=file_sha256(reg), copy_id="copy",
        strands=[dict(strand_id=str(n), sites=seq, five_prime_boundary="representation",
                      three_prime_boundary="representation") for n, seq in enumerate(routes)],
        duplex_pairs=[], pairing_inventory_complete=False))
    edges = put(root / "edges.json", [
        dict(continuation_id=7, source_site="B:9", target_site="B:1", target_operator_xyz="x-1,y,z"),
        dict(continuation_id=4, source_site="A:1" if occupied_donor else "A:9", target_site="A:1",
             target_operator_xyz="x+1,y,z"),
    ])
    return reg, discovery, edges


def call(run, inputs=(), *extra):
    args = ["cif-doctor", "prepared-backbone", str(run), "--json"]
    for flag, path in zip(("--registration", "--discovery-input", "--backbone-continuations"), inputs):
        args.extend([flag, str(path)])
    return main([*args, *map(str, extra)])


def test_open_preparation_status_reopens_construction_without_creating_a_request(tmp_path, capsys):
    run, prepared = construction(tmp_path)
    before = inventory(tmp_path)
    assert main(["cif-doctor", "preparation-status", str(run)]) == 0
    status = capsys.readouterr().out
    assert "Further attempt: BLOCKED" in status and "cif-doctor prepared-backbone" in status
    assert call(run) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["status"] == "OPEN_INCOMING" and observed["registered_continuations"] == []
    assert observed["prepared_model"]["sha256"] == file_sha256(prepared)
    assert observed["local_links"] == [[f"{c}:1", f"{c}:9"] for c in "ABD"]
    assert observed["protected_terminal_phosphates"] == ["D:1"]
    assert [r["site"] for r in observed["without_local_incoming"]] == ["A:1", "B:1"]
    for row in observed["without_local_incoming"]:
        assert len(row["p_o_distances_angstrom"]) == len(row["o_p_o_angles_degrees"]) == 3
    assert observed["scientific_qualification"] == "NOT_ASSESSED"
    assert inventory(tmp_path) == before


def test_closed_local_preparation_needs_no_image_registration(tmp_path, capsys):
    run, _ = construction(tmp_path, "local")
    assert call(run) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["status"] == "LOCAL_BACKBONE_CHECKED" and observed["without_local_incoming"] == []
    assert observed["protected_terminal_phosphates"] == ["A:1", "B:1", "D:1"]


def test_prepare_run_points_to_the_written_construction_after_an_open_phosphate(tmp_path, monkeypatch, capsys):
    from nasolve.phosphate import UnverifiedIncomingPhosphate
    run, _ = construction(tmp_path)
    monkeypatch.setattr("nasolve.cli.load_config", lambda: object())
    monkeypatch.setattr("nasolve.cli.discover_phenix", lambda *args, **kwargs: object())
    monkeypatch.setattr("nasolve.cli.discover_coot", lambda *args, **kwargs: None)
    def stopped(*args, **kwargs):
        raise UnverifiedIncomingPhosphate(("A:1", "B:1"), {})
    monkeypatch.setattr("nasolve.cif_ordinary_postmr.prepare_checked_postmr", stopped)
    assert main(["cif-doctor", "prepare-run", str(run)]) == 2
    text = capsys.readouterr().err
    assert "prepared-backbone" in text and "read saved attempts" not in text.lower()


def test_all_registered_images_and_original_chemistry_replay_after_relocation(tmp_path, capsys):
    pytest.importorskip("gemmi")
    original = tmp_path / "original"
    run, prepared = construction(original)
    inputs = registration(original, prepared)
    def read(run, inputs):
        before = inventory(run.parent)
        assert call(run, inputs) == 0, capsys.readouterr().err
        result = json.loads(capsys.readouterr().out)
        assert inventory(run.parent) == before
        return result
    saved = read(run, inputs)
    assert saved["status"] == "REGISTERED_FOR_REVIEW" and len(saved["local_links"]) == 3
    edges = saved["registered_continuations"]
    assert [(r["id"], r["o3_site"], r["phosphate_site"], r["o3_image"]) for r in edges] == [
        (4, "A:9", "A:1", "x-1,y,z"), (7, "B:9", "B:1", "x+1,y,z")]
    assert all(row["distance_A"] > 2.1 and len(row["coordinate_angles_degrees"]) == 4 for row in edges)
    assert str(original) not in json.dumps(saved)
    moved = original.rename(tmp_path / "moved")
    assert not original.exists()
    assert read(moved / run.name, [moved / p.name for p in inputs]) == saved


@pytest.mark.parametrize(("failure", "diagnostic"), [
    ("partial arguments", "together"), ("omitted edge", "lack a registered partner: A:1"),
    ("occupied donor", "already has an outgoing partner"), ("protected target", "protected terminal phosphate"),
    ("identity image", "nonidentity image"), ("tampered model", "artifact changed"), ("stale intent", "intent differs"),
    ("length", "implausible P-OP1 distance"), ("extra", "Unrequested internal OP3 remains at D:9"),
])
def test_partial_or_conflicting_chemistry_never_becomes_a_review_candidate(tmp_path, capsys, failure, diagnostic):
    pytest.importorskip("gemmi")
    run, prepared = construction(tmp_path, failure)
    inputs = registration(tmp_path, prepared, occupied_donor=failure == "occupied donor")
    reg, disc, edges = inputs
    entries = json.loads(edges.read_bytes())
    if failure == "partial arguments":
        inputs = (reg,)
    elif failure == "omitted edge":
        put(edges, entries[:1])
    elif failure == "protected target":
        entries[0]["target_site"] = "D:1"
        put(edges, entries)
    elif failure == "identity image":
        entries[0]["target_operator_xyz"] = "x,y,z"
        put(edges, entries)
    elif failure == "tampered model":
        prepared.write_bytes(prepared.read_bytes() + b"\n")
    elif failure == "stale intent":
        put(run / "report.json", dict(workflow="automr", **report("D:9")))
    before = inventory(tmp_path)
    assert call(run, inputs) != 0
    result = capsys.readouterr()
    assert not result.out and diagnostic in result.err and inventory(tmp_path) == before


def test_candidate_needs_its_model_capture_and_complete_registration(tmp_path, capsys):
    run, prepared = construction(tmp_path)
    assert call(run, (), "--candidate-model", prepared) == 2
    assert "candidate model and native receipt together" in capsys.readouterr().err
    assert call(run, (), "--candidate-model", prepared, "--native-receipt", tmp_path/"unused.json") == 2
    assert "complete crystal registration" in capsys.readouterr().err


@pytest.mark.parametrize(("damage", "diagnostic"), [
    ("different base", "residue or atom identities"), ("different element", "residue or atom identities"),
    ("other image", "crystal representative"), ("different frame", "same crystal frame"),
    ("damaged internal bond", "implausible P-OP1 distance"),
])
def test_candidate_checks_the_whole_model_and_named_copy_before_reading_native_evidence(tmp_path, capsys, damage, diagnostic):
    pytest.importorskip("gemmi")
    run, prepared = construction(tmp_path)
    inputs = registration(tmp_path, prepared)
    lines = prepared.read_text().splitlines(keepends=True)
    for i, line in enumerate(lines):
        site = line[21:22] + ":" + line[22:26].strip()
        name = line[12:16].strip()
        if damage == "different base" and site == "D:9":
            lines[i] = line[:17] + " DA" + line[20:]
        if damage == "different element" and site == "D:9" and name == "C5'":
            lines[i] = line[:76] + " N" + line[78:]
        if damage == "other image" and site.startswith("A:"):
            lines[i] = line[:30] + f"{float(line[30:38]) + 20:8.3f}" + line[38:]
        if damage == "different frame" and line.startswith("CRYST1"):
            lines[i] = line.replace("20.000", "21.000", 1)
        if damage == "damaged internal bond" and site == "D:9" and name == "OP1":
            lines[i] = line[:30] + f"{100.:8.3f}" + line[38:]
    candidate = tmp_path / "candidate.pdb"
    candidate.write_text("".join(lines))
    before = inventory(tmp_path)
    assert call(run, inputs, "--candidate-model", candidate, "--native-receipt", tmp_path/"unused.json") == 2
    result = capsys.readouterr()
    assert diagnostic in result.err and not result.out and inventory(tmp_path) == before


@pytest.mark.parametrize("native_case", ["matched", "competing", "nonlocal reference", "missing reference torsion"])
def test_one_native_capture_binds_both_image_partners_without_selecting_the_candidate(tmp_path, capsys, monkeypatch, native_case):
    pytest.importorskip("gemmi")
    from .test_phosphate_restraints import inspection
    run, prepared = construction(tmp_path, native_case, native_fixture=True)
    inputs = registration(tmp_path, prepared)
    candidate = tmp_path / "returned.pdb"
    candidate.write_bytes(prepared.read_bytes() + b"\n")
    receipt = tmp_path / "native_receipt.json"
    receipt.write_text("{}")
    row = dict(anchor="native_directory", path="inputs/000_model.pdb", role="model",
               sha256=file_sha256(candidate), size=candidate.stat().st_size)
    captures = []
    def capture(path, data):
        assert path == receipt and data == candidate.read_bytes()
        captures.append(path)
        proof = dict(status="REVIEW", execution=dict(returncode=0), inputs=[row], phenix_version="test")
        return proof, {}, {path: path.read_bytes()}
    def references(native, *, phosphate, o3, o3_image):
        assert (phosphate, o3) in {("A:1", "A:9"), ("B:1", "B:9")}
        assert o3_image == ("x-1,y,z" if phosphate == "A:1" else "x+1,y,z")
        if native_case == "competing" and o3 == "B:9":
            return dict(status="COMPETING_ENDPOINT_BOND", reason="B:9 O3′ already has a native partner")
        ref = inspection()["native_reference_links"]
        ref["groups"][0]["links"] = [[f"{c}:1", f"{c}:9"] for c in "ABD" if c != o3[0]]
        if native_case == "nonlocal reference" and o3 == "B:9":
            ref["groups"][0]["links"][0] = ["A:1", "D:9"]
        return ref
    # Native input parsing and reference-term chemistry have their own tests.
    # This small fixture tests the join to both real, source-bound coordinate measurements.
    monkeypatch.setattr("nasolve.cif_phosphate_reference._capture", capture)
    monkeypatch.setattr("nasolve.cif_phosphate_reference._native_atoms", lambda native, data: None)
    monkeypatch.setattr("nasolve.cif_phosphate_reference.reference_link_terms", references)
    before = inventory(tmp_path)
    status = call(run, inputs, "--candidate-model", candidate, "--native-receipt", receipt)
    result = capsys.readouterr()
    assert captures == [receipt] and inventory(tmp_path) == before
    if native_case != "matched":
        message = {"competing": "already has a native partner", "nonlocal reference": "absent from the audited local bonds",
                   "missing reference torsion": "Missing or unoccupied o3-site C4'"}[native_case]
        assert status == 2 and not result.out and message in result.err
        return
    assert status == 0, result.err
    report = json.loads(result.out)
    reading = report["native_candidate"]
    assert reading["native_inputs"] == [row] and reading["candidate_model_sha256"] == file_sha256(candidate)
    assert reading["native_receipt_sha256"] == file_sha256(receipt) and reading["phenix_version"] == "test"
    for original, returned in zip(report["registered_continuations"], reading["registered_continuations"], strict=True):
        assert returned["o3_image"] == original["o3_image"] and returned["distance_A"] == original["distance_A"]
        assert returned["native_bond_target_A"] == 1.593 and returned["native_bond_sigma_A"] == .02
        assert returned["measured_terms_per_link"] == 8
        assert returned["frame_transfer"]["source_model_sha256"] == file_sha256(prepared)
