"""Maintained whole-plane attribution over owned source/capture evidence.

One bounded native job rebuilds both fixed managers and evaluates complete groups.
The existing caller owns process identity/recovery; this reader runs no saved code.
Chemical approval, derivatives, geometry and runtime adoption remain separate.
"""
from hashlib import sha256
import inspect
from pathlib import Path

from .cif_attachment_native import _json
from .cif_captured_attribution import native_auxiliary as _native_auxiliary
from .cif_captured_mixed_gradients import _inputs, _native_context_worker
from .cif_component_runtime import _tree
from .cif_dictionary_store import _bytes
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact
from .cif_mixed_geometry import _ref
from .cif_plane_generation import read_owned_plane_support
from .cif_plane_native import qualify_owned_plane_captures
from .cif_plane_energy import changed_plane_pairs, native_plane_evaluator, qualify_linked_plane_energy

POLICY_ID = 'cif-captured-owned-plane-attribution-v1'
REPORT = 'captured_plane_attribution.json'
ANCHOR = 'captured_plane_attribution_directory'
MODULES = ('cctbx.geometry_restraints.flags', 'cctbx.geometry_restraints.energies',
           'cctbx.geometry_restraints.manager', 'cctbx.geometry_restraints',
           'cctbx.array_family.flex', 'cctbx_geometry_restraints_ext')
_FIXED = dict(schema_version=1, policy_id=POLICY_ID, maximum_native_calls=1,
    maximum_changed_planes=128, coordinate_selection='UNCHANGED_CAPTURE_INPUT',
    source_chemical_qualification='NOT_ASSESSED', derivative_qualification='NOT_RUN',
    achieved_geometry='NOT_ASSESSED', model_optimization='NOT_RUN', refinement='NOT_RUN',
    captured_code_execution='NOT_RUN', automatic_adoption=False)

_WORKER = r'''from pathlib import Path
from hashlib import sha256
import importlib,json,os,sys
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
from evaluator import native_plane_evaluator
modules=('cctbx.geometry_restraints.flags','cctbx.geometry_restraints.energies',
 'cctbx.geometry_restraints.manager','cctbx.geometry_restraints',
 'cctbx.array_family.flex','cctbx_geometry_restraints_ext')
def pins():
 result=[]
 for name in modules:
  p=Path(importlib.import_module(name).__file__).resolve(strict=True)
  result.append(dict(module=name,historical_path=str(p),sha256=sha256(p.read_bytes()).hexdigest()))
 return result
home=Path.cwd();raw=Path('spec.json').read_bytes();spec=json.loads(raw);before=pins()
assert before[:3]==spec['installed_sources']
evaluate=native_plane_evaluator(gr,flex);sides={}
for label in ('before','after'):
 os.chdir(home/label)
 namespace={'__name__':'__main__','__file__':'native_worker.py'};sys.argv=['native_worker.py','native_spec.json']
 try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
 except SystemExit as exc:
  if exc.code!=0:raise RuntimeError('Native manager rebuild failed')
 actual=namespace['report'];expected=spec[label]['inventory']
 assert json.dumps(actual,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)
 geo=namespace['geo'];assert list(geo.site_symmetry_table.special_position_indices())==[]
 points=actual['geometry']['sites_cart_exact'];references=[]
 assert 0<len(spec[label]['planes'])<=128
 for row in spec[label]['planes']:
  matches=[p for p in geo.planarity_proxies if set(p.i_seqs)==set(row['i_seqs'])]
  assert len(matches)==1;p=matches[0]
  observed=sorted(zip(list(p.i_seqs),list(p.weights)))
  assert [i for i,w in observed]==row['i_seqs'] and [w for i,w in observed]==row['weights'] and int(p.origin_id)==row['origin_id']==0
  ops=None if p.sym_ops is None else [r.as_xyz() for _,r in sorted(zip(list(p.i_seqs),list(p.sym_ops)),key=lambda x:x[0])]
  assert ops is None or (len(ops)==len(row['i_seqs']) and all(v=='x,y,z' for v in ops))
  local=[points[i] for i in row['i_seqs']]
  references.append(dict(proxy=row,sites_cart=local,symmetry_operations=ops,evaluations=[evaluate(local,row) for _ in range(2)]))
 sides[label]=dict(exact_native_inventory=True,special_position_indices=[],references=references)
 os.chdir(home)
after=pins();assert before==after
result=dict(spec_sha256=sha256(raw).hexdigest(),evaluator_sha256=sha256(Path('evaluator.py').read_bytes()).hexdigest(),
 installed_sources=before,installed_sources_after=after,sides=sides)
Path('result.json').write_text(json.dumps(result,sort_keys=True,allow_nan=False)+'\n')
'''


# Preserve the historical worker for old evidence. The compact form changes only
# where the exact expected inventory is read, not the comparison or calculation.
_REFERENCED_WORKER = _WORKER.replace(
    " actual=namespace['report'];expected=spec[label]['inventory']",
    """ ref=spec[label]['inventory_ref']
 assert set(ref)=={'anchor','path','sha256','size'}
 assert ref['anchor']=='captured_plane_attribution_directory' and ref['path']=='inputs/'+label+'/native_validation.json'
 expected_raw=(home.parent/ref['path']).read_bytes()
 assert len(expected_raw)==ref['size'] and sha256(expected_raw).hexdigest()==ref['sha256']
 actual=namespace['report'];expected=json.loads(expected_raw)""")


