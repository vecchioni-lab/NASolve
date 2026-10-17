# Full-auto patch publication and live-validation checkpoint

Updated 2026-10-07. **Live campaign runtime: `984f75db45607e119ad7fc224ae04cc5d0ffded7`.
The four-member native full-auto campaign returned four SOLVED results.**
The subsequent reporting correction is published as
`debd4af553c25d83526fc58185f56a23cbb92f23`: Simon returned **109 focused tests
in 21.05 s and 878 full tests + 224 subtests in 77.23 s**, all passing.
The remote Pine ref was independently verified at that commit. These are
user-local pytest results, not CI or a new native campaign execution.
Recovery and publication are complete. Do not reapply the patch, repeat its
recovery, or rerun successful structures merely to refresh documentation.
The [development handoff](development-handoff.md) owns project ordering;
[full auto](campaign-full-auto.md) and the component contract own policy.
This linked checkpoint supersedes older full-auto/DiU/5CM "native pending"
wording for the precise execution behaviors evidenced below, not all merge gates.

## Returned live evidence

Source: Simon's uploaded `receipt.json`, SHA-256
`653c64a0f1cbe1f55060ec3a256727611b95e75534b5cfb073c75737254da966`.
User-local campaign: `~/NASolve-live-tests/full-auto-984f75d-kaxrtv9w`;
receipt: `ferry_logs/receipt.json` within that root. The raw receipt and scientific
files are not copied into Git by this documentation update.

The receipt records code head `984f75d` before and after execution, runtime-check
and planning exits 0, and campaign run/status exits 3. `campaign run NEW_ROOT`
had no explicit --through override: the frozen `5w6w-full-auto` 1.0.0 recipe
controlled escalation. Recipe blob: `644331ecb35453c3a892502c0f3f1e22263f067f`.
Reported versions: Python 3.12.14, Phenix 2.2.1 and Coot 1.3.3.

All runs below are `DATASET/AutoMR/run_001` in the NEW campaign, not the old
TestSets campaign. SOLVED means numerical workflow success, not user approval.

| Dataset | Outcome and current checkpoint | Returned Rwork / Rfree |
| --- | --- | --- |
| DiU | SOLVED; refine-001 | 0.2072 / 0.2202 |
| EA | SOLVED; refine-001; original MR_REVIEW retained at TFZ 7.60 | 0.1603 / 0.1776 |
| Q5cm | SOLVED; refine-001 | 0.2094 / 0.2304 |
| QiC | SOLVED; Doctor recommendation refine-002 provisionally selected | 0.1500 / 0.1502 (subsequent saved-report extraction) |

EA's warning survives in campaign automation and downstream receipts. Its
Phaser result remains MR_REVIEW; the subsequent refinement passed without
Doctor. This directly exercises the recipe-authorized borderline-MR trial.

DiU passed PostMR and refinement after the prime-preserving coordinate lookup
fix. I5 of 5IU at B:4 is present, element I, and registered as an anomalous
candidate. AutoSol returned AUTOSOL_READY. AutoRefine reports anomalous use of
F(+), SIGF(+), F(-), SIGF(-), with I5 scattering actually in the diagnostic:
parameter_mode=refine, final f''=4.71288, calculated f''=3.367204189300537,
occupancy=1.0, B=241.63 and wavelength=1.00744. These are reported values for
inspection, not a new approval or a reason to invent a chemistry correction.
The subsequent read-only extraction confirms phase_option=True with
inputs.phase_file=overall_best_refine_data.mtz and
inputs.phase_labels=[HLAM, HLBM, HLCM, HLDM]. DiU supplied experimental phases;
this conclusion no longer depends on the defective audit Boolean alone.

Q5cm passed ordinary preparation and refinement with the supplied resource;
the former missing-local-dictionary blocker no longer prevents this workflow.
This receipt is not an extracted final atom inventory or a visual geometry check.

