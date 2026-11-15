# NASolve development handoff — current state

Updated **2026-11-15, C319 written-output acceptance — Rowan**.
Worktree **NASolve-c96**, branch **cedar**. Native source checkpoint **1b9a9918**;
this follow-up adds reader hardening and compact acceptance evidence. Focused
checks only; no full suite, branch, default activation or merge. Linden owns
Pine/Willow and does not edit Cedar.

## Current work and interruption recovery

**Window: 16:25–19:25 London, extended by up to one hour if needed.** C318/C319
jobs are complete with return code 0, verified stopped owners and unchanged
source pins. No native job remains active. Keep expensive checks serial with
Linden; he was told the native window is free after C319.

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

**Current next step:** numerical-candidate delivery through existing repair and
selection owners. Bind the exact source/reference and target-only dictionary
change to complete native before/after inventories, retaining component origin.
Existing native captures, numerical replay, selection and repair-chain code must
be reused. Diagnostic PHIL delivery is not ordinary corrected-CIF delivery.
PDU's remaining bend and whole-substituent survival remain open Q06 work.

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
