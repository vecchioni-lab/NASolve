# NASolve development handoff — current state

Updated **2026-11-14, C302**. Active **cedar** in NASolve-c96. Remote last verified
**C301 `bea76681`**, including C295–C300.
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

**C299 committed/pushed `b4739c76`:** `autorefine --checked-plane-forces` uses the
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

**C300 committed/pushed `d9f3bbb8`:** explicit schema-2 campaign choice and Refine
Doctor API/CLI reuse the same runtime checks and immutable round owner. Focused
validation: 233 tests +61 subtests pass, no full suite. Native control
`300_Cedar_doctor-plane-forces-ncuo_h42` passes one existing ML-fixed-scattering
trial at refine-004 from refine-003, keeping refine-003 current. The recipe
deliberately excludes experimental phases; original observations and Free-R stay
fixed (audit valid/NOISY). All 58 parameters retained; relocated cold read passes.
524 original files, 129 prior-round files and 576 readback files unchanged.
Driver rc0, known stopped, source pins unchanged. Runtime evidence 2.17 MB;
clone-on-write logical total is not unique physical storage.

**Next:** use existing source-selected geometry readers to inspect actual outcomes.
Run a fresh PDU:A campaign control from C270's declared chemical test scaffold,
with explicit checked preparation/plane forces and no experimental phases. This
is a mechanical substitution control with retained observations, not donor
chemistry or a solved structure; it does not unblock original PDU:PDU/B:1. Keep
the original source and all failed work.

**C301 committed/pushed `bea76681`:** fresh declared A:PDU control
`301_Cedar_PDU-campaign-idfuqpan` passed preflight/Phaser/Coot, then the phosphate
guard stopped B:4 outgoing O3′–P displacement. No ReadySet/refinement ran. All
jobs stopped, source pins and five original inputs unchanged. Mixed Coot context
omitted the also-declared canonical A:12 DC→DA mutation from serial authority;
raw OP3 then prevented graph restoration. C80 covered related curated sites.
The generalized explicit canonical serial-only scope now passes 237 focused tests
+10 subtests and read-only replay of actual C301 output. All 31 failed-run files
unchanged; full phosphate validation passes with no further atom removal. No
new phosphate/graph authority, no SDK changes. Historical policy is preserved;
failed final proof retains attempted scope and established rollback behavior.

**Next:** fresh A:PDU campaign on this fixed source, then inspect source-selected
ring/C5/propyne/chi through ReadySet and actual refinement. Record staged geometry,
not just tool completion. The prior failed run and original PDU:PDU/B:1 stay
untouched. Q06 remains open.

**C302 fixed, being committed:** `302_Cedar_PDU-campaign-fig6ru2e` passes
construction, PDU generation/repair and ReadySet, then refuses v2 outer completion
before checkpoint/refinement: parent bucket 143.7 MB also counted the owned repair
child. All processes stopped; source pins and five original inputs unchanged.
V3 separates that exact child, retaining 128 MiB/1024 files per part, 32 MiB members
and 128 MiB shared physical expansion. Actual unique attempt contents 94.0 MB;
all 743 observed attempt files unchanged. V2 still refuses the original grouping.
Old archive/retention and relocated new-format tests pass; exact frozen policy
is bound on read. No migration or retirement of failed C302. Native retries need
a fresh request/run. Full validation commands/results are in the existing ledger.

**Next:** fresh PDU campaign on the committed fix, then source-selected staged
chemistry, cold readback and actual consumer membership. Local c303 runners are
prepared; c304 G:5PC is deferred until PDU succeeds. No active native jobs, no
full suite. Original PDU:PDU/B:1 stays separate and untouched. Q06 remains open.

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
