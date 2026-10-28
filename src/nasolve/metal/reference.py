"""Source-preserving human reference snapshots and explicit internal-geometry comparisons."""
from collections import Counter
from itertools import combinations
import hashlib
from pathlib import Path
import re

from .binding import AtomKey
from .context import _reference, parse_pdb
from .geometry import verify_geometry
from .materialize import _json, _json_bytes, _source
from .preview import _measurement
from .recipe import RecipeError, _fields, canonical, checksum, digest, element, text

PROTOCOL = 'metal-reference-comparison-v1'


def _elements(values):
    if not isinstance(values, (list, tuple)) or not values:
        raise RecipeError('Specify the elements of interest explicitly')
    result = [element(value) for value in values]
    if len(set(result)) != len(result):
        raise RecipeError('Elements of interest must be distinct')
    return sorted(result)


def _atom_rows(raw, parsed):
    charges = [line[78:80].strip() for line in raw.decode('ascii').splitlines()
               if line[:6].strip() in {'ATOM', 'HETATM'}]
    return [dict(key=a.key.to_dict(), element=a.element, xyz=list(a.xyz),
                 occupancy=s['occupancy'], reported_b_A2=s['b_iso'], anisou_pdb=s['anisou'],
                 adp_representation='ANISOU_AND_REPORTED_B' if s['anisou'] is not None else 'REPORTED_B_ONLY',
                 pdb_charge_field=charge, record=s['record'])
            for a, s, charge in zip(parsed.snapshot.atoms, parsed.to_dict()['atomic_state'], charges)]


def inspect_reference(raw, *, elements):
    """Read exact PDB fields; annotations never supply trusted anomalous values."""
    selected = _elements(elements)
    parsed = parse_pdb(raw)
    rows = _atom_rows(raw, parsed)
    return dict(kind='metal-reference-inventory', schema_version=1,
                source_sha256=hashlib.sha256(raw).hexdigest(), byte_count=len(raw),
                atom_count=len(rows), element_counts=dict(sorted(Counter(a['element'] for a in rows).items())),
                anisou_atom_count=sum(a['anisou_pdb'] is not None for a in rows),
                elements_of_interest=selected, atoms_of_interest=[a for a in rows if a['element'] in selected],
                cryst1_records=[line for line in raw.decode('ascii').splitlines() if line.startswith('CRYST1')],
                warnings=dict(occupancies_outside_zero_to_one=sum(not 0 <= a['occupancy'] <= 1 for a in rows),
                              negative_reported_b=sum(a['reported_b_A2'] < 0 for a in rows)),
                stored_anomalous_parameters='UNTRUSTED_IGNORED',
                occupancy_and_adp_interpretation='RECORDED_SNAPSHOT_ONLY',
                scientific_acceptance='NOT_ASSESSED', native_ready=False)


def _inputs(run, geometry):
    doc = verify_geometry(run, geometry)
    raw = _source(doc['files']['model'], run)
    preview = _json(_source(doc['files']['preview'], run))
    path = run / Path(doc['files']['model']['relative_path']).parent / 'manifest.json'
    return doc, raw, preview, _reference(path, run)


