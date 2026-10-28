"""One audited fixed-q anomalous diagnostic; no search or checkpoint adoption."""
from pathlib import Path
import hashlib
import gzip
import json
import math
import re
import subprocess

from .binding import AtomKey
from .context import _reference, parse_pdb
from .export import atom_selection
from .environment import calibrate_b
from .geometry import verify_geometry
from .materialize import _json, _json_bytes, _source, verify_hypothesis
from .recipe import RecipeError, canonical, checksum, digest, number
from .scattering import inspect_observations, reference_scattering
from ..run_context import resolve_artifact_path
from ..refine_doctor import audit_free_r_flags

PROTOCOL = 'metal-frozen-fdp-v1'
NATIVE_VERSION = '2.2.1-6174'
TOLERANCES = {'xyz_A': 1e-7, 'occupancy': 1e-10, 'b_A2': 1e-7,
              'u_cart_A2': 1e-8, 'scattering_e': 1e-10}


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise RecipeError(f'{name} requires an integer between {low} and {high}')
    return value


def make_plan(raw, sites, metadata, references, *, fit_nodes, occupancies=None,
              cycles=3, minimizer_cycles=3, max_iterations=20, start_fdp=0., free_r_test_value=0,
              metal_b_policy=None, preview=None, resources=()):
    """Prepare optional environmental B, then exact groups and declared metal Q."""
    calibration = None
    if metal_b_policy is not None:
        calibration, raw = calibrate_b(raw, sites, preview, fit_nodes, metal_b_policy, resources=resources)
    parsed = parse_pdb(raw)
    atoms = parsed.snapshot.atoms
    state = parsed.to_dict()['atomic_state']
    if {a.key.model_id for a in atoms} != {'1'} or any(a.element in {'H', 'D'} for a in atoms):
        raise RecipeError('Frozen fdp v1 requires model 1 without H/D atoms')
    if any(s['occupancy'] < 0 or s['occupancy'] > 1 or s['b_iso'] < 0 for s in state):
        raise RecipeError('Invalid input occupancy or ADP')
    site_by_node = {s['node_id']: s for s in sites}
    if (not isinstance(fit_nodes, list) or not fit_nodes or len(fit_nodes)>12
            or any(not isinstance(n, str) for n in fit_nodes)
            or len(set(fit_nodes)) != len(fit_nodes) or set(fit_nodes)-set(site_by_node)):
        raise RecipeError('Select 1 to 12 distinct explicitly placed metal nodes')
    fit_nodes = sorted(fit_nodes)
    occupancies = {} if occupancies is None else occupancies
    if not isinstance(occupancies, dict) or set(occupancies)-set(site_by_node):
        raise RecipeError('Occupancies must name existing metal nodes')
    occupancies = {k: number(v, 'occupancy') for k,v in sorted(occupancies.items())}
    if any(not 0 <= q <= 1 or not math.isclose(q, round(q,2), abs_tol=1e-10,rel_tol=0) for q in occupancies.values()):
        raise RecipeError('Occupancy must be within 0 to 1 and PDB-representable to two decimals')
    start_fdp = number(start_fdp, 'starting f-double-prime')
    if not 0 <= start_fdp <= 100:
        raise RecipeError('Starting f-double-prime must be between 0 and 100 electrons')
    _integer(cycles,1,10,'macro cycles');_integer(minimizer_cycles,1,5,'minimizer cycles')
    _integer(max_iterations,1,100,'minimizer iterations');_integer(free_r_test_value,0,100,'Free-R test value')
    index_by_key = {a.key:i for i,a in enumerate(atoms)}
    site_indices = {}
    for node,s in site_by_node.items():
        key = AtomKey(**s['key'])
        if key not in index_by_key: raise RecipeError('Placed site is missing from geometry')
        site_indices[node] = index_by_key[key]
    changes = {site_indices[n]: q for n,q in occupancies.items()}
    lines = raw.decode('ascii').splitlines(keepends=True);i=0
    for pos,line in enumerate(lines):
        if line[:6].strip() in {'ATOM','HETATM'}:
            if i in changes:lines[pos]=line[:54]+f'{changes[i]:6.2f}'+line[60:]
            i+=1
    model=''.join(lines).encode('ascii')
    updated=parse_pdb(model).to_dict()['atomic_state']
    if any(updated[site_indices[n]]['occupancy'] <= 0 for n in fit_nodes):
        raise RecipeError('A fitted site requires positive q; q=0 fdp is not identifiable')
    wavelength=number(metadata['wavelength_A'],'wavelength')
    if wavelength<=0 or metadata['anomalous_labels'] != ['F(+)','SIGF(+)','F(-)','SIGF(-)'] or metadata['free_r_label']!='FreeR_flag':
        raise RecipeError('Require the explicit anomalous quartet, wavelength and original FreeR_flag')
    refs={r['element']:r for r in references}
    if len(refs)!=len(references) or set(refs)!={a.element for a in atoms}:
        raise RecipeError('References must cover every model element exactly once')
    for r in references:
        number(r['f_prime'],'reference f-prime')
        if number(r['f_double_prime'],'reference fdp')<0 or r['wavelength_A']!=wavelength:
            raise RecipeError('Invalid reference scattering')
        if r['provider']!='cctbx-sasaki' or r['native_version']!=NATIVE_VERSION:
            raise RecipeError('Frozen fdp v1 is qualified only for Phenix '+NATIVE_VERSION+' with Sasaki references')
        checksum(r['table_sha256'],'reference table')
    groups=[];selected=set()
    for node in fit_nodes:
        index=site_indices[node];a=atoms[index];r=refs[a.element]
        selection=atom_selection(a.key)
        groups.append(dict(id=node,selection=selection,indices=[index],element=a.element,
                           f_prime=r['f_prime'],f_double_prime_start=start_fdp,
                           reference_f_double_prime=r['f_double_prime'],refine_fp=False,refine_fdp=True))
        selected.add(index)
    exclusion=' or '.join('('+g['selection']+')' for g in groups)
    for symbol in sorted(refs):
        indices=[i for i,a in enumerate(atoms) if a.element==symbol and i not in selected]
        if not indices:continue
        r=refs[symbol]
        groups.append(dict(id='background:'+symbol,selection='element '+symbol+' and not ('+exclusion+')',
                           indices=indices,element=symbol,f_prime=r['f_prime'],
                           f_double_prime_start=r['f_double_prime'],reference_f_double_prime=r['f_double_prime'],
                           refine_fp=False,refine_fdp=False))
    policy=dict(strategy=['group_anomalous'],target='ml',cycles=cycles,minimizer_cycles=minimizer_cycles,
                max_iterations=max_iterations,random_seed=42,nproc=1,apply_overall_isotropic_scale_to_adp=False,
                apply_back_trace=False,update_f_part1=False,nqh_flips=False,ordered_solvent=False,
                find_and_add_hydrogens=False,find_anomalous_automatically=False,outliers_rejection=False,
                bulk_solvent_and_scale=True,experimental_phases=False,free_r_test_value=free_r_test_value)
    options=dict(fit_nodes=fit_nodes,occupancies=occupancies,cycles=cycles,minimizer_cycles=minimizer_cycles,
                 max_iterations=max_iterations,start_fdp=start_fdp,free_r_test_value=free_r_test_value)
    if calibration is not None:
        options["metal_b_policy"] = metal_b_policy
    plan = dict(protocol=PROTOCOL,options=options,metadata=metadata,references=references,groups=groups,policy=policy,
                tolerances=TOLERANCES,background_policy='fixed_Sasaki_reference_for_every_remaining_atom',
                nuisance_policy='profile_bulk_solvent_and_overall_scales_allow_only_uniform_F_sigma_rescaling_without_atomic_ADP_backtrace',
                phase_policy='model_phases_without_external_phase_restraints',input_model_sha256=hashlib.sha256(model).hexdigest())
    if calibration is not None:
        plan['b_calibration'] = calibration
    return plan, model


