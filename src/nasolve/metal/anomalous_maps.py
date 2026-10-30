"""Optional native anomalous Fourier capture from the completed frozen fit.

No native dependencies are imported during offline audit. This verifies saved
provenance and bytes; it does not independently repeat a Fourier calculation.
"""
import hashlib
import math
from pathlib import Path
if __package__:
    from . import map_diagnostics as common
else:
    import map_diagnostics as common

PROTOCOL = 'metal-fdp-anomalous-map-v1'
FILENAME = 'map-anomalous.mtz'


def request():
    return dict(protocol=PROTOCOL,source='completed_native_fdp',map_type='anomalous',
        phase_policy='completed_Fmodel_Bijvoet_average_no_external_phases',
        formula='DANO_exp_i_phi_Fmodel_divided_by_2i',exclude_free_r_pairs=True,
        missing_mates='omit',fill_missing=False,sharp=False,isotropize=False,
        resolution_factor=.25,normalization='whole_cell_sigma',sphere_radius_A=1.5,
        sample_spacing_A=.5,refit_or_rescale=False)


def endpoint_digest(native):
    return common._digest({k:native[k] for k in ('atoms','groups','reflection_after','r_work','r_free')})


def work_pair_indices(pairs,rows):
    by_index={tuple(row[0]):row for row in rows};seen=set();work=[]
    if len(by_index)!=len(rows):raise ValueError('Duplicate observed indices')
    for h in pairs:
        if not isinstance(h,list) or len(h)!=3 or any(type(v) is not int for v in h):
            raise ValueError('Invalid Bijvoet-pair index')
        a=tuple(h);b=tuple(-v for v in h)
        if a==b or a in seen or b in seen or a not in by_index or b not in by_index:
            raise ValueError('Missing, repeated or degenerate Bijvoet pair')
        seen.update((a,b))
        if any(type(by_index[k][3]) is not bool for k in (a,b)):
            raise ValueError('Invalid pair Free-R flags')
        if not by_index[a][3] and not by_index[b][3]:work.append(h)
    return sorted(work)


def summarize(e,native,groups,wavelength_A):
    if (e['protocol']!=PROTOCOL or common._canonical(e['policy'])!=common._canonical(request())
            or e['endpoint_sha256']!=endpoint_digest(native)
            or common._sha(e['active_state_before'])!=common._sha(e['active_state_after'])):
        raise ValueError('Anomalous map policy, endpoint or fitted state changed')
    if common._number(e['wavelength_A'])<=0 or e['wavelength_A']!=wavelength_A:
        raise ValueError('Anomalous map wavelength changed')
    common._sha(e['implementation_sha256'])
    if set(e['native_source_hashes'])!={'map_tools','miller','mtz','map_diagnostics'}:
        raise ValueError('Missing anomalous map source provenance')
    for v in e['native_source_hashes'].values():common._sha(v)
    if native['reflection_after']['anomalous'] is not True:
        raise ValueError('Anomalous map requires unmerged Bijvoet observations')
    work=work_pair_indices(e['pair_indices'],native['reflection_after']['rows'])
    if (not work or e['filename']!=FILENAME or e['column_labels']!=['ANOM','PHANOM']
            or common._canonical(e['coefficient_indices'])!=common._canonical(work)
            or type(e['coefficient_count']) is not int or e['coefficient_count']!=len(work)
            or type(e['excluded_free_pair_count']) is not int
            or e['excluded_free_pair_count']!=len(e['pair_indices'])-len(work)):
        raise ValueError('Anomalous map file, labels or work-pair membership changed')
    common._sha(e['sha256'])
    if type(e['size']) is not int or e['size']<=0:raise ValueError('Invalid anomalous map file size')
    maximum=common._number(e['max_abs_coefficient'])
    if maximum<0:raise ValueError('Negative coefficient magnitude')
    for key,limit in [('readback_max_complex_error',1e-4),('max_dano_amplitude_error',1e-10)]:
        error=common._number(e[key])
        if error<0 or error>limit*max(1.,maximum):raise ValueError('Anomalous coefficient check failed')
    if not isinstance(e['grid'],list) or len(e['grid'])!=3 or any(type(v) is not int or v<=0 for v in e['grid']):
        raise ValueError('Invalid anomalous sampling grid')
    fitted=[g for g in groups if g['refine_fdp']]
    if len(e['sites'])!=len(fitted):raise ValueError('Anomalous sample site count changed')
    for sample,g in zip(e['sites'],fitted):
        atom=native['atoms'][g['indices'][0]]
        if (sample['node_id']!=g['id'] or sample['key']!=atom['key'] or sample['xyz']!=atom['xyz']
                or type(sample['samples']) is not int or sample['samples']!=len(common._offsets())):
            raise ValueError('Anomalous sample identity, coordinate or sampling changed')
        for v in sample['xyz']:common._number(v)
        low=common._number(sample['sphere_min_sigma']);high=common._number(sample['sphere_max_sigma'])
        if not low<=common._number(sample['center_sigma'])<=high or not low<=common._number(sample['sphere_mean_sigma'])<=high:
            raise ValueError('Invalid anomalous map sample range')
    return dict(protocol=PROTOCOL,policy=request(),endpoint_sha256=e['endpoint_sha256'],
        native_state_unchanged=True,implementation_sha256=e['implementation_sha256'],
        native_source_hashes=e['native_source_hashes'],
        map={k:e[k] for k in ('wavelength_A','filename','column_labels','sha256','size','coefficient_count','excluded_free_pair_count',
            'max_abs_coefficient','readback_max_complex_error','max_dano_amplitude_error','grid','sites')},
        fit_context=common.fit_context(native['r_work'],native['r_free']),
        scientific_acceptance='NOT_ASSESSED',automatic_checkpoint_selection=False,
        limitation='Model-phased anomalous Fourier; not independent validation, per-atom fdp or an automatic atom count')