def _calculate(geometry, candidate_raw, preview, reference_raw, plan):
    _fields(plan, {'kind', 'schema_version', 'geometry_id', 'reference_sha256', 'elements', 'nodes', 'note'}, set(), 'reference map')
    if (plan['kind'] != 'metal-reference-map' or type(plan['schema_version']) is not int
            or plan['schema_version'] != 1 or plan['geometry_id'] != geometry['geometry_id']):
        raise RecipeError('Reference map requires the exact geometry ID and supported schema')
    checksum(plan['reference_sha256'], 'reference checksum')
    if plan['reference_sha256'] != hashlib.sha256(reference_raw).hexdigest():
        raise RecipeError('Reference model differs from the mapped source bytes')
    text(plan['note'], 'reference mapping note')
    inventory = inspect_reference(reference_raw, elements=plan['elements'])
    candidate = parse_pdb(candidate_raw)
    reference = parse_pdb(reference_raw)
    candidate_atoms = {a.key: a for a in candidate.snapshot.atoms}
    reference_atoms = {a.key: a for a in reference.snapshot.atoms}
    candidate_rows = {AtomKey(**a['key']): a for a in _atom_rows(candidate_raw, candidate)}
    reference_rows = {AtomKey(**a['key']): a for a in _atom_rows(reference_raw, reference)}
    nodes = {n['node_id']: n for n in preview['nodes']}
    mapping = plan['nodes']
    if (not isinstance(mapping, dict) or not 1 <= len(mapping) <= 64
            or set(mapping) - set(nodes) or not any(nodes[n]['kind'] == 'metal' for n in mapping)):
        raise RecipeError('Map 1 to 64 distinct recipe nodes, including at least one metal')
    rows, bound_candidate, bound_reference = [], {}, {}
    used_candidate, used_reference = set(), set()
    for node_id in sorted(mapping):
        node = nodes[node_id]
        if node['status'] != 'resolved' or node['atom'] is None:
            raise RecipeError('Mapped candidate node is unresolved: ' + node_id)
        try:
            ckey = AtomKey(**node['atom']['key'])
            rkey = AtomKey(**mapping[node_id])
        except (TypeError, ValueError) as exc:
            raise RecipeError('Require exact candidate/reference atom identities') from exc
        if rkey.symmetry != 'x,y,z' or rkey not in reference_atoms or ckey not in candidate_atoms:
            raise RecipeError('Mapped atom missing or symmetry transform unsupported')
        if ckey in used_candidate or rkey in used_reference:
            raise RecipeError('Reference correspondences must be one-to-one')
        used_candidate.add(ckey); used_reference.add(rkey)
        c, r = candidate_rows[ckey], reference_rows[rkey]
        if node['kind'] == 'metal' and r['element'] not in inventory['elements_of_interest']:
            raise RecipeError('Mapped reference metal must be among the explicit elements of interest')
        bound_candidate[node_id] = candidate_atoms[ckey]
        bound_reference[node_id] = reference_atoms[rkey]
        rows.append(dict(node_id=node_id, kind=node['kind'], candidate=c, reference=r,
                         element_agrees=c['element'] == r['element'],
                         candidate_minus_reference_occupancy=c['occupancy']-r['occupancy'],
                         candidate_minus_reference_reported_b_A2=c['reported_b_A2']-r['reported_b_A2'],
                         adp_representation_agrees=c['adp_representation'] == r['adp_representation'],
                         cartesian_displacement_A=None))

    def measure(kind, names):
        if any(name not in mapping for name in names):
            return dict(candidate=None, reference=None, candidate_minus_reference=None, issues=['unmapped_node'])
        c, ci = _measurement(kind, [bound_candidate[n] for n in names])
        r, ri = _measurement(kind, [bound_reference[n] for n in names])
        return dict(candidate=c, reference=r, candidate_minus_reference=c-r if c is not None and r is not None else None,
                    issues=['candidate:'+v for v in ci]+['reference:'+v for v in ri])

    pairs = [dict(node_ids=list(names), unit='angstrom', **measure('distance', names))
             for names in combinations(sorted(mapping), 2)]
    restraints = [dict(restraint_id=r['restraint_id'], node_ids=r['node_ids'], kind=r['kind'],
                       enabled=r['enabled'], unit=r['unit'], recipe_target=r['target'], recipe_sigma=r['sigma'],
                       **measure(r['kind'], r['node_ids'])) for r in preview['restraints']]
    return dict(kind='metal-reference-comparison-report', schema_version=1, protocol=PROTOCOL,
                status='REFERENCE_COMPARISON_REVIEW', geometry_id=geometry['geometry_id'],
                reference_inventory=inventory, mapping_note=plan['note'], nodes=rows,
                unmapped_candidate_nodes=sorted(set(nodes)-set(mapping)),
                unmapped_reference_atoms_of_interest=[a for a in inventory['atoms_of_interest']
                                                      if AtomKey(**a['key']) not in used_reference],
                pair_distances=pairs, recipe_geometry=restraints,
                candidate_cryst1_records=[line for line in candidate_raw.decode('ascii').splitlines() if line.startswith('CRYST1')],
                coordinate_policy='INDEPENDENT_STORED_FRAMES_NO_SUPERPOSITION',
                symmetry_expansion='NOT_PERFORMED', reference_role_equivalence='DECLARED_NOT_CHEMICALLY_QUALIFIED',
                stored_anomalous_parameters='UNTRUSTED_IGNORED',
                scientific_acceptance='NOT_ASSESSED', native_ready=False, automatic_checkpoint_selection=False,
                note='Internal distances and recipe angles use stored coordinates only; raw XYZ and ADP fields remain '
                     'separate snapshots. No target learning, metal assignment, fit, alignment or checkpoint adoption occurs.')


def _allocate(run):
    root = run / 'Metal'
    if root.is_symlink():
        raise RecipeError('Metal root must not be a symlink')
    indices = [int(m.group(1)) for p in root.iterdir()
               if (m := re.fullmatch(r'reference_comparison_(\d{3,})', p.name))]
    index = max(indices, default=0)+1
    while True:
        path = root / f'reference_comparison_{index:03d}'
        try:
            path.mkdir()
            return path
        except FileExistsError:
            index += 1


