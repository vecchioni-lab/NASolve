"""Freeze original literal NA intent and replay the maintained C21 compiler.

This is an input/provenance artifact, not a native qualification or execution
owner. Native capture supplies identities; compiled inputs still need independent
native validation in the selected dictionary/model context.
"""
from pathlib import Path

from .cif_attachment_native import _capture, _native_atoms
from .cif_catalogue import _digest
from .cif_component_runtime import _tree
from .cif_dictionary_sites import _need, _read
from .cif_dictionary_store import _bytes, _json
from .cif_explicit_na_policy import _implementation
from .cif_na_policy import _compile_na_policy_payload, _parse, _path, _resolve
from .cif_repair_attempt import _root
from .cif_restraint_context import _derive_restraint_payload

POLICY_ID = 'cif-literal-na-inputs-v1'
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
    # Legacy context v1 remains byte-compatible. This new conversion contract
    # rejects ambiguous boolean alternatives before introducing derived inputs.
    for data in compiled.values():
        for node in _parse(data.decode('utf-8'))[0]:
            if _path(node) == 'geometry_restraints.edits.parallelity':
                for key in ('atom_selection_1','atom_selection_2'):
                    _resolve(node['fields'][key], native['atoms'], require_scoped_names=True)
    context = _derive_restraint_payload(model, [compiled[n] for n in order])
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
    root.mkdir(parents=True, exist_ok=False)
    for name,data in sorted(files.items()):
        path = root/name; path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as handle: handle.write(data)
    with (root/MANIFEST).open('xb') as handle: handle.write(_bytes(report))
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
          and report['schema_version'] == 1 and report.get('policy_id') == POLICY_ID,
          'Unsupported literal-input artifact')
    expected, files = _payload(root/'model.pdb',root/'native/native_receipt.json')
    _need(_bytes(report) == _bytes(expected) and {n:b for n,b in tree.items() if n != MANIFEST} == files,
          'Literal input/compiler reconstruction differs')
    _need(_exact_tree(root) == tree, 'Literal input changed while reading')
    return report


def resolve_literal_na_inputs(directory):
    """Resolve only the model and ordered compiled PHIL proven by reconstruction."""
    root = Path(directory).absolute(); report = read_literal_na_inputs(root)
    return dict(report=report, model=root/report['model']['path'],
                phils=[root/row['path'] for row in report['compiled_phils']])
