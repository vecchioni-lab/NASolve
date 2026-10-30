"""Offline comparison of verified geometry branches on one observation set.

Unlike fdp_compare, this descriptive review permits different geometry, metal
identity/count and environmental B. It never calls these controlled sensitivity
experiments, ranks solutions, executes a Doctor or selects a checkpoint.
"""
import gzip
from pathlib import Path
import re

from .context import _reference
from .fdp_compare import BUDGET_AXES, _load_trial
from .map_diagnostics import fit_context
from .materialize import _json, _json_bytes, _source
from .recipe import RecipeError, canonical, digest
from .xyz import recipe_diagnostics, verify_xyz

PROTOCOL = 'metal-candidate-review-v1'
MAX_TRIALS = 32


def _load_candidate(run, directory):
    trial = _load_trial(run, directory)
    doc = _json(_source(trial['ref'], run))
    plan = _json(_source(doc['files']['plan.json'], run))
    parent = doc['parent']['manifest']
    geometry = verify_xyz(run, Path(parent['relative_path']).parent)
    xp = _json(_source(geometry['files']['plan.json'], run))
    xr = _json(_source(geometry['files']['result.json'], run))
    xn = _json(gzip.decompress(_source(geometry['files']['native-result.json.gz'], run)))
    basis = trial['basis']
    if xp['policy']['free_r_test_value'] != plan['policy']['free_r_test_value']:
        raise RecipeError('Geometry and anomalous observation protocol uses different Free-R test values')
    if canonical(xp['references']) != canonical(plan['references']):
        raise RecipeError('Geometry and anomalous stages require the same reference scattering')
    # Geometry and B may differ; observations, selected flags, phase source and
    # native machinery must not. Reference values are checked per shared element.
    common = dict(observations=doc['input_sources']['observations'], metadata=plan['metadata'],
                  reflection_input_hash=basis['reflection_input_hash'],
                  native_protocol=basis['native_protocol'], worker_sha256=basis['worker_sha256'],
                  native_version=basis['native_version'], native_source_hashes=basis['native_source_hashes'],
                  policy=basis['policy'], tolerances=basis['tolerances'],
                  background_policy=basis['background_policy'], nuisance_policy=basis['nuisance_policy'],
                  phase_policy=basis['phase_policy'],
                  geometry_phases=geometry['input_sources']['phases'], phase_metadata=xp['phases'],
                  geometry_reflection_hash=xn['reflection_before']['hash'],
                  geometry_worker_sha256=geometry['worker_sha256'], geometry_protocol=geometry['protocol'],
                  geometry_native_version=xn['native_version'], geometry_native_source_hashes=xn['native_source_hashes'],
                  geometry_policy={k:v for k,v in xp['policy'].items() if k not in (*BUDGET_AXES,'weight_controls')},
                  observation_policy=xp['observation_policy'], scattering_policy=xp['scattering_policy'])
    conditions = dict(hypothesis=geometry['parent']['hypothesis_id'],
                      input_model_sha256=xp['input_model_sha256'],
                      xyz_options=xp['options'], fdp_options=plan['options'],
                      geometry_endpoint_sha256=geometry['files']['final.pdb']['sha256'],
                      b_calibration=plan.get('b_calibration'),
                      occupancy_vector=trial['occupancy_vector'], groups=basis['groups'],
                      geometry_groups=xp['groups'], references=plan['references'])
    sites=[]
    for site in trial['result']['sites']:
        expected=site['reference_f_double_prime']
        sites.append(dict(site, fdp_ratio=site['f_double_prime']/expected if expected>0 else None,
                          normalization_status='DEFINED' if expected>0 else 'ZERO_REFERENCE'))
    def maps(doc):
        return {name:ref for name,ref in doc['files'].items() if name.startswith('map-') and name.endswith('.mtz')}
    result=trial['result']
    row=dict(trial_id=trial['trial_id'], manifest=trial['ref'], conditions=conditions,
             geometry=dict(trial_id=geometry['trial_id'], manifest=parent,
                           hypothesis=geometry['parent'], settings=xp['options'],
                           fit=fit_context(xr['r_work'],xr['r_free']), sites=xr['sites'],
                           recipe_geometry=recipe_diagnostics(run,Path(parent['relative_path']).parent),
                           maps=xr.get('map_diagnostics'), map_artifacts=maps(geometry)),
             anomalous=dict(settings=plan['options'], fit=fit_context(result['r_work'],result['r_free']),
                            sites=sites, fitted_site_count=len(sites), wavelength_A=result['wavelength_A'],
                            b_calibration=plan.get('b_calibration'), map=result.get('anomalous_map'),
                            map_artifacts=maps(doc)))
    return dict(ref=trial['ref'], common=common, references=plan['references'], row=row)


def _load_candidates(run, trials):
    if not isinstance(trials,(list,tuple)) or not 2<=len(trials)<=MAX_TRIALS:
        raise RecipeError(f'Review 2 to {MAX_TRIALS} explicit audited native-XYZ/fdp candidates')
    loaded=[_load_candidate(run,p) for p in trials]
    if len({v['row']['trial_id'] for v in loaded})!=len(loaded):
        raise RecipeError('Duplicate trial in candidate review')
    common=canonical(loaded[0]['common'])
    if any(canonical(v['common'])!=common for v in loaded[1:]):
        raise RecipeError('Candidates must share observations, flags, phases and native protocol')
    references={}
    for item in loaded:
        for reference in item['references']:
            key=reference['element']
            if key in references and canonical(references[key])!=canonical(reference):
                raise RecipeError('Candidates have conflicting wavelength reference scattering')
            references[key]=reference
    return loaded


