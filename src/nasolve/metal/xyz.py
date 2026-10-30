"""Phase-restrained XYZ/isotropic-ADP probes before frozen anomalous trials.

This is a separate review artifact. It does not select a checkpoint, infer metal
identity/count or calibrate metal B. The separate fdp adapter can consume a
verified endpoint under an explicit B policy without changing its review status.
"""
import gzip
import hashlib
import math
import os
from pathlib import Path
import re
import signal
import subprocess

from .binding import AtomKey
from .context import _reference, parse_pdb
from .fdp import NATIVE_VERSION, _integer, audit_reflections, make_plan as scattering_plan
from .materialize import _json, _json_bytes, _source, verify_hypothesis
from .recipe import RecipeError, canonical, checksum, digest, number
from .scattering import inspect_observations, reference_scattering
from ..refine_doctor import audit_free_r_flags
from ..run_context import resolve_artifact_path

PROTOCOL = 'metal-phased-xyz-v1'
PHASE_FAMILIES = (['HLAM','HLBM','HLCM','HLDM'], ['HLA','HLB','HLC','HLD'], ['HL_A','HL_B','HL_C','HL_D'])


def make_plan(raw, sites, metadata, references, phases, *, cycles=3, free_r_test_value=0, xyz_weight_scale=None,capture_maps=False):
    """Declare merged-observation MLHL geometry; anomalous data remain intact.

    Phenix 2.2.1 cannot combine MLHL with nonzero anomalous scattering. f-prime
    remains fixed at the wavelength reference; f-double-prime is zero only in
    this geometry step, never a measured anomalous result.
    """
    if (not isinstance(phases,dict) or set(phases)!={'sha256','size','labels'}
            or phases['labels'] not in PHASE_FAMILIES or type(phases['size'])is not int or phases['size']<=0):
        raise RecipeError('Require one explicit complete supported HL quartet and phase checksum/size')
    checksum(phases['sha256'],'phase file')
    parsed=parse_pdb(raw)
    if any(s['anisou'] is not None for s in parsed.to_dict()['atomic_state']):
        raise RecipeError('XYZ v1 requires isotropic input; no implicit ANISOU conversion')
    if len({s['node_id'] for s in sites})!=len(sites):raise RecipeError('Duplicate metal node')
    seed,model=scattering_plan(raw,sites,metadata,references,fit_nodes=[s['node_id'] for s in sites],
                              cycles=cycles,free_r_test_value=free_r_test_value)
    if model!=raw:raise RecipeError('XYZ preparation must preserve the input model')
    groups=seed['groups']
    for group in groups:group.update(refine_fdp=False,f_double_prime_start=0.)
    policy=dict(seed['policy'],strategy=['individual_sites','individual_adp'],target='mlhl',
                experimental_phases=True,anomalous_observations=False,isotropic_selection='all',
                anisotropic_selection=None,automatic_metal_linking=False,optimize_xyz_weight=False,optimize_adp_weight=False)
    if type(capture_maps) is not bool:raise RecipeError('Require a boolean map-capture option')
    options=dict(cycles=cycles,free_r_test_value=free_r_test_value)
    extra={}
    if capture_maps:
        from .map_diagnostics import request
        options['capture_maps']=True
        extra['map_capture']=request()
    if xyz_weight_scale is not None:
        scale=number(xyz_weight_scale,'XYZ experimental-weight scale')
        if not .001 <= scale <= 10.:
            raise RecipeError('Require XYZ experimental-weight scale between 0.001 and 10')
        options['xyz_weight_scale']=scale
        policy['weight_controls']=dict(wxc_scale=scale,wxu_scale=1.,wc=1.,wu=1.,fix_wxc=None,fix_wxu=None)
    return dict(protocol=PROTOCOL,options=options,
        policy=policy,groups=groups,sites=sites,metadata=metadata,references=references,phases=phases,
        input_model_sha256=hashlib.sha256(raw).hexdigest(),
        observation_policy='native_merge_Bijvoet_mates_for_geometry_keep_original_anomalous_file',
        scattering_policy='fixed_reference_fp_zero_fdp_for_MLHL_geometry_only',
        geometry_policy='inherited_and_explicit_recipe_restraints_no_automatic_metal_links',**extra)


