"""Read-only movement-region accounting from complete captured native restraints.

This consumer identifies protected flanks and crossing terms. It does not move
atoms, authenticate a capture, admit a native job or qualify chemical geometry.
The caller binds the native capture and explicit contexts to prepared sources.
"""
from copy import deepcopy
import re

from ..cif_captured_geometry import review_captured_geometry
from ..cif_linked_qualification import native_backbone_links
from .recipe import RecipeError, digest

PROTOCOL = 'metal-movement-scope-review-v1'
_SITE = re.compile(r'[A-Za-z0-9_]:-?[0-9]+')
_KINDS = {'bond_simple', 'bond_asu', 'angle', 'chirality', 'dihedral',
          'const_dihedral', 'planarity', 'parallelity'}


def _site(atom):
    identity = atom['identity']
    return (identity['chain_id'].strip() or '_') + ':' + identity['resseq'].strip() + identity['icode'].strip()


def _need(ok, message):
    if not ok:
        raise RecipeError(message)


def inspect_movement_scope(native, *, site_contexts, metal_labels):
    """Describe an explicit whole-residue/metal region, without coordinate changes.

    Each context has exactly ``site``, ``component``, ``incoming_site`` and
    ``outgoing_site``; missing termini are explicit None. Metal labels are exact
    labels from the same capture. The first scope supports one model, unambiguous
    heavy-atom selected residues and identity-symmetry terms touching the region.
    Residue numbers, distance searches and apparent metal contacts never infer
    polymer connectivity. The caller authenticates preparation and capture files.
    """
    try:
        return _inspect(native, site_contexts, metal_labels)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
        if isinstance(exc, RecipeError):
            raise
        raise RecipeError('Cannot inspect movement scope: ' + str(exc)) from exc


