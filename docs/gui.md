# NASolve GUI design contract

Status: **planned, not implemented**. This document defines the durable shell and
interaction model for a future NASolve GUI. The GUI must expose existing guarded
NASolve capabilities without creating a second scientific state model, a second
checkpoint history, or a parallel set of inference rules.

The guiding principle is simple:

> one application shell, one scientific hierarchy, one immutable model lineage,
> contextual workspaces, and progressive disclosure of detail.

Coot remains the external atomic modeler. Phenix/NARestraints remain external
scientific engines. The NASolve GUI orchestrates, visualizes, audits and branches
the same backend operations that remain available from the CLI.

## Why a GUI now

The GUI is not justified by wanting buttons. It is justified by information
density and lineage.

NASolve already has:

- campaign and dataset hierarchy;
- frozen run/stage state;
- immutable checkpoint branches;
- MR/PostMR/AutoSol/AutoRefine/Doctor transitions;
- manual checkpoint imports;
- read-only inspection of non-current models;
- future topology-surgery branches; and
- future donor/re-MR/cross-dataset branches.

A long refinement history or campaign is naturally a graph. A flat terminal
history becomes difficult to navigate even when the underlying provenance model
is correct.

The GUI therefore visualizes the backend NASolve already owns. It must never
silently turn UI state into scientific authority.

## Scientific hierarchy versus model lineage

Keep two different structures visually and semantically separate.

### Scientific hierarchy

The left-side navigator represents *what scientific object is in scope*:

```text
Root / Project
  -> Campaign
    -> Design (optional but first-class)
      -> Dataset
        -> Run
```

A **Design** groups datasets that share one construct/design-level metadata
object. A design may contain several crystals, collections, wavelengths,
processing attempts, or datasets. Design-level metadata may later include the
full strand inventory, tile hypothesis, junction declarations and topology
intent.

Datasets without an explicit design remain valid and may appear under an
`Ungrouped`/direct campaign grouping rather than being forced into a design.

### Model lineage

The central tree/graph represents *what computational/model history exists
inside the selected scope*:

```text
MR -> PostMR -> AutoSol -> refine -> Doctor branch -> manual model -> ...
                                  \-> topology surgery -> refine
                                  \-> future re-MR from historical/refined model
```

The scientific hierarchy and model lineage must not be merged into one giant
tree. Selecting a campaign/design/dataset/run in the navigator changes the scope
of the central lineage/workspace.

## One-window application shell

Avoid a collection of floating NASolve windows.

The ordinary shell has four persistent regions:

1. **Navigator (left)** — where am I?
2. **Workspace (center)** — what happened / what am I working on?
3. **Inspector (right)** — what is the selected thing and what can I do?
4. **Activity drawer (bottom, collapsible)** — what is running / what did the
   engine report?

A breadcrumb across the top shows the current scientific scope, for example:

```text
Amsterdam > Triangle-17 > Crystal-B > run_004
```

Each breadcrumb component is clickable.

The user may resize/collapse Navigator, Inspector and Activity panes, but routine
operations should not create detached NASolve windows. Coot is the intentional
external-window exception.

## Root/workspace selection

Startup should expose a simple **Open Root** folder selector plus recent roots.

A root is a machine-local browsing/workspace concept, not scientific provenance.
The GUI should be able to:

- select a campaign/project/dataset parent folder;
- show recently opened roots;
- detect an existing campaign plan and datasets beneath the root;
- show/restore NASolve's existing active workspace target;
- set/clear the active workspace through the existing backend operation;
- refresh when files change on disk; and
- coexist with CLI use of the same project without maintaining a private GUI
  copy of state.

The GUI must read authoritative manifests/checkpoint registries from disk and
reload safely after external CLI actions.

## Center workspace modes

Use one central workspace with contextual modes rather than separate
applications.

Initial modes:

- **Overview** — human-readable scope status and attention summary.
- **Tree** — model/checkpoint lineage.
- **Compare** — pinned checkpoints/models side by side.
- **Topology** — Registration/Topo Net workbench when explicitly enabled and
  scientifically applicable.
