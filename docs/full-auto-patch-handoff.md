# Full-auto patch recovery checkpoint

Updated 2026-10-06. **Recover the already-applied local patch; do not reapply it.**
This note is the narrow handoff for the pending ferry. The ordinary development
handoff owns project ordering; the full-auto and component contracts own policy.

## Published versus local state

Last verified remote Pine head before recovery: `d3e1fa389b73843edb5bf33569622cf7b839220e`.
This is the Doctor-transition patch, with returned local regression of 148 tests
+ 85 subtests (37.94 s) and 785 tests + 224 subtests (67.75 s). QiC's fresh guarded
campaign attempt_002/run_002 entered Doctor in one invocation, recommended
refine-002, and left current at postmr. Previous reports, registries, plan and
other members were preserved. This is not full-auto auto-selection evidence.

The subsequent `NASolve_full_auto_and_components_fix.py --apply --validate
--publish` applied its candidate to Simon's local working tree at that head.
The component audit passed, then the focused suite returned **1 failed,
350 passed, 59 subtests passed in 48.72 s**. The ferry stopped before its full
suite, commit/push and any native launch. Do not treat its local files as already
published, and do not repeat its non-resumable --apply command.

Original receipt/backups/logs (user-local, not repository inputs):
`~/NASolve-live-tests/full-auto-component-patch-jf62b0z4/receipt.json`.
Keep the original receipt and patch diff intact; recovery writes a separate
receipt and logs. Do not reset/stash/clean the user's unrelated files.

## Exact failure and correction

Failing test:
`tests/test_campaign_stages.py::CampaignStageTests::test_campaign_refine_doctor_receipts_new_trials_and_preserves_current`.

Its old mocked Doctor returns `SimpleNamespace(round_directory=round_two)` for
a trial. New iodine diagnostics access `trial.checkpoint_id`, then the selected
trial's `report_path`. Both fields belong to the production AutoRefineResult
contract. The mock supplies neither, causing AttributeError before assertions.

Repair the fixture with an explicit refine-002 checkpoint ID and a real synthetic
trial report. Assert that the audit reads that report's anomalous/phase/observation
settings, carries any iodine warning, and keeps current unchanged. Do not hide
this failure with getattr defaults, skip the test, or suppress the production
audit. This recovery changes the fixture/documentation, not the pending runtime
policy. Broader suite results remain the next validation gate.

## Component facts verified in the user's environment

The installed workbook has exactly one 5CM record: cytosine sheet, Base Analog C,
DNA, with the printed N1/C2/N3/C4/C5/C6 role mappings. 5CM is the requested code;
its DC parent and installed local dictionary resolved successfully. No workbook
edit is needed to rename it.

The repaired 5IU reader returned ring C5-I5 = **2.0951107369301507 A** and distinct
sugar C5'-I5 = **8.843030419488558 A**. The earlier apparent long bond came from
stripping the prime and replacing ring coordinates, not bad supplier geometry.
The native DiU placement/anomalous route and 5CM refinement still need fresh tests.

## Candidate scope to carry forward

[Full auto](campaign-full-auto.md) is a recipe-schema-2 opt-in: downstream trials
for retained MR_REVIEW (7 <= TFZ < 8), explicitly permitted rejection-of-phases
fallback, bounded Doctor, and separately recorded reversible provisional
selection of its passing recommendation. Core Doctor stays non-selecting.
Existing frozen guarded plans do not gain new permissions. Selection is never
USER_APPROVED; preserve warnings and all alternative checkpoints. Full-auto
selection is user-authorized scope, not a breach of the older guarded policy.

The same candidate fixes C5' parsing, supplies pinned parameterized 5CM, retains
all intermediate hops, and audits iodine presence versus actual anomalous
refinement/phase use. `1W5 -> DZ` always and `1WA -> DP` remain separate P2 work;
shipping DZ or 5CM is not implementing those conversions.

## Resume order

Use `NASolve_full_auto_recover.py` with the original receipt. It verifies the
expected applied files, repairs the fixture, installs these continuity docs,
runs the previously failing test, the original focused selection, then the full
suite. Commit/push the explicit original patch plus recovery files only after
success and only if remote Pine still matches the original base. A failed check
preserves work and logs. No scientific run or main merge is part of recovery.

After returned green tests, inspect the actual published head and create a NEW
explicitly full-auto campaign for EA/DiU/Q5cm and provisional-selection tests.
Do not edit the existing frozen TestSets plan into a new mode. Preserve its
campaign root `~/NASolve-live-tests/TestSets-dd59b4f-jjra04s9`. Successful GZ11
run_002/refine-001 already passed Simon's visual Coot check; do not rerun it just
to refresh the notes. Complete the bounded Pine live/regression/merge gates,
then return to main and make Scout operational.

The [metal-restraint builder](metal-restraint-builder.md) is newly recorded
future design, not implemented and not another Pine merge gate. It uses workbook
atom roles, visible selectable spheres/constraint overlays, one or more chosen
metals, and reusable geometry recipes without moving coordinates in the editor.
Simon will supply examples. See its contract/intent instead of duplicating the
full design here.

## Recovery validation

Status: **USER_LOCAL_RECOVERY_TESTS_PASSED; NATIVE_FULL_AUTO_PENDING**. The recovery artifact itself has
isolated fixture-contract and staging checks; it is not a full NASolve or native
Phenix/Coot execution. The recovery runner appends the actual returned local
commands and test summaries here only after its suite succeeds.

### Returned recovery tests

Tested working tree based on `d3e1fa389b73843edb5bf33569622cf7b839220e`. Local receipt: `~/NASolve-live-tests/full-auto-component-patch-jf62b0z4/fixture-recovery/receipt.json`.

fixture: **1 passed in 2.87s**

```text
/Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q tests/test_campaign_stages.py::CampaignStageTests::test_campaign_refine_doctor_receipts_new_trials_and_preserves_current
```

focused: **351 passed, 59 subtests passed in 49.26s**

```text
/Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q tests/test_campaign_full_auto_policy.py tests/test_campaign_full_auto_pipeline.py tests/test_component_lookup_repairs.py tests/test_presets.py tests/test_campaigns.py tests/test_campaign_execution.py tests/test_campaign_doctor_transition.py tests/test_campaign_pipeline.py tests/test_campaign_stages.py tests/test_campaign_executor_cli.py tests/test_construction_scaffolds.py tests/test_dictionary_compatibility.py tests/test_dictionary_postmr.py tests/test_linked_phosphate_profile.py
```

full: **851 passed, 224 subtests passed in 80.67s (0:01:20)**

```text
/Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q
```

These are user-local tests, not CI or native crystallographic validation.
The runner commits/pushes separately only after its final integrity checks.
