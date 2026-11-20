# Collaboration, workspaces, and portable results

NASolve separates machine-local convenience state from reviewable
crystallographic artifacts.

## Documentation roles

The root `README.md` is the human-facing operating guide. `architecture.md` and
the active subsystem documents define durable behavior.
`development-handoff.md` records the current implementation/validation edge and
immediate next work. Superseded integration notes, validation diaries and old
handoffs live under `history/`; they are retained for debugging and provenance
but are not implementation instructions.

See [`docs/README.md`](README.md) for the complete documentation map.

## Development cadence

Keep completed patches pushed to their active feature branch after appropriate
validation. This does not imply merging other branches or rewriting remote
history. Check related branch interfaces and shared-file changes as work proceeds,
particularly Cedar; reconcile overlapping documentation and validate shared
behavior before integration. Distinguish a compatibility review from a tested
combined build.

Use focused regression tests for isolated behavior changes. Run the complete
suite when global/shared mechanics change, and verify installation after each
substantial code patch. Documentation-only changes need content/link checks.
Record what actually ran and what remains untested.

Maintain the existing human guides and agent-readable contracts together.
Consolidate stale guidance instead of creating repeated handoff files. Avoid
unused code, redundant tests and leftover task-owned scratch directories, while
preserving scientific evidence and other contributors' work. Raise evidence-based
objections to mistaken assumptions with a practical alternative.

## Lightweight science checkouts

After a substantial scientific work stretch or at a planned checkout, leave a
small human-readable visual record of the work. One table or figure with a short
explanation can be enough; a few files are usually sufficient. Negative,
ambiguous and diagnostic results belong in the trail as well as improvements.
This complements the current handoff and underlying evidence, rather than
creating another operational status ledger.

Use the shared local **`GitHub/ScienceCheckouts/`** folder alongside the project
repositories, with an **agent subfolder** and a fresh dated/topic directory:
`ScienceCheckouts/<agent>/<YYYY-MM-DD_topic>/`. Each collaborator owns their
subfolder. Keep previous published checkouts intact, link the latest one in the
handoff, and point the user directly to its opening report or figure. Keep the
common folder index small and preserve other collaborators' entries.

Show the scientific question, compared inputs or conditions, principal measured
effect, uncertainty and next boundary. Label units, refinement/freeze policies,
actual stopping state and whether a result is diagnostic or scientifically
accepted. Distinguish fixed or unmeasured f″/B/Q values from fitted measurements.
Use a compact provenance record or links to exact models, maps and source receipts;
verify references and available checksums. Keep map/model pairing explicit.

Reuse existing evidence unless further calculation is scientifically warranted.
Prefer links to large immutable artifacts over copied models, maps or run trees.
Reports remain local and potentially unpublished; preparing a checkout does not
authorize uploading or committing raw science. Rebase and verify links when
publishing a report in the shared folder. Small HTML/Markdown, images or tables
are suitable; use the PDF skill when PDF is useful, and inspect its rendered
pages. A PDF or polished layout is not required for every checkout.

### Visual inspection preference

For every newly generated ChimeraX script, use the user's shared defaults:
**grey background, silhouettes enabled, soft lighting, and thin nucleic-acid
ring fills**. Apply these explicitly
so the result does not depend on the viewer's previous session settings:

```python
from chimerax.core.commands import run
run(session, "set bgColor gray")
run(session, "graphics silhouettes true")
run(session, "lighting soft")
run(session, "style nucleic ringFill thin")
```

Apply the nucleic style after loading the models. A different ring-fill style is
allowed when it serves a clear scientific or readability purpose; state that reason.
Colors, other representations, framing and remaining presentation choices are task-specific.
Use these defaults for new or deliberately refreshed scripts; preserve immutable
historical evidence. The ChimeraX command for the requested soft graphics preset
is `lighting soft`. Rowan, Hazel and Linden share this presentation convention.

Use focused 2D density illustrations alongside the 3D inspector when they make
the scientific change clearer. The user particularly values a clean red/green
density slice with a phosphate's before/after positions. Keep the map stationary
when comparing positions, label source, units and normalization, and distinguish
model-assisted density from independent truth. Use restrained color and useful
depth cues rather than decoration. Show residual distortion and ambiguous results
as clearly as recovery; choose 2D for a local interaction and 3D for backbone motion.

## Command available from any directory

The tracked launcher can be linked into an existing `PATH` directory. From the
checkout root, if `$HOME/.local/bin` is already on `PATH`, run:

```bash
mkdir -p "$HOME/.local/bin"
ln -s "$PWD/nasolve" "$HOME/.local/bin/nasolve"
```

The command refuses to overwrite an existing path. Recreate the machine-local
link if the checkout moves. Without a link, use the launcher's absolute path or
run `./nasolve` from the checkout root. This tracked launcher is POSIX-only.
On Windows, use `.\.venv\Scripts\nasolve.exe`; if editable metadata is not
loading, set `$env:PYTHONPATH = (Join-Path $PWD "src")` in PowerShell and run
`.\.venv\Scripts\python.exe -m nasolve`.

