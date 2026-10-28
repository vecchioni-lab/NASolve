# Historical C60 native-capture source

`cif_native_validation.py.txt` is source evidence, never imported or executed.
It preserves the module pinned by `cif_scaffold_return.C60_SOURCE_SHA256`:

- Source: `src/nasolve/cif_native_validation.py` at NASolve commit
  `60cdc0800b33669c9568e78277638aed4bbfe226`, still identical to the C60 pin.
- SHA-256: `a80014965b04e224f0ac9b62ed5065c090fb2814893ef823855ef982f4ee34ce`.

C112 changes the live capture API. Saved C60 replay tests must continue to
exercise the historical source bytes rather than pass the evolving module as
if it were historical evidence. The other five pinned modules are still read
from their unchanged maintained sources. The production pin and worker checks
remain unchanged. This fixture needs neither Git history nor native tools at
test time and contains no scientific data.
