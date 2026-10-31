"""Explicit lossless heavy-PDB serialization before strict native readback.

This is not a restraint permutation comparator. Only atom order, decimal serials,
atom-name padding and TER/END formatting may differ. All scientific fields and
residue/chain boundaries must agree before the reference serialization is used.
Unsupported record families refuse; neither input is modified.
"""
from hashlib import sha256
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_dictionary_sites import _read, _need
from .cif_dictionary_store import _bytes, _json

POLICY_ID = 'cif-readyset-heavy-pdb-order-v1'
ANCHOR = 'readyset_atom_order_directory'
_FILES = ('reference.pdb', 'readyset.pdb', 'model.pdb')


def _parse(data):
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError as exc:
        raise ValueError('Require ASCII heavy PDB') from exc
    atoms = {}; serials = set(); layout = []; previous = None; seen = set(); ended = False
    for line in text.splitlines():
        _need(bool(line.strip()) and not ended, 'Blank or trailing PDB records are unsupported')
        kind = line[:6].strip()
        if kind in ('ATOM', 'HETATM'):
            _need(line[:6] in ('ATOM  ', 'HETATM') and 78 <= len(line) <= 80,
                'Require complete fixed-column atom record')
            line = line.ljust(80)
            _need(line[6:11].strip().isdigit(), 'Require decimal atom serial')
            serial = int(line[6:11]); _need(serial > 0 and serial not in serials, 'Duplicate atom serial')
            serials.add(serial)
            name = line[12:16].strip(); element = line[76:78].strip()
            _need(bool(name) and bool(element) and element.upper() not in ('H', 'D'), 'Require named heavy atom with explicit element')
            try:
                values = [float(line[a:b]) for a,b in ((30,38),(38,46),(46,54),(54,60),(60,66))]
            except ValueError as exc:
                raise ValueError('Invalid PDB numerical field') from exc
            _need(all(math.isfinite(v) for v in values), 'Nonfinite PDB numerical field')
            residue = line[17:27] + line[72:76]
            if residue != previous:
                _need(residue not in seen, 'Discontiguous residue or chain segment')
                seen.add(residue); layout.append(('residue', residue)); previous = residue
            key = (residue, line[16], name)
            _need(key not in atoms, 'Duplicate named atom identity')
            # Exact remaining columns include record type, altloc, coordinates,
            # occupancy, B, segment, element and formal charge. No numeric tolerance.
            atoms[key] = line[:6] + line[11:12] + name + '\0' + line[16:]
        elif kind == 'TER':
            _need(previous is not None, 'TER without a preceding residue')
            # A labelled TER must refer to the last residue. Its serial is display
            # metadata; unsupported extended fields are not discarded silently.
            padded = line.ljust(80)
            _need(not padded[27:].strip(), 'Unsupported extended TER fields')
            _need(not padded[17:27].strip() or padded[17:27] == previous[:10], 'TER residue differs')
            _need(not padded[6:17].strip() or padded[6:11].strip().isdigit()
                and not padded[11:17].strip(), 'Invalid TER serial')
            layout.append(('TER', previous)); previous = None
        elif kind == 'END':
            _need(not line[6:].strip(), 'Unsupported END fields'); layout.append(('END',)); ended = True
        elif kind in ('CRYST1','SCALE1','SCALE2','SCALE3','ORIGX1','ORIGX2','ORIGX3','TITLE','REMARK'):
            _need(not atoms, 'Header record inside atom body is unsupported')
            layout.append(('header', line.rstrip()))
        else:
            raise ValueError('Unsupported PDB record: '+kind)
    _need(bool(atoms) and ended, 'Require nonempty heavy PDB with END')
    return atoms, layout


def _derive(reference, candidate):
    before, layout = _parse(reference); after, other = _parse(candidate)
    _need(before == after, 'ReadySet scientific atom fields differ from reference')
    _need(layout == other, 'ReadySet residue boundaries or metadata differ')
    # Each candidate record has just been proven identical in all scientific
    # columns. Using the original serialization restores serials and padding too.
    return reference, len(before)


def _report(reference, candidate, model, count):
    refs = {name:dict(anchor=ANCHOR, path=name, size=len(data), sha256=sha256(data).hexdigest())
        for name,data in zip(_FILES,(reference,candidate,model))}
    return dict(schema_version=1, policy_id=POLICY_ID, artifacts=refs, atom_count=count,
        changed=candidate != model, scientific_fields_exact=True,
        native_execution='NOT_RUN', requires_final_native_readback=True, automatic_adoption=False)


def prepare_readyset_atom_order(reference, candidate, output):
    """Freeze a fresh lossless serialization; this alone never qualifies a model."""
    reference = Path(reference); candidate = Path(candidate); output = Path(output).absolute()
    a = _read(reference); b = _read(candidate); model, count = _derive(a,b)
    _need(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents)),
        'Require fresh regular atom-order directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = _report(a,b,model,count)
    with TemporaryDirectory(prefix='.readyset-order-',dir=output.parent) as temporary:
        root = Path(temporary)/'prepared'; root.mkdir()
        for name,data in zip(_FILES,(a,b,model)):(root/name).write_bytes(data)
        (root/'atom_order.json').write_bytes(_bytes(report))
        _need(_read(reference)==a and _read(candidate)==b, 'Atom-order inputs changed during preparation')
        _need(not output.exists() and not output.is_symlink(), 'Atom-order output was reserved concurrently')
        root.rename(output)
    return report


def read_readyset_atom_order(directory):
    """Reconstruct from frozen inputs and exact bytes; no native or host reads."""
    root = Path(directory).absolute(); saved = _json(_read(root/'atom_order.json'))
    _need({p.name for p in root.iterdir()} == {*_FILES,'atom_order.json'}, 'Unexpected atom-order artifacts')
    a,b,model = [_read(root/name) for name in _FILES]
    expected,count = _derive(a,b)
    _need(model==expected and _bytes(saved)==_bytes(_report(a,b,model,count)), 'Atom-order receipt does not replay')
    return dict(report=saved, model=root/'model.pdb', reference=root/'reference.pdb', candidate=root/'readyset.pdb')
