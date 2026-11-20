"""Read available preparation authority without admitting a deformation.

The existing Cedar registry/publication/result reader owns scientific evidence
validation. This adapter pins a selected published preparation and describes
which authenticated fields it supplies. It does not manufacture missing intent.
"""
from hashlib import sha256
from pathlib import Path
import re

from . import checkpoints
from .topostitch_checkpoint import _pin, _reference
from .topostitch_preview import _json
from .topostitch_recipe import recipe_digest


def inspect_checkpoint_preparation(run_directory, *, expected_checkpoint_id,
        expected_model_sha256, checkpoint=None, preparation_reader=None,
        expected_context_sha256=None):
    """Inspect a published PostMR/preparation checkpoint, without writing files.

    The optional reader is a trusted dependency with Cedar's
    ``_read_registry_with_preparations`` contract. Its checked/exact result pair
    is consumed from that one call, without replaying the complete history again.
    Refined descendants require a later lineage join and are explicitly refused.
    This snapshot is neither atomic dispatch nor chemical/motion authorization.
    """
    model_pin=_pin(expected_model_sha256)
    if expected_context_sha256 is not None:_pin(expected_context_sha256)
    if (not isinstance(expected_checkpoint_id,str) or not expected_checkpoint_id
            or checkpoint is not None and (not isinstance(checkpoint,str) or not checkpoint)):
        raise ValueError('Require an explicit expected checkpoint identity')
    if preparation_reader is None:
        preparation_reader=getattr(checkpoints,'_read_registry_with_preparations',None)
        if preparation_reader is None:
            raise RuntimeError('The maintained Cedar preparation registry reader is required')
    cp=checkpoints.registry_path(Path(run_directory));run=cp.parent.parent
    snapshots={cp:cp.read_bytes(),run/'report.json':(run/'report.json').read_bytes()}
    registry=_json(snapshots[cp]);parent=checkpoints.resolve_checkpoint(registry,checkpoint)
    if (parent.get('id')!=expected_checkpoint_id
            or sum(r.get('id')==expected_checkpoint_id for r in registry['checkpoints'] if isinstance(r,dict))!=1):
        raise ValueError('Selected checkpoint identity differs from the expected parent')
    if not (parent.get('id')=='postmr' and parent.get('kind')=='postmr'
            or re.fullmatch(r'prepare-[0-9]{3,}',parent.get('id','')) and parent.get('kind')=='preparation'):
        raise ValueError('Refined descendants need a separately qualified preparation lineage join')
    if parent.get('usable') is not True:
        raise ValueError('Require a reusable published preparation')
    def read_ref(value,role):
        ref=_reference(value);path=checkpoints._ref_path(ref,role,run);data=path.read_bytes()
        if len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256'].lower():
            raise ValueError(role+' changed while reading preparation')
        if path in snapshots and snapshots[path]!=data:
            raise ValueError(role+' changed during preparation read')
        snapshots[path]=data
        return ref,path,data
    model,model_path,model_bytes=read_ref(parent.get('model'),'model')
    if sha256(model_bytes).hexdigest()!=model_pin:
        raise ValueError('Selected model differs from expected parent bytes')
    inputs=[dict(role='model',**model)]
    for role,value in [('observations',parent.get('observations'))]+([('phases',parent['phases'])] if parent.get('phases') is not None else []):
        ref,_,_=read_ref(value,role);inputs.append(dict(role=role,**ref))
    if not isinstance(parent.get('restraints'),list):raise ValueError('Require ordered inherited restraints')
    restraint_paths=[]
    for value in parent['restraints']:
        ref,path,_=read_ref(value,'restraint');inputs.append(dict(role='restraint',**ref));restraint_paths.append(path)
    published=parent.get('checked_preparation');publication=None;request_ref=None;result_ref=None
    if published is not None:
        publication,_,data=read_ref(published,'publication');record=_json(data)
        if parent['kind']=='preparation':record=record['preparation']
        meta=record['checked_preparation'];number=meta['attempt_number']
        if type(number) is not int or number<1:raise ValueError('Require an exact preparation attempt')
        request_ref,request_path,request_bytes=read_ref(meta['request'],'request')
        result_ref,result_path,result_bytes=read_ref(meta['result'],'result')
    resolved,owned,verified=preparation_reader(run)
    if resolved!=run or owned!=registry or any(p.read_bytes()!=b for p,b in snapshots.items()):
        raise ValueError('Selected preparation inputs changed during the owner read')
    fields={name:dict(status='UNAVAILABLE') for name in ('model_context','restraint_context','literal_na_inputs','explicit_na_policy')}
    if published is None:
        if verified is not None:raise ValueError('Owner results lack a selected publication reference')
        if registry.get('schema_version')!=2:raise ValueError('Missing checked publication')
        status='NO_CHECKED_PREPARATION'
    else:
        if not isinstance(verified,dict) or number not in verified:
            raise ValueError('Selected publication lacks an authenticated preparation result')
        checked,exact=verified[number]
        if (checked.run_directory!=run or checked.attempt_number!=number
                or checked.model_path is None or Path(checked.model_path).resolve()!=model_path
                or Path(checked.request_directory).resolve()!=request_path.parent
                or Path(checked.report_path).resolve()!=result_path
                or list(map(Path,(*checked.restraint_paths,*checked.dictionary_paths)))!=restraint_paths
                or exact['result']!=_json(result_bytes)):
            raise ValueError('Owner result belongs to different preparation inputs')
        config=_json(request_bytes)['configuration']
        for name in ('model_context','restraint_context'):
            value=config.get(name)
            if value is not None:
                if not isinstance(value,dict):raise ValueError('Malformed preparation context')
                fields[name]=dict(status='AVAILABLE',sha256=recipe_digest(value))
        if fields['model_context']['status']=='AVAILABLE':
            source=config['model_context'].get('model_sha256');_pin(source)
            fields['model_context'].update(source_model_sha256=source,matches_selected_model=source==model_pin)
        for name in ('literal_na_inputs','explicit_na_policy'):
            if (name in config)!=(name in exact):raise ValueError('Compiler reference differs from the authenticated result')
            if name in exact:
                report=exact[name]['report']
                fields[name]=dict(status='AVAILABLE',report_sha256=recipe_digest(report),
                    policy_id=report['policy_id'],index_basis=report.get('index_basis'),
                    reference_sha256=recipe_digest(config[name]))
        status='CHECKED_PREPARATION_FIELDS'
    context=dict(schema_version=1,kind='topostitch-preparation-input-context',checkpoint_id=expected_checkpoint_id,
        selection=dict(mode='current' if checkpoint is None else 'explicit',requested=checkpoint),
        registry_sha256=sha256(snapshots[cp]).hexdigest(),report_sha256=sha256(snapshots[run/'report.json']).hexdigest(),
        parent_record_sha256=recipe_digest(parent),source_model_sha256=model_pin,inputs=inputs,
        publication=publication,request=request_ref,result=result_ref,availability=fields)
    pin=recipe_digest(context)
    if expected_context_sha256 is not None and expected_context_sha256!=pin:
        raise ValueError('Preparation context changed since the previous read')
    if any(p.read_bytes()!=b for p,b in snapshots.items()):raise ValueError('Preparation changed during reporting')
    return dict(schema_version=1,kind='topostitch-preparation-availability',status=status,
        context=context,context_sha256=pin,availability=fields,
        native_capture='NOT_ASSESSED_BY_THIS_READER',chemical_admission=False,
        motion_admission=False,runtime_authority=False,locking=False,scientific_acceptance=False)