def parameters(plan, resource_names):
    """Portable relative filenames; the maintained worker uses these arguments."""
    p=plan['policy']
    lines=['data_manager {','  miller_array {','    file = observations.mtz',
           '    labels { name = "F(+),SIGF(+),F(-),SIGF(-)" }',
           '    labels { name = FreeR_flag }','  }',
           '  fmodel {','    xray_data {','      outliers_rejection = False',
           '      force_anomalous_flag_to_be_equal_to = True',
           '      r_free_flags {','        test_flag_value = '+str(p['free_r_test_value']),
           '        generate = False','      }','    }','  }','}',
           'refinement {','  refine {','    strategy = *group_anomalous',
           '    anomalous_scatterers {']
    for g in plan['groups']:
        lines+=['      group {','        selection = '+json.dumps(g['selection']),
                '        f_prime = '+repr(g['f_prime']),
                '        f_double_prime = '+repr(g['f_double_prime_start']),
                '        refine = '+('f_prime *f_double_prime' if g['refine_fdp'] else 'None'),'      }']
    lines+=['    }','  }','  main {',f'    number_of_macro_cycles = {p["cycles"]}',
            '    random_seed = 42','    nproc = 1','    target = "ml"','    scattering_table = n_gaussian',
            '    bulk_solvent_and_scale = True','    apply_overall_isotropic_scale_to_adp = False',
            '    nqh_flips = False','    flip_peptides = False','    ordered_solvent = False',
            '    simulated_annealing = False','    find_and_add_hydrogens = False',
            '    update_f_part1 = False','  }','  bulk_solvent_and_scale { apply_back_trace = False }',
            '  group_anomalous {','    find_automatically = False',
            f'    number_of_minimizer_cycles = {p["minimizer_cycles"]}',f'    lbfgs_max_iterations = {p["max_iterations"]}','  }',
            '  target_weights {','    optimize_xyz_weight = False','    optimize_adp_weight = False','  }',
            '  electron_density_maps { apply_default_maps = False }','  output {',
            '    write_geo_file = False','    write_final_geo_file = False','    write_maps = False',
            '    write_map_coefficients = False','    write_model_cif_file = False',
            '    write_reflection_cif_file = False','    export_final_f_model = False',
            '    write_mtz_file = False','    write_final_pdb_file = False','    write_def_file = False','  }','}',
            'output {','  prefix = native','  serial = 1','  overwrite = False','}','']
    return '\n'.join(lines).encode(),['input.pdb','observations.mtz',*resource_names,'parameters.phil']