def parameters(plan, resources):
    labels=','.join(plan['phases']['labels']);p=plan['policy']
    lines=['data_manager {',' miller_array {','  file = observations.mtz',
           '  labels { name = "F(+),SIGF(+),F(-),SIGF(-)" }','  labels { name = FreeR_flag }',' }',
           ' miller_array {','  file = phases.mtz',f'  labels {{ name = "{labels}" }}',' }',
           ' fmodel { xray_data {','  outliers_rejection = False','  force_anomalous_flag_to_be_equal_to = False',
           '  r_free_flags {',f'   test_flag_value = {p["free_r_test_value"]}','   generate = False','  }',' } }','}',
           'refinement {',' refine {','  strategy = *individual_sites *individual_adp',
           '  adp.individual {','   isotropic = all','   anisotropic = None','  }','  anomalous_scatterers {']
    for g in plan['groups']:
        lines+=['   group {','    selection = '+canonical(g['selection']),
                '    f_prime = '+repr(g['f_prime']),'    f_double_prime = 0','    refine = None','   }']
    lines+=['  }',' }',' main {',f'  number_of_macro_cycles = {p["cycles"]}',
            '  random_seed = 42','  nproc = 1','  target = mlhl','  scattering_table = n_gaussian',
            '  bulk_solvent_and_scale = True','  apply_overall_isotropic_scale_to_adp = False',
            '  nqh_flips = False','  flip_peptides = False','  ordered_solvent = False',
            '  simulated_annealing = False','  find_and_add_hydrogens = False','  update_f_part1 = False',' }',
            ' bulk_solvent_and_scale { apply_back_trace = False }',' group_anomalous {',
            '  find_automatically = False','  number_of_minimizer_cycles = 3','  lbfgs_max_iterations = 20',' }',
            ' target_weights {','  optimize_xyz_weight = False','  optimize_adp_weight = False',
            *[f'  {name} = {value}' for name,value in p.get('weight_controls',{}).items()],' }',
            ' pdb_interpretation.automatic_linking.link_metals = False',
            ' electron_density_maps { apply_default_maps = False }',' output {',
            '  write_geo_file = False','  write_final_geo_file = False','  write_maps = False',
            '  write_map_coefficients = False','  write_model_cif_file = False',
            '  write_reflection_cif_file = False','  export_final_f_model = False',
            '  write_mtz_file = False','  write_final_pdb_file = False','  write_def_file = False',' }','}',
            'output {',' prefix = native',' serial = 1',' overwrite = False','}','']
    return '\n'.join(lines).encode(),['input.pdb','observations.mtz','phases.mtz',*resources,'parameters.phil',
                                     'experimental_phases.file_name=phases.mtz','experimental_phases.labels='+labels]


def audit_phases(before, after, reflection_indices):
    for capture in (before,after):
        rows=capture['rows'];keys=[]
        if not rows or type(capture['count'])is not int or capture['count']!=len(rows):
            raise RecipeError('Missing active phase evidence')
        for key,values in rows:
            if (not isinstance(key,list) or len(key)!=3 or any(type(x)is not int for x in key)
                    or not isinstance(values,list) or len(values)!=4):raise RecipeError('Invalid phase row')
            for v in values:number(v,'HL coefficient')
            keys.append(tuple(key))
        if keys!=sorted(set(keys)) or keys!=reflection_indices:
            raise RecipeError('Active phases must cover exactly the refinement reflection indices')
        if digest(rows)!=capture['hash']:raise RecipeError('Phase signature changed')
    if canonical(before)!=canonical(after):raise RecipeError('Active phase coefficients changed during refinement')
    return dict(status='UNCHANGED',hash=before['hash'],count=before['count'])


def _atom_permutation(expected, actual):
    """Require a bijection over complete atom keys, never element/name proximity."""
    expected = [canonical(k) for k in expected]
    actual = [canonical(k) for k in actual]
    if len(set(actual)) != len(actual) or len(set(expected)) != len(expected) or set(actual) != set(expected):
        raise RecipeError('Native/serialized atom identities changed or duplicated')
    positions = {key:i for i,key in enumerate(actual)}
    return [positions[key] for key in expected]


