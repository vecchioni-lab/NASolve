# Recipe-controlled full auto

Status: the full-auto/component patch is published; a fresh native campaign
returned four SOLVED outcomes (EA, DiU, Q5cm and provisionally selected QiC).
See [live evidence and reporting follow-up](full-auto-patch-handoff.md) for
exact checkpoints, test results and remaining inspection/merge checks.
Guarded behavior stays the default; numerical success is not user approval.

## Permission to investigate, not automatic approval

A schema-2 preset may explicitly opt into `workflow.mode = "full-auto"`.
A preset is a typed TOML text file; `.toml` or `.txt` is accepted. See the
[W example](recipes/full-auto-5w6w.toml). It is frozen into a **new campaign**:

```bash
./nasolve campaign plan NEW_ROOT --preset docs/recipes/full-auto-5w6w.toml
./nasolve campaign run NEW_ROOT
```

The original recipe source may subsequently disappear; its frozen bytes and
resolved policy remain authoritative. Do not edit an existing plan or silently
upgrade a guarded campaign. Preset schema 1 is unchanged, including its resolved
policy shape/hash. Existing campaign plan schemas 1 and 2 remain readable; the
new preset schema 2 makes older runtimes reject rather than ignore new powers.

Full-auto's first bounded scope is:

- Trial an existing usable **MR_REVIEW, 7 <= TFZ < 8**, through the normal PostMR
  and refinement engines. EA's 7.60 is the motivating case. Keep the raw Phaser
  classification/score, checksummed receipt and a persistent warning. Do not
  globally lower the success threshold or manufacture models for MR_FAILED.
- With `autosol.on_unaccepted = "continue-without-phases"`, continue from the
  intact prepared model after a returned AutoSol WARNING/REVIEW. Never import
  rejected phases. Native refinement still requires usable observations/Free-R
  and determines whether anomalous arrays are available. Full-auto defaults to
  this explicitly frozen fallback; writing `on_unaccepted = "inspect"` retains
  the inspection stop.
- Run the existing bounded Refine Doctor on an eligible refinement review when
  `workflow.run_doctor = true`. This defaults true in full auto. No new MR Doctor,
  donor rescue, unrestricted search, or automatic chemistry inference is added.
- With `workflow.select_recommendation = true`, select a **verified usable
  numerical SUCCESS recommended by Doctor** as the provisional working result.
  Core Doctor still preserves current; the campaign makes and receipts a separate
  selection. Unresolved Doctor REVIEW/repair flags do not become successes.

`run_doctor = false` omits automatic Doctor escalation and defaults selection
false. `select_recommendation = false` runs Doctor but leaves its recommendation
unselected. The ordinary guarded defaults remain unchanged. An explicit CLI
`--through` overrides the recipe endpoint (including an explicit Doctor request);
it does not silently enable automatic selection. Without `--through`, a recipe
that enables Doctor defaults through Doctor, otherwise through AutoRefine.

## What “best” means in this increment

Use the existing bounded recommender's first eligible passing branch, not an
unlimited minimum-Rfree search or a claim of global optimality. Preserve every
failed, reviewed, alternative and recommended checkpoint. Free-R integrity,
required chemistry and usable output checks remain in force.

The result is marked **PROVISIONAL — INSPECT MAPS/MODEL AND DECISION HISTORY**.
Record the prior current checkpoint, selected candidate, reason, policy and
`user_approved = false`. Selecting a working result never sets USER_APPROVED.
`SOLVED` remains a numerical workflow label, not structural/deposition approval.
MR/phase caveats survive downstream numerical passes and appear in campaign
status and `show`. Warning-bearing campaigns can return exit 3 without a
technical execution failure.

Existing `checkpoints use CHECKPOINT` / explicit `show --checkpoint` support
user reversal and comparison. Completed campaign stages are not replayed and do
not reselect the automatic candidate after a user's override. The receipt keeps
the original proposal/decision even when the user later chooses a different
current checkpoint. Model edits remain new immutable children, not overwrites.

## Explicitly omit AutoSol

A synthetic modified-DNA model can exercise construction, restraints and
refinement against donor diffraction that does not represent the model's heavy
atoms. A new schema-2 recipe may explicitly omit the phase stage:

```toml
[autosol]
policy = "disabled"
reason = "Synthetic modified DNA mechanics test against donor observations"
```

The reason is mandatory and frozen with the recipe. This policy is available
in guarded or full-auto mode. Do not supply `on_unaccepted` with `disabled`:
there is no AutoSol result to accept. The default remains `when-anomalous`, and
schema-1 recipes retain their existing behavior and configuration hashes.

