# Collaboration, workspaces, and portable results

NASolve separates machine-local convenience state from reviewable
crystallographic artifacts.

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

A newly allocated AutoMR run becomes active automatically. Passing an explicit
one-off run to a later stage does not change the saved selection; use
`workspace use` when the switch should persist.

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
