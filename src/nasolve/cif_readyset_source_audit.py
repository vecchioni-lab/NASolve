"""Read the installed ReadySet entrypoint and its CCD descriptor selection.

ReadySet source is copied as text, never imported or executed. The separate
native worker calls only the previously captured chemical-components filename
and SMILES accessors. A selected string is not a mapped graph or a restraint.
"""
import ast
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import _inside, MAX_SOURCE_BYTES
from .cif_generation import _terminate_owned_group

POLICY_ID = 'cif-readyset-source-and-descriptor-selection-v1'


def _check(root, row):
    if row.get('anchor') != 'phenix_installation':
        raise ValueError('Require an installation-anchored source')
    data = _inside(root, row['path']).read_bytes()
    if len(data) != row['size'] or sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Installed source differs from its captured proof')
    return data


def _destination(root, output):
    output = Path(output).absolute()
    if (output.exists() or output.is_symlink() or output.resolve().is_relative_to(root)
            or any(p.is_symlink() for p in output.parents)):
        raise ValueError('Require fresh separate source evidence')
    return output


def capture_readyset_sources(root, site, dispatcher, output, *, max_files=32):
    """Capture a literal dispatcher target and bounded first-party imports.

    Follow ReadySet-named modules through three levels and capture their direct
    elbow/mmtbx imports. Dynamic imports and other transitive code stay outside
    this static inventory; no inferred call path is labelled as executed.
    """
    root = Path(root).resolve(strict=True)
    site = PurePosixPath(site)
    output = _destination(root, output)
    if type(max_files) is not int or not 1 <= max_files <= 32:
        raise ValueError('Require a source-file budget in [1,32]')
    data = _check(root, dispatcher)
    targets = set(re.findall(r'"\$LIBTBX_PREFIX/([^"\r\n]+\.py)"', data.decode('utf-8')))
    if len(targets) != 1:
        raise ValueError('Require one exact literal ReadySet dispatcher target')
    entry = PurePosixPath(next(iter(targets)))
    if (entry.is_absolute() or '..' in entry.parts or not entry.is_relative_to(site)
            or not str(entry.relative_to(site)).startswith('elbow/')):
        raise ValueError('ReadySet entrypoint escapes the selected Python library')
    output.mkdir(parents=True)
    queue = [(entry, 0)]; seen = set(); rows = []; imports = []; total = 0
    while queue:
        name, depth = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        payload = _inside(root, name.as_posix()).read_bytes()
        if len(payload) > MAX_SOURCE_BYTES or total + len(payload) > 8 * MAX_SOURCE_BYTES:
            raise ValueError('Oversized ReadySet static source inventory')
        tree = ast.parse(payload, filename=name.as_posix())
        target = output / 'sources' / name.relative_to(site)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = target.with_suffix(target.suffix + '.txt'); target.write_bytes(payload)
        rows.append({'anchor': 'phenix_installation', 'path': name.as_posix(),
            'size': len(payload), 'sha256': sha256(payload).hexdigest(),
            'snapshot': {'anchor': 'readyset_audit_directory', 'path': target.relative_to(output).as_posix()}})
        total += len(payload)
        if depth and not any(t in name.as_posix().lower() for t in ['ready_set', 'readyset']):
            continue
        package = list(name.relative_to(site).parts[:-1])
        candidates = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                candidates.update((a.name, node.lineno) for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    if node.level > len(package):
                        continue
                    parts = package[:len(package)-node.level+1] + (node.module or '').split('.')
                    module = '.'.join(p for p in parts if p)
                else:
                    module = node.module or ''
                candidates.add((module, node.lineno))
                candidates.update((module+'.'+a.name, node.lineno) for a in node.names if a.name != '*')
        for module, line in sorted(candidates):
            if not re.fullmatch(r'(?:elbow|mmtbx)(?:\.[A-Za-z_][A-Za-z_0-9]*)*', module):
                continue
            relative = site / module.replace('.', '/')
            choices = [PurePosixPath(str(relative)+'.py'), relative/'__init__.py']
            found = [p for p in choices if (root/p).is_file()]
            if len(found) > 1:
                raise ValueError('Ambiguous static Python module source')
            edge = {'source': name.as_posix(), 'line': line, 'module': module,
                    'status': 'NO_LITERAL_SOURCE', 'depth': depth+1}
            if found:
                selected = found[0]; _inside(root, selected.as_posix())
                edge['target'] = selected.as_posix()
                pending = {p for p, _ in queue}
                if selected in seen or selected in pending:
                    edge['status'] = 'RECORDED'
                elif depth >= 3:
                    edge['status'] = 'DEPTH_BUDGET'
                elif len(rows)+len(pending) >= max_files:
                    edge['status'] = 'FILE_BUDGET'
                else:
                    queue.append((selected, depth+1)); edge['status'] = 'RECORDED'
            imports.append(edge)
    for row in rows:
        _check(root, row)
    _check(root, dispatcher)
    return {'entrypoint': {'anchor': 'phenix_installation', 'path': entry.as_posix()},
        'sources': rows, 'imports': imports, 'source_file_budget': max_files,
        'coverage_complete': not any(e['status'].endswith('_BUDGET') for e in imports),
        'coverage': 'Literal first-party imports of the entrypoint and ReadySet-named modules only; no dynamic or complete transitive coverage.',
        'static_analysis_is_execution_proof': False, 'readyset_execution': 'NOT_RUN'}


WORKER = r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,json,sys
spec=json.loads(Path(sys.argv[1]).read_text());root=Path(spec['installation']).resolve(strict=True)
directory=Path.cwd().resolve();sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory]
sys.path.insert(0,spec['library'])
def check(row):
    p=Path(row['installed']).resolve(strict=True)
    if not p.is_relative_to(root):raise ValueError('Source escapes selected installation')
    data=p.read_bytes()
    if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:raise ValueError('Installed selection source changed')
    return p
