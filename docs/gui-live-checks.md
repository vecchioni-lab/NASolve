# NASolve GUI human live-check queue

Status: **planned validation contract; GUI not yet implemented**.

These checks are for the future GUI shell itself. They do not replace unit tests
or the Construct Registration / Topo Net human checks.

Keep this list project/scenario-based and small enough to run before meaningful
GUI releases.

## Shell / navigation project

- **Open Root:** choose a campaign/project parent folder from a native folder
  selector; verify campaign/design/dataset/run hierarchy appears without changing
  scientific state.
- **Recent roots:** reopen a recent root and verify recent-root state is
  machine-local only.
- **Breadcrumb round trip:** navigate Campaign -> Design -> Dataset -> Run and
  back using breadcrumbs without changing the current checkpoint.
- **No floating NASolve windows:** routine metadata, actions, logs and comparisons
  remain within Navigator / Workspace / Inspector / Activity regions. Coot is
  the intentional external-window exception.
- **Pane persistence:** collapse/resize Navigator, Inspector and Activity drawer;
  reopen the GUI and verify only machine-local layout preferences persist.

## Current / viewed / pinned project

- **Inspect without select:** click historical checkpoints and open them in Coot;
  current backend pointer remains unchanged.
- **Make current:** explicitly select one eligible historical node; verify the
  backend audited selection changes and the GUI current marker updates.
- **Pinned comparison:** pin several nodes, navigate elsewhere, and verify pins
  remain comparison/navigation state only.
- **Focus versus status:** keyboard/mouse focus must never be visually confused
  with current, review, failure or success state.

## Color / accessibility project

- **Semantic node colors:** ordinary hollow neutral, current checkpoint blue,
  accepted ancestry green, review amber/yellow and blocked/failed red appear
  consistently in Tree, Campaign and Topology workspaces.
- **Successful lineage:** only the accepted/current ancestry path receives the
  stronger green edge; alternate branches remain visible but neutral.
- **No color-only state:** repeat the same inspection in grayscale/color-blind
  simulation and verify fill, shape, line style and badges still identify all
  states.
- **Dark/light contrast:** verify semantic tokens remain distinguishable in both
  themes without redefining their meaning.
- **Screenshot/print:** capture a tree without interactive hover and verify
  current/review/failed/ordinary states remain readable.

## Long-lineage project

- **Forty-refine chain:** load a run with dozens of sequential refinements;
  collapse/expand the chain without hiding branch points.
- **Mixed branches:** show ordinary AutoRefine, Doctor siblings, manual imports,
  topology surgery and a future re-MR branch in one graph.
- **Historical branch source:** start a new eligible branch from an older node
  without deleting descendants or silently changing unrelated lineage.
- **Pinned panels:** compare several important models while traversing elsewhere.

## Campaign / design project

- **Campaign scope:** campaign selection shows campaign progress/attention rather
  than one dataset's checkpoint tree.
- **Design scope:** a stable design containing several datasets shows those
  datasets and shared metadata; selecting one dataset switches the center to its
  lineage.
- **Ungrouped dataset:** a dataset without stable design identity remains usable
  without the GUI inventing a design.
- **Needs Attention:** filter a mixed campaign and verify only authoritative
  backend attention states appear.
- **Batch actions:** Run/Pause/Retry selected campaign datasets must retain
  backend dataset selection and stage-through semantics.

## CLI / GUI interoperability project

- **GUI after CLI change:** while GUI is open, create/select a checkpoint or
  change campaign state from CLI; GUI refreshes from authoritative artifacts
  without a private-state conflict.
- **CLI after GUI change:** perform a GUI state-changing action and verify CLI
  status/list commands see exactly the same result.
- **Unknown optional metadata:** add a newer optional artifact field and verify an
  older compatible GUI can still display the object safely.
- **Unsupported required schema:** verify the GUI reports an explicit
  backend/GUI compatibility requirement rather than rewriting or guessing.

## Existing CLI capability coverage project

Exercise at least one real workflow through each GUI surface:

