"""Read a site-only local-fit recipe from the exact preparation Phenix interpreted."""
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .cif_attachment_native import _capture
from .cif_component_runtime import component_runtime_evidence
from .cif_dictionary_sites import _bind_capture_input_pins, _need, _read
from .cif_furanose_bridge import read_fitted_furanose_model
from .cif_linked_preparation import _selection
from .cif_ordinary_postmr import _read_ordinary_postmr_result


@dataclass(frozen=True, repr=False)
class FuranoseFitInputs:
    """Verified input bytes survive temporary expansion of compact preparation evidence."""
    seed_directory: Path
    site: str
    code: str
    model: bytes
    dictionaries: tuple[bytes, ...]
    interpreted_phils: tuple[bytes, ...]
    minimization_phil: bytes
    result_sha256: str
    native_receipt_sha256: str
    native_parameter_count: int
    requested_restraints: tuple[tuple[str, int], ...]
    consumer: dict


def interpreted_geometry_phils(directory, receipt, native, snapshots):
    """Take each native-written PHIL from the verified receipt in its original order."""
    inputs = [row for row in receipt['inputs'] if row['role'] == 'phil']
    mappings = native.get('phil_adaptations')
    _need(native.get('status') == 'REVIEW' and native.get('unused_definitions') == []
          and isinstance(mappings, list) and len(mappings) == len(inputs) > 0,
          'Local fit requires the complete native interpretation of all selected PHIL files')
    phils = []
    total = 0
    for i, (row, mapped) in enumerate(zip(inputs, mappings)):
        name = f'canonical_{i:03d}.phil'
        _need(isinstance(mapped, dict), 'Invalid native PHIL file mapping')
        definitions = mapped.get('field_mapping')
        _need(mapped.get('input') == row['path'] and mapped.get('canonical') == name
              and mapped.get('policy') == 'refinement-root-to-interpreter-v1'
              and isinstance(definitions, list) and type(mapped.get('definitions_preserved')) is int
              and len(definitions) == mapped['definitions_preserved']
              and definitions and directory/name in snapshots, 'Native PHIL mapping or preserved output differs')
        for definition in definitions:
            _need(isinstance(definition, dict), 'Invalid native PHIL field mapping')
            source = definition.get('source')
            field = definition.get('interpreter')
            _need(isinstance(source, str) and field == source.removeprefix('refinement.')
                  and field.startswith(('geometry_restraints.', 'pdb_interpretation.')),
                  'A native geometry input would change local-fit controls or its parameter namespace')
        phils.append(snapshots[directory/name])
        total += len(definitions)
    return tuple(phils), total


def read_furanose_fit_inputs(run_directory, *, attempt_number):
    """Bind a checked unrelaxed sugar to the native geometry files for the selected model.

    The geometry dispatcher can use the interpreter's own normalized PHIL files
    directly. The parent coordinate records are used only when every named atom
    still has the original position, occupancy and displacement.
    """
    checked, exact = _read_ordinary_postmr_result(run_directory, attempt_number=attempt_number)
    return fit_inputs_from_checked(checked, exact)[0]


def fit_inputs_from_checked(checked, exact):
    """Read the inputs and parent geometry from one authenticated preparation."""
    sugar = (exact.get('construction_inputs') or {}).get('furanose_substitution') or {}
    folders = {'readyset_checked_model':'endpoint', 'readyset_ordered_checked_model':'endpoint',
               'verified_parent_runtime':'baseline'}
    _need(sugar.get('unfitted_pairing_edge_seed') is True and exact.get('continuation') is not None
          and checked.selected in folders, 'Require a checked native preparation with a pending local sugar fit')
    runtime = exact['runtime']
    manifest = runtime['manifest']
    folder = folders[checked.selected]
    name = f'evidence/{folder}/native_receipt.json'
    _need(manifest['source_selection'].get(folder+'_receipt') == name, 'Selected native receipt differs')
    seed = sugar['model'].parent
    clean, comparison = read_fitted_furanose_model(seed, runtime['model'])
    _need(comparison['max_selected_displacement_A'] == 0 and clean == _read(sugar['model']),
          'Selected preparation changed the local sugar starting coordinates')
    model = _read(runtime['model'])
    _need(sha256(model).hexdigest() == comparison['return_sha256'], 'Checked model changed during fit planning')
    dictionaries = tuple(_read(p) for p in runtime['dictionaries'])
    phils = tuple(_read(p) for p in runtime['phils'])
    inputs = [('model', model), *(('dictionary', d) for d in dictionaries), *(('phil', p) for p in phils)]
    with component_runtime_evidence(runtime['manifest_path'].parent, manifest, subtree=folder) as view:
        path = (view/name).resolve(strict=True)
        record, native, snapshots = _capture(path, model)
        _bind_capture_input_pins(record, [(role, sha256(data).hexdigest(), len(data)) for role, data in inputs])
        _need(record['execution']['status'] == 'COMPLETED' and record['execution']['returncode'] == 0,
              'Local fit needs a completed native interpretation')
        interpreted, count = interpreted_geometry_phils(path.parent, record, native, snapshots)
        digest = sha256(snapshots[path]).hexdigest()
        restraints = Counter(row['kind'] for row in native['geometry']['custom_proxy_requests'])
    site, code = sugar['context']['site'], sugar['code']
    controls = (f'selection = {_selection(site, code)}\n'
                'write_geo_file = True\nfix_rotamer_outliers = False\n'
                'minimization.macro_cycles = 3\nminimization.max_iterations = 250\n'
                'output_file_name_prefix = relaxed\n').encode()
    plan = FuranoseFitInputs(seed, site, code, clean, dictionaries, interpreted, controls,
        exact['result']['record_sha256'], digest, count, tuple(sorted(restraints.items())),
        sugar['snapshot']['manifest']['consumer'])
    return plan, native
