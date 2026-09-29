# Plan a campaign before running structures

Campaign planning is the first implemented part of the
[campaign roadmap](campaigns.md). It validates project policy, inventories a
fixed set of datasets, resolves their requested ligands and search models, and
records checksums. It does not run scientific stages or create solution or
approval decisions.

## Quick check using the published inputs

From a NASolve source checkout with its dependencies installed:

```bash
./nasolve preset check 5w6w
./nasolve campaign plan examples --dataset DOHU --dataset QiC_120325_0513
./nasolve campaign status examples
```

The plan is created at `examples/NASolveCampaign/plan.json`. These commands do
not rerun Phaser, Coot, ReadySet, AutoSol, or AutoRefine, and they do not change
the active workspace, existing `nasolve.txt` files, numbered runs, or current
checkpoints. A second `plan` command refuses to replace the saved plan; use
`status` to inspect it.

An installed copy without a discoverable model catalogue needs the explicit
catalogue root:

```bash
nasolve campaign plan /path/to/campaign --frames-dir /path/to/MR_frames
```

The planner uses the existing NASolve catalogue-selection rules. It deliberately
ignores the machine-local `NASOLVE_MR_FRAMES` environment setting so the
catalogue choice is either explicit or the installed/checkout default. An
invalid explicit directory produces an error rather than selecting a fallback
directory on the machine.

## Dataset selection

A campaign root is an existing directory whose immediate subdirectories hold
the datasets. Running `campaign plan ROOT` discovers children containing any
of the normal input markers: MTZ, `Data_1*.cif`, `summary.html`, or
`nasolve.txt`. An incomplete candidate is retained as `BLOCKED` with its reason;
it does not prevent valid datasets from being recorded.

Selection is sorted and shallow. Existing stage directories, environment
directories and symbolic-link directories do not become datasets. Repeat
`--dataset NAME` to select exact direct children rather than discovering the
whole root. The names must stay within that root.

Dataset discovery currently reuses the ordinary AutoMR rules: one authoritative
MTZ, one `Data_1*.cif` processing-metadata file, and one `summary.html`.
This is the **current AutoPROC/STARANISO input profile**, not the intended
universal campaign format. New campaign plans use **schema 2** and support both
the existing standard W/5W6W route and a deliberately conservative
prepared-nonstandard route. Existing schema-1 W plans remain readable and
executable without migration.

### Future reflection-input compatibility profiles

Campaign setup should separate **what crystallographic work the available input
can support** from **which processing package produced it**.

The intended capability ladder is:

1. **MR-ready** — a reflection dataset contains enough validated cell/symmetry
   and observation information for molecular replacement.
2. **Refinement-ready** — MR-ready plus a stable refinement observation array
   and an authoritative Free-R set. NASolve must not silently regenerate Free-R
   flags merely because a generic input omitted them; any future one-time
   Free-R creation policy must be explicit, frozen and separately validated.
3. **Anomalous-ready** — refinement-ready plus the anomalous arrays and
   wavelength/element context required for the guarded AutoSol/anomalous path.
4. **Deposition-ready** — the solved/refined dataset also has the processing,
   collection and experiment metadata required for deposition/reporting. Missing
   deposition metadata should lock deposition/curation features rather than
   preventing otherwise valid MR/refinement work.

The first compatibility expansion should be **generic MTZ input**: allow an MTZ
whose contents satisfy the relevant capability gates without requiring
AutoPROC-specific companion filenames. A later **SCA/Scalepack import adapter**
may convert a validated SCA reflection file into a frozen downstream MTZ plus
explicit provenance; SCA is not a current runtime input.

The GUI/campaign planner should therefore report capability badges and missing
requirements (for example `MR READY`, `REFINEMENT BLOCKED: no Free-R set`,
`DEPOSITION LOCKED: processing metadata incomplete`) instead of treating
absence of AutoPROC/STARANISO files as a universal dataset failure.

For standard W datasets, catalogue selection remains the default and a dataset
may explicitly force one PDB from its own directory or the selected frame
catalogue.

For a prepared nonstandard dataset, `nasolve.txt` must explicitly set
`mode = nonstandard`. Planning then accepts either one named dataset-relative
PDB or exactly one discovered top-level PDB. The dataset must also supply an
explicit complete chain-labelled target, either inline under `[sequences]` or
through `[automr] sequence_file`. Planning freezes:

- the exact model bytes/checksum and provider provenance;
- the exact raw sequence-source bytes/checksum;
- the parsed effective chain-labelled sequence target; and
- the ordinary observations/metadata/configuration provenance.

The raw model/sequence source may later disappear without changing the frozen
campaign authority. Nonstandard datasets do not inherit the W frame/pair,
W sequence-thread overlays, or the W recipe's D:1 terminal-phosphate intent.
Nontrivial construct registration, split/recut chains, unexpected multiplicity
and topology remain inspection stops rather than inferred fixes.

3GBI campaign execution, shared/sibling model providers and automatic
cross-dataset model reuse remain later roadmap steps.

