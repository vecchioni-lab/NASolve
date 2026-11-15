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
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from nasolve import topostitch_transport as transport
    cell=uctbx.unit_cell((40,40,70,90,90,120))
    identity=sgtbx.rt_mx();mate=sgtbx.rt_mx('-x+y+2/3,-x+1/3,z+1/3')
    first=[(0,0,0),(1.3,.1,.01),(.8,1.1,-.01),(-.5,1.4,.02),(-1.2,.4,.01),(-.7,-.6,-.02)]
    angle=math.radians(22)
    second=[(x*math.cos(angle)+z*math.sin(angle)+3.5,y+.2,-x*math.sin(angle)+z*math.cos(angle)+.3) for x,y,z in first]
    source=flex.vec3_double(first+[cell.orthogonalize(mate.inverse()*cell.fractionalize(p)) for p in second])
    ops=[identity]*6+[mate]*6
    O=matrix.sqr(cell.orthogonalization_matrix());F=matrix.sqr(cell.fractionalization_matrix())
    images=[transport.CartesianImage(
        tuple(tuple((O*matrix.sqr(op.r().as_double())*F)[3*i+j] for j in range(3)) for i in range(3)),
        tuple(cell.orthogonalize(op.t().as_double()))) for op in ops]
    refs=tuple(enumerate(images))
    def expand(points):return flex.vec3_double(transport.expand_sites(list(points),refs))
    def pullback(grad):return flex.vec3_double(transport.accumulate_image_gradients(len(source),refs,list(grad)))
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
    for module in (gr,cctbx_geometry_restraints_ext,transport):
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


