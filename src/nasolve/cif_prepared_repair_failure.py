"""Read-only classification of stopped optional native failures, never usability.

Trustworthy negative execution is distinct from a malformed capture. Original
qualification and current-consumer verification remain separate mandatory gates.
"""
from hashlib import sha256
from pathlib import Path
import re

from .cif_attachment_native import _capture, _capture_timeout
from .cif_component_runtime import _tree
from .cif_dictionary_bundle import read_dictionary_bundle
from .cif_dictionary_sites import _bind_capture_inputs, _need, _read
from .cif_dictionary_store import _json
from .cif_dictionary_bundle_repair import _repair_dictionaries
from .cif_linear_torsion_bundle import read_linear_torsion_bundle
from .cif_native_validation import NATIVE_POLICY_ID
from .cif_native_monomers import POLICY_ID as MONOMER_POLICY
from .cif_repair_process import inspect_prepared_repair_processes

POLICY_ID='cif-prepared-native-failure-review-v1'
FALLBACK_POLICY_ID='cif-owned-native-failure-original-v1'


def failure_policy_fields(value):
    _need(value is None or (type(value) is str and value==FALLBACK_POLICY_ID),
          'Unsupported optional native failure policy')
    return {} if value is None else {'optional_failure_policy':value}


def _inspect(root, phase):
    root=Path(root).absolute();before=_tree(root)
    _need(isinstance(phase,str) and re.fullmatch(r'native-[0-9]{3,}',phase), 'Require an optional native stage')
    number=int(phase[7:]);_need(number>=1 and phase==f'native-{number:03d}', 'Initial captures cannot authorize fallback')
    prepared=read_dictionary_bundle(root/'bundle');plan=read_linear_torsion_bundle(root/'plan')
    _need(number<=len(plan['steps']) and plan['modeled_components']==sorted(prepared['report']['components']),
          'Failure stage differs from declared repair plan')
    _repair_dictionaries(prepared,plan,root/'plan')
    state=inspect_prepared_repair_processes(root)
    _need(phase in state['phases'] and all(p['state']=='STOPPED' for p in state['phases'].values()),
          'Optional failure has unknown or active owned work')
    child=state['phases'][phase];job=child['job'];finished=child['finished']
    _need('identity' in child and finished['status'] in {'TIMED_OUT','FAILED'}
        and type(finished['returncode']) is int, 'Require a launched and verified-stopped failed native job')
    receipt=root/job['cwd']['path']/'native_receipt.json'
    record,native,snapshots=(_capture_timeout if finished['status']=='TIMED_OUT' else _capture)(receipt,_read(prepared['model']))
    execution=record['execution']
    _need(execution['status']==finished['status'] and type(execution['returncode']) is int
        and execution['returncode']==finished['returncode']
        and type(execution.get('timeout_seconds')) in (int,float)
        and execution['timeout_seconds']==job['timeout_seconds'], 'Native failure and owned completion disagree')
    _need(record.get('command')==job['argv_provenance'] and len(record['command'])==3
        and record['command'][1:]==['native_worker.py','native_spec.json'], 'Native failure command differs from owned job')
    consumer=prepared['report']['consumer']
    _need(record.get('phenix_version')==consumer['version']
        and record.get('executable_sha256')==consumer['executable_sha256'], 'Failed native dispatcher differs')
    dictionaries=[root/'plan'/ref['path'] for ref in plan['steps'][number-1]['dictionaries_after']]
    _bind_capture_inputs(record,prepared['model'],dictionaries,prepared['after_phils'])
    rows=record['inputs'];spec=_json(_read(receipt.parent/'native_spec.json'))
    _need(spec==dict(policy_id=NATIVE_POLICY_ID,model=rows[0]['path'],
        dictionaries=[row['path'] for row in rows if row['role']=='dictionary'],
        phil_files=[row['path'] for row in rows if row['role']=='phil'],
        phil_namespace_policy='refinement-root-to-interpreter-v1',inventory_detail='linked',
        policy_inventory=True,energy_inventory=True,full_monomer_inventory=True)
        and record.get('full_monomer_inventory_policy')==MONOMER_POLICY,
        'Failed native request differs from the maintained repair context')
    _need(set(_tree(receipt.parent))=={'native_receipt.json'}|{row['path'] for row in record['outputs']},
          'Failed capture has unrecorded artifacts')
    _need(native is None or (isinstance(native.get('error'),str) and bool(native['error'].strip())
        and native.get('automatic_adoption') is False
        and all(native.get(k)=='NOT_RUN' for k in ('scientific_approval','model_editing','optimization','readyset_retry'))),
        'Reported native failure contains missing or contradictory execution claims')
    kind='NATIVE_TIMEOUT' if native is None else 'REPORTED_NATIVE_'+native['status']
    _need(kind in {'NATIVE_TIMEOUT','REPORTED_NATIVE_FAILED','REPORTED_NATIVE_UNSUPPORTED'}, 'Not a supported negative native result')
    if kind=='REPORTED_NATIVE_FAILED':kind='REPORTED_NATIVE_FAILURE'
    def ref(path):
        data=_read(path);return dict(anchor='repair_directory',path=path.relative_to(root).as_posix(),sha256=sha256(data).hexdigest(),size=len(data))
    report=dict(schema_version=1,policy_id=POLICY_ID,status='KNOWN_STOPPED_NATIVE_FAILURE',phase=phase,failure_kind=kind,
        receipt=ref(receipt),plan=ref(root/'plan/linear_torsion_bundle.json'),
        owner=ref(root/'ownership/repair.json'),job=ref(root/'ownership/phases'/phase/'job.json'),
        finished=ref(root/'ownership/phases'/phase/'finished.json'),stopped_verified=True,
        exact_inputs=True,maintained_worker=True,consumer_binding='DISPATCHER_ONLY; NOT_FULL_API_QUALIFICATION',
        fallback_authorized=False,retry_authorized=False,scientific_qualification='NOT_ASSESSED',new_native_calls=0)
    _need(_tree(root)==before and all(_read(p)==data for p,data in snapshots.items()), 'Failure evidence changed during inspection')
    return report


def inspect_prepared_native_failure(directory, phase):
    """Classify one exact optional failure without retrying or selecting inputs.

    Timeouts preserve partial reports as opaque data. Completed failed/unsupported
    worker reports must satisfy the strict existing capture reader. Missing proof,
    changed inputs, malformed reports and uncertain process cleanup still raise.
    Historical executable/argument paths are provenance only and never replayed.
    """
    try:return _inspect(directory,phase)
    except (KeyError,TypeError,IndexError,OSError) as exc:raise ValueError('Incomplete owned native failure evidence') from exc
