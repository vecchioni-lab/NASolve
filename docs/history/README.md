# Historical NASolve documentation

These records explain earlier experiments, failures and design choices. They
are not current instructions: branch names, commands, test counts, paths and
next steps may be obsolete. Start with the [current handoff](../development-handoff.md),
then the relevant contract from the [documentation map](../README.md).

## October 10 reconciliation — exact backups

Source: `a7edddf2059df06c41c015c4cf4a40f318878e2a` (Cedar).
The following files are byte-for-byte copies from that source, made before
shortening or reorganizing active documentation. The `.md.txt` files retain
old relative links as text; historical JSON is not active runtime authority.
Completed native preparation/linkage/coverage now lives in the current ledger;
geometry qualification remains pending. Current queues live in the handoff.

| Original | Exact backup | SHA-256 |
| --- | --- | --- |
| `docs/architecture.md` | [architecture-2026-10-10-pre-reconciliation.md.txt](architecture-2026-10-10-pre-reconciliation.md.txt) | `49ef89b80ee355beffa079c5494f06c53560736a620e1bdb52e11c13fdb56c0c` |
| `docs/campaign-execution.md` | [campaign-execution-2026-10-10-pre-reconciliation.md.txt](campaign-execution-2026-10-10-pre-reconciliation.md.txt) | `7ae2d5e11e5c31fa6fb31020e6b56e41ffc588a6d78e0767028ecca68baea835` |
| `docs/campaign-full-auto.md` | [campaign-full-auto-2026-10-10-pre-reconciliation.md.txt](campaign-full-auto-2026-10-10-pre-reconciliation.md.txt) | `79144ab0912c3f9302f3a12a4a93a281feaac9c99befc0a0447247365c903ba0` |
| `docs/campaign-model-roadmap.md` | [campaign-model-roadmap-2026-10-10-pre-reconciliation.md.txt](campaign-model-roadmap-2026-10-10-pre-reconciliation.md.txt) | `bca908bf25ee20a9f9d40808d4e9bc20a9026bced49778f42013fa4f75ab70a3` |
| `docs/campaign-planning.md` | [campaign-planning-2026-10-10-pre-reconciliation.md.txt](campaign-planning-2026-10-10-pre-reconciliation.md.txt) | `78fd946369bf509204d56c59c6c7f0b7094d8f562639f95e8b4d9d6a1662bb55` |
| `docs/campaigns.md` | [campaigns-2026-10-10-pre-reconciliation.md.txt](campaigns-2026-10-10-pre-reconciliation.md.txt) | `47f5dcd496e9794815cde87af3099b75a4fd9285ff0ae0e73f17cc94d8c66155` |
| `docs/construct-registration.md` | [construct-registration-2026-10-10-pre-reconciliation.md.txt](construct-registration-2026-10-10-pre-reconciliation.md.txt) | `33f4ec713cc1dc82bbf4bc021e04a6a90b1b9db491a0ca1e2c226fdb267be47b` |
| `docs/construct-registration-intent.json` | [construct-registration-intent-2026-10-10-pre-reconciliation.json](construct-registration-intent-2026-10-10-pre-reconciliation.json) | `43bbf9cd1b146a4e6cc80280a913b2ae1fdf28f69862ec340c4bb679277094cf` |
| `docs/construct-registration-live-checks.md` | [construct-registration-live-checks-2026-10-10-pre-reconciliation.md.txt](construct-registration-live-checks-2026-10-10-pre-reconciliation.md.txt) | `c05732f7912621e4bf84054c54b874688ba98a29729f17c1bc27e31826aad2a2` |
| `docs/development-handoff.md` | [development-handoff-2026-10-10-pre-reconciliation.md.txt](development-handoff-2026-10-10-pre-reconciliation.md.txt) | `4bb4125abf7fbd4fd45c894a628eba74d31a20a2dc648773b262a4907d6f849f` |
| `docs/full-auto-patch-handoff.md` | [full-auto-patch-handoff-2026-10-10-pre-reconciliation.md.txt](full-auto-patch-handoff-2026-10-10-pre-reconciliation.md.txt) | `683382cbc70d84926b875dd3fe357343b12cd92188a969d0f572adb939cb38c0` |
| `docs/metal-restraint-builder.md` | [metal-restraint-builder-2026-10-10-pre-reconciliation.md.txt](metal-restraint-builder-2026-10-10-pre-reconciliation.md.txt) | `b11a55d0159caca2adad051c5a4ef99488593597c45974d15914e16d5e1caaf7` |
| `docs/metal-restraint-builder-intent.json` | [metal-restraint-builder-intent-2026-10-10-pre-reconciliation.json](metal-restraint-builder-intent-2026-10-10-pre-reconciliation.json) | `bfe4fb1fd8d682e91fcd1027f6d64cc48791ef765e2210e547466828f92b9de6` |
| `docs/model-compatibility-facts.md` | [model-compatibility-facts-2026-10-10-pre-reconciliation.md.txt](model-compatibility-facts-2026-10-10-pre-reconciliation.md.txt) | `897a46f6473d9ac9751802d6c9e83c3f66406b7691fbe8e9e24ffacdd233fe80` |
| `docs/modified-component-preparation.md` | [modified-component-preparation-2026-10-10-pre-reconciliation.md.txt](modified-component-preparation-2026-10-10-pre-reconciliation.md.txt) | `87c55ed8375e1c1355923efffea45fd7695042524469982f1caa2651dd207ca5` |
| `docs/modified-component-preparation-intent.json` | [modified-component-preparation-intent-2026-10-10-pre-reconciliation.json](modified-component-preparation-intent-2026-10-10-pre-reconciliation.json) | `44e6017515aac47f038279d704ac60991ff607c69e5d4d157e8fbb3e87f910e5` |
| `docs/native-modified-pair-live-validation.md` | [native-modified-pair-live-validation-2026-10-10-pre-reconciliation.md.txt](native-modified-pair-live-validation-2026-10-10-pre-reconciliation.md.txt) | `2dbb8974f7a35a409f31ae68d4a3726f407d8c4b02ec84a96bf8a1a3ba33f301` |
| `docs/sequence-family-targets.md` | [sequence-family-targets-2026-10-10-pre-reconciliation.md.txt](sequence-family-targets-2026-10-10-pre-reconciliation.md.txt) | `0cbcb5f4a23cfce62cf7b831c7704513514e0ab2e927dcf7f90452b4595a1221` |

Stable subsystem designs remain active. Superseded session transcripts and
mutable status snapshots moved out of the reading path; no scientific data,
workbooks or native artifacts were removed. Git retains every original as well.

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
