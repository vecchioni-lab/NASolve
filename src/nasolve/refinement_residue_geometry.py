"""Read the native intramonomer bond and angle targets at named PDB sites."""
from collections import Counter
from hashlib import sha256
from math import dist, sqrt
from pathlib import Path

from .checkpoints import CheckpointError, _ref_path, registry_path, resolve_checkpoint
from .cif_doctor_run import (_checked_registry, _final_geometry, _reference,
                             _require_registry_unchanged, _require_unchanged)
from .cif_phosphate_angles import _reads_as, visit_printed_angles
from .model_assessment import file_sha256
from .refinement_contact_geometry import validate_contact_sites
from .refinement_link_geometry import _model_labels, _printed_rows, _within


def _rows_for_sites(kind, text, labels, coordinates, components, atom_counts):
    rows = {site: [] for site in components}
    other_images = dict.fromkeys(components, 0)

    def observe(atoms, operators, origin, target, printed, sigma, weight, slack=0):
        site = atoms[0][0]
        if site not in rows or any(atom[0] != site for atom in atoms[1:]):
            return
        # A common isometry leaves internal distances and angles invariant.
        if len({operator or "x,y,z" for operator in operators}) > 1:
            other_images[site] += 1
            return
        points = [coordinates[atom] for atom in atoms]
        if kind == "bonds":
            measured = dist(*points)
            agrees = _within(measured, printed, extra=sqrt(3) * 0.001)
        else:
            measured, agrees = _reads_as(points, printed)
        if not agrees:
            names = "–".join(atom[2] for atom in atoms)
            raise ValueError(f"{site} {names} differs from the written coordinates or has undefined geometry")
        delta = measured - float(target)
        row = dict(atoms=[atom[2] for atom in atoms], origin=origin, target=float(target),
                   measured=measured, printed_model=float(printed), sigma=float(sigma),
                   signed_widths=delta / float(sigma), weight=float(weight))
        if kind == "bonds":
            row["slack"] = float(slack)
        rows[site].append(row)

    try:
        if kind == "bonds":
            headers, entries = _printed_rows(text, labels, intra_components=set(components.values()))
            for atoms, origin, values, image in entries:
                observe(atoms, (None, image), origin, values["ideal"], values["model"],
                        values["sigma"], values["weight"], values.get("slack", 0))
        else:
            def angle(atoms, operators, origin, values):
                observe(atoms, operators, origin, values[0], values[1], values[3], values[4])
            headers = visit_printed_angles(text, labels, angle)
    except ValueError as exc:
        return {site: dict(status="UNASSESSED", rows=None, sections=None, other_image_count=None,
                           reason=str(exc)) for site in rows}

    results = {}
    for site, observations in rows.items():
        observations.sort(key=lambda row: (-abs(row["signed_widths"]), row["atoms"], row["origin"]))
        if observations:
            status = "OBSERVED"
        elif not headers:
            status = "NOT_RECORDED"
        elif other_images[site]:
            status = "NO_SAME_IMAGE_ROWS"
        elif atom_counts[site] < (2 if kind == "bonds" else 3):
            status = "TOO_FEW_ATOMS"
        else:
            status = "NO_SITE_ROWS"
        results[site] = dict(status=status, sections=headers, other_image_count=other_images[site],
                             rows=observations if headers else None)
    return results


def _read(model, geometry, sites):
    raw, labels = _model_labels(model)
    model_hash = sha256(raw).hexdigest()
    coordinates = dict(labels.values())
    all_sites = sites is None
    components = {site: code for site, code, name in coordinates if all_sites or site in sites}
    if all_sites:
        sites = list(components)
    atom_counts = Counter(site for site, code, name in coordinates)
    missing = [site for site in sites if site not in components]
    if missing:
        raise ValueError("Requested residue absent from the model: " + ", ".join(missing))
    data = geometry.read_bytes() if geometry is not None else None
    geo_hash = sha256(data).hexdigest() if data is not None else None
    text = data.decode("utf-8") if data is not None else ""
    tables = {kind: _rows_for_sites(kind, text, labels, coordinates, components, atom_counts)
              for kind in ("bonds", "angles")}
    residues = [dict(site=site, component=components[site], modeled_atom_count=atom_counts[site],
                     bonds=tables["bonds"][site], angles=tables["angles"][site])
                for site in sites]
    coverage = {kind: dict(Counter(t["status"] for t in sections.values())) for kind, sections in tables.items()}
    statuses = {status for counts in coverage.values() for status in counts} - {"TOO_FEW_ATOMS"}
    status = next(iter(statuses)) if len(statuses) == 1 else "PARTIAL" if statuses else "TOO_FEW_ATOMS"
    if file_sha256(model) != model_hash or (geometry is not None and file_sha256(geometry) != geo_hash):
        raise ValueError("Model or geometry changed during the inspection")
    return dict(policy_id="printed-residue-geometry-v1", status=status, sites=residues, coverage=coverage,
                site_selection="all_model_sites" if all_sites else "named_sites",
                model_sha256=model_hash, geometry_sha256=geo_hash,
                scope="Intramonomer geometry in one crystal image, evaluated against the printed Phenix targets. "
                      "Signed widths are (coordinate value minus printed ideal) / printed sigma, before any bond slack. "
                      "These values describe refinement restraints; independent chemical validation is a separate measurement.")


