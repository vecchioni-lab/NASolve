from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected one patch anchor, found {count}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ---- automr_input.py: user intent, frozen intent, and human-facing alias ----
replace_once(
    "src/nasolve/automr_input.py",
    "from .phosphate import PhosphateError, validate_op3_sites, validate_phosphate_intent\n",
    "from .phosphate import PhosphateError, validate_op3_sites, validate_phosphate_intent\n"
    "from .backbone import BackboneError, validate_backbone_sites\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "    allow_op3_sites: tuple[str, ...] = ()\n    op3_sites_explicit: bool = False\n",
    "    allow_op3_sites: tuple[str, ...] = ()\n"
    "    op3_sites_explicit: bool = False\n"
    "    backbone_sites: dict[str, str] = field(default_factory=dict)\n"
    "    allow_unreviewed_backbone: bool = False\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "    allow_op3_sites: tuple[str, ...] = ()\n    phosphate_intent: dict[str, object] | None = None\n",
    "    allow_op3_sites: tuple[str, ...] = ()\n"
    "    phosphate_intent: dict[str, object] | None = None\n"
    "    backbone_sites: dict[str, str] = field(default_factory=dict)\n"
    "    allow_unreviewed_backbone: bool = False\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    '_ALLOWED_SECTIONS = {"automr", "sequences", "mutations"}\n',
    '_ALLOWED_SECTIONS = {"automr", "sequences", "mutations", "backbones"}\n',
)
replace_once(
    "src/nasolve/automr_input.py",
    '    "allow_op3_sites",\n}\n',
    '    "allow_op3_sites",\n'
    '    "five_prime_phosphate_sites",\n'
    '    "allow_unreviewed_backbone",\n'
    '}\n',
)
replace_once(
    "src/nasolve/automr_input.py",
    "    try:\n        mirror = parser[\"automr\"].getboolean(\"mirror\", fallback=False)\n    except ValueError as exc:\n        raise AutoMRInputError(\"[automr] mirror must be true or false\") from exc\n",
    "    try:\n        mirror = parser[\"automr\"].getboolean(\"mirror\", fallback=False)\n    except ValueError as exc:\n        raise AutoMRInputError(\"[automr] mirror must be true or false\") from exc\n"
    "    try:\n        allow_unreviewed_backbone = parser[\"automr\"].getboolean(\n            \"allow_unreviewed_backbone\", fallback=False\n        )\n    except ValueError as exc:\n        raise AutoMRInputError(\n            \"[automr] allow_unreviewed_backbone must be true or false\"\n        ) from exc\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "    raw_op3 = automr.get(\"allow_op3_sites\", \"\").strip()\n    try:\n        allow_op3 = validate_op3_sites([v.strip() for v in raw_op3.split(\",\")] if raw_op3 else [])\n    except PhosphateError as exc:\n        raise AutoMRInputError(str(exc)) from exc\n",
    "    if \"allow_op3_sites\" in automr and \"five_prime_phosphate_sites\" in automr:\n"
    "        raise AutoMRInputError(\n"
    "            \"Use five_prime_phosphate_sites (preferred) or legacy allow_op3_sites, not both\"\n"
    "        )\n"
    "    phosphate_key = (\n"
    "        \"five_prime_phosphate_sites\"\n"
    "        if \"five_prime_phosphate_sites\" in automr\n"
    "        else \"allow_op3_sites\"\n"
    "    )\n"
    "    raw_op3 = automr.get(phosphate_key, \"\").strip()\n"
    "    try:\n"
    "        allow_op3 = validate_op3_sites(\n"
    "            [v.strip() for v in raw_op3.split(\",\")] if raw_op3 else []\n"
    "        )\n"
    "        backbone_sites = validate_backbone_sites(\n"
    "            {site.strip(): mode.strip() for site, mode in parser[\"backbones\"].items()}\n"
    "            if \"backbones\" in parser else {}\n"
    "        )\n"
    "    except (PhosphateError, BackboneError) as exc:\n"
    "        raise AutoMRInputError(str(exc)) from exc\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "        allow_op3_sites=allow_op3,\n        op3_sites_explicit=\"allow_op3_sites\" in automr,\n    )\n",
    "        allow_op3_sites=allow_op3,\n"
    "        op3_sites_explicit=(\n"
    "            \"allow_op3_sites\" in automr or \"five_prime_phosphate_sites\" in automr\n"
    "        ),\n"
    "        backbone_sites=backbone_sites,\n"
    "        allow_unreviewed_backbone=allow_unreviewed_backbone,\n"
    "    )\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "    try:\n        allow_op3 = validate_op3_sites(intent.allow_op3_sites)\n    except PhosphateError as exc:\n        raise AutoMRInputError(str(exc)) from exc\n",
    "    try:\n"
    "        allow_op3 = validate_op3_sites(intent.allow_op3_sites)\n"
    "        backbone_sites = validate_backbone_sites(intent.backbone_sites)\n"
    "    except (PhosphateError, BackboneError) as exc:\n"
    "        raise AutoMRInputError(str(exc)) from exc\n"
    "    if type(intent.allow_unreviewed_backbone) is not bool:\n"
    "        raise AutoMRInputError(\"allow_unreviewed_backbone must be true or false\")\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "        allow_op3_sites=allow_op3,\n        phosphate_intent=phosphate_intent,\n    )\n",
    "        allow_op3_sites=allow_op3,\n"
    "        phosphate_intent=phosphate_intent,\n"
    "        backbone_sites=backbone_sites,\n"
    "        allow_unreviewed_backbone=intent.allow_unreviewed_backbone,\n"
    "    )\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "    if resolved.mirror:\n        lines.append(\"mirror = true\")\n",
    "    if resolved.mirror:\n"
    "        lines.append(\"mirror = true\")\n"
    "    if resolved.allow_unreviewed_backbone:\n"
    "        lines.append(\"allow_unreviewed_backbone = true\")\n",
)
replace_once(
    "src/nasolve/automr_input.py",
    "    if resolved.mutations:\n        lines.extend([\"\", \"[mutations]\"])\n        lines.extend(f\"{site} = {ligand.token}\" for site, ligand in resolved.mutations.items())\n    return \"\\n\".join(lines) + \"\\n\"\n",
    "    if resolved.mutations:\n"
    "        lines.extend([\"\", \"[mutations]\"])\n"
    "        lines.extend(f\"{site} = {ligand.token}\" for site, ligand in resolved.mutations.items())\n"
    "    if resolved.backbone_sites:\n"
    "        lines.extend([\"\", \"[backbones]\"])\n"
    "        lines.extend(f\"{site} = {mode}\" for site, mode in resolved.backbone_sites.items())\n"
    "    return \"\\n\".join(lines) + \"\\n\"\n",
)

# ---- automr.py: freeze backbone intent and validate site existence ----
replace_once(
    "src/nasolve/automr.py",
    "from .phosphate import phosphate_intent_summary, validate_phosphate_intent, PhosphateError\n",
    "from .phosphate import phosphate_intent_summary, validate_phosphate_intent, PhosphateError\n"
    "from .backbone import make_backbone_policy\n",
)
replace_once(
    "src/nasolve/automr.py",
    "    return {\n        \"allow_op3_sites\": list(resolved.allow_op3_sites),\n",
    "    return {\n"
    "        \"allow_op3_sites\": list(resolved.allow_op3_sites),\n"
    "        \"backbone_policy\": make_backbone_policy(\n"
    "            resolved.backbone_sites,\n"
    "            allow_unreviewed=resolved.allow_unreviewed_backbone,\n"
    "        ),\n",
)
replace_once(
    "src/nasolve/automr.py",
    "    for site in resolved.allow_op3_sites:\n        chain, residue = site.split(\":\", 1)\n        if residue not in assessment.polymer_residue_ids_by_chain.get(chain, []):\n            raise AutoMRInputError(f\"OP3 request {site} does not exist in the MR model\")\n",
    "    for site in resolved.allow_op3_sites:\n"
    "        chain, residue = site.split(\":\", 1)\n"
    "        if residue not in assessment.polymer_residue_ids_by_chain.get(chain, []):\n"
    "            raise AutoMRInputError(f\"5'-phosphate request {site} does not exist in the MR model\")\n"
    "    for site in resolved.backbone_sites:\n"
    "        chain, residue = site.split(\":\", 1)\n"
    "        if residue not in assessment.polymer_residue_ids_by_chain.get(chain, []):\n"
    "            raise AutoMRInputError(f\"Backbone chemistry site {site} does not exist in the MR model\")\n",
)
replace_once(
    "src/nasolve/automr.py",
    "        phosphate_intent_summary(resolved.allow_op3_sites, resolved.phosphate_intent),\n",
    "        phosphate_intent_summary(resolved.allow_op3_sites, resolved.phosphate_intent),\n"
    "        (\"Backbone chemistry: standard phosphodiester\" if not resolved.backbone_sites else\n"
    "         \"Backbone chemistry exceptions: \" + \", \".join(\n"
    "             f\"{site}={mode}\" for site, mode in resolved.backbone_sites.items()\n"
    "         )),\n",
)

# ---- campaigns.py: freeze/validate the new intent without breaking old plans ----
replace_once(
    "src/nasolve/campaigns.py",
    "        \"sequences\": dict(intent.sequences), \"mutations\": dict(intent.mutations),\n        \"allow_op3_sites\": list(intent.allow_op3_sites),\n",
    "        \"sequences\": dict(intent.sequences), \"mutations\": dict(intent.mutations),\n"
    "        \"allow_op3_sites\": list(intent.allow_op3_sites),\n"
    "        \"backbones\": dict(intent.backbone_sites),\n"
    "        \"allow_unreviewed_backbone\": intent.allow_unreviewed_backbone,\n",
)
replace_once(
    "src/nasolve/campaigns.py",
    "            \"phosphate_intent\": resolved.phosphate_intent,\n            \"pair\": resolved.pair_text,",
    "            \"phosphate_intent\": resolved.phosphate_intent,\n"
    "            \"backbones\": dict(resolved.backbone_sites),\n"
    "            \"allow_unreviewed_backbone\": resolved.allow_unreviewed_backbone,\n"
    "            \"pair\": resolved.pair_text,",
)
replace_once(
    "src/nasolve/campaigns.py",
    "            for boolean in (\"mirror\", \"allow_p1_standard\"):\n                _require(config.get(boolean), bool, f\"{name}.{boolean}\")\n",
    "            for boolean in (\"mirror\", \"allow_p1_standard\"):\n"
    "                _require(config.get(boolean), bool, f\"{name}.{boolean}\")\n"
    "            if \"allow_unreviewed_backbone\" in config:\n"
    "                _require(config.get(\"allow_unreviewed_backbone\"), bool,\n"
    "                         f\"{name}.allow_unreviewed_backbone\")\n"
    "            if \"backbones\" in config:\n"
    "                from .backbone import BackboneError, validate_backbone_sites\n"
    "                try:\n"
    "                    validate_backbone_sites(config[\"backbones\"])\n"
    "                except BackboneError as exc:\n"
    "                    raise CampaignError(f\"Malformed campaign backbone chemistry: {exc}\") from exc\n",
)

# ---- campaign_stages.py: rebuild the exact frozen selection ----
replace_once(
    "src/nasolve/campaign_stages.py",
    "        allow_op3_sites=tuple(effective.get(\"allow_op3_sites\", [])),\n        phosphate_intent=effective.get(\"phosphate_intent\"),\n    )\n",
    "        allow_op3_sites=tuple(effective.get(\"allow_op3_sites\", [])),\n"
    "        phosphate_intent=effective.get(\"phosphate_intent\"),\n"
    "        backbone_sites=dict(effective.get(\"backbones\", {})),\n"
    "        allow_unreviewed_backbone=bool(effective.get(\"allow_unreviewed_backbone\", False)),\n"
    "    )\n",
)

# ---- phosphate.py: explicit passthrough suppresses only standard-backbone rules ----
replace_once(
    "src/nasolve/phosphate.py",
    "    inspect_sites: tuple[str, ...] = (),\n    allow_op3_sites: tuple[str, ...] = (),\n) -> dict[str, object]:\n",
    "    inspect_sites: tuple[str, ...] = (),\n"
    "    allow_op3_sites: tuple[str, ...] = (),\n"
    "    passthrough_sites: tuple[str, ...] = (),\n"
    ") -> dict[str, object]:\n",
)
replace_once(
    "src/nasolve/phosphate.py",
    "    allowed = set(validate_op3_sites(allow_op3_sites))\n",
    "    allowed = set(validate_op3_sites(allow_op3_sites))\n"
    "    passthrough = set(validate_op3_sites(passthrough_sites))\n"
    "    if allowed & passthrough:\n"
    "        raise PhosphateError(\n"
    "            \"A site cannot be both an explicit standard 5'-phosphate and an experimental backbone passthrough\"\n"
    "        )\n",
)
replace_once(
    "src/nasolve/phosphate.py",
    "    targets = [group for group in groups.values()\n               if any(a.name == \"OP3\" for a in group) or group[0].site in requested]\n",
    "    targets = [\n"
    "        group for group in groups.values()\n"
    "        if group[0].site not in passthrough\n"
    "        and (any(a.name == \"OP3\" for a in group) or group[0].site in requested)\n"
    "    ]\n",
)
replace_once(
    "src/nasolve/phosphate.py",
    "        \"mode\": \"op3-explicit-opt-in-v1\", \"allow_op3_sites\": list(allow_op3_sites)}\n",
    "        \"mode\": \"op3-explicit-opt-in-v1\",\n"
    "        \"allow_op3_sites\": list(allow_op3_sites),\n"
    "        \"experimental_passthrough_sites\": sorted(passthrough),\n"
    "        \"skipped\": [\n"
    "            {\"site\": site, \"reason\": \"user-authorized-nonstandard-backbone\"}\n"
    "            for site in sorted(passthrough)\n"
    "        ]}\n",
)
replace_once(
    "src/nasolve/phosphate.py",
    "    check_sites: tuple[str, ...] = (), allow_op3_sites: tuple[str, ...] = (),\n) -> dict[str, object]:\n",
    "    check_sites: tuple[str, ...] = (), allow_op3_sites: tuple[str, ...] = (),\n"
    "    passthrough_sites: tuple[str, ...] = (),\n"
    ") -> dict[str, object]:\n",
)
replace_once(
    "src/nasolve/phosphate.py",
    "    return _process_phosphates(source, destination, reference_model=reference_model,\n                              check_sites=check_sites, allow_op3_sites=allow_op3_sites)\n",
    "    return _process_phosphates(\n"
    "        source, destination, reference_model=reference_model,\n"
    "        check_sites=check_sites, allow_op3_sites=allow_op3_sites,\n"
    "        passthrough_sites=passthrough_sites,\n"
    "    )\n",
)
replace_once(
    "src/nasolve/phosphate.py",
    "    inspect_sites: tuple[str, ...] = (), check_sites: tuple[str, ...] = (),\n    reference_model: Path | None = None,\n) -> dict[str, object]:\n",
    "    inspect_sites: tuple[str, ...] = (), check_sites: tuple[str, ...] = (),\n"
    "    reference_model: Path | None = None, passthrough_sites: tuple[str, ...] = (),\n"
    ") -> dict[str, object]:\n",
)
replace_once(
    "src/nasolve/phosphate.py",
    "    result = _process_phosphates(source, None, allow_op3_sites=allow_op3_sites,\n                                inspect_sites=inspect_sites, check_sites=check_sites,\n                                reference_model=reference_model)\n",
    "    result = _process_phosphates(\n"
    "        source, None, allow_op3_sites=allow_op3_sites,\n"
    "        inspect_sites=inspect_sites, check_sites=check_sites,\n"
    "        reference_model=reference_model, passthrough_sites=passthrough_sites,\n"
    "    )\n",
)

# ---- ligand_profiles.py: authoritative 1AP logic respects passthrough sites ----
replace_once(
    "src/nasolve/ligand_profiles.py",
    "from .run_context import artifact_reference\n",
    "from .run_context import artifact_reference\n"
    "from .backbone import requested_backbone_policy\n",
)
replace_once(
    "src/nasolve/ligand_profiles.py",
    "def write_linked_profile(\n    model: Path, directory: Path, *, allow_op3_sites: tuple[str, ...] = (),\n) -> tuple[dict[str, object], tuple[Path, ...]]:\n",
    "def write_linked_profile(\n"
    "    model: Path, directory: Path, *, allow_op3_sites: tuple[str, ...] = (),\n"
    "    passthrough_sites: tuple[str, ...] = (),\n"
    ") -> tuple[dict[str, object], tuple[Path, ...]]:\n",
)
replace_once(
    "src/nasolve/ligand_profiles.py",
    "    audit = audit_phosphates(model, allow_op3_sites=allow_op3_sites,\n                             inspect_sites=tuple(inventory))\n",
    "    audit = audit_phosphates(\n"
    "        model, allow_op3_sites=allow_op3_sites, inspect_sites=tuple(inventory),\n"
    "        passthrough_sites=passthrough_sites,\n"
    "    )\n",
)
replace_once(
    "src/nasolve/ligand_profiles.py",
    "    allowed = requested_op3_sites(report)\n",
    "    allowed = requested_op3_sites(report)\n"
    "    backbone = requested_backbone_policy(report)\n"
    "    passthrough = tuple(backbone[\"experimental_passthrough_sites\"])\n",
)
replace_once(
    "src/nasolve/ligand_profiles.py",
    "    result = audit_phosphates(model, allow_op3_sites=allowed,\n                             check_sites=tuple(item[\"site\"] for item in modifications))\n",
    "    result = audit_phosphates(\n"
    "        model, allow_op3_sites=allowed,\n"
    "        check_sites=tuple(item[\"site\"] for item in modifications),\n"
    "        passthrough_sites=passthrough,\n"
    "    )\n",
)

# ---- postmr.py: ensure whole terminal phosphate + guarded passthrough ----
replace_once(
    "src/nasolve/postmr.py",
    "from .phosphate import PhosphateError, sanitize_phosphates, requested_op3_sites\n",
    "from .phosphate import PhosphateError, sanitize_phosphates, requested_op3_sites\n"
    "from .backbone import (\n"
    "    BackboneError, ensure_five_prime_phosphates, requested_backbone_policy,\n"
    ")\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "    phosphate_sites: tuple[str, ...] = (),\n    allow_op3_sites: tuple[str, ...] = (),\n) -> tuple[Path, Path, Path | None, list[str], dict[str, object]]:\n",
    "    phosphate_sites: tuple[str, ...] = (),\n"
    "    allow_op3_sites: tuple[str, ...] = (),\n"
    "    passthrough_sites: tuple[str, ...] = (),\n"
    ") -> tuple[Path, Path, Path | None, list[str], dict[str, object]]:\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "            updated, checked, reference_model=model, check_sites=phosphate_sites,\n            allow_op3_sites=allow_op3_sites,\n",
    "            updated, checked, reference_model=model, check_sites=phosphate_sites,\n"
    "            allow_op3_sites=allow_op3_sites, passthrough_sites=passthrough_sites,\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "    modified_pairs_only: bool = False,\n    data_root: Path | None = None,\n",
    "    modified_pairs_only: bool = False,\n"
    "    allow_unreviewed_backbone: bool = False,\n"
    "    data_root: Path | None = None,\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "    try:\n        allowed_op3 = requested_op3_sites(report)\n    except PhosphateError as exc:\n        raise PostMRPreparationError(str(exc)) from exc\n",
    "    try:\n"
    "        allowed_op3 = requested_op3_sites(report)\n"
    "        backbone_policy = requested_backbone_policy(report)\n"
    "    except (PhosphateError, BackboneError) as exc:\n"
    "        raise PostMRPreparationError(str(exc)) from exc\n"
    "    passthrough_sites = tuple(backbone_policy[\"experimental_passthrough_sites\"])\n"
    "    if passthrough_sites and not (\n"
    "        backbone_policy[\"allow_unreviewed\"] or allow_unreviewed_backbone\n"
    "    ):\n"
    "        raise PostMRPreparationError(\n"
    "            \"Non-standard backbone site(s) require explicit experimental passthrough consent: \"\n"
    "            + \", \".join(passthrough_sites)\n"
    "            + \". Set [automr] allow_unreviewed_backbone = true before a new run, \"\n"
    "              \"or use --allow-unreviewed-backbone for this PostMR attempt.\"\n"
    "        )\n"
    "    if set(passthrough_sites) & set(allowed_op3):\n"
    "        raise PostMRPreparationError(\n"
    "            \"A site cannot simultaneously request standard 5'-phosphate construction \"\n"
    "            \"and experimental backbone passthrough\"\n"
    "        )\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "    prepared = model_dir / \"prepared_model.pdb\"\n    try:\n        phosphate_before = sanitize_phosphates(\n            after_coot, prepared, reference_model=original, allow_op3_sites=allowed_op3,\n        )\n    except PhosphateError as exc:\n        raise PostMRPreparationError(f\"PostMR phosphate validation failed: {exc}\") from exc\n",
    "    terminal_ready = model_dir / \"terminal_phosphate_model.pdb\"\n"
    "    try:\n"
    "        terminal_phosphate = ensure_five_prime_phosphates(\n"
    "            after_coot, terminal_ready, allowed_op3\n"
    "        ) if allowed_op3 else None\n"
    "        if terminal_phosphate is None:\n"
    "            shutil.copyfile(after_coot, terminal_ready)\n"
    "    except BackboneError as exc:\n"
    "        raise PostMRPreparationError(f\"5'-terminal phosphate construction failed: {exc}\") from exc\n"
    "    prepared = model_dir / \"prepared_model.pdb\"\n"
    "    try:\n"
    "        phosphate_before = sanitize_phosphates(\n"
    "            terminal_ready, prepared, reference_model=original,\n"
    "            allow_op3_sites=allowed_op3, passthrough_sites=passthrough_sites,\n"
    "        )\n"
    "    except PhosphateError as exc:\n"
    "        raise PostMRPreparationError(f\"PostMR phosphate validation failed: {exc}\") from exc\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "                prepared, restraints_dir, allow_op3_sites=allowed_op3)\n",
    "                prepared, restraints_dir, allow_op3_sites=allowed_op3,\n"
    "                passthrough_sites=passthrough_sites)\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "        allow_op3_sites=allowed_op3,\n    )\n",
    "        allow_op3_sites=allowed_op3, passthrough_sites=passthrough_sites,\n"
    "    )\n",
)
replace_once(
    "src/nasolve/postmr.py",
    "        \"phosphate_cleanup\": {\n            \"before_restraints\": phosphate_before,\n            \"after_readyset\": phosphate_after,\n        },\n",
    "        \"phosphate_cleanup\": {\n"
    "            \"terminal_phosphate_ensure\": terminal_phosphate,\n"
    "            \"before_restraints\": phosphate_before,\n"
    "            \"after_readyset\": phosphate_after,\n"
    "        },\n"
    "        \"backbone_chemistry\": {\n"
    "            \"schema_version\": 1,\n"
    "            \"default\": \"standard_phosphodiester\",\n"
    "            \"sites\": dict(backbone_policy[\"sites\"]),\n"
    "            \"experimental_passthrough_sites\": list(passthrough_sites),\n"
    "            \"user_authorized\": bool(\n"
    "                backbone_policy[\"allow_unreviewed\"] or allow_unreviewed_backbone\n"
    "            ),\n"
    "            \"authorization_source\": (\n"
    "                \"frozen-input\" if backbone_policy[\"allow_unreviewed\"]\n"
    "                else \"postmr-cli-override\" if allow_unreviewed_backbone else None\n"
    "            ),\n"
    "            \"review_required\": bool(passthrough_sites),\n"
    "            \"review_status\": (\n"
    "                \"UNREVIEWED_NONSTANDARD_BACKBONE\" if passthrough_sites else \"NOT_REQUIRED\"\n"
    "            ),\n"
    "        },\n",
)

