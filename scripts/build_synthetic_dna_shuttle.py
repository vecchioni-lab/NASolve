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


def prepare_branch_runner_destination(checkout: Path, output: Path) -> None:
    """Protect an explicitly selected local branch-artifact destination from Git.

    Older frozen everyday checkouts may lack the tracked ignore rule. Install
    only that rule in this clone's local exclude; never alter tracked files.
    """
    checkout = checkout.expanduser().resolve(strict=True)
    output = output.expanduser().absolute()
    relative = output.relative_to(checkout)
    if (len(relative.parts) < 4 or relative.parts[0] != 'branch-artifacts'
            or relative.parts[2] != 'runners' or output.suffix != '.py'
            or any(p.is_symlink() for p in output.parents)):
        raise ValueError('Require a separate branch-artifacts/BRANCH/runners Python output')
    if output.exists() or output.is_symlink():
        raise FileExistsError('Runner destination already exists')
    def git(*args):
        return subprocess.run(['git', '-C', str(checkout), *args], capture_output=True, text=True)
    top = git('rev-parse', '--show-toplevel')
    if top.returncode or Path(top.stdout.strip()).resolve() != checkout:
        raise ValueError('Artifact checkout must be the explicit Git worktree root')
    ignored = git('check-ignore', '-q', '--', str(output))
    if ignored.returncode not in {0, 1}:
        raise ValueError('Could not check local runner exclusion')
    if ignored.returncode:
        excluded = git('rev-parse', '--git-path', 'info/exclude')
        if excluded.returncode:
            raise ValueError('Could not locate this clone local Git exclude')
        path = Path(excluded.stdout.strip())
        if not path.is_absolute():
            path = checkout/path
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('Local exclude path cannot traverse a symlink')
        previous = path.read_bytes() if path.exists() else b''
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('ab') as handle:
            handle.write((b'\n' if previous and not previous.endswith(b'\n') else b'') + b'/branch-artifacts/\n')
        if git('check-ignore', '-q', '--', str(output)).returncode:
            raise ValueError('Local branch artifacts exclusion did not take effect')


