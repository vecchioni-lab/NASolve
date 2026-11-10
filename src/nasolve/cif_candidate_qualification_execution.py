"""Owned two-seed component qualification with conservative, portable readback.

This explicit callback qualifies isolated numerics only. It does not acquire a
source, choose chemistry, retry an attempt, adopt a model or qualify refinement.
"""
from hashlib import sha256
import math
from pathlib import Path
import re
from time import monotonic

from .failure_reporting import add_failure_note
from .campaign_records import path_in, read_record, write_record
from .cif_outer_context import OuterAllowance
from .cif_attachment_native import _capture
from .cif_candidate_qualification import CandidateQualificationProcesses, inspect_candidate_qualification_processes
from .cif_candidate_usability import reassess_complete_candidate, qualify_candidate_native, covalent_proxy_signature
from .cif_component_runtime import _tree
from .cif_dictionary_sites import _consumer, _bind_capture, _need, _read
from .cif_dictionary_store import _bytes, _json, _snapshot_destination
from .cif_generation_process import _valid_attempt_identity
from .cif_native_validation import inspect_native_bundle, NATIVE_POLICY_ID
from .cif_postmr_cache import verify_current_consumer
from .cif_triple_bond_audit import component_control_model_bytes, write_component_control_model

POLICY_ID = 'cif-two-seed-qualification-execution-v1'
ANCHOR = 'qualification_directory'
REPORT = 'qualification_execution.json'
_PHIL = b'pdb_interpretation {\n secondary_structure.enabled = False\n}\n'
_SEEDS = ('source', 'candidate')


class CandidateQualificationBudgetExceeded(TimeoutError):
    """No allowance remains; partial evidence grants no usable qualification."""


def _protocol(code, consumer, native_limit, total_limit, policy):
    _need(isinstance(code,str) and re.fullmatch(r'[A-Z0-9]{1,3}',code), 'Unsupported isolated component code')
    _consumer(consumer)
    _need(type(native_limit) is int and 1 <= native_limit <= 600
          and type(total_limit) is int and 1 <= total_limit <= 3600, 'Require bounded integer qualification deadlines')
    _need(policy is None or isinstance(policy,str), 'Invalid explicit representation policy')
    return dict(policy_id=POLICY_ID, component=code, consumer=_json(_bytes(consumer)),
        native_timeout_seconds=native_limit, total_timeout_seconds=total_limit,
        bond_representation_policy=policy, seeds=list(_SEEDS))


def _ref(path, root):
    data=_read(path)
    return dict(anchor=ANCHOR,path=path.relative_to(root).as_posix(),sha256=sha256(data).hexdigest(),size=len(data))


def _resolve(root, ref):
    _need(isinstance(ref,dict) and ref.get('anchor')==ANCHOR, 'Qualification artifact anchor differs')
    path=path_in(root,ref.get('path'))
    _need(_ref(path,root)==ref, 'Qualification artifact checksum differs')
    return path


def _inventory(root):
    return {n:dict(sha256=sha256(b).hexdigest(),size=len(b)) for n,b in _tree(root).items() if n!=REPORT}


def _inputs(root):
    base=root/'inputs';p=_json(_read(base/'protocol.json'))
    expected=_protocol(p['component'],p['consumer'],p['native_timeout_seconds'],p['total_timeout_seconds'],p['bond_representation_policy'])
    _need(p==expected, 'Qualification protocol differs')
    paths=[base/'source/source.cif',base/'candidate/candidate.cif']
    models=[base/'models'/(seed+'.pdb') for seed in _SEEDS]
    _need(set(_tree(base))=={'protocol.json','isolated.phil','source/source.cif','candidate/candidate.cif','models/source.pdb','models/candidate.pdb'}, 'Qualification input scope differs')
    _need(_read(base/'isolated.phil')==_PHIL, 'Isolated qualification PHIL differs')
    for cif,model in zip(paths,models):
        _need(component_control_model_bytes(cif,p['component'])[0]==_read(model), 'Qualification coordinate seed differs from its dictionary')
    return p,paths,models,base/'isolated.phil'


