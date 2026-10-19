#!/usr/bin/env python3
"""Regenerate the editable CIF Doctor pipeline figure; standard-library only.

SVG labels remain real text, with named groups for vector-editor modification.
This developer/documentation helper is not part of CIF Doctor's runtime.
"""

from pathlib import Path
import re
from xml.sax.saxutils import escape

WIDTH, HEIGHT = 1200, 1190
DESTINATION = Path(__file__).with_name("cif-doctor-overview.svg")
FONT = "Arial, Helvetica, sans-serif"
INK = "#213443"
PIPE = "#214f70"
AUDIT = "#237466"


def text(x, y, content, *, size=24, weight="normal", color=INK, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">'
            f'{escape(content)}</text>')


def box(identifier, x, y, width, height, title, lines, *, audit=False):
    border, fill = (AUDIT, "#eef7f3") if audit else (PIPE, "#f0f5f9")
    parts = [f'<g id="{identifier}">',
             f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
             f'rx="10" fill="{fill}" stroke="{border}" stroke-width="2.5"/>',
             text(x + 22, y + 36, title, size=27, weight="bold", color=border)]
    parts.extend(text(x + 22, y + 70 + index * 30, line) for index, line in enumerate(lines))
    parts.append("</g>")
    return "\n".join(parts)


def path(identifier, commands, *, audit=False, arrow=True):
    color = AUDIT if audit else PIPE
    # Explicit dash segments and arrow polygons survive basic SVG-to-PDF
    # converters that omit marker elements or stroke-dasharray rendering.
    tokens = re.findall(r"[MHV]|-?\d+(?:\.\d+)?", commands)
    points = []
    cursor = 0
    while cursor < len(tokens):
        command = tokens[cursor]
        if command == "M":
            points.append((float(tokens[cursor + 1]), float(tokens[cursor + 2])))
            cursor += 3
        else:
            x, y = points[-1]
            value = float(tokens[cursor + 1])
            points.append((value, y) if command == "H" else (x, value))
            cursor += 2
    parts = [f'<g id="{identifier}">']
    for start, end in zip(points, points[1:]):
        if audit:
            dx, dy = end[0] - start[0], end[1] - start[1]
            length = abs(dx) + abs(dy)
            position = 0
            while position < length:
                stop = min(position + 9, length)
                first = (start[0] + dx * position / length, start[1] + dy * position / length)
                last = (start[0] + dx * stop / length, start[1] + dy * stop / length)
                parts.append(f'<path d="M {first[0]} {first[1]} L {last[0]} {last[1]}" '
                             f'fill="none" stroke="{color}" stroke-width="2.7"/>')
                position += 16
        else:
            parts.append(f'<path d="M {start[0]} {start[1]} L {end[0]} {end[1]}" '
                         f'fill="none" stroke="{color}" stroke-width="2.7"/>')
    if arrow:
        start, tip = points[-2:]
        dx, dy = tip[0] - start[0], tip[1] - start[1]
        length = abs(dx) + abs(dy)
        dx, dy = dx / length, dy / length
        base = (tip[0] - 15 * dx, tip[1] - 15 * dy)
        corners = [tip, (base[0] - 7 * dy, base[1] + 7 * dx),
                   (base[0] + 7 * dy, base[1] - 7 * dx)]
        parts.append('<polygon points="' + ' '.join(f'{x},{y}' for x, y in corners)
                     + f'" fill="{color}"/>')
    parts.append("</g>")
    return "\n".join(parts)


