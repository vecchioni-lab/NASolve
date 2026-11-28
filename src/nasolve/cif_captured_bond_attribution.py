"""Durable target-only bond attribution through the existing repair lifecycle.

Source/reference and full native delivery are replayed before any job. The caller
owns process recovery; this adapter neither selects a bundle nor grants reference
authority. Saved native workers are authenticated as data, never executed on read.
"""
import inspect
from types import SimpleNamespace

from .cif_captured_attribution import audit, read, inventory, kernel_references, native_auxiliary
from .cif_captured_mixed_gradients import _inputs, _native_context_worker
from .cif_component_runtime import _tree
from .cif_dictionary_store import _bytes, _json
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact, _need
from .cif_linear_bond_native import qualify_captured_linear_bond_candidate
from .cif_linear_bond_energy import changed_bond_pairs, native_bond_evaluator, qualify_linked_linear_bond_energy
from .cif_mixed_geometry import _ref

POLICY_ID = 'cif-captured-linear-bond-target-attribution-v1'
REPORT = 'captured_bond_attribution.json'
ANCHOR = 'captured_bond_attribution_directory'
MODULES = ('cctbx.geometry_restraints.flags','cctbx.geometry_restraints.energies',
           'cctbx.geometry_restraints.manager','cctbx.geometry_restraints',
           'cctbx.array_family.flex','cctbx_geometry_restraints_ext')
_FIXED = dict(schema_version=1,policy_id=POLICY_ID,maximum_native_calls=1,
    coordinate_selection='UNCHANGED_CAPTURE_INPUT',reference_authority='NOT_QUALIFIED',
    source_chemical_qualification='CALLER_REQUIRED',derivative_qualification='NOT_RUN',
    achieved_geometry='NOT_ASSESSED',model_optimization='NOT_RUN',refinement='NOT_RUN',
    captured_code_execution='NOT_RUN',automatic_adoption=False)

_WORKER = r'''from pathlib import Path
from hashlib import sha256
import importlib,json,os,sys
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
from evaluator import native_bond_evaluator
modules=('cctbx.geometry_restraints.flags','cctbx.geometry_restraints.energies',
 'cctbx.geometry_restraints.manager','cctbx.geometry_restraints',
 'cctbx.array_family.flex','cctbx_geometry_restraints_ext')
def pins():
 result=[]
 for name in modules:
  path=Path(importlib.import_module(name).__file__).resolve(strict=True)
  result.append(dict(module=name,historical_path=str(path),sha256=sha256(path.read_bytes()).hexdigest()))
 return result
home=Path.cwd();raw=Path('spec.json').read_bytes();spec=json.loads(raw);before=pins()
assert before[:3]==spec['installed_sources']
evaluate=native_bond_evaluator(gr,flex);sides={}
for label in ('before','after'):
 os.chdir(home/label)
 namespace={'__name__':'__main__','__file__':'native_worker.py'};sys.argv=['native_worker.py','native_spec.json']
 try:exec(compile(Path('native_worker.py').read_text(),'native_worker.py','exec'),namespace)
 except SystemExit as exc:
  if exc.code!=0:raise RuntimeError('Native manager rebuild failed')
 ref=spec[label]['inventory_ref']
 assert set(ref)=={'anchor','path','sha256','size'}
 assert ref['anchor']=='captured_bond_attribution_directory' and ref['path']=='inputs/'+label+'/native_validation.json'
 expected_raw=(home.parent/ref['path']).read_bytes()
 assert len(expected_raw)==ref['size'] and sha256(expected_raw).hexdigest()==ref['sha256']
 actual=namespace['report'];assert actual==json.loads(expected_raw)
 geo=namespace['geo'];assert list(geo.site_symmetry_table.special_position_indices())==[]
 sites=namespace['sites'];proxies=namespace['bonds'].simple;references=[]
 for row in spec[label]['bonds']:
  matches=[p for p in proxies if list(p.i_seqs)==row['i_seqs']]
  assert len(matches)==1;p=matches[0]
  assert p.distance_ideal==row['distance_ideal'] and p.weight==row['weight'] and p.origin_id==row['origin_id']==0 and p.rt_mx_ji is None
  references.append(dict(proxy=row,sites_cart=[list(sites[i]) for i in p.i_seqs],
   native_parameters=dict(slack=float(p.slack),limit=float(p.limit),top_out=bool(p.top_out)),
   evaluations=[evaluate(sites,p) for _ in range(2)]))
 sides[label]=dict(exact_native_inventory=True,special_position_indices=[],references=references)
 os.chdir(home)
after=pins();assert before==after
result=dict(spec_sha256=sha256(raw).hexdigest(),evaluator_sha256=sha256(Path('evaluator.py').read_bytes()).hexdigest(),
 installed_sources=before,installed_sources_after=after,sides=sides)
Path('result.json').write_text(json.dumps(result,sort_keys=True,allow_nan=False)+'\n')
'''