def _need(value, message='Captured whole-plane evidence does not reproduce'):
    if not value:
        raise ValueError(message)


def _derive(root, controls):
    compact = controls.get('compact_inventory',False)
    _need(type(compact) is bool and set(controls) == {'component', 'attempt_number', 'dictionary_index'}
          | ({'compact_inventory'} if compact else set()))
    source = root/'inputs/source.cif'; request = root/'inputs/generation'
    entries = [_inputs(root/'inputs'/label) for label in ('before', 'after')]
    before, after = entries
    index = controls['dictionary_index']
    _need(type(index) is int and 0 <= index < len(before[2]) and len(after[2]) == len(before[2]))
    proof = qualify_owned_plane_captures(source, controls['component'], request,
        controls['attempt_number'], after[2][index], before[1],
        root/'inputs/before/native_receipt.json', root/'inputs/after/native_receipt.json',
        dictionaries=before[2], dictionary_index=index, phil_files=before[3])
    support = read_owned_plane_support(source, controls['component'], request, controls['attempt_number'])
    pairs = changed_plane_pairs(before[4], after[4])
    pins = before[4]['energy_inventory']['installed_sources']
    _need(_exact(pins, after[4]['energy_inventory']['installed_sources']))
    prepared = {'job/worker.py': (_REFERENCED_WORKER if compact else _WORKER).encode(),
                'job/evaluator.py': inspect.getsource(native_plane_evaluator).encode()}
    spec = {'installed_sources': pins}
    from .cif_candidate_usability import native_energy_worker
    from .cif_native_validation import _NATIVE_WORKER
    for ordinal, (label, entry) in enumerate(zip(('before', 'after'), entries)):
        capture, model, dictionaries, phils, native, _ = entry
        parent = root/'inputs'/label
        _need(set(_tree(parent)) == {'native_receipt.json'} | {r['path'] for r in capture['outputs']},
              'Capture directory has unrelated files')
        native_spec = (parent/'native_spec.json').read_bytes()
        # _inputs validates the supported spec fields and energy capture. Write
        # maintained code afresh; no historical worker is used as executable input.
        worker = _native_context_worker(native_energy_worker(_NATIVE_WORKER),capture)
        prepared[f'job/{label}/native_worker.py'] = worker.encode()
        prepared[f'job/{label}/native_spec.json'] = native_spec
        for row in capture['inputs']:
            prepared[f"job/{label}/{row['path']}"] = (parent/row['path']).read_bytes()
        expected = ({'inventory_ref':_ref(parent/'native_validation.json',root,ANCHOR)}
                    if compact else {'inventory':native})
        spec[label] = {**expected, 'planes': [p[ordinal] for p in pairs]}
    prepared['job/spec.json'] = _bytes(spec)
    arguments = (before[4], after[4], source, before[2][index],
                 request/support['support']['path'], controls['component'], after[2][index],
                 support['recipe'].get('bond_representation_policy'))
    return prepared, before[0], proof, arguments


def _qualification(root, prepared, arguments):
    from .cif_captured_attribution import kernel_references
    references=kernel_references(root,prepared,*arguments[:2],MODULES)
    *inputs, policy = arguments
    return qualify_linked_plane_energy(*inputs,references,bond_representation_policy=policy)


def _contract():
    from types import SimpleNamespace
    return SimpleNamespace(fixed=_FIXED,report=REPORT,anchor=ANCHOR,derive=_derive,
        qualify=_qualification,auxiliary=_native_auxiliary,pass_status='CAPTURED_PLANE_ATTRIBUTION_PASS')


def _inventory(root):
    from .cif_captured_attribution import inventory
    return inventory(root,_contract())


def audit_captured_plane_attribution(source, component, request_directory, attempt_number,
        before_receipt, after_receipt, dictionary_index, phenix, output, *,
        timeout_seconds=120, compact_inventory=False, _process_runner=None):
    """Freeze owned support/captures through the shared bounded attribution lifecycle."""
    from .cif_captured_attribution import audit
    _need(type(timeout_seconds) is int and 1<=timeout_seconds<=600)
    _need(type(compact_inventory) is bool, 'Require a boolean native-inventory storage choice')
    controls=dict(component=component,attempt_number=attempt_number,dictionary_index=dictionary_index,
                  **({'compact_inventory':True} if compact_inventory else {}))
    request=_path(request_directory,directory=True)
    receipts=[_path(p) for p in (before_receipt,after_receipt)]
    _need(all(p.name=='native_receipt.json' for p in receipts))
    roots=dict(generation=request,before=receipts[0].parent,after=receipts[1].parent)
    return audit(source,roots,controls,phenix,output,timeout_seconds=timeout_seconds,
                 process_runner=_process_runner,contract=_contract())


def read_captured_plane_attribution(directory):
    """Recompute the unchanged plane contract offline; never execute saved code."""
    from .cif_captured_attribution import read
    return read(directory,_contract())