def audit_reflections(before, after, *, anomalous=True):
    """Permit only common F/sigma scale; require declared anomalous state.

    Frozen fdp callers retain the strict anomalous=True default. The separate
    MLHL geometry audit explicitly requests merged observations.
    """
    if type(anomalous)is not bool:raise RecipeError("Require explicit anomalous boolean")
    for captured in (before,after):
        rows=captured['rows']
        if (captured.get('anomalous') is not anomalous or type(captured.get('count')) is not int
                or captured['count']!=len(rows) or not rows):
            raise RecipeError('Missing observations with the required anomalous state')
        keys=[]
        for row in rows:
            if (not isinstance(row,list) or len(row)!=4 or not isinstance(row[0],list)
                    or len(row[0])!=3 or any(type(v)is not int for v in row[0]) or type(row[3])is not bool):
                raise RecipeError('Invalid reflection identity/flag evidence')
            number(row[1],'F observation')
            if number(row[2],'sigma observation')<=0:raise RecipeError('Nonpositive observation sigma')
            keys.append(tuple(row[0]))
        if len(set(keys))!=len(keys) or keys!=sorted(keys):raise RecipeError('Duplicate or unsorted reflection evidence')
        free=sum(row[3] for row in rows)
        if free!=captured.get('free_count') or not 0<free<len(rows):raise RecipeError('Invalid Free-R membership')
        if hashlib.sha256(canonical(rows).encode()).hexdigest()!=captured['hash']:
            raise RecipeError('Reflection signature differs from evidence')
    first,last=before['rows'],after['rows']
    if len(first)!=len(last) or any(a[0]!=b[0] or a[3]!=b[3] for a,b in zip(first,last)):
        raise RecipeError('Reflection indices or Free-R assignments changed')
    index=max(range(len(first)),key=lambda i:abs(first[i][1]))
    if first[index][1]==0:raise RecipeError('All amplitudes are zero')
    scale=number(last[index][1]/first[index][1],'native amplitude scale')
    if scale<=0:raise RecipeError('Native amplitude scale is nonpositive')
    absolute=0.;relative=0.
    for a,b in zip(first,last):
        for field in (1,2):
            wanted=a[field]*scale;delta=abs(b[field]-wanted)
            absolute=max(absolute,delta);relative=max(relative,delta/max(1.,abs(wanted)))
            if not math.isclose(b[field],wanted,rel_tol=1e-10,abs_tol=1e-9):
                raise RecipeError('Observations changed beyond a uniform F/sigma scale')
    return dict(input_hash=before['hash'],output_hash=after['hash'],count=len(first),
                anomalous=anomalous,free_count=before['free_count'],uniform_F_sigma_scale=scale,
                maximum_absolute_residual=absolute,maximum_relative_residual=relative,
                relative_tolerance=1e-10,absolute_tolerance=1e-9,indices_and_flags='UNCHANGED')


