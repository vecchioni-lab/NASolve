"""Freeze original literal NA intent and replay the maintained C21 compiler.

This is an input/provenance artifact, not a native qualification or execution
owner. The original mode uses native capture identities. Source mode uses explicitly
labelled PDB identities and source-graph roles. Both need independent native
validation in the selected dictionary/model context.
"""
from pathlib import Path

from .cif_attachment_native import _capture, _native_atoms
from .cif_catalogue import _digest
from .cif_component_runtime import _tree
from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _bytes, _json
from .cif_explicit_na_policy import _implementation
from .cif_na_policy import _compile_na_policy_payload
from .cif_repair_attempt import _root
from .cif_restraint_context import _derive_restraint_payload

POLICY_ID = 'cif-literal-na-inputs-v1'
SOURCE_POLICY_ID = 'cif-source-literal-na-inputs-v1'
ANCHOR = 'literal_na_input_directory'
MANIFEST = 'literal_na_inputs.json'


def _ref(name, data):
    return dict(anchor=ANCHOR, path=name, **_digest(data))


def _exact_tree(root):
    files = _tree(root)
    expected = {p.as_posix() for n in files for p in Path(n).parents if str(p) != '.'}
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_dir()}
    _need(actual == expected, 'Unrequested literal-input directory')
    return files


def _payload(model, native_receipt):
    model = Path(model).absolute(); native_receipt = Path(native_receipt).absolute()
    original = _read(model); tree = _exact_tree(native_receipt.parent)
    _need(native_receipt.name == 'native_receipt.json', 'Require the maintained native receipt filename')
    receipt, native, snapshots = _capture(native_receipt, original)
    _need({p.relative_to(native_receipt.parent).as_posix(): data for p,data in snapshots.items()} == tree,
          'Native capture contains unbound members')
    _need(receipt['status'] == 'REVIEW' and not native.get('fatal_problems')
          and not native.get('unused_definitions') and not native.get('unsupported_fields'),
          'Require completed unambiguous native input capture')
    spec = _json(tree['native_spec.json'])
    _need(spec.get('policy_inventory') is True, 'Require captured native restraint policy')
    _native_atoms(native, original)
    names = [row['path'] for row in receipt['inputs'] if row['role'] == 'phil']
    _need(1 <= len(names) <= 63, 'Require one to 63 original ordered PHIL inputs')
    pins = _implementation()
    compilation, compiled = _compile_na_policy_payload(model, [native_receipt.parent/n for n in names], native)
    order = [*compilation['retained_phils'], compilation['compiled_phil']]
    # Use the same scoped selection grammar as new explicit input binding.
    context = _derive_restraint_payload(model, [compiled[n] for n in order], require_scoped_names=True)
    files = {'model.pdb': original, **{'native/'+n:b for n,b in tree.items()},
             **{'compiled/'+n:b for n,b in compiled.items()}}
    report = dict(schema_version=1, policy_id=POLICY_ID, status='FROZEN_LITERAL_INPUTS',
        model=_ref('model.pdb', original), native_receipt=_ref('native/native_receipt.json',tree['native_receipt.json']),
        original_phils=[_ref('native/'+n,tree[n]) for n in names],
        compiled_phils=[_ref('compiled/'+n,compiled[n]) for n in order],
        implementation=pins, compilation=compilation, restraint_context=context,
        files=[_ref(n,b) for n,b in sorted(files.items())],
        native_membership='NOT_ASSESSED_FOR_COMPILED_INPUTS', automatic_adoption=False,
        scientific_approval='NOT_RUN', model_optimization='NOT_RUN', refinement='NOT_RUN')
    _need(_read(model) == original and _exact_tree(native_receipt.parent) == tree
          and _implementation() == pins, 'Literal input or compiler changed during compilation')
    return report, files


def _write_payload(root, report, files):
    root.mkdir(parents=True, exist_ok=False)
    for name,data in sorted(files.items()):
        path = root/name; path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as handle: handle.write(data)
    with (root/MANIFEST).open('xb') as handle: handle.write(_bytes(report))


def prepare_literal_na_inputs(model, native_receipt, output):
    """Freeze a preserved native capture and faithful compiled input in a fresh root.

    Literal Saenger 19/20 pairs and mapped stacks use the existing compiler.
    Required planes/edits survive; modifiers and unsupported settings refuse.
    No native worker, generation, refinement or adoption is run here.
    """
    root = _root(output)
    if root.exists(): raise FileExistsError(root)
    capture_root = Path(native_receipt).absolute().parent
    _need(not root.is_relative_to(capture_root) and not capture_root.is_relative_to(root)
          and not Path(model).absolute().is_relative_to(root), 'Literal output overlaps its inputs')
    report, files = _payload(model, native_receipt)
    _write_payload(root,report,files)
    _need(read_literal_na_inputs(root) == report, 'Frozen literal input replay differs')
    fresh, original_files = _payload(model, native_receipt)
    _need(fresh == report and original_files == files, 'Literal source changed while freezing')
    return report


