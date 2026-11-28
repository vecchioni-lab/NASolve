"""Remeasure the nucleic-acid polymer bond and angle findings in a wwPDB return."""
from collections import Counter
from decimal import Decimal, DecimalException
from math import dist, isfinite, ulp

from .cif_deposition_links import _NA_TYPES, _cif_block, _coordinates, _rows
from .topostitch_contacts import _angle


_FAMILIES = {
    "standard": ("intra", "obs", "Z", "count_"),
    "mogul": ("mogul", "obsval", "Zscore", "count_mogul_"),
}


def _value(row, key):
    try:
        value = float(row[key])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"Missing or invalid validation value {key}") from exc
    if row[key] is False or not isfinite(value):
        raise ValueError(f"Invalid validation value {key}")
    return value


def _terms(block, selected_family):
    instances = {}
    for row in _rows(block, "_pdbx_vrpt_model_instance."):
        key = row.get("id")
        if not key or key in instances:
            raise ValueError("Validation instance IDs must be present and unique")
        instances[key] = row
    terms, seen = [], set()
    for family, (code, observation, score, prefix) in _FAMILIES.items():
        if selected_family not in ("all", family):
            continue
        for kind, size in (("bond", 2), ("angle", 3)):
            counts = Counter()
            category = f"_pdbx_vrpt_instance_{code}_{kind}_outliers."
            for row in _rows(block, category):
                key = row.get("instance_id")
                if key not in instances:
                    raise ValueError(f"Unknown validation instance in {category}")
                atoms = [str(row.get(f"atom_{i}") or "").replace("*", "'") for i in range(1, size + 1)]
                identity = (family, key, min(tuple(atoms), tuple(reversed(atoms))))
                if "" in atoms or len(set(atoms)) != size or identity in seen:
                    raise ValueError(f"Missing, repeated or duplicate atom identity in {category}")
                seen.add(identity)
                counts[key] += 1
                mean, sigma = _value(row, "mean"), _value(row, "stdev")
                if sigma <= 0:
                    raise ValueError(f"Non-positive reported standard deviation in {category}")
                observed = _value(row, observation)
                try:
                    exponent = Decimal(row[observation]).as_tuple().exponent
                    half_step = float(Decimal("0.5").scaleb(exponent))
                except (DecimalException, OverflowError) as exc:
                    raise ValueError("Invalid printed precision in validation observation") from exc
                if not isfinite(half_step) or half_step <= 0:
                    raise ValueError("Invalid printed precision in validation observation")
                terms.append(dict(family=family, kind=kind, instance_id=key, atoms=atoms, reported=observed,
                                  half_print_step=half_step, mean=mean, stdev=sigma, reported_z=_value(row, score)))
            for key, instance in instances.items():
                declared = instance.get(f"{prefix}{kind}_outliers")
                if declared and int(declared) != counts[key]:
                    raise ValueError(f"Validation {kind} count differs from {category} for instance {key}")
    return instances, terms


def _measurement(geometry, instance, term, gemmi):
    coords, entity_by_chain = geometry
    label = instance.get("label_seq_id")
    if not label or not str(label).isdigit() or not instance.get("PDB_model_num"):
        return None
    site = (instance["PDB_model_num"], instance.get("label_asym_id"), int(label))
    component = instance.get("label_comp_id")
    if (not component or not instance.get("entity_id") or
            entity_by_chain.get(site[1]) != instance["entity_id"] or
            any(it[:4] == (*site, component) for it in coords.sequence_conflicts)):
        return None
    author = (instance.get("auth_asym_id"), instance.get("auth_seq_id"), instance.get("PDB_ins_code") or "")
    if not all(author[:2]) or coords.authors.get(site) != {author}:
        return None
    alternate = instance.get("label_alt_id") or ""
    positions, elements, alternates = [], [], []
    for name in term["atoms"]:
        hit = coords.locate(site, name, component, alternate)
        if hit is None:
            return None
        key, xyz = hit
        if key[2] and key[2] != alternate:
            return None
        element = coords.atom_elements[site, key]
        if not gemmi.Element(element).atomic_number:
            return None
        positions.append(xyz)
        elements.append(element)
        alternates.append(key[2])
    value = dist(*positions) if term["kind"] == "bond" else _angle(positions)
    if value is None or not isfinite(value):
        return None
    widths = (value - term["mean"]) / term["stdev"]
    if not isfinite(widths):
        raise ValueError("Coordinate residual exceeds the supported numeric range")
    return dict(measured=value, in_report_widths=widths, elements=elements, atom_alt_ids=alternates)


def _model(path, entry_ids, requested_atoms, gemmi):
    digest, block = _cif_block(path, "_atom_site.id", "coordinate", gemmi)
    entry = str(next(_rows(block, "_entry."), {}).get("id") or "").upper()
    pdb_codes, depositions = set(), set()
    for row in _rows(block, "_database_2."):
        code = str(row.get("database_code") or "").upper()
        database = str(row.get("database_id") or "").upper()
        if database == "PDB" and code:
            pdb_codes.add(code)
        if database == "WWPDB" and code:
            depositions.add(code)
    direct = entry in entry_ids
    mapped_deposition = bool(pdb_codes) and depositions == {entry}
    if not entry or not pdb_codes <= entry_ids or not (direct or mapped_deposition):
        raise ValueError("Coordinate entry identity differs from the validation report")
    types = {r.get("entity_id"): str(r.get("type") or "").lower() for r in _rows(block, "_entity_poly.")}
    entities = {r.get("id"): str(r.get("type") or "").lower() for r in _rows(block, "_entity.")}
    other = {k for k, t in types.items() if t and t not in _NA_TYPES}
    other.update(k for k, t in entities.items() if t in ("non-polymer", "water", "branched", "macrolide"))
    chains = {r.get("id"): r.get("entity_id") for r in _rows(block, "_struct_asym.")}
    return digest, (_coordinates(block, gemmi, requested_atoms=requested_atoms), chains), other


