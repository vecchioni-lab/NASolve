#!/usr/bin/env python3
"""Synthetic native image-gradient diagnostic; run with phenix.python.

This is a development probe, not a restraint generator, optimizer or scientific
qualification. It uses no structure/data files and changes no native installation.
Exit 2 records derivative review, including deliberately retained raw controls.
An optional Cedar source is trusted executable source, never a captured worker.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


def probe(cedar_source=None):
    from cctbx import geometry_restraints as gr, sgtbx, uctbx
    from scitbx.array_family import flex
    from scitbx import matrix
    import cctbx_geometry_restraints_ext
    cell=uctbx.unit_cell((40,40,70,90,90,120))
    identity=sgtbx.rt_mx();mate=sgtbx.rt_mx('-x+y+2/3,-x+1/3,z+1/3')
    first=[(0,0,0),(1.3,.1,.01),(.8,1.1,-.01),(-.5,1.4,.02),(-1.2,.4,.01),(-.7,-.6,-.02)]
    angle=math.radians(22)
    second=[(x*math.cos(angle)+z*math.sin(angle)+3.5,y+.2,-x*math.sin(angle)+z*math.cos(angle)+.3) for x,y,z in first]
    source=flex.vec3_double(first+[cell.orthogonalize(mate.inverse()*cell.fractionalize(p)) for p in second])
    ops=[identity]*6+[mate]*6
    O=matrix.sqr(cell.orthogonalization_matrix());F=matrix.sqr(cell.fractionalization_matrix())
    rotations=[O*matrix.sqr(op.r().as_double())*F for op in ops]
    def expand(points):return flex.vec3_double(cell.orthogonalize(op*cell.fractionalize(p)) for op,p in zip(ops,points))
    def pullback(grad):return flex.vec3_double(tuple(R.transpose()*matrix.col(g)) for R,g in zip(rotations,grad))
    bond=gr.shared_bond_simple_proxy([gr.bond_simple_proxy(i_seqs=(0,6),distance_ideal=2.8,weight=25,rt_mx_ji=mate)])
    angles=gr.shared_angle_proxy([gr.angle_proxy(i_seqs=(3,0,6),sym_ops=(identity,identity,mate),angle_ideal=116.2,weight=1/3.46**2)])
    plane=gr.shared_planarity_proxy([gr.planarity_proxy(i_seqs=list(range(12)),weights=flex.double(12,25))])
    symplane=gr.shared_planarity_proxy([gr.planarity_proxy(i_seqs=list(range(12)),sym_ops=ops,weights=flex.double(12,25))])
    parallel=gr.shared_parallelity_proxy([gr.parallelity_proxy(i_seqs=list(range(6)),j_seqs=list(range(6,12)),weight=1.,target_angle_deg=0.,slack=0.,limit=1.,top_out=False)])
    def evaluate(points,kind,gradients):
        g=flex.vec3_double(len(points),(0,0,0)) if gradients else flex.vec3_double()
        if kind=='bond_symmetry':value=gr.bond_residual_sum(unit_cell=cell,sites_cart=points,proxies=bond,gradient_array=g)
        elif kind=='angle_symmetry':value=gr.angle_residual_sum(unit_cell=cell,sites_cart=points,proxies=angles,gradient_array=g)
        elif kind=='planarity_symmetry':value=gr.planarity_residual_sum(unit_cell=cell,sites_cart=points,proxies=symplane,gradient_array=g)
        else:
            expanded=expand(points)
            if kind=='planarity_cartesian_pullback':value=gr.planarity_residual_sum(sites_cart=expanded,proxies=plane,gradient_array=g)
            elif kind in ('parallelity_cartesian_pullback','parallelity_cedar_pullback'):
                value=gr.parallelity_residual_sum(sites_cart=expanded,proxies=parallel,gradient_array=g)
                if gradients and kind=='parallelity_cedar_pullback':
                    fixed=correction.correct_parallelity_gradient(gr,flex,parallel,list(expanded),list(g.as_double()),native_residual=value,plane_order_safe=True)
                    g=flex.vec3_double(flex.double(fixed['gradient']))
            else:raise ValueError(kind)
            if gradients:g=pullback(g)
        if not math.isfinite(value) or (gradients and any(not math.isfinite(v) for row in g for v in row)):
            raise ValueError('Native probe returned nonfinite values')
        return value,g
    correction=None
    if cedar_source is not None:
        import importlib.util
        path=Path(cedar_source)/'nasolve/cif_parallelity_correction.py'
        spec=importlib.util.spec_from_file_location('topostitch_probe_cedar_correction',path)
        correction=importlib.util.module_from_spec(spec);spec.loader.exec_module(correction)
    kinds=['bond_symmetry','angle_symmetry','planarity_symmetry','planarity_cartesian_pullback','parallelity_cartesian_pullback']
    if correction is not None:kinds.append('parallelity_cedar_pullback')
    results=[]
    for kind in kinds:
        value,analytic=evaluate(source,kind,True);steps=[]
        for h in (1e-4,1e-5,1e-6):
            maximum=0.;worst=None
            for i in range(len(source)):
                for axis in range(3):
                    values=[]
                    for sign in (-1,1):
                        changed=source.deep_copy();point=list(changed[i]);point[axis]+=sign*h;changed[i]=point
                        values.append(evaluate(changed,kind,False)[0])
                    numeric=(values[1]-values[0])/(2*h);error=abs(numeric-analytic[i][axis])
                    if error>maximum:maximum=error;worst={'atom_index':i,'axis':axis,'analytic':analytic[i][axis],'finite_difference':numeric}
            steps.append({'step_angstrom':h,'max_absolute_error':maximum,'worst':worst})
        passed=sum(r['max_absolute_error']<=1e-6 for r in steps)>=2 and max(r['max_absolute_error'] for r in steps)<=1e-4
        results.append({'case':kind,'residual':value,'coordinate_count':len(source)*3,'finite_differences':steps,'derivatives_match':passed})
    sources=[]
    for module in (gr,cctbx_geometry_restraints_ext):
        path=Path(module.__file__).resolve();sources.append({'module':module.__name__,'historical_path':str(path),'sha256':sha256(path.read_bytes()).hexdigest()})
    if correction is not None:
        path=Path(correction.__file__).resolve();sources.append({'module':'nasolve.cif_parallelity_correction','historical_path':str(path),'sha256':sha256(path.read_bytes()).hexdigest(),'policy':correction.ORDER_CORRECTION_ID})
    path=Path(__file__).resolve()
    return {'schema_version':1,'kind':'topostitch-native-image-gradient-probe',
        'python':sys.version,'script_sha256':sha256(path.read_bytes()).hexdigest(),'native_sources':sources,
        'fixture':{'kind':'synthetic_noncollinear_planes','cell':list(cell.parameters()),'target_operator':mate.as_xyz(),
                   'asu_coordinates':list(source),'weights':{'bond':25,'angle':1/3.46**2,'planarity_per_atom':25,'parallelity':1}},
        'finite_difference_policy':{'minimum_steps_with_error_at_most_1e_minus_6':2,'all_steps_error_at_most':1e-4},
        'results':results,'status':'PROBE_PASS' if all(r['derivatives_match'] for r in results) else 'NATIVE_DERIVATIVE_REVIEW',
        'scientific_qualification':False,'runtime_authority':False,'optimization':False,
        'limitations':['One synthetic nonorthogonal-cell fixture; no blanket native API or scientific qualification',
            'Symmetry parallelity constructor is not exercised; Cartesian parallelity plus explicit rotation pullback is tested',
            'No manager mutation, chemical topology, covalent attachment or nonbonded exclusion changes']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,help='Optional new JSON file; refuses to overwrite')
    parser.add_argument('--cedar-source',type=Path,help='Optional trusted Cedar src directory for its existing Cartesian plane correction')
    args=parser.parse_args(argv)
    if args.out is not None and args.out.exists():parser.error('Output already exists')
    try:report=probe(args.cedar_source)
    except (ImportError,OSError,ValueError,RuntimeError) as exc:parser.exit(1,f'{parser.prog}: {exc}\n')
    encoded=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if args.out is not None:
        with args.out.open('x') as stream:stream.write(encoded)
    else:print(encoded,end='')
    return 0 if report['status']=='PROBE_PASS' else 2


if __name__=='__main__':sys.exit(main())
