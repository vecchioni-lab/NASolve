"""Opt-in bounded refinement of an explicitly registered phosphate continuation.

Cedar owns bond shells, reference chemistry, native image forces and process
ownership. This entry freezes inputs, runs preflight then refinement, and returns
an unselected coordinate-only result in the unchanged source frame.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import importlib
import json
import math
from pathlib import Path
import re
import sys

from .topostitch_inspect import _keys
from .topostitch_preview import _json
from .topostitch_recipe import recipe_digest, model_atom_rows
from .topostitch_endpoint import audit_masked_endpoint


def _save(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def _request(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes(); value = _json(raw)
    _keys(value, {'schema_version', 'kind', 'inputs', 'restraints', 'continuation_id',
                  'cycles', 'iterations', 'max_displacement_angstrom', 'wxc_scale',
                  'data_labels', 'free_label', 'test_flag_value'})
    if type(value['schema_version']) is not int or value['schema_version'] != 1 or value['kind'] != 'topostitch-phosphate-refinement':
        raise ValueError('Require a schema-1 phosphate refinement request')
    for key, lo, hi in [('continuation_id', 1, 1000000), ('cycles', 1, 5), ('iterations', 1, 200)]:
        if type(value[key]) is not int or not lo <= value[key] <= hi:
            raise ValueError('Unsupported bounded control: '+key)
    for key, hi in [('max_displacement_angstrom', 10), ('wxc_scale', 10)]:
        if type(value[key]) not in (int, float) or not math.isfinite(value[key]) or not 0 < value[key] <= hi:
            raise ValueError('Unsupported positive control: '+key)
    if type(value['test_flag_value']) is not int or not 0 <= value['test_flag_value'] <= 100:
        raise ValueError('Require an explicit Free-R flag value')
    for key in ('data_labels', 'free_label'):
        if not isinstance(value[key], str) or not re.fullmatch(r'[A-Za-z0-9_,()+/\-]+', value[key]):
            raise ValueError('Require explicit native column labels')
    _keys(value['inputs'], {'model', 'registration_model', 'data', 'registration', 'discovery', 'continuations', 'native_receipt'})
    if not isinstance(value['restraints'], list) or not 1 <= len(value['restraints']) <= 30:
        raise ValueError('Require 1-30 explicit restraint/dictionary files')
    files = {}; snapshots = {path: raw}
    for name, ref in [*value['inputs'].items(), *((f'restraint_{i}', ref) for i, ref in enumerate(value['restraints']))]:
        _keys(ref, {'path', 'sha256'})
        if not isinstance(ref['path'], str) or not isinstance(ref['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', ref['sha256']):
            raise ValueError('Require input paths and SHA-256 pins')
        target = (path.parent/ref['path']).resolve(strict=True); data = target.read_bytes()
        if sha256(data).hexdigest() != ref['sha256']:
            raise ValueError('Input checksum differs: '+name)
        files[name] = target; snapshots[target] = data
    return value, files, snapshots


def _masked_result(source, points, movable, bound):
    lines = source.splitlines(keepends=True); indices = [i for i, l in enumerate(lines) if l[:6] in (b'ATOM  ', b'HETATM')]
    if len(indices) != len(points):
        raise ValueError('Native result changed atom inventory')
    for i in movable:
        fields = ''.join(f'{v:8.3f}' for v in points[i]).encode('ascii')
        if len(fields) != 24:
            raise ValueError('Candidate exceeds PDB coordinate fields')
        k = indices[i]; lines[k] = lines[k][:30] + fields + lines[k][54:]
    candidate = b''.join(lines)
    audit = audit_masked_endpoint(source, candidate, points, movable_indices=movable,
        max_displacement_angstrom=bound, anisou_policy='preserve-cartesian')
    return candidate, audit


def _verify_return(before, after, chosen, initial_observations, final_observations):
    if not before or set(before) != set(after) or not chosen <= set(before):
        raise ValueError('Atom inventory changed')
    if not initial_observations or not any(r[-1] for r in initial_observations) or all(r[-1] for r in initial_observations):
        raise ValueError('Require nonempty work and Free-R sets')
    if (len(initial_observations) != len(final_observations)
            or len({tuple(r[0]) for r in initial_observations}) != len(initial_observations)
            or [(r[0], r[-1]) for r in initial_observations] != [(r[0], r[-1]) for r in final_observations]):
        raise ValueError('Reflection indices or Free-R flags changed')
    # Native apply_scale_k1_to_f_obs rescales F and sigma together. This is
    # numerical normalization, not permission to filter or alter observations.
    total = math.fsum(r[1] for r in initial_observations)
    if not math.isfinite(total) or total <= 0:
        raise ValueError('Require finite positive total observed amplitude')
    scale = math.fsum(r[1] for r in final_observations) / total
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Invalid native observation normalization')
    for original, returned in zip(initial_observations, final_observations):
        for k in (1, 2):
            expected = original[k] * scale
            if not math.isfinite(returned[k]) or not math.isclose(returned[k], expected, rel_tol=1e-12, abs_tol=1e-10):
                raise ValueError('Observations changed beyond a common F/sigma scale')
    for key, row in after.items():
        prior = before[key]
        if set(row) != set(prior) or any(row[k] != prior[k] for k in row if k != 'xyz'):
            raise ValueError('ADP, occupancy or element changed')
        if any(not math.isfinite(v) for v in row['xyz']):
            raise ValueError('Nonfinite returned coordinate')
        if key not in chosen and math.dist(row['xyz'], prior['xyz']) > 1e-9:
            raise ValueError('Fixed coordinates changed')
    return dict(indices_and_flags_exact=True, amplitude_sigma_common_scale=scale,
                observations_exact=final_observations == initial_observations)


def run_registered_phosphate_refinement(request_path, output_directory, *, phenix, cedar_source=None, timeout_seconds=1200):
    """Run one preflight and one fit; never modify a checkpoint or select a model.

    Input references are resolved relative to the request, with explicit absolute
    paths also supported. The complete native reference capture is authenticated
    by Cedar. Only six canonical connecting atoms move; all other source bytes,
    Cartesian ADPs and occupancies are protected. Output remains under review.
    """
    from .topostitch_captured_job import _cedar, _unchanged
    if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 3600:
        raise ValueError('Require a timeout from 1 to 3600 seconds')
    spec, files, original = _request(request_path)
    root = Path(output_directory).absolute()
    if root.exists():
        raise FileExistsError(root)
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Output cannot traverse a symlink')
    with _cedar(cedar_source) as cedar:
        namespace = cedar['cif_attachment_native'].__package__
        continuation = importlib.import_module(namespace+'.cif_phosphate_continuation')
        chemistry = importlib.import_module(namespace+'.cif_phosphate_restraints')
        registration = continuation.RegisteredContinuation(spec['continuation_id'], files['registration'], files['discovery'], files['continuations'])
        inspection = continuation.inspect_inherited_continuation(files['registration_model'], files['model'], registration,
            geometry=None, native_receipt=files['native_receipt'])
        bond = chemistry.phosphate_bond_phil(inspection)
        for name in ('cif_phosphate_runtime', 'cif_refinement_runtime'):
            importlib.import_module(namespace+'.'+name)
        runtime_sources = {}
        for name, module in list(sys.modules.items()):
            if (name.startswith(namespace+'.') or name.startswith(__package__+'.')) and getattr(module, '__file__', None):
                path = Path(module.__file__).resolve()
                if path.suffix == '.py':
                    original[path] = path.read_bytes()
                    runtime_sources[name.replace(namespace, 'cedar', 1)] = sha256(original[path]).hexdigest()
        # Authenticate full reference evidence before creating any job directory.
        _, _, capture = cedar['cif_attachment_native']._capture(files['native_receipt'], original[files['model']])
        original.update(capture)
        sdk = cedar['phenix_runtime'].installation_from_candidate(Path(phenix))
        source = original[files['model']]
        names = [(inspection['phosphate'][0], n) for n in ('P', 'OP1', 'OP2', "O5'", "C5'")]
        names.append((inspection['o3'][0], "O3'"))
        rows = model_atom_rows(source)
        chosen = [i for i, row in enumerate(rows) if (f"{row['chain']}:{row['residue_number']}", row['atom_name']) in names]
        points = [tuple(float(l[a:b]) for a, b in ((30,38),(38,46),(46,54))) for l in source.splitlines() if l[:6] in (b'ATOM  ', b'HETATM')]
        if len(chosen) != 6:
            raise ValueError('Require six unambiguous connecting-backbone atoms')
        _masked_result(source, points, chosen, spec['max_displacement_angstrom'])
        root.mkdir(parents=True); inputs = root/'inputs'; inputs.mkdir()
        frozen = {}
        for name, path in files.items():
            if name == 'native_receipt': continue
            suffix = path.suffix if name.startswith('restraint_') else dict(model='.pdb', registration_model='.pdb', data='.mtz').get(name, '.json')
            relative = 'inputs/'+name+suffix
            (root/relative).write_bytes(original[path]); frozen[name] = relative
        capture_root = root/'native-reference'; capture_root.mkdir()
        for path, raw in capture.items():
            dest = capture_root/path.relative_to(files['native_receipt'].parent)
            dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(raw)
        _save(root/'inspection.json', inspection)
        (root/'bond.phil').write_text(bond)
        plan = dict(schema_version=1, kind=spec['kind'], controls={k: spec[k] for k in spec if k not in ('inputs','restraints')},
            inputs=frozen, movable_indices=chosen, model_sha256=sha256(source).hexdigest(),
            native_version=sdk.version, runtime_sources=runtime_sources,
            inspection_sha256=recipe_digest(inspection), scientific_acceptance=False, checkpoint_created=False)
        plan['frozen_files'] = {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
        _save(root/'plan.json', plan)
        package = Path(__file__).resolve().parent.parent
        native_package = Path(cedar['cif_attachment_native'].__file__).resolve().parent
        bootstrap = "import sys;sys.path.insert(0,sys.argv[1]);import nasolve;nasolve.__path__.append(sys.argv[2]);from nasolve.topostitch_phosphate import _worker;_worker(sys.argv[3])"
        frozen_bytes = {root/p: (root/p).read_bytes() for p in plan['frozen_files']}
        frozen_bytes[root/'plan.json'] = (root/'plan.json').read_bytes()
        report = dict(status='FAILED', scientific_acceptance=False, checkpoint_created=False, phases=[])
        try:
            for phase in ('preflight', 'fit'):
                if not _unchanged(original) or not _unchanged(frozen_bytes):
                    raise ValueError('Inputs, plan or runtime sources changed before native phase')
                work = root/phase; work.mkdir()
                rc = cedar['campaign_process'].run_owned_command(
                    [str(sdk.executables['phenix.python']), '-B', '-c', bootstrap, str(package), str(native_package), phase],
                    cwd=work, log_path=work/'native.log', timeout_seconds=timeout_seconds, poll_interval=.5,
                    environment=dict(sdk.environment, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'),
                    on_process=lambda p: _save(work/'process.json', p))
                stopped = not cedar['campaign_process'].process_alive(_json((work/'process.json').read_bytes()))
                _save(work/'stopped.json', dict(returncode=rc, stopped=stopped))
                if rc != 0 or not stopped:
                    raise RuntimeError('Native '+phase+' failed; retained evidence')
                observed = _json((work/'science.json').read_bytes())
                if observed['status'] != 'COMPLETE_REQUIRES_REVIEW':
                    raise ValueError('Incomplete native phase')
                report['phases'].append(phase)
            report.update(status='REFINED_FOR_REVIEW', candidate=dict(anchor='run', relative_path='fit/candidate.pdb', sha256=sha256((root/'fit/candidate.pdb').read_bytes()).hexdigest()))
        except BaseException as exc:
            report['error'] = type(exc).__name__+': '+str(exc)
            raise
        finally:
            report['original_inputs_unchanged'] = _unchanged(original)
            report['frozen_inputs_unchanged'] = _unchanged(frozen_bytes)
            if not report['original_inputs_unchanged'] or not report['frozen_inputs_unchanged']:
                report['status'] = 'FAILED_INPUT_DRIFT'
            _save(root/'result.json', report)
        if not report['original_inputs_unchanged'] or not report['frozen_inputs_unchanged']:
            raise ValueError('Inputs changed during execution')
        return report


def _worker(phase):
    """Native-only worker, entered by the maintained product process owner."""
    from functools import wraps
    from unittest.mock import patch
    from phenix.programs.phenix_refine import Program
    from .cif_refinement_runtime import run_compatible_refinement
    from .cif_phosphate_runtime import RegisteredPhosphateRuntime
    if phase not in ('preflight', 'fit'): raise ValueError('Unknown phase')
    root = Path.cwd().parent; plan = _json((root/'plan.json').read_bytes()); controls = plan['controls']
    if any(sha256((root/p).read_bytes()).hexdigest() != h for p,h in plan['frozen_files'].items()):
        raise ValueError('Frozen input changed before native execution')
    inspection = _json((root/'inspection.json').read_bytes())
    if recipe_digest(inspection) != plan['inspection_sha256']: raise ValueError('Inspection changed')
    model_path = root/plan['inputs']['model']; raw = model_path.read_bytes()
    if sha256(raw).hexdigest() != plan['model_sha256']: raise ValueError('Model changed')
    atom_lines = [l for l in raw.decode('ascii').splitlines() if l[:6] in ('ATOM  ', 'HETATM')]
    source = {'pdb="'+l[12:27]+'"': l for l in atom_lines}
    if len(source) != len(atom_lines): raise ValueError('Ambiguous source atom labels')
    chosen = {list(source)[i] for i in plan['movable_indices']}
    selections = []
    for label in chosen:
        l = source[label]
        selections.append(f"(chain {l[21]} and resseq {int(l[22:26])} and resname {l[17:20].strip()} and name {l[12:16].strip()})")
    selection = ' or '.join(sorted(selections))
    data = '../'+plan['inputs']['data']
    policy = f'''data_manager {{ miller_array {{ file = "{data}"
 labels {{ name = "{controls['data_labels']}" }}
 labels {{ name = "{controls['free_label']}" }}
}} }}
refinement {{
 main {{ number_of_macro_cycles = {controls['cycles']}
 max_number_of_iterations = {controls['iterations']}
 random_seed = 15403
 nproc = 1
 target = ml
 scattering_table = n_gaussian
 apply_overall_isotropic_scale_to_adp = False
 place_ions = False
 update_ss = off
 ias = False
 find_and_add_hydrogens = False
 }}
 refine {{ strategy = *individual_sites
 sites {{ individual = "{selection}" }} }}
 target_weights {{ optimize_xyz_weight = False
 optimize_adp_weight = False
 force_optimize_weights = False
 shake_sites = False
 wxc_scale = {controls['wxc_scale']}
 }}
 output {{ write_final_geo_file = True }}
}}
'''
    Path('policy.phil').write_text(policy)
    args = ['../'+p for k,p in plan['inputs'].items() if k in ('model','data') or k.startswith('restraint_')]
    args += ['../bond.phil', 'policy.phil', f'xray_data.file_name={data}', f'xray_data.labels={controls["data_labels"]}',
        f'xray_data.r_free_flags.file_name={data}', f'xray_data.r_free_flags.label={controls["free_label"]}',
        f'xray_data.r_free_flags.test_flag_value={controls["test_flag_value"]}', 'xray_data.r_free_flags.generate=False',
        'xray_data.force_anomalous_flag_to_be_equal_to=False', 'xray_data.outliers_rejection=False',
        'ordered_solvent=False', 'simulated_annealing=False', 'output.prefix=refined',
        'output.write_model_cif_file=True', 'output.export_final_f_model=True',
        'refinement.dry_run='+str(phase=='preflight')]
    def observations(fm):
        fo=fm.f_obs(); flags=fm.r_free_flags()
        if list(fo.indices()) != list(flags.indices()): raise ValueError('Observation/flag index mismatch')
        return [[list(h),float(f),float(s),bool(b)] for h,f,s,b in zip(fo.indices(),fo.data(),fo.sigmas(),flags.data())]
    def state(model):
        x=model.get_xray_structure()
        return {a.id_str(): dict(xyz=list(a.xyz), q=s.occupancy, u_star=list(s.u_star), u_iso=s.u_iso,
            use_u_iso=s.flags.use_u_iso(), use_u_aniso=s.flags.use_u_aniso(), element=a.element.strip())
            for a,s in zip(model.get_hierarchy().atoms(),x.scatterers())}
    initial={}; original_validate=Program.validate
    @wraps(original_validate)
    def validate(program,*a,**kw):
        result=original_validate(program,*a,**kw)
        if initial or program.joint_xn: raise ValueError('Require one X-ray model')
        model=program.model; p=program.params.refinement
        expressions=p.refine.sites.individual
        if not expressions: raise ValueError('Missing explicit refinement selection')
        mask=model.selection(' or '.join('('+e+')' for e in expressions))
        selected={a.id_str() for a,yes in zip(model.get_hierarchy().atoms(),mask) if yes}
        if selected != chosen or list(p.refine.strategy) != ['individual_sites']:
            raise ValueError('Compiled refinement changes the requested coordinate-only mask')
        if p.main.number_of_macro_cycles != controls['cycles'] or p.main.max_number_of_iterations != controls['iterations'] or p.main.nproc != 1:
            raise ValueError('Compiled refinement exceeds the bounded protocol')
        if p.main.apply_overall_isotropic_scale_to_adp or p.target_weights.optimize_xyz_weight or p.target_weights.optimize_adp_weight:
            raise ValueError('Compiled refinement permits ADP or weight changes')
        initial.update(atoms=state(model), observations=observations(program.fmodel))
        _save('initial-state.json', initial)
        if phase=='fit':
            pre=_json((root/'preflight/science.json').read_bytes())
            if recipe_digest(initial) != pre['initial_sha256']: raise ValueError('Fit differs from qualified preflight')
        return result
    owner=RegisteredPhosphateRuntime(inspection,raw)
    report=dict(status='FAILED',phase=phase,scientific_acceptance=False)
    try:
        with patch.object(Program,'validate',validate), owner.active():
            result=run_compatible_refinement(args,evidence_directory='native-runtime',capture_written_model=True)
            model=result.model; fm=result.fmodels.fmodel_xray(); final=state(model)
            selected={a.id_str() for a,yes in zip(model.get_hierarchy().atoms(),model.refinement_flags.sites_individual) if yes}
            if selected != chosen: raise ValueError('Native refinement mask changed')
            if set(final) != set(source) or set(initial['atoms']) != set(source): raise ValueError('Atom inventory changed')
            returned_observations=observations(fm)
            _save('returned-state.json', dict(atoms=final, observations=returned_observations))
            observation_audit=_verify_return(initial['atoms'], final, chosen, initial['observations'], returned_observations)
            if phase=='fit' and (not owner.calls.get((7,True),0) or result.macro_cycle!=controls['cycles']):
                raise ValueError('Complete phosphate forces or requested cycles missing')
            points=[final[k]['xyz'] for k in source]
            # Restore exact source coordinates for fixed sites only after proving native immobility.
            for i,l in enumerate(atom_lines):
                if list(source)[i] not in chosen: points[i]=[float(l[a:b])for a,b in ((30,38),(38,46),(46,54))]
            candidate,audit=_masked_result(raw,points,plan['movable_indices'],controls['max_displacement_angstrom'])
            Path('candidate.pdb').write_bytes(candidate)
            _save('full-precision-points.json',points)
            report.update(status='COMPLETE_REQUIRES_REVIEW',initial_sha256=recipe_digest(initial),observation_audit=observation_audit,
                observations_sha256=recipe_digest(initial['observations']),reflection_count=len(initial['observations']),
                free_count=sum(r[-1] for r in initial['observations']),rwork=fm.r_work(),rfree=fm.r_free(),
                endpoint_audit=audit,phosphate_terms_sha256=recipe_digest(owner.live_terms),
                complete_force_calls=owner.calls.get((7,True),0),bond=owner.bond)
        if not owner.restored: raise ValueError('Native phosphate hooks not restored')
        report['hooks_restored']=True
    except BaseException as exc:
        report.update(status='FAILED',error=type(exc).__name__+': '+str(exc));raise
    finally:
        _save('science.json',report)


def main(argv=None):
    parser=argparse.ArgumentParser(prog='nasolve-topostitch-fit native-phosphate')
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--phenix',type=Path,required=True)
    parser.add_argument('--cedar-source',type=Path,help='Explicit compatible Cedar package root for branch development')
    parser.add_argument('--timeout',type=float,default=1200)
    args=parser.parse_args(argv)
    try: result=run_registered_phosphate_refinement(args.request,args.out,phenix=args.phenix,cedar_source=args.cedar_source,timeout_seconds=args.timeout)
    except (OSError,ValueError,RuntimeError) as exc: parser.exit(2,str(exc)+'\n')
    print(json.dumps(result,indent=2));return 0
