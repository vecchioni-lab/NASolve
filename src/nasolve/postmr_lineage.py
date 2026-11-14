"""Ordinary construction lineage, distinct from chemical qualification.

The caller captures input identities before construction and seals returned
models before ReadySet. Replay reads only explicitly anchored run artifacts.
It neither reruns Coot nor establishes a scientifically usable geometry.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import re

from .campaign_records import read_record, write_record
from .cif_construction_provenance import _safe
from .cif_dictionary_sites import _need, _read
from .cif_repair_attempt import _root

POLICY_ID = 'postmr-construction-lineage-v1'
RECORD_PATH = 'PostMR/Coot/construction.json'


def _reference(path, root):
    path = Path(path).absolute()
    relative = path.relative_to(root).as_posix()
    _need(_safe(relative) and relative.startswith('PostMR/'), 'Construction artifact must be run-local')
    data = _read(path)
    return dict(anchor='run', path=relative, sha256=sha256(data).hexdigest(), size=len(data))


def _resolve(reference, root):
    _need(isinstance(reference, dict) and set(reference) == {'anchor','path','sha256','size'}
          and reference['anchor'] == 'run' and _safe(reference['path'])
          and reference['path'].startswith('PostMR/'), 'Invalid construction artifact reference')
    path = root/reference['path']
    _need(reference == _reference(path, root), 'Construction dictionary/model artifact changed')
    return path


def _inputs(root, inputs):
    _need(isinstance(inputs,dict) and set(inputs)=={'model','reference_model','dictionaries'},
          'Unexpected construction input fields')
    model = _resolve(inputs['model'],root)
    reference = _resolve(inputs['reference_model'],root)
    _need(inputs['model']['path'] in {'PostMR/Model/mr_solution.pdb','PostMR/Model/component_normalized.pdb'}
          and inputs['reference_model']['path']=='PostMR/Model/mr_solution.pdb',
          'Construction model role differs')
    dictionaries=inputs['dictionaries']
    _need(isinstance(dictionaries,dict) and all(isinstance(c,str) and re.fullmatch('[A-Z0-9]{1,3}',c) for c in dictionaries),
          'Invalid construction dictionary inventory')
    for code,ref in dictionaries.items():
        _resolve(ref,root)
        _need(ref['path']==f'PostMR/Coot/source_dictionaries/{code}.cif', 'Construction dictionary role differs')
    return model, reference


def _controls(value, dictionaries):
    _need(isinstance(value,dict) and set(value)=={'actions','allow_op3_sites','passthrough_sites'},
          'Unexpected construction controls')
    actions=value['actions']
    _need(isinstance(actions,list) and all(isinstance(a,dict) and set(a)=={
        'site','before','after','method','parent_code','deposition_code'} for a in actions),
        'Invalid construction actions')
    for action in actions:
        _need(all(isinstance(action[k],str) and action[k] for k in ('site','before','after','method'))
              and all(action[k] is None or isinstance(action[k],str) and action[k]
                      for k in ('parent_code','deposition_code')), 'Invalid construction action fields')
        _need(action['method'] in {'none','component-normalization','coot-mutate-base','coot-parent-overlap'},
              'Unknown construction method')
    _need(len({a['site'] for a in actions})==len(actions), 'Duplicate construction site')
    _need(set(dictionaries)=={a['after'] for a in actions if a['method'] in {'coot-parent-overlap','component-normalization'}},
          'Consumed construction dictionaries differ from mutation actions')
    for key in ('allow_op3_sites','passthrough_sites'):
        _need(isinstance(value[key],list) and all(isinstance(s,str) for s in value[key])
              and value[key]==sorted(set(value[key])), 'Invalid construction site policy')
    _need(not set(value['allow_op3_sites']) & set(value['passthrough_sites']), 'Conflicting construction site policy')


def begin_postmr_construction(run, model, reference_model, dictionaries, actions, *,
                             allow_op3_sites=(), passthrough_sites=()):
    """Capture the identities of existing consumed inputs before construction."""
    root=_root(run)
    inputs=dict(model=_reference(model,root),reference_model=_reference(reference_model,root),
                dictionaries={c:_reference(p,root) for c,p in sorted(dictionaries.items())})
    controls=dict(actions=[asdict(a) for a in actions],allow_op3_sites=sorted(allow_op3_sites),
                  passthrough_sites=sorted(passthrough_sites))
    _inputs(root,inputs); _controls(controls,inputs['dictionaries'])
    return dict(inputs=inputs,controls=controls)


def finish_postmr_construction(run, started, prepared_model, construction):
    """Seal a fresh, non-qualifying record before downstream numerical work."""
    root=_root(run); path=root/RECORD_PATH
    if path.exists() or path.is_symlink():raise FileExistsError(path)
    _need(isinstance(started,dict) and set(started)=={'inputs','controls'}, 'Invalid construction start identity')
    _inputs(root,started['inputs']); _controls(started['controls'],started['inputs']['dictionaries'])
    outputs=dict(after_coot=_reference(construction['model'],root),prepared=_reference(prepared_model,root))
    evidence={}
    for name,p in [('raw_model',construction['raw_model']),('coot_log',construction['coot_log']),
                   ('script',root/'PostMR/Coot/mutate.py')]:
        evidence[name]=_reference(p,root) if p is not None and Path(p).is_file() else None
    record=dict(schema_version=1,policy_id=POLICY_ID,status='CONSTRUCTION_RETURNED',
        scientific_qualification='NOT_ASSESSED',native_interpretation='NOT_RUN',automatic_adoption=False,
        **started,outputs=outputs,evidence=evidence)
    write_record(path,record)
    return read_postmr_construction(root)['report']


def read_postmr_construction(run):
    """Resolve the declared record only, without SDK access or executing saved code.

    A containing run may have unrelated artifacts. The returned files mapping is
    the exact closure a request must freeze; it must not copy the entire run.
    Missing execution evidence stays missing and cannot become qualification.
    """
    root=_root(run); raw=_read(root/RECORD_PATH); r=read_record(root/RECORD_PATH)
    _need(set(r)=={'schema_version','policy_id','status','scientific_qualification','native_interpretation',
                  'automatic_adoption','inputs','outputs','controls','evidence','record_sha256'}
          and type(r['schema_version']) is int and r['schema_version']==1
          and r['policy_id']==POLICY_ID and r['status']=='CONSTRUCTION_RETURNED'
          and r['scientific_qualification']=='NOT_ASSESSED' and r['native_interpretation']=='NOT_RUN'
          and r['automatic_adoption'] is False, 'Invalid construction lineage claims')
    _, reference = _inputs(root,r['inputs']); _controls(r['controls'],r['inputs']['dictionaries'])
    _need(isinstance(r['outputs'],dict) and set(r['outputs'])=={'after_coot','prepared'}, 'Invalid construction output inventory')
    for key,name in [('after_coot','after_coot.pdb'),('prepared','prepared_model.pdb')]:
        _resolve(r['outputs'][key],root)
        _need(r['outputs'][key]['path']=='PostMR/Model/'+name, 'Construction output role differs')
    _need(isinstance(r['evidence'],dict) and set(r['evidence'])=={'raw_model','coot_log','script'}, 'Invalid construction evidence inventory')
    for key,name in [('raw_model','PostMR/Model/after_coot_raw.pdb'),('coot_log','PostMR/Coot/coot.log'),('script','PostMR/Coot/mutate.py')]:
        if r['evidence'][key] is not None:
            _resolve(r['evidence'][key],root)
            _need(r['evidence'][key]['path']==name,'Construction execution evidence role differs')
    references=[r['inputs']['model'],r['inputs']['reference_model'],*r['inputs']['dictionaries'].values(),
                *r['outputs'].values(),*(v for v in r['evidence'].values() if v is not None)]
    files={RECORD_PATH:raw}
    for ref in references:files[ref['path']]=_read(_resolve(ref,root))
    # Check declared identities with the ordinary caller's existing parser. This
    # is a model/action join, not a second chemistry or geometry validator.
    from .postmr import PostMRPreparationError, residue_name
    try:
        for action in r['controls']['actions']:
            _need(residue_name(reference,action['site']) == action['before']
                  and residue_name(root/r['outputs']['prepared']['path'],action['site']) == action['after'],
                  'Construction action differs from recorded model identities')
    except PostMRPreparationError as exc:
        raise ValueError('Invalid construction model/action identity: '+str(exc)) from exc
    _need(all(_read(root/name)==data for name,data in files.items()), 'Construction lineage changed during readback')
    return dict(report=r,files=files,model=root/r['outputs']['prepared']['path'],
                dictionaries={c:root/ref['path'] for c,ref in r['inputs']['dictionaries'].items()})
