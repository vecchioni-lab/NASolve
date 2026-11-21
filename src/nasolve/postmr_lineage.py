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
CANONICAL_POLICY_ID = 'postmr-canonical-construction-lineage-v1'
SITE_DICTIONARY_POLICY_ID = 'postmr-site-dictionary-construction-lineage-v1'
PROJECTION_POLICY_ID = 'postmr-projected-dictionary-construction-lineage-v1'
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


def _site_dictionary_closure(root, references, inputs, controls):
    """Validate only declared per-site files using the constructor's existing rule."""
    from .postmr import MutationAction, PostMRPreparationError, _construction_site_dictionaries
    _need(isinstance(references, dict) and references
          and all(isinstance(site, str) for site in references), 'Invalid site dictionary inventory')
    choices = {}
    for index, (site, reference) in enumerate(sorted(references.items())):
        path = _resolve(reference, root)
        _need(reference['path'] == f'PostMR/Coot/site_dictionaries/{index:03d}.cif',
              'Site dictionary role differs')
        choices[site] = path
    dictionaries = {c: _resolve(ref, root) for c, ref in inputs['dictionaries'].items()}
    try:
        checked, _ = _construction_site_dictionaries(
            tuple(MutationAction(**a) for a in controls['actions']), dictionaries,
            choices, controls['passthrough_sites'])
    except PostMRPreparationError as exc:
        raise ValueError('Invalid construction site dictionary: ' + str(exc)) from exc
    return checked, {ref['path']: _read(_resolve(ref, root)) for ref in references.values()}


def _projection_closure(root, references, inputs, controls, site_references):
    """Join the existing site derivation to exact consumed choices and intent."""
    from .cif_dictionary_sites import read_dictionary_sites, CONSTRUCTION_POLICY_ID
    _need(isinstance(references, dict) and 1 <= len(references) <= 16
          and set(references) <= inputs['dictionaries'].keys(), 'Invalid construction projection inventory')
    _need(isinstance(site_references, dict) and site_references,
          'Construction projections require explicit consumed site dictionaries')
    selected, files, contexts, sources = {}, {}, {}, {}
    actions = {a['site']: a for a in controls['actions']}
    for code, reference in sorted(references.items()):
        path = _resolve(reference, root)
        _need(reference['path'] == f'PostMR/Coot/construction_projections/{code}/site_receipt.json',
              'Construction projection evidence has the wrong role')
        saved = read_dictionary_sites(path.parent); report = saved['report']
        _need(report['policy_id'] == CONSTRUCTION_POLICY_ID and report['component'] == code,
              'Require a canonical-input projection for the declared component')
        _need(_read(saved['canonical_model']) == _read(_resolve(inputs['model'], root)),
              'Projection canonical model differs from construction input')
        sites = set(report['construction_targets'])
        _need(sites == {site for site,a in actions.items() if a['after'] == code}
              and sites <= site_references.keys() and not sites & set(controls['passthrough_sites']),
              'Projection sites differ from complete construction intent')
        for context in report['contexts']:
            site = context['site']; action = actions[site]
            _need(action['method'] == 'coot-parent-overlap'
                  and action['before'] == report['construction_targets'][site],
                  'Projection original identity differs from construction action')
            _need((context['five_prime_state'] == 'phosphate') == (site in controls['allow_op3_sites']),
                  'Projection phosphate state differs from construction intent')
            projection, component = saved['projections'][site]
            _need(component == code and _read(projection) == _read(_resolve(site_references[site], root)),
                  'Consumed site dictionary differs from its saved chemical projection')
        selected.update({site: saved['projections'][site][0] for site in sites})
        contexts[code] = {k: report[k] for k in ('contexts','expected_links')}
        sources[code] = dict(source=saved['snapshot']['source'],
            source_authority=saved['snapshot']['manifest']['request']['source_authority'])
        files[reference['path']] = _read(path)
        for ref in report['files']:
            artifact = path.parent/ref['path']
            files[artifact.relative_to(root).as_posix()] = _read(artifact)
        _need(_reference(path, root) == reference and read_dictionary_sites(path.parent)['report'] == report,
              'Construction projection changed during lineage readback')
    _need(set(selected) == set(site_references), 'Every chosen site dictionary needs its declared projection')
    return contexts, files, sources


