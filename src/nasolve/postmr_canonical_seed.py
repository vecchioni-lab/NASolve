"""Explicit canonical base seeds that retain a modified model's DNA scaffold.

This is coordinate construction, not dictionary qualification or refinement.
The caller supplies both chemical authorities and persists any returned output.
No native process, mutation alias, phosphate inference or fallback runs here.
"""
from hashlib import sha256
from math import atan2, degrees, dist, sqrt
from pathlib import Path
import re

from .cif_stereochemistry_audit import _values, _coordinates, _volume
from .postmr_conformation import (
    _PARENT_ROLES, MATCH_TOLERANCE_DEGREES, parent_conformation_plan,
)
from .postmr_restoration import (
    _atom_records, _frame, _dot, _sub, _cross, source_graph_fragment,
)

POLICY_ID = 'postmr-explicit-canonical-base-seed-v1'


def _chi(xyz, names):
    a, b, c, d = [xyz[n] for n in names]
    axis = _sub(c, b)
    length = sqrt(_dot(axis, axis))
    if length < .5:
        raise ValueError('Degenerate glycosidic axis')
    axis = [v / length for v in axis]
    vectors = [_sub(a, b), _sub(d, c)]
    v, w = [[x - _dot(p, axis) * y for x, y in zip(p, axis)] for p in vectors]
    if min(_dot(v, v), _dot(w, w)) < .01:
        raise ValueError('Degenerate glycosidic torsion frame')
    return degrees(atan2(_dot(_cross(axis, v), w), _dot(v, w)))


def _template_coordinates(dictionary, component, graph):
    values = _values(dictionary, component)
    a = '_chem_comp_atom.'
    families = [[a + x for x in 'xyz'],
                [a + 'pdbx_model_cartn_' + x + '_ideal' for x in 'xyz'],
                [a + 'model_cartn_' + x for x in 'xyz']]
    for keys in families:
        if any(k in values for k in keys):
            if not all(k in values for k in keys):
                raise ValueError('Incomplete preferred canonical coordinate family')
            break
    family, xyz = _coordinates(values, source=False)
    if not set(graph['elements']) <= xyz.keys():
        raise ValueError('Require complete finite canonical heavy-atom coordinates')
    return family, xyz


def _model_records(data, site, component):
    match = re.fullmatch(r'([^\s:]):(-?[0-9]+)', site) if isinstance(site, str) else None
    if match is None:
        raise ValueError('Require one explicit PDB chain and integer residue site')
    chain, number = match[1], int(match[2])
    lines = data.decode('ascii').splitlines(keepends=True)
    indices, serials = [], set()
    for i, line in enumerate(lines):
        kind = line[:6].strip()
        if kind in {'MODEL', 'ENDMDL', 'CONECT', 'ANISOU', 'SIGATM', 'SIGUIJ'}:
            raise ValueError('Model/atom-reference records require a separate construction owner')
        if kind not in {'ATOM', 'HETATM', 'TER'}:
            continue
        if kind == 'TER' and not line[6:].strip():
            continue
        field = line[6:11].strip()
        if not field.isascii() or not field.isdecimal() or not 0 < int(field) <= 99999:
            raise ValueError('Require positive decimal PDB atom/TER serials')
        serial = int(field)
        if serial in serials:
            raise ValueError('Duplicate PDB atom/TER serial')
        serials.add(serial)
        if kind == 'TER' and len(line.rstrip()) < 26:
            continue
        try:
            residue = int(line[22:26])
        except ValueError as exc:
            raise ValueError('Malformed PDB residue number') from exc
        if line[21:22] == chain and residue == number:
            if line[26:27].strip():
                raise ValueError('Insertion-coded construction site is ambiguous')
            if line[17:20].strip() != component:
                raise ValueError('Selected atom/TER component differs from the declared source')
            indices.append(i)
    atoms = _atom_records([lines[i] for i in indices], component)
    return lines, indices, atoms, max(serials)