def audit_result(plan, model, native, final_model):
    """Audit fixed Q/scattering/identity; report allowed XYZ/B changes separately."""
    if (native.get('completed')is not True or native.get('execution')!='complete'
            or native.get('protocol')!=PROTOCOL or native.get('native_version')!=NATIVE_VERSION):
        raise RecipeError('Missing qualified native XYZ completion')
    if hashlib.sha256(model).hexdigest()!=plan['input_model_sha256']:raise RecipeError('Input model differs from XYZ plan')
    if canonical(native['policy'])!=canonical(plan['policy']):raise RecipeError('Native XYZ policy changed')
    if native.get('phase_labels')!=plan['phases']['labels']:raise RecipeError('Native phase labels changed')
    symmetries=[native[k] for k in ('input_symmetry','symmetry_before','symmetry_after')]
    if (len({s['space_group_number'] for s in symmetries})!=1
            or len(symmetries[2]['unit_cell'])!=6
            or any(abs(number(a,'native cell')-number(b,'native cell'))>1e-9
                   for a,b in zip(symmetries[1]['unit_cell'],symmetries[2]['unit_cell']))):
        raise RecipeError('Crystal symmetry changed')
    initial_cell=symmetries[0]['unit_cell'];native_cell=symmetries[1]['unit_cell']
    if (not isinstance(native_cell,list) or len(native_cell)!=6
            or any(abs(number(a,'input cell')-number(b,'native cell'))>(.000501 if i<3 else .005001)
                   for i,(a,b) in enumerate(zip(initial_cell,native_cell)))):
        raise RecipeError('Input crystal symmetry changed beyond PDB precision')
    cell=symmetries[1]['unit_cell'];sg=symmetries[0]['space_group_number']
    if not isinstance(cell,list) or len(cell)!=6 or any(number(v,'unit cell')<=0 for v in cell):raise RecipeError('Invalid unit cell')
    if type(sg)is not int or not 1<=sg<=230:raise RecipeError('Invalid space-group number')
    serialized_groups=[]
    for raw in (model,final_model):
        headers=[line for line in raw.decode('ascii').splitlines() if line.startswith('CRYST1')]
        if len(headers)!=1:raise RecipeError('Require one serialized crystal cell')
        serialized_groups.append(' '.join(headers[0][55:66].split()))
        values=[float(headers[0][a:b]) for a,b in ((6,15),(15,24),(24,33),(33,40),(40,47),(47,54))]
        if any(abs(a-b)>(.000501 if i<3 else .005001) for i,(a,b) in enumerate(zip(values,cell))):
            raise RecipeError('Serialized crystal cell differs from native state')
    if serialized_groups[0]!=serialized_groups[1]:raise RecipeError('Serialized space-group setting changed')
    reflections=audit_reflections(native['reflection_before'],native['reflection_after'],anomalous=False)
    phases=audit_phases(native['phases_before'],native['phases_after'],[tuple(r[0]) for r in native['reflection_after']['rows']])
    source=native['phase_source'];source_keys=[tuple(row[0]) for row in source['rows']]
    audit_phases(source,source,source_keys)
    lookup={tuple(key):values for key,values in source['rows']}
    if any(lookup.get(tuple(key))!=values for key,values in native['phases_before']['rows']):
        raise RecipeError('Active phase coefficients differ from captured source array')
    phases['source_count']=source['count']
    phases['source_hash']=source['hash']
    phases['zero_coefficient_count']=sum(all(v==0 for v in row[1]) for row in native['phases_before']['rows'])
    before=parse_pdb(model);after=parse_pdb(final_model);actual=native['atoms']
    states=before.to_dict()['atomic_state'];last=after.to_dict()['atomic_state']
    if len(actual)!=len(before.snapshot.atoms) or len(actual)!=len(after.snapshot.atoms):
        raise RecipeError('Native/serialized atom inventory changed')
    keys = [a.key.to_dict() for a in before.snapshot.atoms]
    native_order = _atom_permutation(keys, [a['key'] for a in actual])
    serialized_order = _atom_permutation(keys, [a.key.to_dict() for a in after.snapshot.atoms])
    if native.get('normal_scattering_before')!=[a.get('normal_scattering_type') for a in actual]:
        raise RecipeError('Normal scattering types changed')
    if len(native['groups'])!=len(plan['groups']):raise RecipeError('Anomalous group inventory changed')
    indices={}
    for expected,g in zip(plan['groups'],native['groups']):
        expected = dict(expected, indices=sorted(native_order[i] for i in expected['indices']))
        if canonical({k:g[k] for k in expected})!=canonical(expected) or abs(number(g['f_double_prime'],'fdp'))>1e-10:
            raise RecipeError('Fixed scattering group changed')
        for i in g['indices']:
            if i in indices:raise RecipeError('Overlapping scattering groups')
            indices[i]=g
    if set(indices)!=set(range(len(actual))):raise RecipeError('Incomplete scattering groups')
    source_hashes=native.get('native_source_hashes',{})
    if set(source_hashes)!={'fp_fdp','bulk_scaling','anomalous_minimizer','xray_kernel','lbfgs_kernel'}:raise RecipeError('Missing native source provenance')
    for v in source_hashes.values():checksum(v,'native source fingerprint')
    charges=lambda raw:[l[78:80].strip() for l in raw.decode('ascii').splitlines() if l[:6].strip() in {'ATOM','HETATM'}]
    first_charges,last_charges=charges(model),charges(final_model)
    changes=[]
    for i,(a,s) in enumerate(zip(before.snapshot.atoms,states)):
        ni, si = native_order[i], serialized_order[i]
        b, out, end = actual[ni], after.snapshot.atoms[si], last[si]
        if (canonical(b['key'])!=canonical(a.key.to_dict()) or out.key!=a.key or b['element']!=a.element
                or out.element!=a.element or b.get('charge')!=first_charges[i] or last_charges[si]!=first_charges[i]):
            raise RecipeError('Atom identity/element/charge changed')
        xyz=b['xyz']
        if not isinstance(xyz,list) or len(xyz)!=3:raise RecipeError('Invalid native XYZ')
        for v in xyz:number(v,'native coordinate')
        bval=number(b['b_iso'],'native B');q=number(b['occupancy'],'native Q')
        if bval<0 or b['u_cart'] is not None or end['anisou'] is not None:raise RecipeError('Invalid isotropic ADP endpoint')
        if (abs(q-s['occupancy'])>1e-10 or abs(number(b['fp'],'native fp')-indices[ni]['f_prime'])>1e-10
                or abs(number(b['fdp'],'native fdp'))>1e-10):raise RecipeError('Fixed Q or scattering changed')
        if (max(abs(v-w) for v,w in zip(xyz,out.xyz))>.000501 or abs(bval-end['b_iso'])>.005001
                or end['occupancy']!=s['occupancy']):raise RecipeError('Serialized endpoint differs from native state')
        changes.append(dict(key=a.key.to_dict(),element=a.element,xyz=xyz,occupancy=q,b_iso=bval,
                            displacement_A=math.dist(a.xyz,xyz),delta_b_A2=bval-s['b_iso']))
    by_key={canonical(a['key']):a for a in changes}
    sites=[dict(by_key[canonical(s['key'])],node_id=s['node_id']) for s in plan['sites']]
    result = dict(status='XYZ_REVIEW',fixed_state_audit='PASS',sites=sites,
                maximum_displacement_A=max(a['displacement_A'] for a in changes),
                maximum_absolute_delta_b_A2=max(abs(a['delta_b_A2']) for a in changes),
                reflection_signature=reflections,phase_signature=phases,
                r_work=number(native['r_work'],'Rwork'),r_free=number(native['r_free'],'Rfree'),
                native_version=native['native_version'],scientific_acceptance='NOT_ASSESSED',
                automatic_checkpoint_selection=False,convergence='NOT_INDEPENDENTLY_ASSESSED',
                fdp_quantitation_ready=False,environmental_b_applied=False)
    if 'fit_diagnostics' in native:
        from .fit_diagnostics import summarize
        result['fit_diagnostics']=summarize(native['fit_diagnostics'],native['reflection_after'],native['r_work'],native['r_free'])
    if ('map_capture' in plan) != ('map_diagnostics' in native):
        raise RecipeError('Requested map capture missing or unexpected')
    if 'map_capture' in plan:
        from .map_diagnostics import request, summarize as summarize_maps
        if plan['map_capture']!=request():raise RecipeError('Map capture policy changed')
        result['map_diagnostics']=summarize_maps(native['map_diagnostics'],native,plan['sites'],plan['metadata']['wavelength_A'])
    identity = list(range(len(keys)))
    if native_order != identity or serialized_order != identity:
        result['atom_order_mapping'] = dict(input_to_native=native_order, input_to_serialized=serialized_order,
                                           policy='exact_atom_key_bijection')
    return result


