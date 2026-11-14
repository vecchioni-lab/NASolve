#!/usr/bin/env python3
"""Check a frozen complete pair recipe with phenix.python; no optimization.

The Cedar source is explicitly trusted executable code, never a captured worker.
Finite differences cover every referenced ASU coordinate within an explicit cap.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import sys


def probe(model, recipe, expected_digest, cedar_source, *, max_coordinates=1200):
    from iotbx import pdb
    from cctbx import geometry_restraints
    import cctbx_geometry_restraints_ext
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from nasolve import topostitch_recipe, topostitch_native_recipe, topostitch_transport
    model_data, recipe_data = model.read_bytes(), recipe.read_bytes()
    packet = json.loads(recipe_data)
    correction_path = cedar_source/'nasolve/cif_parallelity_correction.py'
    spec = importlib.util.spec_from_file_location('trusted_topostitch_cedar_correction',correction_path)
    correction = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(correction)
    modules = (geometry_restraints,cctbx_geometry_restraints_ext,topostitch_recipe,
               topostitch_native_recipe,topostitch_transport,correction)
    source_snapshots = {Path(m.__file__).resolve():Path(m.__file__).resolve().read_bytes() for m in modules}
    cls = topostitch_native_recipe.NativePairRecipe
    binding = cls(packet,model_data,expected_recipe_sha256=expected_digest,correction=correction)
    hierarchy = pdb.input(source_info=None,lines=model_data.decode('ascii')).construct_hierarchy(sort_atoms=False)
    identities = topostitch_native_recipe.native_atom_identities(hierarchy)
    points = list(hierarchy.atoms().extract_xyz())
    report = binding.binding_report()
    indices = sorted({r['asu_index'] for r in report['references']})
    if type(max_coordinates) is not int or not 1 <= max_coordinates <= 10000 or 3*len(indices) > max_coordinates:
        raise ValueError('Complete derivative coverage exceeds the declared coordinate budget')
    initial = binding.evaluate(points,atom_identities=identities)
    energy_only = binding.evaluate(points,atom_identities=identities,compute_gradients=False)
    if energy_only['gradients'] is not None or energy_only['target'] != initial['target']:
        raise ValueError('Energy-only and gradient evaluations disagree')
    checks = []
    for step in (1e-4,1e-5):
        maximum, worst = 0., None
        for i in indices:
            for axis in range(3):
                values = []
                for sign in (-1,1):
                    changed = list(points)
                    p = list(changed[i]);p[axis] += sign*step;changed[i] = tuple(p)
                    values.append(binding.evaluate(changed,atom_identities=identities,compute_gradients=False)['target'])
                numeric = (values[1]-values[0])/(2*step)
                error = abs(numeric-initial['gradients'][i][axis])
                if error > maximum:
                    maximum, worst = error, {'asu_index':i,'axis':axis}
        checks.append({'step_angstrom':step,'coordinate_count':3*len(indices),
                       'max_absolute_error':maximum,'worst':worst})
    untouched = set(range(len(points)))-set(indices)
    if any(any(v != 0 for v in initial['gradients'][i]) for i in untouched):
        raise ValueError('Unreferenced ASU atom received a pair-energy gradient')
    rejected = []
    def rejects(name, fn):
        try:
            fn()
        except (ValueError, RuntimeError):
            rejected.append(name)
        else:
            raise ValueError('Negative control was accepted: '+name)
    rejects('stale_recipe_digest',lambda:cls(packet,model_data,expected_recipe_sha256='0'*64,correction=correction))
    rejects('changed_source_bytes',lambda:cls(packet,model_data+b'\n',expected_recipe_sha256=expected_digest,correction=correction))
    wrong_order = list(reversed(identities))
    rejects('changed_atom_order',lambda:binding.evaluate(points,atom_identities=wrong_order))
    rejects('changed_coordinate_count',lambda:binding.evaluate(points[:-1],atom_identities=identities))
    changed = list(points);changed[indices[0]] = (float('nan'),0.,0.)
    rejects('nonfinite_coordinates',lambda:binding.evaluate(changed,atom_identities=identities))
    def changed_phil(edit):
        value = deepcopy(packet)
        value['pairs'][0]['phil'] = edit(value['pairs'][0]['phil'])
        value['pairs'][0]['phil_sha256'] = sha256(value['pairs'][0]['phil'].encode()).hexdigest()
        value['library']['effective']['emitted_recipes'] = [p['phil'] for p in value['pairs']]
        value['library']['effective_sha256'] = topostitch_recipe.recipe_digest(value['library']['effective'])
        return cls(value,model_data,expected_recipe_sha256=topostitch_recipe.recipe_digest(value),correction=correction)
    rejects('negative_plane_sigma',lambda:changed_phil(lambda s:s.replace('sigma = 0.176','sigma = -0.176')))
    rejects('partial_canonical_plane',lambda:changed_phil(lambda s:s.replace(' or name N7','')))
    rejects('unsupported_phil_field',lambda:changed_phil(lambda s:s.replace('planarity {','planarity {\n      slack = 1')))
    packet['pairs'][0]['phil'] = 'caller mutation after construction'
    if binding.binding_report() != report or binding.evaluate(points,atom_identities=identities)['target'] != initial['target']:
        raise ValueError('Mutable input changed a compiled binding')
    if model.read_bytes() != model_data or recipe.read_bytes() != recipe_data:
        raise ValueError('Input files changed during native probe')
    if any(path.read_bytes() != data for path,data in source_snapshots.items()):
        raise ValueError('Trusted numerical source changed during native probe')
    sources = [{'module':m.__name__,'sha256':sha256(source_snapshots[Path(m.__file__).resolve()]).hexdigest()}
               for m in modules]
    passed = all(c['max_absolute_error'] <= 1e-4 for c in checks)
    return {'schema_version':1,'kind':'topostitch-complete-pair-recipe-probe',
        'status':'DERIVATIVES_PASS' if passed else 'DERIVATIVE_REVIEW',
        'recipe_sha256':expected_digest,'recipe_file_sha256':sha256(recipe_data).hexdigest(),
        'model_sha256':sha256(model_data).hexdigest(),'native_sources':sources,
        'script_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'python':sys.version,'binding':report,'target':initial['target'],'components':initial['components'],
        'finite_differences':checks,'negative_controls_rejected':rejected,
        'unreferenced_gradients_zero':True,'mutable_input_detached':True,'input_bytes_unchanged':True,
        'execution':'COMPLETE_ENERGY_AND_DERIVATIVE_PROBE','optimization':False,'refinement':False,
        'native_callback_attached':False,'scientific_acceptance':False,
        'limitations':['Recipe arithmetic only; no complete native objective, movement mask or lifecycle qualification',
                       'No native exclusions, covalent closure, packing or diffraction acceptance']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--recipe',type=Path,required=True)
    parser.add_argument('--recipe-sha256',required=True)
    parser.add_argument('--cedar-source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--max-coordinate-tests',type=int,default=1200)
    args = parser.parse_args(argv)
    if args.out.exists():parser.error('Output already exists')
    try:
        report = probe(args.model,args.recipe,args.recipe_sha256,args.cedar_source,max_coordinates=args.max_coordinate_tests)
        with args.out.open('x') as stream:
            json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
        print(json.dumps({k:report[k] for k in ('status','target','finite_differences','negative_controls_rejected')}))
        return 0 if report['status']=='DERIVATIVES_PASS' else 2
    except (ImportError,OSError,ValueError,RuntimeError,KeyError,TypeError,IndexError) as exc:
        parser.exit(1,f'{parser.prog}: {exc}\n')


if __name__ == '__main__':sys.exit(main())
