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
             'Returned Cedar 23 matches the fixed manager and sources, and localizes stable sampled gradient disagreement to native parallelity at both precisions. Independent plane calculations and public accumulation-loop bounds reproduce the saved evidence; Cedar 24 supplies installed per-proxy confirmation. Returned Cedar 24 confirms an installed plane-gradient accumulation defect: sampled individual-restraint derivatives agree while second-plane contributions are omitted in all captured and tilted-control orders. The installed loop-bound model reproduces the accumulation arrays exactly. Saved-data recombination explains all prior sampled mismatches. Cedar 25 implements an explicit NASolve-local correction using complete original single-restraint gradients and unchanged native energies. Its return passes both endpoints but retains six initial-coordinate directions. An independent model of normal-orientation sign handling reproduces the remaining gradient. Returned Cedar 26 uses each plane as the first plane in both orders and passes all sampled global, per-plane and rotated-control derivatives with unchanged native energies. Cedar 27 supplies a bounded trial from the original initial coordinates, gated by exact qualified source/gradient matching and followed by endpoint derivatives and native PDB mechanics. Returned Cedar 27 passes all 17 mechanics checks and 336 sampled endpoint directions while retaining the 1,000-iteration limit. Its target falls 28.72% and still descends; Cedar 28 supplies a bounded saved-full-precision coordinate continuation with fresh optimizer history, exact start-gradient/target matching and repeated endpoint/native mechanics gates. Returned Cedar 28 passes all 17 mechanics and 336 sampled endpoint directions, with another 3.64% target decrease. The cumulative 2,000 iterations retain the limit and the same three distance/ten angle reviews. Cedar 29 supplies a separate graph-selected base-orientation audit: temporary rigid-base rotations under the same fixed policy, with full/rounded category slopes, fresh rotational derivatives, source-angle context and repeat/additivity/periodic controls. Returned Cedar 29 passes all 96 sampled rotation directions; zero degrees is the lowest independent coarse sample at each site, without a minimum claim. Cedar 30 supplies separate graph-only source numerical recovery with exact chemical comparisons and explicit source-coordinate seed provenance. Returned Cedar 30 stops before generation on external coordinate-tag case. Cedar 31 preserves canonical CCD Cartn spelling and adds an explicit public PDU graph/NARestraints compiler control. PDU retains the propynyl triple bond; existing AT and both stacking-order compiler checks pass. Returned Cedar 31 separates a DP missing-alias reader failure from a PDU optimizer/restart crash after nonconvergence; neither produces a dictionary. Cedar 32 supplies missing alias metadata and anchored installed-source/read-only input checks before another generation. Returned Cedar 32 passes PDU read-only input and exposes DP reader-dialect review. Cedar 33 projects declared chemistry into a separate reader input and supplies an opt-in explicit bounded step trial after installed options-parser/source proof. Unknown atom metadata and nonconvergence remain explicit. Returned Cedar 33 passes both readers, stops DP in preparatory chirality handling and writes a nonconverged PDU candidate. Cedar 34 separately compares source/generated signed hands and omitted R/S metadata, summarizes the printed energy trace and probes installed reader markers plus its isolated chiral constructor without another generation. Absolute CIP assignment remains open. Returned Cedar 34 reproduces the DP assertion and passes PDU known markers. Native constructor internals include local chiral-template minimization, so the legacy NOT_RUN flag does not instrument those operations. Cedar 35 preserves source comp_list reader routing and equal coordinate aliases, then records selected native parser dispatch and raw atom/bond/charge/coordinate readback without requesting a constructor or generation. Returned Cedar 35 stops at the internal temporary graph path before native parsing. Cedar 36 resolves only the owned temporary directory and preserves the failed capsule for the same parser retry. Returned Cedar 36 passes PDU raw inventory and exposes DP monomer bond-token case fallback plus omitted formal charges, while signed markers survive. Cedar 37 translates declared order vocabulary and separately controls explicit source-charge population on a temporary parsed component under exact graph/coordinate and pinned API proofs, retaining raw findings and recorded before/after graph and stereo fields. Returned Cedar 37 preserves declared orders and passes isolated source-charge controls. Cedar 38 screens graph-selected triple lengths, linear angles, active proxy membership and linear-axis torsions in fixed isolated PDU and 5PC controls, comparing installed lookup, captured installed CIF and the saved PDU candidate. The two 5PC role records remain ambiguous. Returned Cedar 38 finds no component in both default monomer lookups and confirms active triple/linear terms plus six torsion reviews for the supplied PDU dictionary at fixed source seeds. Cedar 39 separates installed CCD chemistry from numerical libraries, records direct/canonical lookup context, compares declarations/descriptor text and captures route-helper/dispatcher source without running ReadySet, a constructor, generation or optimization. Returned Cedar 39 confirms installed CCD declarations and raw readers while all four numerical monomer lookups remain missing. Cedar 40 captures the literal ReadySet entrypoint and bounded import text without execution, and records only the native CCD filename/SMILES accessor selection. Descriptor membership is not mapped-graph or numerical restraint qualification. Returned Cedar 40 verifies both CACTVS selections and 24 static sources. Returned Cedar 41 records failed preparatory file-input builder calls: leaked wrapper PHIL options stop nested eLBOW parsing. Its surviving CIFs are unchanged source copies and native triple checks do not run. Cedar 42 keeps explicit ReadySet API arguments out of process options, matching the captured native entrypoint, preserves original builder kwargs, and reports worker/native/output outcomes separately. Failed source-copy and fixed-model evidence replays before another bounded isolated attempt. Returned C42 completes both controls and passes generated/native triple targets, retaining six dictionary and three active heavy-atom linear-axis torsions each, phosphate charge/hydrogen changes and 5PC plane review. C43 rebuilds the exact isolated managers and evaluates fixed native torsion kernels/gradients at saved source and generated full/rounded coordinates with central differences, repeats, reversal and nonchemical collinearity controls. Returned C43 passes sampled derivatives but retains near-collinear conditioning review. C44 prepares separate candidates omitting only torsions containing explicit triple-bond graph angles declared as 180 degrees, preserving all other parsed values. Fresh native original/candidate comparisons must show only six definition-row and three heavy-proxy omissions each, with triple targets and every unrelated term intact. Returned C44 passes both exact native comparisons and triple screens, with dihedral counts 28 to 25 and all unrelated fields intact. C45 rebuilds both managers and compares original/candidate energies and gradients at identical saved source/full/rounded coordinates. Deltas must equal saved omitted-torsion contributions; other families, additivity, repeats, static signatures and source hashes remain fixed. Candidate full/dihedral derivatives are sampled with six steps and graph-selected directions under a 2000-evaluation/180-second bound. Norm decreases are descriptive, not required. Returned C45 passes arithmetic and omitted-term deltas, retaining two 5PC count-only reviews with unchanged repeated energies/gradients. C46 captures actual native pair identities, parameters, single/container contributions and cache state. Changed pairs must contribute exactly zero before a separate settled-cache retry of unchanged strict criteria; pair identities and function parameters remain monitored. Old failures stay visible; native cache proof remains pending. No model, chemical state or production adoption occurs. Native internal geometry operations remain uninstrumented; no scaffold or production integration occurs. Equivalent operational role aliases now compile once, with descriptive columns excluded and a registered canonical synthetic partner preferred; conflicting mappings remain blocked. 5PC already has C-sheet roles, so no NAR workbook or release changes. '
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
        text(70, 1082, "Triple targets pass; torsions and chemical state remain under review.", size=24),
        text(70, 1116, "Derivatives agree; native neighbour-cache proof remains open.", size=24),
        '</g>',
        '</svg>'])
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    DESTINATION.write_text(build(), encoding="utf-8")
    print(DESTINATION)
