"""Bind an original coordinate mmCIF to an explicitly aliased working recut.

This reader preserves original double-precision values and document bytes. It
neither writes a model nor authenticates chemistry, annotation coverage or a
historical conversion merely because two coordinate inventories correspond.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from .topostitch_registration import _fingerprint
from .topostitch_transport import ReferenceFrame


@dataclass(frozen=True)
class CifRelabelSource:
    """Immutable original-order numerical input; absent U remains None.

    ``frame`` uses the original atom IDs and the original-source binding digest,
    not the working PDB receipt as a substitute for full-precision authority.
    ``observation`` returns a fresh descriptive dict, never workflow permission.
    """
    document_bytes: bytes
    atom_ids: tuple
    working_atom_indices: tuple
    positions_angstrom: tuple
    u_cart_angstrom_squared: tuple
    frame: ReferenceFrame
    _observation_json: str

    @property
    def observation(self):
        return json.loads(self._observation_json)


def _coordinate_block(data):
    import gemmi
    from .topostitch_scattering import _serialized_structure

    try:
        doc = gemmi.cif.read_string(data.decode('ascii'))
        coordinate = [b for b in doc if '_atom_site.' in b.get_mmcif_category_names()]
        if len(coordinate) != 1:
            raise ValueError('Require exactly one original coordinate CIF block')
        block = coordinate[0]; definitions = []; seen = set()
        for b in doc:
            if b.name == block.name:
                continue
            categories = b.get_mmcif_category_names()
            comp = b.get_mmcif_category('_chem_comp.').get('id', [])
            if (len(comp) != 1 or not isinstance(comp[0], str) or not comp[0]
                    or comp[0] in seen or not categories
                    or any(not c.startswith('_chem_comp') for c in categories)):
                raise ValueError('Extra CIF blocks must be unique attached component definitions')
            seen.add(comp[0])
            definitions.append(dict(block=b.name, component=comp[0], categories=categories))
        single = gemmi.cif.Document(); single.add_copied_block(block)
        # Reuse the maintained strict identity/element/ADP/model reader. Raw
        # numeric columns below, not float32 Atom U/B, own the original values.
        parsed = _serialized_structure(single.as_string().encode('ascii'), 'mmcif')
        return block, parsed, definitions
    except (RuntimeError, UnicodeError, OverflowError, TypeError) as exc:
        raise ValueError('Malformed original coordinate CIF') from exc


def load_relabel_cif_source(directory, model, *, expected_receipt_sha256,
        expected_model_sha256, component_aliases,
        max_coordinate_component_error_angstrom,
        max_u_component_error_angstrom_squared,
        max_b_error_angstrom_squared, max_occupancy_error):
    """Bind every original atom to one replayed working-PDB atom and image.

    Bounds must be explicitly supplied for the known working-file precision.
    They constrain a source/working compatibility check, not chemistry or source
    lineage proof. Identity, elements, charge, record type, crystal and ADP modes
    must agree exactly; only explicitly named component spellings may differ.
    No chain, atom-name, residue-number, missing-atom or refined-child guessing.
    Full document bytes, attached definitions and original numeric values survive
    in memory. Polymer and connection categories are inventoried, not validated.
    """
    from .topostitch_recut_bundle import (_FILES, load_relabel_preview,
                                          load_relabel_reference_frame)
    from .topostitch_scattering import _parsed_identity, _structure
    from .topostitch_preview import _atom_identity

    for value in (expected_receipt_sha256, expected_model_sha256):
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise ValueError('Require exact preview and original CIF SHA-256 bindings')
    bounds = dict(coordinate=max_coordinate_component_error_angstrom,
                  u_cart=max_u_component_error_angstrom_squared,
                  b_iso=max_b_error_angstrom_squared, occupancy=max_occupancy_error)
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
           for v in bounds.values()):
        raise ValueError('Require explicit finite nonnegative source precision bounds')
    if not isinstance(component_aliases, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) or k == v
            or not re.fullmatch(r'[A-Za-z0-9_+\-]{1,32}', k)
            or not re.fullmatch(r'[A-Za-z0-9_+\-]{1,3}', v)
            for k, v in component_aliases.items()):
        raise ValueError('Require explicit original-to-working component spelling aliases')
    aliases = dict(sorted(component_aliases.items()))
    root = Path(directory); model = Path(model); manifest = root/'preview.json'
    frozen = {p: p.read_bytes() for p in
              [manifest, *(root/n for n in _FILES.values()), model]}
    if (sha256(frozen[manifest]).hexdigest() != expected_receipt_sha256
            or sha256(frozen[model]).hexdigest() != expected_model_sha256):
        raise ValueError('Original CIF or saved preview differs from requested binding')
    packet = load_relabel_preview(root)
    working_frame = load_relabel_reference_frame(
        root, expected_receipt_sha256=expected_receipt_sha256)
    if _fingerprint(packet) != _fingerprint(json.loads(frozen[manifest])):
        raise ValueError('Saved preview changed before original CIF binding')
    block, original, definitions = _coordinate_block(frozen[model])
    working, working_atoms, _ = _structure(
        frozen[root/'source.pdb'], packet['observation']['source_orbit_observation'])
    if (original.cell.parameters != working.cell.parameters
            or original.find_spacegroup() is None or working.find_spacegroup() is None
            or original.find_spacegroup().hall != working.find_spacegroup().hall):
        raise ValueError('Original CIF crystal differs from the saved working crystal')
    import gemmi
    for category, field in (('_space_group_symop.', 'operation_xyz'),
                            ('_symmetry_equiv.', 'pos_as_xyz')):
        values = block.get_mmcif_category(category).get(field, [])
        if values:
            try:
                declared = [gemmi.Op(v).wrap().triplet() for v in values]
            except (RuntimeError, TypeError) as exc:
                raise ValueError('Invalid original CIF crystal operations') from exc
            expected = {op.wrap().triplet() for op in original.find_spacegroup().operations()}
            if len(set(declared)) != len(declared) or set(declared) != expected:
                raise ValueError('Original CIF crystal operations disagree with its space group')
    table = block.get_mmcif_category('_atom_site.')
    rows = [dict(zip(table, values)) for values in zip(*table.values())]
    atoms = list(original[0].all()); ids = tuple(row['id'] for row in rows)
    adp = block.get_mmcif_category('_atom_site_anisotrop.')
    adp_rows = {row['id']: row for row in
                (dict(zip(adp, values)) for values in zip(*adp.values()))}
    lookup = {_fingerprint(_parsed_identity(a)): i for i, a in enumerate(working_atoms)}
    pdb_lines = frozen[root/'source.pdb'].decode('ascii').splitlines()
    lines = [s for s in pdb_lines if s.startswith(('ATOM  ', 'HETATM'))]
    written_u = {_atom_identity(s): tuple(int(s[a:a+7])*1e-4
                 for a in (28,35,42,49,56,63)) for s in pdb_lines if s.startswith('ANISOU')}
    indices = []; positions = []; tensors = []; identities = []; used = set()
    maximum = dict.fromkeys(bounds, 0.)
    for atom, row in zip(atoms, rows):
        identity = _parsed_identity(atom); original_identity = dict(identity)
        comp = identity['residue_code']
        if comp in aliases:
            identity['residue_code'] = aliases[comp]; used.add(comp)
        key = _fingerprint(identity)
        if key not in lookup:
            raise ValueError('Original atom has no explicitly mapped working identity')
        index = lookup[key]; other = working_atoms[index]; indices.append(index)
        identities.append(original_identity)
        if (atom.residue.het_flag != other.residue.het_flag
                or atom.atom.element != other.atom.element or atom.atom.charge != other.atom.charge
                or atom.atom.aniso.nonzero() != other.atom.aniso.nonzero()):
            raise ValueError('Original record type, element, charge or ADP mode differs')
        xyz = tuple(float(row['Cartn_'+a]) for a in 'xyz')
        u = None
        if row['id'] in adp_rows:
            u = tuple(float(adp_rows[row['id']]['U'+s]) for s in
                      ('[1][1]', '[2][2]', '[3][3]', '[1][2]', '[1][3]', '[2][3]'))
        positions.append(xyz); tensors.append(u)
        # Compare to explicitly written PDB values, not Gemmi float32 U/B/Q.
        line = lines[index]
        errors = dict(coordinate=max(abs(a-b) for a,b in zip(xyz, other.atom.pos)),
                      b_iso=abs(float(row['B_iso_or_equiv'])-float(line[60:66])),
                      occupancy=abs(float(row['occupancy'])-float(line[54:60])), u_cart=0.)
        if u is not None:
            written = written_u[_atom_identity(line)]
            errors['u_cart'] = max(abs(a-b) for a,b in zip(u, written))
        for kind, error in errors.items():
            maximum[kind] = max(maximum[kind], error)
            if error > bounds[kind]:
                raise ValueError('Original-to-working '+kind+' exceeds declared precision')
    if (len(indices) != len(working_atoms) or len(set(indices)) != len(indices)
            or set(indices) != set(range(len(working_atoms))) or used != set(aliases)):
        raise ValueError('Require a complete atom bijection and only used component aliases')
    layouts = {}
    for item in block:
        tags = [item.pair[0]] if item.pair else list(item.loop.tags)
        for tag in tags:
            layouts.setdefault(tag.split('.')[0]+'.', set()).add('scalar' if item.pair else 'loop')
    observation = dict(schema_version=1, kind='topostitch-original-cif-source-binding',
        status='BOUND_REVIEW_REQUIRED', original_model_sha256=expected_model_sha256,
        preview_receipt_sha256=expected_receipt_sha256,
        working_model_sha256=packet['source_model_sha256'],
        coordinate_block=block.name, component_aliases=aliases, attached_components=definitions,
        atom_count=len(ids), source_atom_ids=list(ids), working_atom_indices=indices,
        original_identities=identities, anisotropic_atom_count=sum(u is not None for u in tensors),
        precision_bounds=bounds, maximum_working_precision_errors=maximum,
        coordinate_categories=[dict(name=c, rows=len(block.find_mmcif_category(c)),
            layout=next(iter(layouts[c])) if len(layouts[c]) == 1 else 'mixed')
            for c in block.get_mmcif_category_names()],
        original_document_retained=True, coordinates_written=False, runtime_authority=False,
        scientific_acceptance=False, annotation_coverage_validated=False,
        limitations=['Compatibility with an explicitly pinned original, not independent historical producer proof',
            'Aliases bind spelling only; original component identity and attached definitions are not rewritten',
            'No polymer/path/annotation validation, native interpretation, writer, edit import or changed-child rebase',
            'Original raw XYZ/U are doubles; working PDB rounding is not original-source authority'])
    binding = _fingerprint(observation); observation['report_sha256'] = binding
    labels = tuple(json.dumps(dict(atom_id=i, identity=a), sort_keys=True, separators=(',', ':'))
                   for i,a in zip(ids, identities))
    frame = ReferenceFrame(labels, tuple(working_frame.images[i] for i in indices), binding)
    if any(p.read_bytes() != data for p,data in frozen.items()):
        raise ValueError('Original CIF or saved packet changed during source binding')
    return CifRelabelSource(frozen[model], ids, tuple(indices), tuple(positions),
        tuple(tensors), frame, json.dumps(observation, sort_keys=True, allow_nan=False))
