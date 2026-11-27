"""Compare measured intramonomer geometry across two authenticated readings."""
from collections import defaultdict
from itertools import islice


def _by_atoms(section):
    terms = defaultdict(list)
    for row in section["rows"] or ():
        atoms = tuple(row["atoms"])
        terms[min(atoms, atoms[::-1]), row["origin"]].append(row)
    return terms


def _parameters(row):
    return {k: row[k] for k in ("target", "sigma", "weight", "slack") if k in row}


def geometry_change(reference, current):
    """Match identical printed restraints before attributing a change to coordinates."""
    def source(report):
        result = {k: report[k] for k in ("model_sha256", "geometry_sha256", "site_selection")}
        if "checkpoint" in report:
            result["checkpoint"] = report["checkpoint"]
        return result

    earlier, later = ({s["site"]: s for s in report["sites"]} for report in (reference, current))
    matched = dict(bonds=0, angles=0)
    changes, unmatched, other_images = [], [], []
    for site in sorted(earlier.keys() | later.keys()):
        before, after = earlier.get(site), later.get(site)
        if before is None or after is None or before["component"] != after["component"]:
            unmatched.append(dict(site=site, status="SITE_CHANGED",
                                  reference_component=before["component"] if before else None,
                                  current_component=after["component"] if after else None))
            continue
        for kind in matched:
            first, last = before[kind], after[kind]
            site_key = dict(site=site, component=before["component"], kind=kind)
            if first["other_image_count"] or last["other_image_count"]:
                other_images.append(dict(**site_key, reference=first["other_image_count"],
                                         current=last["other_image_count"]))
            if first["status"] == last["status"] == "TOO_FEW_ATOMS":
                continue
            if first["status"] != "OBSERVED" or last["status"] != "OBSERVED":
                unmatched.append(dict(**site_key, status="INCOMPLETE_READING",
                                      reference_status=first["status"], current_status=last["status"],
                                      reference_reason=first.get("reason"), current_reason=last.get("reason")))
                continue
            old, new = _by_atoms(first), _by_atoms(last)
            for atoms, origin in sorted(old.keys() | new.keys()):
                key = dict(**site_key, atoms=list(atoms), origin=origin)
                a, b = old[atoms, origin], new[atoms, origin]
                pa, pb = list(map(_parameters, a)), list(map(_parameters, b))
                if len(a) == len(b) == 1 and pa == pb:
                    matched[kind] += 1
                    if a[0]["measured"] != b[0]["measured"]:
                        changes.append(dict(**key, **pa[0], reference=a[0]["measured"], current=b[0]["measured"],
                                            reference_widths=a[0]["signed_widths"], current_widths=b[0]["signed_widths"],
                                            change_in_absolute_widths=abs(b[0]["signed_widths"]) - abs(a[0]["signed_widths"])))
                else:
                    if not a or not b:
                        status = "ADDED_RESTRAINT" if b else "REMOVED_RESTRAINT"
                    else:
                        status = "AMBIGUOUS_RESTRAINT" if len(a) != 1 or len(b) != 1 else "CHANGED_RESTRAINT"
                    unmatched.append(dict(**key, status=status, reference=pa, current=pb))
    changes.sort(key=lambda row: -abs(row["change_in_absolute_widths"]))
    status = "PARTIAL" if unmatched else "OBSERVED" if sum(matched.values()) else "NO_MATCHED_RESTRAINTS"
    return dict(policy_id="printed-residue-geometry-change-v1", status=status,
                reference=source(reference), current=source(current), matched=matched, changes=changes,
                unmatched=unmatched, other_image_rows=other_images,
                scope="Same-site bonds and angles in a common image. Positive change means farther from the "
                      "same printed target in restraint widths, before any bond slack. Independent chemical "
                      "validation and the force that caused the change require separate evidence.")


def print_geometry_change(report):
    counts = report["matched"]
    print(f"Compared {counts['bonds']} bonds and {counts['angles']} angles with the same printed targets and weights.")
    for direction, sign in (("away from", 1), ("toward", -1)):
        rows = (r for r in report["changes"] if sign * r["change_in_absolute_widths"] > 0)
        for row in islice(rows, 4):
            unit = "Å" if row["kind"] == "bonds" else "°"
            qualifier = " (zero weight)" if row["weight"] == 0 else ""
            if row.get("slack"):
                qualifier += f" (slack {row['slack']:.3f} Å)"
            print(f"  {row['site']} {row['component']} {'–'.join(row['atoms'])} "
                  f"{row['reference']:.3f} → {row['current']:.3f}{unit}, "
                  f"{abs(row['change_in_absolute_widths']):.2f} widths {direction} "
                  f"{row['target']:.3f}{unit}{qualifier}.")
    if report["unmatched"]:
        print(f"{len(report['unmatched'])} unmatched restraints or site readings. Use --json for their identities.")
    if report["other_image_rows"]:
        print("Additional rows involve different crystal images. Use --json for their counts.")