QiC first returned AUTOREFINE_REVIEW at refine-001 (0.1646 / 0.1561). Doctor
returned REFINE_DOCTOR_RECOMMEND for refine-002. Core Doctor preserved current;
the campaign then explicitly changed current from postmr to refine-002 under
the frozen recipe. The selection records its source, reason and
user_approved=false. Thus current_checkpoint_preserved=false for the complete
campaign stage and doctor_current_checkpoint_preserved=true are consistent,
not an integrity failure. The selected-branch audit reports anomalous refinement
on Bijvoet amplitudes with experimental phases disabled. The later read-only
extraction from this exact selected checkpoint reports Rwork/Rfree
0.1500/0.1502, recipe RefineDoctor/ML-fixed-scattering, anomalous=True,
scattering=fixed, phase_option=False, phase_file=None and phase_labels=[].
These selected-trial numbers were returned separately, not exported in the
original receipt or borrowed from the older guarded campaign.

The receipt reports final_integrity=OK, changed_baseline_files=[], the new plan
unchanged, identical initial/final code heads, and no tracked changes afterward.
The preceding ferry footer also reports old state/reports/registries and copied
inputs unchanged. Every member retains inspection_required=true and
user_approved=false. EA's retained warning explains a flagged exit despite all
four members being SOLVED; do not hide it by weakening status reporting.

## Bounded follow-up: reporting precision, not another campaign rerun

This reporting follow-up is now implemented, regression-tested and published
at `debd4af`; the following describes the preserved historical discrepancy.
EA and Q5cm have AutoSol SKIPPED/NOT_RUN yet their original iodine audits say
experimental_phases_used=true. Source inspection at tested commit 984f75d
explained the diagnostic weakness: `iodine_refinement_audit` in
`src/nasolve/anomalous_expectations.py` copied
refinement.use_experimental_phases, which `autorefine.py` records as the request
argument. It did not inspect inputs.phase_file or inputs.phase_labels.
Permission to use phases is not evidence that phases were supplied or consumed.

Simon returned that saved-report extraction (2026-10-07):

| Exact checkpoint | Phase option | Phase file / labels | Anomalous / scattering |
| --- | --- | --- | --- |
| DiU refine-001 | true | overall_best_refine_data.mtz; HLAM, HLBM, HLCM, HLDM | true / refine |
| EA refine-001 | true | None; [] | false / refine (inactive setting) |
| Q5cm refine-001 | true | None; [] | false / refine (inactive setting) |
| QiC refine-002 | false | None; [] | true / fixed |

The small reporting correction now distinguishes requested permission, supplied
phase inputs, and phase usage derived from both. Positive usage requires the
option plus a nonblank phase-file locator and a complete recorded four-label
set in THIS refinement report. AutoSol availability, a parent's report or the
word "refine" in an inactive scattering option cannot substitute for those
inputs. This is not a new file-integrity or chemistry gate: do not reopen phase
files merely to interpret historical reports after relocation.

The audit retains its existing schema-1 fields and adds requested/input/basis
evidence; it does not change AutoRefine parameters, scientific acceptance,
checkpoint selection, or any stored campaign receipt. Older records can still
contain the inaccurate Boolean. Preserve them; interpret their actual inputs
or produce separate derived evidence rather than rewriting checksums/history.

Initial isolated validation comprised 27 new report-only cases (25 failed /
2 passed before; all 27 passed after) plus 43 existing pure policy/diagnostic
cases: 70 passed. This was source-level evidence, not a full checkout.

Simon's subsequent local patch ferry, based on `cf2df92`, passed:

| Reporting-patch regression | Result |
| --- | --- |
| Focused: phase audit, full-auto policy, campaign stages, full-auto pipeline | 109 passed in 21.05 s |
| Full NASolve suite | 878 passed, 224 subtests passed in 77.23 s |

