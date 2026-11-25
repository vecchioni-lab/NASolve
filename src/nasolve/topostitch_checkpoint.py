"""Read-only checkpoint inputs, with optional binding to a registered bend preview.

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


def _snapshot(run_directory, checkpoint, expected_checkpoint_id, preview_pin, *, registry_reader=None):
    registry_path=checkpoints.registry_path(Path(run_directory))
    run=registry_path.parent.parent
    report_path=run/'report.json'
    report_bytes=report_path.read_bytes()
    registry_bytes=registry_path.read_bytes()  # Deliberately require a saved registry.
    reader=checkpoints.read_registry if registry_reader is None else registry_reader
    resolved,registry=reader(run)
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



def inspect_checkpoint_inputs(run_directory, *, expected_checkpoint_id,
        expected_model_sha256, registry_reader, checkpoint=None, expected_context_sha256=None):
    """Observe one saved parent's exact inputs without requiring a bend preview.

    ``registry_reader`` is an explicit trusted dependency with Cedar's
    ``read_registry`` contract; it must authenticate supported history or raise.
    It is executable application code, never an artifact-supplied callback.
    This adapter pins its returned registry to the actual saved bytes and reuses
    the existing anchored input resolver. Schema 2 only; no migration is implied.

    A refined descendant may be observed without calling it an original checked
    preparation or admitting its chemistry, thermal model, Free-R interpretation,
    recut, deformation or next native restart. An unusable or unexpected selected
    parent is refused. An explicit checkpoint leaves current selection alone.
    The returned digest can pin a later observation. Two snapshots detect drift;
    the execution owner must still revalidate and own input lifetime at dispatch.
    """
    model_pin=_pin(expected_model_sha256)
    if expected_context_sha256 is not None:_pin(expected_context_sha256)
    if not callable(registry_reader):
        raise ValueError('Require an explicit trusted registry reader')
    if (not isinstance(expected_checkpoint_id,str) or not expected_checkpoint_id.strip()
            or checkpoint is not None and (not isinstance(checkpoint,str) or not checkpoint.strip())):
        raise ValueError('Require an explicit expected checkpoint identity')

    def read():
        context,source=_snapshot(run_directory,checkpoint,expected_checkpoint_id,None,
                                 registry_reader=registry_reader)
        if sha256(source).hexdigest()!=model_pin:
            raise ValueError('Checkpoint model differs from the expected source bytes')
        # No invented preview receipt or original-preparation claim.
        context.pop('preview_receipt_sha256')
        return context,source

    before,source=read()
    pin=recipe_digest(before)
    if expected_context_sha256 is not None and pin!=expected_context_sha256:
        raise ValueError('Checkpoint input context changed since the previous read')
    after,latest=read()
    if before!=after or source!=latest:
        raise ValueError('Checkpoint inputs or selection changed during observation')
    return dict(schema_version=1,kind='topostitch-checkpoint-input-observation',
        context=before,context_sha256=pin,
        history_validation='DELEGATED_TO_EXPLICIT_REGISTRY_READER',
        runtime_authority=False,chemical_admission=False,motion_admission=False,
        native_restart_qualified=False,selection_applied=False,locking=False,
        scientific_acceptance=False)

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


def load_execution_bend_motion(run_directory, preview_directory, *, expected_checkpoint_id,
        expected_receipt_sha256, expected_checkpoint_context_sha256, execution_reference,
        child_checkpoint_id, request_model_role, generated_parameters, checkpoint=None,
        additional_restraints=(), refinement_input_reference=None, execution_reader=None,
        refinement_input_reader=None, expected_execution_context_sha256=None):
    """Join a checked preview/parent to an existing immutable execution request.

    The caller explicitly distinguishes an unchanged ``parent`` input from the
    exact serialized preview ``candidate``. Neither result grants native transfer
    or launch authority. Default readers belong to Cedar; an explicitly supplied
    trusted reader permits branch compatibility checks without copying its code.
    Generated round parameters are a separate input, never inherited restraints.
    """
    _pin(expected_checkpoint_context_sha256)
    if expected_execution_context_sha256 is not None:_pin(expected_execution_context_sha256)
    if (not isinstance(child_checkpoint_id,str)
            or re.fullmatch(r'refine-[0-9]{3,}',child_checkpoint_id) is None
            or child_checkpoint_id==expected_checkpoint_id):
        raise ValueError('Require a distinct numbered child checkpoint identity')
    if request_model_role not in ('parent','candidate'):
        raise ValueError('Require an explicit parent or candidate request model role')
    run=checkpoints.registry_path(Path(run_directory)).parent.parent
    directory='AutoRefine/round_'+child_checkpoint_id.split('-')[1]
    request_ref=_reference(execution_reference);params_ref=_reference(generated_parameters)
    if (request_ref['anchor']!='run'
            or request_ref['relative_path']!=directory+'/parallelity_runtime/request.json'):
        raise ValueError('Execution request does not belong to the expected child')
    if params_ref['anchor']!='run' or params_ref['relative_path']!=directory+'/autorefine.params':
        raise ValueError('Generated parameters must belong to the exact child round')
    if not isinstance(additional_restraints,(list,tuple)):
        raise ValueError('Require an ordered additional restraint declaration')
    for ref in additional_restraints:_reference(ref)
    adapter_ref=None if refinement_input_reference is None else _reference(refinement_input_reference)
    if execution_reader is None:
        try:from .refinement_parallelity import read_execution_request as execution_reader
        except ImportError as exc:
            raise RuntimeError('The maintained Cedar execution request reader is required') from exc
    if adapter_ref is not None and refinement_input_reader is None:
        try:from .refinement_inputs import validate_refinement_inputs as refinement_input_reader
        except ImportError as exc:
            raise RuntimeError('The maintained Cedar refinement input reader is required') from exc
    motion,parameters,parent_binding=load_checkpoint_bend_motion(run,preview_directory,
        expected_checkpoint_id=expected_checkpoint_id,expected_receipt_sha256=expected_receipt_sha256,
        checkpoint=checkpoint,expected_checkpoint_context_sha256=expected_checkpoint_context_sha256)
    parent_context=parent_binding['context']
    candidate_bytes=(Path(preview_directory)/'candidate.pdb').read_bytes()
    candidate_identity=dict(sha256=sha256(candidate_bytes).hexdigest(),size=len(candidate_bytes))

    def read_join():
        return _execution_input_context(run,execution_reference=execution_reference,
            child_checkpoint_id=child_checkpoint_id,expected_checkpoint_id=expected_checkpoint_id,
            request_model_role=request_model_role,generated_parameters=generated_parameters,
            parent_context=parent_context,parent_context_sha256=parent_binding['context_sha256'],
            candidate_identity=candidate_identity,additional_restraints=additional_restraints,
            refinement_input_reference=refinement_input_reference,execution_reader=execution_reader,
            refinement_input_reader=refinement_input_reader)

    before=read_join()
    if expected_execution_context_sha256 is not None and recipe_digest(before)!=expected_execution_context_sha256:
        raise ValueError('Bound execution context changed')
    after=read_join()
    latest,source=_snapshot(run,checkpoint,expected_checkpoint_id,expected_receipt_sha256)
    if before!=after or latest!=parent_context:
        raise ValueError('Execution request or checkpoint changed during binding')
    # Recheck all preview inputs after request readers; this remains non-atomic.
    load_bend_motion(preview_directory,expected_receipt_sha256=expected_receipt_sha256,
                     parent_model_bytes=source)
    checkpoints._ref_path(execution_reference,'execution request',run)
    if (Path(preview_directory)/'candidate.pdb').read_bytes()!=candidate_bytes:
        raise ValueError('Preview candidate changed during execution binding')
    return motion,parameters,dict(schema_version=1,kind='topostitch-execution-input-binding',
        **before,context_sha256=recipe_digest(before),parent_binding=parent_binding,
        candidate_coordinates_in_request=request_model_role=='candidate',
        runtime_authority=False,chemical_admission=False,locking=False,scientific_acceptance=False)


def _execution_input_context(run, *, execution_reference, child_checkpoint_id,
        expected_checkpoint_id, request_model_role, generated_parameters,
        parent_context, parent_context_sha256, candidate_identity,
        additional_restraints, refinement_input_reference, execution_reader,
        refinement_input_reader):
    """Read request membership; caller must authenticate the parent context."""
    request_ref=_reference(execution_reference)
    params_ref=_reference(generated_parameters)
    extras=[_reference(ref) for ref in additional_restraints]
    adapter_ref=None if refinement_input_reference is None else _reference(refinement_input_reference)
    inherited=parent_context['inputs']
    source_restraints=[_reference(row) for row in inherited if row['role']=='restraint']
    declared_restraints=[*source_restraints,*extras]
    # The maintained owner validates request records, frozen code and inputs.
    request=execution_reader(run,execution_reference,checkpoint=child_checkpoint_id)
    if request.get('checkpoint')!=child_checkpoint_id or request.get('parent')!=expected_checkpoint_id:
        raise ValueError('Execution request parent or child identity differs')
    actual=[_reference(row) for row in request['inputs']]
    execution_restraints=list(declared_restraints)
    adaptation=None
    if adapter_ref is not None:
        adaptation=refinement_input_reader(run,declared_restraints,
            refinement_input_reference,checkpoint=child_checkpoint_id)
        for row in adaptation['adaptations']:
            # Semantic validation of the namespace derivative stays with its owner.
            index=row['index']
            if (type(index) is not int or index not in range(len(declared_restraints))
                    or _reference(row['source'])!=declared_restraints[index]):
                raise ValueError('Adapted restraint differs from its declared source order')
            execution_restraints[index]=_reference(row['execution'])
    observations=next(_reference(row) for row in inherited if row['role']=='observations')
    source_model=next(_reference(row) for row in inherited if row['role']=='model')
    phases=[_reference(row) for row in inherited if row['role']=='phases']
    if len(actual)<2:raise ValueError('Execution request omits model/data inputs')
    if request_model_role=='parent':
        if actual[1]!=source_model:raise ValueError('Request model is not the exact declared parent')
    elif any(actual[1][key]!=value for key,value in candidate_identity.items()):
        raise ValueError('Request model is not the exact preview candidate')
    expected=[observations,actual[1],*execution_restraints,*phases,params_ref]
    if actual!=expected:
        raise ValueError('Execution input roles or ordered restraints differ from declarations')
    # Resolve independently declared extra/parameter/adapter files as well.
    for ref in [*extras,params_ref,*([adapter_ref] if adapter_ref is not None else [])]:
        path=checkpoints._ref_path(ref,'declared execution input',run)
        if path.stat().st_size!=ref['size']:raise ValueError('Execution input size differs')
    roles=['observations','model',*(['restraint']*len(source_restraints)),
        *(['additional_restraint']*len(extras)),*(['phases']*len(phases)),'generated_parameters']
    inputs=[dict(role=role,**ref) for role,ref in zip(roles,actual)]
    for index,source in enumerate(declared_restraints):
        if source!=execution_restraints[index]:inputs[index+2]['source']=source
    return dict(request_sha256=request_ref['sha256'],request_record_sha256=recipe_digest(request),
        policy_id=request['policy_id'],checkpoint_context_sha256=parent_context_sha256,
        parent_checkpoint_id=expected_checkpoint_id,child_checkpoint_id=child_checkpoint_id,
        request_model_role=request_model_role,inputs=inputs,refinement_input_reference=adapter_ref,
        adaptation_sha256=None if adaptation is None else recipe_digest(adaptation))