# ---- cli.py: explicit passthrough flag and two-step Coot review ----
replace_once(
    "src/nasolve/cli.py",
    "from .coot_view import CootViewError, launch_coot_view, resolve_run\n",
    "from .coot_view import (\n"
    "    CootViewError, launch_coot_view, resolve_run, resolve_view_profile,\n"
    ")\n"
    "from .backbone import BackboneError, requested_backbone_policy, write_backbone_review\n",
)
replace_once(
    "src/nasolve/cli.py",
    "    postmr.add_argument(\n        \"--modified-pairs-only\",\n        action=\"store_true\",\n        help=\"guess base pairs and restrain only pairs containing a modified nucleotide\",\n    )\n",
    "    postmr.add_argument(\n"
    "        \"--modified-pairs-only\",\n"
    "        action=\"store_true\",\n"
    "        help=\"guess base pairs and restrain only pairs containing a modified nucleotide\",\n"
    "    )\n"
    "    postmr.add_argument(\n"
    "        \"--allow-unreviewed-backbone\", action=\"store_true\",\n"
    "        help=(\"experimental: continue at explicitly marked non-standard backbone \"\n"
    "              \"sites without validating their linkage chemistry\"),\n"
    "    )\n"
    "    backbone_review = subparsers.add_parser(\n"
    "        \"backbone-review\",\n"
    "        help=\"inspect experimental backbone sites in Coot and record human review\",\n"
    "    )\n"
    "    backbone_review.add_argument(\n"
    "        \"run\", nargs=\"?\", type=Path,\n"
    "        help=\"NASolve run (default: active workspace run)\",\n"
    "    )\n"
    "    backbone_review.add_argument(\"--coot\", help=\"one-run Coot executable override\")\n",
)
replace_once(
    "src/nasolve/cli.py",
    "            modified_pairs_only=args.modified_pairs_only,\n        )\n",
    "            modified_pairs_only=args.modified_pairs_only,\n"
    "            allow_unreviewed_backbone=args.allow_unreviewed_backbone,\n"
    "        )\n",
)
replace_once(
    "src/nasolve/cli.py",
    "    print(f\"Report: {result.report_path}\")\n    return 0\n\n\ndef _autosol(args: argparse.Namespace) -> int:\n",
    "    print(f\"Report: {result.report_path}\")\n"
    "    try:\n"
    "        run_report = json.loads((result.run_directory / \"report.json\").read_text(encoding=\"utf-8\"))\n"
    "        policy = requested_backbone_policy(run_report)\n"
    "        pending = tuple(policy[\"experimental_passthrough_sites\"])\n"
    "    except (OSError, ValueError, BackboneError):\n"
    "        pending = ()\n"
    "    if pending:\n"
    "        print(_color(\"WARNING: unreviewed non-standard backbone chemistry: \" + \", \".join(pending), \"33\"))\n"
    "        print(\"NASolve did not validate those linkage atoms. After refinement, run:\")\n"
    "        print(\"  \" + shlex.join([\"./nasolve\", \"backbone-review\", str(result.run_directory)]))\n"
    "    return 0\n\n\n"
    "def _backbone_review(args: argparse.Namespace) -> int:\n"
    "    try:\n"
    "        config = load_config()\n"
    "        run = _workspace_run(args.run, config)\n"
    "        report = json.loads((run / \"report.json\").read_text(encoding=\"utf-8\"))\n"
    "        policy = requested_backbone_policy(report)\n"
    "        sites = tuple(policy[\"experimental_passthrough_sites\"])\n"
    "        if not sites:\n"
    "            print(\"No experimental backbone passthrough sites are recorded for this run.\")\n"
    "            return 0\n"
    "        if not sys.stdin.isatty():\n"
    "            raise ConfigError(\"backbone-review is interactive; run it in a terminal\")\n"
    "        print(_color(\"NON-STANDARD BACKBONE CHEMISTRY — REVIEW REQUIRED\", \"33\"))\n"
    "        print(\"Flagged site(s): \" + \", \".join(sites))\n"
    "        print(\"NASolve intentionally did not infer or validate their inter-residue linkage chemistry.\")\n"
    "        answer = input(\"Show the flagged result in Coot? [y/N]: \" ).strip().casefold()\n"
    "        if answer not in {\"y\", \"yes\"}:\n"
    "            print(\"Review remains pending.\")\n"
    "            return 2\n"
    "        coot = discover_coot(config, explicit=args.coot)\n"
    "        remember_coot(config, coot)\n"
    "        save_config(config)\n"
    "        view = launch_coot_view(run, coot.executable)\n"
    "        print(f\"Opened {view.model_path} in Coot (PID {view.pid}).\")\n"
    "        print(\"Inspect the flagged backbone site(s) and maps, then return here.\")\n"
    "        confirm = input(\"Confirm that you reviewed the non-standard backbone chemistry? [y/N]: \" ).strip().casefold()\n"
    "        if confirm not in {\"y\", \"yes\"}:\n"
    "            print(\"Review remains pending; passthrough provenance is unchanged.\")\n"
    "            return 2\n"
    "        review_dir = run / \"PostMR\" / \"BackboneReview\"\n"
    "        review_dir.mkdir(parents=True, exist_ok=True)\n"
    "        number = 1\n"
    "        while (review_dir / f\"review_{number:03d}.json\").exists():\n"
    "            number += 1\n"
    "        profile = resolve_view_profile(run)\n"
    "        review_path = review_dir / f\"review_{number:03d}.json\"\n"
    "        write_backbone_review(review_path, sites=sites, model=profile.model_path, reviewed=True)\n"
    "        print(_color(\"Backbone review recorded as USER_REVIEWED.\", \"32\"))\n"
    "        print(f\"Review record: {review_path}\")\n"
    "        print(\"Experimental passthrough provenance remains in the run report.\")\n"
    "        return 0\n"
    "    except (ConfigError, CootDiscoveryError, CootViewError, BackboneError, OSError, ValueError) as exc:\n"
    "        print(f\"Backbone review error: {exc}\", file=sys.stderr)\n"
    "        return 2\n\n\n"
    "def _autosol(args: argparse.Namespace) -> int:\n",
)
replace_once(
    "src/nasolve/cli.py",
    "    if args.command == \"autosol\":\n        return _autosol(args)\n",
    "    if args.command == \"backbone-review\":\n"
    "        return _backbone_review(args)\n"
    "    if args.command == \"autosol\":\n"
    "        return _autosol(args)\n",
)

