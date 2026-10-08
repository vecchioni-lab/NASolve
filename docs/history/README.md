# Historical NASolve documentation

These records explain earlier experiments, failures and design choices. They
are not current instructions: branch names, commands, test counts, paths and
next steps may be obsolete. Start with the [current handoff](../development-handoff.md),
then the relevant contract from the [documentation map](../README.md).

## October 8 consolidation — last long current-state records

These two files preserve the full pre-prune bodies (with an archival banner).
Current priority moved into one short
[handoff](../development-handoff.md), and the exact five-case scientific
matrix into one [live ledger](../native-modified-pair-live-validation.md).
Source commit before pruning:
`eaa6b201b947fbd19dcf17648947d513ca8a053a`.

- [Development handoff before pruning](development-handoff-2026-10-08-pre-consolidation.md):
  previous long Pine P1–P7 chronology, all prior full-auto cases, provenance
  records, PR #24/#25 evolution and historical next-step statements.
- [Native modified-pair ledger before pruning](native-modified-pair-2026-10-08-pre-consolidation.md):
  literal run_001 N2 failure, run_002 Saenger failure, run_003 numerical
  success, workbook/dictionary audits and per-gate test plan as recorded
  before the latest user live `nasolve show` acceptance.

**Do not execute their old next-step commands or promote superseded
statuses.** Every original pre-prune source also remains in Git at the
source commit; these files are for forensic readability only.

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
