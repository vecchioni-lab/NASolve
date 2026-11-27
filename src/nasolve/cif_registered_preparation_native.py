"""Join frozen registered input to an exact, already recorded native interpretation.

No process, preparation child, producer ancestry, image force or publication is
authorized by this read. The complete-request intake remains execution-held.
"""
from hashlib import sha256
from pathlib import Path

from .cif_dictionary_sites import _need, _read
from .cif_model_context import _local_backbone
from .cif_phosphate_continuation import (
    RegisteredContinuation, _inherit_measured, inspect_registered_backbone,
)
from .cif_registered_preparation_input import FILES, ROLE, read_registered_backbone

POLICY_ID = 'registered-native-input-review-v1'


def review_registered_native_input(inputs, components, reference, *, native_receipt,
                                   dictionaries, supplementary_phils):
    """Read the frozen model/graph and exact native model/CIF/ordered PHIL inputs.

    All paths are explicit. The returned native-directory references belong to
    the supplied receipt; callers must retain that receipt's anchored closure.
    Dictionaries and supplementary_phils name the complete original input lists,
    including any declared terminal protection. No suffix discovery or implicit
    PHIL conversion is performed. Native reference terms describe intact local
    bonds; this review does not assert those forces were applied across symmetry.
    """
    inputs = Path(inputs); model = inputs/'model.pdb'
    _need(isinstance(dictionaries, (list, tuple)) and isinstance(supplementary_phils, (list, tuple)),
          'Native inputs require ordered dictionary and PHIL lists')
    ordered = [('model', model), *[('dictionary', Path(p)) for p in dictionaries],
               *[('phil', Path(p)) for p in supplementary_phils]]
    paths = [p for _,p in ordered]
    _need(len({p.absolute() for p in paths}) == len(paths), 'Native inputs must be distinct')
    original = {p:_read(p) for p in paths}
    receipt = Path(native_receipt); receipt_bytes = _read(receipt)
    view, context = read_registered_backbone(model, components, inputs, reference)
    role = inputs/ROLE
    source = role/FILES['registration_model']
    registered = tuple(role/FILES[k] for k in ('registration','discovery','continuations'))
    observed = inspect_registered_backbone(source, *registered)
    if _read(source) != original[model]:
        observed = [_inherit_measured(source, model,
            RegisteredContinuation(row['registered_continuation']['continuation_id'], *registered), row)
            for row in observed]
    local = _local_backbone(model, context['intent'], context['components'], review_open=True)
    from .cif_prepared_backbone import _native_candidate
    native = _native_candidate(model, model, receipt, registered, observed, local,
                               context['intent'], context['components'])
    expected = [dict(role=kind, sha256=sha256(original[p]).hexdigest(), size=len(original[p]))
                for kind,p in ordered]
    actual = [{k:row[k] for k in ('role','sha256','size')} for row in native['native_inputs']]
    _need(actual == expected, 'Native dictionaries, model or ordered restraint inputs differ')
    _need(native['native_receipt_sha256'] == sha256(receipt_bytes).hexdigest()
          and native['candidate_model_sha256'] == context['model_sha256'],
          'Native receipt or model changed during registered input review')
    _need(all(_read(p) == raw for p,raw in original.items()) and _read(receipt) == receipt_bytes,
          'Native input changed during registered review')
    final_view, final_context = read_registered_backbone(model, components, inputs, reference)
    _need(final_view == view and final_context == context, 'Registered inputs changed during native review')
    return dict(schema_version=1, policy_id=POLICY_ID,
        status='REGISTERED_NATIVE_INPUTS_VERIFIED_FOR_REVIEW', registered_backbone=dict(reference),
        model_sha256=context['model_sha256'], source_model_sha256=context['source_model_sha256'],
        components=context['components'], contexts=view['contexts'], local_links=context['local_links'],
        image_links=context['image_links'], protected_terminal_phosphates=context['protected_terminal_phosphates'],
        native=native, construction_provenance='NOT_ASSESSED', native_image_forces='NOT_ASSESSED',
        ordinary_admission=False, refinement='NOT_RUN', scientific_qualification='NOT_ASSESSED')
