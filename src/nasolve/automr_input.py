"""Dataset discovery and shared standard/nonstandard AutoMR input schema."""

from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Collection, Mapping

from .residue_aliases import LigandCodeError, ResolvedLigand, resolve_ligand, resolve_pair


class AutoMRInputError(RuntimeError):
    """Raised when an AutoMR request is incomplete, unsafe, or ambiguous."""


@dataclass(frozen=True)
class FrameSpec:
    name: str
    accession: str
    aliases: tuple[str, ...]
    catalogue_directory: str
    fallback_model: str


FRAME_SPECS: tuple[FrameSpec, ...] = (
    FrameSpec("W", "5W6W", ("W", "5W6W"), "5W6W", "C_G.pdb"),
    FrameSpec("3GBI", "3GBI", ("3GBI",), "3GBI", "C_C.pdb"),
)


@dataclass
class AutoMRIntent:
    mode: str | None = None
    frame: str | None = None
    pair: str | None = None
    model: str | None = None
    sequence_file: str | None = None
    mirror: bool = False
    allow_p1_standard: bool = False
    sequences: dict[str, str] = field(default_factory=dict)
    mutations: dict[str, str] = field(default_factory=dict)
    source: Path | None = None


@dataclass(frozen=True)
class DatasetFiles:
    root: Path
    reflections: Path
    metadata: Path
    summary: Path


@dataclass(frozen=True)
class ResolvedAutoMRInput:
    dataset: DatasetFiles
    mode: str
    frame: FrameSpec | None
    pair_text: str | None
    pair: tuple[ResolvedLigand, ResolvedLigand] | None
    model: Path
    model_source: str
    model_pair: tuple[ResolvedLigand, ResolvedLigand] | None
    exact_pair_model: bool | None
    catalogue_warnings: tuple[str, ...]
    allow_p1_standard: bool
    mirror: bool
    sequences: dict[str, str]
    sequence_file: Path | None
    mutations: dict[str, ResolvedLigand]
    config_source: Path | None


_ALLOWED_SECTIONS = {"automr", "sequences", "mutations"}
_ALLOWED_AUTOMR_KEYS = {
    "mode",
    "frame",
    "pair",
    "model",
    "sequence_file",
    "mirror",
    "allow_p1_standard",
}


def _validated_sequences(
    sequences: Mapping[str, str],
    context: str,
) -> dict[str, str]:
    validated: dict[str, str] = {}
    for raw_chain, raw_sequence in sequences.items():
        chain = raw_chain.strip()
        sequence = "".join(raw_sequence.split()).upper()
        if not chain or not sequence:
            raise AutoMRInputError(f"{context} chain names and sequences cannot be empty")
        if len(chain) != 1:
            raise AutoMRInputError(
                f"{context} chain {chain!r} must be one PDB chain identifier"
            )
        invalid = sorted(set(sequence) - set("ACGTU"))
        if invalid:
            raise AutoMRInputError(
                f"{context} chain {chain} contains unsupported sequence symbol(s): "
                + ", ".join(invalid)
            )
        if chain in validated:
            raise AutoMRInputError(f"{context} contains duplicate chain {chain!r}")
        validated[chain] = sequence
    return validated


def read_sequence_file(path: Path) -> dict[str, str]:
    """Read chain-labelled FASTA or ``CHAIN = SEQUENCE`` text."""
    source = path.expanduser().resolve()
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AutoMRInputError(f"Could not read sequence file {source}: {exc}") from exc
    meaningful = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not meaningful:
        raise AutoMRInputError(f"Sequence file is empty: {source}")
    parsed: dict[str, str] = {}
    if any(line.startswith(">") for line in meaningful):
        current: str | None = None
        chunks: list[str] = []

        def finish() -> None:
            if current is not None:
                if current in parsed:
                    raise AutoMRInputError(
                        f"Sequence file contains duplicate FASTA chain {current!r}"
                    )
                parsed[current] = "".join(chunks)

        for line in meaningful:
            if line.startswith(">"):
                finish()
                header = line[1:].strip()
                current = header.split()[0] if header else None
                chunks = []
                if current is None:
                    raise AutoMRInputError("FASTA sequence header must name a PDB chain")
            else:
                if current is None:
                    raise AutoMRInputError(
                        "FASTA sequence data appeared before the first chain header"
                    )
                chunks.append(line)
        finish()
    else:
        for line in meaningful:
            if line.count("=") != 1:
                raise AutoMRInputError(
                    "Non-FASTA sequence files must use CHAIN = SEQUENCE on each line"
                )
            chain, sequence = line.split("=", 1)
            chain = chain.strip()
            if chain in parsed:
                raise AutoMRInputError(
                    f"Sequence file contains duplicate chain {chain!r}"
                )
            parsed[chain] = sequence.strip()
    return _validated_sequences(parsed, f"Sequence file {source.name}")


