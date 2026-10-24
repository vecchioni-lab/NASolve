"""Stage one fresh, explicitly synthetic mixed-base DNA mechanics challenge.

This module prepares inputs, not coordinates for the modified bases. Ordinary
PostMR/Coot/ReadySet must construct and assess those targets in a new run.
Donor observations and the original canonical search scaffold are never edited.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import mkdtemp

from .presets import load_preset
from .sequence_reference import compile_sequence_family_targets, parse_sequence_reference


class SyntheticDNAError(ValueError):
    """A declared source or staged synthetic input failed its preparation gate."""


ANNOTATED_SEQUENCES = {
    "A": "GAGC(1AP)(IGU)(5CM)CTGT(DZ)TGGACA(DF)(CGY)A",
    "B": "CCA(DP)ACA",
    "C": "GG(IMC)TGCT",
    "D": "CT(DX)ATGT",
}
TARGET_CODES = {
    "A": "DG DA DG DC 1AP IGU 5CM DC DT DG DT DZ DT DG DG DA DC DA DF CGY DA".split(),
    "B": "DC DC DA DP DA DC DA".split(),
    "C": "DG DG IMC DT DG DC DT".split(),
    "D": "DC DT DX DA DT DG DT".split(),
}
PAIR_SITES = (
    {"family": "D:T", "sites": ["A:5", "C:11"], "codes": ["1AP", "DT"]},
    {"family": "B:S", "sites": ["A:6", "C:10"], "codes": ["IGU", "IMC"]},
    {"family": "Z:P", "sites": ["A:12", "B:4"], "codes": ["DZ", "DP"]},
    {"family": "K:X", "sites": ["A:20", "D:3"], "codes": ["CGY", "DX"]},
    {"family": "5CM:G", "sites": ["A:7", "C:9"], "codes": ["5CM", "DG"]},
    {"family": "DF:A", "sites": ["A:19", "D:4"], "codes": ["DF", "DA"]},
)
CHAIN_IDS = {"A": tuple(map(str, range(1, 22))), "B": tuple(map(str, range(1, 8))),
             "C": tuple(map(str, range(8, 15))), "D": tuple(map(str, range(1, 8)))}
FIVE_PRIME_SITES = ("A:1", "B:1", "C:8", "D:1")
_SUGAR = {"C1'", "C2'", "C3'", "C4'", "C5'", "O3'", "O4'", "O5'"}
_PHOSPHATE = {"P", "OP1", "OP2", "OP3", "O1P", "O2P", "O3P"}
_CANONICAL = {"DA", "DC", "DG", "DT"}


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _selected(root: Path, relative: str, label: str) -> tuple[Path, bytes]:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or "\\" in relative or not rel.parts:
        raise SyntheticDNAError(f"{label} must use a declared relative path under its source anchor")
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise SyntheticDNAError(f"{label} escapes its source anchor: {relative}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SyntheticDNAError(f"Missing/unreadable {label}: {path}") from exc
    if not data:
        raise SyntheticDNAError(f"Empty {label}: {path}")
    return path, data


def _model_inventory(data: bytes) -> tuple[list[str], dict[str, set[str]]]:
    try:
        lines = data.decode("utf-8").splitlines(keepends=True)
    except UnicodeError as exc:
        raise SyntheticDNAError("Canonical W search model must be UTF-8 PDB text") from exc
    if sum(line.startswith("MODEL ") for line in lines) > 1:
        raise SyntheticDNAError("Canonical W search model must contain one coordinate model")
    expected = {f"{chain}:{resid}" for chain, ids in CHAIN_IDS.items() for resid in ids}
    atoms: dict[str, set[str]] = defaultdict(set)
    serials: set[int] = set()
    for line in lines:
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        if len(line.rstrip("\n")) < 54:
            raise SyntheticDNAError("Truncated coordinate record in canonical W search model")
        site = line[21:22] + ":" + line[22:27].strip()
        atom = line[12:16].strip()
        try:
            serial = int(line[6:11])
        except ValueError as exc:
            raise SyntheticDNAError("Invalid canonical W atom serial") from exc
        if site not in expected or line[17:20].strip() not in _CANONICAL:
            raise SyntheticDNAError(f"Expected the fresh canonical 42-site W scaffold; found {site}")
        if line[16:17].strip() or atom in atoms[site] or serial in serials:
            raise SyntheticDNAError(f"Ambiguous duplicate/alternate coordinate identity at {site}/{atom}")
        atoms[site].add(atom)
        serials.add(serial)
    if set(atoms) != expected:
        raise SyntheticDNAError("Canonical W search model must have exactly A21/B7/C7/D7 at the declared residue IDs")
    for site, names in atoms.items():
        if not _SUGAR <= names or names & {"O2'", "O2*"}:
            raise SyntheticDNAError(f"Canonical W search model lacks the complete DNA sugar at {site}")
    return lines, dict(atoms)


def prepare_free_five_prime_model(data: bytes) -> tuple[bytes, list[dict[str, object]]]:
    """Remove phosphate groups only at the four explicitly declared chain starts.

    The original noPO4 W fixture still contains P/OP1/OP2 at B:1 and C:8.
    Remove matching ANISOU and CONECT references as well as coordinate records;
    do not change any remaining coordinates or internal phosphate atoms.
    """
    lines, atoms = _model_inventory(data)
    removed: list[dict[str, object]] = []
    serials: set[int] = set()
    for line in lines:
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        site = line[21:22] + ":" + line[22:27].strip()
        atom = line[12:16].strip()
        if site in FIVE_PRIME_SITES and atom in _PHOSPHATE:
            serial = int(line[6:11])
            serials.add(serial)
            removed.append({"site": site, "atom": atom, "serial": serial})
    for site in FIVE_PRIME_SITES:
        names = atoms[site] & _PHOSPHATE
        if names and names not in ({"P", "OP1", "OP2"}, {"P", "OP1", "OP2", "OP3"}):
            raise SyntheticDNAError(f"Partial/alternate terminal phosphate needs review at {site}: {sorted(names)}")
    result: list[str] = []
    for line in lines:
        if line.startswith(("ATOM  ", "HETATM", "ANISOU")) and int(line[6:11]) in serials:
            continue
        if line.startswith("CONECT"):
            try:
                linked = [int(line[i:i + 5]) for i in range(6, len(line.rstrip()), 5)
                          if line[i:i + 5].strip()]
            except ValueError as exc:
                raise SyntheticDNAError("Malformed CONECT in canonical W model") from exc
            if not linked or linked[0] in serials:
                continue
            retained = [linked[0], *[item for item in linked[1:] if item not in serials]]
            if len(retained) < 2:
                continue
            if retained != linked:
                line = "CONECT" + "".join(f"{item:5d}" for item in retained) + "\n"
        result.append(line)
    prepared = "".join(result).encode("utf-8")
    _, after = _model_inventory(prepared)
    if any(after[site] & _PHOSPHATE for site in FIVE_PRIME_SITES):
        raise SyntheticDNAError("5'-OH preparation left a terminal phosphate atom")
    return prepared, removed


def _reference() -> dict[str, object]:
    return {
        "schema_version": 1, "kind": "sequence-defined-reference",
        "id": "synthetic-dna-combined-w", "version": "1.0.0",
        "chains": [
            {"chain": chain, "residue_ids": list(CHAIN_IDS[chain]), "polymer": "DNA",
             "sequence": sequence}
            for chain, sequence in (("A", "GAGCAGCCTGTATGGACATCA"), ("B", "CCATACA"),
                                    ("C", "GGCTGCT"), ("D", "CTGATGT"))
        ],
    }


def validate_synthetic_dna_inputs(root: Path) -> dict[str, object]:
    """Verify staged hashes, all 42 literal DNA targets and free 5'-OH termini."""
    root = Path(root).resolve()
    try:
        receipt = json.loads((root / "synthetic-inputs.json").read_text(encoding="utf-8"))
        for name, record in receipt["artifacts"].items():
            path = (root / record["relative_path"]).resolve()
            if record["anchor"] != "output" or not path.is_relative_to(root):
                raise SyntheticDNAError(f"Invalid staged artifact anchor: {name}")
            data = path.read_bytes()
            if len(data) != record["size"] or _digest(data) != record["sha256"]:
                raise SyntheticDNAError(f"Staged input checksum mismatch: {name}")
        reference = parse_sequence_reference(json.loads((root / "dataset/sequence_reference.json").read_text()))
        if any(chain.polymer != "DNA" for chain in reference.chains):
            raise SyntheticDNAError("Every synthetic target chain must explicitly be DNA")
        target = compile_sequence_family_targets(reference, dataset_sequences=ANNOTATED_SEQUENCES)
        expected = {f"{chain}:{resid}": code for chain, ids in CHAIN_IDS.items()
                    for resid, code in zip(ids, TARGET_CODES[chain])}
        observed = {row["site"]: row["residue_code"] for row in target["sites"]}
        if observed != expected or receipt["target_sites"] != target["sites"]:
            raise SyntheticDNAError("Compiled synthetic target differs from the reviewed combined DNA recipe")
        model = (root / "dataset/synthetic_search_W_free5OH.pdb").read_bytes()
        _, atoms = _model_inventory(model)
        if any(atoms[site] & _PHOSPHATE for site in FIVE_PRIME_SITES):
            raise SyntheticDNAError("Synthetic search model must have four free 5'-OH chain starts")
        config = (root / "dataset/nasolve.txt").read_text()
        expected_config = _configuration()
        if config != expected_config:
            raise SyntheticDNAError("Synthetic sequence/terminal-phosphate configuration changed")
        policy = load_preset(root / "synthetic-dna-combined.toml").to_dict()
        if policy["chemistry"]["terminal_phosphate_sites"] or policy["autosol"]["policy"] != "disabled":
            raise SyntheticDNAError("Synthetic recipe must disable AutoSol and declare no terminal phosphates")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, SyntheticDNAError):
            raise
        raise SyntheticDNAError(f"Could not validate staged synthetic inputs: {exc}") from exc
    return {"status": "STAGED_INPUTS_VALIDATED", "target_count": len(observed),
            "chain_counts": {name: len(ids) for name, ids in CHAIN_IDS.items()},
            "autosol": "DISABLED", "native_tools": "NOT_RUN"}


