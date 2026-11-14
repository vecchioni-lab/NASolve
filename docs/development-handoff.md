# NASolve development handoff — current state

Updated **2026-11-14, C278**. Active **cedar**, NASolve-c96; base before this
patch **C277 `16494c4`**. Simon originally authorized12:36–14:36 Europe/London;
Linden relayed Simon's extension to16:00 with wind-down signal expected. Focused
checks only: **no full suite, new branch or merge**. The
[completion queue](cif-doctor-completion-queue.md) owns unfinished work.

## Latest result — the prepared bundle reaches real refinement

C277 allows only the initial checked preparation registry into first campaign
refinement, preserving prior/partial/unknown work and newer choices. Its first
actual campaign control C278 completed AutoSol but refinement dry-run rejected
C138's bare full-model interpretation policy. The failed run is preserved.

C278 now creates an exact round-local `refinement` wrapper for only that known
policy, preserving its False value and argument position. Original preparation,
historical worker bytes and inherited restraints stay unchanged. The small
schema-1 `refinement_inputs.json` receipt binds source/copy hashes, sizes and order;
AutoRefine and checkpoint readers rederive it. Unknown input is not rewritten.
Old readers do not verify the optional evidence; old refinement code still rejects
the bare policy, so old-version continuation is not qualified.

Fresh control `279_Cedar_refinement-policy-2cfxjsvp` uses a distinct pristine C276
copy and the ordinary campaign coordinator/stage worker. Phenix2.2.1-6174 completed
AutoSol and all five refinement cycles: AUTOREFINE_READY, Rwork0.1971/Rfree0.2222.
Seven original PHIL/CIF inputs, explicit D:1 phosphate protection and original
FreeR_flag/test0/generateFalse remain. Effective native parameters retain the
full-model flag False. This is a software control, not a solved-structure claim.

All native stage groups stopped. All257 original source files and206 PostMR files
retain bytes/timestamps. After relocation, exact refine-001 inspection works with
old/source/SDK reads and native launches forbidden; all462 campaign files remain
unchanged. Cold read57.75s,606.7MB Python peak. Whole control70.1MB; the new policy
copy/receipt add841bytes. Raw science and logs stay local, excluded from Git.

Validation:198 focused tests+19subtests in19.51s; final size guard15tests in2.81s;
relocated temporary checkout15tests in4.15s after original path disappears. Code
copies removed, small validation records retained. Exact commands/hashes and
negative controls: `refinement_policy_namespace_2026_11_14` in the
[evidence ledger](cif-linked-native-registration-evidence.json). Failed native
preflight: `campaign_first_refinement_native_2026_11_14`. No full regression.

## Reuse completed work

- C274 `6403407` / C275 `d2381fc`: exact sealed AutoSol save completion, verified
  producer/group stop, ordinary-command reuse before discovery, real interruption
  and relocated readback. Pre-seal/unowned/unknown work stays preserved.
- C276 `d5f505a`: explicit source-preserving-v1 profile reaches normal checked
  PostMR/prepare-run/frozen campaigns. Real preflight/Phaser/Coot/NAR/ReadySet/
  retirement and cold relocated reading pass.231tests+47subtests.
- C277 `16494c4`: first-refinement folder gate and newer-choice guard.
  190tests+26subtests, final focused11. No second scientific reader.
- C252 later alternatives, C258/C260 interrupted retirement, C270–C272 selected
  phasing/Coot, C273 inspection-local numerical reuse remain their existing owners.
  Do not rebuild transport, readers, recovery, publication or a compiler.

## Next — finish scope reconciliation without hiding limitations

Q04/Q05 core preparation and chosen-input handoff now have an actual normal
campaign control through refinement. Overall closure is not claimed: reconcile
serial/repeated-failure capacity and explicit opt-in/recovery scope in the queue.
Keep one heavy reader and sequential campaign work. Measured single controls are
not a hard native scratch-disk quota or a100-dataset capacity test. Failed work
is retained; no new allowance or cleanup policy was introduced.

Unsealed AutoSol results, uncertain/shared/foreign groups, absent outer campaign
receipts and historical unarchived campaigns are not automatically adopted.
Standalone AutoSol still lacks isolated child ownership; do not invent a parallel
owner or retrofit old evidence. Default checked-route activation remains explicit.

**Simon’s downstream PDU requirement is saved:** an earlier beautiful PDU reportedly
distorted after collaborator refinement. Exact files/revision/tool/settings are
not yet identified; no cause is diagnosed. Q06 must compare built/ReadySet/refined
geometry and effective native restraints: ring, trigonal C5, propyne coplanarity,
internal propyne and chi/base orientation, plus sugar/phosphate/pair/Free-R intent.
Use generalized source-graph checks and a related held-out substituent. Do not
interrupt the current task or equate ReadySet acceptance with refinement survival.

C279’s5IU descriptive C5 elevation reaches1.33degrees; its native ring plane includes
I5 at0.020A deviation/sigma0.020A. Final GEO prints42covalent planes,3user planes,
58user parallelities. These are useful observations, not complete membership,
derivative or scientific qualification; PDU remains untested here. Q06 must retain
the known ordinary-native parallelity-gradient boundary and Linden’s distinction
between bond edits/exclusions and additive contact energy. WillowW38/W39 findings
are reported context, not combined Cedar-build validation.

Q07 mixed/held-out controls and Q08–Q14 chemistry learning remain; Q15 reporting
and Q16 AutoPhase compatibility, integration checks and reviewed merge are later.
Last full suite: **C220/583d30df,9,178tests+276subtests**, not a current pass.
Linden owns Pine/Willow; everyday NASolve/pine code remains untouched. Signed
cross-agent handoffs: **— Rowan**.
