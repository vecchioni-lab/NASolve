import hashlib
import json
import math
import shutil

import pytest

from nasolve.topostitch_coordinates import EndAssignment, ResidueSite, inspect_end_assignments
from .helpers import pdb_record


def site(chain, number, insertion=""):
    return ResidueSite(chain, number, insertion)


def assignment(name="end1", chain="A", state="available"):
    return EndAssignment(name, (site(chain, 1), site(chain, 2)),
                         (site(chain, 3), site("B", 3)),
                         (site(chain, 4), site("B", 2)), "5prime", state)


def fixture(transform=lambda p: p):
    rows = []
    serial = 1
    # Synthetic planar hexagons, deliberately not a chemical validation fixture.
    for chain, resid, code, x, z in [
        ("A", 1, "DG", -5, 6), ("A", 2, "DA", -5, 3),
        ("A", 3, "DC", -5, 0), ("B", 3, "DG", 5, 0),
        ("A", 4, "DA", -5, -3), ("B", 2, "DT", 5, -3),
    ]:
        for i, atom in enumerate(("N1", "C2", "N3", "C4", "C5", "C6", "C1'")):
            p = ((x + math.cos(i*math.pi/3), math.sin(i*math.pi/3), z)
                 if i < 6 else (x, -2, z))
            p = transform(p)
            rows.append(pdb_record("ATOM", serial, atom, code, chain, resid,
                                   x=p[0], y=p[1], z=p[2], element=atom[0]))
            serial += 1
    return "".join(rows)+"END\n"


def inspect(tmp_path, text=None, assignments=None, **kwargs):
    p = tmp_path/"input.pdb"
    p.write_text(fixture() if text is None else text)
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    result = inspect_end_assignments(p, assignments or [assignment()],
                                    expected_sha256=digest, max_distance_angstrom=20,
                                    **kwargs)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest
    return result


def test_verified_sequence_end_frame_and_gui_state(tmp_path):
    report = inspect(tmp_path)
    end, = report["ends"]
    assert report["source_bytes_verified"] is True
    assert end["sequence"] == "GA"
    assert end["assessment"] == "FRAME_AVAILABLE"
    assert end["frame"]["origin"] == pytest.approx([0,0,0])
    assert end["frame"]["x"] == pytest.approx([1,0,0])
    assert end["frame"]["y"] == pytest.approx([0,1,0])
    assert end["frame"]["z"] == pytest.approx([0,0,1])
    assert report["workflow"] == {"proposal_state": "NO_CANDIDATES", "execution_state": "NOT_ATTEMPTED", "review_state": "UNREVIEWED"}
    assert report["changes"] == []
    assert report["runtime_authority"] is False
    assert report["geometry_validated"] is False
    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert str(tmp_path) not in json.dumps(report)


def test_frame_equivariance_under_rotation_and_translation(tmp_path):
    report = inspect(tmp_path, fixture(lambda p: (-p[1]+20,p[0]-7,p[2]+12)))
    frame = report["ends"][0]["frame"]
    assert frame["origin"] == pytest.approx([20,-7,12])
    assert frame["x"] == pytest.approx([0,1,0])
    assert frame["y"] == pytest.approx([-1,0,0])
    assert frame["z"] == pytest.approx([0,0,1])


def test_chain_renaming_does_not_change_geometry_or_sequence(tmp_path):
    original = inspect(tmp_path)
    renamed = fixture().replace(" A   ", " Z   ")
    result = inspect(tmp_path, renamed, [assignment(chain="Z")])
    for key in ["frame", "sequence", "assessment"]:
        assert result["ends"][0][key] == original["ends"][0][key]


def test_missing_atoms_exclude_end_instead_of_fabricating_coordinates(tmp_path):
    text = "\n".join(line for line in fixture().splitlines()
                     if not (line[12:16].strip()=="C4" and line[21:26]=="A   3"))
    report = inspect(tmp_path, text)
    assert report["ends"][0]["assessment"] == "UNASSESSED"
    assert report["ends"][0]["issues"][0]["code"] == "MISSING_ATOM"
    assert report["screening"]["candidates"] == []
    assert report["workflow"]["proposal_state"] == "INCOMPLETE_ASSESSMENT"


