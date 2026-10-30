"""Opt-in maps from the active, completed XYZ fit; no endpoint reload or refit.

Native methods are imported only by capture. Offline verification uses stdlib
and checks provenance, membership, bounded summaries and artifact checksums; it
never claims to independently recompute crystallographic map coefficients.
"""
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

PROTOCOL = 'metal-xyz-maps-v1'
MAPS = (('2mFo-DFc', 'map-2mfo-dfc.mtz', 'TWOFOFC'),
        ('mFo-DFc', 'map-mfo-dfc.mtz', 'FOFC'))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e100:
        raise ValueError('Invalid map diagnostic number')
    return float(value)


def _sha(value):
    if not isinstance(value, str) or re.fullmatch('[a-f0-9]{64}', value) is None:
        raise ValueError('Invalid map provenance checksum')
    return value


def request():
    return dict(protocol=PROTOCOL, source='completed_native_xyz',
                map_types=[m[0] for m in MAPS], exclude_free_r_reflections=True,
                fill_missing=False, isotropize=True, sharp=False,
                resolution_factor=.25, normalization='whole_cell_sigma',
                sphere_radius_A=1.5, sample_spacing_A=.5,
                phase_policy='active_MLHL_model_assisted_not_independent',
                refit_or_rescale=False)


def endpoint_digest(native):
    return _digest({k:native[k] for k in ('atoms', 'reflection_after', 'phases_after',
                                         'r_work', 'r_free', 'symmetry_after')})


def fit_context(r_work, r_free):
    """Mirror AutoRefine numerical conditions, without granting acceptance."""
    rw, rf = _number(r_work), _number(r_free)
    if rw < 0 or rf < 0:
        raise ValueError('Negative refinement residual')
    return dict(r_work=rw, r_free=rf, r_free_minus_r_work=rf-rw,
                r_work_less_than_0_30=rw < .30, r_work_less_than_r_free=rw < rf,
                numerical_conditions_met=rw < .30 and rw < rf,
                r_free_upper_limit=None, scientific_acceptance='NOT_ASSESSED',
                note='Numerical conditions only; geometry, maps, Rfree gap and anomalous evidence still require review')


def _offsets():
    return [(i*.5, j*.5, k*.5) for i,j,k in itertools.product(range(-3,4), repeat=3)
            if i*i+j*j+k*k <= 9]


def summarize(evidence, native, sites):
    if (evidence['protocol'] != PROTOCOL or _canonical(evidence['policy']) != _canonical(request())
            or evidence['endpoint_sha256'] != endpoint_digest(native)
            or _sha(evidence['active_state_before']) != _sha(evidence['active_state_after'])):
        raise ValueError('Map policy, endpoint or active native state changed')
    _sha(evidence['implementation_sha256'])
    sources=evidence['native_source_hashes']
    if set(sources) != {'map_tools','miller','mtz'}:
        raise ValueError('Incomplete native map source provenance')
    for value in sources.values():_sha(value)
    if native['reflection_after']['anomalous'] is not False:
        raise ValueError('XYZ maps require the audited merged geometry observations')
    work=[r[0] for r in native['reflection_after']['rows'] if not r[3]]
    atoms={_canonical(a['key']):a for a in native['atoms']}
    if len(atoms) != len(native['atoms']) or len(evidence['maps']) != len(MAPS):
        raise ValueError('Map atom or map inventory changed')
    result=[]
    for row, (typ, filename, label) in zip(evidence['maps'], MAPS):
        if (row['type'] != typ or row['filename'] != filename or row['label'] != label
                or type(row['coefficient_count']) is not int or row['coefficient_count'] != len(work)
                or _canonical(row['coefficient_indices']) != _canonical(work) or not work):
            raise ValueError('Map type, coefficients or work/free membership changed')
        if 'column_labels' in row and row['column_labels'] != [label,'PHI'+label]:
            raise ValueError('Map amplitude/phase labels changed')
        _sha(row['sha256'])
        if type(row['size']) is not int or row['size'] <= 0:
            raise ValueError('Invalid map file size')
        maximum=_number(row['max_abs_coefficient']);error=_number(row['readback_max_complex_error'])
        if maximum < 0 or error < 0 or error > 1e-4*max(1., maximum):
            raise ValueError('Map MTZ readback differs from native coefficients')
        if (not isinstance(row['grid'],list) or len(row['grid']) != 3
                or any(type(v) is not int or v <= 0 for v in row['grid'])):
            raise ValueError('Invalid map sampling grid')
        if len(row['sites']) != len(sites):raise ValueError('Map site count changed')
        for sample, site in zip(row['sites'], sites):
            atom=atoms[_canonical(site['key'])]
            if (sample['node_id'] != site['node_id'] or sample['key'] != atom['key']
                    or sample['xyz'] != atom['xyz'] or type(sample['samples']) is not int
                    or sample['samples'] != len(_offsets())):
                raise ValueError('Map site identity, coordinates or sampling changed')
            for value in sample['xyz']:_number(value)
            low=_number(sample['sphere_min_sigma']);high=_number(sample['sphere_max_sigma'])
            if not low <= _number(sample['center_sigma']) <= high or not low <= _number(sample['sphere_mean_sigma']) <= high:
                raise ValueError('Inconsistent local map samples')
        result.append({k:v for k,v in row.items() if k != 'coefficient_indices'})
    return dict(protocol=PROTOCOL, source='completed_native_xyz', policy=request(),
                endpoint_sha256=evidence['endpoint_sha256'], native_state_unchanged=True,
                implementation_sha256=evidence['implementation_sha256'], native_source_hashes=sources,
                maps=result, fit_context=fit_context(native['r_work'],native['r_free']),
                scientific_acceptance='NOT_ASSESSED', automatic_checkpoint_selection=False,
                limitation='Model-assisted map samples are not independent validation, resolved atom counts or an automatic ranking')