def _parser() -> configparser.ConfigParser:
    parser = configparser.ConfigParser(
        interpolation=None,
        delimiters=("=",),
        comment_prefixes=("#", ";"),
        inline_comment_prefixes=("#", ";"),
        strict=True,
        empty_lines_in_values=False,
    )
    parser.optionxform = str
    return parser


def read_intent(path: Path | None) -> AutoMRIntent:
    """Read the canonical INI-style ``nasolve.txt`` input file."""
    if path is None:
        return AutoMRIntent()
    source = path.expanduser().resolve()
    if not source.is_file():
        raise AutoMRInputError(f"NASolve input file does not exist: {source}")
    parser = _parser()
    try:
        with source.open(encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, configparser.Error) as exc:
        raise AutoMRInputError(f"Could not read {source}: {exc}") from exc
    unknown_sections = set(parser.sections()) - _ALLOWED_SECTIONS
    if unknown_sections:
        raise AutoMRInputError(
            "Unknown nasolve.txt section(s): " + ", ".join(sorted(unknown_sections))
        )
    if "automr" not in parser:
        raise AutoMRInputError("nasolve.txt must contain an [automr] section")
    automr = dict(parser["automr"])
    unknown_keys = set(automr) - _ALLOWED_AUTOMR_KEYS
    if unknown_keys:
        raise AutoMRInputError(
            "Unknown [automr] setting(s): " + ", ".join(sorted(unknown_keys))
        )
    try:
        allow_p1_standard = parser["automr"].getboolean(
            "allow_p1_standard", fallback=False
        )
    except ValueError as exc:
        raise AutoMRInputError(
            "[automr] allow_p1_standard must be true or false"
        ) from exc
    try:
        mirror = parser["automr"].getboolean("mirror", fallback=False)
    except ValueError as exc:
        raise AutoMRInputError("[automr] mirror must be true or false") from exc
    sequences = _validated_sequences({
        chain.strip(): "".join(sequence.split())
        for chain, sequence in parser["sequences"].items()
    } if "sequences" in parser else {}, "[sequences]")
    mutations = {
        site.strip(): residue.strip()
        for site, residue in parser["mutations"].items()
    } if "mutations" in parser else {}
    if any(not site or not residue for site, residue in mutations.items()):
        raise AutoMRInputError("Mutation sites and residue values cannot be empty")
    return AutoMRIntent(
        mode=automr.get("mode") or None,
        frame=automr.get("frame") or None,
        pair=automr.get("pair") or None,
        model=automr.get("model") or None,
        sequence_file=automr.get("sequence_file") or None,
        mirror=mirror,
        allow_p1_standard=allow_p1_standard,
        sequences=sequences,
        mutations=mutations,
        source=source,
    )


def discover_dataset(root: Path) -> DatasetFiles:
    dataset = root.expanduser().resolve()
    if not dataset.is_dir():
        raise AutoMRInputError(f"Dataset directory does not exist: {dataset}")

    mtz_files = sorted(
        path for path in dataset.iterdir()
        if path.is_file() and path.suffix.casefold() == ".mtz"
    )
    staraniso_candidates = [
        path for path in mtz_files
        if "staraniso" in _normalized_name(path) and "alldata" in _normalized_name(path)
    ]
    if len(staraniso_candidates) == 1:
        reflections = staraniso_candidates[0]
    elif len(staraniso_candidates) > 1:
        raise AutoMRInputError(
            "Ambiguous STARANISO all-data MTZ files: "
            + ", ".join(path.name for path in staraniso_candidates)
        )
    elif len(mtz_files) == 1:
        reflections = mtz_files[0]
    elif not mtz_files:
        raise AutoMRInputError("Missing required reflection MTZ file")
    else:
        raise AutoMRInputError(
            "Ambiguous reflection MTZ files: " + ", ".join(path.name for path in mtz_files)
        )

    metadata_candidates = sorted(
        path for path in dataset.iterdir()
        if path.is_file()
        and path.suffix.casefold() == ".cif"
        and _normalized_name(path).startswith("data1")
    )
    if not metadata_candidates:
        raise AutoMRInputError("Missing required Data_1*.cif metadata file")
    if len(metadata_candidates) > 1:
        raise AutoMRInputError(
            "Ambiguous Data_1*.cif metadata files: "
            + ", ".join(path.name for path in metadata_candidates)
        )
    summaries = sorted(
        path for path in dataset.iterdir()
        if path.is_file() and path.name.casefold() == "summary.html"
    )
    if not summaries:
        raise AutoMRInputError("Missing required file: summary.html")
    if len(summaries) > 1:
        raise AutoMRInputError(
            "Ambiguous summary files: " + ", ".join(path.name for path in summaries)
        )
    summary = summaries[0]
    return DatasetFiles(dataset, reflections, metadata_candidates[0], summary)


