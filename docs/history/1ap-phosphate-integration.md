> **Historical record — not an active implementation contract.**  
> Preserved for provenance, debugging, and understanding why earlier decisions were made. Commands, paths, test counts, branch names, and next-action sections below may be obsolete. Verify current behavior against active documentation and code before acting on this file.

# 1AP and explicit OP3 integration checkpoint

Implementation candidate, 2026-09-14. This supersedes older notes that
inferred terminal status automatically authorized OP3. No DE correction or
sulfur pair-target change is included. See the **2026-09-15 recipe addendum**
below: Simon explicitly confirmed the W motif's D:1 phosphate; selecting this
annotated recipe now supplies that site's consent before freezing.

## User contract

**Working models must not contain OP3/O3P unless explicitly requested by the
user for that site.** Existing coordinates, a component dictionary, a Coot or
ReadySet addition, and apparent terminal placement are not authorization.

Default input requires no new setting. To retain an already-defined, chemically
consistent 5-prime phosphate, use a comma-separated list in dataset `nasolve.txt`:

```ini
[automr]
mode = standard
frame = W
pair = E:D
allow_op3_sites = A:1, D:7
```

The sites above illustrate syntax, not a prescription for the ED dataset.
Sites must exist and have a valid unlinked phosphate with OP3. The request does
not manufacture missing atoms. A request for an internally linked phosphate,
ambiguous connectivity, a missing requested atom/site, a possible cyclic
phosphate or conflicting explicit bond stops preparation. `_` denotes a blank
PDB chain; insertion codes and negative residue numbers are supported. Broad
selectors and boolean permission switches are not accepted.

For a verified internal phosphate, OP3 is removed from a new working copy.
For an unrequested unlinked phosphate, preparation stops for chemistry review:
it does not remove an oxygen and call the incomplete phosphate valid. Raw
models and previous numbered runs remain unchanged. Unidentifiable/orphan OP3
also requires review rather than becoming a hidden exception.

Explicit requests are frozen into AutoMR's effective input and
`post_mr_plan.allow_op3_sites`, including campaign plans/execution. Existing
plans without this additive field imply no consent, not the former automatic
terminal exception. Presets cannot infer consent from coordinates. An explicit
`[chemistry] terminal_phosphate_sites` declaration on the selected recipe is now
supported as an auditable request; see the addendum. Existing frozen plans are
not reinterpreted under a newly installed recipe.

## Reviewed dictionary

The 1AP source is CCP4 MonomerLibrary `1/1AP.cif`, Git blob
`1be06d4bb0848891fd3e7dca22d217dd2ad1b69b`:
https://github.com/MonomerLibrary/monomers/blob/master/1/1AP.cif

The only chemical-library adaptation is `_chem_comp.group` from `NON-POLYMER`
to `DNA`, as used in Simon's successful interpretation tests. All numerical
restraint rows, atoms, energy types, chirality and plane definitions are
unchanged. A regression reconstructs the original library bytes (apart from
the two audit comments and the group adaptation) and verifies the Git blob
hash. Topology checks include C1'-N9 and forbid the spurious O4'-N1 connection
seen in the unsuccessful eLBOW attempt. Raw CCD-only definitions are rejected
for this reviewed profile because they lack parameterized refinement targets.

The complete monomer dictionary still contains OP3. That does not grant
permission to add it to coordinates. `ligand_profiles.write_linked_profile`
inspects each 1AP occurrence and applies `NASnoOP3` only where an incoming
O3'-P link is verified. Internally linked and explicitly phosphorylated
terminal instances of the same residue code therefore get different treatment.

The modification deletes OP3 from the selected monomer definition, not from
the source CIF or by a global residue-name rule. Its dependent restraints are
handled by Phenix's CIF modification machinery. It does not retarget base
pairing or change the sulfur-contact policy.

Phenix command-line reference for selected-residue CIF modifications:
https://www.phenix-online.org/documentation/reference/refinement.html
The production PHIL uses `refinement.pdb_interpretation.apply_cif_modification`;
standalone `pdb_interpretation` diagnostics need the corresponding top-level
`pdb_interpretation` scope, as in the original test.

## Propagation and precedence

PostMR now merges component-list blocks when preparing a combined ReadySet
input instead of blindly concatenating duplicate `data_comp_list` blocks.
Component numerical blocks are preserved. Unsupported/conflicting input
layouts stop rather than silently dropping a component.

For 1AP-profile runs, ReadySet output remains raw provenance. A separate
supplement excludes its 1AP definition; the reviewed run-local 1AP CIF wins.
Other generated components are retained. The OP3 modification CIF and its
site-selected PHIL are frozen along with the normal pair/stacking files in
`postmr.refinement_restraints`. Checkpoint creation must not let the generated
ReadySet CIF supersede this explicit list.