- runtime check and Phenix/Coot configuration;
- workspace select/status/clear;
- preset validation;
- campaign plan/status/run/pause/retry;
- AutoMR preflight and execute;
- PostMR plus one review/advanced option;
- backbone review;
- conditional AutoSol;
- AutoRefine from current and historical checkpoint;
- Refine Doctor;
- checkpoint bookmark/manual import/select;
- Open in Coot for current, historical checkpoint and explicit stage.

The pass condition is semantic parity with the backend/CLI, not pixel parity
with terminal output.

## Extensibility project

- **Register one new backend action:** add a test/dummy future action descriptor
  with scope, eligibility, parameters, progress and result type. Verify it
  appears in the correct Inspector/command-palette context without editing the
  main layout.
- **Disabled reason:** make that action ineligible and verify the user sees a
  useful reason rather than a dead button.
- **New Inspector metadata section:** register one additional metadata provider
  and verify it appears contextually without changing the shell.
- **New specialized workspace:** register a test view for one capability/scope
  and verify it reuses Navigator, Inspector, Activity and selection semantics.
- **Status token reuse:** introduce no new hard-coded color; use the semantic
  theme/status registry.

## Coot bridge project

- **Open without selecting:** open historical model/maps in Coot without changing
  current.
- **Session reuse:** when supported, send a second selection/model context to the
  NASolve-launched Coot session without proliferating unnecessary Coot windows.
- **Topology round trip:** select a Topo residue/junction/seam and center the same
  atoms in Coot; return to NASolve with selection context intact.
- **Manual model return:** import a manually repaired Coot PDB as a new immutable
  review checkpoint while retaining its parent and failed automated attempts.

## Live tree / notification-stream project

- **Running node animation:** launch a campaign stage and verify the active
  dataset/node/edge shows restrained activity without changing its scientific
  status color prematurely.
- **Reduced motion:** disable animation and verify the same RUNNING state remains
  obvious through a static activity badge/ring.
- **Authoritative publication:** verify a completion/checkpoint node does not
  appear before the backend receipt/checkpoint record is published.
- **Live campaign updates:** run several sequential stages and verify Navigator,
  campaign workspace and dataset model tree update without manual reload.
- **External CLI update:** change campaign/checkpoint state from CLI while the GUI
  is open; verify the live tree and event stream reconcile from authoritative
  files.
- **Human event wording:** confirm representative events are intelligible without
  internal tokens, e.g. "refinement 21 passed", "PostMR needs your review", and
  "new retry attempt is ready".
- **Technical drill-down:** expand each human event and verify exact backend
  status, run/checkpoint ID, relevant metrics, raw diagnostic and artifact/log
  references remain accessible.
- **Event coalescing:** heartbeats/repeated RUNNING observations must not flood
  the stream; one stage-start and one terminal/review event are sufficient.
- **Attention semantics:** events requiring human action appear in both the
  notification filter and Needs Attention without creating a second state store.
- **Read/dismiss semantics:** marking an event read or clearing a GUI notification
  changes only machine-local UI state and never campaign/checkpoint provenance.

## Activity / process project

- **Progress:** long-running Phenix work reports progress/activity without
  blocking navigation/inspection.
- **Campaign pause:** GUI pause preserves the existing "after active stage"
  semantics rather than killing a scientific program mid-write.
- **Failure:** backend failure leaves logs/artifacts accessible and marks the
  appropriate node/attention state without losing previous checkpoints.
- **Close/reopen:** reopening the GUI reconstructs state from authoritative
  project artifacts rather than requiring an in-memory session history.

## Future metal-restraint builder checks

See [the builder contract](metal-restraint-builder.md). Once Simon supplies
examples: verify docked/small-window parity; clickable atoms/metals and visible
restraint overlays without coordinate movement; role-to-renamed-atom resolution;
save/load/reapply across supported bases; one-/two-metal and heterometal recipes;
and a separately launched refinement child receiving the exact emitted targets
and uncertainties. Confirm unresolved donor selection is local to that recipe,
not a global workflow veto. No GUI test is claimed run by this note.
