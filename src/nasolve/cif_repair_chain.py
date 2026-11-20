"""Ordered existing repair proofs, without another executor or chemical selector.

An optional declared-linear chain precedes owned plane completions and explicit
reference-backed bond-target repairs. Historical plane chains retain v1.
Every transition retains identical model/PHIL/consumer context and exact dictionary
order. Source authority and derivative qualification belong to the existing selector.
"""
from contextlib import nullcontext
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_captured_linear_attribution import read_captured_linear_attribution
from .cif_captured_plane_attribution import read_captured_plane_attribution
from .cif_linear_torsion_bundle import read_linear_torsion_bundle
from .cif_captured_mixed_gradients import _inputs
from .cif_component_runtime import CombinedEvidenceLimit, _snapshot_roots, _tree, MAX_FILES, MAX_BYTES
from .cif_dictionary_store import _bytes, _json
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact
from .cif_mixed_geometry import _ref

POLICY_ID = 'cif-ordered-source-repair-chain-v1'
BOND_POLICY_ID = 'cif-ordered-source-repair-chain-v2'
STAGED_POLICY_ID = 'cif-staged-source-repair-chain-v1'
REPORT = 'repair_chain.json'
ANCHOR = 'repair_chain_directory'
MAX_PLANES = 16
MAX_BONDS = 16
_FIXED = dict(schema_version=1, policy_id=POLICY_ID, coordinate_selection='UNCHANGED_PREPARED_MODEL',
    source_qualification='CALLER_REQUIRED', derivative_qualification='NOT_RUN',
    automatic_adoption=False, new_native_calls=0, captured_code_execution='NOT_RUN')


def _need(value, message='Ordered repair chain does not reproduce'):
    if not value:
        raise ValueError(message)


def _context(entry):
    capture, model, dictionaries, phils, native, _ = entry
    return dict(model=sha256(model.read_bytes()).hexdigest(), phils=[sha256(p.read_bytes()).hexdigest() for p in phils],
        producer={k:capture.get(k) for k in ('phenix_version','executable_sha256','api_sources',
            'phil_namespace_policy','dictionary_source_policy','full_monomer_inventory_policy')},
        installed_sources=native['energy_inventory']['installed_sources'])


def _check_controls(controls):
    _need(isinstance(controls,dict) and set(controls) in
          ({'linear','plane_count'},{'linear','plane_count','bond_count'}))
    bond_count=controls.get('bond_count',0);with_bonds='bond_count' in controls
    _need(type(controls['linear']) is bool and type(controls['plane_count']) is int
          and (0 if with_bonds else 1) <= controls['plane_count'] <= MAX_PLANES
          and type(bond_count) is int and (1 if with_bonds else 0) <= bond_count <= MAX_BONDS)


def _stage_names(controls):
    names = ['linear'] if controls['linear'] else []
    names.extend(f'planes/{i:03d}' for i in range(controls['plane_count']))
    names.extend(f'bonds/{i:03d}' for i in range(controls.get('bond_count', 0)))
    return names


@dataclass(frozen=True)
class RepairTransition:
    """One observed change. Capture paths are valid only during the visitor call."""

    stage: str
    directory: Path
    kind: str
    component: str
    dictionary_index: int
    before_receipt: Path
    after_receipt: Path
    source: Path | None
    before: tuple
    after: tuple
    first: bool
    last: bool

    def references(self, root, anchor):
        return dict(kind=self.kind, component=self.component, dictionary_index=self.dictionary_index,
                    before_receipt=_ref(self.before_receipt,root,anchor),
                    after_receipt=_ref(self.after_receipt,root,anchor),
                    source=None if self.source is None else _ref(self.source,root,anchor))


