# Full-auto patch publication checkpoint

Updated 2026-10-06. **PUBLISHED: `984f75db45607e119ad7fc224ae04cc5d0ffded7` on Pine.**
Recovery and publication are complete. Do not reapply the original patch, rerun
its recovery, or repeat unchanged tests merely to refresh documentation.
This note supersedes the earlier local-recovery instructions. The ordinary
[development handoff](development-handoff.md) owns project ordering; the
full-auto and component contracts own policy.

## Published state and stopping point

Simon returned the successful publication footer, and the GitHub connection
independently verified remote `refs/heads/pine` at the exact commit above.
The user-local checkout reported `pine...origin/pine` with only the existing
untracked files listed. No tracked changes were shown at that point.

The published payload includes recipe-schema-2 full auto, the DiU atom-name
parser correction, the parameterized 5CM resource, iodine diagnostics, the
Doctor fixture repair, and continuity/metal-builder documentation. The final
formatting accommodation is scoped to the pinned 5CM file; its source bytes
were retained. Publication did not launch scientific work or merge main.

Returned user-local regression:

| Scope | Result |
| --- | --- |
| Previously failing Doctor fixture | 1 passed in 2.87 s |
| Focused selection | 351 passed, 59 subtests passed in 49.26 s |
| Full suite | 851 passed, 224 subtests passed in 80.67 s |

These tests ran against the recovered working tree based on `d3e1fa3`, before
publication. They are user-local pytest evidence, not GitHub CI or native
full-auto validation. The publication footer reports code, dictionaries,
original receipts and scientific runs unchanged by the finishing step.

User-local records (provenance, not repository inputs):

- Original: `~/NASolve-live-tests/full-auto-component-patch-jf62b0z4/receipt.json`.
- Recovery: `~/NASolve-live-tests/full-auto-component-patch-jf62b0z4/fixture-recovery/receipt.json`.
- Publication: `~/NASolve-live-tests/full-auto-component-patch-jf62b0z4/fixture-recovery/publication/receipt.json`.

Preserve those records and their backups/logs. No further terminal action is
needed at this stopping point. Untracked environments, old patches and
scientific directories are not cleanup targets.

## Next session: new opt-in live campaign

Prepare a NEW explicitly full-auto campaign for EA, DiU, Q5cm and a suitable
Doctor/provisional-selection case such as QiC. Inspect and freeze the actual
[example recipe](recipes/full-auto-5w6w.toml); do not edit the old TestSets plan
into a new mode. A new plan must explicitly authorize the new behavior.

Validate borderline-MR continuation with retained warnings, DiU construction
and iodine/anomalous evidence, 5CM construction/refinement, and separately
recorded reversible provisional Doctor selection. Do not manufacture a review
or force an anomalous/phasing success to meet a test expectation. Native
full-auto, DiU and 5CM outcomes remain pending at this checkpoint.

Preserve `~/NASolve-live-tests/TestSets-dd59b4f-jjra04s9`. Successful GZ11
run_002/refine-001 already passed ordinary execution and Simon's requested
visual Coot check; no unchanged rerun or repeated visual check is needed.
Complete the bounded Pine live/regression/merge gates, return to main, then
make Scout operational. Standing `1W5 -> DZ` and `1WA -> DP` conversions remain
separate P2 work; shipping DZ or 5CM does not implement those conversions.

## Earlier guarded Doctor validation

The preceding published head was `d3e1fa389b73843edb5bf33569622cf7b839220e`.
Its returned regression was 148 campaign tests + 85 subtests in 37.94 s and
785 full tests + 224 subtests in 67.75 s. Fresh guarded QiC
attempt_002/run_002 entered Doctor in one invocation, recommended refine-002,
and left current at postmr. Previous reports, registries, plan and other
members were preserved. This is not full-auto auto-selection evidence.

## Recovery history: resolved, not instructions to repeat

The original full-auto installer applied its candidate, passed the component
audit, then stopped at 1 failed, 350 passed and 59 subtests in 48.72 s. The test
`CampaignStageTests.test_campaign_refine_doctor_receipts_new_trials_and_preserves_current`
had a mock trial containing only `round_directory`. The new presented-trial
iodine audit also uses `checkpoint_id` and `report_path`, both normal fields
of the production AutoRefineResult contract.

The fixture repair supplied refine-002 and a synthetic trial report, with
assertions that diagnostics read the presented trial's anomalous/phase settings
and preserve guarded current. The production audit was not suppressed or
weakened. The repaired fixture, focused selection and full suite then passed
with the results above.

Publication subsequently stopped on trailing whitespace in the unchanged
upstream 5CM CIF. The finishing helper verified the tested working/staged
payload and pinned dictionary, added a file-specific `.gitattributes`
formatting exception, passed staged-diff hygiene, and published `984f75d`.
No scientific or numerical dictionary change was needed for that formatting
issue. Earlier recovery instructions and the original PR comment describe
historical states, not an outstanding failure.

## Component facts verified in the user's environment

The installed workbook has exactly one 5CM record: cytosine sheet, Base Analog C,
DNA, with the printed N1/C2/N3/C4/C5/C6 role mappings. 5CM is the requested code;
its DC parent and installed local dictionary resolved successfully. No workbook
edit was needed to rename it.

The repaired 5IU reader returned ring C5-I5 = **2.0951107369301507 A** and distinct
sugar C5'-I5 = **8.843030419488558 A**. The earlier apparent long bond came from
stripping the prime and replacing ring coordinates, not bad supplier geometry.
Native DiU placement/anomalous behavior and 5CM refinement still need the fresh
tests above.

## Policy and future metal tool

[Full auto](campaign-full-auto.md) is recipe-schema-2 opt-in: downstream trials
for retained MR_REVIEW (7 <= TFZ < 8), explicitly permitted rejected-phase
fallback, bounded Doctor, and separately recorded reversible provisional
selection of its passing recommendation. Core Doctor stays non-selecting.
Existing frozen guarded plans gain no new permissions. Selection is never
USER_APPROVED; preserve warnings and all alternative checkpoints.

The [metal-restraint builder](metal-restraint-builder.md) and its
[machine intent](metal-restraint-builder-intent.json) are published future
design, not implemented and not another Pine merge gate. A toggleable workspace
or small companion window shares one backend, with clickable atom spheres,
selected metal sites, visible restraint edges and save/load/select recipes.
Canonical workbook role keys such as O4/N3 resolve to actual model atoms;
drawing an edge does not move coordinates or create a chemical bond. Square
planar, one-/two-metal and homo-/heterometal hypotheses remain manually
authorable alternatives. Simon will supply examples and numerical targets.

## Exact recovery commands already executed

All used the user's `.venv/bin/python` with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`.

Fixture:

```text
python -m pytest -q tests/test_campaign_stages.py::CampaignStageTests::test_campaign_refine_doctor_receipts_new_trials_and_preserves_current
```

Focused selection:

```text
python -m pytest -q tests/test_campaign_full_auto_policy.py tests/test_campaign_full_auto_pipeline.py tests/test_component_lookup_repairs.py tests/test_presets.py tests/test_campaigns.py tests/test_campaign_execution.py tests/test_campaign_doctor_transition.py tests/test_campaign_pipeline.py tests/test_campaign_stages.py tests/test_campaign_executor_cli.py tests/test_construction_scaffolds.py tests/test_dictionary_compatibility.py tests/test_dictionary_postmr.py tests/test_linked_phosphate_profile.py
```

Full suite:

```text
python -m pytest -q
```

Publication and this subsequent documentation synchronization are not new
native validation, structural approval or authority to merge main.