def begin_postmr_construction(run, model, reference_model, dictionaries, actions, *,
                             allow_op3_sites=(), passthrough_sites=(), site_dictionary_paths=None,
                             construction_projections=None):
    """Capture the identities of existing consumed inputs before construction."""
    root=_root(run)
    inputs=dict(model=_reference(model,root),reference_model=_reference(reference_model,root),
                dictionaries={c:_reference(p,root) for c,p in sorted(dictionaries.items())})
    controls=dict(actions=[asdict(a) for a in actions],allow_op3_sites=sorted(allow_op3_sites),
                  passthrough_sites=sorted(passthrough_sites))
    _inputs(root,inputs); _controls(controls,inputs['dictionaries'])
    result = dict(inputs=inputs,controls=controls)
    if site_dictionary_paths is not None:
        _need(isinstance(site_dictionary_paths, dict), 'Invalid site dictionary mapping')
        references = {site: _reference(p, root) for site, p in site_dictionary_paths.items()}
        _site_dictionary_closure(root, references, inputs, controls)
        result['site_dictionaries'] = references
    if construction_projections is not None:
        _need(isinstance(construction_projections, dict), 'Invalid construction projection mapping')
        references = {code: _reference(Path(directory)/'site_receipt.json', root)
                      for code, directory in construction_projections.items()}
        _projection_closure(root, references, inputs, controls, result.get('site_dictionaries'))
        result['construction_projections'] = references
    return result


def _canonical_closure(root, reference, inputs, controls):
    """Join the existing pure seed proof to original input/actions, without copying a tree."""
    from .postmr_canonical_input import read_canonical_parent_input, _resolve as seed_resolve, REPORT
    path = _resolve(reference, root)
    _need(reference['path'] == 'PostMR/Coot/canonical_seeds/' + REPORT,
          'Canonical construction evidence has the wrong role')
    saved = read_canonical_parent_input(path.parent)
    receipt = saved['receipt']
    original = seed_resolve(path.parent, receipt['input'])
    _need(_read(original) == _read(_resolve(inputs['model'], root)),
          'Canonical seed does not start from the recorded construction input')
    actions = [step['action'] for step in receipt['steps']]
    sites = {a['site'] for a in actions}
    _need(actions == [a for a in controls['actions'] if a['site'] in sites]
          and not sites.intersection(controls['passthrough_sites']),
          'Canonical seed actions differ from original construction intent')
    references = [receipt['input'], receipt['model'],
                  *[step[k] for step in receipt['steps'] for k in ('source', 'template')]]
    files = {reference['path']: _read(path)}
    for ref in references:
        artifact = seed_resolve(path.parent, ref)
        files[artifact.relative_to(root).as_posix()] = _read(artifact)
    _need(_reference(path, root) == reference and read_canonical_parent_input(path.parent) == saved,
          'Canonical seed evidence changed during lineage readback')
    return saved, files


