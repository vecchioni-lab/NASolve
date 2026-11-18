# NASolve development handoff — current state

Updated **2026-11-18 evening, C402 / C403 — Rowan**.
Active branch **cedar**, worktree **NASolve-c96**. Runtime candidate **`23c1f411`**
adds only the narrow publication cleanup fix described below. Its 162 focused checks
pass; Linden owns independent review and one pinned installed/full qualification.
The last full-qualified runtime is `4f7aeb84`, identical in source/tests/packaging to
`d8656b22`: **12,008 passed, 2 existing native opt-in skips, 293 subtests** in
3581.07 s with NARestraints `a9264f9e`. Do not describe that as a full pass of C402.

## Current checkpoint

**C402 — archive successful preparation without losing its usable result.**
New v3/v4 ordinary publications now share the existing retirement owner. Previously,
automatic bond preparation used v4 and skipped this cleanup. The v4 regression fails
before the fix; focused coverage includes old/unknown layouts, optional cleanup
errors, broken exact-result detection, real interrupted deletion and moved readback.
Historical publication and inspection do not trigger cleanup. No new schema,
chemistry rule, executor or storage owner.

Separately, explicit existing-owner retirement of completed C401 reduces its whole
root from **250,794,627 to 53,055,067 bytes**, 1,048 to 245 files. All eight public
model/PHIL/CIF paths, bytes and timestamps remain unchanged. Exact archived result
and ordinary registry cold reads pass; the retirement worker stopped. This is one
real preparation, not a 100-dataset capacity claim. The earlier C401/Hazel inventory
is pre-retirement evidence; the transition is recorded, not hidden.

**C403 complete — the fresh PDU preparation reaches ordinary refinement.**
The genuine C401 `postmr` REVIEW parent now has an unselected `refine-001` child.
Five cycles preserve original observations/Free-R, all ordered restraints and D:1
protection, with no experimental phases. Actual inputs/settings match C338 except
paths. Both phases reproduce its native state, selected atoms/definitions/proxies
and correction calls; final whole-model atom inventory and all 3,239 reflection rows
also match. Rwork/Rfree are 0.2125/0.2265. Triple angles remain 175.4494°/174.4251°,
so the existing coordinate screen remains REVIEW. This closes ordinary integration,
not the remaining chemical-survival gate. No repeated native experiment is needed.

The worker stopped after 424.92 s; cold readback leaves 283 current and 57 C338 files
unchanged. Hazel independently verifies 358 bindings/measurements without native
calls. All 243 original surviving preparation files stay unchanged; only the ordinary
registry/root report are appropriately updated. A byte-verified 1.28 MB delta archive
records the new child and depends explicitly on the retained C401 parent archive.

**Next bounded code: actual-final trigonal geometry, using existing evidence.**
C206 requires local trigonal/exocyclic geometry alongside triple-axis reporting.
C208 already selects supported centres from source connectivity; its Cartesian
measurements exist in `cif_plane_geometry`. C338 already captures selected-site
heavy coordinates and native plane membership at full precision. Ordinary chemical
readback currently reports only triples. Compose these existing parts into a new
explicit read-only report, preserving old reports/worker bytes and unsupported scope.
No plane strengthening, coordinate editing, new acceptance threshold or PDU-name rule.

## Reuse the existing science

| Evidence | What it establishes; what it does not |
| --- | --- |
| C401 | Fresh AutoMR/Phaser → Coot/NARestraints → new source/plane generation → automatic bond discovery/repair → ReadySet → ordinary initial REVIEW publication. No borrowed C327 checkpoint authority. Published model, five PHILs and two dictionaries reproduce earlier corrected inputs. Preparation is not refinement survival. |
| C329 / C338 / C392 | Corrected PDU targets reach actual Phenix; the terminal C5B–C5M single target is 1.470 Å and C5A≡C5B remains 1.174 Å. Five-cycle PDU still bends. C392's passive weight observer exactly reproduces model/native state/maps and 1,962 correction calls. Do not repeat delivery or weight sweeps. |
| C395 / C396 | Declared pairing dominates pooled unweighted bond delta², not necessarily energy. Excluding only declared pairing from eligibility changes choices but does not repair chemistry: some lengths improve while terminal plane offset and diffraction agreement worsen. No production selector or threshold change. |
| C397–C399 / Hazel A85 | Actual-state FFT score/force mismatch is isolated; direct calculation agrees locally. Matched fresh histories still stop at rounding/iteration bounds without repairing sugar–base/metal strain. These diagnostics are complete; do not restart them without a new hypothesis. |
| C400 / Willow W137–W139 | Explicit 100-cap control and matched native/zero/full pair mechanics are qualified. Zero reproduces native history/model/reflections; passive full reproduces ordinary full. All arms share the existing plane-force correction. Seventeen added terms improve pair geometry, but all stop with lower-bound line-search errors before the cap. Not convergence or modified-residue acceptance. |