def _derive(root, refs, state):
    p,paths,models,phil=_inputs(root)
    _need(isinstance(refs,list) and len(refs)==2, 'Require both independent native captures')
    qualifications=[];signatures=[]
    for i,(ref,model) in enumerate(zip(refs,models)):
        receipt=_resolve(root,ref);phase=f'native-{i:03d}'
        _need(receipt.name=='native_receipt.json' and receipt.parent.parent==root/'native'/f'{i:03d}', 'Native capture belongs to another phase')
        job=state['phases'][phase]['job'];finished=state['phases'][phase]['finished']
        _need(job['cwd']==dict(anchor=ANCHOR,path=receipt.parent.relative_to(root).as_posix())
              and job['timeout_seconds']<=min(p['native_timeout_seconds'],p['total_timeout_seconds']), 'Native ownership/deadline differs')
        _need(finished['status']=='COMPLETED' and finished['returncode']==0,
              f"Native qualification failed for {_SEEDS[i]} seed ({finished['status']}, return code {finished['returncode']}); inspect {receipt}")
        capture,native,_=_capture(receipt,_read(model))
        _bind_capture(capture,p['consumer'],model,[paths[1]],[phil])
        rows=capture['inputs'];spec=_json(_read(receipt.parent/'native_spec.json'))
        _need(spec==dict(policy_id=NATIVE_POLICY_ID,model=rows[0]['path'],dictionaries=[rows[1]['path']],phil_files=[rows[2]['path']],
            phil_namespace_policy='direct',inventory_detail='linked',policy_inventory=True,energy_inventory=True), 'Isolated native specification differs')
        _need(capture['execution']['timeout_seconds']==job['timeout_seconds'], 'Native deadline differs from its owned intent')
        _need(set(_tree(receipt.parent))=={'native_receipt.json'}|{r['path'] for r in capture['outputs']}, 'Native capture inventory differs')
        q=qualify_candidate_native(*paths,model,p['component'],native,bond_representation_policy=p['bond_representation_policy'])
        _need(q['native_usable'] is True, 'Independent coordinate seed is not natively usable')
        qualifications.append(q);signatures.append(covalent_proxy_signature(native))
    _need(signatures[0]==signatures[1], 'Covalent proxy signatures differ between coordinate seeds')
    return dict(qualification=qualifications[0],seed_qualifications=qualifications,same_covalent_proxies=True)


def read_candidate_qualification(directory):
    """Rederive completed isolated qualification without SDK access or mutation."""
    root=Path(directory).absolute();inventory=_inventory(root)
    report=read_record(root/REPORT);p,_,_,_=_inputs(root)
    fields={'schema_version','policy_id','status','scope','automatic_adoption','protocol','native_receipts',
            'elapsed_seconds','outputs','process_header_sha256','process_finish_sha256','qualification',
            'seed_qualifications','same_covalent_proxies','record_sha256'}
    _need(set(report)==fields, 'Unexpected qualification report fields')
    _need(report.get('schema_version')==1 and type(report['schema_version']) is int
          and report.get('policy_id')==POLICY_ID and report.get('status')=='ISOLATED_NATIVE_USABILITY_PASS'
          and report.get('automatic_adoption') is False and report.get('scope')=='ISOLATED_COMPONENT_ONLY'
          and report.get('outputs')==inventory, 'Qualification report scope/inventory differs')
    elapsed=report.get('elapsed_seconds')
    _need(type(elapsed) in (int,float) and math.isfinite(elapsed) and 0<=elapsed<p['total_timeout_seconds'], 'Qualification elapsed allowance differs')
    state=inspect_candidate_qualification_processes(root)
    _need(state['state']=='STOPPED' and state['finished']['outcome']=='RETURNED'
          and set(state['phases'])=={'native-000','native-001'}
          and report.get('process_header_sha256')==state['header']['record_sha256']
          and report.get('process_finish_sha256')==state['finished']['record_sha256'], 'Qualification ownership is incomplete')
    _need(report.get('protocol')==_ref(root/'inputs/protocol.json',root), 'Qualification protocol binding differs')
    derived=_derive(root,report.get('native_receipts'),state)
    _need(all(report.get(k)==v for k,v in derived.items()), 'Saved qualification does not reproduce')
    _need(_inventory(root)==inventory, 'Qualification changed during inspection')
    return report