def build(root: Path, narestraints_root: Path, output: Path, *,
          template_name: str = "synthetic_dna_shuttle_template.py",
          delivery_prefix: str | None = None,
          component_controls: tuple[str, ...] = ()) -> dict:
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Shuttle already exists: {output}")
    probe_templates = {
        "cif_generation_probe_template.py": "04_Cedar",
        "cif_native_probe_template.py": "05_Cedar",
        "cif_linked_probe_template.py": "06_Cedar",
        "cif_terminal_probe_template.py": "10_Cedar",
        "cif_terminal_bundle_probe_template.py": "12_Cedar",
        "cif_outgoing_bundle_probe_template.py": "13_Cedar",
        "cif_geometry_review_probe_template.py": "15_Cedar",
        "cif_construction_probe_template.py": "16_Cedar",
        "cif_fragment_restoration_probe_template.py": "17_Cedar",
        "cif_effective_source_recovery_probe_template.py": "18_Cedar",
        "cif_fixed_geometry_probe_template.py": "19_Cedar",
        "cif_na_policy_probe_template.py": "21_Cedar",
        "cif_na_geometry_probe_template.py": "22_Cedar",
        "cif_gradient_audit_probe_template.py": "23_Cedar",
        "cif_parallelity_audit_probe_template.py": "24_Cedar",
        "cif_corrected_gradient_probe_template.py": "25_Cedar",
        "cif_plane_order_probe_template.py": "26_Cedar",
        "cif_corrected_geometry_probe_template.py": "27_Cedar",
        "cif_geometry_continuation_probe_template.py": "28_Cedar",
        "cif_base_rotation_probe_template.py": "29_Cedar",
        "cif_numerical_recovery_probe_template.py": "30_Cedar",
        "mixed_pair_probe_template.py": "80_Cedar",
        "mixed_native_probe_template.py": "82_Cedar",
        "mixed_recovery_probe_template.py": "83_Cedar",
        "mixed_linked_recovery_probe_template.py": "84_Cedar",
        "mixed_context_probe_template.py": "86_Cedar",
        "mixed_gradient_probe_template.py": "89_Cedar",
        "mixed_geometry_probe_template.py": "90_Cedar",
    }
    if template_name in probe_templates:
        delivery_prefix = delivery_prefix or probe_templates[template_name]
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
    controls = []
    if component_controls:
        if (template_name not in {'cif_numerical_recovery_probe_template.py', 'mixed_pair_probe_template.py'}
                or len(component_controls) > 3 or len(set(component_controls)) != len(component_controls)):
            raise ValueError('Require one to three unique explicit numerical component controls')
        catalog = json.loads((root/'docs/cif-doctor-ccd-controls.json').read_text())
        for code in component_controls:
            rows = [r for r in catalog['components'] if r['code'] == code]
            if len(rows) != 1 or not rows[0].get('test_fixture'):
                raise ValueError('No pinned public fixture for component control: '+code)
            record = rows[0];relative = record['test_fixture'];fixture = root/relative
            if (Path(relative).is_absolute() or '..' in Path(relative).parts or fixture.is_symlink()
                    or not fixture.resolve().is_relative_to(root.resolve())):
                raise ValueError('Unsafe component control fixture')
            payload = fixture.read_bytes();pinned = record['source']
            if len(payload) != pinned['bytes'] or _sha(payload) != pinned['sha256']:
                raise ValueError('Public component control differs from pinned source')
            name = 'controls/'+code+'.cif';members[name] = payload
            controls.append({'component': code, 'path': name, 'size': len(payload),
                             'sha256': _sha(payload), 'source_url': pinned['requested_url']})
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
    if template_name not in {"synthetic_dna_shuttle_template.py", *probe_templates}:
        raise ValueError("Unknown reviewed shuttle template")
    if template_name == "cif_generation_probe_template.py":
        metadata["kind"] = "cif-generation-probe-shuttle"
        metadata["delivery_prefix"] = delivery_prefix
        metadata["native_generation"] = "explicit-source-preserving-candidate-only"
        metadata["automatic_adoption"] = False
    if template_name == "cif_native_probe_template.py":
        metadata["kind"] = "cif-native-probe-shuttle"
        metadata["delivery_prefix"] = delivery_prefix
        metadata["native_validation"] = "explicit-diagnostic-bundle-only"
        metadata["automatic_adoption"] = False
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "cif_linked_probe_template.py":
        metadata.update(kind="cif-linked-probe-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="explicit-source-preserving-linked-diagnostic",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "cif_terminal_probe_template.py":
        metadata.update(kind="cif-terminal-probe-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="installed-terminal-resources-only",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native resource inventory"]
    if template_name == "cif_terminal_bundle_probe_template.py":
        metadata.update(kind="cif-terminal-bundle-probe-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="explicit-terminal-and-reviewed-5cm-bundle-only",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native bundle interpretation"]
    if template_name == "cif_outgoing_bundle_probe_template.py":
        metadata.update(kind="cif-outgoing-bundle-probe-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="explicit-curated-outgoing-bundle-only",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native bundle interpretation"]
    if template_name == "cif_geometry_review_probe_template.py":
        metadata.update(kind="cif-captured-geometry-review-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="NOT_RUN_CAPTURED_EVIDENCE_ONLY", automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10"]
    if template_name == "cif_construction_probe_template.py":
        metadata.update(kind="cif-construction-provenance-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="NOT_RUN_FROZEN_CONSTRUCTION_EVIDENCE_ONLY", automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10"]
    if template_name == "cif_fragment_restoration_probe_template.py":
        metadata.update(kind="cif-fragment-restoration-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="explicit-separate-fragment-candidate-only", automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Phenix for native bundle interpretation"]
    if template_name == "cif_effective_source_recovery_probe_template.py":
        metadata.update(kind="cif-effective-source-recovery-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="explicit-source-and-fragment-candidates-only", automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix with eLBOW for native execution"]
    if template_name == "cif_fixed_geometry_probe_template.py":
        metadata.update(kind="cif-fixed-native-geometry-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="explicit-bounded-fixed-definition-geometry-only", automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Phenix for native geometry trial"]
    if template_name == "cif_na_policy_probe_template.py":
        metadata.update(kind="cif-na-policy-probe-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="explicit-narestraints-membership-two-coordinate-check",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "Phenix for native interpretation"]
    if template_name == "cif_na_geometry_probe_template.py":
        metadata.update(kind="cif-na-policy-geometry-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="explicit-bounded-verified-na-policy-geometry",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Phenix for native geometry trial"]
    if template_name == "cif_gradient_audit_probe_template.py":
        metadata.update(kind="cif-native-gradient-audit-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="saved-fixed-manager-gradient-evaluations-only",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native gradient evaluations"]
    if template_name == "cif_parallelity_audit_probe_template.py":
        metadata.update(kind="cif-native-parallelity-audit-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="fixed-policy-per-restraint-and-accumulated-gradients-only",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native plane-gradient evaluations"]
    if template_name == "cif_corrected_gradient_probe_template.py":
        metadata.update(kind="cif-native-corrected-gradient-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="explicit-complete-plane-accumulation-fixed-objective-audit",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native corrected-gradient validation"]
    if template_name == "cif_plane_order_probe_template.py":
        metadata.update(kind="cif-native-plane-order-gradient-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="explicit-both-first-planes-fixed-objective-audit",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native plane-order derivative validation"]
    if template_name == "cif_corrected_geometry_probe_template.py":
        metadata.update(kind="cif-corrected-na-geometry-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="bounded-native-qualified-correction-fixed-na-geometry",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for corrected native geometry trial"]
    if template_name == "cif_geometry_continuation_probe_template.py":
        metadata.update(kind="cif-corrected-na-geometry-continuation-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="bounded-qualified-full-precision-fixed-na-continuation",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for corrected native geometry continuation"]
    if template_name == "cif_base_rotation_probe_template.py":
        metadata.update(kind="cif-fixed-na-base-rotation-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="temporary-graph-selected-base-rotations-fixed-native-objective",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix for native orientation evaluations"]
    if template_name == "cif_numerical_recovery_probe_template.py":
        metadata.update(kind="cif-source-graph-numerical-recovery-shuttle",delivery_prefix=delivery_prefix,
                        native_validation="NOT_RUN_DICTIONARY_CANDIDATE_ONLY",automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "Phenix eLBOW for independent numerical generation"]
        if controls:
            metadata['component_controls'] = controls
            metadata['dependencies'].append('openpyxl for bundled NARestraints role controls')
    if template_name == "mixed_geometry_probe_template.py":
        metadata.update(kind="mixed-geometry-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="qualified-mixed-model-fixed-geometry-and-native-readback",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "mixed_gradient_probe_template.py":
        metadata.update(kind="mixed-gradient-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="initial-only-fixed-mixed-model-native-gradient-audit",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "mixed_context_probe_template.py":
        metadata.update(kind="mixed-context-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="fixed-mixed-model-source-declared-context-readback",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "mixed_linked_recovery_probe_template.py":
        metadata.update(kind="mixed-linked-recovery-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="fixed-mixed-linked-recovery-explicit-policy-readback",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "mixed_recovery_probe_template.py":
        metadata.update(kind="mixed-numerical-recovery-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="isolated-source-bound-deficient-numerics-recovery",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "mixed_native_probe_template.py":
        metadata.update(kind="mixed-eight-pair-native-shuttle", delivery_prefix=delivery_prefix,
                        native_validation="fixed-mixed-model-readyset-and-explicit-policy-readback",
                        automatic_adoption=False)
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "tomli on Python 3.10", "Phenix for native execution"]
    if template_name == "mixed_pair_probe_template.py":
        metadata.update(kind="mixed-eight-pair-construction-shuttle", delivery_prefix=delivery_prefix,
                        recipe="nasolve.cif_mixed_pair_fixture.build_mixed_pair_plan",
                        native_validation="NOT_RUN; CONSTRUCTION_AND_PDB_SELECTOR_COMPILATION_ONLY",
                        automatic_adoption=False, component_controls=controls,
                        default_model="MR_frames/5W6W/C_G.pdb")
        metadata["dependencies"] = ["Python >=3.10", "Biopython", "numpy", "openpyxl",
                                    "Phenix installation for read-only CCD sources",
                                    "Coot for one bounded construction"]
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
