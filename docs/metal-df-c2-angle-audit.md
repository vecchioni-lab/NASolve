# DF C2 sulfur-angle provenance and chemical review

22 November 2026. A01 remains partial; A02 remains gated. Read-only audit:
no restraint change, coordinate replacement, optimization, maps or f″ run.

## The distinction that changes the next experiment

The investigator identifies DF/A1AAZ as their own originally Phenix-generated,
unrepaired component. It is not independent experimental calibration. The
currently bound QF1 numerical dictionary was subsequently regenerated through
Cedar C410; agreement with it establishes source consistency, not chemical truth.
The descriptions of a “healthy” source fragment in earlier diagnostics mean
source-consistent internal geometry and do not independently validate its angles.

| Angle at C2 | Current target (σ), degrees | Final model, degrees |
| --- | ---: | ---: |
| S1–C2–N1 | 126.83 (1.918) | 135.324 |
| S1–C2–N3 | 115.92 (2.647) | 108.705 |
| N1–C2–N3 | 117.24 (2.665) | 115.969 |

All three terms are present in the captured native geometry. Their final angles
sum to 359.9977°: the conspicuous asymmetry is principally in-plane distortion.
S1 is the working dictionary's sulfur label; it is the sulfur attached to C2.

## Independent chemical comparator

Fabijanić et al., *Acta Cryst. C* 73 (2017), 1078–1086, Table 2, reports
independent small-molecule 2-thiouracil structures: N1–C2–S1 121.93–123.09°,
N3–C2–S1 121.78–122.06°, and N1–C2–N3 114.86–116.29° across the listed
polymorph/temperature measurements. These support approximately trigonal-planar
chemistry with unequal angles; they do not support imposing three exact 120°
angles. The paper attributes modest differences to hydrogen-bonding environments.
[Primary paper and Table 2](https://fulir.irb.hr/4302/7/Acta.Cryst.C-2017-Fabijanic_et_al.pdf),
DOI 10.1107/S205322961701542X.

These are neutral free bases, not Hg-bound DF nucleotides. The comparison flags
both the final 135°/109° split and the generated 127°/116° targets for chemical
review; it does not establish the correct metal-bound targets or restraint widths.
The closer independent free **2-thiothymine** comparator was subsequently
recovered through the authors’ publicly indexed full text, following Cedar’s
pointer: Matković-Čalogović, Bešić and Sanković (2002), Table 1 and supporting
information sup-3, DOI 10.1107/S010827010201315X. It gives **N1–C2–S
122.57(9)°, N3–C2–S 122.80(9)°, N1–C2–N3 114.63(10)°**, and C2=S
**1.6735(13) Å**. The reported refinement uses 1,801 independent reflections
and zero restraints. This is independent small-molecule evidence for a near
symmetric sulfur direction in the neutral free base; its uncertainties are
measurement uncertainties, not proposed refinement restraint widths. It still
does not assign targets for N3–Hg DF.
[Author-provided paper and supporting information](https://www.researchgate.net/publication/11184095_5-Methyl-2-thiouracil).
Direct publisher retrieval failed; the numerical table and refinement details
were verified in the indexed author full text. No local CIF was obtained.

## Actual numerical generator

Declared artifact anchor `NASolve-local-artifacts` resolves to the local
`NASolve/branch-artifacts` directory. Read the exact declared path
`cedar/c410-matched-neutral/QF1/generation/attempts/attempt-0001/generation/`.
Its `candidate_spec.json`, `candidate_worker.py`,
`source_candidate_receipt.json` and `execution/candidate/finished.json` show a
completed Phenix **2.2.1-6174** execution on 19 November, not a dry-run:
`phenix.python` calls installed `elbow.command_line.builder.run` with the
prepared native molecule and `cctbx=True`. Arguments include `--opt`,
`--opt_steps=180`, `--template=source_ideal.pdb`,
`--initial_geometry=source_ideal.pdb`, `--add_hydrogens=False`, `--pH=low`
and `--chiral=retain`. These are historical generation parameters, not an
experimental pH determination. The native backend uses installed optimization
defaults; no independently validated quantum-chemical target is claimed.

Candidate SHA256:
`aa4c5da5b47d5df04a90a920ac09fbc3a4c984f00c2dcdcd031ca50786726705`.
Final linked/plane-patched QF1 SHA256:
`cbaa29991e650423148da121cc28a77c825ee3d92cf50c3cfa172a48c9c512c0`.
Direct CIF readback confirms all three C2 targets and widths are identical.
The original deposition's exact generator command is not established here.

Cedar coordination confirms C423 demonstrated numerical target delivery for
C2–S1 and C435 isolated native usability of thiocarbonyl representation; neither
is independent sulfur-angle calibration. C409/C410 donor-state comparisons
changed numerical targets and widths. Preserve those distinctions.

## Existing fragment availability and next boundary

Private evidence at `Alder/a01-existing-fragment-20261122-01/comparison.json`
passes 124 read-only checks. The nine-heavy-atom base graph has 21 internal
bond/angle terms consistent with the generated dictionary; the retained precursor
already contains that shape. Proper-rotation maximum alignment error is
0.000921 Å, below the 0.001905 Å coordinate-rounding bound.
Of the eleven previously selected internally frozen terms, six belong entirely
to the base and five to sugar. A base-only replacement would change the former,
not the latter. This subset is not every base term. No replacement was applied.

Next: validate coupled C2 bond/angle targets and the declared donor/protonation
state against independent chemical evidence before admitting a source-fragment
transport/recovery experiment. Then test whether coupled placement and restrained
open XYZ/B recovery retain defensible base geometry, attachment, polymer links,
metal contacts and map fit. Initial worse work score alone is not rejection.
Do not add a hardcoded DF-specific 120° repair or launch another unchanged grid.

Validation: retained comparison receipt reports 124 checks; a separate Gemmi
readback compared candidate and effective CIF C2 terms and SHA256 values.
Documentation only: no new tests, full suite, native execution or schema changes.
Scientific files remain local and excluded from Git. No migration is required.