def _input_bundle(run, hypothesis):
    h=verify_hypothesis(run,hypothesis);resources=[]
    for ref in h['inputs']['restraints']+[h['files']['restraints']]:
        path=resolve_artifact_path(ref,run)
        if path is None or path.suffix.lower() not in {'.cif','.phil','.eff','.params'}:
            raise RecipeError('Unsupported inherited restraint resource')
        resources.append((f'resource_{len(resources):03d}'+path.suffix.lower(),_source(ref,run)))
    parent=run/Path(h['files']['model']['relative_path']).parent/'manifest.json'
    return h,_source(h['files']['model'],run),resources,_reference(parent,run)



def _recipe_diagnostics(parent_preview, model):
    """Measure explicit recipe terms at serialized endpoint precision."""
    from .geometry import _preview
    bound = _preview(parent_preview, model)
    rows = []
    for term in bound['restraints']:
        z = None
        if term['status'] == 'resolved':
            z = number((term['measured']-term['target'])/term['sigma'], 'recipe sigma deviation')
        rows.append(dict(term, signed_sigma_deviation=z))
    values = [abs(r['signed_sigma_deviation']) for r in rows if r['signed_sigma_deviation'] is not None]
    return dict(protocol='metal-recipe-endpoint-v1', model_sha256=hashlib.sha256(model).hexdigest(),
                recipe_sha256=bound['inputs']['recipe_sha256'], restraints=rows,
                active_resolved_count=len(values), maximum_absolute_sigma_deviation=max(values, default=None),
                scope='explicit_recipe_only_excludes_inherited_and_nonbonded_terms',
                coordinate_precision='serialized_PDB', native_proxy_equivalence='NOT_ASSESSED',
                scientific_acceptance='NOT_ASSESSED', automatic_checkpoint_selection=False)


