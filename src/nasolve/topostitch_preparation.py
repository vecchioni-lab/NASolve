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
from .topostitch_endpoint import _native_atom_order


def inspect_checkpoint_preparation(run_directory, *, expected_checkpoint_id,
        expected_model_sha256, checkpoint=None, preparation_reader=None,
        expected_context_sha256=None, ordinary_model_context_owner=None):
    """Inspect a published PostMR/preparation checkpoint, without writing files.

    The optional reader is a trusted dependency with Cedar's
    ``_read_registry_with_preparations`` contract. Its checked/exact result pair
    is consumed from that one call, without replaying the complete history again.
    Refined descendants require a later lineage join and are explicitly refused.
    Opt in to deriving canonical ordinary backbone context with the trusted Cedar
    ``ordinary_model_context_owner``. It uses this exact original PostMR model and
    frozen plan, and remains separate from checked-preparation availability. Its
    coordinate/plan derivation is not independent experimental topology or pairing.
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
    derived = None
    if ordinary_model_context_owner is not None:
        from .topostitch_recipe import model_atom_rows
        report = _json(snapshots[run/'report.json'])
        codes = sorted({r['residue_code'] for r in model_atom_rows(model_bytes)})
        owner = ordinary_model_context_owner
        if (published is not None or parent['id'] != 'postmr'
                or not codes or not set(codes) <= {'DA','DC','DG','DT'}
                or not isinstance(report.get('post_mr_plan'),dict)
                or not isinstance(report.get('postmr'),dict)
                or report['postmr'].get('prepared_sha256') != model_pin
                or owner.POLICY_ID != 'cif-prepared-model-context-v1'):
            raise ValueError('Require an exact original canonical PostMR model and frozen ordinary intent')
        record = owner.derive_prepared_model_context(model_path, report, codes)
        if (record.get('policy_id') != owner.POLICY_ID
                or type(record.get('schema_version')) is not int or record['schema_version'] != 1
                or record.get('model_sha256') != model_pin or record.get('components') != codes
                or record.get('scientific_qualification') != 'NOT_ASSESSED'):
            raise ValueError('Ordinary source context differs from the exact canonical parent or scope')
        derived = dict(status='DERIVED_ORDINARY_BACKBONE_CONTEXT',model_context=record,
            authority='CURRENT_MODEL_AND_FROZEN_ORDINARY_PLAN',
            pair_or_stack_assignments='NOT_INFERRED',experimental_topology='NOT_ESTABLISHED',
            checked_preparation=False,chemical_admission=False,motion_admission=False)
    context=dict(schema_version=1,kind='topostitch-preparation-input-context',checkpoint_id=expected_checkpoint_id,
        selection=dict(mode='current' if checkpoint is None else 'explicit',requested=checkpoint),
        registry_sha256=sha256(snapshots[cp]).hexdigest(),report_sha256=sha256(snapshots[run/'report.json']).hexdigest(),
        parent_record_sha256=recipe_digest(parent),source_model_sha256=model_pin,inputs=inputs,
        publication=publication,request=request_ref,result=result_ref,availability=fields)
    if derived is not None:context['derived_source_context_sha256']=recipe_digest(derived)
    pin=recipe_digest(context)
    if expected_context_sha256 is not None and expected_context_sha256!=pin:
        raise ValueError('Preparation context changed since the previous read')
    if any(p.read_bytes()!=b for p,b in snapshots.items()):raise ValueError('Preparation changed during reporting')
    return dict(schema_version=1,kind='topostitch-preparation-availability',status=status,
        context=context,context_sha256=pin,availability=fields,
        native_capture='NOT_ASSESSED_BY_THIS_READER',chemical_admission=False,
        motion_admission=False,runtime_authority=False,locking=False,scientific_acceptance=False,
        **({'derived_source_context':derived} if derived is not None else {}))


def inspect_checkpoint_native_window(run_directory, *, expected_checkpoint_id,
        expected_model_sha256, native_receipt, expected_native_receipt_sha256,
        selected_indices, expected_context_sha256=None, checkpoint=None,
        preparation_reader=None, native_owners=None, ordinary_model_context_owner=None):
    """Report captured restraint support for an explicit preparation atom window.

    Indices refer to source PDB atom-record order, not native order or serials.
    Counts retain proxy multiplicity, including both planes of parallelity terms.
    Selection is ASU atom-index membership; captured symmetry metadata is retained
    without claiming an image-aware spatial window or complete interaction graph.

    ``native_owners`` optionally supplies trusted Cedar attachment, named-proxy
    and full-monomer modules, in that order. This mirrors the existing explicit
    preparation-reader seam for standalone Willow; it never imports artifact code.
    The capture may use additional explicit inputs, which are separately reported.
    Every inherited restraint must be represented with its actual multiplicity.
    Optional ordinary model context is forwarded to the preparation inspector;
    derived source topology remains distinct from native or chemical qualification.
    This performs repeated snapshot checks, not locking or execution admission.
    """
    from collections import Counter
    from .topostitch_recipe import model_atom_rows
    _pin(expected_native_receipt_sha256)
    if (not isinstance(selected_indices, (list, tuple)) or not selected_indices
            or any(type(i) is not int or i < 0 for i in selected_indices)
            or list(selected_indices) != sorted(set(selected_indices))):
        raise ValueError('Require nonempty ordered unique atom indices')
    selected_indices = list(selected_indices)
    if native_owners is None:
        try:
            from . import cif_attachment_native, cif_terminal_qualification, cif_native_monomers
        except ImportError as exc:
            raise RuntimeError('Maintained Cedar native capture/proxy/monomer readers are required') from exc
        native_owners = (cif_attachment_native, cif_terminal_qualification, cif_native_monomers)
    if not isinstance(native_owners, (tuple, list)) or len(native_owners) != 3:
        raise ValueError('Require three trusted native reader owners')
    capture_owner, proxy_owner, monomer_owner = native_owners
    opts = dict(expected_checkpoint_id=expected_checkpoint_id,
        expected_model_sha256=expected_model_sha256, checkpoint=checkpoint,
        preparation_reader=preparation_reader, ordinary_model_context_owner=ordinary_model_context_owner)
    prepared = inspect_checkpoint_preparation(run_directory,
        expected_context_sha256=expected_context_sha256, **opts)
    run = checkpoints.registry_path(Path(run_directory)).parent.parent
    model_ref = next(r for r in prepared['context']['inputs'] if r['role'] == 'model')
    model_path = checkpoints._ref_path(model_ref, 'native window model', run)
    payload = model_path.read_bytes()
    if sha256(payload).hexdigest() != expected_model_sha256:
        raise ValueError('Parent model changed before native window read')
    identities = model_atom_rows(payload)
    if selected_indices[-1] >= len(identities):
        raise ValueError('Selected atom indices exceed parent inventory')
    path = Path(native_receipt).expanduser().resolve(strict=True)
    receipt_bytes = path.read_bytes()
    if sha256(receipt_bytes).hexdigest() != expected_native_receipt_sha256:
        raise ValueError('Native receipt differs from expected capture')
    receipt, native, snapshots = capture_owner._capture(path, payload)
    if receipt.get('status') != 'REVIEW' or native.get('status') != 'REVIEW':
        raise ValueError('Require a completed fixed-coordinate native capture')
    if snapshots.get(path) != receipt_bytes:
        raise ValueError('Native receipt changed during capture read')
    native_to_input, _ = _native_atom_order(native, payload, capture_owner)
    monomers = monomer_owner.review_full_monomers(native)
    atoms, named = proxy_owner._native_atom_identities(native)
    if set(atoms) != set(range(len(identities))):
        raise ValueError('Native atom mapping does not cover the exact parent')
    selected_input = set(selected_indices)
    selected = {i for i,j in enumerate(native_to_input) if j in selected_input}
    inherited = [r for r in prepared['context']['inputs'] if r['role'] == 'restraint']
    required = Counter((r['sha256'].lower(),r['size']) for r in inherited)
    supplied = [r for r in receipt['inputs'] if r['role'] in ('phil','dictionary')]
    available = Counter((r['sha256'].lower(),r['size']) for r in supplied)
    if required - available:
        raise ValueError('Native capture lacks inherited restraint input multiplicity')
    extras = []
    for r in supplied:
        key = (r['sha256'].lower(),r['size'])
        if required[key]: required[key] -= 1
        else: extras.append({k:r[k] for k in ('role','input_index','path','sha256','size')})
    families = ('bond_simple','bond_asu','angle','dihedral','const_dihedral',
                'chirality','planarity','parallelity')
    geometry = native['geometry']; details = geometry.get('proxy_details',{})
    if set(details) != set(families):
        raise ValueError('Missing or unknown native proxy families')
    counts = {}; boundary = []; all_native_indices = set(atoms)
    for family in families:
        rows = details[family]; number = geometry['proxy_counts'].get(family)
        state = ('RECORDED' if family.startswith('bond_')
                 else geometry.get('proxy_count_status',{}).get(family))
        if rows is None and number is None and state == 'UNSUPPORTED':
            counts[family] = dict(status='UNAVAILABLE',counts=None); continue
        if (state != 'RECORDED' or not isinstance(rows,list)
                or type(number) is not int or number != len(rows)):
            raise ValueError('Native proxy count/detail disagreement: '+family)
        partition = dict(selected=0,boundary=0,fixed=0,total=len(rows))
        for ordinal,row in enumerate(rows):
            indices, endpoints = proxy_owner._bound_proxy_endpoints(row,atoms,named)
            support = set(indices)
            if not support or not support <= all_native_indices:
                raise ValueError('Unbound native proxy support')
            role = 'selected' if support <= selected else 'boundary' if support & selected else 'fixed'
            partition[role] += 1
            if role == 'boundary':
                boundary.append(dict(family=family,ordinal=ordinal,
                    native_indices=indices,input_indices=[native_to_input[i] for i in indices],
                    named_endpoints=endpoints,parameters={k:v for k,v in row.items()
                        if k not in ('i_seqs','j_seqs','atoms','j_atoms')}))
        counts[family] = dict(status='RECORDED',counts=partition)
    requests = geometry.get('custom_proxy_requests')
    if not isinstance(requests,list):
        raise ValueError('Missing native custom-request inventory')
    if (model_path.read_bytes() != payload
            or any(p.read_bytes() != b for p,b in snapshots.items())):
        raise ValueError('Native window inputs changed during inspection')
    repeated = inspect_checkpoint_preparation(run_directory,
        expected_context_sha256=prepared['context_sha256'], **opts)
    if repeated != prepared or any(p.read_bytes() != b for p,b in snapshots.items()):
        raise ValueError('Preparation or native capture changed during inspection')
    result = dict(schema_version=1,kind='topostitch-preparation-native-window',
        policy_id='topostitch-preparation-native-window-v1',status='RECORDED',
        preparation=prepared,
        native_receipt=dict(anchor='native_capture_directory',relative_path=path.name,
            sha256=expected_native_receipt_sha256,size=len(receipt_bytes)),
        native_version=receipt['phenix_version'],full_monomers=monomers,
        window=dict(index_basis='SOURCE_PDB_ATOM_RECORD_ORDER',
            selected_input_indices=selected_indices,selected_native_indices=sorted(selected),
            selected_atoms=[identities[i] for i in selected_indices],
            selected_atom_count=len(selected),fixed_atom_count=len(identities)-len(selected),
            image_scope='ASU_INDEX_MEMBERSHIP; CAPTURED_SYMMETRY_METADATA_RETAINED'),
        source_intent=dict(inherited_restraint_file_count=len(inherited),
            captured_custom_request_count=len(requests),
            pair_or_stack_assignments='NOT_INFERRED',interaction_absence='NOT_ESTABLISHED',
            additional_capture_inputs=extras),
        families=counts,boundary_terms=boundary,proxy_definitions_sha256=recipe_digest(details),
        coverage='PARTIAL_NATIVE_FAMILIES' if any(r['status']=='UNAVAILABLE' for r in counts.values())
            else 'RECORDED_NATIVE_FAMILIES',
        nonbonded_interactions='NOT_ASSESSED',geometry_quality='NOT_ASSESSED',
        chemical_admission=False,motion_admission=False,locking=False,
        runtime_authority=False,scientific_acceptance=False)
    # Detach structured reader values and refuse nonfinite numerical evidence.
    import json
    return json.loads(json.dumps(result,allow_nan=False))
