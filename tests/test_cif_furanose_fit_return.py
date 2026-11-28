"""A local geometry return contributes only the fitted sugar's coordinates."""
from hashlib import sha256

import pytest

from nasolve.cif_furanose_bridge import prepare_furanose_bridge_seed
from nasolve.cif_whole_furanose import prepare_base_anchored_furanose_from_model
from tests.test_cif_pyrimidine_placement import inputs
from tests.test_cif_model_context import report


@pytest.fixture(scope="module")
def frozen(tmp_path_factory):
    root = tmp_path_factory.mktemp("furanose-return")
    source, numerical, host, workbook, frame = inputs(root)
    crystal = "CRYST1   90.000   90.000   90.000  90.00  90.00  90.00 P 1           1\n"
    frame.write_text(crystal + "REMARK retain parent history\n" + frame.read_text())
    placement = root / "placement"
    prepare_base_anchored_furanose_from_model(source, numerical, host, workbook, frame, placement,
        code="UY1", site="A:2", postmr_report=report())
    seed = root / "seed"
    prepare_furanose_bridge_seed(placement, seed, endpoint_weight=1000., max_base_displacement=2.)
    return seed


def _atom(line):
    return line.startswith((b"ATOM  ", b"HETATM"))


def _shift(line, axis, distance):
    start = 30 + 8 * axis
    return line[:start] + f"{float(line[start:start+8]) + distance:8.3f}".encode() + line[start+8:]


def test_site_fit_returns_only_selected_coordinates_and_preserves_parent_records(frozen, tmp_path):
    from nasolve.cif_furanose_bridge import read_fitted_furanose_model

    input_data = (frozen/"model.pdb").read_bytes()
    original = input_data.splitlines(keepends=True)
    expected = [_shift(l, 0, 0.02) if _atom(l) and l[21:26] == b"A   2" else l for l in original]
    # Native geometry files can reorder atoms, omit history and add hydrogen bonds as LINK records.
    fitted = tmp_path/"native.pdb"
    fitted.write_bytes(b"LINK      native hydrogen-bond annotation\n" + original[0]
                       + b"".join(reversed([l for l in expected if _atom(l)])) + b"END\n")
    candidate, observed = read_fitted_furanose_model(frozen, fitted)
    assert candidate == b"".join(expected)
    assert observed["fixed_atoms"] == sum(_atom(l) and l[21:26] != b"A   2" for l in original)
    assert observed["selected_atoms"] == sum(_atom(l) and l[21:26] == b"A   2" for l in original)
    assert observed["source_stereocentres"] == 4 and observed["returned_link_records"] == 1
    assert observed["candidate_sha256"] == sha256(candidate).hexdigest()
    assert (frozen/"model.pdb").read_bytes() == input_data


@pytest.mark.parametrize(("defect", "reason"), [
    ("fixed", "outside"), ("occupancy", "occupancy"), ("b", "displacement"),
    ("element", "inventory"), ("residue", "Ambiguous PDB site"), ("missing", "inventory"),
    ("duplicate", "duplicate atom"), ("cell", "crystal frame"), ("hand", "stereocentre"),
])
def test_unrelated_or_chemically_inconsistent_native_return_is_rejected(frozen, tmp_path, defect, reason):
    from nasolve.cif_furanose_bridge import read_fitted_furanose_model

    lines = (frozen/"model.pdb").read_bytes().splitlines(keepends=True)
    fixed = next(i for i,l in enumerate(lines) if _atom(l) and l[21:26] == b"A   1")
    moving = [i for i,l in enumerate(lines) if _atom(l) and l[21:26] == b"A   2"]
    i = moving[0]
    if defect == "fixed":
        lines[fixed] = _shift(lines[fixed], 0, .001)
    elif defect == "occupancy":
        lines[i] = lines[i][:54] + b"  0.50" + lines[i][60:]
    elif defect == "b":
        lines[fixed] = lines[fixed][:60] + b" 10.00" + lines[fixed][66:]
    elif defect == "element":
        lines[i] = lines[i][:76] + b"FE" + lines[i][78:]
    elif defect == "residue":
        lines[i] = lines[i][:17] + b" DC" + lines[i][20:]
    elif defect == "missing":
        del lines[i]
    elif defect == "duplicate":
        lines.insert(i, lines[i])
    elif defect == "cell":
        lines[0] = lines[0].replace(b"90.000", b"94.000", 1)
    else:
        for i in moving:
            lines[i] = _shift(lines[i], 2, -2*float(lines[i][46:54]))
    native = tmp_path/"returned.pdb"
    native.write_bytes(b"".join(lines))
    with pytest.raises(ValueError, match=reason):
        read_fitted_furanose_model(frozen, native)