## Active workspace

Remember a dataset or a specific run once:

```bash
nasolve workspace use /path/to/dataset
nasolve workspace use /path/to/dataset/AutoMR/run_004
nasolve workspace status
```

After selecting a run, these forms are equivalent to passing the run path:

```bash
nasolve postmr
nasolve autosol
nasolve autorefine
nasolve refine-doctor
nasolve checkpoints list
nasolve checkpoints use refine-001
nasolve show
```

Explicit paths always take precedence. Clear the pointer with:

```bash
nasolve workspace clear
```

A newly allocated standalone AutoMR run becomes active automatically. An
unambiguous **single-dataset `campaign run`** now also makes its verified,
viewable result the active run, so `nasolve show` can open the **current
checkpoint with no path**. A dataset-only workspace selection lets bare
`nasolve show` choose that dataset's latest numbered readable run. Explicit
run/`--checkpoint`/`--stage` requests remain authoritative. Multi-dataset
campaigns and `campaign run --no-activate` preserve the previous active run.
A blocked/unviewable campaign result cannot silently become the active view.
Passing an explicit one-off run to other stages does not by itself change the
saved selection; use `workspace use` when the switch should persist.

The pointer lives in the platform-specific NASolve user configuration. It is a
small JSON value, starts no process, duplicates no crystallographic files, and
uses no persistent RAM. A working directory consumes disk only when tools write
artifacts into it.

Workspace selection does not install an executable. The repository's tracked
`./nasolve` launcher uses that checkout's `.venv` and `src` tree directly, so it
works in a fresh terminal without activation. It also resolves symbolic links,
allowing collaborators to place a link in an existing `PATH` directory when
they want the shorter `nasolve` spelling from elsewhere. The link is
machine-local and should be recreated after moving the checkout.

## Why historical runs failed after cloning

Early reports recorded absolute paths such as
`/Users/collaborator/.../AutoMR/run_004/PostMR/Model/readyset_model.pdb`.
The file could be committed under the new checkout and still be rejected
because the old path no longer existed.

New checkpoint references identify both an anchor and a relative path:

```json
{
  "anchor": "run",
  "relative_path": "PostMR/Model/readyset_model.pdb",
  "sha256": "...",
  "size": 68187
}
```

Top-level observations use the `dataset` anchor. NASolve also rebases legacy
absolute references through the exact `AutoMR/run_NNN` or dataset suffix.
Both POSIX and Windows legacy path forms are understood. Current-checkout
matches take precedence over an old checkout that still exists; arbitrary
basename searches, ambiguous matches, and path escapes are rejected.

Checkpoint schema 2 distinguishes `relative_path` from legacy schema-1
absolute `path` values. NASolve reads schema 1 and migrates it on the next
checkpoint write. New AutoMR reports freeze the authoritative reflection
checksum and, when the selected standard-frame catalogue supplies
`seq_base.txt`, copy it into `Model/` with a portable, checksummed report
reference. Legacy frame runs resolve the exact declared frame directory without
requiring the historical pair-model filename to remain in the catalogue.
Legacy reports without a reflection checksum remain usable, but their root
checkpoint records `legacy-unverified` observation integrity when the registry
is first initialized.

## What to commit

A useful results-bearing commit should include everything needed to inspect or
continue the selected checkpoint:

- run and stage reports;
- frozen effective configuration and parameter files;
- the run-local standard-frame `Model/seq_base.txt` snapshot when present;
- dataset metadata and `summary.html` needed for review and conditional AutoSol;
- the authoritative observation MTZ;
- selected Phaser/PostMR/AutoSol HA/refined models;
- active restraint PHIL/EFF and ligand CIF files;
- checkpoint registry, metrics, and selected map/reflection outputs;
- concise diagnostic logs needed to explain a failure or decision.

Do not routinely commit Coot GUI state, backups, duplicate scratch products, or
every exploratory branch. Logs are ignored globally, so add a diagnostic log
with `git add -f PATH` only after reviewing it for unpublished or
machine-sensitive content.

Before committing a live run, inspect:

```bash
git status --short
git diff --stat
du -sh DATASET/AutoMR/run_NNN
```

Ordinary Git is adequate for the current small fixtures. Adopt Git LFS or
external/private artifact storage when repeated MTZ/map history materially
increases repository size. Do not introduce LFS attributes piecemeal: all
collaborators and CI must be able to hydrate the selected artifacts.

## AI-agent review record

Agents must follow the repository-root `AGENTS.md` and update
`CHANGELOG.md`. The pull-request template mirrors the required handoff so a
reviewer can distinguish source changes, portable artifacts, local-only state,
and remaining external-tool validation.
