"""Ordered existing repair proofs, without another executor or chemical selector.

An optional declared-linear chain precedes one or more owned plane completions.
Every transition retains identical model/PHIL/consumer context and exact dictionary
order. Source authority and derivative qualification belong to the existing selector.
"""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_captured_linear_attribution import read_captured_linear_attribution
from .cif_captured_plane_attribution import read_captured_plane_attribution
from .cif_linear_torsion_bundle import read_linear_torsion_bundle
from .cif_captured_mixed_gradients import _inputs
from .cif_component_runtime import _tree, MAX_FILES, MAX_BYTES
from .cif_dictionary_store import _bytes, _json
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact
from .cif_mixed_geometry import _ref

POLICY_ID = 'cif-ordered-source-repair-chain-v1'
REPORT = 'repair_chain.json'
ANCHOR = 'repair_chain_directory'
MAX_PLANES = 16
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


def _derive(root, controls):
    _need(isinstance(controls,dict) and set(controls) == {'linear', 'plane_count'}
          and type(controls['linear']) is bool and type(controls['plane_count']) is int
          and 1 <= controls['plane_count'] <= MAX_PLANES)
    expected={'planes'} | ({'linear'} if controls['linear'] else set())
    _need({p.name for p in root.iterdir()} - {REPORT} == expected)
    _need({p.name for p in (root/'planes').iterdir()} == {f'{i:03d}' for i in range(controls['plane_count'])})
    steps=[]; stages=[]; context=None; current=None; attributed=True
    def append(kind, code, index, before_path, after_path, source=None):
        nonlocal context, current
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
        ref=lambda p:_ref(p,root,ANCHOR)
        steps.append(dict(kind=kind,component=code,dictionary_index=index,
            before_receipt=ref(before_path),after_receipt=ref(after_path),
            source=None if source is None else ref(source)))
        stages.append(dict(before_receipt=before_path,after_receipt=after_path,
            before_dictionaries=before[2],after_dictionaries=after[2],source=source))
    if controls['linear']:
        directory=root/'linear';job=read_captured_linear_attribution(directory)
        plan=read_linear_torsion_bundle(directory/'bundle')
        _need(bool(plan['steps']))
        _need({p.name for p in (directory/'captures').iterdir()} ==
              {f'{i:03d}' for i in range(len(plan['steps'])+1)}, 'Unexpected linear repair stage')
        attributed &= (job['status']=='CAPTURED_LINEAR_ATTRIBUTION_PASS'
                       and job['kernel_execution_authentication']=='MAINTAINED_FRESH_NATIVE_JOB')
        for i,step in enumerate(plan['steps']):
            append('declared_linear_torsion',step['component'],step['dictionary_index'],
                   directory/'captures'/f'{i:03d}'/'native_receipt.json',
                   directory/'captures'/f'{i+1:03d}'/'native_receipt.json')
    plane_codes=[]
    for i in range(controls['plane_count']):
        directory=root/'planes'/f'{i:03d}';job=read_captured_plane_attribution(directory)
        control=job['controls'];code=control['component'];plane_codes.append(code)
        attributed &= (job['status']=='CAPTURED_PLANE_ATTRIBUTION_PASS'
                       and job['kernel_execution_authentication']=='MAINTAINED_FRESH_NATIVE_JOB')
        append('source_trigonal_plane',code,control['dictionary_index'],
            directory/'inputs/before/native_receipt.json',directory/'inputs/after/native_receipt.json',
            directory/'inputs/source.cif')
    _need(len(set(plane_codes)) == len(plane_codes), 'A component cannot borrow two independent plane choices')
    first=_inputs(stages[0]['before_receipt'].parent)
    report=dict(_FIXED,controls=controls,steps=steps,all_steps_attributed=bool(attributed),
        status='ATTRIBUTED_REPAIR_CHAIN' if attributed else 'REVIEW',
        outputs=[_ref(root/name,root,ANCHOR) for name in _tree(root) if name != REPORT],
        directories=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()))
    return report,dict(model=first[1],phils=first[3],before_dictionaries=stages[0]['before_dictionaries'],
        after_dictionaries=stages[-1]['after_dictionaries'],stages=stages,report=report)


def prepare_repair_chain(plane_attributions, output, *, linear_attribution=None):
    """Freeze existing proofs in explicit order; no native work or selection.

    Plane-only chains are supported. No-op/linear-only work keeps its old reader.
    Every component plane operation must already have its owned source proof.
    """
    _need(isinstance(plane_attributions,(list,tuple)) and 1 <= len(plane_attributions) <= MAX_PLANES)
    sources={f'planes/{i:03d}':_path(p,directory=True) for i,p in enumerate(plane_attributions)}
    if linear_attribution is not None: sources['linear']=_path(linear_attribution,directory=True)
    _need(len(set(sources.values()))==len(sources))
    output=Path(output).expanduser().absolute()
    _need(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents))
          and all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in sources.values()))
    snapshots={name:_tree(p) for name,p in sources.items()}
    _need(sum(len(v) for v in snapshots.values()) <= MAX_FILES
          and sum(len(b) for v in snapshots.values() for b in v.values()) <= MAX_BYTES)
    directories={name:sorted(p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_dir())
                 for name,source in sources.items()}
    controls=dict(linear=linear_attribution is not None,plane_count=len(plane_attributions))
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


def repair_chain_inputs(directory):
    """Recheck every constituent proof once and return its exact ordered paths."""
    try:
        root=_path(directory,directory=True);_tree(root);saved=_json((root/REPORT).read_bytes())
        report,inputs=_derive(root,saved['controls'])
        _need(_exact(saved,report))
        return inputs
    except (KeyError,TypeError,IndexError,OverflowError) as exc:
        raise ValueError('Incomplete ordered repair chain') from exc


def read_repair_chain(directory):
    return repair_chain_inputs(directory)['report']