- **Campaign** — campaign/design progress and dataset relationships at higher
  scopes.

Modes appear only when meaningful for the selected scope.

## Viewed versus current versus pinned

These states must never be conflated.

- **Current** is an authoritative NASolve pointer/state and changes only through
  an audited backend selection operation.
- **Viewed** is transient GUI inspection. Clicking around the tree never changes
  current state.
- **Pinned** is GUI memory for comparison/navigation only and has no scientific
  effect.
- **Selected** is keyboard/mouse focus in the UI and likewise has no scientific
  effect.

The current node must always have an unmistakable redundant marker independent
of color. A "Make current" action is explicit.

## Model-tree behavior

The graph must remain useful when a run contains dozens of refinements.

Support:

- pan and zoom;
- collapse/expand repetitive linear refinement chains;
- preserve all branch points while collapsed;
- show stage/model type on every node;
- pin/bookmark important nodes as comparison panels;
- inspect siblings or parent/child metrics without selecting them;
- open any resolvable node in Coot without changing current;
- branch AutoRefine/Doctor/future topology/re-MR operations from an explicit
  eligible source node;
- traverse back to historical nodes without deleting descendants; and
- show manual imports as ordinary lineage nodes with clear provenance.

A collapsed chain may render as, for example:

```text
MR -> PostMR -> refine x 12 -> Doctor
                    \-> manual fix -> refine x 4
```

The same graph component is shared by normal mode and Topo Net.

## Semantic color and shape system

Color is important but must never be the only state carrier. Every semantic
color also has a shape/fill/line/badge equivalent for color-blind use, dark
mode, screenshots and printing.

Use semantic theme tokens rather than hard-coding colors independently in each
view.

### Nodes

Recommended default semantics:

- **ordinary/uninteresting generated node** — hollow neutral grey/black circle;
- **current checkpoint** — blue filled node plus a strong double-ring/target
  marker;
- **explicit bookmark/pinned checkpoint** — blue checkpoint styling plus a
  small pin/star badge without changing scientific state;
- **accepted previous checkpoint on the current successful ancestry** — green
  filled node;
- **needs review / human attention** — yellow/amber node plus `!` badge;
- **blocked/stuck/technical failure** — red node plus `x`/stop badge;
- **skipped/not applicable** — hollow neutral node with dashed outline;
- **currently viewed but not current** — a separate focus halo around whatever
  semantic node style it already has.

Do not reuse blue/green/red to mean unrelated concepts in another workspace.

### Edges

- **current accepted/successful ancestry path** — green, visually stronger line;
- **other preserved lineage branches** — neutral grey/black, visible but not
  highlighted;
- **currently running transition** — blue progress treatment plus a non-color
  animation/pattern indicator when motion is enabled;
- **failed/blocked transition** — keep lineage visible; rely primarily on the
  red destination/status badge, with optional restrained red/dashed edge;
- **comparison/reference relationship rather than ancestry** — dashed neutral
  connector, never confused with checkpoint parentage.

Accessibility preference must allow disabling animation and increasing contrast.

## Inspector: contextual metadata and actions

The right Inspector changes with the selected object rather than opening
separate dialogs.

Examples:

### Campaign/design

- metadata and frozen plan identity;
- dataset counts/status;
- preset/design references;
- full strand/tile metadata where applicable;
- Plan / Run / Pause / Retry actions;
- attention items.

### Dataset/run

- source reflections and processing summary;
- model provider/frame/pair/configuration;
- run/stage status;
- TFZ and MR interpretation;
- PostMR/AutoSol readiness;
- current checkpoint;
- registration/topology status;
- provenance disclosure.

### Checkpoint/model

- checkpoint ID/bookmark/name;
- parent/source operation;
- Rwork/Rfree and relevant model metrics;
- current/viewed/pinned state;
- model/map availability;
- local review status;
- Open in Coot / Refine / Doctor / Branch / Make current / Compare / Bookmark;
- import/export/provenance details in advanced disclosure.