def _derive(root,controls):
    _need(isinstance(controls,dict) and set(controls)=={'component','dictionary_index','bonds'},
          'Unsupported bond attribution controls')
    _need({p.name for p in (root/'inputs').iterdir()}=={'source.cif','reference.json','before','after'},
          'Unexpected frozen bond attribution inputs')
    source=root/'inputs/source.cif';reference=_json((root/'inputs/reference.json').read_bytes())
    before,after=entries=[_inputs(root/'inputs'/label) for label in ('before','after')]
    index=controls['dictionary_index'];component=controls['component']
    _need(type(index) is int and 0<=index<len(before[2]) and len(after[2])==len(before[2]),'Invalid candidate dictionary slot')
    candidate=after[2][index]
    proof=qualify_captured_linear_bond_candidate(source,component,reference,candidate,
        root/'inputs/before/native_receipt.json',root/'inputs/after/native_receipt.json',
        dictionary_index=index,bonds=controls['bonds'])
    pairs=changed_bond_pairs(before[4],after[4]);pins=before[4]['energy_inventory']['installed_sources']
    _need(_exact(pins,after[4]['energy_inventory']['installed_sources']),'Native energy sources differ')
    prepared={'job/worker.py':_WORKER.encode(),'job/evaluator.py':inspect.getsource(native_bond_evaluator).encode()}
    spec=dict(installed_sources=pins)
    from .cif_candidate_usability import native_energy_worker
    from .cif_native_validation import _NATIVE_WORKER
    for ordinal,(label,entry) in enumerate(zip(('before','after'),entries)):
        capture=entry[0];parent=root/'inputs'/label
        _need(set(_tree(parent))=={'native_receipt.json'}|{r['path'] for r in capture['outputs']},
              'Capture directory contains unrelated files')
        prepared[f'job/{label}/native_worker.py']=_native_context_worker(native_energy_worker(_NATIVE_WORKER),capture).encode()
        prepared[f'job/{label}/native_spec.json']=(parent/'native_spec.json').read_bytes()
        for row in capture['inputs']:prepared[f"job/{label}/{row['path']}"]=(parent/row['path']).read_bytes()
        spec[label]=dict(inventory_ref=_ref(parent/'native_validation.json',root,ANCHOR),bonds=[p[ordinal] for p in pairs])
    prepared['job/spec.json']=_bytes(spec)
    arguments=(before[4],after[4],source,before[2][index],component,reference,candidate,controls['bonds'])
    return prepared,before[0],proof,arguments


def _qualification(root,prepared,arguments):
    references=kernel_references(root,prepared,*arguments[:2],MODULES)
    return qualify_linked_linear_bond_energy(*arguments[:-1],references,bonds=arguments[-1])


def _contract():
    return SimpleNamespace(fixed=_FIXED,report=REPORT,anchor=ANCHOR,derive=_derive,
        qualify=_qualification,auxiliary=native_auxiliary,pass_status='CAPTURED_BOND_TARGET_ATTRIBUTION_PASS')


def _inventory(root):
    return inventory(root,_contract())


def audit_captured_bond_attribution(source,component,reference_file,before_receipt,after_receipt,
        dictionary_index,phenix,output,*,bonds,timeout_seconds=120,_process_runner=None):
    """Prepare only or run one owned native job, retaining failures and exact inputs."""
    _need(type(timeout_seconds) is int and 1<=timeout_seconds<=600,'Invalid attribution timeout')
    receipts=[_path(p) for p in (before_receipt,after_receipt)]
    _need(all(p.name=='native_receipt.json' for p in receipts),'Require exact native receipts')
    controls=dict(component=component,dictionary_index=dictionary_index,bonds=bonds)
    roots=dict(zip(('before','after'),(p.parent for p in receipts)))
    return audit(source,roots,controls,phenix,output,timeout_seconds=timeout_seconds,
        process_runner=_process_runner,contract=_contract(),extra_inputs={'reference.json':reference_file})


def read_captured_bond_attribution(directory):
    """Rebuild all source/capture/kernel claims without SDK access or execution."""
    return read(directory,_contract())
