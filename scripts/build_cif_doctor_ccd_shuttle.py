#!/usr/bin/env python3
"""Build a single offline CCD audit runner from reviewed repository sources.

The complete assessor and compatibility module are embedded unchanged. Only the
unchanged shared _Block/_blocks parser definitions and its exception are sliced
from the larger pipeline modules to avoid importing PostMR and Phenix adapters.
The output pins every payload source, each original module, and the control ZIP.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _definitions(source: str, names: tuple[str, ...]) -> str:
    tree = ast.parse(source)
    result = []
    for name in names:
        nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name]
        if len(nodes) != 1:
            raise ValueError("Cannot locate exactly one reviewed definition: " + name)
        node = nodes[0]
        start = min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])
        lines = source.splitlines(keepends=True)
        result.append("".join(lines[start - 1:node.end_lineno]).rstrip() + "\n")
    return "\n".join(result)


def build(root: Path, corpus_zip: Path, output: Path) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError("Shuttle output already exists: " + str(output))
    sources = {name: (root / "src" / "nasolve" / name).read_bytes() for name in
               ("cif_doctor.py", "dictionary_compatibility.py", "ligand_profiles.py", "phosphate.py")}
    # These definitions retain their exact source lines, including decorators.
    reader = ("from __future__ import annotations\nimport io\nimport re\n"
              "from dataclasses import dataclass\nfrom pathlib import Path\n"
              "from Bio.PDB.MMCIF2Dict import MMCIF2Dict\nfrom .phosphate import PhosphateError\n\n"
              + _definitions(sources["ligand_profiles.py"].decode("utf-8"), ("_Block", "_blocks"))).encode("utf-8")
    exception = _definitions(sources["phosphate.py"].decode("utf-8"), ("PhosphateError",)).encode("utf-8")
    payload_files = {"__init__.py": b'"""Private, hash-bound NASolve CCD shuttle runtime."""\n',
                     "cif_doctor.py": sources["cif_doctor.py"],
                     "dictionary_compatibility.py": sources["dictionary_compatibility.py"],
                     "ligand_profiles.py": reader, "phosphate.py": exception}
    runtime = io.BytesIO()
    with zipfile.ZipFile(runtime, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload_files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    zip_bytes = corpus_zip.read_bytes()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        manifest_bytes = archive.read("source_manifest.json")
    manifest = json.loads(manifest_bytes)
    metadata = {"schema_version": 1, "builder_policy": "offline-ccd-shuttle-v1",
                "control_zip_sha256": _sha(zip_bytes), "manifest_sha256": _sha(manifest_bytes),
                "component_count": len(manifest["components"]),
                "assessor_source_sha256": _sha(sources["cif_doctor.py"]),
                "runtime_archive_sha256": _sha(runtime.getvalue()),
                "source_modules": {name: {"repository_path": "src/nasolve/" + name,
                                           "sha256": _sha(data)} for name, data in sorted(sources.items())},
                "runtime_files": {name: {"sha256": _sha(data), "size": len(data),
                                         "scope": "unchanged complete module" if name in {"cif_doctor.py", "dictionary_compatibility.py"}
                                         else "unchanged selected definitions plus minimal imports" if name in {"ligand_profiles.py", "phosphate.py"}
                                         else "private package marker"} for name, data in sorted(payload_files.items())},
                "dependencies": ["Python >=3.10", "Biopython"], "network_required": False,
                "native_tools_run": False}
    template = (root / "scripts" / "cif_doctor_ccd_shuttle_template.py").read_text(encoding="utf-8")
    generated = template.replace("BUNDLE = None  # @bundle-metadata@", "BUNDLE = " + repr(metadata))
    generated = generated.replace("RUNTIME_BASE64 = None  # @runtime-base64@", "RUNTIME_BASE64 = " + repr(base64.b64encode(runtime.getvalue()).decode("ascii")))
    compile(generated, str(output), "exec")
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(generated)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    metadata = build(root, args.corpus_zip, args.output)
    print(json.dumps({"output": str(args.output), "assessor_source_sha256": metadata["assessor_source_sha256"],
                      "component_count": metadata["component_count"], "shuttle_sha256": _sha(args.output.read_bytes())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