def _inspect(native, site_contexts, metal_labels):
    measured = review_captured_geometry(native)
    _need(native.get('fatal_problems') is None and not native.get('unused_definitions')
          and not native.get('unsupported_fields'), 'Require a complete interpretable native inventory')
    atoms = native['atoms']
    _need(len({a['identity']['model_id'].strip() for a in atoms}) == 1, 'Require one captured model')
    identities = [tuple(a['identity'][k].strip() for k in
                        ('model_id', 'chain_id', 'resseq', 'icode', 'altloc', 'resname')) + (a['atom_id'],)
                  for a in atoms]
    _need(len(identities) == len(set(identities)), 'Ambiguous captured atom identities')
    labels = {a['label']:a['i_seq'] for a in atoms}
    by_site = {}
    for atom in atoms:
        by_site.setdefault(_site(atom), []).append(atom)
    _need(isinstance(site_contexts, (list, tuple)) and 1 <= len(site_contexts) <= 256,
          'Require one to 256 explicit prepared site contexts')
    contexts = {}
    fields = {'site', 'component', 'incoming_site', 'outgoing_site'}
    for context in site_contexts:
        _need(isinstance(context, dict) and set(context) == fields, 'Require exact prepared context fields')
        site, component = context['site'], context['component']
        _need(isinstance(site, str) and _SITE.fullmatch(site) and site not in contexts,
              'Require unique unambiguous site declarations')
        _need(isinstance(component, str) and re.fullmatch(r'[A-Za-z0-9]{1,3}', component),
              'Require an explicit supported component identity')
        _need(site in by_site and all(a['identity']['resname'].strip() == component for a in by_site[site]),
              'Prepared site/component is missing or differs from capture: ' + site)
        for field in ('incoming_site', 'outgoing_site'):
            partner = context[field]
            _need(partner is None or isinstance(partner, str) and _SITE.fullmatch(partner)
                  and partner != site and partner in by_site, 'Missing or ambiguous declared polymer flank')
        contexts[site] = dict(context)
    for site, context in contexts.items():
        for direction, reverse in [('incoming_site', 'outgoing_site'), ('outgoing_site', 'incoming_site')]:
            partner = context[direction]
            _need(partner not in contexts or contexts[partner][reverse] == site,
                  'Selected site declarations are not reciprocal')

    _need(isinstance(metal_labels, (list, tuple)) and 1 <= len(metal_labels) <= 256
          and all(isinstance(label, str) and label in labels for label in metal_labels)
          and len(set(metal_labels)) == len(metal_labels), 'Require unique exact captured metal labels')
    residue_indices = {a['i_seq'] for site in contexts for a in by_site[site]}
    metal_indices = {labels[label] for label in metal_labels}
    _need(not residue_indices & metal_indices, 'Metal selection overlaps a whole selected residue')
    moving = residue_indices | metal_indices
    for index in moving:
        atom = atoms[index]
        _need(not atom['identity']['altloc'].strip() and not atom['identity']['icode'].strip()
              and atom['element'].strip().upper() not in {'H', 'D'},
              'Selected alternates, insertions or hydrogen-bearing movement need a separate policy')

    geometry = native['geometry']
    details, counts = geometry['proxy_details'], geometry['proxy_counts']
    _need(set(details) == set(counts) == _KINDS, 'Require complete supported native term families')
    term_counts, boundary, fixed_boundary = {}, {}, set()
    for kind, rows in details.items():
        _need(isinstance(rows, list) and type(counts[kind]) is int and counts[kind] == len(rows),
              'Native detail/count mismatch: ' + kind)
        totals = dict(internal=0, boundary=0, outside=0)
        crossing = []
        for number, row in enumerate(rows):
            indices = row['i_seqs']
            _need(isinstance(indices, list) and indices and all(type(i) is int and 0 <= i < len(atoms) for i in indices),
                  'Incomplete native term indices: ' + kind)
            _need(row['atoms'] == [atoms[i]['label'] for i in indices], 'Native term labels differ: ' + kind)
            if kind == 'parallelity':
                other = row['j_seqs']
                _need(isinstance(other, list) and other and all(type(i) is int and 0 <= i < len(atoms) for i in other),
                      'Incomplete second plane indices')
                _need(row['j_atoms'] == [atoms[i]['label'] for i in other], 'Native second plane labels differ')
                indices = indices + other
            selected = set(indices) & moving
            scope = 'outside' if not selected else 'internal' if set(indices) <= moving else 'boundary'
            totals[scope] += 1
            if selected:
                _need(kind != 'bond_asu' and (kind != 'bond_simple' or row.get('symmetry_operation') in (None, 'x,y,z')),
                      'Moving nonidentity-symmetry terms require a separate context')
            if scope == 'boundary':
                fixed = set(indices) - moving
                fixed_boundary.update(fixed)
                crossing.append(dict(proxy_index=number, moving_indices=sorted(selected),
                                     fixed_indices=sorted(fixed), proxy=deepcopy(row)))
        term_counts[kind], boundary[kind] = totals, crossing

    # Both representations must describe the same links. Do not hide a lost
    # cross-site term behind the complete intra-site scalar report.
    links = native_backbone_links(native)
    detail_links = native_backbone_links(dict(atoms=atoms, geometry=dict(simple_bonds=details['bond_simple'],
                                                                       asu_bonds=details['bond_asu'])))
    _need(links == detail_links, 'Native backbone inventories disagree')
    expected = set()
    for site, context in contexts.items():
        if context['incoming_site'] is not None:
            expected.add((context['incoming_site'], site))
        if context['outgoing_site'] is not None:
            expected.add((site, context['outgoing_site']))
    actual = {edge for edge in links if set(edge) & contexts.keys()}
    _need(expected == actual, 'Declared polymer junctions differ from captured native links')
    flanks = sorted({site for edge in expected for site in edge} - contexts.keys())
    junctions = []
    for left, right in sorted(expected):
        endpoints = [[a for a in by_site[site] if a['atom_id'] == name]
                     for site, name in ((left, "O3'"), (right, 'P'))]
        _need(all(len(rows) == 1 for rows in endpoints), 'Ambiguous polymer junction endpoint')
        endpoint_atoms = [rows[0] for rows in endpoints]
        _need(all(not a['identity']['altloc'].strip() and not a['identity']['icode'].strip()
                  for a in endpoint_atoms), 'Alternate polymer junction requires a separate context')
        edge = {a['i_seq'] for a in endpoint_atoms}
        matches = [row for row in measured['measurements']['bond_simple'] if set(row['i_seqs']) == edge]
        _need(len(matches) == 1 and matches[0]['status'] == 'MEASURED', 'Junction scalar measurement unavailable or duplicated')
        angles = [row for row in measured['measurements']['angle']
                  if edge in (set(row['i_seqs'][:2]), set(row['i_seqs'][1:]))]
        junctions.append(dict(sites=[left, right], scope='internal' if edge <= moving else 'boundary',
                              endpoints=[deepcopy(a) for a in endpoint_atoms],
                              bond=deepcopy(matches[0]), angles=deepcopy(angles)))

    result = dict(schema_version=1, protocol=PROTOCOL, status='MOVEMENT_SCOPE_REVIEW',
                  capture_fingerprint=digest(native), site_contexts=[contexts[k] for k in sorted(contexts)],
                  metal_labels=sorted(metal_labels), atom_count=len(atoms), moving_indices=sorted(moving),
                  moving_atoms=[deepcopy(atoms[i]) for i in sorted(moving)], fixed_atom_count=len(atoms)-len(moving),
                  fixed_flank_sites=flanks, fixed_flank_atoms=[deepcopy(a) for site in flanks for a in by_site[site]],
                  fixed_boundary_indices=sorted(fixed_boundary), term_counts=term_counts,
                  boundary_terms=boundary, polymer_junctions=junctions,
                  coordinates_changed=False, native_execution='NOT_RUN', movement_admitted=False,
                  nonbonded_coverage='NOT_ASSESSED', diffraction_coverage='NOT_ASSESSED',
                  scientific_acceptance=False, automatic_checkpoint_selection=False,
                  limitations=[
                      'Caller authenticates the full capture and prepared site contexts; a fingerprint is not source authority.',
                      'This is a region inventory, not a motion generator, native admission or covalent-closure proof.',
                      'Native target/weight records and Cartesian measurements are descriptive; no scientific angle cutoff is applied.',
                      'Crossing torsion/plane terms are retained, not independently evaluated as native energies.',
                      'Only captured supported bonded families are inventoried; nonbonded packing and diffraction need separate review.',
                      'PDB bytes, B/Q preservation, tensor transport, source chemical state and complete symmetry packing require their existing owners.',
                      'No atom-count, protonation, cluster coordination, conformational choice or refinement outcome is inferred.'])
    result['scope_id'] = digest(result)
    return result
