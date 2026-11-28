"""Controller storage and cold review of an explicitly captured final pair state.

The runtime must already have stopped. Reuse the sealed preparation and bounded
archive owner; neither old commands nor stored native code are executed here.
"""
import os
from pathlib import Path

from .campaign_records import path_in, read_record, write_record, _sync_directory
from .refinement_inputs import _bound_path
from .refinement_counted import _digest, _json, _need
from .cif_runtime_evidence import pack_runtime_evidence, expanded_runtime_evidence
from .topostitch_pair_geometry import review_pair_geometry

POLICY_ID = 'saved-final-pair-geometry-v1'
CAPTURE_POLICY_ID = 'closed-counted-pair-observation-v1'


def _review_capture(capture, prepared, native, lifetime):
    """Bind an actual captured state to the completed writer and frozen providers."""
    fields={'schema_version','policy_id','prepared_sha256','attribution','compiled_declarations',
        'native_state','points_sha256','fixed_observation_sha256','provider_selection_sha256',
        'counted_lifetime_sha256','diagnostic_kernel_before','diagnostic_kernel_after',
        'native_state_unchanged','scientific_acceptance'}
    _need(isinstance(capture,dict) and set(capture)==fields
          and type(capture['schema_version']) is int and capture['schema_version']==1
          and capture['policy_id']==CAPTURE_POLICY_ID and capture['native_state_unchanged'] is True
          and capture['scientific_acceptance'] is False, 'Unsupported final pair capture')
    _need(lifetime.get('status')=='COMPLETE' and lifetime.get('binding_restored') is True
          and lifetime.get('pair_geometry_capture')==dict(status='CAPTURED',record_sha256=_digest(capture))
          and _digest(lifetime.get('owner'))==capture['counted_lifetime_sha256'],
          'Pair capture differs from completed counted lifetime')
    _need(_digest(prepared)==capture['prepared_sha256']
          and _digest(prepared['provider_selection'])==capture['provider_selection_sha256'],
          'Pair capture differs from sealed preparation')
    original=prepared['native_observation']
    fixed={k:v for k,v in original.items() if k not in ('native_state','points_sha256')}
    _need(_digest(fixed)==capture['fixed_observation_sha256'],
          'Final pair inventory does not match the saved preparation')
    state=capture['native_state']; outputs=native.get('output_synchronization')
    _need(native.get('status')=='COMPLETE' and native.get('dry_run') is False
          and isinstance(outputs,list) and len(outputs)==1
          and outputs[0].get('write_completed') is True,
          'Final pair geometry requires a completed native writer')
    _need(state['hierarchy_sha256']==outputs[0]['hierarchy_after_sha256']
          ==native['written_model']['model_state_sha256']
          and state['scattering_sha256']==outputs[0]['scattering_sha256'],
          'Pair geometry is not the actual written native state')
    before,after=(capture[k] for k in ('diagnostic_kernel_before','diagnostic_kernel_after'))
    keys={'successful_calls','gradient_calls','energy_only_calls','maximum_proxy_count'}
    for value in (before,after):
        _need(isinstance(value,dict) and set(value)==keys|{'policy_id'}
              and value['policy_id']=='native-parallelity-kernel-adapter-v1'
              and all(type(value[k]) is int and value[k]>=0 for k in keys)
              and value['successful_calls']==value['gradient_calls']+value['energy_only_calls'],
              'Invalid descriptive kernel accounting')
    _need(after['gradient_calls']==before['gradient_calls']
          and all(after[k]>=before[k] for k in keys), 'Pair read changed gradient accounting')
    observed=dict(original,native_state=state,points_sha256=capture['points_sha256'])
    records=[capture['attribution'],capture['compiled_declarations'],observed,prepared['provider_selection']]
    return review_pair_geometry(*records,expected_inputs_sha256=_digest(records))


