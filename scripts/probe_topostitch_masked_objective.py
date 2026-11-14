#!/usr/bin/env python3
"""Read-only complete derivatives of an explicit masked native objective.

Run with phenix.python. The trusted Cedar source supplies native correction and
static-definition checks. Native monomer interpretation uses installed defaults
with NCS restraint building disabled; this is not authenticated capture replay.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys


def _module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def probe(model,recipe,recipe_sha256,mask_path,mask_sha256,cedar_source):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from nasolve import topostitch_native_recipe as compiled, topostitch_transport
    from iotbx import phil
    from mmtbx.command_line import pdb_interpretation as command
    from mmtbx.monomer_library import server,pdb_interpretation
    from cctbx import geometry_restraints as gr
    from cctbx.geometry_restraints import flags
    from scitbx.array_family import flex
    original={p:p.read_bytes() for p in (model,recipe,mask_path)}
    if sha256(original[mask_path]).hexdigest()!=mask_sha256:
        raise ValueError('Mask request checksum mismatch')
    request=json.loads(original[mask_path]);packet=json.loads(original[recipe])
    fields={'schema_version','kind','source_model_sha256','movable_indices',
            'tether_sigma_angstrom','max_displacement_angstrom','max_evaluations'}
    if (set(request)!=fields or type(request['schema_version']) is not int or request['schema_version']!=1
            or request['kind']!='topostitch-native-mask-request'
            or request['source_model_sha256']!=sha256(original[model]).hexdigest()):
        raise ValueError('Unsupported or stale mask request')
    correction=_module('trusted_cedar_correction',cedar_source/'nasolve/cif_parallelity_correction.py')
    audit=_module('trusted_cedar_audit',cedar_source/'nasolve/cif_gradient_audit.py')
    modules=[compiled,topostitch_transport,correction,audit]+[importlib.import_module(n) for n in (
        'cctbx.geometry_restraints.manager','cctbx.geometry_restraints.energies','cctbx_geometry_restraints_ext')]
    sources={Path(m.__file__).resolve():Path(m.__file__).resolve().read_bytes() for m in modules}
    pairs=compiled.NativePairRecipe(packet,original[model],expected_recipe_sha256=recipe_sha256,correction=correction)
    master=command.get_master_phil().fetch(sources=[phil.parse('pdb_interpretation.use_ncs_to_build_restraints = False')])
    params=master.extract();log=io.StringIO()
    interpreted=pdb_interpretation.process(mon_lib_srv=server.server(),ener_lib=server.ener_lib(),
        params=params.pdb_interpretation,file_name=str(model),strict_conflict_handling=True,
        substitute_non_crystallographic_unit_cell_if_necessary=False,keep_monomer_mappings=True,log=log)
    acp=interpreted.all_chain_proxies
    if acp.fatal_problems_message() is not None:
        raise ValueError(acp.fatal_problems_message())
    geo=interpreted.geometry_restraints_manager(params_edits=params.geometry_restraints.edits,
                                               params_remove=params.geometry_restraints.remove)
    signature=audit.fixed_signature(geo,acp.sites_cart_exact())
    options={k:request[k] for k in ('tether_sigma_angstrom','max_displacement_angstrom','max_evaluations')}
    def construct(**changes):
        kw=dict(movable_indices=request['movable_indices'],expected_native_signature=signature,
                correction=correction,native_audit=audit,**options);kw.update(changes)
        return compiled.NativeMaskedObjective(geo,acp.pdb_hierarchy,original[model],pairs,**kw)
    objective=construct();binding=objective.binding_report();count=3*len(request['movable_indices'])
    if count>1200:
        raise ValueError('Complete masked derivative probe is capped at 1200 coordinates')
    # Frozen general perturbation, independent of structure/geometry outcomes.
    amplitude=.002
    if math.sqrt(3)*amplitude+1e-4>=request['max_displacement_angstrom']:
        raise ValueError('Displacement bound is too small for the declared probe')
    cases=[]
    for name,delta in [('zero',[0.]*count),('nonuniform',[amplitude*math.sin(i+1) for i in range(count)])]:
        start=objective.evaluate(delta);checks=[]
        native=correction.evaluate_fixed_native(geo,start['points'],flags.flags(default=True),gr,flex,plane_order_safe=True)
        pair=pairs.evaluate(start['points'],atom_identities=compiled.native_atom_identities(acp.pdb_hierarchy))
        manual=native['target']+pair['target']+math.fsum(v*v/request['tether_sigma_angstrom']**2 for v in delta)
        if abs(start['target']-manual)>1e-8:
            raise ValueError('Composed target differs from independent direct components')
        for step in (1e-4,1e-5):
            maximum=0.;worst=None
            for i in range(count):
                plus=delta.copy();minus=delta.copy();plus[i]+=step;minus[i]-=step
                numeric=(objective.evaluate(plus)['target']-objective.evaluate(minus)['target'])/(2*step)
                error=abs(numeric-start['gradient'][i])
                if error>maximum:maximum,worst=error,i
            checks.append({'step_angstrom':step,'coordinate_count':count,'max_absolute_error':maximum,'worst_variable':worst})
        repeat=objective.evaluate(delta)
        if repeat['target']!=start['target'] or repeat['gradient']!=start['gradient']:
            raise ValueError('Repeated masked objective changed')
        cases.append({'name':name,'displacement_amplitude_angstrom':0. if name=='zero' else amplitude,
            'target':start['target'],'native_target':start['native_target'],'pair_target':start['pair_target'],
            'tether_target':start['tether_target'],'native_components':start['native_components'],
            'pair_components':start['pair_components'],'derivatives':checks,'fixed_coordinates_preserved':True})
        print(json.dumps({'case':name,'checks':checks}),flush=True)
    rejected=[]
    def rejects(name,fn):
        try:fn()
        except (ValueError,RuntimeError):rejected.append(name)
        else:raise ValueError('Negative control accepted: '+name)
    zero=[0.]*count
    rejects('wrong_static_signature',lambda:construct(expected_native_signature='0'*64))
    rejects('duplicate_mask_index',lambda:construct(movable_indices=[0,0]))
    rejects('nonfinite_variable',lambda:objective.evaluate([float('nan')]+zero[1:]))
    rejects('excess_displacement',lambda:objective.evaluate([request['max_displacement_angstrom']+1]+zero[1:]))
    rejects('nonrepresentable_tether',lambda:construct(tether_sigma_angstrom=1e-300))
    tiny=construct(max_evaluations=1);tiny.evaluate(zero)
    rejects('evaluation_budget',lambda:tiny.evaluate(zero))
    geo.external_energy_function=lambda **kw:0.
    try:rejects('unexpected_native_callback',lambda:objective.evaluate(zero))
    finally:geo.external_energy_function=None
    atom=acp.pdb_hierarchy.atoms()[0];saved=atom.xyz;atom.xyz=(saved[0]+.01,saved[1],saved[2])
    try:rejects('changed_native_reference',lambda:objective.evaluate(zero))
    finally:atom.xyz=saved
    saved=atom.name;atom.name=' QQQ'
    try:rejects('changed_native_identity',lambda:objective.evaluate(zero))
    finally:atom.name=saved
    proxy=geo.angle_proxies[0];saved=proxy.weight;proxy.weight=saved*2
    try:rejects('changed_native_definition',lambda:objective.evaluate(zero))
    finally:proxy.weight=saved
    objective.evaluate(zero)
    if any(p.read_bytes()!=data for p,data in original.items()) or any(p.read_bytes()!=data for p,data in sources.items()):
        raise ValueError('Inputs or trusted numerical sources changed during probe')
    passed=all(c['max_absolute_error']<=1e-3 for row in cases for c in row['derivatives'])
    return {'schema_version':1,'kind':'topostitch-masked-native-objective-probe',
        'status':'DERIVATIVES_PASS' if passed else 'DERIVATIVE_REVIEW',
        'execution':'COMPLETE_ENERGY_AND_DERIVATIVE_PROBE','binding':binding,'cases':cases,
        'derivative_absolute_bound':1e-3,'negative_controls_rejected':rejected,
        'mask_file_sha256':mask_sha256,'recipe_sha256':recipe_sha256,
        'effective_native_phil':master.as_str(),'native_interpretation_log':log.getvalue(),
        'native_sources':[{'module':m.__name__,'sha256':sha256(sources[Path(m.__file__).resolve()]).hexdigest()} for m in modules],
        'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'python':sys.version,
        'inputs_unchanged':True,'optimization':False,'refinement':False,'scientific_acceptance':False,
        'limitations':['Installed monomer interpretation only; not authenticated Cedar capture replay',
            'No optimizer, native lifecycle, complete nonbonded policy authentication, packing or diffraction qualification']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('model','recipe','mask','cedar-source','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--recipe-sha256',required=True);parser.add_argument('--mask-sha256',required=True)
    args=parser.parse_args(argv)
    if args.out.exists():parser.error('Output already exists')
    try:
        report=probe(args.model,args.recipe,args.recipe_sha256,args.mask,args.mask_sha256,args.cedar_source)
        with args.out.open('x') as stream:json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print(report['status'])
        return 0 if report['status']=='DERIVATIVES_PASS' else 2
    except (ImportError,OSError,ValueError,RuntimeError,KeyError,TypeError,IndexError) as exc:
        parser.exit(1,f'{parser.prog}: {exc}\n')


if __name__=='__main__':sys.exit(main())