New additive PostMR fields:

- `phosphate_policy`: mode `op3-explicit-opt-in-v1`, explicit allowed sites;
- `linked_phosphate_profile`: schema 1, 1AP site inventory and selected
  modifications with incoming/outgoing partners;
- `refinement_restraints`: run-anchored SHA-256/size references for the exact
  operational restraint inputs;
- `view_dictionaries`: similarly frozen monomer files for Coot, excluding
  modification-only CIFs;
- `dictionary_precedence`: the reviewed-1AP policy and source dictionary refs.

Raw `readyset.generated_ligand_cif`, the older `restraints` list and the raw
model outputs remain available for provenance and legacy readers. New readers
use the explicit frozen list when present and fail on missing, modified or
malformed references instead of falling back. Later AutoRefine and Refine
Doctor checkpoints and manual children inherit the same selected artifacts.
Both sides of the profiled backbone are rechecked. A refined output that
reintroduces OP3 is failed and is not selected. Manual imports are checked
without editing the supplied model. Coot views use the reviewed dictionaries;
viewing old raw models is not a coordinate sanitizer.

NARestraints is pinned to merged stacking commit
`1f20e9f15074d15caa9691bd3d55956b50d86837` rather than the older `v1.1.1` tag.
The existing editable checkout does not require reinstalling. Fresh network
installs can retrieve that specific commit; the offline validation used the
uploaded editable NARestraints source and did not test a network install.

## Validation and provenance

Working source supplied by Simon:

- NASolve recorded HEAD: `589a08e83f528525502fa33f77323e5b492a0f13`;
- NARestraints recorded HEAD: `ff386d017c11a1c897e3013ea13cd35fce2b8445`;
- archive: `NASolve-1ap-source-20260914-171329.zip`.

The patch is against those working bytes, not a guessed GitHub snapshot.
The uploaded archive excluded NASolve experimental runs; all new workflow
fixtures use synthetic coordinates and fake external executables. No user
models, reflection files, maps, scientific runs, environments or old patches
are added to this change. NARestraints source/workbook and the DE dictionary
are unchanged.

The reproduced baseline was **414 tests + 145 subtests passed**. After the
integration, the complete NASolve suite returned **460 tests + 145 subtests
passed** (31.07 s). The unchanged NARestraints suite returned **25 passed**
(1.07 s), explicitly selecting its `tests/` directory. Validation ran on Linux
with Python 3.13.5 and pytest 9.0.2; the user's pre-change baseline ran on
macOS with the project's own Python environment. The package's non-test
example scripts were not used as test-discovery roots.

The exported patch was also applied to a clean copy of the uploaded baseline;
that patched copy returned **460 tests + 145 subtests passed** (30.96 s).
An offline wheel build succeeded. Inspection confirmed it includes the new
profile module, the byte-identical reviewed 1AP dictionary, and the exact
stacking dependency pin. All uploaded NARestraints files and NASolve's DE CIF
were compared byte-for-byte with the source archive and remain unchanged.