source=spec['selector'];path=check(source);found=importlib.util.find_spec('mmtbx.chemical_components')
if found is None or Path(found.origin).resolve(strict=True)!=path:raise ValueError('Unselected installed descriptor API')
api=importlib.import_module('mmtbx.chemical_components')
if Path(api.__file__).resolve(strict=True)!=path:raise ValueError('Unselected descriptor import')
result={}
for code,row in spec['components'].items():
    expected=check(row);actual=Path(api.get_cif_filename(code)).resolve(strict=True)
    if actual!=expected:raise ValueError('Native CCD filename differs from captured selected resource')
    selected=api.get_smiles(code)
    if type(selected) is not str or len(selected)>16384:raise ValueError('Unsupported native descriptor selection')
    check(row);result[code]={'selected_smiles':selected,'ccd_path':actual.relative_to(root).as_posix()}
check(source)
Path('descriptor_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def verify_readyset_sources(root, report, output):
    root = Path(root).resolve(strict=True); output = Path(output).resolve(strict=True)
    for row in report['sources']:
        data = _check(root, row)
        if row['snapshot'].get('anchor') != 'readyset_audit_directory':
            raise ValueError('Unsafe source snapshot anchor')
        if _inside(output, row['snapshot']['path']).read_bytes() != data:
            raise ValueError('ReadySet evidence snapshot changed')
    return True


def audit_readyset_sources(root, executable, api_sources, catalogue, output, *, environment, timeout_seconds=30):
    """Freeze ReadySet text and call the pinned CCD SMILES selector only."""
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30:
        raise ValueError('Require bounded descriptor-selection timeout')
    root = Path(root).resolve(strict=True); executable = Path(executable).resolve(strict=True)
    if not executable.is_relative_to(root):
        raise ValueError('Require selected Phenix Python')
    site = _library_anchor(api_sources); output = _destination(root, output)
    selectors = [r for r in catalogue['sources'] if r['path'] in {
        (site/'mmtbx/chemical_components.py').as_posix(), (site/'mmtbx/chemical_components/__init__.py').as_posix()}]
    if len(selectors) != 1:
        raise ValueError('Require one previously captured descriptor selector')
    selector = selectors[0]; _check(root, selector)
    components = catalogue['components']
    if not 1 <= len(components) <= 3 or any(not re.fullmatch('[A-Z0-9]{1,3}', c) for c in components):
        raise ValueError('Require one to three explicit source controls')
    for code, row in components.items():
        if row['status'] != 'RECORDED':
            raise ValueError('Require captured installed CCD resources')
        expected = site/'chem_data/chemical_components'/code[0].lower()/('data_'+code+'.cif')
        if row['resource']['path'] != expected.as_posix():
            raise ValueError('Unexpected CCD resource anchor')
        _check(root, row['resource'])
    static = capture_readyset_sources(root, site, catalogue['readyset_dispatcher'], output)
    rows = list(static['sources'])
    for name, row in [('selector.py', selector), ('dispatcher.txt', catalogue['readyset_dispatcher'])]+[
            ('ccd/'+c+'.cif', r['resource']) for c,r in components.items()]:
        target = output/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(_check(root,row))
        rows.append({**row, 'snapshot': {'anchor': 'readyset_audit_directory', 'path': name}})
    dispatcher = executable.read_bytes()
    report = {'schema_version': 1, 'policy_id': POLICY_ID, 'status': 'REVIEW', 'sources': rows,
        'static_readyset': static, 'components': {}, 'readyset_execution': 'NOT_RUN',
        'dictionary_generation': 'NOT_RUN', 'optimization': 'NOT_RUN', 'automatic_adoption': False,
        'mapped_smiles_graph_comparison': 'NOT_RUN', 'numerical_restraints': 'UNASSESSED',
        'limitations': ['Static imports and a descriptor accessor do not establish an executed ReadySet path.',
            'Descriptor selection/text agreement does not establish a mapped graph, native restraints or historical correctness.',
            'No chiral constructor, generator, optimizer or scaffold change is requested.']}
    def worker_row(row):
        return {'installed': str(root/row['path']), 'size': row['size'], 'sha256': row['sha256']}
    spec = {'installation': str(root), 'library': str(root/site), 'selector': worker_row(selector),
        'components': {c: worker_row(r['resource']) for c,r in components.items()}}
    (output/'descriptor_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    (output/'descriptor_worker.py').write_text(WORKER)
    verify_readyset_sources(root,report,output)
    with (output/'descriptor_worker.log').open('xb') as log:
        process = subprocess.Popen([str(executable),'descriptor_worker.py','descriptor_spec.json'],cwd=output,
            env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
        try:
            rc = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_owned_group(process); raise ValueError('Descriptor-selection audit timed out')
        except BaseException:
            _terminate_owned_group(process); raise
    if rc != 0:
        raise ValueError('Installed descriptor selector failed; inspect descriptor_worker.log')
    result = json.loads((output/'descriptor_result.json').read_text())
    if set(result) != set(components):
        raise ValueError('Unexpected descriptor result component scope')
    for code, row in result.items():
        selected = row['selected_smiles']
        matches = [d for d in components[code]['comparison']['descriptors'] if d['descriptor']==selected]
        report['components'][code] = {**row, 'matching_descriptors': matches,
            'status': 'SELECTED_DESCRIPTOR_MATCH' if selected and matches else 'REVIEW',
            'mapped_smiles_graph_comparison': 'NOT_RUN', 'numerical_restraints': 'UNASSESSED'}
    verify_readyset_sources(root,report,output)
    if executable.read_bytes() != dispatcher:
        raise ValueError('Selected Phenix Python dispatcher changed')
    (output/'readyset_source_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return report