def _normalized_name(path: Path) -> str:
    """Return a case/punctuation-insensitive filename stem for discovery."""
    return re.sub(r"[^a-z0-9]+", "", path.stem.casefold())


def normalize_frame(value: str) -> FrameSpec:
    cleaned = value.strip().casefold()
    for spec in FRAME_SPECS:
        if cleaned in {alias.casefold() for alias in spec.aliases}:
            return spec
    supported = ", ".join(spec.name for spec in FRAME_SPECS)
    raise AutoMRInputError(f"Unknown standard frame {value!r}; choose {supported}")


def locate_frames_directory(
    explicit: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Find the development or future package location of approved MR frames."""
    env = os.environ if environ is None else environ
    candidates: list[tuple[str, Path]] = []
    if explicit is not None:
        candidates.append(("--frames-dir", explicit.expanduser()))
    if env.get("NASOLVE_MR_FRAMES"):
        candidates.append(("NASOLVE_MR_FRAMES", Path(env["NASOLVE_MR_FRAMES"]).expanduser()))
    package_dir = Path(__file__).resolve().parent
    candidates.extend([
        ("package data", package_dir / "data" / "MR_frames"),
        ("repository MR_frames", package_dir.parents[1] / "MR_frames"),
    ])
    for _, candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    attempted = ", ".join(f"{label}={path}" for label, path in candidates)
    raise AutoMRInputError(
        "Standard mode needs the approved MR_frames directory. "
        "Use --frames-dir PATH or set NASOLVE_MR_FRAMES. Tried: " + attempted
    )


def _pair_from_model_name(
    path: Path,
    valid_ligand_codes: Collection[str] | None,
) -> tuple[ResolvedLigand, ResolvedLigand]:
    """Resolve the ordered TOKEN_TOKEN pair encoded by a catalogue filename."""
    if path.stem.count("_") != 1:
        raise AutoMRInputError(
            f"Invalid standard model filename {path.name!r}; use FIRST_SECOND.pdb"
        )
    first, second = path.stem.split("_", 1)
    try:
        return (
            resolve_ligand(first, valid_ligand_codes),
            resolve_ligand(second, valid_ligand_codes),
        )
    except LigandCodeError as exc:
        raise AutoMRInputError(f"Invalid standard model filename {path.name!r}: {exc}") from exc


def _resolve_frame_model(
    spec: FrameSpec,
    frames_dir: Path,
    requested_pair: tuple[ResolvedLigand, ResolvedLigand],
    valid_ligand_codes: Collection[str] | None,
) -> tuple[Path, tuple[ResolvedLigand, ResolvedLigand], bool, tuple[str, ...]]:
    catalogue = frames_dir / spec.catalogue_directory
    if not catalogue.is_dir():
        raise AutoMRInputError(
            f"Missing standard frame catalogue: {catalogue}"
        )
    files = sorted(
        path for path in catalogue.iterdir()
        if path.is_file() and path.suffix.casefold() == ".pdb"
    )
    if not files:
        raise AutoMRInputError(f"No PDB models found in standard frame catalogue {catalogue}")

    requested_codes = tuple(ligand.ligand_code for ligand in requested_pair)
    indexed: list[tuple[Path, tuple[ResolvedLigand, ResolvedLigand]]] = []
    warnings: list[str] = []
    for path in files:
        try:
            indexed.append((path, _pair_from_model_name(path, valid_ligand_codes)))
        except AutoMRInputError as exc:
            warnings.append(str(exc))
    matches = [
        (path, pair)
        for path, pair in indexed
        if tuple(ligand.ligand_code for ligand in pair) == requested_codes
    ]
    if len(matches) > 1:
        raise AutoMRInputError(
            "Ambiguous exact standard models for "
            f"{requested_codes[0]}:{requested_codes[1]}: "
            + ", ".join(path.name for path, _ in matches)
        )
    if matches:
        path, pair = matches[0]
        return path.resolve(), pair, True, tuple(warnings)

    fallback = catalogue / spec.fallback_model
    if not fallback.is_file():
        raise AutoMRInputError(
            f"Required fallback model for frame {spec.name} is missing: {fallback}"
        )
    fallback_pair = _pair_from_model_name(fallback, valid_ligand_codes)
    return fallback.resolve(), fallback_pair, False, tuple(warnings)


def _resolve_dataset_model(dataset: Path, configured: str | None) -> tuple[Path, str]:
    if configured:
        relative = Path(configured).expanduser()
        if relative.is_absolute():
            raise AutoMRInputError("Nonstandard model paths in nasolve.txt must be dataset-relative")
        model = (dataset / relative).resolve()
        try:
            model.relative_to(dataset)
        except ValueError as exc:
            raise AutoMRInputError("Nonstandard model path must remain inside the dataset") from exc
        if not model.is_file():
            raise AutoMRInputError(f"Configured MR model does not exist: {model}")
        if model.suffix.casefold() != ".pdb":
            raise AutoMRInputError("The current nonstandard model layer accepts PDB files only")
        return model, "nasolve.txt"
    candidates = sorted(path.resolve() for path in dataset.glob("*.pdb") if path.is_file())
    if not candidates:
        raise AutoMRInputError(
            "MODEL_REQUIRED: no top-level PDB model was found and standard mode was not selected"
        )
    if len(candidates) > 1:
        raise AutoMRInputError(
            "Ambiguous nonstandard MR models: " + ", ".join(path.name for path in candidates)
        )
    return candidates[0], "dataset discovery"


def _resolve_relative_input(dataset: Path, configured: str, label: str) -> Path:
    relative = Path(configured).expanduser()
    if relative.is_absolute():
        raise AutoMRInputError(f"{label} paths in nasolve.txt must be dataset-relative")
    selected = (dataset / relative).resolve()
    try:
        selected.relative_to(dataset)
    except ValueError as exc:
        raise AutoMRInputError(f"{label} path must remain inside the dataset") from exc
    if not selected.is_file():
        raise AutoMRInputError(f"Configured {label.lower()} does not exist: {selected}")
    return selected


def _validate_mutation_site(site: str) -> None:
    if site.count(":") != 1:
        raise AutoMRInputError(
            f"Mutation site {site!r} must use CHAIN:RESID syntax, for example A:8"
        )
    chain, residue = (part.strip() for part in site.split(":", 1))
    if not chain or not residue:
        raise AutoMRInputError(
            f"Mutation site {site!r} must use CHAIN:RESID syntax, for example A:8"
        )


def resolve_automr_input(
    root: Path,
    intent: AutoMRIntent,
    frame_override: str | None = None,
    pair_override: str | None = None,
    frames_dir: Path | None = None,
    allow_p1_standard: bool = False,
    mirror_override: bool = False,
    environ: Mapping[str, str] | None = None,
    valid_ligand_codes: Collection[str] | None = None,
) -> ResolvedAutoMRInput:
    """Apply CLI precedence, validate intent, and select exactly one model."""
    dataset = discover_dataset(root)
    configured_mode = intent.mode.strip().casefold() if intent.mode else None
    if configured_mode not in {None, "standard", "nonstandard"}:
        raise AutoMRInputError("[automr] mode must be standard or nonstandard")

    selected_frame = frame_override or intent.frame
    # A command-line frame explicitly changes the effective mode.  Otherwise an
    # explicit nonstandard mode is not silently reinterpreted.
    if frame_override:
        mode = "standard"
    elif configured_mode:
        mode = configured_mode
    elif selected_frame:
        mode = "standard"
    else:
        mode = "nonstandard"

    pair_text = pair_override or intent.pair
    frame: FrameSpec | None = None
    pair: tuple[ResolvedLigand, ResolvedLigand] | None = None
    model_pair: tuple[ResolvedLigand, ResolvedLigand] | None = None
    exact_pair_model: bool | None = None
    catalogue_warnings: tuple[str, ...] = ()
    effective_allow_p1 = bool(allow_p1_standard or intent.allow_p1_standard)
    effective_mirror = bool(mirror_override or intent.mirror)
    if mode == "standard":
        if not selected_frame:
            raise AutoMRInputError("Standard mode requires frame = W or frame = 3GBI")
        if not pair_text:
            raise AutoMRInputError("Standard mode requires an ordered pair, for example pair = D:T")
        frame = normalize_frame(selected_frame)
        try:
            pair = resolve_pair(pair_text, valid_ligand_codes)
        except LigandCodeError as exc:
            raise AutoMRInputError(str(exc)) from exc
        if intent.model and not frame_override:
            raise AutoMRInputError("Standard mode selects its model by frame; remove model = from [automr]")
        located_frames = locate_frames_directory(frames_dir, environ)
        model, model_pair, exact_pair_model, catalogue_warnings = _resolve_frame_model(
            frame, located_frames, pair, valid_ligand_codes
        )
        if exact_pair_model:
            model_source = f"standard frame catalogue ({frame.name}; exact pair)"
        else:
            model_source = (
                f"standard frame catalogue ({frame.name}; fallback {frame.fallback_model})"
            )
    else:
        if selected_frame and not frame_override:
            raise AutoMRInputError("Nonstandard mode cannot also specify a standard frame")
        if pair_text:
            raise AutoMRInputError(
                "pair = is only valid in standard mode; use exact [mutations] sites for nonstandard models"
            )
        model, model_source = _resolve_dataset_model(dataset.root, intent.model)

    sequence_file: Path | None = None
    sequences = dict(intent.sequences)
    if intent.sequence_file:
        if mode != "nonstandard":
            raise AutoMRInputError("sequence_file is currently supported only in nonstandard mode")
        if sequences:
            raise AutoMRInputError(
                "Use either [automr] sequence_file or inline [sequences], not both"
            )
        sequence_file = _resolve_relative_input(
            dataset.root, intent.sequence_file, "Sequence file"
        )
        sequences = read_sequence_file(sequence_file)

    resolved_mutations: dict[str, ResolvedLigand] = {}
    for site, residue in intent.mutations.items():
        _validate_mutation_site(site)
        try:
            resolved_mutations[site] = resolve_ligand(residue, valid_ligand_codes)
        except LigandCodeError as exc:
            raise AutoMRInputError(f"Mutation {site}: {exc}") from exc

    return ResolvedAutoMRInput(
        dataset=dataset,
        mode=mode,
        frame=frame,
        pair_text=pair_text,
        pair=pair,
        model=model,
        model_source=model_source,
        model_pair=model_pair,
        exact_pair_model=exact_pair_model,
        catalogue_warnings=catalogue_warnings,
        allow_p1_standard=effective_allow_p1,
        mirror=effective_mirror,
        sequences=sequences,
        sequence_file=sequence_file,
        mutations=resolved_mutations,
        config_source=intent.source,
    )


def format_intent(resolved: ResolvedAutoMRInput) -> str:
    """Return a canonical, re-readable snapshot of effective user intent."""
    lines = ["[automr]", f"mode = {resolved.mode}"]
    if resolved.mode == "standard":
        assert resolved.frame is not None and resolved.pair_text is not None
        lines.extend([f"frame = {resolved.frame.name}", f"pair = {resolved.pair_text}"])
        if resolved.allow_p1_standard:
            lines.append("allow_p1_standard = true")
    else:
        relative_model = resolved.model.relative_to(resolved.dataset.root).as_posix()
        lines.append(f"model = {relative_model}")
    if resolved.mirror:
        lines.append("mirror = true")
    if resolved.sequences:
        lines.extend(["", "[sequences]"])
        lines.extend(f"{chain} = {sequence}" for chain, sequence in resolved.sequences.items())
    if resolved.mutations:
        lines.extend(["", "[mutations]"])
        lines.extend(f"{site} = {ligand.token}" for site, ligand in resolved.mutations.items())
    return "\n".join(lines) + "\n"