def verify_file(e,directory):
    if e['filename']!=FILENAME:raise ValueError('Unexpected anomalous map filename')
    p=Path(directory)/FILENAME
    if p.is_symlink() or not p.is_file():raise ValueError('Missing or linked anomalous map')
    raw=p.read_bytes()
    if len(raw)!=e['size'] or hashlib.sha256(raw).hexdigest()!=e['sha256']:
        raise ValueError('Anomalous map bytes differ from native capture')


def capture(fmodel,native,groups,policy,wavelength_A):
    from cctbx.array_family import flex
    from cctbx import miller
    from iotbx import mtz,reflection_file_reader
    import mmtbx.map_tools as map_tools
    if common._canonical(policy)!=common._canonical(request()) or not fmodel.f_obs().anomalous_flag() or fmodel.hl_coeffs() is not None:
        raise ValueError('Unsupported anomalous map policy')
    if (fmodel.r_work(),fmodel.r_free())!=(native['r_work'],native['r_free']):
        raise ValueError('Anomalous map is not from the completed fit')
    before=common._active_state(fmodel)
    # Native anomalous export returns before its generic Free-R filter.
    coeff=fmodel.map_coefficients(map_type='anomalous',exclude_free_r_reflections=False,
                                  fill_missing=False,isotropize=False,sharp=False)
    if coeff is None or coeff.size()==0:raise ValueError('No observed Bijvoet pairs for anomalous map')
    pairs=sorted(list(h) for h in coeff.indices())
    work=work_pair_indices(pairs,native['reflection_after']['rows']);wanted={tuple(h) for h in work}
    if not work:raise ValueError('No work-only Bijvoet pairs for anomalous map')
    coeff=coeff.select(flex.bool([tuple(h) in wanted for h in coeff.indices()]))
    obs={tuple(row[0]):row[1] for row in native['reflection_after']['rows']}
    amplitude_error=max(abs(abs(z)-abs(obs[tuple(h)]-obs[tuple(-v for v in h)])/2.) for h,z in zip(coeff.indices(),coeff.data()))
    path=Path(FILENAME)
    if path.exists():raise ValueError('Refuse to overwrite anomalous map')
    coeff.as_mtz_dataset(column_root_label='ANOM',column_types='FP',
        label_decorator=mtz.label_decorator(phases_prefix='PH'),wavelength=wavelength_A).mtz_object().write(FILENAME)
    restored=reflection_file_reader.any_reflection_file(FILENAME).as_miller_arrays()
    if len(restored)!=1 or list(restored[0].indices())!=list(coeff.indices()):
        raise ValueError('Anomalous MTZ inventory or indices changed')
    grid=coeff.fft_map(resolution_factor=.25).apply_sigma_scaling().real_map_unpadded()
    uc=fmodel.f_obs().unit_cell();samples=[]
    for g in groups:
        if not g['refine_fdp']:continue
        a=native['atoms'][g['indices'][0]];pos=a['xyz']
        values=[float(grid.eight_point_interpolation(uc.fractionalize(tuple(pos[i]+delta[i] for i in range(3))))) for delta in common._offsets()]
        samples.append(dict(node_id=g['id'],key=a['key'],xyz=pos,samples=len(values),
            center_sigma=float(grid.eight_point_interpolation(uc.fractionalize(pos))),
            sphere_min_sigma=min(values),sphere_max_sigma=max(values),sphere_mean_sigma=math.fsum(values)/len(values)))
    raw=path.read_bytes()
    e=dict(protocol=PROTOCOL,policy=request(),endpoint_sha256=endpoint_digest(native),
        active_state_before=before,active_state_after=common._active_state(fmodel),
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_source_hashes={name:hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
            for name,module in [('map_tools',map_tools),('miller',miller),('mtz',mtz),('map_diagnostics',common)]},
        wavelength_A=wavelength_A,pair_indices=pairs,excluded_free_pair_count=len(pairs)-len(work),filename=FILENAME,
        column_labels=restored[0].info().labels,sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),
        coefficient_indices=work,coefficient_count=coeff.size(),max_abs_coefficient=float(flex.max(flex.abs(coeff.data()))),
        readback_max_complex_error=float(flex.max(flex.abs(restored[0].data()-coeff.data()))),
        max_dano_amplitude_error=amplitude_error,grid=list(grid.all()),sites=samples)
    summarize(e,native,groups,wavelength_A);verify_file(e,Path.cwd())
    return e