def finish_postmr_construction(run, started, prepared_model, construction):
    """Seal a fresh, non-qualifying record before downstream numerical work."""
    root=_root(run); path=root/RECORD_PATH
    if path.exists() or path.is_symlink():raise FileExistsError(path)
    _need(isinstance(started,dict) and {'inputs','controls'} <= set(started)
          and set(started) <= {'inputs','controls','site_dictionaries','construction_projections'},
          'Invalid construction start identity')
    _inputs(root,started['inputs']); _controls(started['controls'],started['inputs']['dictionaries'])
    outputs=dict(after_coot=_reference(construction['model'],root),prepared=_reference(prepared_model,root))
    evidence={}
    for name,p in [('raw_model',construction['raw_model']),('coot_log',construction['coot_log']),
                   ('script',root/'PostMR/Coot/mutate.py')]:
        evidence[name]=_reference(p,root) if p is not None and Path(p).is_file() else None
    record=dict(schema_version=1,policy_id=POLICY_ID,status='CONSTRUCTION_RETURNED',
        scientific_qualification='NOT_ASSESSED',native_interpretation='NOT_RUN',automatic_adoption=False,
        **started,outputs=outputs,evidence=evidence)
    if 'canonical_parent_input' in construction:
        from .postmr_canonical_input import REPORT
        supplied = construction['canonical_parent_input']
        _need(isinstance(supplied, dict) and set(supplied) == {'model', 'directory', 'receipt'},
              'Invalid returned canonical construction evidence')
        reference = _reference(Path(supplied['directory']) / REPORT, root)
        saved, _ = _canonical_closure(root, reference, started['inputs'], started['controls'])
        _need(supplied == saved, 'Returned canonical construction evidence differs from saved proof')
        record.update(policy_id=CANONICAL_POLICY_ID, canonical_parent_input=reference)
    else:
        _need(not (root/'PostMR/Coot/canonical_seeds').exists(),
              'Canonical construction evidence cannot be silently omitted')
    if 'site_dictionaries' in started:
        choices, _ = _site_dictionary_closure(root, started['site_dictionaries'], started['inputs'], started['controls'])
        supplied = construction.get('site_dictionary_paths')
        _need(isinstance(supplied, dict) and supplied == choices,
              'Returned site dictionaries differ from the choices captured before construction')
        record.update(policy_id=SITE_DICTIONARY_POLICY_ID, site_dictionaries=started['site_dictionaries'])
    else:
        _need('site_dictionary_paths' not in construction
              and not (root/'PostMR/Coot/site_dictionaries').exists(),
              'Site dictionary choices cannot be silently omitted')
    if 'construction_projections' in started:
        _projection_closure(root, started['construction_projections'], started['inputs'],
                            started['controls'], started.get('site_dictionaries'))
        record['policy_id'] = PROJECTION_POLICY_ID
    else:
        _need(not (root/'PostMR/Coot/construction_projections').exists(),
              'Construction projection evidence cannot be silently omitted')
    write_record(path,record)
    return read_postmr_construction(root)['report']


def read_postmr_construction(run):
    """Resolve the declared record only, without SDK access or executing saved code.

    A containing run may have unrelated artifacts. The returned files mapping is
    the exact closure a request must freeze; it must not copy the entire run.
    Missing execution evidence stays missing and cannot become qualification.
    """
    root=_root(run); raw=_read(root/RECORD_PATH); r=read_record(root/RECORD_PATH)
    canonical = 'canonical_parent_input' in r
    site_choices = 'site_dictionaries' in r
    projections = 'construction_projections' in r
    fields = {'schema_version','policy_id','status','scientific_qualification','native_interpretation',
              'automatic_adoption','inputs','outputs','controls','evidence','record_sha256'}
    if canonical: fields.add('canonical_parent_input')
    if site_choices: fields.add('site_dictionaries')
    if projections: fields.add('construction_projections')
    _need(set(r)==fields
          and type(r['schema_version']) is int and r['schema_version']==1
          and r['policy_id']==(PROJECTION_POLICY_ID if projections else
                               SITE_DICTIONARY_POLICY_ID if site_choices else
                               CANONICAL_POLICY_ID if canonical else POLICY_ID)
          and r['status']=='CONSTRUCTION_RETURNED'
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
    if canonical:
        _, seed_files = _canonical_closure(root, r['canonical_parent_input'], r['inputs'], r['controls'])
        files.update(seed_files)
    selected = None
    if site_choices:
        selected, site_files = _site_dictionary_closure(root, r['site_dictionaries'], r['inputs'], r['controls'])
        files.update(site_files)
    if projections:
        projection_contexts, projection_files, projection_sources = _projection_closure(root, r['construction_projections'],
            r['inputs'], r['controls'], r.get('site_dictionaries'))
        files.update(projection_files)
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
                dictionaries={c:root/ref['path'] for c,ref in r['inputs']['dictionaries'].items()},
                **({'site_dictionary_paths': selected} if site_choices else {}),
                **({'projection_contexts': projection_contexts, 'projection_sources': projection_sources} if projections else {}))