`DISCOVERED` means input and model selection succeeded. It does **not** assert
that the MTZ contains usable arrays, symmetry agrees, the model passes its full
assessment, a mutation can be constructed, or a structure is solved. Those
remain the existing scientific stage gates.

## Presets and precedence

The built-in `5w6w` TOML preset is versioned separately from the preset schema.
It records the current W-frame policy and five-cycle default refinement
recipe. A local preset can be validated before planning:

```bash
nasolve preset check /path/to/project/preset.toml --json
nasolve campaign plan /path/to/campaign --preset /path/to/project/preset.toml
```

The loader rejects unsupported schema versions, unknown settings, wrong types,
unsupported policies and unsafe resource paths. Optional named resources are
relative to the preset directory and must resolve within it. Presets contain
typed settings; they cannot supply shell commands.

For standard W members, precedence is NASolve defaults, then preset, then
explicitly supplied `nasolve.txt` values. An explicitly written `false`
overrides a preset's `true`; an omitted value inherits the preset. Sequences
and explicit mutations use the existing dataset intent parser. An explicit
dataset `[automr] sequence_reference` is also resolved during planning. Its
selector remains visible in the effective configuration while the exact
reference bytes are copied into the campaign resource store.

An explicitly nonstandard dataset is different: its own model/sequence request
is authoritative, so W-specific AutoMR defaults from the selected preset are
not applied. The preset still supplies the bounded shared stage policy
(PostMR/AutoSol/AutoRefine settings). For a geometry-diverse real campaign, a
small project-local preset with a neutral project ID is preferable to displaying
the built-in `5w6w` name even though the nonstandard datasets would not inherit
W chemistry. The resolved configuration is stored per dataset while the
original input file is preserved.

Current preset schema 1 freezes the conditional AutoSol policy and AutoRefine
recipe/cycle count, but it does **not** yet declare the campaign workflow
endpoint/transition graph itself. Today a plain `campaign run ROOT` uses the
executor's fixed stage order and defaults through AutoRefine; `--through` is an
explicit stop boundary.

A future preset/workflow schema should freeze the intended endpoint and
conditional transitions as versioned recipe data so the same one-command
unattended behavior is project-declared rather than executor-implicit. One
important optional policy is conceptually **"apply Doctor as needed"**. The exact
field name is intentionally deferred. Absence means an eligible review stops for
inspection; enabling it authorizes only the specific bounded Doctor transitions
that the installed backend exposes and the recipe validates. It is not blanket
permission for arbitrary recovery search or automatic checkpoint selection.

The future GUI recipe builder must construct this same backend recipe, not a
parallel GUI configuration. It may show sensible defaults and only currently
supported/validated options; unavailable future capabilities stay absent or
clearly disabled rather than being simulated in UI state.

### Prepared nonstandard providers

A first-slice nonstandard member may use:

```ini
[automr]
mode = nonstandard
model = models/search.pdb
sequence_file = construct.fasta
model_family = triangle-v1
```

or omit `model =` when exactly one top-level PDB exists. The optional
`model_family` is explicit provenance only; it does not authorize sibling
reuse or Campaign Doctor rescue.

The sequence file may be chain-labelled FASTA or `CHAIN = SEQUENCE` text.
Inline `[sequences]` is also accepted. Planning rejects a nonstandard member
without a complete explicit target, and currently rejects W-family sequence
threads on nonstandard members.

The frozen effective target is the parsed chain map. The frozen raw sequence
source remains separate provenance so later code can verify what user input
produced that target without reparsing an unfrozen file.

### Explicit standard-model providers

A standard W dataset may set `[automr] model = NAME.pdb`. The selector is
resolved only from the dataset directory and selected W catalogue. If both
contain that selector, planning stops rather than choosing one. Absolute,
escaping and non-PDB selectors are rejected.

The frozen effective configuration records a structured provider:

```json
{
  "kind": "explicit-standard-model",
  "selection": "user-forced",
  "frame": "W",
  "location": "dataset",
  "selector": "alternate.pdb"
}
```

This changes only the coordinates offered to Phaser. The W pair target, recipe
chemistry, symmetry gate, sequence reference/thread overlays and PostMR rules
remain independent. A forced filename is not parsed as evidence that its
standard pair matches the requested pair.

A dataset may additionally bind a stable family identifier to that explicit
model:

```ini
[automr]
model = alternate.pdb
model_family = w-metal-scaffold
```

The family is frozen with the provider and survives campaign relocation. It is
not inherited from a sequence thread or W-frame membership, and a campaign
plan is rejected if a re-signed provider/family record disagrees with its
effective configuration.

The exact selected PDB is copied into `NASolveCampaign/resources/`. Execution
therefore uses the frozen model after relocation even if the source PDB or
original frame catalogue has disappeared. The W frame sequence resource is
frozen separately so a dataset-supplied model cannot silently replace frame
context with a neighboring `seq_base.txt`.

Campaign preflight then runs ordinary AutoMR from these frozen selections. Every
fresh campaign AutoMR run therefore receives the same
`Model/model_compatibility_facts.json` fact sheet as a standalone run. Its
provider, frame, target, chemistry and symmetry facts come from the frozen
campaign selection and run preflights; execution does not rediscover the source
catalogue or infer sibling-model eligibility. The fact sheet contains no score
or reuse decision.