def build():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="180mm" height="178.5mm" '
             f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
             'aria-labelledby="title description">',
             '<title id="title">CIF Doctor around PostMR and ReadySet</title>',
             '<desc id="description">The existing model-preparation path runs from source dictionaries '
             'and an MR model through optional Coot mutation, prepared inputs, ReadySet and effective '
             'dictionary selection to existing PostMR gates and refinement. Dashed read-only audit '
             'branches inspect mutation sources, frozen source and runtime inputs, and the selected '
             'effective bundle. Explicit external linked candidates and native diagnostics check site definitions and selected proxies. '
             'Bounded source-declared ring comparisons retain all raw bond differences. '
             'Native site IDs and component-list metadata loops preserve reader contracts. '
             'Returned Cedar 09 native checks preserve formal-charge and terminal-chemistry review limits. '
             'A completed terminal-source review records installed parameters and a canonical hydroxyl control. '
             'Selected modified-terminal candidates and explicit 5CM preparation pass installed projected-definition and unaffected-proxy checks; formal-charge readback remains unavailable. '
             'A separate graph-selected outgoing-oxygen candidate layer preserves existing dictionaries and modifiers. Returned Cedar 14 clears all four outgoing-hydrogen findings and passes installed projected-definition, captured-baseline replay and exact modifier-ID checks; source, charge and achieved-geometry limits remain open. '
             'A separate captured Cartesian review measures simple-bond distances, angles and ordered chirality volumes. Nominal deviations are descriptive; native residuals, deferred geometry and absolute stereochemistry remain unassessed. '
             'Returned Cedar 15 source-versus-model and coordinate-lineage comparisons expose earlier model distortions. '
             'Cedar 16 freezes original stages and parses saved Coot declarations without execution; controlled legacy replay reproduces the damaging coordinate-copy operation for captured transitions. Other MR/raw/source problems remain open. '
             'A separate graph-selected fragment candidate transports the entire raw base through a preserved sugar frame. Returned Cedar 17 passes native mechanics while retaining unresolved and worsened pairing contacts. '
             'A separate source/effective recovery requires exact original hashes and supported source graphs, then whole-component generation and linked/native gates at fixed coordinates before a fragment trial. Returned Cedar 18 verifies source-preserving generation and both native phases; full scientific qualification stays open. A separate fixed-definition geometry trial records native stopping, gradients and full-precision versus PDB round-trip evidence; returned Cedar 19 optimization reaches its explicit iteration cap. Identity mapping preserves original PDB records across native reordering, and Cedar 20 reuses saved endpoints. Its native reread preserves identities/definitions and activates extra distance-filtered hydrogen bonds. A read-only reload audit retains the changed proxy set and original REVIEW separately from saved fixed-manager endpoint equivalence. A separate explicit NARestraints pair/stack compiler preserves existing edits and tests native membership at two saved coordinate sets; both returned native cases pass exact membership checks while geometry qualification stays open. Production PostMR is unchanged. '
             'Returned Cedar 22 verifies a separate bounded geometry trial under this policy: exact initial manager matching and all 17 native PDB readback checks pass. The objective decreases, while a line-search error and remaining pairing/local-angle strain retain scientific review. '
             'Cedar 23 prepares a separate saved-gradient audit with exact manager/source matching, finite differences, category controls and dictionary review. It performs no optimization or target edit; native evidence is pending. '
             'JSON receipts preserve findings; no coordinate repair or stitching '
             'is performed by this audit layer.</desc>',
             '<rect width="1200" height="1190" fill="white"/>',
             text(50, 47, "CIF Doctor: evidence around model preparation", size=33, weight="bold"),
             text(50, 84, "Implemented assessment layer · exact inputs · preserved provenance", size=24),
             text(50, 134, "NASolve preparation", size=27, weight="bold", color=PIPE),
             text(690, 134, "Read-only CIF Doctor audits", size=27, weight="bold", color=AUDIT)]

    left, right, left_width, right_width = 50, 690, 540, 460
    rows = [
        ("source-inputs", 165, "Source dictionaries + MR model", ["Declared modified-residue targets"]),
        ("coot-mutation", 300, "Coot mutation (when requested)", ["Existing construction and identity checks"]),
        ("prepared-inputs", 435, "Prepared model + runtime inputs", ["Source preserved; supported normalization"]),
        ("readyset", 570, "ReadySet (Phenix)", ["Model / ligand preparation; hydrogens=False"]),
        ("effective-inputs", 705, "Final model + selected bundle", ["Existing dictionary precedence / filtering"]),
        ("postmr-gates", 840, "Existing PostMR gates → refinement", ["Audit findings remain report-only"]),
    ]
    for identifier, y, title, lines in rows:
        parts.append(box(identifier, left, y, left_width, 100, title, lines))
    for index, (_, y, _, _) in enumerate(rows[:-1]):
        parts.append(path(f"preparation-flow-{index}", f"M 320 {y + 100} V {rows[index + 1][1] - 8}"))

    audits = [
        ("mutation-audit", 165, "A  Construction-source audit", ["Before requested mutations"]),
        ("source-runtime-audit", 435, "B  Source + runtime audit", ["Distinct inventories before ReadySet"]),
        ("effective-audit", 705, "C  Effective-bundle audit", ["Selected inputs + final PDB inventory"]),
    ]
    for identifier, y, title, lines in audits:
        parts.append(box(identifier, right, y, right_width, 100, title, lines, audit=True))
        parts.append(path(f"audit-branch-{identifier}", f"M 590 {y + 50} H 682", audit=True))

    parts.append(box("json-receipts", right, 840, right_width, 120,
                     "Hash-bound JSON receipts", ["Findings and measurements", "Input hashes and software versions"], audit=True))
    parts.append(path("mutation-to-receipts", "M 1150 215 H 1176 V 890 H 1158", audit=True))
    parts.append(path("source-to-receipts", "M 1150 485 H 1176", audit=True, arrow=False))
    parts.append(path("effective-to-receipts", "M 1150 755 H 1176", audit=True, arrow=False))

    parts.extend([
        '<g id="scope-notes">',
        '<rect x="50" y="980" width="1100" height="173" rx="10" '
        'fill="#fafafa" stroke="#b7c2ca" stroke-width="1.5"/>',
        text(70, 1014, "Checks: graph, numerical consistency and bonded-atom coordinate degeneracy", size=24, weight="bold"),
        text(70, 1048, "PASS / REVIEW / INVALID / UNASSESSED describe the checked evidence.", size=24),
        text(70, 1082, "Trial mechanics pass; gradient audit prepared; geometry open.", size=24),
        text(70, 1116, "Native site / terminal controls recorded; formal-charge readback unavailable.", size=24),
        '</g>',
        '</svg>'])
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    DESTINATION.write_text(build(), encoding="utf-8")
    print(DESTINATION)