def read_literal_na_inputs(directory):
    """Reconstruct every compiled byte without writes, execution or old paths."""
    root = Path(directory).absolute(); tree = _exact_tree(root)
    _need(MANIFEST in tree, 'Missing literal-input manifest')
    report = _json(tree[MANIFEST])
    _need(isinstance(report,dict) and type(report.get('schema_version')) is int
          and report['schema_version'] == 1 and report.get('policy_id') in {POLICY_ID,SOURCE_POLICY_ID},
          'Unsupported literal-input artifact')
    if report['policy_id']==POLICY_ID:
        expected,files=_payload(root/'model.pdb',root/'native/native_receipt.json')
    else:
        from .cif_explicit_na_policy import _CODE
        originals=report.get('original_phils');sources=report.get('source_components')
        _need(isinstance(originals,list) and 1 <= len(originals) <= 63
              and isinstance(sources,dict) and sources
              and all(isinstance(c,str) and _CODE.fullmatch(c) for c in sources),
              'Invalid source literal input inventory')
        names=[f'original/{i:03}.phil' for i in range(len(originals))]
        _need(all(name in tree and ref==_ref(name,tree[name]) for name,ref in zip(names,originals))
              and all(f'sources/{c}.cif' in tree and ref==_ref(f'sources/{c}.cif',tree[f'sources/{c}.cif'])
                      for c,ref in sources.items()),'Source literal operational references differ')
        expected,files=_source_payload(root/'model.pdb',[root/n for n in names],
            {c:root/'sources'/f'{c}.cif' for c in sources})
    _need(_bytes(report) == _bytes(expected) and {n:b for n,b in tree.items() if n != MANIFEST} == files,
          'Literal input/compiler reconstruction differs')
    _need(_exact_tree(root) == tree, 'Literal input changed while reading')
    return report


def resolve_literal_na_inputs(directory):
    """Resolve only the model and ordered compiled PHIL proven by reconstruction."""
    root = Path(directory).absolute(); report = read_literal_na_inputs(root)
    return dict(report=report, model=root/report['model']['path'],
                phils=[root/row['path'] for row in report['compiled_phils']])


def _source_payload(model, phils, sources):
    from .cif_na_policy import _compile_source_na_policy_payload
    _need(isinstance(phils,(list,tuple)) and 1 <= len(phils) <= 63,
          'Require one to 63 original ordered PHIL inputs')
    _need(isinstance(sources,dict) and sources, 'Require explicit source component graphs')
    original=_read(model); original_phils=[_read(p) for p in phils]
    original_sources={code:_read(p) for code,p in sources.items()};pins=_implementation()
    compilation,compiled,source_data=_compile_source_na_policy_payload(model,phils,sources)
    _need(source_data==original_sources,'Source component changed during literal compilation')
    order=[*compilation['retained_phils'],compilation['compiled_phil']]
    context=_derive_restraint_payload(model,[compiled[n] for n in order],require_scoped_names=True)
    files={'model.pdb':original,**{f'original/{i:03}.phil':data for i,data in enumerate(original_phils)},
           **{f'sources/{code}.cif':data for code,data in source_data.items()},
           **{'compiled/'+n:data for n,data in compiled.items()}}
    report=dict(schema_version=1,policy_id=SOURCE_POLICY_ID,status='FROZEN_LITERAL_INPUTS',
        index_basis='PDB_RECORD_ORDER; NOT_NATIVE_CAPTURE_INDICES',model=_ref('model.pdb',original),
        original_phils=[_ref(f'original/{i:03}.phil',data) for i,data in enumerate(original_phils)],
        source_components={code:_ref(f'sources/{code}.cif',data) for code,data in sorted(source_data.items())},
        compiled_phils=[_ref('compiled/'+n,compiled[n]) for n in order],
        implementation=pins,compilation=compilation,restraint_context=context,
        files=[_ref(n,data) for n,data in sorted(files.items())],
        native_membership='NOT_ASSESSED_FOR_COMPILED_INPUTS',automatic_adoption=False,
        scientific_approval='NOT_RUN',model_optimization='NOT_RUN',refinement='NOT_RUN')
    _need(_read(model)==original and [_read(p) for p in phils]==original_phils
          and {c:_read(p) for c,p in sources.items()}==source_data and _implementation()==pins,
          'Source literal input or compiler changed during compilation')
    return report,files


def prepare_source_literal_na_inputs(model, phils, sources, output):
    """Freeze source-bound literal compilation without requiring native capture.

    Uses the existing C21 parser/emitter and C80 actual/source NAR role checks.
    Preserves original order, explicit edits and planes; never guesses pairs or
    fabricates native identities. Source graphs must be readable and consistent.
    Numerical/chemical usability and native membership remain unassessed.
    """
    root=_root(output)
    if root.exists():raise FileExistsError(root)
    _need(isinstance(phils,(list,tuple)) and isinstance(sources,dict), 'Require ordered PHIL and source mapping')
    inputs=[Path(model),*map(Path,phils),*map(Path,sources.values())]
    _need(all(not p.absolute().is_relative_to(root) for p in inputs), 'Source literal output overlaps its inputs')
    report,files=_source_payload(model,phils,sources)
    _write_payload(root,report,files)
    _need(read_literal_na_inputs(root)==report,'Frozen source literal replay differs')
    fresh,original_files=_source_payload(model,phils,sources)
    _need(fresh==report and original_files==files,'Source literal input changed while freezing')
    return report
