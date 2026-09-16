from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one patch anchor, found {count}: {old[:90]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# Review records must remain portable with the run rather than freezing a laptop path.
replace_once(
    "src/nasolve/backbone.py",
    "from typing import Mapping\n",
    "from typing import Mapping\n\nfrom .run_context import artifact_reference\n",
)
replace_once(
    "src/nasolve/backbone.py",
    '''def backbone_review_record(\n    *, sites: tuple[str, ...], model: Path, reviewed: bool\n) -> dict[str, object]:\n    return {\n        "schema_version": 1,\n        "status": "USER_REVIEWED" if reviewed else "UNREVIEWED",\n        "sites": list(sites),\n        "model": str(model.resolve()),\n        "model_sha256": sha256(model.read_bytes()).hexdigest(),\n        "updated_utc": datetime.now(timezone.utc).isoformat(),\n        "provenance": "experimental-passthrough; NASolve did not validate custom backbone connectivity",\n    }\n\n\ndef write_backbone_review(path: Path, *, sites: tuple[str, ...], model: Path, reviewed: bool) -> None:\n    value = backbone_review_record(sites=sites, model=model, reviewed=reviewed)\n    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n''',
    '''def backbone_review_record(\n    *, sites: tuple[str, ...], model: Path, run: Path, reviewed: bool\n) -> dict[str, object]:\n    return {\n        "schema_version": 1,\n        "status": "USER_REVIEWED" if reviewed else "UNREVIEWED",\n        "sites": list(sites),\n        "model": artifact_reference(model, run),\n        "model_sha256": sha256(model.read_bytes()).hexdigest(),\n        "updated_utc": datetime.now(timezone.utc).isoformat(),\n        "provenance": "experimental-passthrough; NASolve did not validate custom backbone connectivity",\n    }\n\n\ndef write_backbone_review(\n    path: Path, *, sites: tuple[str, ...], model: Path, run: Path, reviewed: bool\n) -> None:\n    value = backbone_review_record(sites=sites, model=model, run=run, reviewed=reviewed)\n    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n''',
)

# A complete requested terminal phosphate is still invalid if it is actually internally linked.
replace_once(
    "src/nasolve/backbone.py",
    '''        present = {atom.name for atom in group if atom.name in {"P", "OP1", "OP2", "OP3"}}\n        last_index = max(atom.index for atom in group)\n        template = o5.line\n        if present == {"P", "OP1", "OP2", "OP3"}:\n            report["preserved"].append({"site": site, "atoms": sorted(present)})\n            continue\n        if present == {"P", "OP1", "OP2"}:\n            p = _one(group, "P", site)\n            # A requested terminal group must not already be an internal phosphate.\n            incoming = [\n                atom for atom in atoms\n                if atom.site != site and atom.chain == p.chain and atom.name == "O3'"\n                and math.dist(atom.xyz, p.xyz) <= 2.1\n            ]\n            if incoming:\n                raise BackboneError(f"5'-phosphate {site}: missing OP3 conflicts with an internal O3'-P link")\n''',
    '''        present = {atom.name for atom in group if atom.name in {"P", "OP1", "OP2", "OP3"}}\n        last_index = max(atom.index for atom in group)\n        template = o5.line\n        p = _one(group, "P", site) if "P" in present else None\n        incoming = (\n            [\n                atom for atom in atoms\n                if atom.site != site and atom.chain == p.chain and atom.name == "O3'"\n                and math.dist(atom.xyz, p.xyz) <= 2.1\n            ]\n            if p is not None else []\n        )\n        if len(incoming) > 1:\n            raise BackboneError(f"5'-phosphate {site}: multiple possible incoming O3'-P links")\n        if incoming:\n            raise BackboneError(\n                f"5'-phosphate {site}: terminal phosphate request conflicts with an internal O3'-P link"\n            )\n        if present == {"P", "OP1", "OP2", "OP3"}:\n            report["preserved"].append({"site": site, "atoms": sorted(present)})\n            continue\n        if present == {"P", "OP1", "OP2"}:\n            assert p is not None\n''',
)

# Human confirmation writes a portable, run-anchored model reference.
replace_once(
    "src/nasolve/cli.py",
    '''        write_backbone_review(review_path, sites=sites, model=profile.model_path, reviewed=True)\n''',
    '''        write_backbone_review(\n            review_path, sites=sites, model=profile.model_path, run=run, reviewed=True\n        )\n''',
)

# After a successful standalone refinement, offer the requested Coot review immediately.
replace_once(
    "src/nasolve/cli.py",
    '''    if result.selected_as_current:\n        print(_color("Current checkpoint updated.", "32"))\n    else:\n        print("Current checkpoint unchanged; inspect or select this result explicitly.")\n    return result.exit_code\n''',
    '''    if result.selected_as_current:\n        print(_color("Current checkpoint updated.", "32"))\n    else:\n        print("Current checkpoint unchanged; inspect or select this result explicitly.")\n    if result.exit_code == 0:\n        try:\n            run_report = json.loads((run / "report.json").read_text(encoding="utf-8"))\n            backbone_policy = requested_backbone_policy(run_report)\n            pending_backbone = tuple(backbone_policy["experimental_passthrough_sites"])\n        except (OSError, ValueError, BackboneError):\n            pending_backbone = ()\n        if pending_backbone:\n            print()\n            print(_color("NON-STANDARD BACKBONE CHEMISTRY — REVIEW REQUIRED", "33"))\n            print("Flagged site(s): " + ", ".join(pending_backbone))\n            if sys.stdin.isatty():\n                # Review is deliberately advisory to refinement status: declining inspection\n                # leaves a persistent warning but does not turn a successful refinement into\n                # a failed crystallographic run.\n                _backbone_review(argparse.Namespace(run=run, coot=None))\n            else:\n                print("Interactive Coot review was not possible in this session. Run:")\n                print("  " + shlex.join(["./nasolve", "backbone-review", str(run)]))\n    return result.exit_code\n''',
)

# Focused chemistry and portability regressions.
replace_once(
    "tests/test_backbone.py",
    '''from nasolve.backbone import (\n    BackboneError,\n    ensure_five_prime_phosphates,\n    make_backbone_policy,\n    requested_backbone_policy,\n    validate_backbone_sites,\n)\n''',
    '''from nasolve.backbone import (\n    BackboneError,\n    backbone_review_record,\n    ensure_five_prime_phosphates,\n    make_backbone_policy,\n    requested_backbone_policy,\n    validate_backbone_sites,\n)\n''',
)
replace_once(
    "tests/test_backbone.py",
    '''    def test_builder_report_is_json_serializable(self):\n        report, _ = self.run_ensure(terminal_without_phosphate())\n        json.dumps(report)\n\n\nif __name__ == "__main__":\n''',
    '''    def test_complete_terminal_group_cannot_hide_internal_link(self):\n        records = terminal_without_phosphate()\n        records[1:1] = [\n            atom(20, "P", "DC", "D", 1, (1.6, 0.0, 0.0)),\n            atom(21, "OP1", "DC", "D", 1, (2.1, 1.4, 0.0)),\n            atom(22, "OP2", "DC", "D", 1, (2.1, -0.7, 1.2)),\n            atom(23, "OP3", "DC", "D", 1, (2.1, -0.7, -1.2)),\n            atom(24, "O3'", "DG", "D", 0, (1.65, 0.0, 0.0)),\n        ]\n        source = self.root / "internal.pdb"\n        output = self.root / "internal-output.pdb"\n        source.write_text("".join(records), encoding="utf-8")\n        with self.assertRaisesRegex(BackboneError, "internal O3'-P link"):\n            ensure_five_prime_phosphates(source, output, ("D:1",))\n\n    def test_review_record_uses_run_anchored_model_reference(self):\n        run = self.root / "run_001"\n        model_dir = run / "AutoRefine" / "round_001"\n        model_dir.mkdir(parents=True)\n        model = model_dir / "refined.pdb"\n        model.write_text("END\\n", encoding="utf-8")\n        record = backbone_review_record(\n            sites=("A:12",), model=model, run=run, reviewed=True\n        )\n        self.assertEqual(record["status"], "USER_REVIEWED")\n        self.assertEqual(record["model"]["anchor"], "run")\n        self.assertEqual(\n            record["model"]["relative_path"], "AutoRefine/round_001/refined.pdb"\n        )\n        self.assertNotIn(str(self.root), json.dumps(record["model"]))\n\n    def test_builder_report_is_json_serializable(self):\n        report, _ = self.run_ensure(terminal_without_phosphate())\n        json.dumps(report)\n\n\nif __name__ == "__main__":\n''',
)

# Update user-facing wording to make the automatic final prompt explicit.
replace_once(
    "README.md",
    '''The run stays visibly unreviewed. After refinement use `./nasolve backbone-review RUN`; NASolve first asks whether to open the flagged result in Coot, then separately asks whether the chemistry was reviewed. Confirmation records the inspected model hash but never erases passthrough provenance.\n''',
    '''The run stays visibly unreviewed. After a successful interactive AutoRefine, NASolve immediately offers to show the flagged result in Coot and then separately asks whether the chemistry was reviewed. You can defer that inspection and later run `./nasolve backbone-review RUN`. Confirmation records a portable reference plus the inspected model hash but never erases passthrough provenance.\n''',
)
replace_once(
    "docs/backbone-chemistry.md",
    '''The intended review interaction is:\n\n1. NASolve asks whether to show the flagged result in Coot (`y/n`).\n2. If opened, the user inspects the current model and maps.\n3. NASolve then asks whether the chemistry has been reviewed (`y/n`).\n4. Confirmation writes a separate review record with the inspected model hash\n   and changes the human status to `USER_REVIEWED`; it does not erase the fact\n   that passthrough chemistry was used.\n\nFor non-interactive campaigns, the same condition remains an inspection flag\nand can be reviewed later with the dedicated backbone review command.\n''',
    '''The review interaction is:\n\n1. After a successful interactive AutoRefine, NASolve asks whether to show the\n   flagged result in Coot (`y/n`). The same flow is available later through\n   `nasolve backbone-review RUN`.\n2. If opened, the user inspects the current model and maps.\n3. NASolve then asks whether the chemistry has been reviewed (`y/n`).\n4. Confirmation writes a separate review record with a run-anchored model\n   reference and the inspected model hash and marks it `USER_REVIEWED`; it does\n   not erase the fact that passthrough chemistry was used.\n\nDeclining review does not convert an otherwise successful refinement into a\nfailed run; the warning remains pending. For non-interactive campaigns, the\nsame condition remains an inspection flag and can be reviewed later with the\ndedicated backbone review command.\n''',
)

print("Backbone follow-up patch applied successfully.")