The new
`test_1ap_has_energy_types_and_numeric_bond_targets` failed against the old
CCD-only dictionary and passes with the replacement. Use:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q
```

Coverage includes explicit terminal consent, unrequested terminal failures,
internal/terminal instances of one code, aliases, insertion codes, malformed
requests, chain/TER ambiguity, cyclic-phosphate rejection, linked-site PHIL,
ReadySet reintroduction/precedence, frozen campaign intent, checkpoint
inheritance, manual imports, Doctor trials, dataset relocation with the old
location removed, and checksum corruption. Numerical outputs from fake
executables are fixtures, not crystallographic validation.

Simon's **prior real Phenix 2.2.1-6174** combined-input interpretation test:
17 fallback pairs, 36 native hydrogen-bond restraints, 72 hydrogen-bond angles,
17 native pair parallelities, 34 native stacking parallelities, and 7 custom
parallelities (3 manual pairs + 4 modified stacks). B4 received NASnoOP3 once;
all six chain-B links remained. No matching warning, unresolved-heavy-atom or
unknown-typing lines appeared in the filtered output. This evidence used the
old DE dictionary solely to isolate 1AP; it is not a completed refinement.
Local evidence was `full-restraints.fWZy2N/interpretation.log` under Simon's
Desktop audit directory, not a portable committed artifact.

## Remaining work / next action

The automated integration still needs a **live ReadySet -> full-input Phenix
interpretation/dry-run check on Simon's laptop**. The remote test environment
has no Phenix or Coot; their workflow calls were simulated. Keep the distinction
between the already-tested hand-written inputs and the new automatic pipeline.

An unphosphorylated 1AP terminus (no P/OP3) currently stops for a reviewed
terminal dictionary profile; this patch does not guess that profile or build
missing terminal phosphates. Automatic selected modifications are presently
reviewed for 1AP only, not generalized to every possible modified nucleotide.

DE remains defective, and its first replacement candidate remains unapproved.
Do not start a production ED refinement on the strength of this integration.
Replace DE with reviewed monomer geometry first, then compare a fresh ED
refinement with preserved Free-R assignments and explicitly measure the final
N6-S4 distance. The earlier 2.498 A value came from the prepared starting model,
not a demonstrated final refined measurement. Keep the 3.04 A / 0.2 A pair
restraint unchanged until that comparison supports a separate decision.

No commit, remote push, merge or numbered release is performed by applying
this patch. Review the changed files and local test result before publication.

## 2026-09-15 recipe addendum: W includes D:1

Simon explicitly confirmed that the W/5W6W design includes the chain-D
5-prime phosphate. The first new PostMR attempt stopped at D:1 because the
original integration correctly refused unrequested terminal OP3 but the recipe
had not yet declared this known chemistry. No terminal/geometry guard has been
disabled to accommodate it.

The source of this declaration is now `src/nasolve/data/presets/5w6w.toml`,
recipe version **1.1.0**, with `[chemistry] terminal_phosphate_sites = ["D:1"]`.
Choosing `-W`, `frame = W` or `frame = 5W6W` explicitly selects this recipe's
chemistry. Campaign planning uses the selected recipe card and freezes its
sites, id, version, frame and hashes in each effective configuration, then in
AutoMR's `post_mr_plan.phosphate_intent`. Workers consume that frozen record;
PostMR and later stages continue to use the existing `allow_op3_sites` contract.
AutoMR and campaign plan/status print the effective sites and origin.

Explicit dataset lists replace (not union with) the recipe list. An explicitly
empty `allow_op3_sites =` suppresses recipe permission for a variant, without
editing any atoms. Custom cards can declare exact site lists; an omitted
chemistry table authorizes no recipe sites. Nonstandard models and other frame
recipes do not acquire W's D:1 permission. Internal OP3 remains invalid even
when its site is requested; missing atoms, ambiguous links and unexpected other
terminal phosphates still require review.

### Validation / patch scope

Incremental patch against the already-applied 1AP integration supplied in this
conversation (the user's 460-test baseline), not against an unpatched checkout.
Changes affect input resolution, recipe-card loading, portable/frozen metadata,
CLI reporting and tests/documentation. No monomer dictionary, coordinates,
reflection data, Free-R assignments, refinement targets, NARestraints source or
workbook is changed. Existing small preflight fixtures now include the declared
D:1 inventory; intentionally phosphate-free pipeline fixtures explicitly opt
out. The new recipe tests do not replace the original phosphate guards.

`test_w_recipe_declares_d1_phosphate_before_postmr` was first run against the
pre-change implementation: it failed because the effective list was empty.
The modified NASolve suite returned **497 passed, 145 subtests passed** with
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q` (32.78 s; Linux,
Python 3.13.5, pytest 9.0.2). Coverage includes the actual six existing W model
inventories, frozen recipe provenance, independent dataset overrides including
empty, other frames/nonstandard models, an automatic synthetic W preflight ->
PostMR/ReadySet path, campaign reporting, relocation after removing the original
path, frozen execution without the live card, and malformed/corrupt declarations.
External executables are simulated; this is **not** a new Phenix/Coot execution.
The exported incremental patch was also applied after the prior integration to
an independent clean extraction of Simon's source archive: **497 passed,
145 subtests passed** (32.89 s). An offline wheel build passed and includes the
updated recipe card. The 1AP and DE dictionary bytes match the already-applied
integration baseline exactly.

### Resume safely on Simon's laptop

1. Apply the incremental W-recipe patch on `fix/1ap-linked-phosphate` over the
   existing uncommitted 1AP integration; run the full local suite again.
2. Keep failed `examples/TestSets/ED/AutoMR/run_002` intact. Its frozen intent
   does not declare D:1, and its partial PostMR directory must not be overwritten.
3. Allocate a fresh AutoMR attempt. Check its printed recipe source and D:1
   permission, then run PostMR on the exact new run directory. No manual
   modification of ED's existing `nasolve.txt` is required unless it has an
   explicit phosphate override.
4. Validate the new live ReadySet and full-input Phenix interpretation output
   before committing/pushing. DE remains defective: no production ED refinement
   is approved by this recipe change. Repair DE separately and retain the prior
   3.04 A / 0.2 A sulfur-contact target pending that review.

Old frozen campaigns are unchanged; installing this card is not a migration or
permission update. A retry of an old campaign consumes its old frozen selection.
Use a separately planned collection/fresh explicit attempt for new chemistry,
not an in-place edit of the old manifest. No remote push, merge or release has
been performed by this incremental patch.
