#!/usr/bin/env python3
"""Package a fresh synthetic-DNA mechanics recipe with isolated source runtimes.

Only source code, packaged resources, and committed MR-frame templates enter
the shuttle. Donor diffraction and prior native results never enter the bundle.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _revision(root: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    return {"commit": git("rev-parse", "HEAD"),
            "working_tree_has_changes": bool(git("status", "--porcelain"))}


def build(root: Path, narestraints_root: Path, output: Path, *,
          template_name: str = "synthetic_dna_shuttle_template.py",
          delivery_prefix: str | None = None) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Shuttle already exists: {output}")
    if template_name == "cif_generation_probe_template.py":
        delivery_prefix = delivery_prefix or "04_Cedar"
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", delivery_prefix):
            raise ValueError("Delivery prefix must be 1–32 ASCII letters, numbers, underscores or hyphens")
    elif delivery_prefix is not None:
        raise ValueError("This shuttle template does not support a delivery prefix")
    members = {}
    for source, prefix in ((root / "src/nasolve", "src/nasolve"),
                           (narestraints_root / "restraints", "restraints"),
                           (root / "MR_frames/5W6W", "MR_frames/5W6W")):
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if not path.is_file() or "__pycache__" in relative.parts:
                continue
            if path.is_symlink():
                raise ValueError(f"Runtime resource must be a regular file: {path}")
            if path.suffix not in {".py", ".toml", ".json", ".cif", ".phil", ".eff", ".txt", ".xlsx", ".pdb"}:
                continue
            members[prefix + "/" + relative.as_posix()] = path.read_bytes()
    recipe = "docs/recipes/synthetic-dna-combined.toml"
    members[recipe] = (root / recipe).read_bytes()
    required = {recipe, "src/nasolve/synthetic_dna.py", "MR_frames/5W6W/5W6W_noPO4.pdb",
                "restraints/data/Ligands.xlsx"}
    if not required <= members.keys():
        raise ValueError("Synthetic-DNA runtime is incomplete")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            handle.writestr(info, data)
    metadata = {
        "schema_version": 1, "kind": "synthetic-dna-mechanics-shuttle",
        "nasolve_source": _revision(root), "narestraints_source": _revision(narestraints_root),
        "runtime_archive_sha256": _sha(archive.getvalue()),
        "runtime_files": {name: {"sha256": _sha(data), "size": len(data)}
                          for name, data in sorted(members.items())},
        "recipe": recipe, "autosol": "DISABLED", "experimental_phases": False,
        "private_diffraction_included": False, "prior_native_results_included": False,
        "dependencies": ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                         "tomli on Python 3.10", "Phenix and Coot for native execution"],
    }
    if template_name not in {"synthetic_dna_shuttle_template.py", "cif_generation_probe_template.py"}:
        raise ValueError("Unknown reviewed shuttle template")
    if template_name == "cif_generation_probe_template.py":
        metadata["kind"] = "cif-generation-probe-shuttle"
        metadata["delivery_prefix"] = delivery_prefix
        metadata["native_generation"] = "explicit-source-preserving-candidate-only"
        metadata["automatic_adoption"] = False
    template = (root / "scripts" / template_name).read_text()
    generated = template.replace("BUNDLE = None  # @bundle-metadata@", "BUNDLE = " + repr(metadata))
    generated = generated.replace("RUNTIME_BASE64 = None  # @runtime-base64@",
                                 "RUNTIME_BASE64 = " + repr(base64.b64encode(archive.getvalue()).decode("ascii")))
    compile(generated, str(output), "exec")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(generated)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--narestraints-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    metadata = build(Path(__file__).resolve().parents[1], args.narestraints_root.resolve(), args.output)
    print(json.dumps({"output": str(args.output), "files": len(metadata["runtime_files"]),
                      "sha256": _sha(args.output.read_bytes())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
