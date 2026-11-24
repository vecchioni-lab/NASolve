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


def construction(root, damage=None):
    run = root / "run with spaces"
    models = run / "PostMR/Model"
    models.mkdir(parents=True)
    (run / "PostMR/Coot").mkdir()
    chains = (("A", "DC"), ("B", "DA"), ("D", "DT"))
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
    rows = [(f"{c}:{i}", code) for c, code in (("A", "DC"), ("B", "DA"), ("D", "DT")) for i in (1, 9)]
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


def call(run, inputs=()):
    args = ["cif-doctor", "prepared-backbone", str(run), "--json"]
    for flag, path in zip(("--registration", "--discovery-input", "--backbone-continuations"), inputs):
        args.extend([flag, str(path)])
    return main(args)


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