def audit_result(plan, model, native):
    """Recompute the freeze verdict from retained native full-precision evidence."""
    if (native.get('completed') is not True or native.get('execution')!='complete'
            or native.get('protocol')!=PROTOCOL or native.get('native_version')!=NATIVE_VERSION):
        raise RecipeError('Native completion/version evidence is missing')
    if canonical(native['policy'])!=canonical(plan['policy']):
        raise RecipeError('Effective native parameter policy differs from frozen plan')
    reflections=audit_reflections(native['reflection_before'],native['reflection_after'])
    parsed=parse_pdb(model);atoms=parsed.snapshot.atoms;states=parsed.to_dict()['atomic_state']
    actual=native['atoms']
    charges=[line[78:80].strip() for line in model.decode('ascii').splitlines() if line[:6].strip() in {'ATOM','HETATM'}]
    if native.get('normal_scattering_before')!=[a.get('normal_scattering_type') for a in actual]:
        raise RecipeError('Normal scattering atom types changed')
    if set(native.get('native_source_hashes',{}))!={'fp_fdp','bulk_scaling','anomalous_minimizer','xray_kernel','lbfgs_kernel'}:
        raise RecipeError('Native source/kernel fingerprints are missing')
    for value in native['native_source_hashes'].values():checksum(value,'native source fingerprint')
    if len(actual)!=len(atoms) or len(native['groups'])!=len(plan['groups']):
        raise RecipeError('Native atom/group inventory changed')
    by_index={}
    for expected,group in zip(plan['groups'],native['groups']):
        comparison={k:group[k] for k in expected}
        if canonical(comparison)!=canonical(expected):raise RecipeError('Native group membership or parameter freedoms changed')
        fdp=number(group['f_double_prime'],'fitted f-double-prime')
        if not expected['refine_fdp'] and abs(fdp-expected['f_double_prime_start'])>TOLERANCES['scattering_e']:
            raise RecipeError('Background scattering changed')
        for i in group['indices']:
            if i in by_index:raise RecipeError('Native scattering groups overlap')
            by_index[i]=group
    if set(by_index)!=set(range(len(atoms))):raise RecipeError('Native scattering groups do not cover all atoms')
    maxima={'xyz_A':0.,'occupancy':0.,'b_A2':0.,'u_cart_A2':0.,'scattering_e':0.}
    for i,(a,s,b) in enumerate(zip(atoms,states,actual)):
        if canonical(b['key'])!=canonical(a.key.to_dict()) or b['element']!=a.element or b.get('charge')!=charges[i]:
            raise RecipeError('Native atom identity or element changed')
        if not isinstance(b['xyz'],list) or len(b['xyz'])!=3:raise RecipeError('Invalid native XYZ')
        deltas={'xyz_A':max(abs(number(v,'native coordinate')-w) for v,w in zip(b['xyz'],a.xyz)),
                'occupancy':abs(number(b['occupancy'],'native q')-s['occupancy']),
                'b_A2':abs(number(b['b_iso'],'native B')-s['b_iso']),
                'scattering_e':max(abs(number(b['fp'],'native fp')-by_index[i]['f_prime']),
                                   abs(number(b['fdp'],'native fdp')-by_index[i]['f_double_prime']))}
        if s['anisou'] is None:
            if b['u_cart'] is not None:raise RecipeError('Native ADP representation changed')
        else:
            if not isinstance(b['u_cart'],list) or len(b['u_cart'])!=6:raise RecipeError('Native anisotropic ADP disappeared')
            deltas['u_cart_A2']=max(abs(number(v,'native U')-w/10000.) for v,w in zip(b['u_cart'],s['anisou']))
        for k,delta in deltas.items():
            maxima[k]=max(maxima[k],delta)
            if delta>TOLERANCES[k]:raise RecipeError('Frozen native state changed: '+k)
    rows=[]
    for group in native['groups']:
        if not group['refine_fdp']:continue
        index=group['indices'][0];a=actual[index]
        rows.append(dict(node_id=group['id'],key=a['key'],element=a['element'],xyz=a['xyz'],
                         occupancy=a['occupancy'],b_iso=a['b_iso'],f_prime=a['fp'],
                         f_double_prime=a['fdp'],reference_f_double_prime=group['reference_f_double_prime'],
                         q_times_f_double_prime=a['occupancy']*a['fdp'],
                         warning='NEGATIVE_FDP' if a['fdp']<0 else None))
    if 'b_calibration' in plan:
        by_node={r['node_id']:r for r in plan['b_calibration']['sites']}
        for row in rows:
            row['b_calibration']=by_node.get(row['node_id'], {'policy':'keep'})
    return dict(status='FDP_REVIEW',freeze_audit='PASS',maximum_deltas=maxima,tolerances=TOLERANCES,
                sites=rows,wavelength_A=plan['metadata']['wavelength_A'],native_version=native['native_version'],r_work=number(native['r_work'],'Rwork'),r_free=number(native['r_free'],'Rfree'),
                reflection_signature=reflections,convergence='NOT_INDEPENDENTLY_ASSESSED',
                scientific_acceptance='NOT_ASSESSED',automatic_checkpoint_selection=False,
                note='Completed conditional fit; geometry, identity, count and optimizer convergence remain review questions')