def _report(loaded):
    baseline=loaded[0]['row']['conditions']
    rows=[dict(item['row'], changed_from_first=[key for key,value in item['row']['conditions'].items()
                                              if canonical(value)!=canonical(baseline[key])]) for item in loaded]
    references={r['element']:r for item in loaded for r in item['references']}
    return dict(kind='metal-candidate-review-report',schema_version=1,protocol=PROTOCOL,
                status='CANDIDATE_REVIEW',comparison_basis=loaded[0]['common'],
                references=[references[k] for k in sorted(references)],candidates=rows,
                controlled_sensitivity='NOT_ESTABLISHED',convergence='NOT_ESTABLISHED',
                scientific_acceptance='NOT_ASSESSED',automatic_checkpoint_selection=False,
                refine_doctor=dict(status='NOT_EXECUTED',route='existing_refine_doctor',
                                   limitation='Exact metal-checkpoint execution bridge remains pending'),
                notes=[
                    'Each candidate groups all fitted sites from one frozen-fdp snapshot; node names are local to its hypothesis.',
                    'Geometry and anomalous R factors belong to different targets and observation policies; compare each stage separately.',
                    'Changed conditions are descriptive, not proof of a one-variable experiment, convergence or a winning geometry.',
                    'Missing maps are unavailable, never zero. Model-assisted/phased maps and their sigma samples are not independent evidence.',
                    'Rwork < 0.30 and Rwork < Rfree are numerical conditions only; Rfree gaps, geometry and anomalous evidence still need review.',
                    'Fitted-site count is the number of fitted nodes, not an inferred atom count; explicit count scopes belong to fdp_count.',
                    'Base/donor B preparation, fixed Q and fixed f-prime remain visible; f-double-prime/reference is descriptive, including negative values.'])


def _allocate(run):
    root=run/'Metal'
    if root.is_symlink():raise RecipeError('Metal root must not be a symlink')
    numbers=[int(m.group(1)) for p in root.iterdir() if (m:=re.fullmatch(r'candidate_review_(\d{3,})',p.name))]
    index=max(numbers,default=0)+1
    while True:
        directory=root/f'candidate_review_{index:03d}'
        try:
            directory.mkdir()
            return directory
        except FileExistsError:index+=1


def _manifest(run,directory,loaded):
    doc=dict(kind='metal-candidate-review',schema_version=1,protocol=PROTOCOL,status='CANDIDATE_REVIEW',
             inputs=[v['ref'] for v in loaded],files={'report':_reference(directory/'report.json',run)},
             scientific_acceptance='NOT_ASSESSED',automatic_checkpoint_selection=False)
    doc['review_id']=digest(doc)
    return doc


def build_review(run,trials):
    """Save grouped, descriptive candidate evidence without any native execution."""
    run=Path(run).expanduser().resolve()
    loaded=_load_candidates(run,trials);report=_report(loaded)
    directory=_allocate(run)
    try:
        (directory/'report.json').write_bytes(_json_bytes(report))
        repeated=_load_candidates(run,[Path(v['ref']['relative_path']).parent for v in loaded])
        if canonical(repeated)!=canonical(loaded):raise RecipeError('Candidate changed during review publication')
        doc=_manifest(run,directory,loaded)
        (directory/'manifest.json').write_bytes(_json_bytes(doc))
        return doc
    except BaseException as exc:
        with (directory/'failure.json').open('xb') as handle:
            handle.write(_json_bytes(dict(status='FAILED',exception=type(exc).__name__,error=str(exc))))
        raise


def verify_review(run,directory):
    """Replay a saved review from anchored, audited trials; never find by basename."""
    run=Path(run).expanduser().resolve();directory=Path(directory).expanduser()
    if not directory.is_absolute():directory=run/directory
    if directory.is_symlink() or directory.parent.is_symlink():raise RecipeError('Review must not be a symlink')
    directory=directory.resolve()
    if directory.parent!=run/'Metal' or not re.fullmatch(r'candidate_review_\d{3,}',directory.name):
        raise RecipeError('Require an explicit numbered candidate review within this run')
    try:
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
            raise RecipeError('Review payload must contain regular files only')
        if {p.name for p in directory.iterdir()}!={'manifest.json','report.json'}:
            raise RecipeError('Failed or unexpected review inventory')
        doc=_json((directory/'manifest.json').read_bytes())
        if (doc.get('kind')!='metal-candidate-review' or type(doc.get('schema_version'))is not int
                or doc['schema_version']!=1 or doc.get('protocol')!=PROTOCOL):
            raise RecipeError('Unsupported candidate review manifest')
        refs=doc['inputs']
        if not isinstance(refs,list) or not 2<=len(refs)<=MAX_TRIALS:raise RecipeError('Invalid review input count')
        for ref in refs:
            if ref.get('anchor')!='run' or Path(ref['relative_path']).name!='manifest.json':
                raise RecipeError('Review requires run-anchored trial manifests')
            _source(ref,run)
        loaded=_load_candidates(run,[Path(ref['relative_path']).parent for ref in refs])
        if canonical([v['ref'] for v in loaded])!=canonical(refs):raise RecipeError('Review input references changed')
        if (directory/'report.json').read_bytes()!=_json_bytes(_report(loaded)):
            raise RecipeError('Candidate report differs from endpoint replay')
        if canonical(doc)!=canonical(_manifest(run,directory,loaded)):
            raise RecipeError('Candidate manifest or review state changed')
        return doc
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot verify candidate review: '+str(exc)) from exc