Provenance should use progressive disclosure. Main views should say, for example,
"standard frame catalogue / provider verified"; exact checksums and frozen paths
remain one disclosure click away.

## Live campaign/tree activity

When a campaign or long-running action is active, the GUI should feel alive
without becoming visually noisy.

The scientific Navigator and model/checkpoint tree should update from
authoritative campaign/job/checkpoint records while work proceeds. The GUI may
use filesystem watching plus bounded polling/reconciliation, but it must derive
state from NASolve records rather than treating animation or subprocess stdout
as authority.

A currently running operation should be recognizable at low visual intensity.
Recommended semantics:

- running node: blue active ring/pulse or subtle perimeter shimmer;
- running edge: restrained moving dot/dash/progress treatment from source toward
  the operation/result node;
- active dataset/campaign item: small nonintrusive activity glyph;
- reduced-motion mode: replace animation with a static blue activity badge;
- completed transition: animation stops and the node/edge immediately adopts
  its ordinary success/review/failure semantic state.

Avoid flashing/blinking at high contrast. Motion should indicate activity, not
demand attention.

The live tree should update when, for example:

- a campaign dataset enters preflight/Phaser/PostMR/AutoSol/AutoRefine;
- a new numbered run is allocated;
- a new checkpoint/refinement child is published;
- the current checkpoint changes;
- a stage becomes solved/review/blocked/no-solution;
- a pause request reaches a stage boundary;
- a retry creates a new immutable attempt; or
- an external CLI action changes authoritative project state.

The GUI should tolerate partial publication. It must not invent a successful
node before the corresponding immutable backend record/receipt/checkpoint exists.

Conditional stages must preserve their backend meaning. For example, campaign
state may say the next stage boundary is `autosol` even though PostMR evidence
will cause that stage to record accepted status `SKIPPED` without launching
`phenix.autosol`. The GUI should render this as skipped/not-applicable, never
as a failure and never as evidence that AutoSol was scientifically required.

When first-class campaign workflow recipes are added, the GUI should display the
frozen recipe identity, intended endpoint and conditional path as backend-owned
state. It must not maintain a separate GUI-only notion of "what should run next."

## Human-readable event stream / notifications

The shell should include a **Notifications / Events** stream as a tab or mode of
the bottom Activity drawer, not a floating window.

Its default language should summarize meaningful NASolve state changes without
forcing the user to read internal status tokens or logs. Examples:

- `Crystal-B: refinement 21 passed the numerical gate`
- `Crystal-B: current checkpoint changed to refine-021`
- `Crystal-C: PostMR needs your review`
- `Crystal-D: molecular replacement did not find a solution in this attempt`
- `Campaign paused after Crystal-A PostMR completed`
- `Crystal-F: a new retry attempt is ready`

Every event should retain structured provenance:

- timestamp;
- campaign/design/dataset/run/checkpoint scope;
- event type/severity;
- short human summary;
- authoritative backend status/record reference;
- optional details/metrics;
- relevant artifact/log links; and
- whether user attention is required.

Clicking/expanding an event reveals the technical layer: exact NASolve status
tokens, checkpoint IDs, TFZ/R factors, provider/recipe identity, raw diagnostic,
record/artifact paths and logs as applicable. This keeps jargon accessible
without requiring CLI/GUI swapping.

Prefer typed events derived from structured state transitions. Do not parse
free-form stdout as the scientific source of truth when a structured record
exists. The event adapter may use logs only for supplementary detail.

To avoid notification spam:

- coalesce repeated unchanged RUNNING/heartbeat observations;
- surface stage start once and stage completion/review/failure once;
- prioritize attention/completion/checkpoint-change events;
- allow filters for All / Attention / Completed / System;
- retain a bounded machine-local read marker without modifying scientific
  artifacts; and
- never make dismissing/reading a notification alter campaign scientific state.

## Activity drawer

The bottom drawer replaces most transient report/log windows and contains at
least **Events** and **Technical Log** views.

Collapsed form may show one line:

