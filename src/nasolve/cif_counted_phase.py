"""Frozen phase entry for the existing refinement controller, never a process runner.

The entry script authenticates the request and all frozen code before importing
this module. This writes observations, not admission. The enclosing controller
owns stopped processes, the immutable admission and compact evidence retention.
"""
import hashlib
import json
from pathlib import Path
import sys

from . import cif_counted_contribution as counted
from . import cif_counted_refinement as lifetime
from . import cif_refinement_runtime as runtime
from . import topostitch_native_recipe as factory

POLICY_ID = 'counted-phase-observation-v1'


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _write(path,value):
    with path.open('x',encoding='utf-8') as handle:
        json.dump(value,handle,sort_keys=True,allow_nan=False)
        handle.write('\n')


def run_phase(root, request, phase, arguments, *, admission=None, prepared_path=None):
    """One already-requested native phase; provider selection only in preflight."""
    need=counted._need
    need(phase in ('preflight','refine'),'Unknown counted phase')
    # The controller resolves anchored inputs; historical commands are never a
    # relocation/retry shortcut. Verify their bytes again in the fresh process.
    for reference,name in zip(request['inputs'],request['command'][1:]):
        data=Path(name).read_bytes()
        need(len(data)==reference['size'] and hashlib.sha256(data).hexdigest()==reference['sha256'],
             'Counted native input changed')
    intent=request['counted_intent']
    packet=json.loads((root/'intent/current-recipe.json').read_text())
    model_bytes=Path(request['command'][2]).read_bytes()
    need(_digest(packet)==intent['current_recipe_sha256'],'Counted recipe changed')
    pins={Path(name).stem:row['sha256'] for name,row in request['code'].items() if name.endswith('.py')}
    factory_sources={name:pins[name] for name in counted._factory_modules(factory)}
    helper_sources={name:pins[name] for name in counted.HELPER_MODULES}
    sites=[{k:row[k] for k in ('site','component')} for row in request.get('chemistry_projections',[])]
    folder=root/phase
    if phase=='preflight':
        refined=runtime.run_compatible_refinement(arguments,evidence_directory=folder,chemistry_sites=sites)
        # Successful native preflight and subsequent preparation refusal are
        # different outcomes. Keep native zero and its complete raw evidence.
        try:
            scope=lifetime.refinement_scope(refined)
            prepared=counted.observe_prepared_pair_contribution(refined.model,
                factory_module=factory,factory_sources=factory_sources,helper_sources=helper_sources,
                packet=packet,model_bytes=model_bytes,expected_recipe_sha256=intent['current_recipe_sha256'],
                counted_baseline=True)
        except (ValueError,RuntimeError) as exc:
            _write(folder/'counted.json',dict(policy_id=POLICY_ID,status='REFUSED',
                error=dict(type=type(exc).__name__,message=str(exc))))
            return
        work=folder/'preparation-work';work.mkdir()
        _write(work/'prepared.json',prepared)
        _write(folder/'counted.json',dict(policy_id=POLICY_ID,status='PREPARED',
            scope=scope,prepared_sha256=_digest(prepared),recipe_sha256=intent['current_recipe_sha256']))
        return
    need(isinstance(admission,dict) and prepared_path is not None,'Counted refinement requires sealed admission')
    prepared=json.loads(Path(prepared_path).read_text())
    need(_digest(prepared)==admission['prepared_sha256'],'Expanded preparation differs from admission')
    helper_sources['cif_refinement_runtime']=pins['cif_refinement_runtime']
    owner=lifetime.PreparedCountedRefinement(expected_scope=admission['scope'],
        factory_module=factory,factory_sources=factory_sources,helper_sources=helper_sources,
        packet=packet,model_bytes=model_bytes,expected_recipe_sha256=intent['current_recipe_sha256'],
        prepared=prepared,expected_prepared_sha256=admission['prepared_sha256'])
    primary=None
    try:
        with owner:
            runtime.run_compatible_refinement(arguments,evidence_directory=folder,chemistry_sites=sites)
    except BaseException as exc:
        primary=exc
        raise
    finally:
        if folder.is_dir():
            try:
                _write(folder/'counted.json',dict(policy_id=POLICY_ID,lifetime=owner.statistics(),
                    admission_record_sha256=admission['record_sha256'],
                    prepared_sha256=_digest(prepared),compiled_binding_sha256=_digest(prepared['compiled_binding']),
                    provider_selection_sha256=_digest(prepared['provider_selection']),
                    recipe_sha256=intent['current_recipe_sha256'],scope_sha256=_digest(admission['scope'])))
            except BaseException as secondary:
                if primary is None:raise
                note='Counted evidence write also failed: '+type(secondary).__name__+': '+str(secondary)
                if hasattr(primary,'add_note'):primary.add_note(note)
                else:
                    try:sys.stderr.write(note+'\n')
                    except OSError:pass