def probe_angle_snapshot():
    """Qualify only the new angle record/rebuild adapter, not a native manager."""
    import copy
    import pickle
    from types import SimpleNamespace
    from cctbx import geometry_restraints as gr, sgtbx, uctbx
    from scitbx.array_family import flex
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
    from nasolve.topostitch_native_terms import freeze_native_angles, NativeAngleSnapshot
    from nasolve.topostitch_recipe import recipe_digest
    cell = uctbx.unit_cell((40,40,70,90,90,120))
    mate = sgtbx.rt_mx('-x+y+2/3,-x+1/3,z+1/3')
    identity = sgtbx.rt_mx()
    # The third site is stored in a distant ASU image; its intended mate is local.
    points = [(1.,2.,3.), (2.4,2.2,3.1), (3.2,3.4,3.5), (4.,4.,4.)]
    points[2] = cell.orthogonalize(mate.inverse()*cell.fractionalize(points[2]))
    labels = ['synthetic-'+str(i) for i in range(4)]
    rows = [dict(i_seqs=[0,1,2], atoms=labels[:3], angle_ideal=109.5, weight=2., origin_id=2),
            dict(i_seqs=[1,2,3], atoms=labels[1:], angle_ideal=115., weight=0., origin_id=3)]
    proxies = gr.shared_angle_proxy([
        gr.angle_proxy(i_seqs=(0,1,2),sym_ops=(identity,identity,mate),
                       angle_ideal=109.5,weight=2.,slack=.25,origin_id=2),
        gr.angle_proxy(i_seqs=(1,2,3),angle_ideal=115.,weight=0.,slack=0.,origin_id=3)])
    native = dict(atom_count=4, atoms=[dict(i_seq=i,label=l) for i,l in enumerate(labels)],
                  geometry=dict(proxy_counts=dict(angle=2),proxy_details=dict(angle=rows)))
    record = freeze_native_angles(SimpleNamespace(angle_proxies=proxies), native,
                                  cell_parameters=cell.parameters(), space_group='R 3:H')
    adapter = NativeAngleSnapshot(record, expected_sha256=recipe_digest(record))
    value = adapter.evaluate(points, atom_labels=labels)
    for restored in (copy.deepcopy(adapter), pickle.loads(pickle.dumps(adapter)),
                     NativeAngleSnapshot(json.loads(json.dumps(record)), expected_sha256=recipe_digest(record))):
        assert restored.snapshot() == record
        assert restored.evaluate(points, atom_labels=labels) == value
    # Native array reload remains a negative control; this adapter does not fix it.
    raw = pickle.loads(pickle.dumps(proxies))
    wrong = float(gr.angle_residual_sum(unit_cell=cell, sites_cart=flex.vec3_double(points),
                  proxies=raw, gradient_array=flex.vec3_double()))
    assert raw[0].sym_ops is None and abs(wrong-value['residual_sum']) > 1.
    cell_missing = float(gr.angle_residual_sum(sites_cart=flex.vec3_double(points),
                         proxies=proxies, gradient_array=flex.vec3_double()))
    assert abs(cell_missing-value['residual_sum']) > 1.
    errors = []
    for h in (1e-5,1e-6):
        changes=[]
        for i in range(len(points)):
            for axis in range(3):
                plus=[list(p) for p in points];minus=[list(p) for p in points]
                plus[i][axis]+=h;minus[i][axis]-=h
                derivative=(adapter.evaluate(plus,atom_labels=labels)['residual_sum']-
                            adapter.evaluate(minus,atom_labels=labels)['residual_sum'])/(2*h)
                changes.append(abs(derivative-value['gradients'][i][axis]))
        errors.append(dict(step_angstrom=h,max_absolute_error=max(changes)))
    assert max(r['max_absolute_error'] for r in errors) < 1e-4
    refusals=[]
    def refuses(name, call):
        try:call()
        except (ValueError, RuntimeError):refusals.append(name)
        else:raise AssertionError('Expected refusal: '+name)
    refuses('reordered_labels', lambda:adapter.evaluate(points,atom_labels=labels[::-1]))
    refuses('short_coordinates', lambda:adapter.evaluate(points[:-1],atom_labels=labels))
    # Even a correctly checksummed record must obey the native group and metric.
    wrong_group=copy.deepcopy(record);wrong_group['crystal']['space_group']='P 1'
    refuses('wrong_space_group',lambda:NativeAngleSnapshot(wrong_group,expected_sha256=recipe_digest(wrong_group)))
    changed=copy.deepcopy(record);changed['terms'][0]['sym_ops'][2]='x,y,z'
    refuses('stale_snapshot_digest',lambda:NativeAngleSnapshot(changed,expected_sha256=recipe_digest(record)))
    adapter._proxies=raw
    refuses('lost_live_operators',lambda:adapter.evaluate(points,atom_labels=labels))
    refuses('serialize_damaged_adapter',lambda:pickle.dumps(adapter))
    adapter=NativeAngleSnapshot(record,expected_sha256=recipe_digest(record));adapter._proxies[0].weight=1.
    refuses('changed_live_weight',lambda:adapter.evaluate(points,atom_labels=labels))
    # Native subset/reindex remains explicit; the adapter requires a freshly bound record.
    selection=flex.size_t([2,0,1]);subset=proxies.proxy_select(n_seq=4,iselection=selection)
    subset_points=flex.vec3_double(points).select(selection)
    selected_energy=float(gr.angle_residual_sum(unit_cell=cell,sites_cart=subset_points,
                          proxies=subset,gradient_array=flex.vec3_double()))
    assert abs(selected_energy-value['residual_sum']) < 1e-8
    assert [o.as_xyz() for o in subset[0].sym_ops] == record['terms'][0]['sym_ops']
    import cctbx_geometry_restraints_ext
    from nasolve import topostitch_native_terms, topostitch_transport
    sources=[]
    for module in (gr,cctbx_geometry_restraints_ext,topostitch_native_terms,topostitch_transport):
        path=Path(module.__file__).resolve()
        sources.append(dict(module=module.__name__,historical_path=str(path),sha256=sha256(path.read_bytes()).hexdigest()))
    return dict(schema_version=1,kind='topostitch-native-angle-snapshot-probe',status='PROBE_PASS',
        script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),native_sources=sources,
        python=sys.version,fixture=dict(cell=list(cell.parameters()),space_group='R 3:H',points=points),
        snapshot=record,snapshot_sha256=recipe_digest(record),evaluation=value,
        finite_differences=errors,json_deepcopy_pickle_reconstruction_exact=True,
        native_subset_reindex_energy_matches=True,refusals=refusals,
        negative_controls=dict(native_pickle_drops_images=True,native_pickle_residual=wrong,
                               omitted_cell_residual=cell_missing),
        runtime_authority=False,scientific_qualification=False,optimization=False,
        limitations=['Synthetic angle-only adapter diagnostic; no ordinary manager or refinement integration',
                     'No covalent links, complete seam terms, exclusions or topology approval'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,help='Optional new JSON file; refuses to overwrite')
    parser.add_argument('--cedar-source',type=Path,help='Optional trusted Cedar src directory for its existing Cartesian plane correction')
    parser.add_argument('--angle-snapshot-only',action='store_true',help='Only qualify explicit angle snapshot reload/evaluation')
    args=parser.parse_args(argv)
    if args.out is not None and args.out.exists():parser.error('Output already exists')
    try:report=probe_angle_snapshot() if args.angle_snapshot_only else probe(args.cedar_source)
    except (ImportError,OSError,ValueError,RuntimeError) as exc:parser.exit(1,f'{parser.prog}: {exc}\n')
    encoded=json.dumps(report,indent=2,allow_nan=False)+'\n'
    if args.out is not None:
        with args.out.open('x') as stream:stream.write(encoded)
    else:print(encoded,end='')
    return 0 if report['status']=='PROBE_PASS' else 2


if __name__=='__main__':sys.exit(main())