def _manifest(run, directory, parent, original_path):
    text(original_path, 'historical original path')
    files = {key: _reference(directory/name, run)
             for key, name in [('reference','reference.pdb'), ('mapping','mapping.json'), ('report','report.json')]}
    doc = dict(kind='metal-reference-comparison', schema_version=1, protocol=PROTOCOL,
               status='REFERENCE_COMPARISON_REVIEW', parent=parent, files=files,
               source_provenance=dict(original_path=original_path, path_is_provenance_only=True,
                                      source_sha256=files['reference']['sha256']),
               stored_anomalous_parameters='UNTRUSTED_IGNORED', native_ready=False,
               automatic_checkpoint_selection=False, scientific_acceptance='NOT_ASSESSED')
    doc['comparison_id'] = digest(doc)
    return doc


def compare_reference(run, geometry, reference_model, mapping):
    """Capture an explicit reference and compare mapped geometry without fitting."""
    run = Path(run).expanduser().resolve()
    reference_path = Path(reference_model).expanduser().resolve()
    raw = reference_path.read_bytes()
    plan = _json(canonical(mapping))  # Freeze caller-owned data before any writes.
    g, candidate, preview, parent = _inputs(run, geometry)
    report = _calculate(g, candidate, preview, raw, plan)
    directory = _allocate(run)
    try:
        (directory/'reference.pdb').write_bytes(raw)
        (directory/'mapping.json').write_bytes(_json_bytes(plan))
        (directory/'report.json').write_bytes(_json_bytes(report))
        if reference_path.read_bytes() != raw or canonical(_inputs(run, geometry)[0]) != canonical(g):
            raise RecipeError('Reference or candidate changed during capture')
        _source(parent, run)
        doc = _manifest(run, directory, parent, str(reference_path))
        (directory/'manifest.json').write_bytes(_json_bytes(doc))
        return doc
    except BaseException as exc:
        with (directory/'failure.json').open('xb') as handle:
            handle.write(_json_bytes(dict(status='FAILED', exception=type(exc).__name__, error=str(exc))))
        raise


def verify_reference_comparison(run, directory):
    """Replay from captured reference bytes; the original path is never reopened."""
    run = Path(run).expanduser().resolve()
    directory = Path(directory).expanduser()
    if not directory.is_absolute():
        directory = run / directory
    if directory.is_symlink() or directory.parent.is_symlink():
        raise RecipeError('Reference comparison must not be a symlink')
    directory = directory.resolve()
    if directory.parent != run/'Metal' or not re.fullmatch(r'reference_comparison_\d{3,}',directory.name):
        raise RecipeError('Require a numbered reference comparison in this run')
    try:
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
            raise RecipeError('Reference payload must be regular files')
        if {p.name for p in directory.iterdir()} != {'reference.pdb','mapping.json','report.json','manifest.json'}:
            raise RecipeError('Failed or unexpected reference comparison inventory')
        doc = _json((directory/'manifest.json').read_bytes())
        _fields(doc, {'kind', 'schema_version', 'protocol', 'status', 'parent', 'files',
                      'source_provenance', 'stored_anomalous_parameters', 'native_ready',
                      'automatic_checkpoint_selection', 'scientific_acceptance', 'comparison_id'},
                set(), 'reference comparison')
        if (doc.get('kind') != 'metal-reference-comparison' or type(doc.get('schema_version')) is not int
                or doc['schema_version'] != 1 or doc.get('protocol') != PROTOCOL):
            raise RecipeError('Unsupported reference comparison')
        check = dict(doc); identifier = check.pop('comparison_id')
        if digest(check) != identifier:
            raise RecipeError('Reference manifest checksum changed')
        parent = doc['parent']; _source(parent, run)
        if parent['anchor'] != 'run' or Path(parent['relative_path']).name != 'manifest.json':
            raise RecipeError('Reference comparison requires an anchored geometry manifest')
        g, candidate, preview, expected_parent = _inputs(run,Path(parent['relative_path']).parent)
        if parent != expected_parent:
            raise RecipeError('Geometry lineage changed')
        raw = _source(doc['files']['reference'], run)
        plan = _json(_source(doc['files']['mapping'], run))
        report = _calculate(g,candidate,preview,raw,plan)
        if _source(doc['files']['report'], run) != _json_bytes(report):
            raise RecipeError('Reference report differs from calculation replay')
        if canonical(doc) != canonical(_manifest(run,directory,parent,doc['source_provenance']['original_path'])):
            raise RecipeError('Reference manifest, files or review policy changed')
        return doc
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
        if isinstance(exc,RecipeError):
            raise
        raise RecipeError('Cannot verify reference comparison: '+str(exc)) from exc