def _verify_stages(controls, open_stage, library, visit):
    """Reproduce scientific ownership and consecutive edits while each proof is open."""
    names = _stage_names(controls)
    final_stage = names[-1]
    context=None; current=None; attributed=True; first=True
    def append(name, directory, kind, code, index, before_path, after_path, source=None):
        nonlocal context, current, first
        before,after=[_inputs(p.parent) for p in (before_path,after_path)]
        for entry in (before,after):
            observed=_context(entry)
            if context is None: context=observed
            else:_need(_exact(observed,context), 'Repair changed model, ordered PHIL or native consumer')
        before_bytes=[p.read_bytes() for p in before[2]]
        if current is not None:
            _need(current == before_bytes, 'Repair steps do not form an exact consecutive dictionary chain')
        _need(type(index) is int and 0 <= index < len(before[2]) and len(before[2]) == len(after[2]))
        after_bytes=[p.read_bytes() for p in after[2]]
        _need(all(a == b for j,(a,b) in enumerate(zip(before_bytes,after_bytes)) if j != index),
              'Repair changed an unowned dictionary slot')
        _need(before_bytes[index] != after_bytes[index], 'Repair step does not change its declared dictionary')
        current=after_bytes
        visit(RepairTransition(name, directory, kind, code, index, before_path, after_path, source,
                               before, after, first, name == final_stage))
        first = False

    plane_codes=set();bond_codes=set()
    for name in names:
        with open_stage(name) as directory:
            if name == 'linear':
                job=read_captured_linear_attribution(directory)
                plan=read_linear_torsion_bundle(directory/'bundle')
                _need(bool(plan['steps']))
                _need({p.name for p in (directory/'captures').iterdir()} ==
                      {f'{i:03d}' for i in range(len(plan['steps'])+1)}, 'Unexpected linear repair stage')
                attributed &= (job['status']=='CAPTURED_LINEAR_ATTRIBUTION_PASS'
                               and job['kernel_execution_authentication']=='MAINTAINED_FRESH_NATIVE_JOB')
                for i,step in enumerate(plan['steps']):
                    append(name, directory, 'declared_linear_torsion',step['component'],step['dictionary_index'],
                           directory/'captures'/f'{i:03d}'/'native_receipt.json',
                           directory/'captures'/f'{i+1:03d}'/'native_receipt.json')
                continue
            if name.startswith('planes/'):
                job=read_captured_plane_attribution(directory)
                control=job['controls'];code=control['component'];index=control['dictionary_index']
                _need(code not in plane_codes, 'A component cannot borrow two independent plane choices')
                plane_codes.add(code);kind='source_trigonal_plane'
                attributed &= (job['status']=='CAPTURED_PLANE_ATTRIBUTION_PASS'
                               and job['kernel_execution_authentication']=='MAINTAINED_FRESH_NATIVE_JOB')
            else:
                from .cif_energy_library import qualify_bond_attribution_reference
                consumer=_json((library/'spec.json').read_bytes())['consumer']
                binding=qualify_bond_attribution_reference(directory,library,consumer=consumer)
                code=binding['reference']['component'];index=binding['dictionary_index']
                _need(code not in bond_codes, 'A component cannot borrow two independent target choices')
                bond_codes.add(code);kind='source_linear_bond_target'
                attributed &= binding['status']=='LIBRARY_BOUND_BOND_ATTRIBUTION_PASS'
            append(name, directory, kind, code, index, directory/'inputs/before/native_receipt.json',
                   directory/'inputs/after/native_receipt.json',directory/'inputs/source.cif')
    return bool(attributed)


def _derive(root, controls, visit=None):
    _check_controls(controls)
    bond_count=controls.get('bond_count',0);with_bonds='bond_count' in controls
    expected=({'planes'} if controls['plane_count'] else set()) | ({'linear'} if controls['linear'] else set())
    if with_bonds:expected |= {'bonds','library'}
    _need({p.name for p in root.iterdir()} - {REPORT} == expected)
    for name,count in [('planes',controls['plane_count']),('bonds',bond_count)]:
        if count:_need({p.name for p in (root/name).iterdir()} == {f'{i:03d}' for i in range(count)})
    steps=[];stages=[]
    def record(step):
        steps.append(step.references(root, ANCHOR))
        stages.append(dict(before_receipt=step.before_receipt, after_receipt=step.after_receipt,
                           before_dictionaries=step.before[2], after_dictionaries=step.after[2], source=step.source))
        if visit is not None:
            visit(step)
    attributed=_verify_stages(controls, lambda name:nullcontext(root/name), root/'library', record)
    first=_inputs(stages[0]['before_receipt'].parent)
    report=dict(_FIXED,controls=controls,steps=steps,all_steps_attributed=bool(attributed),
        status='ATTRIBUTED_REPAIR_CHAIN' if attributed else 'REVIEW',
        outputs=[_ref(root/name,root,ANCHOR) for name in _tree(root) if name != REPORT],
        directories=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))
    if with_bonds:report['policy_id']=BOND_POLICY_ID
    return report,dict(model=first[1],phils=first[3],before_dictionaries=stages[0]['before_dictionaries'],
        after_dictionaries=stages[-1]['after_dictionaries'],stages=stages,report=report)