# ---- README + changelog ----
replace_once(
    "README.md",
    "## Requirements\n",
    "## Backbone and terminal-phosphate chemistry\n\n"
    "NASolve treats ordinary DNA/RNA-like backbones as standard phosphodiesters. "
    "A requested 5'-terminal phosphate is a complete P/OP1/OP2/OP3 group; PostMR "
    "preserves a complete group, completes a missing OP3 when P/OP1/OP2 are present, "
    "or seeds the whole group from O5'-C5' when the phosphate is absent. New input "
    "files may use `five_prime_phosphate_sites`; the historical `allow_op3_sites` "
    "name remains readable for old frozen runs.\n\n"
    "Unsupported backbone chemistry is never guessed. Mark a site explicitly in "
    "`nasolve.txt` and opt into the experimental passthrough only when you intend "
    "to inspect the result yourself:\n\n"
    "```ini\n[automr]\nallow_unreviewed_backbone = true\n\n[backbones]\nA:12 = experimental_passthrough\n```\n\n"
    "Passthrough suppresses only NASolve's standard phosphate-linkage rules at the "
    "listed site. It does not disable pairing/stacking elsewhere and does not invent "
    "custom bonds. The run stays visibly unreviewed. After refinement use "
    "`./nasolve backbone-review RUN`; NASolve first asks whether to open the flagged "
    "result in Coot, then separately asks whether the chemistry was reviewed. "
    "Confirmation records the inspected model hash but never erases passthrough "
    "provenance.\n\n"
    "Reviewed arbitrary GNA/PNA/TNA linkage recipes and 3'-terminal phosphate "
    "construction are intentionally deferred until we have real validated examples. "
    "If you need one, contact the developers with the intended atom connections and "
    "deletions so it can become a reviewed recipe rather than a guess. See "
    "[Backbone chemistry](docs/backbone-chemistry.md), the "
    "[machine-readable schema](docs/backbone-chemistry.schema.json), and the "
    "[human recipe example](docs/backbone-recipe-example.txt).\n\n"
    "## Requirements\n",
)
replace_once(
    "CHANGELOG.md",
    "### Changed\n\n",
    "### Changed\n\n"
    "- Generalized the OP3-specific policy into an explicit standard-phosphodiester "
    "backbone contract. `five_prime_phosphate_sites` is the preferred user-facing "
    "name (legacy `allow_op3_sites` remains readable). PostMR now treats a requested "
    "5'-terminal phosphate as the complete P/OP1/OP2/OP3 group, preserving a complete "
    "group, completing missing OP3 from existing P/OP1/OP2, or seeding a whole missing "
    "group from O5'-C5' with recorded idealized starting geometry. Partial ambiguous "
    "groups still fail closed.\n"
    "- Added site-scoped `experimental_passthrough` for explicitly declared non-standard "
    "backbones. Standard phosphate rules are skipped only at those sites; no custom "
    "linkage is inferred. Passthrough requires explicit user authorization, persists in "
    "run/campaign provenance, and has a two-step `backbone-review` Coot/confirmation "
    "workflow that records the inspected model hash without erasing provenance. Reviewed "
    "custom backbone recipes and 3'-phosphate construction remain future work.\n\n",
)

# ---- synthetic passthrough regression in existing phosphate test suite ----
replace_once(
    "tests/test_phosphate.py",
    "    def test_orphan_ligand_atom_named_op3_requires_review(self):\n",
    "    def test_explicit_nonstandard_passthrough_skips_standard_phosphate_rules(self):\n"
    "        records = [\n"
    "            atom(1, \"OP3\", \"XYZ\", \"L\", 1, (0, 0, 0)),\n"
    "            atom(2, \"C7\", \"XYZ\", \"L\", 1, (1.4, 0, 0)),\n"
    "            \"END\\n\",\n"
    "        ]\n"
    "        report, cleaned = self.run_cleanup(records, passthrough_sites=(\"L:1\",))\n"
    "        self.assertEqual(report[\"removed\"], [])\n"
    "        self.assertEqual(report[\"experimental_passthrough_sites\"], [\"L:1\"])\n"
    "        self.assertEqual(cleaned, \"\".join(records))\n\n"
    "    def test_orphan_ligand_atom_named_op3_requires_review(self):\n",
)

print("Backbone feature patch applied successfully.")