@pytest.mark.parametrize("edit,code", [
    (lambda s: s.replace(" DC A   3", "  X A   3"), "UNSUPPORTED_RESIDUE"),
    (lambda s: s.replace(" DC A   3", " DA A   3"), "UNSUPPORTED_PAIR"),
    (lambda s: s.replace("  1.00", "  0.00"), "UNUSABLE_OCCUPANCY"),
    (lambda s: "\n".join(l[:16]+"A"+l[17:] if l.startswith("ATOM") else l for l in s.splitlines()), "ALTERNATE_CONFORMER"),
    (lambda s: s.splitlines()[0]+"\n"+s, "AMBIGUOUS_ATOM"),
])
def test_uncertain_coordinates_are_unassessed(tmp_path, edit, code):
    report = inspect(tmp_path, edit(fixture()))
    assert report["ends"][0]["assessment"] == "UNASSESSED"
    assert report["ends"][0]["issues"][0]["code"] == code


def test_multimodel_file_is_rejected_without_merging_models(tmp_path):
    text = "MODEL        1\n"+fixture()+"ENDMDL\nMODEL        2\n"+fixture()+"ENDMDL\n"
    with pytest.raises(ValueError, match="model"):
        inspect(tmp_path,text)


def test_checksum_mismatch_is_rejected_before_coordinate_work(tmp_path):
    p=tmp_path/"model.pdb";p.write_text(fixture())
    with pytest.raises(ValueError, match="checksum"):
        inspect_end_assignments(p,[assignment()],expected_sha256="0"*64,max_distance_angstrom=20)


def test_repeated_identity_across_ter_is_not_silently_joined(tmp_path):
    text=fixture().replace("END\n", "TER\n")+fixture()
    report=inspect(tmp_path,text)
    assert report["ends"][0]["issues"][0]["code"] == "AMBIGUOUS_RESIDUE"


def test_frame_degeneracy_does_not_produce_nan(tmp_path):
    lines=[]
    for line in fixture().splitlines():
        if line.startswith("ATOM"):
            line=line[:30]+f"{0:8.3f}{0:8.3f}{0:8.3f}"+line[54:]
        lines.append(line)
    result=inspect(tmp_path,"\n".join(lines))
    assert result["ends"][0]["issues"][0]["code"] == "DEGENERATE_FRAME"
    json.dumps(result,allow_nan=False)


def test_input_order_does_not_define_strand_order(tmp_path):
    original=inspect(tmp_path)
    shuffled="\n".join(reversed(fixture().splitlines()[:-1]))+"\nEND\n"
    result=inspect(tmp_path,shuffled)
    assert result["ends"] == original["ends"]


def test_can_be_relocated_after_original_input_is_gone(tmp_path):
    original=tmp_path/"original";original.mkdir()
    result=inspect(original)
    moved=tmp_path/"moved";moved.mkdir()
    shutil.move(original/"input.pdb",moved/"different.pdb")
    original.rmdir()
    after=inspect_end_assignments(moved/"different.pdb",[assignment()],expected_sha256=result["source_model_sha256"],max_distance_angstrom=20)
    assert after == result


def test_explicit_insertion_codes_resolve_exactly(tmp_path):
    text="\n".join(l[:26]+"X"+l[27:] if l.startswith("ATOM") and l[21:26]=="A   1" else l for l in fixture().splitlines())
    a=assignment()
    fixed=EndAssignment(a.end_id,(site("A",1,"X"),site("A",2)),a.terminal_pair,a.inner_pair,a.polarity)
    assert inspect(tmp_path,text,[fixed])["ends"][0]["sequence"] == "GA"
    assert inspect(tmp_path,text)["ends"][0]["issues"][0]["code"] == "MISSING_RESIDUE"


@pytest.mark.parametrize("kwargs", [
    {"chain":"AB"}, {"residue_number":True}, {"insertion_code":"AB"},
])
def test_invalid_coordinate_sites_fail(kwargs):
    values=dict(chain="A",residue_number=1,insertion_code="")
    values.update(kwargs)
    with pytest.raises(ValueError): ResidueSite(**values)


def test_assignment_overlap_duplicate_and_empty_are_rejected():
    a=assignment()
    for sites in [(), (site("A",1),site("A",1)), (site("A",3),)]:
        with pytest.raises(ValueError):
            EndAssignment("e",sites,a.terminal_pair,a.inner_pair,"5prime")


def test_same_coordinate_overhang_cannot_be_two_ends(tmp_path):
    with pytest.raises(ValueError,match="overhang"):
        inspect(tmp_path,assignments=[assignment(),assignment(name="other")])


