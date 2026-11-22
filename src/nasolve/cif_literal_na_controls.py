"""Capture-bound reader controls for researcher inspection, never execution.

Only the reviewed False-valued sorting/CDL/full-monomer reader controls are
accepted. The literal compiler is unchanged; no control is silently discarded.
"""
from pathlib import Path
import re

from .cif_dictionary_sites import _need, _read
from .cif_explicit_na_policy import _implementation
from .cif_literal_na_inputs import (_captured_source, _exact_tree, _ref,
    _write_payload, read_literal_na_inputs)
from .cif_na_policy import _compile_na_policy_payload
from .cif_interpretation_controls import CONTROLS, DICTIONARY_PARENT_POLICY_ID, control_definitions
from .cif_repair_attempt import _root
from .cif_restraint_context import _derive_restraint_payload

POLICY_ID = 'cif-typed-native-literal-inputs-v1'


def _control_values(data, adaptation, seen):
    values, mappings = control_definitions(data, seen)
    _need(adaptation.get('policy') in {'direct', 'refinement-root-to-interpreter-v1'},
          'Unsupported native control namespace policy')
    if adaptation['policy'] == 'direct':
        _need(all(row['source'] == row['interpreter'] for row in mappings),
              'Direct native control namespace differs')
    captured = adaptation.get('field_mapping')
    _need(isinstance(captured, list) and len(captured) == len(mappings)
          and all(isinstance(row, dict) and row in mappings for row in captured)
          and all(captured.count(row) == 1 for row in mappings)
          and type(adaptation.get('definitions_preserved')) is int
          and adaptation['definitions_preserved'] == len(mappings),
          'Native control definition readback differs')
    return values


def _typed_payload(model, native_receipt, phil_roles, expected_receipt_sha256, *, source_policy=POLICY_ID):
    _need(source_policy in (POLICY_ID, DICTIONARY_PARENT_POLICY_ID), 'Unsupported typed source policy')
    model = Path(model).absolute(); native_receipt = Path(native_receipt).absolute()
    original, tree, receipt, native, names = _captured_source(model, native_receipt)
    receipt_ref = _ref('native/native_receipt.json', tree['native_receipt.json'])
    _need(isinstance(expected_receipt_sha256, str)
          and re.fullmatch('[0-9a-f]{64}', expected_receipt_sha256)
          and receipt_ref['sha256'] == expected_receipt_sha256, 'Native receipt pin differs')
    rows = [row for row in receipt['inputs'] if row['role'] == 'phil']
    _need(isinstance(phil_roles, list) and len(phil_roles) == len(rows),
          'Require exact ordered PHIL roles')
    literals = []; controls = []; seen = set()
    adaptations = native.get('phil_adaptations', [])
    for row, role, adaptation in zip(rows, phil_roles, adaptations):
        _need(isinstance(role, dict) and set(role) == {'input_index', 'role', 'sha256'}
              and type(role['input_index']) is int and role['input_index'] == row['input_index']
              and role['sha256'] == row['sha256']
              and isinstance(role['role'], str)
              and role['role'] in {'literal_restraints', 'interpretation_controls'},
              'Ordered PHIL role or digest differs')
        if role['role'] == 'literal_restraints':
            literals.append(row['path'])
        else:
            _need(adaptation.get('policy') == receipt.get('phil_namespace_policy'),
                  'Native control namespace differs from capture policy')
            values = _control_values(tree[row['path']], adaptation, seen)
            controls.append(dict(input_index=row['input_index'],
                input=_ref('native/'+row['path'], tree[row['path']]), values=values,
                native_definition_readback=adaptation))
    if source_policy == DICTIONARY_PARENT_POLICY_ID:
        _need(controls and not literals and seen == CONTROLS,
              'A dictionary parent requires exactly the four reader controls and no literal restraint inputs')
        _need(receipt['dictionary_source_policy'] == 'INSTALLED_LIBRARY_ONLY'
              and native['geometry'].get('custom_proxy_requests') == [],
              'A dictionary parent requires the installed library and no custom geometry edits')
        pins = compilation = context = None
        compiled, order = {}, []
    else:
        _need(literals and controls, 'Require both literal restraint and interpretation control roles')
        pins = _implementation()
        compilation, compiled = _compile_na_policy_payload(model,
            [native_receipt.parent/name for name in literals], native)
        order = [*compilation['retained_phils'], compilation['compiled_phil']]
        context = _derive_restraint_payload(model, [compiled[n] for n in order], require_scoped_names=True)
    files = {'model.pdb': original, **{'native/'+n:b for n,b in tree.items()},
             **{'compiled/'+n:b for n,b in compiled.items()}}
    report = dict(schema_version=1, policy_id=source_policy,
        status='FROZEN_DICTIONARY_PARENT' if compilation is None else 'FROZEN_LITERAL_INPUTS',
        index_basis='NATIVE_CAPTURE_INDICES', model=_ref('model.pdb', original),
        native_receipt=receipt_ref, phil_roles=phil_roles,
        original_phils=[_ref('native/'+n, tree[n]) for n in names],
        captured_controls=controls, compiled_phils=[_ref('compiled/'+n, compiled[n]) for n in order],
        implementation=pins, compilation=compilation, restraint_context=context,
        execution_context=dict(status='REQUIRES_CONTROL_AWARE_OWNER', ordinary_handoff_allowed=False),
        files=[_ref(n,b) for n,b in sorted(files.items())],
        native_membership='ORIGINAL_OBSERVATION_ONLY' if compilation is None else 'NOT_ASSESSED_FOR_COMPILED_INPUTS',
        automatic_adoption=False,
        scientific_approval='NOT_RUN', model_optimization='NOT_RUN', refinement='NOT_RUN')
    _need(_read(model) == original and _exact_tree(native_receipt.parent) == tree
          and (pins is None or _implementation() == pins), 'Typed input or compiler changed during compilation')
    return report, files


def prepare_typed_literal_na_inputs(model, native_receipt, output, *, phil_roles,
                                   expected_receipt_sha256, source_policy=POLICY_ID):
    """Freeze an explicit geometry source and its observed reader controls."""
    root = _root(output)
    if root.exists(): raise FileExistsError(root)
    capture_root = Path(native_receipt).absolute().parent
    _need(not root.is_relative_to(capture_root) and not capture_root.is_relative_to(root)
          and not Path(model).absolute().is_relative_to(root), 'Typed output overlaps its inputs')
    report, files = _typed_payload(model, native_receipt, phil_roles, expected_receipt_sha256,
                                   source_policy=source_policy)
    _write_payload(root, report, files)
    _need(read_literal_na_inputs(root) == report, 'Typed literal replay differs')
    fresh, fresh_files = _typed_payload(model, native_receipt, phil_roles, expected_receipt_sha256,
                                        source_policy=source_policy)
    _need(fresh == report and fresh_files == files, 'Typed source changed while freezing')
    return report


def inspect_typed_literal_na_inputs(directory, *, source_policy=POLICY_ID):
    """Expose separate inspected inputs; this is not an executable PHIL list."""
    root = Path(directory).absolute(); report = read_literal_na_inputs(root)
    _need(source_policy in (POLICY_ID, DICTIONARY_PARENT_POLICY_ID) and report['policy_id'] == source_policy,
          'Require the explicitly requested typed native source')
    return dict(report=report, model=root/report['model']['path'],
        compiled_restraint_phils=[root/ref['path'] for ref in report['compiled_phils']],
        interpretation_control_phils=[root/row['input']['path'] for row in report['captured_controls']],
        execution_context=report['execution_context'])