def inspect_residue_geometry(model, sites, *, geometry=None, checkpoint=None):
    """Inspect an explicit PDB and GEO, or the model and final GEO of one checkpoint."""
    if sites is not None:
        validate_contact_sites(sites)
    source = Path(model).expanduser()
    if source.is_dir() or source.name == "report.json" or checkpoint is not None:
        if not checkpoint or not checkpoint.strip():
            raise ValueError("A numbered run needs an explicit --checkpoint")
        if geometry is not None:
            raise ValueError("Use the final geometry recorded by the named checkpoint")
        from .cif_numerical_replay import numerical_replay_scope
        with numerical_replay_scope():
            run, registry, _, report_ref, registry_ref = _checked_registry(source)
            record = resolve_checkpoint(registry, checkpoint)
            model_ref = record.get("model")
            if not isinstance(model_ref, dict) or not isinstance(model_ref.get("sha256"), str):
                raise CheckpointError("Checkpoint needs a written model with a recorded checksum")
            pdb = _ref_path(model_ref, "model", run)
            final = _final_geometry(run, record)
            geo, geo_ref = final if final is not None else (None, None)
            result = _read(pdb, geo, sites)
            pdb_snapshot = _reference(pdb, run)
            geo_snapshot = _reference(geo, run) if geo is not None else None
            if (not (result["model_sha256"] == pdb_snapshot["sha256"] == model_ref["sha256"].lower()) or
                    (geo_ref is not None and
                     not (result["geometry_sha256"] == geo_snapshot["sha256"] == geo_ref["sha256"].lower()))):
                raise CheckpointError("Residue geometry differs from the frozen model or geometry")
            result["checkpoint"] = dict(id=record["id"], parent=record.get("parent"),
                                        model=pdb_snapshot, geometry=geo_snapshot)
            _require_unchanged(pdb, pdb_snapshot)
            if geo is not None:
                _require_unchanged(geo, geo_snapshot)
            _require_unchanged(run / "report.json", report_ref)
            _require_registry_unchanged(registry_path(run), registry_ref)
            return result
    if geometry is None:
        raise ValueError("An explicit PDB needs its matching --geometry FINAL_GEO")
    return _read(source, Path(geometry).expanduser(), sites)


def flanking_residue_geometry(model, geometry, inspection, *, model_sha256, geometry_sha256):
    """Read each residue at the fitted junction and the same native reference links once."""
    from .cif_phosphate_restraints import _reference_group

    group = _reference_group(inspection)
    donor, donor_code, _ = inspection["o3"]
    acceptor, acceptor_code, _ = inspection["phosphate"]
    junction = [donor, acceptor]
    expected = {}
    for left, right in [junction, *group["links"]]:
        for site, code in ((left, donor_code), (right, acceptor_code)):
            if expected.setdefault(site, code) != code:
                raise ValueError(f"Conflicting native reference components at {site}")
    report = _read(model, geometry, list(expected))
    if report["model_sha256"] != model_sha256:
        raise ValueError("Flanking residues differ from the recorded model checksum")
    if report["geometry_sha256"] != geometry_sha256:
        raise ValueError("Flanking residues differ from the recorded final geometry checksum")
    for site in report["sites"]:
        if site["component"] != expected[site["site"]]:
            raise ValueError(f"Written residue at {site['site']} differs from the native reference component")
    return dict(report, junction=junction, ordinary_links=group["links"])


def print_residue_geometry(result, *, rows_per_site=4):
    """Print the largest raw discrepancies, with the unit, origin and coverage."""
    if "checkpoint" in result:
        print(f"Checkpoint {result['checkpoint']['id']}.")
    print("Distances and angles against the printed Phenix targets, in restraint widths.")

    def show(site, row, unit):
        qualifiers = [row["origin"]]
        if row["weight"] == 0:
            qualifiers.append("zero weight")
        if row.get("slack"):
            qualifiers.append(f"slack {row['slack']:.3f}{unit}")
        print(f"  {site['site']} {site['component']} {'–'.join(row['atoms'])} "
              f"{row['measured']:.3f}{unit}, target {row['target']:.3f}{unit}, "
              f"{row['signed_widths']:+.2f} widths ({', '.join(qualifiers)}).")

    if result["site_selection"] == "all_model_sites":
        for kind, unit in (("bonds", "Å"), ("angles", "°")):
            counts = result["coverage"][kind]
            print(f"{kind.capitalize()} across {len(result['sites'])} residues: "
                  + ", ".join(f"{count} {status}" for status, count in counts.items()))
            measured = [(site, row) for site in result["sites"] for row in site[kind]["rows"] or ()]
            for site, row in sorted(measured, key=lambda item: -abs(item[1]["signed_widths"]))[:4]:
                show(site, row, unit)
            for site in result["sites"]:
                section = site[kind]
                if section["status"] not in {"OBSERVED", "TOO_FEW_ATOMS"}:
                    print(f"  {site['site']} {section['status']}.", section.get("reason", ""))
                if section["other_image_count"]:
                    print(f"  {site['site']} has {section['other_image_count']} rows involving another crystal image.")
        return
    for site in result["sites"]:
        for kind, unit in (("bonds", "Å"), ("angles", "°")):
            section = site[kind]
            rows = section["rows"] or []
            print(f"{site['site']} {site['component']} {kind}: {section['status']} ({len(rows)} observed).")
            if section.get("reason"):
                print(" ", section["reason"])
            if section["other_image_count"]:
                print(f"  {section['other_image_count']} rows involve another crystal image.")
            for row in rows[:rows_per_site]:
                show(site, row, unit)
