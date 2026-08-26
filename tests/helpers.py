import stat
from pathlib import Path


def pdb_record(
    record: str,
    serial: int,
    atom: str,
    residue: str,
    chain: str,
    residue_number: int,
    occupancy: float = 1.0,
    element: str = "P",
) -> str:
    return (
        f"{record:<6}{serial:5d} {atom:>4s} {residue:>3s} {chain:1s}"
        f"{residue_number:4d}    {0.0:8.3f}{0.0:8.3f}{0.0:8.3f}"
        f"{occupancy:6.2f}{20.0:6.2f}          {element:>2s}\n"
    )


def model_text() -> str:
    return "".join([
        pdb_record("ATOM", 1, "P", "DA", "A", 1),
        pdb_record("ATOM", 2, "P", "DC", "A", 2),
        pdb_record("HETATM", 3, "MG", "MG", "A", 50, element="MG"),
        "END\n",
    ])


def make_dataset(root: Path, include_model: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "staraniso-alldata.mtz").write_bytes(b"mtz")
    (root / "data_1.cif").write_text(
        "data_test\n_symmetry.space_group_name_H-M 'H 3'\n"
    )
    (root / "summary.html").write_text(
        "<html>\nPossible space group P1\nSpacegroup name          H3\n</html>\n"
    )
    if include_model:
        (root / "search.pdb").write_text(model_text())
    return root


def make_mtz_dump(
    root: Path,
    symbol: str = "H 3",
    number: int = 146,
    matrix_symbol: str | None = None,
) -> Path:
    executable = root / "phenix.mtz.dump"
    matrix = symbol if matrix_symbol is None else matrix_symbol
    executable.write_text(
        "#!/bin/sh\n"
        f"echo 'Space group symbol from file: {symbol}'\n"
        f"echo 'Space group number from file: {number}'\n"
        f"echo 'Space group from matrices: {matrix} (No. {number})'\n"
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def make_phaser(
    root: Path,
    tfz: float | None = 8.4,
    llg: float = 121.0,
    return_code: int = 0,
    create_outputs: bool = True,
) -> Path:
    executable = root / "phenix.phaser"
    output_commands = ""
    if create_outputs:
        output_commands = (
            "printf 'MODEL\\nEND\\n' > PHASER.1.pdb\n"
            "printf 'mtz' > PHASER.1.mtz\n"
        )
    score_command = (
        f"echo 'SOLU SET RFZ=9.1 TFZ={tfz} LLG={llg}'\n"
        if tfz is not None else "echo 'No placed solution'\n"
    )
    executable.write_text(
        "#!/bin/sh\n"
        + output_commands
        + score_command
        + f"exit {return_code}\n"
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable
