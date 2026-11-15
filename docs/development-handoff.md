# NASolve development handoff — current state

Updated **2026-11-15, C322 durable bond attribution complete — Rowan**.
Worktree **NASolve-c96**, branch **cedar**. Native source checkpoint **1b9a9918**;
C319 published as **c4adb6b2**, C320 as **794e0d7b**. This follow-up adds
native target-only energy/force attribution and compact evidence. Focused
checks only; no full suite, branch, default activation or merge. Linden owns
Pine/Willow and does not edit Cedar.

## Current work and interruption recovery

**Window: 16:25–19:25 London, extended by up to one hour if needed.** C318/C319
jobs are complete with return code 0, verified stopped owners and unchanged
source pins. C321 is also complete/stopped; the native window is free and Linden
has been informed. Keep expensive checks serial.

C319 ordinary root: `319_Cedar_ordinary-output-sync-_ycu9ff8` under the local
`NASolve-live-tests` anchor. It creates unselected PDU **refine-003** from postmr,
using C308's exact target-only PHIL, original observations/Free-R, four processors
and five cycles. Selected **refine-001**, all prior checkpoint records and old
scientific outputs are preserved. Only the expected root report/history and
registry change; the exact previous report is reconstructible.

C319 independent readback root: `319_Cedar_written-output-readback-0ed6xqcd`.
Both actual written formats reproduce saved scattering without a B correction:
PDB ΔRwork/ΔRfree = 4.40e−7/3.17e−5; mmCIF = 1.14e−6/3.53e−6. All 1,234 run
files stay unchanged during readback. Saved scattering reproduces the fit
Rwork/Rfree 0.206236/0.236192 and retains the original Free-R mapping. Coordinates
and printed geometry exactly match C308; only model ADPs change. Do not rerun
these successful controls or reinterpret them as chemical-survival approval.

**C321 is complete/stopped:** `321_Cedar_native-bond-attribution-lf7mvpjs` under
the live-test anchor. One 5.53 s native job rebuilt four exact PDU/5PC contexts,
recorded actual bond slack/limit/top-out and compared native single/container
energies and gradients. Target changes account for the whole energy difference
(−55.15143/−11.10162 native units), with force-difference errors below 6e−14.
Potential options are unchanged: slack 0, limit −1, top-out false. An independent
synthetic softened-potential finite-difference control passes. All 88 old files
remain unchanged. No refinement or adoption. Source pins: working C321 over
794e0d7b; see start/driver/native execution records. No retry is needed.
The 25 new regressions failed before implementation; **123 focused tests pass**
(1.90 s), including existing torsion/plane numerical gates. No full suite.

**C320 delivery gate is complete:** the maintained source/reference candidate
rebuild, full-monomer coverage and captured-input binding pass for PDU and 5PC's
existing C308 dictionary captures. One bond target changes in each; every other
recorded native field is exact. Both source library references reproduce. All 46
input/capture files per control remain unchanged; no native tool was rerun.
Final local root: `320_Cedar_native-target-delivery-kpghikw9`. Source pins are in `start.json`.
Earlier pre-producer-hardening cold pass is retained at
`320_Cedar_native-target-delivery-2jx19f6g`; do not duplicate it again.

**C322 is complete/stopped:** `322_Cedar_durable-bond-attribution-yn1bos1w`.
Both PDU/5PC pass the shared owned attribution route: two native jobs, four exact
manager rebuilds, 13.49 s including cold relocation. Both fresh readers pass with
original inputs/SDK blocked; 176 saved files and all 88 original files stay
unchanged. The unpacked proof trees total 60.8 MB, not a new ordinary retention
policy. Source pins (working C322 over 315fe3e2) remain unchanged.

The old plane worker identities/policy are unchanged. A synthetic old-format
report reads identically after relocation with original paths removed. The actual
native PDU preparation/registry also passes: **1,234 files unchanged**, current
**refine-001**, checkpoints through refine-003 retained (70.29 s; no native job).
The focused selection passes **193 tests (47.87 s)**, including plane lifecycle,
repair chain and prepared execution. A new relocation test fails on 315fe3e2
before the bond API exists. No full suite; no repeated successful controls needed.

**Current next step:** authenticate selected-library reference authority and bind
it through existing repair/selection owners. C322 closes durable kernel evidence,
not source chemical approval, derivative qualification or ordinary selection.
Diagnostic PHIL delivery is not ordinary corrected-CIF delivery. PDU's remaining
bend and whole-substituent survival remain open Q06 work. Keep native readers
serial with Linden; all C322 owners are stopped and its window is clear.

Linden W78 reports a distinct native-copy hazard: generic deepcopy/pickle drops
nonbonded radius/ionic/donor tables despite matching contacts, whereas tested
native identity selections retain energy/gradient behavior. It is queued under
Q06; no Cedar fix or source-manager-copy adapter is installed. Current final
output synchronization retains the same geometry owner. Do not interrupt target
repair or build a duplicate contact engine for this new idea.

C320 focused validation: **184 passed in 21.17 s**, covering the new gate,
reference candidates, repair chain and captured mixed gradients. Initial 34
regressions fail before implementation; the first implementation also exposed
the macOS temporary-directory alias, now resolved before strict candidate replay.
No full suite. Exact command is in the ledger entry below.

## What changed and what is qualified

C318 synchronizes only stale final ADPs from the exact current Phenix scattering
object, requiring unchanged coordinates, scattering, FCALC and geometry owner.
A temporary final-writer binding records completion/restoration. New requests use
`round-local-parallelity-execution-v2`; exact frozen v1 sources/readers remain.
No SDK edit or new restraint target/strength/default. Joint neutron and mismatches
beyond ADPs remain unqualified. C319 verifies the actual five-cycle writer and
serialized outputs on **Phenix 2.2.1-6174 / dispatcher 2.2.1, Darwin arm64**.
No Coot repeat or new native relocation qualification.

The reader follow-up rejects non-text policy identifiers through CheckpointError
instead of leaking TypeError. Four new regressions fail before the guard; all
**39 reader tests pass** afterward (9.91 s), including v1/v2 cold relocation and
weakened-evidence refusal. Frozen native helper bytes are unchanged. Exact command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/svecchio/Documents/Amsterdam/_Wind/GitHub/NASolve/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_refinement_parallelity.py --tb=short
```

C318's broader focused check remains **140 tests +13 subtests** (16.58 s).
Last full suite: **C220/583d30df, 9,178 tests +276 subtests**, not this revision.
No full suite is requested in this work window.

## Evidence, earlier findings and pipeline

The existing `cif-linked-native-registration-evidence.json` ledger owns exact
commands, hashes, local anchors and limits; avoid duplicating its full history:

- C307 `linear_neighborhood_reference_candidates_2026_11_15`: graph-selected
  triple neighborhoods, supplied references, separate target-only candidates.
- C308 `matched_linear_neighbor_refinement_2026_11_15`: 1.470 Å terminal target
  gives PDU/5PC lengths 1.4818/1.4864 Å. Existing strengths/data unchanged.
  PDU angles 175.02°/173.94° remain REVIEW; 5PC scoped triple screen passes.
- C309 `linear_arm_opening_force_review_2026_11_15`: geometry favors both tested
  opening motions; no opposing plane/nonbonded derivative in these directions.
- C310–C317 `pdu_scattering_state_and_opening_forces_2026_11_15`: final scattering
  mismatch traced to stale hierarchy ADPs. Temporary reconstruction indicates
  data favors one opening and opposes the other. No guessed combined weight,
  optimizer-history reconstruction or permission to strengthen restraints.
- C318 `versioned_refinement_output_state_2026_11_15`: implementation and isolated
  native guard; its then-pending writer limitation is closed by the new entry.
- C322 `durable_linear_bond_attribution_2026_11_15`: shared owned lifecycle,
  native PDU/5PC cold relocation, legacy compatibility and focused regressions.
- C321 `native_linear_bond_target_energy_2026_11_15`: full fixed-point energy/
  force attribution and native bond options; persistent owned replay remains next.
- C320 `native_linear_bond_target_delivery_2026_11_15`: exact target-only
  dictionary delivery and captured context; energy/authority still separate.
- C319 `ordinary_written_refinement_output_state_2026_11_15`: actual writer,
  independent native readback, reader regression and preservation evidence.

PDU run: `303_Cedar_PDU-campaign-btuh5sop/relocated-after-c304/DiU/AutoMR/run_001`.
5PC run: `305_Cedar_5PC-campaign-nu1t7jyw/relocated/DiU/AutoMR/run_001`.
Both are relative to local `NASolve-live-tests`. C304/C305 already qualified moved
archive-backed reads. Earlier attempts, failures and original selections remain.
These are substituted-scaffold controls, not modified-crystal diffraction data.

**Q04/Q05 are accepted for the explicit supported route** at C285/d5996bc4.
Q06 remains open; Q08 supplies numerical/force diagnosis. The
[completion queue](cif-doctor-completion-queue.md) is the sole work order, retaining
combined/unfamiliar ligands, sugar/fluorine learning, PNA, locked sugars, catalogue
coverage, chemical states and false alarms. Q15 reporting/PDF and Q16 AutoPhase,
full integration/platform validation and reviewed release cleanup remain later.
No automatic merge or default activation.

## Scientific and collaboration boundaries

Original PDU:PDU B:1 means intended incoming symmetry continuation: **P/OP1/OP2,
no OP3**, superseding the earlier free-OH reply. C295's B:7 O3′ image `-x+y,-x,z`
at 3.34019 Å is a candidate, not confirmed linkage. D:1's separately declared
complete terminal phosphate remains distinct. No blanket OP3 removal, inferred
free OH or lone symmetry bond without its surrounding chemistry/forces.
Pine owns editable intent; TopoStitch previews; Cedar distinguishes intent,
coordinate evidence and enforcement. Linden's source-frame/packing tests are
separate experimental evidence, not an installed Cedar adapter. Current checked
plane forces refuse symmetry planes; no SDK edits.

Simon authorizes code/tests and compact evidence pushes. Models, reflections,
CIFs, full inventories, logs and runners stay local. Keep one expensive scientific
reader at a time; preserve failures and original science. Retire duplicates only
through qualified existing owners. No 100-native-dataset capacity claim. Check
current docs/history before new work; keep new ideas queued unless Simon explicitly
redirects. Cross-agent notes are signed **— Rowan**.
