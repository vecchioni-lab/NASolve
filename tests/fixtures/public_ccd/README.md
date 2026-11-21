# Public CCD regression fixtures

`PDU.cif` is the unmodified wwPDB/RCSB Chemical Component Dictionary download
from https://files.rcsb.org/ligands/download/PDU.cif, retrieved 2026-10-19.
It is 9,033 bytes, SHA-256
`cd192f18964a28c628544ae1c0b4b1f2aed124e1b90a21b9c6ca0aa4458c0292`.
PDB archive data are provided under CC0 1.0; see
https://www.wwpdb.org/about/usage-policies.

The user requested this additional T-derivative test. It covers the complete
propynyl triple-bond graph, source hydrogen/formal-charge and sugar-stereo
state, CCD tag serialization and existing NARestraints role mappings. This
explicit public test fixture is separate from the original 18-control local
ZIP and is not installed into the production curated dictionary library.
No generated candidate, private crystal model, diffraction or native log is
included here. The provenance catalog is `docs/cif-doctor-ccd-controls.json`.
Git preserves the downloaded bytes, including line endings and trailing spaces,
through the scoped public-fixture rule in `.gitattributes`.

`5PC.cif` is the unmodified download from
https://files.rcsb.org/ligands/download/5PC.cif, retrieved 2026-10-20:
9,080 bytes, SHA-256
`cea88a7236f4775310e0d997a063c00c4dfc5982d89f1dc27c59593fb4c71650`.
The user requested this cytosine propynyl control to test the same triple-bond
auditor independently, with C7/C8 instead of PDU's C5A/C5B. Its graph passes;
the pinned NARestraints workbook has two matching 5PC records, so this slice
preserves the ambiguity and compiles no 5PC pair/stack policy. Both fixtures
are public graph/isolated-component controls, never scaffold insertions.

`PIM.cif` is the unmodified public download from
https://files.rcsb.org/ligands/download/PIM.cif, retrieved 2026-11-16:
5,750 bytes, SHA-256
`af049e7b0feb29f0e8f608498737eee68227786fac5bab0f764b64b792755e8e`.
This neutral phenyl-imidazole control declares inter-ring C5–C6 SINGLE and
aromatic Y. It tests a separate graph-based reader correction: qualified rings
may become aromatic, but their bridge stays single. Source bytes stay exact;
renamed/reordered controls exclude a PIM-name exception. This is an isolated
public control, not a curated production dictionary or experimental model.