```text
Crystal-B - refinement 21 passed - refine-021
```

Expanded **Events** view shows the high-level human-readable stream above.

Expanded **Technical Log** view may show:

- currently running backend action and stage;
- stdout/stderr/log tail;
- low-level progress/heartbeat information;
- warnings/errors;
- exact generated command/backend action for forensic use;
- structured status/receipt identifiers; and
- links to full immutable reports/artifacts.

Closing/collapsing the drawer does not stop work.

## Needs Attention

At campaign/root scope, provide a first-class **Needs Attention** filter/queue.

Examples:

- ambiguous registration;
- MR review / competing candidates;
- Rwork >= Rfree;
- Doctor review;
- unsupported/backbone review required;
- failed/stuck stage;
- Topo seam/junction geometry failure;
- manual Coot review required;
- changed/missing frozen input integrity issue.

Attention is a view/filter over authoritative backend states, not a separate
workflow database.

## Current CLI capability coverage

The GUI should eventually expose the existing CLI surface rather than forcing
users back to Terminal for routine operations.

### Environment / app setup

Current CLI:

- `check`;
- `configure phenix`;
- `configure coot`;
- one-run Phenix/Coot overrides.

GUI:

- Settings/Environment panel;
- green/yellow/red runtime health for Python/Phenix/Coot/NARestraints;
- Locate/Change Phenix and Coot;
- advanced per-action override in the Inspector when genuinely needed.

### Workspace

Current CLI:

- `workspace use`;
- `workspace status`;
- `workspace clear`.

GUI:

- Open Root / recent roots;
- active-workspace indicator;
- Make Active / Clear Active actions;
- breadcrumb navigation.

### Presets

Current CLI:

- `preset check`.

GUI:

- Preset/Design inspector;
- validate preset/resources;
- show checksum/integrity issues without requiring JSON output.

### Campaigns

Campaign setup should not assume every laboratory uses AutoPROC/STARANISO.
Before planning/running, the GUI should show a compact **input capability
assessment** per dataset:

- **MR-ready** — reflection observations + cell/symmetry are sufficient;
- **Refinement-ready** — authoritative refinement observations and Free-R are
  available;
- **Anomalous-ready** — anomalous arrays plus required wavelength/element
  context are available;
- **Deposition-ready** — collection/processing metadata is sufficient for
  curation/deposition.

These are independent capabilities. A dataset may be MR/refinement-ready while
deposition remains locked. Missing deposition metadata must not be presented as
a reason that structure solution itself is impossible.

The first implemented profile remains AutoPROC/STARANISO MTZ +
`Data_1*.cif` + `summary.html`. Future GUI import should also admit generic
MTZ input when its contents satisfy the relevant gates, plus SCA/Scalepack as a
direct MR-capable source when Phenix can consume it. If later stages need a
derived MTZ, the GUI should show that as a separate provenance-bearing conversion
artifact rather than hiding it inside import. Unsupported formats remain visibly
unavailable rather than being guessed.

Current CLI:

- `campaign plan`;
- `campaign status`;
- `campaign run --through ...`;
- `campaign pause`;
- `campaign retry`;
- dataset selection.

GUI:

- Campaign workspace and Navigator;
- **visual workflow-recipe builder** that exposes only backend-supported,
  validated capabilities;
- sensible defaults preselected where the backend has a real default, with
  advanced/rare choices progressively disclosed;
- recipe preview/validation showing the same frozen backend policy the CLI would
  consume—no GUI-only workflow configuration;
- optional future **"apply Doctor as needed"** control. When off/absent, review
  states stop for attention; when enabled, only eligible bounded Doctor
  transitions may run automatically;
- Plan button;
- stage-through dropdown for explicit validation/debug boundaries;
- Run selected / Run campaign;
- Pause after active stage;
- Retry selected dataset;
- structured integrity/status display;
- design-level grouping when implemented.

### AutoMR

Current CLI options include:

- standard frame W / 3GBI / explicit frame;
- ordered pair;
- explicit model selector;
- P1 standard shunt;
- config source;
- frames directory;
- preflight versus execute;
- mirror.