The command applied `NASolve_phase_usage_audit.patch`, ran those suites with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, passed unstaged/staged diff checks,
then committed and pushed exactly four source/test/documentation files as
`debd4af553c25d83526fc58185f56a23cbb92f23`. Returned status showed no tracked
changes and only the existing untracked files. The remote ref was verified.
No new native execution or historical-receipt rewrite accompanied this fix.
No reapplication, repeat pytest or repeat campaign is needed for this slice.

The exported statistics have null bond_rmsd/angle_rmsd; do not interpret null as
zero. Terminal D:1 geometry audits pass in the initial AutoRefine records, with
maximum sigma deviations 1.66 (DiU), 1.72 (EA), 1.83 (Q5cm) and 1.74 (QiC).
Those checks are terminal-phosphate-specific, not whole-model geometry approval.
No new model/map inspection or user-veto/resume exercise is reported here.
Rejected-AutoSol continuation was not exercised: the returned gates either
succeeded or skipped. Prepared-nonstandard validation and P2 component
normalization remain separate, as does final-candidate review/merge.

## Published patch and regression provenance

The published full-auto payload includes recipe-schema-2 full auto, the DiU
parser fix, parameterized 5CM, iodine diagnostics, the Doctor fixture repair,
and continuity/metal-builder documentation. A 5CM-only .gitattributes exception
preserves the checksum-pinned supplier bytes; it is not a numerical CIF edit.

| Original full-auto user-local regression before publication | Result |
| --- | --- |
| Previously failing Doctor fixture | 1 passed in 2.87 s |
| Focused selection | 351 passed, 59 subtests passed in 49.26 s |
| Full suite | 851 passed, 224 subtests passed in 80.67 s |

That recovered tree was based on d3e1fa3 and published as 984f75d. These are
historical returned local pytest results, not GitHub CI; the newer reporting
patch's 878 + 224 full-suite result is recorded above. This documentation-only
synchronization executes no tests or native scientific programs.

Retain the original, fixture-recovery and publication receipts beneath
`~/NASolve-live-tests/full-auto-component-patch-jf62b0z4/`. The original failure
was an incomplete Doctor trial mock lacking checkpoint_id/report_path; the
fixture was repaired, not the production audit disabled. The later publication
stop concerned upstream trailing whitespace only. Neither recovery is pending.

The installed workbook audit found exactly one 5CM record: cytosine sheet,
Base Analog C, DNA; its parent is DC. The repaired 5IU dictionary lookup
returned ring C5-I5=2.0951107369301507 A, separately from
sugar C5'-I5=8.843030419488558 A. No workbook or supplier 5IU coordinate edit
was required. Do not mistake those ideal-coordinate distances for measurements
from the final native refined model.

## Preserved context and next priorities

The old guarded campaign remains at
`~/NASolve-live-tests/TestSets-dd59b4f-jjra04s9`. Its GZ11 run_002/refine-001
passed ordinary execution and Simon's visual Coot check; no repeated lap is
needed. Guarded QiC run_002 recommended refine-002 while current stayed postmr;
that is distinct from the NEW campaign's provisional automatic selection.

The P2 candidate now implements standing 1W5->DZ and 1WA->DP preparation,
including the DP resource and mapped-derivative provenance. Returned full-checkout
and native conversion validation remain pending; this is not another full-auto
rerun. The component contract owns the exact P2 behavior.
Complete the remaining prepared-nonstandard and campaign inspection/resume
checks and final-candidate review under the finite Pine gates, merge to main,
then Simon's new blind AlphaFold/PDB + sequence geometry campaign, followed
by operational Scout. No main merge is authorized by this note.

The [metal-restraint builder](metal-restraint-builder.md) and its
[machine intent](metal-restraint-builder-intent.json) are published future
design, not implemented and not a Pine merge gate. Keep canonical workbook
roles distinct from actual names, graphical restraint previews distinct from
coordinate edits, and reusable templates distinct from bound refinement inputs.
Simon will supply coordination examples and numerical targets.
