# Alder receiving compatibility — 28 November 2026

This is release integration evidence, not a new crystallographic result. A01
remains partial and A02 quantitative trials remain gated. The metal roadmap is
still the single forward queue.

## Scope and behavior

The receiving history starts at published Alder `1efcd034`, preserves all 13
first-parent receiving commits through `b1bb176f`, and integrates Cedar
`02c61e9b`. Release candidate `29eaba73` is received in `85330f7a`; final Cedar
`47caea97` is now integrated and qualified. The actual released-main merge and
normal Alder push remain pending. The installed source matches every packaged
file byte for byte; this is not yet a delivered-main claim.

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
| Installed interface panel | 153 passed / 49 subtests; the corrected source-assuming relocation fixture separately passed | Disposable NASolve 0.2.0 installation; original build removed |
| Final Cedar changed-owner installed panel | 147 passed, then all 35 public-data fixture cases passed after supplying installed reference data | Same native libraries and NARestraints 1.1.4 |
| Release guide / inspector / CCD shuttle | 33 passed | Complete Python 3.12.14 release environment |
| Final installed FT parent, phase and Coot binding after relocation | PASS, 70.49 s; 227 installed modules; 130 unchanged input files | Original NARestraints 1.1.3; original/build paths absent or denied |

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
   Cedar `47caea97` fixes this ordinary-reader regression by separating
   dictionary comparison from component assessment and validating known historical
   assessor identities against the full unchanged assessment. The recorded
   identity stays intact; arbitrary fingerprints and changed findings still
   refuse. The original comparison showed no changed chemistry, coordinates,
   targets or numerical verdict. Both source and installed genuine readers pass.

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
replay matrix and exact leaf differences. Reproducers and packaging continuations are local runners A922–A934
in `branch-artifacts/Alder/runners/`. These paths are workspace evidence, not
operational references required by a committed scientific artifact.

The native-Python child relocation probe also lacks installed `openpyxl` after
its subprocess resets `PYTHONPATH`. The complete release environment supplies the
declared dependencies; that relocated read passes there. An unrelated registered
import was narrowed to its explicit topology role, with a fail-before regression.
The later ordinary publication import still requires its installed dependencies.

Receive the actual released-main SHA, verify its source delta against the
qualified candidate, then fast-forward and push Alder with normal history. No
schema migration, saved evidence rewrite, new refinement or automatic checkpoint
selection is needed. Older compiler-specific evidence still requires its exact
recorded provider; current 1.1.4 is intentionally refused with an explanatory
message on that old C80 record. Scientific follow-up remains explicit Hg placement
and a numbered open XYZ/DNA group-B child with both crystal-image forces.


## Harness corrections and retained failure evidence

Installed tests initially assumed that `repo/src` still existed. The workbench
relocation fixture now copies the actual imported package. The CIF tests receive
only public data copied from the installed wheel; no Python source tree or import
fallback is restored. Only affected cases were rerun. One relocated-read harness
also placed its output JSON under the input deny list: all reader assertions had
passed, but writing that receipt was refused. It now writes to disposable scratch,
with the original input denials unchanged. The failed logs remain separate.

Local receipts preserve the exact command vectors, working directories, source
and test hashes, versions, XML and results: `owners-result.json`,
`native-result.json`, `metals-result.json`, `metal-host-result.json`,
`ordinary-import-{before,after}.json`, `ordinary-full-deps.json`,
`release-guide-result.json`, and `final-cedar-01/result.json`. The initial owner
panel explicitly used 1.1.3; later current-provider panels used 1.1.4. No complete
suite was rerun by Alder: the release owner retains that responsibility.

All generated experimental inputs remain local and excluded from Git. Completed
synthetic-test scratch retirement recovered 540,159,720 bytes after checking host
processes and recorded simulated child PIDs. Disposable package trees are also
retired after their retained wheel/source hash and relocated-input receipts.


## Future Willow join: package ownership

The common copied-package test fixture and the native-recipe damage fixture now
copy actual `refinement-runtime-*.json` archives rather than an enumerated subset.
This permits the frozen Willow transport resource to coexist with Alder's frozen
native-recipe and explicit-NA resources without hiding a deliberate damage check
behind an unrelated missing-file error. All tamper assertions remain in force.

The three metal web patterns now belong to `nasolve.metal` in package data.
The rebuilt installed namespace contains exactly the same 448 code/data objects
as the prior qualified manifest. No runtime source, policy, saved evidence or
scientific parameter changes. The two affected suites pass **87 source cases** (20.33 s) and **87 installed
cases** (19.07 s); all four metal web objects remain exact. Their commands, object hashes and
retired scratch size are in `package-ownership/result.json` in the same local
compatibility evidence folder.
