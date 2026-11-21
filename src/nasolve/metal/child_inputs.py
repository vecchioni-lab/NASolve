"""Read-only derivation check joining prepared child bytes to a protected parent.

Existing checkpoint/metal readers own their scientific replay. This bridge does
not launch a worker, accept a fit, redo scattering/Free-R acquisition or retire
payload. Typed reader-control handoff remains a separate supported-role gate.
"""
from hashlib import sha256
from pathlib import PurePosixPath
import re

from ..checkpoints import CheckpointError, read_registry, resolve_checkpoint, inherited_paths
from ..run_context import resolve_artifact_path
from . import child_process, parent_archive
from .context import _reference
from .fdp import _input_bundle, make_plan, parameters
from .materialize import _json, _json_bytes, _source
from .recipe import RecipeError, canonical, digest

KIND = 'metal-fdp-child-input-derivation'


def _relative(value, label):
    if (not isinstance(value,str) or not value or chr(92) in value or ':' in value
            or any(ord(c)<32 for c in value)):
        raise RecipeError('Require a portable explicit '+label)
    path=PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path)!=value:
        raise RecipeError('Require a normalized explicit '+label)
    return path


def _inside(path, root):
    path=path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise RecipeError('Parent input resolves outside its declared protected layout')
    return path


def _closed_references(value, run, root):
    if isinstance(value,dict):
        if 'anchor' in value:
            path=resolve_artifact_path(value,run)
            if path is None:raise RecipeError('Parent input reference cannot be resolved')
            _inside(path,root)
        else:
            for item in value.values():_closed_references(item,run,root)
    elif isinstance(value,list):
        for item in value:_closed_references(item,run,root)


def _refuse_reader_controls(value, run, root, seen=None):
    """Capability guard only: do not parse or fold typed controls into restraints."""
    seen=set() if seen is None else seen
    if isinstance(value,dict):
        if 'interpretation_controls' in value:
            raise RecipeError('Typed reader-control role is not supported by this bridge')
        if isinstance(value.get('checked_preparation'),dict):
            meta=value['checked_preparation']
            ref=meta if 'anchor' in meta else meta.get('request')
            if ref is not None:
                _closed_references(ref,run,root)
                identity=canonical(ref)
                if identity not in seen:
                    seen.add(identity)
                    _refuse_reader_controls(_json(_source(ref,run)),run,root,seen)
        for item in value.values():_refuse_reader_controls(item,run,root,seen)
    elif isinstance(value,list):
        for item in value:_refuse_reader_controls(item,run,root,seen)