def test_state_and_manifest_provenance_are_retained(tmp_path):
    result=inspect(tmp_path,assignments=[assignment(state="free")])
    assert result["ends"][0]["state"] == "free"
    assert result["screening"]["ends"][0]["reason"] == "free"
    assert len(result["assignments_sha256"]) == 64
    assert result["assignment_authority"] == "caller_declared_not_inferred"


def two_end_fixture():
    first=fixture().replace("END\n", "")
    second=[]
    for line in fixture(lambda p: (-p[0],p[1],12-p[2])).splitlines():
        if not line.startswith("ATOM"):
            continue
        old_chain=line[21]
        resid=int(line[22:26])
        line=line[:21]+{"A":"C","B":"D"}[old_chain]+line[22:]
        if old_chain=="A" and resid in (1,2):
            line=line[:17]+{1:" DT",2:" DC"}[resid]+line[20:]
        second.append(line)
    a=assignment()
    b=EndAssignment("end2",(site("C",1),site("C",2)),
                    (site("C",3),site("D",3)),(site("C",4),site("D",2)),"5prime")
    return first+"TER\n"+"\n".join(second)+"\nEND\n", [a,b]


def test_two_verified_coordinate_ends_feed_candidate_screen(tmp_path):
    text, assignments=two_end_fixture()
    report=inspect(tmp_path,text,assignments)
    assert [e["sequence"] for e in report["ends"]] == ["GA","TC"]
    candidate,=report["screening"]["candidates"]
    assert candidate["distance_angstrom"] == pytest.approx(12)
    assert report["ends"][1]["frame"]["z"] == pytest.approx([0,0,-1])
    assert report["workflow"]["proposal_state"] == "CANDIDATES_FOR_REVIEW"
    assert report["workflow"]["execution_state"] == "NOT_ATTEMPTED"
    assert report["changes"] == []
    assert report["screening"]["selected_candidate"] is None


def test_one_unassessed_end_does_not_hide_healthy_other_end(tmp_path):
    text, assignments=two_end_fixture()
    text="\n".join(l for l in text.splitlines()
                    if not (l[12:16].strip()=="C1'" and l[21:26]=="C   2"))
    report=inspect(tmp_path,text,assignments)
    assert [e["assessment"] for e in report["ends"]] == ["FRAME_AVAILABLE","UNASSESSED"]
    assert report["workflow"]["proposal_state"] == "INCOMPLETE_ASSESSMENT"
    assert report["screening"]["candidates"] == []


def test_single_explicit_model_and_hetatm_canonical_residues(tmp_path):
    text="MODEL        7\n"+fixture().replace("ATOM  ","HETATM").replace("END\n", "ENDMDL\nEND\n")
    assert inspect(tmp_path,text)["ends"][0]["assessment"] == "FRAME_AVAILABLE"


def test_legacy_sugar_atom_prime_alias(tmp_path):
    assert inspect(tmp_path,fixture().replace("C1'", "C1*"))["ends"][0]["assessment"] == "FRAME_AVAILABLE"


def test_alias_collision_is_ambiguous(tmp_path):
    text=fixture()
    duplicate=next(l for l in text.splitlines() if "C1'" in l).replace("C1'","C1*")
    assert inspect(tmp_path,duplicate+"\n"+text)["ends"][0]["issues"][0]["code"] == "AMBIGUOUS_ATOM"


def test_empty_assignment_list_does_not_invent_ends(tmp_path):
    p=tmp_path/"m.pdb"; p.write_text(fixture())
    result=inspect_end_assignments(p,[],expected_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),max_distance_angstrom=20)
    assert result["ends"] == []
    assert result["workflow"]["proposal_state"] == "NO_CANDIDATES"


def test_assignments_are_immutable_snapshots():
    a=assignment()
    sites=list(a.overhang_sites)
    b=EndAssignment("b",sites,a.terminal_pair,a.inner_pair,"5prime")
    sites.clear()
    assert b.overhang_sites == a.overhang_sites


def test_changed_assignment_state_changes_manifest_identity(tmp_path):
    a=inspect(tmp_path)
    b=inspect(tmp_path,assignments=[assignment(state="free")])
    assert a["source_model_sha256"] == b["source_model_sha256"]
    assert a["assignments_sha256"] != b["assignments_sha256"]


@pytest.mark.parametrize("replacement", ["     nan", "     inf", " garbage"])
def test_malformed_coordinates_fail_entire_parse(tmp_path,replacement):
    lines=fixture().splitlines()
    lines[0]=lines[0][:30]+replacement+lines[0][38:]
    with pytest.raises(ValueError,match="Malformed PDB"):
        inspect(tmp_path,"\n".join(lines))