def _allocate(run):
    root=run/'Metal'
    if root.is_symlink():raise RecipeError('Metal root must not be a symlink')
    index=max([int(m.group(1)) for p in root.iterdir() if (m:=re.fullmatch(r'fdp_(\d{3,})',p.name))],default=0)+1
    while True:
        p=root/f'fdp_{index:03d}'
        try:p.mkdir();return p
        except FileExistsError:index+=1


def _native(directory, native, timeout):
    worker=Path(__file__).with_name('_fdp_native.py')
    try:
        with (directory/'native.log').open('xb') as log:
            process=subprocess.run([str(native.executables['phenix.python']),'-B',str(worker),'native-plan.json'],
                                   cwd=directory,env=native.environment,stdout=log,stderr=subprocess.STDOUT,
                                   timeout=timeout,check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecipeError('Native fdp execution failed or exceeded its timeout; attempt retained') from exc
    if process.returncode:raise RecipeError(f'Native fdp run failed ({process.returncode}); inspect retained native.log')
    return _json(gzip.decompress((directory/'native-result.json.gz').read_bytes()))


def _input_bundle(run, geometry):
    g=verify_geometry(run,geometry)
    parent=verify_hypothesis(run,Path(g['parent']['manifest']['relative_path']).parent)
    resources=[]
    for ref in g['inputs']['restraints']+[g['files']['restraints']]:
        path=resolve_artifact_path(ref,run)
        if path is None or path.suffix.lower() not in {'.cif','.phil','.eff','.params'}:
            raise RecipeError('Unsupported or missing inherited restraint resource')
        resources.append((f'resource_{len(resources):03d}'+path.suffix.lower(),_source(ref,run)))
    raw=_source(g['files']['model'],run)
    manifest=run/Path(g['files']['model']['relative_path']).parent/'manifest.json'
    return g,parent,raw,resources,_reference(manifest,run)


def run_fdp(run, geometry, *, native, fit_nodes, occupancies=None, cycles=3,
            minimizer_cycles=3, max_iterations=20, start_fdp=0., free_r_test_value=0, timeout=240, metal_b_policy=None):
    """Run one independent trial. Failed attempts retain their numbered directory."""
    run=Path(run).expanduser().resolve();_integer(timeout,10,600,'timeout seconds')
    g,parent,raw,resources,parent_ref=_input_bundle(run,geometry)
    observations=_source(g['inputs']['observations'],run)
    observation_path=resolve_artifact_path(g['inputs']['observations'],run)
    metadata=inspect_observations(observation_path,executable=native.executables['phenix.mtz.dump'],environment=native.environment)
    references=reference_scattering({a.element for a in parse_pdb(raw).snapshot.atoms},metadata['wavelength_A'],
        executable=native.executables['phenix.python'],version=native.version,environment=native.environment)
    plan,model=make_plan(raw,parent['sites'],metadata,references,fit_nodes=fit_nodes,occupancies=occupancies,cycles=cycles,
        minimizer_cycles=minimizer_cycles,max_iterations=max_iterations,start_fdp=start_fdp,free_r_test_value=free_r_test_value,
        metal_b_policy=metal_b_policy,preview=_json(_source(g['files']['preview'],run)),resources=resources)
    phil,args=parameters(plan,[name for name,_ in resources])
    directory=_allocate(run)
    try:
        content={'input.pdb':model,'observations.mtz':observations,'parameters.phil':phil,**dict(resources)}
        content['plan.json']=_json_bytes(plan)
        content['native-plan.json']=_json_bytes({'plan':plan,'args':args})
        for name,data in content.items():(directory/name).write_bytes(data)
        audit=audit_free_r_flags(directory/'observations.mtz','FreeR_flag',free_r_test_value,
            native.executables['phenix.python'],directory,environment=native.environment)
        free_r=dict(status=audit.status,usable=audit.valid,details=audit.details,warnings=list(audit.warnings))
        (directory/'free-r.json').write_bytes(_json_bytes(free_r))
        if not audit.valid:raise RecipeError('Original Free-R audit failed; see retained free-r.json')
        evidence=_native(directory,native,timeout)
        result=audit_result(plan,model,evidence)
        # Audit serialization independently; full-precision evidence remains primary.
        before=parse_pdb(model);after=parse_pdb((directory/'final.pdb').read_bytes())
        if before.snapshot.atoms!=after.snapshot.atoms or canonical(before.to_dict()['atomic_state'])!=canonical(after.to_dict()['atomic_state']):
            raise RecipeError('Serialized final PDB changed frozen atomic state')
        for name,data in content.items():
            if (directory/name).read_bytes()!=data:raise RecipeError('Frozen trial input changed: '+name)
        _source(parent_ref,run);verify_geometry(run,geometry)
        (directory/'result.json').write_bytes(_json_bytes(result))
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
            raise RecipeError('Unexpected nonregular native artifact')
        files={p.name:_reference(p,run) for p in sorted(directory.iterdir())}
        doc=dict(kind='metal-fdp-trial',schema_version=1,protocol=PROTOCOL,status='FDP_REVIEW',
                 parent=dict(geometry_id=g['geometry_id'],manifest=parent_ref),files=files,
                 input_sources=g['inputs'],worker_sha256=hashlib.sha256(Path(__file__).with_name('_fdp_native.py').read_bytes()).hexdigest(),
                 execution=dict(phenix_version=evidence['native_version'],timeout_seconds=timeout,mode='complete'),
                 automatic_checkpoint_selection=False,scientific_acceptance='NOT_ASSESSED')
        doc['trial_id']=digest(doc)
        (directory/'manifest.json').write_bytes(_json_bytes(doc))
        return doc
    except BaseException as exc:
        with (directory/'failure.json').open('xb') as handle:
            handle.write(_json_bytes(dict(status='FAILED',error=str(exc),exception=type(exc).__name__)))
        raise


def verify_fdp(run, directory):
    """Verify saved inputs, native evidence and audit; never repeat a native fit."""
    run=Path(run).expanduser().resolve();directory=Path(directory).expanduser()
    if not directory.is_absolute():directory=run/directory
    if directory.is_symlink() or directory.parent.is_symlink():raise RecipeError('Trial directory must not be a symlink')
    directory=directory.resolve()
    if directory.parent!=run/'Metal' or not re.fullmatch(r'fdp_\d{3,}',directory.name):
        raise RecipeError('Require an explicit numbered fdp trial within this run')
    try:
        doc=_json((directory/'manifest.json').read_bytes())
        check=dict(doc);trial_id=check.pop('trial_id')
        if digest(check)!=trial_id or doc['kind']!='metal-fdp-trial' or type(doc['schema_version'])is not int or doc['schema_version']!=1 or doc['protocol']!=PROTOCOL:
            raise RecipeError('Unsupported or changed fdp manifest')
        if (doc['status']!='FDP_REVIEW' or doc['automatic_checkpoint_selection'] is not False
                or doc['scientific_acceptance']!='NOT_ASSESSED' or doc['execution']['mode']!='complete'):
            raise RecipeError('Unexpected trial acceptance state')
        if any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):raise RecipeError('Trial payload must contain regular files only')
        if set(p.name for p in directory.iterdir())!={'manifest.json',*doc['files']}:
            raise RecipeError('Failed or unexpected trial inventory')
        for name,ref in doc['files'].items():
            if Path(name).name!=name or ref!=_reference(directory/name,run):raise RecipeError('Trial artifact changed or moved unexpectedly')
            _source(ref,run)
        pref=doc['parent']['manifest'];_source(pref,run)
        if pref.get('anchor')!='run':raise RecipeError('Trial parent must be in this run')
        g,parent,raw,resources,expected_ref=_input_bundle(run,Path(pref['relative_path']).parent)
        if pref!=expected_ref or doc['parent']['geometry_id']!=g['geometry_id'] or canonical(doc['input_sources'])!=canonical(g['inputs']):
            raise RecipeError('Trial parent lineage changed')
        plan=_json((directory/'plan.json').read_bytes())
        free_r=_json((directory/'free-r.json').read_bytes())
        if free_r.get('usable') is not True or free_r.get('status') not in {'VALID','NOISY'}:
            raise RecipeError('Saved Free-R audit is not usable')
        if doc['execution']['phenix_version']!=NATIVE_VERSION:
            raise RecipeError('Saved native version is unsupported')
        checksum(doc['worker_sha256'],'native worker provenance')
        replay,model=make_plan(raw,parent['sites'],plan['metadata'],plan['references'],
            preview=_json(_source(g['files']['preview'],run)),resources=resources,**plan['options'])
        phil,args=parameters(replay,[name for name,_ in resources])
        expected={'input.pdb':model,'observations.mtz':_source(g['inputs']['observations'],run),
                  'plan.json':_json_bytes(replay),'parameters.phil':phil,
                  'native-plan.json':_json_bytes({'plan':replay,'args':args}),**dict(resources)}
        if any((directory/name).read_bytes()!=data for name,data in expected.items()):raise RecipeError('Trial inputs differ from derivation replay')
        native=_json(gzip.decompress((directory/'native-result.json.gz').read_bytes()))
        result=audit_result(replay,model,native)
        if (directory/'result.json').read_bytes()!=_json_bytes(result):raise RecipeError('Saved result differs from freeze audit')
        before=parse_pdb(model);after=parse_pdb((directory/'final.pdb').read_bytes())
        if before.snapshot.atoms!=after.snapshot.atoms or canonical(before.to_dict()['atomic_state'])!=canonical(after.to_dict()['atomic_state']):
            raise RecipeError('Serialized final PDB changed')
        return doc
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as exc:
        if isinstance(exc,RecipeError):raise
        raise RecipeError('Cannot verify fdp trial: '+str(exc)) from exc