C400's same-fourteen-pair written-model comparison gives selected G:C plane mismatch
27.30→6.30°, A:T 8.85→4.59° and pair-distance RMS 0.247→0.200 Å. The A:T contacts
remain long. Final Rwork/Rfree are 0.2267/0.2613 for native/zero and 0.2271/0.2609
for full. Final clashscores are 23.27 and 24.77; the old runner's 32.28 was initial,
with a separate immutable amendment. Small Rfree/clashscore changes are context,
not standalone rejection gates. Same-coordinate denominator changes explain scalar
jumps, not the complete cause of stopping. Full-precision twelve-core-pair results
remain distinct from the fourteen-pair rounded-PDB comparison.

The A:PDU substituted scaffold is a mechanics control; its observations are not
claimed to come from a PDU crystal. Original PDU:PDU/B:1 intent remains separate.
C401's rounded published geometry has terminal single length 1.457987 Å, triple
1.189433 Å, adjacent angles 176.401°/176.885°, and terminal carbon distance from the
six-atom ring plane 0.094297 Å. These descriptive starting values are not acceptance.

## Next work, in order

1. Finish C402's independent full gate (relocated installed checks pass), retain
   C403's completed ordinary evidence and update the compact science checkout.
2. Use the resulting actual-manager evidence to identify the remaining chemical
   defect. Q06 needs useful PDU/DF geometry after refinement and whole-substituent
   evidence, not merely successful execution or a readable CIF. Reuse existing
   source-selected geometry/coverage and native observation tools before adding code.
3. Close any needed combined ordinary descendant coverage through existing owners.
   Keep wider counted protocols and density-fitting policy separately qualified;
   finite map coefficients alone do not establish a valid density-fitting policy.
4. Q07: original mixed scaffold with ATL alongside, then the held-out modified-pair
   challenge. Retain L-DNA/FANA/L-FANA/L-FDNA/PNA/locked-sugar learning under Q08–Q14.
   Q15 explains the result. Q16 ends with the AutoPhase compatibility audit,
   combined-source/full/native gates and merge review. No automatic merge or defaults.

The [single maintained queue](cif-doctor-completion-queue.md) owns closure criteria.
Q04/Q05 are complete for their recorded supported route; narrow integration gaps do
not reopen all ownership foundations. Linden owns Willow/TopoStitch and Hazel owns
Alder; coordinate before shared-source or native work. Do not duplicate their runs.

## Scientific boundaries to preserve

- **Native ownership:** C381–C391 provide preflight admission, counted-intent
  continuity, exact written-model proof and compact actual-final pair capture.
  Existing v3–v7 emitted workers keep their bytes; explicit v8 is separately bound.
  Missing optional improvement can retain a qualified parent. Unknown process state
  never authorizes retry, deletion or in-place repair.
- **PDU:** native planes and targets are present. C338 angles 175.4494°/174.4251°
  retain REVIEW. Do not flatten the molecule, copy coordinates into targets or
  strengthen restraints merely to force a pass. Site projections avoid incorrectly
  treating an isolated reference's OP3 as missing from linked B:4.
- **DF:** lab DF is 2-thio-dT/A1AAZ. Existing whole-base transport improves C1′–N1
  construction to 1.49958 Å, but Hazel's matched refinement stretches it to 1.662440 Å
  at native precision. Good construction is not successful refinement; preserve
  curated sulfur/iodine protections and the separate metal experiment's authority.
- **DY:** explicit packaged-source/backbone composition and ordinary construction
  are connected through C366. The C4–N1T single bond joins two independently rotatable
  rings; do not impose a common plane. PDU→DT→DY and the reverse preserve the shared
  scaffold under the explicit deoxy rule. Broader sugar-family placement and DY
  pairing semantics remain separate; do not invent NARestraints relationships.
- **Phosphates:** original PDU:PDU B:1 is incoming symmetry continuation with
  P/OP1/OP2 and no OP3, superseding the earlier free-OH answer. B:7 O3′ is a candidate
  partner, not confirmed linkage. D:1 terminal protection is separate. Remove OP3
  only with proven incoming bonding; no blanket removal or invented symmetry angles.
- **ReadySet:** C323 traced the old 1.607 Å target to upstream RM1/GDIIS output after
  nonconvergence; ReadySet retained the supplied dictionary. Prefer source-faithful,
  independently checked repair over repeating the same generation for longer.

## Evidence, storage and reporting

Exact commands, revisions, limits and hashes are in the existing
[evidence ledger](cif-linked-native-registration-evidence.json). Current entries:
`fresh_automatic_pdu_publication_2026_11_18` (C401)
and `automatic_bond_publication_retention_2026_11_18` (C402), and
`fresh_ordinary_pdu_refinement_child_2026_11_18` (C403). Historical worker,
chemistry and construction entries remain evidence, not a second active queue.
Models, reflections, logs and archives stay local; compact evidence alone is committed.

The eight-file science checkout (about 1.2 MB) is
`ScienceCheckouts/Rowan/2026-11-18/review.html` under the sibling GitHub root. Update it
with completed effects, reusing original model links and the Linden/Hazel checkouts.
Do not copy raw datasets to decorate reports. Private continuity and coordination
notes stay outside the product repository.

The earlier audit of 3,965 test definitions found seven exact-body groups with
mostly distinct owners/parameters, and no accidental imported-test collection.
Do not delete tests merely because their bodies look similar. Retire only verified
owned duplicates through the appropriate owner; unrelated local files and peer
work remain untouched. Archive size does not measure peak temporary disk or memory.