def _configuration() -> str:
    return (
        "[automr]\nmode = standard\nframe = W\npair = Z:P\n"
        "model = synthetic_search_W_free5OH.pdb\n"
        "sequence_reference = sequence_reference.json\n"
        "five_prime_phosphate_sites =\n\n[sequences]\n"
        + "".join(f"{chain} = {sequence}\n" for chain, sequence in ANNOTATED_SEQUENCES.items())
    )


def stage_synthetic_dna(
    repository: Path, donor: Path, output_parent: Path, *,
    mtz_relative_path: str = "staraniso_alldata-unique.mtz",
    cif_relative_path: str = "Data_1_autoPROC_STARANISO_all.cif",
    summary_relative_path: str = "summary.html",
) -> dict[str, object]:
    """Prepare one exclusive attempt from declared source anchors, then validate.

    The explicitly named MTZ, STARANISO metadata CIF and summary are required
    by ordinary NASolve preflight; none is fabricated or found by basename search.
    ``root``, ``dataset`` and ``recipe`` in the return value are runtime locators;
    the persisted receipt uses portable output-relative artifact references.
    """
    repository = Path(repository).expanduser().resolve()
    donor = Path(donor).expanduser().resolve()
    output_parent = Path(output_parent).expanduser().resolve()
    for source in (repository, donor):
        if output_parent == source or output_parent.is_relative_to(source):
            raise SyntheticDNAError("Synthetic output must be outside the repository and donor anchors")
    source_model = _selected(repository, "MR_frames/5W6W/5W6W_noPO4.pdb", "canonical W scaffold")
    source_recipe = _selected(repository, "docs/recipes/synthetic-dna-combined.toml", "synthetic recipe")
    mtz = _selected(donor, mtz_relative_path, "donor MTZ")
    if mtz[1][:4] != b"MTZ ":
        raise SyntheticDNAError("Declared donor MTZ lacks the MTZ file signature")
    metadata = {
        "donor_cif": _selected(donor, cif_relative_path, "donor STARANISO CIF"),
        "donor_summary": _selected(donor, summary_relative_path, "donor summary"),
    }
    recipe_policy = load_preset(source_recipe[0]).to_dict()
    if recipe_policy["chemistry"]["terminal_phosphate_sites"] or recipe_policy["autosol"]["policy"] != "disabled":
        raise SyntheticDNAError("Synthetic recipe must disable AutoSol and declare no terminal phosphates")
    prepared_model, removed = prepare_free_five_prime_model(source_model[1])
    reference = _reference()
    target = compile_sequence_family_targets(parse_sequence_reference(reference), dataset_sequences=ANNOTATED_SEQUENCES)
    snapshots = {"canonical_search_model": ("repository", source_model),
                 "recipe_source": ("repository", source_recipe), "donor_mtz": ("donor", mtz)}
    snapshots.update({key: ("donor", value) for key, value in metadata.items()})
    output_parent.mkdir(parents=True, exist_ok=True)
    root = Path(mkdtemp(prefix="synthetic-dna-combined-", dir=output_parent))
    (root / "dataset").mkdir()
    artifacts: dict[str, dict[str, object]] = {}

    def write(name: str, relative: str, data: bytes) -> None:
        path = root / relative
        with path.open("xb") as stream:
            stream.write(data)
        artifacts[name] = {"anchor": "output", "relative_path": relative,
                           "sha256": _digest(data), "size": len(data)}

    write("model", "dataset/synthetic_search_W_free5OH.pdb", prepared_model)
    # The canonical predecessor is separate from top-level PDB discovery.
    (root / "provenance").mkdir()
    write("source_model", "provenance/canonical_search_W.pdb", source_model[1])
    write("mtz", "dataset/staraniso_alldata-unique.mtz", mtz[1])
    for name, filename in (("donor_cif", "Data_1_autoPROC_STARANISO_all.cif"), ("donor_summary", "summary.html")):
        write(name, "dataset/" + filename, metadata[name][1])
    write("sequence_reference", "dataset/sequence_reference.json", _json_bytes(reference))
    write("configuration", "dataset/nasolve.txt", _configuration().encode("utf-8"))
    write("recipe", "synthetic-dna-combined.toml", source_recipe[1])
    source_records = {}
    for name, (anchor, (path, data)) in snapshots.items():
        base = repository if anchor == "repository" else donor
        source_records[name] = {"anchor": anchor, "relative_path": path.relative_to(base).as_posix(),
                                "sha256": _digest(data), "size": len(data),
                                "historical_absolute_path": str(path)}
        if path.read_bytes() != data:
            raise SyntheticDNAError(f"Selected source changed during staging: {name}")
    receipt = {
        "schema_version": 1, "kind": "nasolve-synthetic-dna-combined-inputs",
        "synthetic": True,
        "scientific_scope": "Hypothetical modified DNA targets on real donor observations; software mechanics only, not experimental identity or scientific approval",
        "source": source_records, "artifacts": artifacts,
        "target_sites": target["sites"], "pair_sites": deepcopy(PAIR_SITES),
        "polymer": "DNA", "target_count": 42,
        "chemistry": {"five_prime_state": "OH", "five_prime_sites": list(FIVE_PRIME_SITES),
                      "terminal_phosphate_sites": [], "removed_coordinate_atoms": removed,
                      "internal_phosphates": "PRESERVED"},
        "autosol": {"policy": "disabled", "reason": recipe_policy["autosol"]["reason"]},
        "dictionary_selection": "Ordinary source lookup and ReadySet; no preselected numerical dictionaries or previous post-MR coordinates",
        "native_tools": "NOT_RUN", "human_review": "NOT_PERFORMED",
    }
    with (root / "synthetic-inputs.json").open("xb") as stream:
        stream.write(_json_bytes(receipt))
    validation = validate_synthetic_dna_inputs(root)
    return {**receipt, "root": str(root), "dataset": str(root / "dataset"),
            "recipe": str(root / "synthetic-dna-combined.toml"), "validation": validation}