def _seed(data, site, source, code, template, parent):
    if parent not in _PARENT_ROLES:
        raise ValueError('Require an explicit supported canonical DNA parent')
    if not isinstance(code, str) or not re.fullmatch(r'[A-Z0-9]{1,3}', code):
        raise ValueError('Require a PDB-compatible source identity')
    graphs = [source_graph_fragment(p, c) for p, c in ((source, code), (template, parent))]
    for p, c in ((source, code), (template, parent)):
        plan = parent_conformation_plan(p, c, parent)
        if plan['status'] != 'MATCH_PARENT_CHI':
            raise ValueError(plan['reason'])
    before, canonical = graphs
    lines, indices, atoms, serial = _model_records(data, site, code)
    names = set(atoms)
    if (not set(before['sugar_atoms']) <= names or
            not set(before['fragment_atoms']) <= names or names - before['elements'].keys()):
        raise ValueError('Require complete source base/sugar and no unknown model atoms')
    phosphate = names & set(before['phosphate_atoms'])
    if phosphate and phosphate not in ({'P', 'OP1', 'OP2'}, {'P', 'OP1', 'OP2', 'OP3'}):
        raise ValueError('Incomplete or unsupported model phosphate atom set')
    if any(atoms[n]['element'] != before['elements'][n] for n in names):
        raise ValueError('Model elements differ from the source graph')
    family, xyz = _template_coordinates(template, parent, canonical)
    current = {n: a['xyz'] for n, a in atoms.items()}
    anchor, first, second = _PARENT_ROLES[parent]
    if atoms[anchor]['line'][78:80].strip():
        raise ValueError('Charged model attachment requires separate chemical qualification')
    hands = []
    for center, neighbors in [("C1'", ("C2'", anchor, "O4'")),
                              ("C3'", ("C2'", "C4'", "O3'")),
                              ("C4'", ("C3'", "C5'", "O4'"))]:
        model_volume, template_volume = [_volume(p, center, neighbors) for p in (current, xyz)]
        if min(abs(model_volume), abs(template_volume)) < .01 or model_volume * template_volume <= 0:
            raise ValueError('Degenerate or incompatible model/template sugar hand')
        hands.append(dict(center=center, ordered_neighbors=list(neighbors),
                          model_volume=model_volume, template_volume=template_volume))
    frame = [anchor, first, second]
    left, right = [_frame([p[n] for n in frame]) for p in (xyz, current)]
    rotation = [[sum(left[k][i] * right[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    determinant = _dot(rotation[0], _cross(rotation[1], rotation[2]))
    if abs(determinant - 1.) > 1e-10:
        raise ValueError('Require a proper canonical base rotation')
    moved = {}
    for name in canonical['fragment_atoms']:
        local = [_dot(_sub(xyz[name], xyz[anchor]), axis) for axis in left]
        moved[name] = tuple(round(current[anchor][i] + sum(local[j] * right[j][i] for j in range(3)), 3)
                            for i in range(3))
    fragment = sorted(moved)
    maximum = max(abs(dist(xyz[a], xyz[b]) - dist(moved[a], moved[b]))
                  for i, a in enumerate(fragment) for b in fragment[i+1:])
    if maximum > .002:
        raise ValueError('PDB serialization changed rigid canonical base distances')
    chi_names = ["O4'", "C1'", anchor, first]
    chi_before, chi_after = [_chi(p, chi_names) for p in (current, {**current, **moved})]
    difference = abs((chi_after - chi_before + 180.) % 360. - 180.)
    if difference > MATCH_TOLERANCE_DEGREES:
        raise ValueError('Canonical seed did not preserve the model glycosidic torsion')
    scaffold = names & set(before['scaffold_atoms'])
    scaffold_names = {atoms[n]['line'][12:16].strip() for n in scaffold}
    replacements = []
    for name in fragment:
        old = atoms.get(name)
        line = (old or atoms[anchor])['line']
        if name == anchor:
            replacements.append(line[:17] + f'{parent:>3}' + line[20:])
            continue
        if old is None:
            serial += 1
            if serial > 99999:
                raise ValueError('New atoms exceed decimal PDB serial capacity')
            line = line[:6] + f'{serial:5d}' + line[11:]
        fields = [f'{v:8.3f}' for v in moved[name]]
        if any(len(v) != 8 for v in fields) or not 1 <= len(name) <= 4:
            raise ValueError('Canonical atom exceeds PDB field width')
        atom_name = (' ' + name).ljust(4) if len(name) < 4 else name
        # Chemical identity/charge belongs to the new base, not the removed atom.
        suffix = '\r\n' if line.endswith('\r\n') else '\n'
        line = (line[:12] + atom_name + line[16:17] + f'{parent:>3}' + line[20:30] +
                ''.join(fields) + line[54:76].ljust(22) + f"{canonical['elements'][name]:>2}" + '  ' + suffix)
        replacements.append(line)
    selected = set(indices)
    emitted = False
    output = []
    for i, line in enumerate(lines):
        if i not in selected:
            output.append(line)
        elif line[:6].strip() == 'TER' or line[12:16].strip() in scaffold_names:
            output.append(line[:17] + f'{parent:>3}' + line[20:])
        elif not emitted:
            output.extend(replacements)
            emitted = True
    result = ''.join(output).encode('ascii')
    # Re-read serialized output through the same strict model boundary.
    _, _, actual, _ = _model_records(result, site, parent)
    if set(actual) != scaffold | set(fragment):
        raise ValueError('Canonical output atom inventory differs from construction')
    if any(actual[n]['xyz'] != current[n] for n in scaffold | {anchor}):
        raise ValueError('Canonical output changed protected scaffold/attachment coordinates')
    report = dict(schema_version=1, policy_id=POLICY_ID, status='CANONICAL_BASE_SEED',
                  site=site, source_component=code, canonical_component=parent,
                  source_sha256=before['source_sha256'], canonical_dictionary_sha256=canonical['source_sha256'],
                  input_model_sha256=sha256(data).hexdigest(), output_model_sha256=sha256(result).hexdigest(),
                  template_coordinate_family=family, frame_atoms=frame,
                  preserved_scaffold_atoms=sorted(scaffold), preserved_attachment_atom=anchor,
                  removed_base_atoms=sorted(set(before['fragment_atoms']) - set(fragment)),
                  added_base_atoms=sorted(set(fragment) - set(before['fragment_atoms'])),
                  rotation_determinant=determinant, maximum_template_pair_distance_change_A=maximum,
                  chi_before_degrees=chi_before, chi_after_degrees=chi_after, chi_difference_degrees=difference,
                  relative_sugar_hand=hands, absolute_cip_assignment='NOT_RUN',
                  native_qualification='NOT_RUN', automatic_adoption=False)
    return result, report


def canonical_parent_seed(model, site, source_dictionary, source_component,
                          canonical_dictionary, canonical_component):
    """Return model bytes and compact provenance from a model path or immutable bytes.

    Standard unbridged DNA, a shared N-glycosidic frame and matching model/template
    sugar hand are required. Preserve the incoming sugar, phosphate atom set and
    glycosidic anchor exactly. Place the complete explicit canonical base rigidly;
    unrelated records stay byte-identical. This does not certify either supplied
    dictionary, assign absolute stereochemistry or choose a chemical end state.
    """
    sources = [Path(source_dictionary), Path(canonical_dictionary)]
    paths = sources if isinstance(model, bytes) else [Path(model), *sources]
    originals = [p.read_bytes() for p in paths]
    data = model if isinstance(model, bytes) else originals[0]
    try:
        return _seed(data, site, sources[0], source_component, sources[1], canonical_component)
    finally:
        if any(p.read_bytes() != original for p, original in zip(paths, originals)):
            raise ValueError('Canonical seed input changed during construction')
