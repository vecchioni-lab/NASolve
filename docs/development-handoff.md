# NASolve development handoff

Updated 26 November 2026. Cedar is at the Q06 refinement check. Its purpose is to let a
scientist use a supported modified nucleotide without hand-editing a CIF. Coot builds the
residue, NARestraints supplies the intended pairs and stacks, and Cedar checks what
ReadySet and Phenix actually use. The [completion queue](cif-doctor-completion-queue.md#pipeline-position) owns the work order. The [capability table](cif-doctor.md#current-capability-boundary) owns the support
claims.

## Where to resume

In two five-cycle Phenix 2.2.1-6174 fits, the B:4 PDU tip was within 0.033 Å of its
six-membered ring at the end of cycle two. It reached about 0.63 Å in cycle three. The
diffraction calculation began to favor an outward motion as Phenix changed from least
squares to maximum likelihood. The added chemical plane continued to pull inward. At 4.19 Å
the data leave the individual methyl position uncertain. [Measurements, replay and scope](backbone-chemistry.md#when-the-b4-tip-left-the-ring-plane).

Read the two scores on the **same saved molecular state** at the boundary. First reproduce
the recorded working-set gradient. Then keep unrounded coordinates, occupancies,
displacement factors, reflection identities, model structure factors and solvent/scaling
inputs fixed. Record each score's own scale and likelihood estimates separately. Reuse the
C588 replay and C589 per-cycle log reader. If the comparison fails to distinguish the
cause, retain the qualified parent and record B:4 for review. A further intervention needs
evidence that would change that decision. [Q06 and the following transfer check](cif-doctor-completion-queue.md#the-next-small-steps).

## What already works

- **Preparing and handing off a model.** Q04/Q05 closed on the explicit checked route. A
  normal campaign on the recorded control completed preparation, phasing and five
  refinement cycles, then reopened the chosen result after relocation. A separately
  qualified fallback can survive failed optional chemistry. Unknown or failed attempts
  retain their files and identity. [Acceptance and limits](cif-doctor-completion-queue.md#q04q05-acceptance-and-supported-boundary-at-c285).
- **Delivering modified chemistry.** Source-backed PDU and 5PC bond targets and neutral
  DF–adenine chemistry reached native refinement. Two five-cycle rounds used the known
  13-change scaffold, including ATL alongside the eight original pairs. Two close ATL
  contacts and site-dependent PDU/5PC geometry remain. The independent G:5PC C474
  measurements survive, but its final geometry/report no longer resolve at the original
  temporary location for a fresh C587 reading. Reuse its recorded evidence with that limit.
  [Mixed-scaffold requirements](cif-doctor-completion-queue.md#q07--one-mixed-scaffold-ordinary-acceptance-run).
- **Crystal links and deposition.** On the tested 5W6W-derived PDU scaffold, both
  crossovers survived native restart with the original Free-R set. B:1 has P, OP1 and OP2
  and connects to B:7 through a crystal copy. D:1 terminal protection is a separate intent.
  A recut must carry the declared atoms and image into its new numbering. Independent sugar
  class, torsions and local density still matter even when the O3′–P length recovers. The
  deposition guide records what the wwPDB actually returned for the locked-DNA models and
  how to remeasure a reported outlier. [Backbone chemistry](backbone-chemistry.md#the-central-strand-in-the-5w6w-scaffold) · [OneDep checks](pdb-deposition.md).
- **Transfer beyond the original ligands.** Carry the FANA and mirror-sugar stereochemistry
  checks, locked-sugar junctions and connected PNA attachment rules into the ordinary
  route. Census coverage (599 distinct codes in 618 NARestraints rows) identifies the
  remaining work. Geometric survival on one member qualifies only the tested context. [Coverage and chemical-family gates](cif-doctor-completion-queue.md#chemistry-transfer-and-coverage-packages).

## Boundaries with Willow/Pine and Alder

Willow/Pine identifies the logical strand, the crystallographic copy and what changes when
the model is recut. Cedar verifies the component graph, the intended covalent versus
pairing interactions, and the forces and geometry at those endpoints. Alder declares the
metal site, its donors and protected atoms and the occupancy, displacement and
anomalous-scattering policy. When a site crosses those boundaries, carry the same chosen
parent, atom identities, image, dictionaries and Free-R assignments through ordinary
refinement and its returned model. Reuse the shared map sampling, checkpoint and Phenix
readers. The transferable handoff still needs an installed combined-source check. [Integration checks](cif-doctor-completion-queue.md#q16--final-integration-portability-and-retained-artifact-closure).

## Validation and release

C587's plane inspection passed 123 focused tests plus seven subtests. C589's AutoRefine
reporting passed 61 plus 52 subtests. Each set passed from source and from a relocated
installation. Four PDU logs and a separate FT–Hg log support the target reader. C588's
relocated full five-cycle replay reproduced the written coordinates, final geometry and all
140 recorded gradient evaluations for the combined case. These are distinct software and
native checks.

The last recorded standalone full Cedar pass is C406 at `58965920`, with 12,043 tests passed, 293
subtests passed and two native opt-in skips. The later combined C407 experiment had one
location-dependent fixture failure. The fixture correction has focused coverage. Current
Cedar and any combined integration revision still require their own full qualification.
Provisional integration into Pine and eventual main review are separate decisions. [Archived commands and receipts](history/README.md#november-26-cedar-roadmap-audit) ·
[CIF Doctor evidence ledger](cif-linked-native-registration-evidence.json).
