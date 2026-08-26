# NASolve architecture

NASolve orchestrates external crystallographic programs; it does not reimplement them.

## Runtime precedence

Phenix is resolved in this order:

1. `--phenix-root`
2. `NASOLVE_PHENIX_ROOT`
3. saved user configuration
4. current `PATH`
5. validated installations in standard platform locations
6. a clear request to run `nasolve configure phenix PATH`

When multiple standard installations exist, NASolve selects the highest validated version.
An automatically discovered path is saved and revalidated on use. Each structure-solution report will record the exact
Phenix version and executable paths used.

## Planned pipeline gates

1. Validate dataset inputs.
2. Run Phaser in an isolated run directory without stripping heteroatoms from the search model.
3. Classify the best TFZ: `>= 8.0` pass; `7.0–7.99` review; `< 7.0` fail.
4. Pause for a mutation decision until scripted Coot mutation is restored.
5. Call NARestraints, ReadySet, and `phenix.refine` behind their own validation gates.