def execute_candidate_qualification(source,candidate,code,consumer,phenix,output,*,
        native_timeout_seconds=90,total_timeout_seconds=180,bond_representation_policy=None,_attempt_identity=None,_remaining_seconds=None):
    """Run both isolated seeds once within a cooperative monotonic allowance.

    Time begins before preflight. Each job receives at most whole seconds left;
    late local work is refused before publication. Final atomic publication and
    owned cleanup are cooperative, not a hard wall-clock kill. Failed/interrupted
    work is preserved and must use a fresh output; no retry is inferred. An optional
    enclosing allowance also clamps both jobs and the publication boundaries.
    """
    started=monotonic()
    outer=OuterAllowance(_remaining_seconds,monotonic,CandidateQualificationBudgetExceeded)
    p=_protocol(code,consumer,native_timeout_seconds,total_timeout_seconds,bond_representation_policy)
    _need(_attempt_identity is None or _valid_attempt_identity(_attempt_identity), 'Invalid parent attempt identity')
    def remaining(minimum=0):
        cap=outer.remaining()
        value=total_timeout_seconds-(monotonic()-started)
        if cap is not None:value=min(value,cap)
        if value<=0 or value<minimum:raise CandidateQualificationBudgetExceeded('Qualification allowance exhausted; partial output is not usable')
        return value
    originals=[Path(source).absolute(),Path(candidate).absolute()];before=[_read(path) for path in originals]
    root=_snapshot_destination(output).resolve();installation=Path(phenix.root).resolve()
    _need(not root.is_relative_to(installation) and not installation.is_relative_to(root)
          and not any(path.resolve().is_relative_to(root) for path in originals), 'Qualification output overlaps selected inputs/installation')
    _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],p['consumer']), 'Selected native consumer differs')
    _need(reassess_complete_candidate(*originals,code,bond_representation_policy=bond_representation_policy)['candidate_status']=='CANDIDATE_REVIEW', 'Candidate does not preserve declared chemistry')
    remaining();root.mkdir(parents=True,exist_ok=False)
    base=root/'inputs';base.mkdir()
    for seed,data in zip(_SEEDS,before):
        folder=base/seed;folder.mkdir();(folder/(seed+'.cif')).write_bytes(data)
    (base/'protocol.json').write_bytes(_bytes(p));(base/'isolated.phil').write_bytes(_PHIL)
    for seed in _SEEDS:write_component_control_model(base/seed/(seed+'.cif'),code,base/'models'/(seed+'.pdb'))
    p,paths,models,phil=_inputs(root)
    owner=CandidateQualificationProcesses(root,attempt_identity=_attempt_identity);sealed=False
    try:
        refs=[]
        for i,model in enumerate(models):
            limit=min(native_timeout_seconds,int(remaining(1)))
            result=inspect_native_bundle(model,[paths[1]],root/'native'/f'{i:03d}',phenix.executables['phenix.python'],environment=phenix.environment,
                phenix_version=phenix.version,timeout_seconds=limit,phil_files=[phil],inventory_detail='linked',policy_inventory=True,energy_inventory=True,
                _process_runner=owner.runner(f'native-{i:03d}'))
            remaining();receipt=Path(result['native_directory']).absolute()/'native_receipt.json'
            _need(receipt.parent.parent==root/'native'/f'{i:03d}', 'Native adapter returned another capture')
            refs.append(_ref(receipt,root))
        state=inspect_candidate_qualification_processes(root);derived=_derive(root,refs,state)
        _need([_read(path) for path in originals]==before, 'Selected qualification inputs changed')
        _need(verify_current_consumer(phenix,phenix.executables['phenix.ready_set'],p['consumer']), 'Native consumer changed during qualification')
        remaining();_need(owner.finish('RETURNED'), 'Native cleanup remains unverified');sealed=True
        state=inspect_candidate_qualification_processes(root);inventory=_inventory(root)
        remaining();elapsed=monotonic()-started
        report=dict(schema_version=1,policy_id=POLICY_ID,status='ISOLATED_NATIVE_USABILITY_PASS',scope='ISOLATED_COMPONENT_ONLY',automatic_adoption=False,
            protocol=_ref(base/'protocol.json',root),native_receipts=refs,elapsed_seconds=elapsed,outputs=inventory,
            process_header_sha256=state['header']['record_sha256'],process_finish_sha256=state['finished']['record_sha256'],**derived)
        remaining()  # final cooperative boundary, before atomic publication
        return write_record(root/REPORT,report)
    except BaseException as exc:
        if not sealed:
            try:owner.finish('RAISED')
            except Exception as seal_error:add_failure_note(exc, 'Ownership completion could not be sealed', seal_error)
        raise


def make_candidate_qualifier(phenix,code,*,native_timeout_seconds=90,total_timeout_seconds=180,bond_representation_policy=None):
    """Return the four-argument callback accepted by cache-first acquisition.

    Creating the callback performs no SDK discovery or execution, so cache hits
    remain independent of the installation. Evidence is retained in fresh output.
    """
    def qualify(source,candidate,consumer,output):
        result=execute_candidate_qualification(source,candidate,code,consumer,phenix,output,
            native_timeout_seconds=native_timeout_seconds,total_timeout_seconds=total_timeout_seconds,bond_representation_policy=bond_representation_policy)
        return result['qualification']
    return qualify
