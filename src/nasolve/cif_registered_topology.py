"""Keep checked crystal partners explicit when publishing an original model.

This is identity/frame validation, not an assertion that symmetry forces were
applied. Frozen sources use run anchors; descendants reuse the registered graph
and named-atom frame transfer rather than discovering a new nearest partner.
"""
from copy import deepcopy
from pathlib import Path

from .cif_dictionary_sites import _need, _read
from .cif_model_context import _intent
from .cif_registered_preparation_input import FILES, ROLE, read_registered_backbone

POLICY_ID = 'registered-prepared-model-topology-v1'
_IMAGE_FIELDS = ('id', 'logical_o3_site', 'logical_phosphate_site', 'o3_site',
                 'phosphate_site', 'o3_image', 'target_operator_xyz')


def _shape(context):
    return deepcopy(dict(components=context['components'], intent=context['intent'],
        contexts=context['site_contexts'], local_links=context['local_links'],
        image_links=[{k:row[k] for k in _IMAGE_FIELDS} for row in context['image_links']],
        protected_terminal_phosphates=context['protected_terminal_phosphates']))


def publication_topology(run, checked, exact, config):
    """Project only the complete owner's verified unchanged registered selection."""
    from .cif_registered_execution import POLICY_ID as EXECUTION_POLICY
    from .cif_registered_preparation_native import RUNTIME_POLICY_ID
    from .checkpoints import _file_reference
    review=exact.get('registered_runtime_review')
    _need(config.get('registered_execution_policy') == EXECUTION_POLICY
          and exact['result'].get('registered_execution_policy') == EXECUTION_POLICY
          and checked.selected == 'verified_prepared_bundle'
          and isinstance(review,dict) and review.get('policy_id') == RUNTIME_POLICY_ID
          and review.get('status') == 'REGISTERED_ORIGINAL_RUNTIME_FOR_REVIEW',
          'Registered publication requires the qualified original execution result')
    inputs=checked.request_directory/'inputs'; model=inputs/'model.pdb'
    _need(_read(checked.model_path) == _read(model), 'Registered publication requires the unchanged original model')
    _,context=read_registered_backbone(model,sorted(config['components']),inputs,config['registered_backbone'])
    native=review.get('native_input_review')
    keys=('model_sha256','components','local_links','image_links','protected_terminal_phosphates')
    _need(isinstance(native,dict) and all(native.get(k) == context[k] for k in keys),
          'Registered native review differs from the publication topology')
    sources={key:_file_reference(path,run) for key,path in dict(model=model,
        **{k:inputs/ROLE/name for k,name in FILES.items()}).items()}
    _need(all(row['anchor']=='run' for row in sources.values()), 'Registered sources require run anchors')
    return dict(schema_version=1,policy_id=POLICY_ID,**_shape(context),sources=sources,
                registered_backbone=deepcopy(config['registered_backbone']))


def validate_registered_model_topology(model, record, report, *, run_directory):
    """Validate a same-frame descendant against immutable registered sources."""
    from .checkpoints import _ref_path, CheckpointError
    from .cif_ordinary_postmr import _ordinary_request_directory
    from .cif_registered_preparation_context import derive_registered_preparation_context
    _need(run_directory is not None, 'Registered topology requires an explicit run anchor')
    _need(isinstance(record,dict) and type(record.get('schema_version')) is int
          and record['schema_version']==1 and record.get('policy_id')==POLICY_ID,
          'Unsupported registered preparation topology')
    run=Path(run_directory).expanduser().resolve(); inputs=_ordinary_request_directory(run)/'inputs'
    refs=record.get('sources')
    _need(isinstance(refs,dict) and set(refs)=={'model',*FILES}, 'Incomplete registered topology sources')
    paths={}
    for key,ref in refs.items():
        _need(isinstance(ref,dict) and ref.get('anchor')=='run', 'Registered topology needs run-anchored sources')
        try:
            path=_ref_path(ref,'registered '+key,run)
        except CheckpointError as exc:
            raise ValueError(str(exc)) from exc
        expected=inputs/'model.pdb' if key=='model' else inputs/ROLE/FILES[key]
        _need(path==expected.resolve(), 'Registered topology source differs from its frozen request role')
        paths[key]=path
    originals={k:_read(p) for k,p in paths.items()}
    _,context=read_registered_backbone(paths['model'],record.get('components'),inputs,record.get('registered_backbone'))
    expected=dict(schema_version=1,policy_id=POLICY_ID,**_shape(context),sources=refs,
                  registered_backbone=record['registered_backbone'])
    _need(record==expected and _intent(report)==context['intent'],
          'Registered topology or chemical intent differs from frozen sources')
    current=derive_registered_preparation_context(model,context['intent'],context['components'],
        **{key:paths[key] for key in FILES})
    _need(_shape(current)==_shape(context), 'Model identities or registered phosphate partners changed; review required')
    _need(all(_read(paths[k])==raw for k,raw in originals.items()), 'Registered topology sources changed during validation')
    return dict(current['phosphate_audit'], registered_image_links=current['image_links'],
                registered_topology_policy=POLICY_ID, native_image_forces='NOT_ASSESSED')
