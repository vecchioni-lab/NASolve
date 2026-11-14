# NASolve development handoff — current state

Updated **2026-11-14, C294**. Active **cedar** in NASolve-c96. Remote last verified
**C289 `7e843af7`**; C290 is committed locally as **`c911bdc5`**. C291–C294 code,
tests and native evidence are complete and being committed locally. Simon's
cutoff is **23:00 Europe/London, 2026-11-14**; interruptions expected. Focused tests
only: **no full suite, new branch or merge**. Linden owns Pine/Willow.

## Pending decisions and publication

- **B:1 intent:** C290's original PDU-pair model has P/OP1/OP2 but no OP3 or verified
  incoming O3′–P link; only D:1 is declared terminal phosphate. Simon was asked
  whether B:1 is free hydroxyl, a complete terminal phosphate or an incoming
  symmetry linkage. No answer yet. Preserve the stopped attempt; do not alter
  phosphate or infer a link to force the control through.
- **GitHub publication:** automatic approval review rejected C290's push because
  compact PDU measurements/provenance may be unpublished science. Simon was asked
  explicitly to authorize compact-evidence publication; no answer yet. Keep new
  commits local and do not retry the push. Raw science/logs/runners stay local.

## Accepted foundations

**Q04/Q05 are accepted for the explicit supported route and recorded controls**
at C285 `d5996bc4`. The [completion queue](cif-doctor-completion-queue.md) is the
sole work order. Prepare/check/repair, retain alternatives and failed attempts,
recover known-stopped work, and deliver exactly the chosen model/restraints.
C276–C279 join actual preparation, phasing and five-cycle refinement; C280 preserves
native exhaustion; C282 retains earlier archived alternatives and current choice.
C283's 100 synthetic datasets reduce hash reads 651,504 → 13,104. C284 reuses pure
math within a read; source/ownership checks stay fresh. Do not rebuild these owners.

Recorded whole-request retention: one success 35.1 MB, two archived successes
65.7 MB, two native failures 70.7 MB. These are not native 100-dataset disk/RAM
capacity or hard quotas. Keep work serial, one expensive reader at a time.
Defaults, old-run migration, broader capacity/platform checks and full integration
remain Q16. Last full suite: **C220/583d30df, 9,178 tests +276 subtests**.

## Q06 — real refinement preserves the intended chemistry

C286/C287 establish the C279 prepared/final GEO memberships (45 planes,
58 parallelities); the checked reader avoids the installed parser's truncation.
C288 exposes a diagnostic contact/normalization change when switching families.
C289 keeps all terms active and demonstrates an actual ordinary startup force
error: raw fails 17/20 sampled directions, diagnostic correction passes 20/20 at
identical score. Do not attribute PDU distortion to this independently found defect.

**C291–C294 now qualify an explicit kernel-composition mechanism.** New
`cif_parallelity_kernel.ParallelityKernel` reuses the unchanged both-first-planes
correction, preserves the native score and adds checked forces atomically to the
caller's existing array. It installs no hook and adds no ordinary runtime option.
Unit-cell/symmetry planes remain unsupported; counters are process-local evidence.

- C291 startup: adapted 20/20, raw fails 17/20; identical score/contacts/normalization.
- C292 actual one-cycle programs: adapted endpoint 20/20, raw fails 18/20.
- C293/C294 actual original five-cycle recipe: endpoint 20/20, same static
  restraints and indexed Free-R (4530/250 test), 25 process receipts including
  fork workers. Phenix 2.2.1-6174 / dispatcher 2.2.1; exact source hashes recorded.
- C293 completes refinement but a later exact normalized-score assertion after
  model.select(all atoms) fails; preserve its rc1. C294 records contacts 8041→8060,
  total terms 11321→11340. Unnormalized targets are identical, maximum force
  difference 5.7e-14; the selected manager's own normalized force probe passes.
  This diagnostic division never changes optimizer normalization.
- All drivers/native jobs are stopped. C294 driver returns zero; source/SDK files,
  original 410 run files and 64 earlier capture files stay unchanged. Local roots
  `291_Cedar_kernel-compatibility-33uhgsdp`, `292_Cedar_ordinary-cycle-k4cfrddj`,
  `293_Cedar_kernel-five-cycles-jjxia03q`, `294_Cedar_manager-copy-kzcnunvi`.

Focused command: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTHON -m pytest -q
-p no:cacheprovider tests/test_cif_parallelity_kernel.py
tests/test_cif_parallelity_correction.py tests/test_cif_objective_probe.py`
→ **62 pass, 3.17 s**. Nineteen regressions fail before the API; 19 pass from a
relocated minimal source copy with its temporary original absent. Seven saved
reports replay without native execution and with 275 files unchanged; this is
arithmetic replay, not whole-run portability. Exact evidence:
`explicit_parallelity_kernel_compatibility_2026_11_14` in the existing ledger.

**Next bounded gap:** qualify an explicit ordinary NASolve execution route for the
adapter, binding native capabilities/full consumed parameters and policy through
existing immutable attempt/checkpoint owners. Keep default behavior unchanged.
Historical static signatures omit some optional fields; source/version labels
alone are not universal capability proof. Other platforms/process modes, complete
chemical acceptance and PDU survival remain open. Do not patch installed Phenix,
drop NAR terms, retune chemistry or duplicate Linden's W46 endpoint observer.

## PDU control remains separate

C290 current ordinary PDU A:12/B:4 construction preserves parent chi (0.027°/0.006°
deviation; old construction both ~+53°). Current C5 elevations are 1.114°/1.016°
before repair. Old/current literal dictionaries differ despite equal parsed
atom/bond graphs; bond-length changes are not a one-patch causal comparison.
The known raw-W B:1 guard (C188/C189/C270) then stops intake. No repair, ReadySet,
publication or refinement ran. NAR has no T:T pair recipe and does not invent one.
All 19 original inputs and 72 attempt files stay fixed. Output:
`290_Cedar_PDU-pair-current-k3sdohpc`; read receipt `c290_read_records/geometry.json`
under ignored runners. C252's A:9/synthetic observations are a different control.

Simon's collaborator before/after files, native version and settings remain
unidentified. Compare built/ReadySet/refined ring, trigonal C5, propyne geometry
and chi while retaining sugar/phosphate/pair/Free-R intent. PDU and a held-out
substituent must demonstrate graph-based transfer. Q07 mixed/held-out scaffold,
Q08–Q14 retained chemistry learning, Q15 reporting and Q16 AutoPhase/integration
follow. Signed cross-agent notes: **— Rowan**.
