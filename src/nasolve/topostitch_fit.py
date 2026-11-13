"""Finite single-window placement proposals against an explicitly selected pair.

This local least-squares search has no density or R-factor target and never
writes/adopts a model. Pairing intent, window and all motion/strain scales are
caller inputs. A proposed transform still needs geometry and native validation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys

from .topostitch_contacts import inspect_end_contacts
from .topostitch_coordinates import ResidueSite, _read_atoms, _residue, _plane, _dot, _cross
from .topostitch_inspect import _keys, load_registered_end_assignments
from .topostitch_periodic import _crystal
from .topostitch_preview import _json, _number, _vector, _rotation, _apply, _angle, _prepare, TrialLimitError
from .topostitch_registration import _coordinate_site


class _BudgetExhausted(RuntimeError):
    pass


def _scipy():
    try:
        from scipy.optimize import least_squares
    except ImportError as exc:
        raise RuntimeError('Placement fitting requires the optional NASolve[topology-fit] installation') from exc
    return least_squares


def _validate_request(request):
    _keys(request, {'schema_version','kind','model_sha256','discovery_file_sha256','registration_file_sha256',
        'reference_catalog_sha256','search','candidate','window','motion_bounds','objective','limits','max_residual_evaluations'})
    if type(request['schema_version']) is not int or request['schema_version'] != 1 or request['kind'] != 'topostitch-placement-request':
        raise ValueError('Expected a schema-1 topostitch-placement-request')
    search=request['search']
    _keys(search, {'periodic','radius_angstrom','max_pairs','max_image_tests'})
    if type(search['periodic']) is not bool:
        raise ValueError('periodic must be a boolean')
    _number(search['radius_angstrom'],'radius_angstrom',positive=True)
    for name,value in (('max_pairs',search['max_pairs']),('max_image_tests',search['max_image_tests']),
                       ('max_residual_evaluations',request['max_residual_evaluations'])):
        if type(value) is not int or value < 1:
            raise ValueError(f'{name} must be a positive integer')
    _keys(request['candidate'], {'ends','target_image_operator'})
    ends=request['candidate']['ends']
    if not isinstance(ends,list) or len(ends)!=2 or any(not isinstance(e,str) for e in ends) or ends[0]==ends[1]:
        raise ValueError('Initial placement requires two distinct explicitly selected ends')
    operator=request['candidate']['target_image_operator']
    if (search['periodic'] and (not isinstance(operator,str) or not operator)) or (not search['periodic'] and operator is not None):
        raise ValueError('Selected image operator must match the periodic search mode')
    _keys(request['window'], {'window_id','max_base_pairs','fixed_anchor_pairs'})
    if not isinstance(request['window']['window_id'],str):
        raise ValueError('window_id must be a string')
    _keys(request['motion_bounds'], {'rotation_degrees','translation_angstrom'})
    rotation=_vector(request['motion_bounds']['rotation_degrees'],'rotation bounds')
    translation=_vector(request['motion_bounds']['translation_angstrom'],'translation bounds')
    if min(*rotation,*translation)<=0 or math.hypot(*rotation)>180:
        raise ValueError('Motion component bounds must be positive with total rotation bound at most 180 degrees')
    _keys(request['objective'], {'backbone_distance_scale_angstrom','backbone_angle_scale_degrees',
        'plane_offset_scale_angstrom','plane_normal_scale_degrees','motion_weight'})
    for name,value in request['objective'].items():
        _number(value,name,positive=True)
    if request['objective']['plane_normal_scale_degrees']>90:
        raise ValueError('Plane-normal scale must not exceed 90 degrees')
    _keys(request['limits'], {'max_atom_displacement_angstrom','max_backbone_bond_change_angstrom','max_backbone_angle_change_degrees'})
    for name,value in request['limits'].items():
        _number(value,name,positive=True)
    return rotation+translation


def _trial(request, parameters):
    return {'schema_version':1,'kind':'topostitch-window-transform',
        'model_sha256':request['model_sha256'],'discovery_file_sha256':request['discovery_file_sha256'],
        'registration_file_sha256':request['registration_file_sha256'],
        'window_id':request['window']['window_id'],'max_window_pairs':request['window']['max_base_pairs'],
        'fixed_anchor_pairs':request['window']['fixed_anchor_pairs'],
        'rotation_vector_degrees':[float(v) for v in parameters[:3]],
        'translation_angstrom':[float(v) for v in parameters[3:]],**request['limits']}


def fit_end_placement(model_path, discovery_path, *, registration_path, request_path):
    """Return one bounded placement proposal, or an explicit no-proposal outcome.

    The residual-call cap includes finite-difference Jacobian evaluations. No
    partial best-so-far transform is promoted after budget exhaustion. The
    optimizer starts once, at zero motion; it never searches pairing alternatives.
    """
    request_bytes=Path(request_path).read_bytes()
    request=_json(request_bytes)
    bounds=_validate_request(request)
    least_squares=_scipy()
    zero=(0.,)*6
    snapshots,baseline=_prepare(model_path,discovery_path,registration_path,trial_value=_trial(request,zero))
    def verify_inputs():
        paths={'source':Path(model_path),'discovery':Path(discovery_path),'registration':Path(registration_path)}
        if any(path.read_bytes()!=snapshots[name] for name,path in paths.items()) or Path(request_path).read_bytes()!=request_bytes:
            raise ValueError('Placement inputs changed during fitting')
    digest,assignments,_,mapping=load_registered_end_assignments(model_path,discovery_path,registration_path)
    search=request['search']
    observations=inspect_end_contacts(model_path,assignments,expected_sha256=digest,
        max_distance_angstrom=search['radius_angstrom'],periodic=search['periodic'],
        max_pairs=search['max_pairs'],max_image_tests=search['max_image_tests'])
    library=observations['contact_assessment']['library']
    if library['effective_catalog_sha256']!=request['reference_catalog_sha256']:
        raise ValueError('NARestraints reference catalog checksum mismatch')
    screening=observations['periodic_screening' if search['periodic'] else 'screening']
    candidates=screening['candidates']
    selected=[i for i,c in enumerate(candidates) if c['ends']==request['candidate']['ends']
              and c.get('target_image',{}).get('operator_xyz')==request['candidate']['target_image_operator']]
    if len(selected)!=1:
        raise ValueError('Selected pairing/image is absent or ambiguous in the frozen search scope')
    index=selected[0]; candidate=candidates[index]
    image_audit=None
    if search['periodic']:
        from .topostitch_images import _attach_image_audit
        _attach_image_audit(model_path,assignments,observations,candidate_index=index)
        image_audit=observations['selected_image_identity']
    contact=observations['contact_assessment']['candidates'][index]
    if any(p['assessment']!='MEASURED_NOT_VALIDATED' for p in contact['residue_pairs']):
        raise ValueError('Placement requires complete canonical contact measurements')
    window=baseline['window']
    if window['end_id'] not in candidate['ends']:
        raise ValueError('Selected window does not belong to the selected pairing')
    registry=_json(snapshots['registration'])
    registered=next(c for c in registry['copies'] if c['copy_id']==window['copy_id'])
    logical_needed=set(window['movable_sites'])|set(window['fixed_sites'])
    logical_needed.update(r[k] for r in baseline['backbone_audit']['links'] for k in ('from_site','to_site'))
    site_map={r['logical_site']:_coordinate_site(r['coordinate_site']) for r in registered['mappings']
              if r['logical_site'] in logical_needed}
    weights={site_map[s]:w for s,w in baseline['site_weights'].items()}
    other=next(a for a in assignments if a.end_id in candidate['ends'] and a.end_id!=window['end_id'])
    if set(weights)&set(other.overhang_sites+other.terminal_pair+other.inner_pair):
        raise ValueError('Initial single-window fit cannot move atoms belonging to the other end')
    inventory=_read_atoms(snapshots['source'])
    links=baseline['backbone_audit']['links']
    needed=set(weights)|{site_map[r[k]] for r in links for k in ('from_site','to_site')}
    for pair in contact['residue_pairs']:
        needed.update(ResidueSite(**s) for s in pair['sites'])
    coordinates={s:_residue(inventory,s)[1] for s in needed}
    if search['periodic']:
        gemmi,cell,_=_crystal(screening['inputs']['cell_parameters'],screening['inputs']['space_group'])
        op=gemmi.Op(candidate['target_image']['operator_xyz'])
        def image(xyz):
            frac=cell.fractionalize(gemmi.Position(*xyz))
            point=cell.orthogonalize(gemmi.Fractional(*op.apply_to_xyz(list(frac))))
            return (point.x,point.y,point.z)
    else:
        def image(xyz): return xyz
    origin=baseline['terminal_origin_angstrom']; objective=request['objective']
    normal_scale=math.sin(math.radians(objective['plane_normal_scale_degrees']))
    if normal_scale == 0:
        raise ValueError('Plane-normal scale is below the supported numerical range')

    def evaluate(parameters, *, serialized=None):
        source=coordinates if serialized is None else serialized
        moved={}
        for site,points in source.items():
            if serialized is None and site in weights:
                weight=weights[site]; rotation=_rotation(parameters[:3],weight)
                moved[site]={}
                for name,point in points.items():
                    rotated=_apply(rotation,tuple(x-o for x,o in zip(point,origin)))
                    moved[site][name]=tuple(x+o+weight*t for x,o,t in zip(rotated,origin,parameters[3:]))
            else:
                moved[site]=points
        contact_terms=[]; plane_terms=[]; backbone_terms=[]; distances=[]; angles=[]
        for pair in contact['residue_pairs']:
            for kind in ('bonds','angles'):
                for measurement in pair[kind]:
                    points=[]
                    for atom in measurement['atoms']:
                        point=moved[ResidueSite(**atom['site'])][atom['atom_name']]
                        points.append(image(point) if atom['image']=='target' else point)
                    observed=math.dist(*points) if kind=='bonds' else _angle(*points)
                    deviation=observed-measurement['reference_ideal']
                    contact_terms.append(deviation/measurement['reference_sigma'])
                    (distances if kind=='bonds' else angles).append(deviation)
            left,right=(moved[ResidueSite(**s)] for s in pair['sites'])
            a,na,_=_plane(left); b,nb,_=_plane({name:image(xyz) for name,xyz in right.items()})
            delta=tuple(y-x for x,y in zip(a,b))
            plane_terms.extend((_dot(delta,na)/objective['plane_offset_scale_angstrom'],
                                _dot(delta,nb)/objective['plane_offset_scale_angstrom']))
            plane_terms.extend(v/normal_scale for v in _cross(na,nb))
        for link in links:
            a,b=moved[site_map[link['from_site']]],moved[site_map[link['to_site']]]
            distance=math.dist(a["O3'"],b['P'])
            measured=(_angle(a["C3'"],a["O3'"],b['P']),_angle(a["O3'"],b['P'],b["O5'"]))
            backbone_terms.append((distance-link['distance_angstrom']['before'])/objective['backbone_distance_scale_angstrom'])
            backbone_terms.extend((v-old['before'])/objective['backbone_angle_scale_degrees']
                                  for v,old in zip(measured,link['angles_degrees']))
        motion_terms=[objective['motion_weight']*float(v)/bound for v,bound in zip(parameters,bounds)]
        residuals=contact_terms+plane_terms+backbone_terms+motion_terms
        if not all(math.isfinite(v) for v in residuals):
            raise ValueError('Nonfinite placement residual')
        def ss(values):
            total=sum(v*v for v in values)
            if not math.isfinite(total):
                raise ValueError('Placement objective exceeds the supported numerical range')
            return total
        metrics={'contact_sum_squares':ss(contact_terms),'plane_sum_squares':ss(plane_terms),
            'pair_target_sum_squares':ss(contact_terms+plane_terms),'backbone_sum_squares':ss(backbone_terms),
            'motion_sum_squares':ss(motion_terms),'total_sum_squares':ss(residuals),
            'bond_deviations_angstrom':distances,'angle_deviations_degrees':angles}
        return residuals,metrics

    _,before=evaluate(zero)
    settings={'method':'trf','jac':'3-point','diff_step':1e-4,'ftol':1e-8,'xtol':1e-8,'gtol':1e-8,
              'x_scale':list(bounds),'initial_parameters':list(zero),'loss':'linear'}
    report={'schema_version':1,'kind':'topostitch-placement-proposal',
        'algorithm':'single-window-canonical-contact-least-squares-v2',
        'request':request,'request_file_sha256':sha256(request_bytes).hexdigest(),
        'source_model_sha256':digest,'reference_library':library,'selected_candidate':candidate,'window':window,
        'selected_image_identity':image_audit,
        'solver':{'name':'scipy.optimize.least_squares','scipy_version':version('scipy'),
                  'numpy_version':version('numpy'),'settings':settings,'residual_calls':0,'nfev':None,'njev':None},
        'before':before,'continuous_after':None,'serialized_after':None,'trial':None,
        'status':None,'geometry_validated':False,'runtime_authority':False,
        'source_preserved':True,'model_written':False,'refinement_state':'NOT_ATTEMPTED','review_state':'UNREVIEWED',
        'limitations':['One zero-initialized local search for one explicitly chosen pairing and window',
            'Canonical full-overhang geometry target; no density, diffraction or R-factor objective',
            'Objective scales are caller policy, not calibrated likelihoods or acceptance thresholds',
            'Selected-coordinate image audit is a precondition only; full physical orbit/capacity remains unqualified',
            'No torsion, packing, atomistic closure or native qualification',
            'No reconstruction, chemical topology changes, campaign adoption or best-partner claim']}
    if image_audit is not None and image_audit['assessment']!='SELECTED_COORDINATES_DISTINCT':
        report['status']='IMAGE_IDENTITY_REVIEW_REQUIRED'
        verify_inputs()
        return report
    calls=0
    def residual(parameters):
        nonlocal calls
        if calls>=request['max_residual_evaluations']:
            raise _BudgetExhausted()
        calls+=1
        return evaluate(parameters)[0]
    try:
        fitted=least_squares(residual,zero,bounds=([-v for v in bounds],bounds),
            method='trf',jac='3-point',diff_step=1e-4,ftol=1e-8,xtol=1e-8,gtol=1e-8,
            x_scale=bounds,loss='linear',max_nfev=request['max_residual_evaluations'])
    except _BudgetExhausted:
        report['status']='BUDGET_EXHAUSTED'
    else:
        report['solver'].update(nfev=int(fitted.nfev),njev=None if fitted.njev is None else int(fitted.njev),
            success=bool(fitted.success),status_code=int(fitted.status),message=str(fitted.message))
        _,report['continuous_after']=evaluate(fitted.x)
        if not fitted.success:
            report['status']='SOLVER_DID_NOT_CONVERGE'
        else:
            proposed=_trial(request,fitted.x)
            try:
                final_snapshots,preview=_prepare(model_path,discovery_path,registration_path,trial_value=proposed)
            except TrialLimitError as exc:
                report.update(status='TRIAL_LIMIT_REJECTED',reason=str(exc))
            else:
                final_inventory=_read_atoms(final_snapshots['candidate'])
                rounded={site:_residue(final_inventory,site)[1] for site in needed}
                _,report['serialized_after']=evaluate(fitted.x,serialized=rounded)
                # Numerical non-improvement is a no-op, not an accepted repair.
                if report['serialized_after']['pair_target_sum_squares']>=before['pair_target_sum_squares']-1e-8:
                    report['status']='NO_PAIR_TARGET_IMPROVEMENT'
                else:
                    report.update(status='TRANSFORM_FOR_REVIEW',trial=proposed,
                        candidate_model_sha256=preview['candidate_model_sha256'],
                        preview_audit={'max_atom_displacement_angstrom':preview['max_atom_displacement_angstrom'],
                                       'backbone_audit':preview['backbone_audit']})
    report['solver']['residual_calls']=calls
    verify_inputs()
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(prog='nasolve-topostitch-fit',
        description='Propose a bounded terminal motion for an explicitly chosen pairing; write no models.')
    parser.add_argument('model',type=Path)
    parser.add_argument('discovery',type=Path)
    parser.add_argument('--registration',required=True,type=Path)
    parser.add_argument('--request',required=True,type=Path)
    args=parser.parse_args(argv)
    try:
        report=fit_end_placement(args.model,args.discovery,registration_path=args.registration,request_path=args.request)
    except (OSError,ValueError,RuntimeError) as exc:
        parser.exit(2,f'{parser.prog}: {exc}\n')
    print(json.dumps(report,indent=2,sort_keys=True,allow_nan=False))
    return 0


if __name__=='__main__':
    sys.exit(main())
