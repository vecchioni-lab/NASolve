"""Read-only checkpoint binding for an existing registered bend preview.

This is input admission, not a run lock, native chemistry check or dispatcher.
The executor must re-read at dispatch and consume frozen inputs under its own
ownership protocol. No registry, model or current selection is written here.
"""
from hashlib import sha256
from pathlib import Path
import re

from . import checkpoints
from .topostitch_endpoint import audit_masked_endpoint
from .topostitch_preview import _json, load_bend_motion
from .topostitch_recipe import recipe_digest


def _pin(value):
    if not isinstance(value,str) or re.fullmatch('[0-9a-f]{64}',value) is None:
        raise ValueError('Require an exact lowercase SHA-256 binding')
    return value


def _reference(value):
    # The existing resolver owns containment and checksum verification. This
    # first caller requires saved relative references; it does not migrate old
    # registries or infer authority for an unavailable phase/restraint input.
    if (not isinstance(value,dict) or value.get('anchor') not in ('run','dataset','repository')
            or not isinstance(value.get('relative_path'),str) or not value['relative_path']
            or not isinstance(value.get('sha256'),str)
            or re.fullmatch('[0-9a-fA-F]{64}',value['sha256']) is None
            or type(value.get('size')) is not int or value['size']<0):
        raise ValueError('Require complete anchored checkpoint input references')
    return {k:value[k] for k in ('anchor','relative_path','sha256','size')}


def _snapshot(run_directory, checkpoint, expected_checkpoint_id, preview_pin):
    registry_path=checkpoints.registry_path(Path(run_directory))
    run=registry_path.parent.parent
    report_path=run/'report.json'
    report_bytes=report_path.read_bytes()
    registry_bytes=registry_path.read_bytes()  # Deliberately require a saved registry.
    resolved,registry=checkpoints.read_registry(run)
    if (resolved!=run or registry!=_json(registry_bytes)
            or type(registry.get('schema_version')) is not int or registry['schema_version']!=2):
        raise ValueError('Require an unchanged saved schema-2 checkpoint registry')
    parent=checkpoints.resolve_checkpoint(registry,checkpoint)
    if parent.get('id')!=expected_checkpoint_id:
        raise ValueError('Selected checkpoint identity differs from the requested parent')
    if (sum(isinstance(row,dict) and row.get('id')==expected_checkpoint_id for row in registry['checkpoints'])!=1
            or parent.get('usable') is not True):
        raise ValueError('Require one unambiguous reusable checkpoint parent')
    restraints=parent.get('restraints')
    if not isinstance(restraints,list):
        raise ValueError('Require the complete ordered checkpoint restraint list')
    references=[('model',_reference(parent.get('model'))),('observations',_reference(parent.get('observations')))]
    if parent.get('phases') is not None:references.append(('phases',_reference(parent['phases'])))
    references.extend(('restraint',_reference(row)) for row in restraints)
    inherited=checkpoints.inherited_paths(parent,run)
    paths=[inherited['model'],inherited['observations']]
    if parent.get('phases') is not None:paths.append(inherited['phases'])
    paths.extend(inherited['restraints'])
    if len(paths)!=len(references) or any(not isinstance(p,Path) for p in paths):
        raise ValueError('Missing declared checkpoint input')
    if any(p.stat().st_size!=ref['size'] for p,(_,ref) in zip(paths,references)):
        raise ValueError('Checkpoint input size differs from its frozen reference')
    model_bytes=inherited['model'].read_bytes()
    if sha256(model_bytes).hexdigest()!=parent['model']['sha256'].lower():
        raise ValueError('Checkpoint model changed while reading its snapshot')
    if registry_path.read_bytes()!=registry_bytes or report_path.read_bytes()!=report_bytes:
        raise ValueError('Checkpoint metadata changed during admission')
    context=dict(schema_version=1,kind='topostitch-checkpoint-input-context',
        checkpoint_id=expected_checkpoint_id,selection=dict(mode='current' if checkpoint is None else 'explicit',requested=checkpoint),
        registry_sha256=sha256(registry_bytes).hexdigest(),report_sha256=sha256(report_bytes).hexdigest(),
        parent_record_sha256=recipe_digest(parent),source_model_sha256=sha256(model_bytes).hexdigest(),
        preview_receipt_sha256=preview_pin,inputs=[dict(role=role,**ref) for role,ref in references])
    return context,model_bytes


def load_checkpoint_bend_motion(run_directory, preview_directory, *, expected_checkpoint_id,
        expected_receipt_sha256, checkpoint=None, expected_checkpoint_context_sha256=None):
    """Return ``(motion, parameters, binding)`` for one exact saved parent.

    ``checkpoint=None`` reads the current selection; an explicit checkpoint or
    bookmark uses the existing resolver and must resolve to the expected ID.
    Supply the returned ``context_sha256`` on a subsequent call at dispatch to
    refuse changed selections, metadata or inherited input declarations. Every
    call rechecks inherited file hashes and replays the pinned preview.

    Scope: saved schema-2 registry, complete anchored inputs and the existing
    strict canonical coordinate-only endpoint policy. This neither authenticates
    intended native topology nor validates a thermal model, Free-R semantics or
    checkpoint execution history. It supplies no atomic locking/dispatch promise.
    """
    preview_pin=_pin(expected_receipt_sha256)
    if expected_checkpoint_context_sha256 is not None:_pin(expected_checkpoint_context_sha256)
    if (not isinstance(expected_checkpoint_id,str) or not expected_checkpoint_id.strip()
            or checkpoint is not None and (not isinstance(checkpoint,str) or not checkpoint.strip())):
        raise ValueError('Require an explicit expected checkpoint identity')
    before,source=_snapshot(run_directory,checkpoint,expected_checkpoint_id,preview_pin)
    context_digest=recipe_digest(before)
    if expected_checkpoint_context_sha256 is not None and context_digest!=expected_checkpoint_context_sha256:
        raise ValueError('Checkpoint context changed since the motion was bound')
    motion,parameters=load_bend_motion(preview_directory,
        expected_receipt_sha256=preview_pin,parent_model_bytes=source)
    candidate=(Path(preview_directory)/'candidate.pdb').read_bytes()
    points=motion.mask.expand(motion.displacements(parameters))
    endpoint=audit_masked_endpoint(source,candidate,points,movable_indices=motion.mask.indices,
                                   max_displacement_angstrom=motion.mask.max_displacement_angstrom)
    after,latest=_snapshot(run_directory,checkpoint,expected_checkpoint_id,preview_pin)
    if after!=before or latest!=source:
        raise ValueError('Checkpoint inputs or selection changed during preview admission')
    return motion,parameters,dict(schema_version=1,kind='topostitch-checkpoint-motion-binding',
        context=before,context_sha256=context_digest,endpoint=endpoint,
        runtime_authority=False,locking=False,scientific_acceptance=False)
