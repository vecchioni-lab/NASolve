"""Read-only exact-topology prerequisite for source-bound FANA construction."""
from .cif_attachment_native import _capture
from .cif_catalogue import _digest
from .cif_fana_component import _load
from .cif_fana_junction import _bind, _path
from .cif_topology_gate import review_native_topology

POLICY_ID = 'cif-source-bound-fana-topology-v1'


def inspect_fana_topology(control, model, native_receipt, *, bridge_seed=None,
                          na_policy=None, na_phil=None):
    """Bind source projection, complete model and preserved native capture.

    Optional NARestraints inputs are explicit frozen policy JSON and compiled
    PHIL files. They are read as declarations; installed recipes are not rerun.
    Historical provenance paths in captures are never used for resolution.
    """
    try:
        control = _path(control, directory=True)
        model, native_receipt = [_path(p) for p in (model, native_receipt)]
        if bridge_seed is not None:
            bridge_seed = _path(bridge_seed, directory=True)
        if (na_policy is None) != (na_phil is None):
            raise ValueError('Supply both frozen NARestraints policy and compiled PHIL')
        extra = [] if na_policy is None else [_path(na_policy), _path(na_phil)]
        trees = [control, *([bridge_seed] if bridge_seed is not None else [])]
        paths = [model, native_receipt, *extra, *[p for tree in trees for p in tree.rglob('*') if p.is_file()]]
        before = {p:p.read_bytes() for p in paths}
        receipt, native, captured = _capture(native_receipt, before[model])
        before.update(captured)
        if (native.get('status') != 'REVIEW' or native.get('inventory_detail') != 'linked'
                or native.get('fatal_problems') is not None or native.get('unused_definitions')
                or native.get('unsupported_fields')):
            raise ValueError('Require a complete usable native linked capture for topology')
        placement, _, _ = _bind(control, model, native, bridge_seed)
        sites = {a['identity']['resseq'].strip():a['identity']['resname'].strip() for a in native['atoms']}
        context = placement['context']; expected = []
        for left, right in [(context['incoming_site'],context['site']), (context['site'],context['outgoing_site'])]:
            expected.append({'endpoints':[{'site':site,'component':sites[site.split(':')[1]],'atom_id':atom}
                                         for site,atom in [(left,"O3'"),(right,'P')]]})
        result = review_native_topology(native, before[model], expected,
                    na_policy=_load(extra[0]) if extra else None,
                    na_phil=before[extra[1]].decode('utf-8') if extra else None)
        result.update(policy_id=POLICY_ID, topology_policy_id=result['policy_id'],
                      source_binding='EXACT_PLACEMENT_PROJECTION_AND_MODEL',
                      phenix_version=receipt['phenix_version'], native_execution='NOT_RUN_BY_READER',
                      bindings={'placement_receipt':_digest(before[control/'receipt.json']),
                                'model':_digest(before[model]),'native_receipt':_digest(before[native_receipt])},
                      scope='THREE_SITE_CONSTRUCTION_PREREQUISITE; FLANK_CHEMISTRY_UNQUALIFIED')
        if bridge_seed is not None:
            result['bindings']['bridge_seed_receipt'] = _digest(before[bridge_seed/'receipt.json'])
        if extra:
            result['bindings'].update(na_policy=_digest(before[extra[0]]),na_phil=_digest(before[extra[1]]))
        if any(p.read_bytes() != data for p,data in before.items()):
            raise ValueError('Topology evidence changed during inspection')
        result['input_integrity'] = 'UNCHANGED'
        return result
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise ValueError('Malformed FANA topology evidence: ' + str(exc)) from exc


def require_fana_topology(*args, **kwargs):
    """Stop construction/score comparison unless exact declared topology matches."""
    report = inspect_fana_topology(*args, **kwargs)
    if report['link_status'] != 'MATCH':
        raise ValueError('FANA topology gate requires exact declared links; inspect_fana_topology reports discrepancies')
    return report