NASolve records `SKIPPED` and the reason without discovering a Phenix runtime
for that stage or calling AutoSol. It retains PostMR's nucleotide-candidate
classification, iodine warnings, observation arrays and frozen Free-R flags.
AutoRefine explicitly excludes experimental phase inputs and uses the prepared
PostMR model. Its new checkpoints have no phase input, so subsequent bounded
Doctor trials cannot select a phase-based recipe. An existing AutoSol execution
or accepted-phase report is refused; use a fresh campaign rather than rewriting
historical phase evidence. Native refinement still decides whether the supplied
observations support anomalous refinement. Omitting AutoSol does not switch
anomalous observations off or imply that model heavy atoms are present in the
experimental crystal.

For a methods description: *Campaign phase-stage execution was controlled by
an explicit frozen recipe. In synthetic model tests, AutoSol was disabled with
a recorded reason while preserving anomalous-atom classification and the
original diffraction observations. NASolve's Python coordinator recorded the
skip and invoked Phenix refinement from the PostMR model with experimental
phase use disabled. Optional bounded Refine Doctor trials inherited phase-free
checkpoints. These tests assess workflow and restraint mechanics rather than
validate the synthetic chemistry against the donor diffraction.*

Regression fixtures cover candidate preservation, no AutoSol invocation,
phase-free refinement and Doctor checkpoints, refusal of previous AutoSol
evidence, and execution after relocating the campaign and deleting its original
path. These are offline fixtures, not a native Phenix/Coot validation of this
new policy; the native synthetic challenge remains a separate live check.

## DiU iodine and 5CM

The observed **8.843 A C5-I5** failure was a NASolve atom-name parsing bug:
`strip("'\"")` removed a meaningful prime from `C5'`, allowing the sugar atom to
overwrite ring `C5`. With the same packaged 5IU ideal coordinates, the ring
C5-I5 distance is **2.0951107369 A**; the erroneous sugar C5'-I5 distance is
8.8430304195 A. Remove only matching surrounding quotes. Do not change the
supplier's coordinates, introduce a new bond target, or loosen the guard.

PostMR now records explicit iodine expectations for the existing curated 5IU
(I5) and C38 (I) targets. Missing/wrong-element atoms or a present iodine absent
from anomalous-candidate classification are warnings, not silent skips.
Refinement and the presented Doctor trial report whether iodine was detected,
AutoSol returned accepted phases, anomalous observations/scattering were used,
and experimental phases were actually used. These are distinct statements.
Do not force anomalous mode or invent wavelength/Bijvoet observations when data
cannot support it; preserve the resulting diagnostic.

Phase-use diagnostics distinguish `experimental_phases_requested` (the option),
`experimental_phase_inputs_present` (this report names a phase file and four
nonempty distinct coefficient labels), and `experimental_phases_used` (both).
They include `phase_file`, `phase_labels` and
`phase_usage_basis = "reported-refinement-inputs-v1"`. A true option without
inputs does not mean phases were used; available AutoSol phases do not prove
a Doctor branch used them. The check reads only the supplied report and makes
no new scientific decisions or filesystem-existence assumptions. Missing
legacy input details cannot establish positive use. Historical receipts are
not rewritten when the reporting code is corrected.

5CM is the requested methyl-deoxycytidine component. The earlier run resolved
its identity and then failed to locate the local dictionary. Supply the unchanged
parameterized MonomerLibrary 5/5CM.cif (Git blob
`a8a590f15f0b50c42ed9ad46d59eec3aab11d583`), already classified DNA, with provenance.
The ferry explicitly obtains that pinned resource at installation; solving does
not download chemistry. A read-only installed-library regression checks the
5CM record. Keep the final code/pair class unchanged; use DC as the existing
construction hop. Internal phosphate handling uses the supported component set
and verified site connectivity, not another DZ-only dispatch. Frozen old profile
scopes are not reinterpreted.

## Validation boundary

The attached QiC transcript already demonstrated same-invocation Doctor:
`QiC/AutoMR/run_002`, recommendation `refine-002`, current still `postmr`; old
reports/registries/plan and other members remained unchanged. That was the
**guarded** policy, not validation of new full-auto selection.

New tests cover policy/schema/defaults, original MR evidence, explicit endpoints,
phase rejection without phase reuse, dependency propagation, provisional choice,
non-selection of unusable outcomes, user veto surviving resume, iodine detection
and selected-branch diagnostics, exact primed atom parsing, 5CM resource identity,
installed workbook semantics and linked-phosphate scope. Returned full-checkout
and four-member native full-auto results are preserved in the
[published checkpoint](full-auto-patch-handoff.md). Rejected-AutoSol continuation
was not exercised by that native cohort; its members either accepted or skipped
AutoSol. The [development handoff](development-handoff.md) owns remaining gates.
Do not repeat GZ11 merely to prove a separate new policy. Source-native P2
1W5->DZ / 1WA->DP conversion validation remains separate work.