def recipe_diagnostics(run, directory):
    """Inspect a verified old/new XYZ endpoint offline; never edit its bundle."""
    run = Path(run).expanduser().resolve()
    doc = verify_xyz(run, directory)
    h = verify_hypothesis(run, Path(doc['parent']['manifest']['relative_path']).parent)
    return _recipe_diagnostics(_json(_source(h['files']['preview'], run)),
                               _source(doc['files']['final.pdb'], run))


def _allocate(run):
    root=run/'Metal'
    if root.is_symlink():raise RecipeError('Metal root must not be a symlink')
    index=max([int(m.group(1)) for p in root.iterdir() if (m:=re.fullmatch(r'xyz_(\d{3,})',p.name))],default=0)+1
    while True:
        p=root/f'xyz_{index:03d}'
        try:p.mkdir();return p
        except FileExistsError:index+=1


def _native(directory,native,timeout):
    worker=Path(__file__).with_name('_xyz_native.py')
    with (directory/'native.log').open('xb') as log:
        proc=subprocess.Popen([str(native.executables['phenix.python']),'-B',str(worker),'native-plan.json'],
            cwd=directory,env=native.environment,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RecipeError('Native XYZ timeout; attempt retained') from exc
        finally:
            # Native children must not survive success, timeout or interruption.
            try:os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            proc.wait()
    if proc.returncode:raise RecipeError(f'Native XYZ failed ({proc.returncode}); inspect retained native.log')
    return _json(gzip.decompress((directory/'native-result.json.gz').read_bytes()))


def run_xyz(run,hypothesis,*,native,phases,phase_labels,cycles=3,free_r_test_value=0,timeout=240,xyz_weight_scale=None,capture_maps=False):
    """Explicit API-only experiment; phases must have a declared portable anchor."""
    run=Path(run).expanduser().resolve();_integer(timeout,10,600,'timeout seconds')
    h,model,resources,parent_ref=_input_bundle(run,hypothesis)
    phase_bytes=_source(phases,run)
    phase_meta=dict(sha256=phases['sha256'],size=phases['size'],labels=phase_labels)
    obs=_source(h['inputs']['observations'],run);obs_path=resolve_artifact_path(h['inputs']['observations'],run)
    metadata=inspect_observations(obs_path,executable=native.executables['phenix.mtz.dump'],environment=native.environment)
    references=reference_scattering({a.element for a in parse_pdb(model).snapshot.atoms},metadata['wavelength_A'],
        executable=native.executables['phenix.python'],version=native.version,environment=native.environment)
    plan=make_plan(model,h['sites'],metadata,references,phase_meta,cycles=cycles,free_r_test_value=free_r_test_value,xyz_weight_scale=xyz_weight_scale,capture_maps=capture_maps)
    phil,args=parameters(plan,[name for name,_ in resources]);directory=_allocate(run)
    try:
        content={'input.pdb':model,'observations.mtz':obs,'phases.mtz':phase_bytes,'parameters.phil':phil,
            'plan.json':_json_bytes(plan),'native-plan.json':_json_bytes({'plan':plan,'args':args}),**dict(resources)}
        for name,raw in content.items():(directory/name).write_bytes(raw)
        audit=audit_free_r_flags(directory/'observations.mtz','FreeR_flag',free_r_test_value,
                                native.executables['phenix.python'],directory,environment=native.environment)
        (directory/'free-r.json').write_bytes(_json_bytes(dict(status=audit.status,usable=audit.valid,details=audit.details,warnings=list(audit.warnings))))
        if not audit.valid:raise RecipeError('Original Free-R audit failed')
        evidence=_native(directory,native,timeout)
        result=audit_result(plan,model,evidence,(directory/'final.pdb').read_bytes())
        if 'map_diagnostics' in evidence:
            from .map_diagnostics import verify_files
            verify_files(evidence['map_diagnostics'],directory)
        if any((directory/name).read_bytes()!=raw for name,raw in content.items()):raise RecipeError('Frozen XYZ input changed')
        _source(phases,run);_source(parent_ref,run);verify_hypothesis(run,hypothesis)
        (directory/'result.json').write_bytes(_json_bytes(result))
        if 'fit_diagnostics' in evidence:
            geometry = _recipe_diagnostics(_json(_source(h['files']['preview'],run)), (directory/'final.pdb').read_bytes())
            (directory/'recipe-geometry.json').write_bytes(_json_bytes(geometry))
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):raise RecipeError('Unexpected native artifact')
        doc=dict(kind='metal-xyz-trial',schema_version=1,protocol=PROTOCOL,status='XYZ_REVIEW',
            parent=dict(hypothesis_id=h['hypothesis_id'],manifest=parent_ref),input_sources=dict(h['inputs'],phases=phases),
            files={p.name:_reference(p,run) for p in sorted(directory.iterdir())},
            worker_sha256=hashlib.sha256(Path(__file__).with_name('_xyz_native.py').read_bytes()).hexdigest(),
            execution=dict(phenix_version=evidence['native_version'],timeout_seconds=timeout,mode='complete'),
            automatic_checkpoint_selection=False,scientific_acceptance='NOT_ASSESSED')
        doc['trial_id']=digest(doc);(directory/'manifest.json').write_bytes(_json_bytes(doc));return doc
    except BaseException as exc:
        (directory/'failure.json').write_bytes(_json_bytes(dict(status='FAILED',error=str(exc),exception=type(exc).__name__)))
        raise