GUI:

- dataset/run action card;
- common options shown directly;
- dangerous/rare options (for example P1 standard shunt) behind an Advanced
  disclosure with the same warning semantics as CLI;
- Preflight and Run Phaser as explicit actions;
- provider/model/config preview before execution.

### PostMR and backbone review

Current CLI includes:

- PostMR;
- Coot override;
- explicit MR-review continuation;
- modified-pairs-only mode;
- experimental unreviewed-backbone continuation;
- `backbone-review`.

GUI:

- PostMR action card;
- review gate shown in context rather than as a modal;
- backbone experimental state appears in Needs Attention;
- Open Review in Coot / Record Human Review actions.

### AutoSol

Current CLI:

- conditional `autosol`.

GUI:

- AutoSol appears only when the run is eligible/relevant;
- heavy-atom/anomalous context shown in Inspector;
- run result becomes an ordinary lineage stage/node.

### AutoRefine

Current CLI includes:

- refine current or `--from` historical checkpoint;
- recipe label;
- cycle count.

GUI:

- Refine from selected/current node;
- cycles and recipe in a compact action popover/Inspector;
- every attempt becomes an immutable child;
- current pointer semantics remain unchanged from backend.

### Refine Doctor

Current CLI includes:

- source checkpoint;
- cycles;
- max trials;
- interactive inspect/select behavior.

GUI:

- Doctor from selected eligible node;
- recipe-level "apply Doctor as needed" may launch Doctor automatically at an
  eligible review gate, but does not itself authorize selecting a candidate;
- bounded options shown before launch;
- candidate siblings rendered directly in the tree;
- recommended/inspection candidate highlighted descriptively;
- **Inspect/Open in Coot**, **Yes/No confirmation**, and **Make Current / keep
  current** are explicit GUI actions equivalent to the CLI interaction;
- Open in Coot / Make Current remain separate actions, preserving viewed versus
  current semantics.

### Checkpoints

Current CLI includes:

- list;
- bookmark current;
- import manual PDB;
- optional deliberate replacement MTZ;
- explicit parent;
- select checkpoint.

GUI:

- Tree mode replaces list as the primary visual;
- Bookmark/Pin;
- Import Manual Model;
- advanced Import Replacement Observations with the same validation/warnings;
- Branch From selected;
- Make Current.

### Show / Coot

Current CLI includes:

- show current;
- show last;
- show explicit stage;
- show explicit checkpoint without selection;
- Coot override.

GUI:

- one ubiquitous **Open in Coot** action on resolvable stages/checkpoints;
- viewed versus current stays separate;
- reuse/coordinate an existing NASolve-launched Coot session when possible;
- Topo selections may round-trip to the same Coot context.

## Extensibility: do not rebuild the GUI for every feature

The GUI shell should be **capability-driven**, not a pile of hard-coded buttons.

Backend features should expose descriptors that the shell can render in existing
places.

### Action registry

A backend action descriptor should be able to declare:

- stable action ID;
- label/icon;
- applicable scope/entity types;
- eligibility predicate and human-readable disabled reason;
- read-only versus state-changing;
- expected source/current semantics;
- simple/common parameters;
- advanced parameters;
- progress/log source;
- resulting artifact/node type;
- attention/warning semantics; and
- documentation/help target.

The Inspector renders applicable actions from this registry.

Adding a future stage/Doctor should normally add a descriptor/backend operation,
not require redesigning the main window.

### Inspector-section registry

Metadata providers should declare contextual Inspector sections for entity types.
Unknown/new metadata may still appear in a generic structured "Details" section
until a richer renderer exists.

### Workspace/view registry

Specialized views such as Topo Net register against applicable scopes/capabilities.
They reuse the Navigator, Inspector, Activity drawer, selection model and
checkpoint graph.

### Status/theme registry

Scientific statuses map to semantic tokens such as:

- neutral;
- active/current;
- success/accepted ancestry;
- attention/review;
- blocked/failure;
- skipped/not-applicable.