def review_capture(capture, prepared, native, lifetime):
    try:
        return _review_capture(capture, prepared, native, lifetime)
    except (KeyError, TypeError, AttributeError, IndexError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError('Incomplete final pair geometry evidence') from exc


def _review_saved(run,root,admission,capture):
    archive=admission['prepared_archive'];path=_bound_path(archive,'prepared pair inventory',run)
    with expanded_runtime_evidence(path,archive['sha256']) as view:
        prepared=_json(view/'evidence/prepared.json')
    _need(_digest(prepared)==admission['prepared_sha256'], 'Changed prepared pair inventory')
    native=_json(path_in(run,root+'/refine/result.json'))
    lifetime=_json(path_in(run,root+'/refine/counted.json'))['lifetime']
    return review_capture(capture,prepared,native,lifetime)


def seal_pair_geometry(run,root,request,admission):
    """Seal one completed capture; never repair a partial native attempt in place."""
    from .checkpoints import _file_reference
    work=path_in(run,root+'/refine/pair-geometry-work');raw=work/'capture.json'
    _need(list(work.iterdir())==[raw] and not raw.is_symlink(), 'Unexpected pair capture membership')
    original=raw.read_bytes();capture=_json(raw)
    report=_review_saved(run,root,admission,capture)
    archive=path_in(run,root+'/refine/pair-geometry.zip')
    stored=pack_runtime_evidence(work,archive)
    with expanded_runtime_evidence(archive,stored['archive_sha256']) as view:
        _need((view/'evidence/capture.json').read_bytes()==original, 'Archived pair capture changed')
    with archive.open('rb') as handle:os.fsync(handle.fileno())
    _sync_directory(archive.parent)
    _need(raw.read_bytes()==original, 'Pair capture changed during storage')
    target=path_in(run,root+'/refine/pair-geometry.json')
    write_record(target,dict(schema_version=1,policy_id=POLICY_ID,
        checkpoint=request['checkpoint'],capture_record_sha256=_digest(capture),
        prepared_sha256=admission['prepared_sha256'],archive=_file_reference(archive,run),
        report_sha256=_digest(report)))
    # Retire only this verified transient copy; archive and receipt already durable.
    raw.unlink();work.rmdir();_sync_directory(archive.parent)
    return report


def read_pair_geometry(run,root,request):
    """Read exact evidence through existing path/checksum/size and archive owners."""
    value=read_record(path_in(run,root+'/refine/pair-geometry.json'))
    _need(set(value)=={'schema_version','policy_id','checkpoint','capture_record_sha256',
          'prepared_sha256','archive','report_sha256','record_sha256'}
          and type(value['schema_version']) is int and value['schema_version']==1
          and value['policy_id']==POLICY_ID and value['checkpoint']==request['checkpoint'],
          'Unsupported saved final pair geometry')
    admission=read_record(path_in(run,root+'/admission.json'))
    _need(value['prepared_sha256']==admission['prepared_sha256'], 'Changed pair geometry admission')
    reference=value['archive'];expected=root+'/refine/pair-geometry.zip'
    _need(isinstance(reference,dict) and reference.get('anchor')=='run' and reference.get('relative_path')==expected,
          'Pair geometry archive belongs to another round')
    archive=_bound_path(reference,'final pair geometry',run)
    with expanded_runtime_evidence(archive,reference['sha256']) as view:
        capture=_json(view/'evidence/capture.json')
    _need(_digest(capture)==value['capture_record_sha256'], 'Changed final pair capture')
    report=_review_saved(run,root,admission,capture)
    _need(_digest(report)==value['report_sha256'], 'Changed final pair report')
    return report


def summary(report):
    """Keep ordinary checkpoint metrics small; the complete report is read on demand."""
    return dict(status='OBSERVED',scope='ACTUAL_FINAL_NATIVE_STATE',
        report_sha256=_digest(report),force_sites_sha256=report['force_sites_sha256'],
        pair_geometry=report['pair_geometry'],pair_count=len(report['pairs']),
        native_requested_term_count=report['coverage']['native_requested_term_count'],
        additive_requested_term_count=report['coverage']['additive_requested_term_count'],
        unclassified_observed_term_count=len(report['unclassified_native_terms']),
        unclassified_scope='bond,angle,planarity,parallelity only',
        covalent_geometry='UNASSESSED',scientific_acceptance=False)