def verify_xyz(run,directory):
    """Replay provenance and audits offline; never re-run captured code."""
    run=Path(run).expanduser().resolve();directory=Path(directory).expanduser()
    if not directory.is_absolute():directory=run/directory
    if directory.is_symlink() or directory.parent.is_symlink():raise RecipeError('XYZ directory must not be a symlink')
    directory=directory.resolve()
    if directory.parent!=run/'Metal' or not re.fullmatch(r'xyz_\d{3,}',directory.name):raise RecipeError('Require an explicit numbered XYZ trial')
    try:
        doc=_json((directory/'manifest.json').read_bytes());check=dict(doc);identity=check.pop('trial_id')
        if (digest(check)!=identity or doc['kind']!='metal-xyz-trial' or type(doc['schema_version'])is not int
                or doc['schema_version']!=1 or doc['protocol']!=PROTOCOL or doc['status']!='XYZ_REVIEW'
                or doc['automatic_checkpoint_selection']is not False or doc['scientific_acceptance']!='NOT_ASSESSED'
                or doc['execution']['mode']!='complete' or doc['execution']['phenix_version']!=NATIVE_VERSION):
            raise RecipeError('Unsupported or changed XYZ manifest')
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):raise RecipeError('Unexpected XYZ payload')
        if {p.name for p in directory.iterdir()}!={'manifest.json',*doc['files']}:raise RecipeError('XYZ inventory changed')
        for name,ref in doc['files'].items():
            if Path(name).name!=name or ref!=_reference(directory/name,run):raise RecipeError('XYZ file reference changed')
            _source(ref,run)
        checksum(doc['worker_sha256'],'worker provenance');pref=doc['parent']['manifest'];_source(pref,run)
        if pref.get('anchor')!='run':raise RecipeError('XYZ parent must be in the run')
        h,model,resources,expected=_input_bundle(run,Path(pref['relative_path']).parent)
        if pref!=expected or doc['parent']['hypothesis_id']!=h['hypothesis_id']:raise RecipeError('XYZ parent changed')
        phases=doc['input_sources']['phases'];phase_bytes=_source(phases,run)
        if canonical(doc['input_sources'])!=canonical(dict(h['inputs'],phases=phases)):raise RecipeError('XYZ inputs changed')
        saved=_json((directory/'plan.json').read_bytes())
        plan=make_plan(model,h['sites'],saved['metadata'],saved['references'],
            dict(sha256=phases['sha256'],size=phases['size'],labels=saved['phases']['labels']),**saved['options'])
        phil,args=parameters(plan,[name for name,_ in resources])
        expected={'input.pdb':model,'observations.mtz':_source(h['inputs']['observations'],run),'phases.mtz':phase_bytes,
            'parameters.phil':phil,'plan.json':_json_bytes(plan),'native-plan.json':_json_bytes({'plan':plan,'args':args}),**dict(resources)}
        if any((directory/name).read_bytes()!=raw for name,raw in expected.items()):raise RecipeError('XYZ inputs differ from derivation replay')
        free=_json((directory/'free-r.json').read_bytes())
        if free.get('usable')is not True or free.get('status') not in {'VALID','NOISY'}:raise RecipeError('Invalid saved Free-R audit')
        evidence=_json(gzip.decompress((directory/'native-result.json.gz').read_bytes()))
        result=audit_result(plan,model,evidence,(directory/'final.pdb').read_bytes())
        if 'map_diagnostics' in evidence:
            from .map_diagnostics import verify_files
            verify_files(evidence['map_diagnostics'],directory)
        if (directory/'result.json').read_bytes()!=_json_bytes(result):raise RecipeError('XYZ audit changed')
        if 'fit_diagnostics' in result:
            geometry = _recipe_diagnostics(_json(_source(h['files']['preview'],run)), (directory/'final.pdb').read_bytes())
            if (directory/'recipe-geometry.json').read_bytes()!=_json_bytes(geometry):raise RecipeError('Endpoint recipe diagnostics changed')
        return doc
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot verify XYZ trial: '+str(exc)) from exc