Views consume semantic tokens rather than choosing colors independently.

### Schema/version behavior

- GUI reads backend schema/version declarations.
- Unknown optional fields are preserved/ignored safely, not treated as corrupt.
- Unsupported required schema/capability produces a clear "backend/GUI update
  required" state.
- GUI never rewrites manifests merely to display them.
- CLI and GUI remain interoperable over the same artifacts.

## Search and command palette

A global search/command palette is useful for scalability without toolbar bloat.

It may search:

- campaigns/designs/datasets/runs;
- checkpoint IDs/bookmarks;
- model/provider names;
- attention states; and
- available backend actions.

Actions still obey the same eligibility rules as Inspector buttons.

Keyboard shortcuts should supplement, not replace, visible discoverable actions.

## Modals and confirmations

Avoid routine modal dialogs.

Every interactive CLI prompt must have a GUI-equivalent choice with the same
meaning. A terminal `y/n` prompt normally becomes two explicit actions/buttons;
an inspect prompt becomes an Open in Coot/Inspect action; a Doctor selection
prompt becomes a candidate-selection action in the model tree/Inspector. GUI
defaults must match CLI/backend defaults and must never silently answer a prompt
on the user's behalf.

Use inline Inspector/action-popover confirmation for ordinary branching actions.
Reserve blocking confirmation for genuinely dangerous/irreversible external
operations. NASolve's internal immutable branching should make most scientific
operations reversible by traversal rather than confirmation-heavy.

## Topology-informed workspace

Topo Net is an opt-in specialized workspace inside this shell.

It reuses:

- scientific Navigator;
- generic checkpoint/model tree;
- pinned Compare panels;
- Inspector/actions;
- Activity drawer;
- Needs Attention;
- semantic colors/status;
- Coot bridge.

Topo-specific content adds the periodic molecular graph, tile/junction/repeat
semantics, surgery preview and local geometry diagnostics. It does not create a
separate application or history system.

## Design-level campaign grouping

The GUI should be ready for an optional Design layer before the campaign backend
fully implements it.

A design may own shared metadata such as:

- full input strand sheet and stoichiometry;
- tile/junction/repeat declarations;
- model-provider intent;
- sample/design notes;
- multiple datasets/collections derived from the same construct.

The GUI may render design grouping only when the backend supplies stable design
identity. It must not infer that two datasets share a design merely from similar
filenames or sequences.

## Human validation

The minimum human validation queue for the GUI shell is maintained in
[`gui-live-checks.md`](gui-live-checks.md). It covers navigation, current versus
viewed state, color/accessibility semantics, long lineage trees, campaign/design
scope switching, CLI/GUI interoperability, capability-driven extensibility, the
Coot bridge and long-running activity handling.

## Human-facing invariants

User-facing feature names should describe scientific capability rather than
internal implementation generations. In particular, the registration preflight
feature is displayed simply as **Scout**. Internal developer/machine provenance
may retain `Scout v1` / `Scout v2` where needed to distinguish historical
implementations.

1. One main NASolve window.
2. Coot is the intentional external atomic viewer/editor.
3. Clicking/viewing never changes the current scientific pointer.
4. State-changing actions create/reuse backend provenance, never GUI-only state.
5. Current lineage, alternative branches and attention states are visible.
6. Color always has a redundant non-color encoding.
7. High-detail provenance/logs use progressive disclosure.
8. New features should register actions/metadata/views into the shell rather than
   requiring a new standalone window.
9. CLI remains a complete interoperable control surface.
10. GUI state must never become the only copy of scientific intent or history.
11. Conditional/skipped stages and future workflow-recipe endpoints are rendered
    from authoritative backend records; the GUI never infers a stronger
    scientific requirement from stage order alone.
12. The visual recipe builder exposes only backend-supported/validated options
    and serializes the same workflow recipe consumed by CLI execution.
13. Every interactive CLI decision has a GUI-equivalent action with the same
    default, eligibility, provenance and scientific consequence.