def inspect_deposition_geometry(reference, validation, *, candidate=None, family="all"):
    """Use a returned report's original empirical references only at the reported atoms."""
    try:
        import gemmi
    except ImportError as exc:
        raise ValueError("Deposition geometry inspection requires NASolve[topology]") from exc
    if family != "all" and family not in _FAMILIES:
        raise ValueError("Select a known validation family: all, standard or mogul")
    digest, block = _cif_block(validation, "_pdbx_vrpt_model_instance.id", "validation", gemmi)
    summaries = list(_rows(block, "_pdbx_vrpt_summary."))
    if len(summaries) != 1 or not summaries[0].get("entry_id"):
        raise ValueError("Validation report must identify one entry")
    summary = summaries[0]
    entry = summary["entry_id"]
    ids = {str(i).upper() for i in (entry, summary.get("extended_entry_id")) if i}
    instances, findings = _terms(block, family)
    names = {atom for row in findings for atom in row["atoms"]}
    ref_sha, source, other_entities = _model(reference, ids, names, gemmi)
    candidate_sha, revised = None, None
    if candidate is not None:
        candidate_sha, revised, _ = _model(candidate, ids, names, gemmi)
    rows = []
    outside = Counter()
    for term in findings:
        item = instances[term["instance_id"]]
        if item.get("entity_id") in other_entities:
            outside[term["family"]] += 1
            continue
        identity = {key: item.get(key) for key in ("PDB_model_num", "entity_id", "label_asym_id", "label_seq_id",
                                                   "label_comp_id", "auth_asym_id", "auth_seq_id")}
        identity.update(alt_id=item.get("label_alt_id") or "", insertion_code=item.get("PDB_ins_code") or "")
        first = _measurement(source, item, term, gemmi)
        difference = first["measured"] - term["reported"] if first is not None else None
        status = "SOURCE_UNMEASURED" if first is None else "SOURCE_MISMATCH"
        if difference is not None:
            rounding = term["half_print_step"] + 2 * ulp(max(abs(first["measured"]), abs(term["reported"])))
            if abs(difference) <= rounding:
                status = "REMEASURED"
        rows.append(dict(**term, instance=identity, source=first, source_minus_reported=difference,
                         candidate=None, status=status))
    reproduced = sum(row["status"] == "REMEASURED" for row in rows)
    if revised is not None and reproduced == len(rows):
        for row in rows:
            value = _measurement(revised, instances[row["instance_id"]], row, gemmi)
            if value is None or any(value[key] != row["source"][key] for key in ("elements", "atom_alt_ids")):
                row["status"] = "CANDIDATE_UNMEASURED"
            else:
                row["candidate"] = value
    status = "REVIEW" if any(r["status"] != "REMEASURED" for r in rows) else "REMEASURED"
    if not rows:
        status = "NO_REPORTED_TERMS"
    families = {}
    for name in _FAMILIES if family == "all" else (family,):
        selected = [r for r in rows if r["family"] == name]
        families[name] = {
            "reported": len(selected),
            "source_reproduced": sum(r["status"] in ("REMEASURED", "CANDIDATE_UNMEASURED") for r in selected),
            "candidate_measured": sum(r["candidate"] is not None for r in selected),
        }
    return dict(schema_version=1, status=status, entry_id=entry, family=family, families=families, reference_sha256=ref_sha,
                validation_sha256=digest, candidate_sha256=candidate_sha, supported_terms=len(rows),
                reproduced_terms=reproduced, excluded_non_nucleic_acid=dict(outside), terms=rows,
                scope="Previously reported within-residue bond lengths and angles in nucleic-acid polymer entities. "
                      "Both models are scored on the report's original reference. New outliers, inter-residue links, "
                      "a changed reference class and overall deposition acceptance require separate checks.")


def print_deposition_geometry(report):
    print(f"{report['entry_id']} reproduced {report['reproduced_terms']} of {report['supported_terms']} "
          f"reported nucleic-acid bond and angle measurements ({report['family']}).")
    if report["candidate_sha256"] and report["reproduced_terms"] < report["supported_terms"]:
        print("The source differs from the return. Candidate scores are withheld for this comparison.")
    for row in report["terms"]:
        site = row["instance"]
        text = (f"  {row['family']} {site['auth_asym_id']} {site['auth_seq_id']}{site['insertion_code']} "
                f"{site['label_comp_id']} {'–'.join(row['atoms'])}")
        unit = "Å" if row["kind"] == "bond" else "°"
        if row["candidate"]:
            print(f"{text} moved from {row['source']['measured']:.3f} to {row['candidate']['measured']:.3f}{unit} "
                  f"({row['candidate']['in_report_widths']:+.2f} original widths).")
        elif row["source"] is not None:
            print(f"{text}  {row['status']}  source {row['source']['measured']:.4f}{unit}, "
                  f"reported {row['reported']:g}{unit}.")
        else:
            print(f"{text}  {row['status']}")
    print(report["scope"])