def prepare_repair_chain(plane_attributions, output, *, linear_attribution=None,
        bond_attributions=(), energy_library=None, storage='expanded'):
    """Freeze existing proofs in explicit order; no native work or selection.

    Old linear/plane calls retain exact v1 output. Explicit bond stages use v2,
    follow any planes, and share one authenticated library capture. Source
    qualification and derivatives remain the existing selector's responsibility.
    Auto storage uses separate archives only when the expanded combination exceeds
    its allowance. A malformed individual proof always raises.
    """
    _need(isinstance(bond_attributions,(list,tuple)) and len(bond_attributions)<=MAX_BONDS
          and bool(bond_attributions)==(energy_library is not None), 'Bond repairs require exactly one shared library')
    _need(isinstance(plane_attributions,(list,tuple))
          and (0 if bond_attributions else 1) <= len(plane_attributions) <= MAX_PLANES)
    sources={f'planes/{i:03d}':_path(p,directory=True) for i,p in enumerate(plane_attributions)}
    if linear_attribution is not None: sources['linear']=_path(linear_attribution,directory=True)
    if bond_attributions:
        sources.update({f'bonds/{i:03d}':_path(p,directory=True) for i,p in enumerate(bond_attributions)})
        sources['library']=_path(energy_library,directory=True)
    _need(len(set(sources.values()))==len(sources))
    output=Path(output).expanduser().absolute()
    _need(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents))
          and all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in sources.values()))
    controls=dict(linear=linear_attribution is not None,plane_count=len(plane_attributions))
    if bond_attributions:controls['bond_count']=len(bond_attributions)
    _need(storage in ('expanded', 'staged', 'auto'), 'Unknown repair chain storage')
    snapshots = None
    if storage != 'staged':
        try:
            snapshots = _snapshot_roots(sources, max_files=MAX_FILES, max_bytes=MAX_BYTES,
                message='Combined repair evidence exceeds its limit')
        except CombinedEvidenceLimit:
            if storage != 'auto':
                raise
    if snapshots is None:
        from .cif_staged_repair_chain import write_staged_chain
        return write_staged_chain(output, sources, controls)
    directories={name:sorted(p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_dir())
                 for name,source in sources.items()}
    with TemporaryDirectory(prefix='repair-chain-') as temporary:
        staging=Path(temporary).resolve()
        for name,files in snapshots.items():
            for relative in directories[name]:(staging/name/relative).mkdir(parents=True,exist_ok=True)
            for relative,data in files.items():
                p=staging/name/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        report,_=_derive(staging,controls)
        _need(all(_tree(sources[k])==v for k,v in snapshots.items()), 'Repair evidence changed during freezing')
        output.mkdir(parents=True,exist_ok=False)
        for relative in report['directories']:(output/relative).mkdir(parents=True,exist_ok=True)
        for name,data in _tree(staging).items():
            p=output/name;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as stream:stream.write(data)
        with (output/REPORT).open('xb') as stream:stream.write(_bytes(report))
    _need(all(_tree(sources[k])==v and
              sorted(p.relative_to(sources[k]).as_posix() for p in sources[k].rglob('*') if p.is_dir()) == directories[k]
              for k,v in snapshots.items()), 'Repair evidence changed during freezing')
    return read_repair_chain(output)


def _read_chain(directory, visit=None):
    """Recheck each constituent proof using the storage declared in the sealed record."""
    try:
        root=_path(directory,directory=True);_tree(root);saved=_json((root/REPORT).read_bytes())
        if saved.get('policy_id') == STAGED_POLICY_ID:
            from .cif_staged_repair_chain import inspect_staged_chain
            return inspect_staged_chain(root, saved, visit)
        report,inputs=_derive(root,saved['controls'],visit)
        _need(_exact(saved,report))
        return inputs
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete ordered repair chain') from exc


def visit_repair_chain(directory, visit=None):
    """Return the stable endpoints after verifying the complete chain.

    The optional callback receives a RepairTransition while its capture paths
    are live. Its observations are provisional until this function returns.
    """
    return _read_chain(directory, visit)


def repair_chain_inputs(directory):
    """Return persistent intermediate paths for the original expanded formats."""
    result = _read_chain(directory)
    _need('stages' in result, 'Staged repair intermediates require visit_repair_chain')
    return result


def read_repair_chain(directory):
    return _read_chain(directory)['report']