### Explicit sequence threads

A campaign root may optionally contain `nasolve-campaign.toml` with explicit
sequence-family membership. Schema 1 currently supports named W-family threads
using the reviewed `w-metal-scaffold` reference:

```toml
schema_version = 1

[sequence_threads.w-family]
datasets = ["sample_A", "sample_B"]
sequence_reference = "w-metal-scaffold"

[sequence_threads.w-family.sequences]
B = "CCCCCCC"

[sequence_threads.w-family.site_codes]
"A:13" = "1AP"
```

A dataset may belong to at most one sequence thread. Thread values affect only
the intended residue target. They do not change search-model selection, symmetry,
copy number, or cross-dataset model eligibility.

Target precedence is: family reference, thread sequence, dataset sequence,
thread site chemistry, then dataset site chemistry. More specific dataset
declarations therefore override inherited thread values. The normalized thread
definition and exact root declaration bytes are frozen into the campaign plan;
the run freezes only the thread ID and overlays actually applied to that dataset.

Recipe cards may explicitly declare terminal phosphates:

```toml
[chemistry]
terminal_phosphate_sites = ["D:1"]
```

The built-in `5w6w` card version 1.1.0 declares D:1 as part of the designed W
motif, following Simon's explicit confirmation. A custom card must declare its
own list; omission does not authorize any sites. Booleans, broad selectors,
malformed sites and duplicate sites are rejected. The dataset
`[automr] allow_op3_sites` overrides the complete card list, even when explicitly
empty. No option bypasses connectivity checks or constructs a missing phosphate.

Each dataset freezes the effective sites and their origin (`recipe` or explicit
`dataset` override), with recipe id, version and hashes. Plan/status prints
these beside the dataset. Workers use the frozen list after relocation without
reloading today's recipe or catalogue. Old plans do not acquire new permission
merely because the installed built-in card changed.

The campaign executor consumes these frozen declarations. Standalone `-W` /
`frame = W` uses the same **built-in** recipe chemistry, but never an active
campaign's custom preset. Planning does not alter another command's arguments,
source input, stage settings, or existing run.

## Frozen inputs and portable resources

The manifest records input paths, file sizes and SHA-256 checksums, the resolved
preset and its identity, selected models and sequence resources, duplicate
observation groups, and dataset diagnostics. References are anchored to the
campaign root. Selected models (including explicit provider overrides), explicit sequence-family references, the preset
source and declared preset resources are copied into
`NASolveCampaign/resources/`; they remain available after the source catalogue,
dataset-relative reference file, installed reference, or custom preset is
removed.

The large dataset inputs remain in their existing directories. Freezing records
their identities and checksums; it does not make another copy of every MTZ or
prevent a user editing a file. `campaign status` verifies the frozen references
and reports changed, missing, or unsafe inputs as `DRIFT`.

Move or copy the **whole campaign root**, including dataset inputs and
`NASolveCampaign/`, to preserve these relative references. A status check does
not need the old absolute location, source preset, source catalogue, or original
sequence-reference file. Campaign preflight copies the checksummed reference
resource into its immutable attempt tree and ordinary AutoMR then freezes those
same bytes into the numbered run's sequence-family contract.

Identical authoritative MTZ bytes are reported as duplicates. The datasets stay
separate because different intended chemistry can remain a meaningful reason
to evaluate the same measurements differently.

New directories added after planning are not silently admitted. Changes that
make a planned dataset's input selection ambiguous, or change the presence of
its configuration, are also integrity concerns. There is no automatic refresh,
repair, or overwrite. A future explicit revision command will manage changes
to an existing plan.

The plan is published only after its resource snapshots are complete. If a
process is interrupted before publication, an incomplete `NASolveCampaign/`
directory may remain. Keep it for inspection; another plan invocation refuses
to overwrite it.

## Status and automation

```bash
nasolve campaign status /path/to/campaign
nasolve campaign status /path/to/campaign --json
```

Status is read-only. The frozen dataset state and the current integrity result
are separate: fixing a blocked input does not silently rewrite the earlier
planning decision. After execution begins, status also reports each dataset's
current attempt, exact run, next stage, checkpoint and diagnostic from the
separate execution record.

| Exit code | Meaning |
| --- | --- |
| `0` | Preset check passed, or all planned datasets were discovered and integrity checks passed where performed |
| `2` | Invalid command/preset/manifest, unavailable campaign, or failed plan publication |
| `3` | Plan/status includes blocked datasets, detected input/resource drift, or execution outcomes needing inspection |

The JSON output includes full diagnostics and checksums. Planning checks only
the stages described above; successful planning does not replace `nasolve check`
or the numerical and structural acceptance gates.

## Execute the saved plan

The [campaign executor](campaign-execution.md) composes one frozen candidate
per dataset using the existing scientific stages. Schema-2 plans may mix
standard W and prepared nonstandard members; existing schema-1 W plans remain
compatible and need no regeneration. Durable execution progress is stored
separately from the immutable plan. Automatic Doctor selection, approval,
reporting PDFs and deposition remain later work.
