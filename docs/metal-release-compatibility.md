# Alder receiving compatibility — 28 November 2026

This is release integration evidence, not a new crystallographic result. A01
remains partial and A02 quantitative trials remain gated. The metal roadmap is
still the single forward queue.

## Scope and behavior

The receiving history starts at published Alder `1efcd034`, preserves all 13
first-parent receiving commits through `b1bb176f`, and integrates Cedar
`02c61e9b`. The release candidate and actual released main are received in a
subsequent merge; qualification is in progress, not a delivered-merge claim.

Before reconciliation, Cedar's fitted-sugar and source-order APIs conflicted with
Alder's explicit original registered request. The combined paths retain both
contracts. Source-order recovery cannot release a held registered request, and
an original-only preparation cannot acquire an unrequested sugar fit. Both
frozen native helpers and frozen explicit-NA readers remain selected by their
historical policy. No metal geometry, refinement strategy, B/Q/f′/f″ policy,
phase identity or schema meaning changes.

Changed integration boundaries: `cif_complete_request`, `cif_ordinary_postmr`,
`cif_postmr_request`, `cif_postmr_publication`, and `refinement_parallelity`;
ordinary-entry, registered publication/request and ordinary import regressions;
`ligand_profiles` skips the registered import when no topology is declared;
parametrized relocation tests allocate independent destination directories; root architecture,
changelog, handoff and metal roadmap. Cedar's other changes remain its own
received history. No raw diffraction, coordinates or generated native output is
included in Git.

## Validation retained so far

| Check | Result | Environment |
| --- | --- | --- |
| Three new receiving regressions on `b1bb176f` | All fail before the API reconciliation | Phenix 2.2.1-6174 Python; NARestraints 1.1.3 |
| Registered/complete/fitted/PostMR/Coot owner panel | 480 passed, 15 subtests; 379.76 s pytest time | Same native libraries and dependency |
| Protected refinement/phase/native panel | 334 passed, 59 subtests; 57.91 s | Phenix 2.2.1-6174 Python; NARestraints 1.1.4 |
| Metal feature panel | 1,273 passed; 14 environment/fixture failures, all covered by the 17-pass focused host rerun | Phenix 2.2.1-6174 Python then complete Python 3.12.14 release environment; NARestraints 1.1.4 |
| Installed release and relocated input reader | Pending reconciliation | Separate disposable installation |

Each test command uses `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`, one numerical
thread, `pytest -q -p no:cacheprovider`, an exclusive `--basetemp`, and a retained
JUnit report. The native Python bootstrap imports Gemmi before adding the
explicit dependency site, then inserts the tested source directory. The exact
argument vectors, environments and file hashes are in the local evidence receipts
below; the ordinary full suite belongs to the release owner and is not repeated.
No Phenix refinement or Coot construction was executed in this pass.

## Two distinct frozen-reader boundaries

The retained FT parent is a REVIEW checkpoint with unchanged 858-atom DNA and no
Hg placed. This pass found two separate compatibility questions while reopening
it; neither permits rewriting the source evidence.

1. **Existing dependency-specific replay:** the original C80 compiler reads with
   NARestraints 1.1.3 on the old, reconciled and Cedar-only sources. Version 1.1.4
   is refused on all three. The current compiler records 16 differences: two
   module fingerprints, workbook fingerprint, a removed whitespace-correction
   record and 12 normalized `C5` source labels. Generated PHIL/control bytes are
   identical. Explicitly supplying the recorded workbook leaves two module
   fingerprint differences. This is an expected exact-dependency boundary;
   matching output alone does not justify substituting provenance.
2. **Received assessor provenance:** under original NARestraints 1.1.3, the old
   acquired preparation replays on `b1bb176f`, but Cedar and the receiving source
   reject it. Its 13 differing leaves are solely `assessor_source_sha256` from
   the updated CIF assessor. The original comparator verdict is preserved.
   The shared release owner is investigating this ordinary-reader compatibility
   regression. No chemistry, coordinates, targets or numerical verdict differs
   in the captured preparation comparison.

The diagnostic wraps comparison only to record differences, always returns its
original result, blocks subprocesses, and verifies all 74 frozen request files
remain exact. Archive-backed reads use the declared `attempt_read_view` owner.
An earlier direct-bundle probe omitted that view and encountered missing archived
working duplicates; that is a harness failure, not a product failure. Its log is
retained separately. The fail-before harness also initially assumed three
TypeErrors: the actual expected refusals were two ValueErrors and one TypeError.
The corrected receipt uses the original XML without rerunning those tests.

## Local evidence and next action

The repository-local, ignored `branch-artifacts/Alder/release-compat-20261128-01/`
contains start/source pins, conflict-resolution decisions, test commands/logs/XML,
replay matrix and exact leaf differences. Reproducers are local runners A922–A926
in `branch-artifacts/Alder/runners/`. These paths are workspace evidence, not
operational references required by a committed scientific artifact.

The native-Python child relocation probe also lacks installed `openpyxl` after
its subprocess resets `PYTHONPATH`. The complete release environment supplies the
declared dependencies; that relocated read passes there. An unrelated registered
import was narrowed to its explicit topology role, with a fail-before regression.
The later ordinary publication import still requires its installed dependencies.

Receive the release owner's reader fix, qualify the
installed package and relocation, then fast-forward/push Alder's preserved merge
history. Receive the actual released-main SHA separately. Preserve dependency
limits explicitly and retire only owned disposable test/package scratch after
retaining its results. Scientific follow-up is still explicit Hg placement and
a numbered open XYZ/DNA group-B child with both crystal-image forces.
