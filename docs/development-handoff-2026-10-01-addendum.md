# Temporary development handoff — 2026-10-01

Status: **documentation-only checkpoint; review and production patches deferred**.

Read this addendum before the GZ11 sections of [development-handoff.md](development-handoff.md).
It supersedes the 2026-09-29 immediate GZ11 validation/blocker statements, not the
broader campaign, registration or GUI contracts. The companion
[modified-component-preparation-intent.json](modified-component-preparation-intent.json)
is development intent, not a runtime registry. Older machine-intent snapshots
remain historical evidence for the validation state they describe.

## Latest explicit user request: curated component normalization

Simon clarified: **we WANT 1W5 to go to DZ ALWAYS**.

- Record the intended direction as **1W5 -> DZ**, never the reverse. This is a
  requested standing component-normalization policy, not a pH-conditioned
  fallback, an optional preference for this one GZ11 run, or a request to
  preserve 1W5 as the preferred final component.
- Simon identified the corresponding problematic P component as **1WA**:
  the requested normalization is **1WA -> DP**. The source identifier and
  direction are now supplied by the user; chemistry and implementation review
  remain pending.
- These are specific additions to the curated problematic-component policy,
  separate from general construction-scaffold inference and torsion conversion.
  Tautomer/identity details, atom correspondence, dictionary provenance and the
  exact application boundary need review before implementation. The requested
  direction is settled; the safe implementation is not yet settled.
- Preserve original input identities and all frozen/historical models. A future
  normalization must produce an audited prepared derivative, not relabel raw
  files or assume a residue-name swap alone supplies the intended chemistry.
  Do not infer a universal chemical equivalence or deposition rule from this
  requested NASolve normalization policy.

The inspected current `CURATED_LIGANDS` registry contains **DE, DF, 1AP, S6G,
C38 and 5IU**. These entries cover several kinds of exception, not one universal
tautomer rule. Existing documentation distinguishes the historical **8RO/DE**
identity problem; do not turn the user's uncertain recollection of `1W0` into a
new mapping. The 1AP dictionary/OP3/compatibility fixes also remain distinct.
Review the existing registry and alias layer before adding the new policy.

## Evidence returned during this session

All live results below were reported by Simon from his local environment, not
executed by GitHub CI or by the documentation editor.

1. At local code head `0803989b1c51c6aae7d50a3fcb11835e5280e533`, the force-focused
   tests passed **6**; the input/PostMR/campaign slice passed **115 tests + 50
   subtests**; the full suite passed **694 tests + 224 subtests** in 53.60 s.
   Syntax, patch hygiene and machine-intent JSON parsing passed.
2. The real installed NARestraints force probe generated restraints and audited
   actual G/Z classes -> forced G/C recipe classes. That first probe used the
   historical manual `GZ11/Refine_74` model (DG/1W5) and a historical DOHU
   `Std_padd.txt`, not a verified current packaged pair-file source. It validates
   that particular generation seam, not complete production GZ11 preparation.
3. Fresh `examples/TestSets/GZ11/AutoMR/run_002` reached **MR_SUCCESS, TFZ 12.20**.
   Its frozen target remained DG/DZ and its separate override G/C. Production
   PostMR stopped before mutation: `DNA + Base Analog Z` had no construction
   parent. No new-run coordinate inventory showed 1W5. Simon identified Refine_74
   as his manual pre-NASolve work, not evidence of a NASolve-created 1W5 model.
4. A single-use experimental probe registered **DC as DZ's construction scaffold**
   and supplied a checksum-pinned parameterized MonomerLibrary DZ dictionary
   with DNA group adaptation. It used a copied MR snapshot. Ordinary
   PostMR/Coot/ReadySet reached **POSTMR_READY**: B:4 DG -> DC parent snapshot ->
   DZ, with A:12 DG and the separate G/Z -> G/C force audit. Production code,
   registry and original GZ11 run were unchanged. This is experimental live
   preparation evidence, not production integration or structural approval.
5. `Probe/DZ-via-DC` refinement of that experimental copy failed at
   `refine-001` / `AutoRefine/round_001`, before R statistics, with **Conflicting
   dihedral restraints**. The audit identifies DZ B:4 `C3e-nyu0` over
   C4'-O4'-C1'-C2'. Both C2e and C3e alternative rows are present. The actual
   refinement command consumed **PostMR/ReadySet/prepared_model.ligands.cif**,
   whose DZ definition still contains those rows. Current checkpoint stayed
   unchanged. This is not numerical refinement success.

The retained experimental pen was `nasolve-dz-dc-probe-kad1eax8` in the user's
macOS temporary directory, with `MR_snapshot/` and `probe_receipt.json`. Its
continued availability is not guaranteed; keep the original failed run and
all experimental artifacts intact. The nine-dataset TestSets campaign has not
been validated or launched by this documentation checkpoint.

## What to review and generalize next

Keep four independent responsibilities explicit:

- **Component normalization:** requested 1W5 -> DZ always, and user-identified
  1WA -> DP. Both await implementation review. Do not implement broad tautomer guessing.
- **Construction scaffold:** preserve working explicit recipes, then consider a
  validated purine/pyrimidine role-map fallback. Simon's N9 means the workbook's
  canonical atom-role COLUMN, not a literal PDB atom name. DA/A versus DC/C is a
  proposed placement scaffold, not a change to final identity or pairing class.
  Missing N9 data alone must not be confused with positive pyrimidine evidence.
  Retain sugar/chirality, mapped-anchor and backbone-preservation checks.
- **Dictionary compatibility:** September 24 commit
  `d203d2e32effd8c5f7b4b319ee2774b05972aa82` added alternative-torsion normalization
  but dispatched it only for 1AP. Generalize supported representation handling
  by content, with tests for ordered/reversed atom quartets, periods, existing
  alternatives and unequal uncertainties. Do not assume preserving angle values
  alone preserves every restraint parameter or collapse arbitrary conflicts.
- **Effective dictionary authority:** normalization must survive ReadySet and
  checkpoint creation. Audit the exact dictionaries consumed downstream; merely
  fixing an unused DZ.cif cannot repair the combined ReadySet definition.

Historical context: [1AP integration](history/1ap-phosphate-integration.md),
[September 11 handoff](history/development-handoff-2026-09-11.md), the September 24
normalization commit, `src/nasolve/curated_ligands.py`, `ligand_profiles.py` and
`postmr.py`. The earlier 1AP work addressed dictionary quality, verified internal
OP3 removal and authoritative dictionary propagation; it does not justify
indiscriminate OP3 deletion or weakening component-specific topology checks.

Next session: review the requested 1W5 -> DZ and 1WA -> DP normalization policies;
agree the normalization and general scaffold/dictionary contracts; patch NASolve
with regressions; then repeat the bounded live test in a fresh experimental branch.
No installed NARestraints workbook edits, silent dictionary downloads, changed
observations/Free-R flags, overwritten failed attempts, or production chemistry
changes are authorized by this note.