def _derive(root, payload, run_relative, endpoint_relative):
    run=child_process._root(root/run_relative)
    endpoint=child_process._root(run/endpoint_relative)
    source=_input_bundle(run,endpoint)
    context=_json(_source(source['parent']['files']['context'],run))
    # Metal replay intentionally uses the saved hypothesis context. Admission
    # additionally checks that its ordinary root still selects these same files.
    ordinary_run,registry=read_registry(run)
    if ordinary_run.resolve()!=run.resolve():raise RecipeError('Ordinary run changed')
    selected=resolve_checkpoint(registry,context['checkpoint_id'])
    if selected.get('usable') is not True:raise RecipeError('Ordinary source checkpoint is not usable')
    _refuse_reader_controls([_json((run/'report.json').read_bytes()),selected,context],run,root)
    paths=inherited_paths(selected,run)
    actual={key:_reference(_inside(paths[key],root),run) for key in ('model','observations')}
    actual['restraints']=[_reference(_inside(p,root),run) for p in paths['restraints']]
    actual['phases']=_reference(_inside(paths['phases'],root),run) if paths['phases'] else None
    for name,ref in actual.items():
        if canonical(ref)!=canonical(context['sources'][name]):
            raise RecipeError('Ordinary checkpoint inputs differ from saved hypothesis: '+name)
    _closed_references([{k:v for k,v in context['sources'].items() if k!='report'},source['inputs'],source['lineage'],source['parent']['files']],run,root)
    plan=_json(payload['plan.json'])
    if source['source_kind']=='native_xyz_endpoint' and plan['options'].get('metal_b_policy') is None:
        raise RecipeError('Native XYZ endpoint requires an explicit environmental B policy')
    replay,model=make_plan(source['model'],source['parent']['sites'],plan['metadata'],plan['references'],
        preview=source['preview'],resources=source['resources'],**plan['options'])
    phil,args=parameters(replay,[name for name,_ in source['resources']])
    expected={'input.pdb':model,'observations.mtz':_source(source['inputs']['observations'],run),
        'plan.json':_json_bytes(replay),'parameters.phil':phil,
        'native-plan.json':_json_bytes({'plan':replay,'args':args}),**dict(source['resources'])}
    if payload!=expected:raise RecipeError('Prepared child inputs differ from ordinary parent derivation')
    return dict(run={'anchor':'parent','relative_path':str(run_relative)},
        endpoint={'anchor':'run','relative_path':str(endpoint_relative)},
        parent=source['lineage'],source_kind=source['source_kind'],input_sources=source['inputs'],
        root_checkpoint_id=selected['id'],root_context_id=context['context_id'],
        ordinary_checkpoint_verified=True,derivation_verified=True,
        input_model_sha256=sha256(model).hexdigest(),plan_sha256=sha256(payload['plan.json']).hexdigest(),
        metal_b_policy=plan['options'].get('metal_b_policy'),
        free_r_label=plan['metadata']['free_r_label'],free_r_test_value=plan['options']['free_r_test_value'])


def verify_child_inputs(prepared_directory,parent_directory,request,*,request_id,
                        run_relative,endpoint_relative,reader_control_policy=None,
                        max_parent_disk_bytes=parent_archive.DEFAULT_DISK_BYTES):
    """Verify one explicit protected parent/input relationship; no mutation.

    Metadata and scattering references are replayed as declared in the request,
    not independently reacquired. No fresh original Free-R audit or supported
    native-control delivery is asserted by this derivation-only result.
    """
    if reader_control_policy is not None:
        raise RecipeError('Typed reader-control handoff is not supported by this bridge')
    run_relative=_relative(run_relative,'run path');endpoint_relative=_relative(endpoint_relative,'endpoint path')
    if (len(run_relative.parts)<2 or run_relative.parts[-2]!='AutoMR'
            or not re.fullmatch(r'run_[0-9]{3,}',run_relative.name)
            or not re.fullmatch(r'Metal/(xyz|geometry)_[0-9]{3,}',str(endpoint_relative))):
        raise RecipeError('Require an exact numbered run and metal geometry/XYZ endpoint')
    request=child_process._request(request,request_id)
    prepared=child_process._root(prepared_directory)
    payload=child_process._inputs(prepared,request['files']);child_process._declared_plan(payload)
    try:
        with parent_archive.materialized_parent_inputs(parent_directory,request['parent_manifest_sha256'],
                max_disk_bytes=max_parent_disk_bytes) as (root,transport):
            result=_derive(root,payload,run_relative,endpoint_relative)
            child_process._inputs(prepared,request['files'])
        if not transport['inputs_unchanged'] or not transport['snapshot_removed']:
            raise RecipeError('Protected parent transport did not finish verified')
    except (CheckpointError,OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot verify child input derivation: '+str(exc)) from exc
    result.update(kind=KIND,schema_version=1,request_id=request_id,
        parent_manifest_sha256=request['parent_manifest_sha256'],parent_transport=transport,
        metadata_reacquired=False,scattering_reacquired=False,fresh_free_r_audit=False,
        typed_reader_controls_supported=False,scientific_acceptance='NOT_ASSESSED',
        execution_authorized=False,reuse_authorized=False,retirement_authorized=False)
    result['derivation_id']=digest(result)
    return result