def verify_files(evidence, directory):
    directory=Path(directory)
    for row, (_, filename, _) in zip(evidence['maps'],MAPS):
        if row['filename'] != filename:raise ValueError('Unexpected map path')
        path=directory/filename
        if path.is_symlink() or not path.is_file():raise ValueError('Missing or linked map coefficients')
        raw=path.read_bytes()
        if len(raw) != row['size'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Map coefficient artifact differs from native capture')


def _active_state(fmodel):
    """Include all mutable fitted state and scales; caches are not science state."""
    x=fmodel.xray_structure;obs=fmodel.f_obs();calc=fmodel.f_model();hl=fmodel.hl_coeffs()
    return _digest(dict(atoms=[(s.label,s.scattering_type,list(s.site),s.occupancy,s.u_iso,
        list(s.u_star),s.fp,s.fdp,s.flags.use_u_iso(),s.flags.use_u_aniso()) for s in x.scatterers()],
        cell=list(x.unit_cell().parameters()),space_group=str(x.space_group_info()),
        observations=list(zip(list(obs.indices()),list(obs.data()),list(obs.sigmas()),list(fmodel.r_free_flags().data()))),
        calculated=[(list(h),z.real,z.imag) for h,z in zip(calc.indices(),calc.data())],
        hl=None if hl is None else [(list(h),list(v)) for h,v in zip(hl.indices(),hl.data())],
        k_isotropic=list(fmodel.k_isotropic()),k_anisotropic=list(fmodel.k_anisotropic()),
        k_masks=[list(k) for k in fmodel.k_masks()],r_work=fmodel.r_work(),r_free=fmodel.r_free()))


def capture(fmodel, native, sites, policy):
    """Called once in get_results, after a complete fit; never refit or rescale."""
    from cctbx.array_family import flex
    from cctbx import miller
    from iotbx import mtz, reflection_file_reader
    import mmtbx.map_tools as map_tools
    if policy != request() or fmodel.hl_coeffs() is None or fmodel.f_obs().anomalous_flag():
        raise ValueError('Unsupported final XYZ map policy')
    if (fmodel.r_work(),fmodel.r_free()) != (native['r_work'],native['r_free']):
        raise ValueError('Map capture does not match completed native residuals')
    before=_active_state(fmodel);atoms={_canonical(a['key']):a for a in native['atoms']}
    uc=fmodel.f_obs().unit_cell();rows=[]
    for typ,filename,label in MAPS:
        coeff=fmodel.map_coefficients(map_type=typ,exclude_free_r_reflections=True,
                                      fill_missing=False,isotropize=True,sharp=False)
        path=Path(filename)
        if path.exists():raise ValueError('Refuse to overwrite map artifact')
        coeff.as_mtz_dataset(column_root_label=label).mtz_object().write(filename)
        restored=reflection_file_reader.any_reflection_file(filename).as_miller_arrays()
        if len(restored) != 1 or list(restored[0].indices()) != list(coeff.indices()):
            raise ValueError('Native map MTZ inventory/readback changed')
        maximum=float(flex.max(flex.abs(coeff.data())))
        error=float(flex.max(flex.abs(restored[0].data()-coeff.data())))
        fft=coeff.fft_map(resolution_factor=.25).apply_sigma_scaling();grid=fft.real_map_unpadded()
        samples=[]
        for site in sites:
            atom=atoms[_canonical(site['key'])];pos=atom['xyz']
            values=[float(grid.eight_point_interpolation(uc.fractionalize(tuple(pos[i]+delta[i] for i in range(3))))) for delta in _offsets()]
            samples.append(dict(node_id=site['node_id'],key=atom['key'],xyz=pos,
                center_sigma=float(grid.eight_point_interpolation(uc.fractionalize(pos))),
                sphere_min_sigma=min(values),sphere_max_sigma=max(values),
                sphere_mean_sigma=math.fsum(values)/len(values),samples=len(values)))
        raw=path.read_bytes()
        rows.append(dict(type=typ,filename=filename,label=label,sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
            column_labels=restored[0].info().labels,
            coefficient_indices=sorted(list(h) for h in coeff.indices()),coefficient_count=coeff.size(),
            max_abs_coefficient=maximum,readback_max_complex_error=error,grid=list(grid.all()),sites=samples))
    evidence=dict(protocol=PROTOCOL,policy=request(),endpoint_sha256=endpoint_digest(native),
        active_state_before=before,active_state_after=_active_state(fmodel),
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_source_hashes={name:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name,module in [('map_tools',map_tools),('miller',miller),('mtz',mtz)]},maps=rows)
    summarize(evidence,native,sites);verify_files(evidence,Path.cwd())
    return evidence
