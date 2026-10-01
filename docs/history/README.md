# Historical NASolve documentation

These records explain earlier experiments, failures and design choices. They
are not current instructions: branch names, commands, test counts, paths and
next steps may be obsolete. Start with the [current handoff](../development-handoff.md),
then the relevant contract from the [documentation map](../README.md).

## Exact snapshots retained during the October 1 consolidation

Source commit: `859a29cc77d1c37cb277be8242b3cfb8590ed7f4`.
The following are byte-for-byte snapshots, reusing their original Git blobs:

| Snapshot | Original blob | Purpose |
| --- | --- | --- |
| [September 29 handoff](development-handoff-2026-09-29.md.txt) | `9353b57064280768b1a48bc8ca9c11ace7fe969e` | Long pipeline, terminal-phosphate, campaign, Scout and topology chronology. |
| [October 1 addendum](development-handoff-2026-10-01-addendum.md.txt) | `f96bd68e6b8d036141c71a372e3253a11c2cae4e` | GZ11 experiments, returned 735-test report and library-backed continuation clarification. |
| [Component intent snapshot](modified-component-preparation-intent-2026-10-01.json) | `47cc2cae65c0125da5df451bc77d2f2fdd8a6282` | Exact earlier machine development record, including detailed provenance and unknown validation fields. |

The `.md.txt` suffix deliberately displays original Markdown as archival text.
Its relative links retain their original `docs/` context, not this directory;
use the live documentation map for navigation. The JSON snapshot is historical,
not an active runtime schema or a current work queue. Consult these records for
a specific question rather than automatically loading all of them.

## Earlier focused records

- [1AP integration](1ap-phosphate-integration.md): dictionary replacement,
  connectivity-selected OP3 handling and effective-dictionary precedence.
- [September 11 handoff](development-handoff-2026-09-11.md): early campaign,
  sulfur/force and evidence-provenance decisions.
- [Refine Doctor triage](refine-doctor-triage.md): earlier bounded-trial design.
- [DOHU validation](validation-dohu.md): earlier real-tool evidence and limits.

Use history to explain current behavior, not to override the current contract
or erase a later user decision. Archived validation does not grant new chemistry,
Scout authority, donor eligibility, or permission to overwrite an old attempt.
