# NASolve development handoff — current state

Updated **2026-11-14, C299**. Active **cedar** in NASolve-c96. Remote last verified
**C298 `85a45a0f`**, including C295–C297.
C295 records corrected phosphate intent and a read-only symmetry observation. Simon's
cutoff is **23:00 Europe/London, 2026-11-14**; interruptions expected. Focused tests
only: **no full suite, new branch or merge**. Linden owns Pine/Willow.

## Corrected intent and publication

- **B:1 intent:** Simon explicitly superseded his earlier free-OH reply: preserve
  P/OP1/OP2, no OP3, with intended incoming covalent continuation to a symmetry
  copy. C295's read-only native calculation finds B:7 O3′ under `-x+y,-x,z`
  nearest at 3.34019 Å in both original MR and prepared coordinates. This is a
  candidate image, not a confirmed partner or formed bond. All 19 original inputs
  and 72 C290 files remain unchanged. D:1's separately declared complete terminal
  phosphate is distinct; no new blanket OP3 policy or atom edits.
- **Shared ownership:** Pine carries editable declared topology; TopoStitch
  previews it; Cedar distinguishes intent, coordinate evidence and actual native
  enforcement. Reslicing must map identities/images or flag unresolved mappings,
  retaining previous choices. No absent Cartesian neighbor implies free OH.
- **GitHub publication:** after the initial automatic rejection Simon explicitly
  authorized pushing compact evidence. Code/tests/compact notes may be pushed;
  raw science, models, diffraction data, logs and runners remain local.

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

**C299 complete, being committed:** `autorefine --checked-plane-forces` uses the
configured Phenix Python, isolates zero-cycle native setup outputs, and requires
explicit continuation through corrected ancestry (including manual edits).
99 focused tests +33 subtests pass. Native CLI one-cycle continuation produced
refine-003 from C298 refine-002, kept all 58 complete plane parameter rows, and
passed cold relocation with both request formats. Omission refuses before native
work/new round; an uncorrected sibling keeps legacy behavior.

Local control `299_Cedar_cli-continuation-n0qa9yxh`: actual CLI returned zero and
selected its new checkpoint in the isolated clone. Outer driver rc1 is preserved:
it incorrectly expected a PDB from zero-cycle setup, which writes EFF/GEO/log/MTZ.
Separate readback finished relocation/inspection without another refinement.
All native jobs stopped; source pins unchanged. Exact files/counts/storage and
commands are in `explicit_cli_plane_force_continuation_2026_11_14` in the ledger.

Prior qualified foundations: C296 `1d455fdd` validates complete plane parameters;
C297 `fe7e9fd7` freezes the exact local native implementation and restores bindings;
C298 `85a45a0f` joins ordinary AutoRefine/checkpoint readers and passes five cycles
plus cold relocation. Its argument-only preflight failure remains stopped/readable.
C291–C294 qualify five-cycle/fork/replacement-manager forces. Preserve original
Free-R, NAR membership, observations and native targets. No SDK edits. Native
version is Phenix 2.2.1-6174 / dispatcher 2.2.1, local Darwin/arm64 exact profile;
version labels alone are not broader capability or pristine-distribution proof.

**Next bounded step:** carry the explicit choice through campaign and Refine
Doctor owners without a new executor or default activation. Then achieved chemical
geometry, PDU/held-out survival and broader platform/capacity scope. Do not duplicate
Linden's endpoint observer or topology owners. C299 is a command/continuation
qualification, not complete chemistry or PDU acceptance.

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
