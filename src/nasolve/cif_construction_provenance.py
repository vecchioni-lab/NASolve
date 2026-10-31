"""Read-only construction-stage provenance for captured geometry findings."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
from math import dist, isfinite, sqrt
from pathlib import Path, PurePosixPath

from .cif_captured_geometry import CAPTURED_GEOMETRY_POLICY, _observed

CONSTRUCTION_POLICY = 'cif-construction-stage-provenance-v1'
STAGE_PATHS = {
    'mr_input': 'PostMR/Model/mr_solution.pdb',
    'component_normalized': 'PostMR/Model/component_normalized.pdb',
    'coot_raw': 'PostMR/Model/after_coot_raw.pdb',
    'restored': 'PostMR/Model/after_coot_geometry.pdb',
    'after_coot': 'PostMR/Model/after_coot.pdb',
    'terminal': 'PostMR/Model/terminal_phosphate_model.pdb',
    'prepared': 'PostMR/Model/prepared_model.pdb'}
_RECEIPTS = ('report.json', 'PostMR/report.json', 'PostMR/Coot/mutate.py',
             'PostMR/Coot/coot.log', 'PostMR/Restraints/cif_doctor_source.json')


def _safe(path):
    return isinstance(path, str) and not path.startswith('/') and '\\' not in path and ':' not in path and all(
        part not in {'', '.', '..'} for part in path.split('/'))


def declared_coot_references(text: str, historical_run: str) -> dict:
    """Read literal artifact declarations from the saved script; never execute it."""
    root = PurePosixPath(historical_run)
    inputs, dictionaries, parents, external, unsupported = [], [], {}, [], []
    pending = None
    for statement in ast.parse(text).body:
        calls = [n for n in ast.walk(statement) if isinstance(n, ast.Call)]
        for call in calls:
            name = call.func.attr if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == 'coot' else None
            if name in {'handle_read_draw_molecule', 'read_cif_dictionary', 'write_pdb_file'}:
                index = 1 if name == 'write_pdb_file' else 0
                if len(call.args) <= index or not isinstance(call.args[index], ast.Constant) or not isinstance(call.args[index].value, str):
                    unsupported.append(name + ':nonliteral-path'); continue
                original = call.args[index].value; path = PurePosixPath(original)
                if '..' in path.parts or '\\' in original:
                    raise ValueError('Unsafe saved Coot artifact reference')
                try:
                    relative = path.relative_to(root).as_posix()
                except ValueError:
                    external.append(original); continue
                if not _safe(relative):
                    raise ValueError('Unsafe saved run-relative artifact reference')
                if name == 'handle_read_draw_molecule': inputs.append(relative)
                elif name == 'read_cif_dictionary': dictionaries.append(relative)
                elif relative.startswith('PostMR/Coot/'):
                    pending = relative
            if isinstance(call.func, ast.Name) and call.func.id == 'print' and len(call.args) >= 2:
                values = [a.value if isinstance(a, ast.Constant) else None for a in call.args[:2]]
                if values[0] == 'NASOLVE_OVERLAP' and isinstance(values[1], str) and pending:
                    if values[1] in parents:
                        raise ValueError('Ambiguous saved parent declaration')
                    parents[values[1]] = pending; pending = None
    return {'inputs': sorted(set(inputs)), 'dictionaries': sorted(set(dictionaries)), 'parents': parents,
            'uncollected_external_paths': sorted(set(external)), 'unsupported_declarations': unsupported}


def snapshot_construction_run(run: Path, destination: Path, binding: dict,
                              historical_run: str) -> dict:
    """Freeze exact declared stage files outside a hash-bound original run."""
    run = Path(run).resolve(strict=True); destination = Path(destination).resolve()
    if destination == run or destination.is_relative_to(run):
        raise ValueError('Construction output must be outside the original run')
    if destination.exists():
        raise FileExistsError(destination)
    def source(relative):
        if not _safe(relative): raise ValueError('Unsafe run artifact path')
        path = run / PurePosixPath(relative)
        if any(p.is_symlink() for p in [path, *path.parents] if p != run and run in p.parents):
            raise ValueError('Source artifact has a symlink: ' + relative)
        if not path.resolve().is_relative_to(run): raise ValueError('Source artifact escaped run')
        return path
    bound = source(binding['path']); data = bound.read_bytes()
    if len(data) != binding['size'] or hashlib.sha256(data).hexdigest() != binding['sha256']:
        raise ValueError('Original model binding differs from reviewed evidence')
    destination.mkdir(parents=True)
    records = {}; payloads = {}
    def freeze(relative):
        if relative in records: return records[relative]
        path = source(relative)
        if not path.exists():
            records[relative] = {'status': 'NOT_PRESENT', 'anchor': 'run', 'path': relative}
            return records[relative]
        if not path.is_file() or path.stat().st_size > 16*1024*1024:
            raise ValueError('Unsupported construction artifact: ' + relative)
        content = path.read_bytes(); target = destination / PurePosixPath(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle: handle.write(content)
        if path.read_bytes() != content: raise ValueError('Construction source changed during snapshot')
        payloads[relative] = content
        records[relative] = {'status': 'RECORDED', 'anchor': 'run', 'path': relative,
                             'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content)}
        return records[relative]
    for relative in [*STAGE_PATHS.values(), *_RECEIPTS]: freeze(relative)
    script = payloads.get('PostMR/Coot/mutate.py')
    references = declared_coot_references(script.decode('utf-8'), historical_run) if script else {
        'inputs': [], 'dictionaries': [], 'parents': {}, 'uncollected_external_paths': [],
        'unsupported_declarations': ['Saved Coot script absent']}
    for relative in [*references['inputs'], *references['dictionaries'], *references['parents'].values()]: freeze(relative)
    frozen_binding = records[binding['path']]
    if frozen_binding.get('sha256') != binding['sha256'] or frozen_binding.get('size') != binding['size']:
        raise ValueError('Original model binding changed during snapshot')
    def frozen(relative):
        return destination / PurePosixPath(relative) if records[relative]['status'] == 'RECORDED' else None
    return {'stages': {name: frozen(relative) for name, relative in STAGE_PATHS.items()},
            'parents': {site: frozen(relative) for site, relative in references['parents'].items()},
            'records': records, 'references': references,
            'binding': dict(binding), 'run_provenance': str(run)}


def verify_construction_snapshot(run: Path, destination: Path, records: dict) -> None:
    """Recheck both original and frozen recorded files after analysis."""
    run = Path(run).resolve(); destination = Path(destination).resolve()
    for relative, row in records.items():
        if not _safe(relative): raise ValueError('Unsafe construction record')
        for anchor in (run, destination):
            path = anchor / PurePosixPath(relative)
            if row['status'] == 'NOT_PRESENT':
                if path.exists() or path.is_symlink(): raise ValueError('Missing evidence appeared during review')
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(anchor):
                raise ValueError('Construction artifact escaped anchor')
            data = path.read_bytes()
            if len(data) != row['size'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Construction evidence changed: ' + relative)


def _pdb_inventory(path):
    result = {}; models = 0
    for line in Path(path).read_text().splitlines():
        if line.startswith('MODEL '):
            models += 1
            if models > 1: raise ValueError('Multiple PDB models require a separate context')
        if line[:6] not in {'ATOM  ', 'HETATM'}: continue
        if len(line) < 78: raise ValueError('PDB stage lacks explicit element columns')
        key = (line[21].strip() or '_', line[22:26].strip(), line[26].strip(), line[16].strip(), line[12:16].strip())
        if key in result: raise ValueError('Duplicate PDB atom identity')
        xyz = [float(line[a:b]) for a,b in [(30,38),(38,46),(46,54)]]
        if not all(isfinite(x) for x in xyz): raise ValueError('Nonfinite PDB coordinate')
        result[key] = {'xyz': xyz, 'element': line[76:78].strip().upper(), 'code': line[17:20].strip()}
    return result


def _key(atom):
    identity = atom['identity']
    return (identity['chain_id'].strip() or '_', identity['resseq'].strip(), identity['icode'].strip(),
            identity['altloc'].strip(), atom['atom_id'])


def audit_construction_stages(native: dict, geometry: dict, stages: dict,
                              parents: dict | None = None) -> dict:
    """Locate observed threshold crossings; chronology alone does not prove cause."""
    if geometry.get('policy_id') != CAPTURED_GEOMETRY_POLICY or not geometry.get('analysis_completed'):
        raise ValueError('Require a completed captured Cartesian review')
    inventories = {name: _pdb_inventory(path) if path else None for name,path in stages.items()}
    findings = []; selected = {}
    for kind in ('bond_simple', 'angle'):
        for row in geometry['measurements'][kind]:
            if row['nominal_deviation'] is None or abs(row['nominal_deviation']) < 5 or len(row['sites']) != 1:
                continue
            endpoints = [native['atoms'][i] for i in row['i_seqs']]
            if row['atoms'] != [a['label'] for a in endpoints]: raise ValueError('Captured finding identity differs')
            site = row['sites'][0]
            selected.setdefault(site, {}).update({_key(a): a for a in endpoints})
            comparisons = []
            for stage, inventory in inventories.items():
                value = {'stage': stage, 'status': 'NOT_PRESENT', 'observed': None, 'nominal_deviation': None}
                if inventory is not None:
                    atoms = [inventory.get(_key(a)) for a in endpoints]
                    if any(a is None for a in atoms): value['status'] = 'ATOMS_NOT_PRESENT'
                    elif any(a['code'] != e['identity']['resname'].strip() for a,e in zip(atoms,endpoints)):
                        value['status'] = 'COMPONENT_NOT_YET_PRESENT'
                    elif any(a['element'] != e['element'].strip().upper() for a,e in zip(atoms,endpoints)):
                        value['status'] = 'ELEMENT_MISMATCH'
                    else:
                        observed = _observed(kind, [a['xyz'] for a in atoms])
                        value.update(status='DEGENERATE' if observed is None else 'MEASURED', observed=observed,
                            nominal_deviation=None if observed is None else (observed-row['target'])*sqrt(row['weight']))
                comparisons.append(value)
            crossings = [{'before': left['stage'], 'after': right['stage']} for left,right in zip(comparisons, comparisons[1:])
                if left['status'] == right['status'] == 'MEASURED' and abs(left['nominal_deviation']) < 5 <= abs(right['nominal_deviation'])]
            first = next((v['stage'] for v in comparisons if v['nominal_deviation'] is not None and abs(v['nominal_deviation']) >= 5), None)
            findings.append({'kind': kind, 'site': site, 'atoms': [a['atom_id'] for a in endpoints],
                             'captured_proxy_index': row['proxy_index'], 'target': row['target'], 'weight': row['weight'],
                             'unit': row['unit'], 'stages': comparisons,
                             'first_observed_outlier_stage': first, 'threshold_crossings': crossings})
    parent_comparisons = {}
    for site, path in (parents or {}).items():
        if site not in selected or path is None: continue
        parent = _pdb_inventory(path); raw = inventories.get('coot_raw'); restored = inventories.get('restored')
        rows = []
        for key, expected in selected[site].items():
            a = parent.get(key); b = raw.get(key) if raw else None; c = restored.get(key) if restored else None
            if not all([a,b,c]) or any(x['element'] != expected['element'].strip().upper() for x in (a,b,c)): continue
            # Same-name coordinates are evidence only, never a semantic atom map.
            before, after = dist(a['xyz'], b['xyz']), dist(a['xyz'], c['xyz'])
            rows.append({'atom_id': key[-1], 'altloc': key[-2], 'parent_code': a['code'],
                         'raw_to_parent': before, 'restored_to_parent': after,
                         'raw_to_restored': dist(b['xyz'], c['xyz']),
                         'observed_parent_coordinate_copy': before > .01 and after <= .001})
        parent_comparisons[site] = rows
    return {'schema_version': 1, 'audit_kind': 'cif_construction_stage_provenance', 'policy_id': CONSTRUCTION_POLICY,
            'status': 'REVIEW', 'analysis_completed': True, 'selected_sites': sorted(selected),
            'findings': findings, 'parent_coordinate_comparisons': parent_comparisons,
            'first_observed_outlier_counts': dict(Counter(f['first_observed_outlier_stage'] or 'NOT_LOCATED' for f in findings)),
            'threshold_crossing_count': sum(len(f['threshold_crossings']) for f in findings),
            'root_cause': 'NOT_ESTABLISHED', 'model_editing': 'NOT_RUN', 'native_execution': 'NOT_RUN',
            'optimization': 'NOT_RUN', 'refinement': 'NOT_RUN', 'automatic_adoption': False,
            'limitations': ['Nominal threshold five selects evidence, not scientific acceptance.',
                'Earliest observed stage is not necessarily the originating step; absent evidence stays explicit.',
                'Threshold crossings require adjacent comparable stages; gaps cannot prove a transition.',
                'Same-name parent coordinate matches do not establish semantic graph correspondence.',
                'No coordinate repair, atom remapping, target change or full geometry qualification is performed.']}
