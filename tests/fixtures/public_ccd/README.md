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
