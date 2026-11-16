# Historical metal foundation pause — 16 November 2026

This records superseded scoping and a retained October Cedar snapshot. It is
evidence, not the current task queue. Read the [current handoff](../development-handoff.md)
for A01 status and next work. Relative documentation links have been rebased;
scientific receipts and their recorded paths are unchanged.

## Retained October Cedar context

Metal integration updated **2026-11-16** in the section below. The following
Cedar boundary is the retained **2026-10-26 snapshot**, not a new statement of
the separate checkout's current status. It records native receipts, user visual
review and verified geometry/DF bundles. **Active candidate: `cedar`; integration target: `pine` (draft PR #26),
then `main` (draft PR #23).** The current laptop Cedar checkout remains at
**`e7451eedbc03c3accc93bc3138dfa9d1d031a7a9`**, with only the explicitly
authorized `src/nasolve/phaser.py` fix modified after the GeoTest rerun.
Its other 45 frozen source hashes, including the distinct curated source,
are preserved. Preserve this local unpublished diagnostic head; do not pull or
replace it with a remote head to continue the run. Diagnostic scripts/derivatives are
not general production support. Earlier wording remains in Git and the
[exact pre-reconciliation backup](development-handoff-2026-10-10-pre-reconciliation.md.txt).

## FT_Hg foundation and storage scoping 2026-11-16 — A40

**Earlier checkpoint:** the user requested a pause after storage scoping to lower
compute; all owned native jobs were stopped. They subsequently resumed A01 work;
the newer A01 handoff above supersedes this historical pause. [Roadmap](../metal-development-roadmap.md) and [storage plan](../metal-campaign-storage.md)
record the implementation order; focused tests only for subsequent bounded work.

**Roadmap correction.** At the user's request, the feature milestones are
explicitly **post-merge**, numbered **A01–A08**. Merging the current experimental
implementation has separate integration/compatibility checks; the feature
completion gates are not prerequisites. A05 is a dedicated scientist/developer
GUI co-design session. A07 requires reconstruction of the metal test solutions
from declared experimental inputs and general mechanics, keeping human solutions
out of construction/search and recording all extra priors and manual intervention.
Historical implementation receipts A37–A40 keep their existing identifiers.
This documentation update does not resume paused native work. Validation: the
Python local-link/numbering audit passes five document links, ordered A01–A08
IDs, both new scope sections and index/handoff consistency; `git diff --check`
passes. No runtime/schema change, scientific artifact changes or pytest run.

**Before/after.** A39 supplied comparison accounting. A40 begins the ligand/open
XYZ/B foundation and now scopes operation-specific storage before campaign
fan-out. Frozen XYZ/B/f′ points keep one pristine parent plus compact Q/f″ data;
geometry-changing work retains Cedar's stronger evidence policy. Important nodes
remain protected, and small fdp maps may be kept until selection within a byte
budget. This is documentation/design, not a pruning implementation or migration.

**Coordination.** Rowan confirmed the C98 DF source/candidate hashes and existing
qualification/preparation APIs. A40 owns a source snapshot of Cedar
`53116e1f1ff2e1d51d6ec2709dd8077c2d72af22`; Alder remains `bcffed56` before this
documentation checkpoint. Cedar archive/retirement owners were inspected and
remain unchanged. The lean metal profile must add its own compact-record and
regeneration contract rather than applying complete-attempt archives to every
frozen point. No general campaign garbage collector is implemented.

**Native evidence.** Phenix 2.2.1-6174, complete fixed-coordinate executions,
not dry runs: two fresh isolated DF controls and baseline/corrected full-model
interpretations completed. Initial reporting failed because the harness omitted
an API argument; native evidence is preserved. A newer full-inventory attempt
stopped because `use_ncs_to_build_restraints=False` was not explicit. Fresh v3
controls supplied it and preserved the PostMR-declared D:1 terminal phosphate.
The latest linked report is **REVIEW** for custom-restraint realization; exact
formal-charge readback is independently **UNSUPPORTED**. Do not claim the full
model is qualified. No A40 XYZ/B refinement or f″ execution has occurred.

Private evidence: everyday checkout `branch-artifacts/Alder/ft-hg-foundation-20261116-01/`,
runner prefix `A40_`. Resume by inspecting `linked-qualification-v3.json` and the
captured custom-restraint evidence, then use the supported Cedar native runtime
and output-state synchronization for a bounded matched geometry comparison.
Preserve the exact DF source HOP2/OP2 state; a different phosphate state is not a
silent replacement. Parent files and every failed attempt remain intact.

**Storage evidence.** A read-only inventory of three saved frozen trials measured
about 1.0–1.17 MB each, with two anomalous maps at 21,420/26,100 bytes. Exact
private file inventories and the explicit 200×100 extrapolation are in
`branch-artifacts/Alder/storage-plan-20261116-01/footprint.json`. Compact 1–8 KiB
records are a design target, not measured implementation. Inputs, maps, native
payloads and this inventory are excluded from Git; no scientific files deleted.

**Files/validation.** Documentation only: new roadmap/storage descriptors,
existing index, anomalous-workflow retention section, changelog and this handoff.
No artifact schema or runtime compatibility changes. Validation: a Python path/anchor audit passes all five new-document links and
three navigation cross-links; the 200×100 size arithmetic passes.
`git diff --check` passes. No pytest/full suite for this documentation slice.
Native results above establish only their stated scopes; the next scientific
gate remains open. User requested the storage plan be settled before returning
to the paused FT_Hg work.

