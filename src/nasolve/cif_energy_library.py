"""Freeze the numerical library opened by a selected native consumer.

The existing process owner runs one read-only lookup. This is reusable reference
provenance, not chemical approval, parameter calibration or repair selection.
Readers never import captured code or reopen historical installation paths.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import time

from .cif_component_runtime import _tree
from .cif_dictionary_sites import _consumer, _safe, _need
from .cif_dictionary_store import _bytes, _json
from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import MAX_SOURCE_BYTES
from .cif_fana_junction import _path
from .cif_linked_linear_torsion import _exact
from .cif_linear_bond_reference import energy_library_linear_reference, _library_table
from .cif_mixed_geometry import _ref
from .cif_native_validation import _run_native_command
from .cif_phenix_configuration import _pin
from .cif_postmr_cache import verify_current_consumer
from .ligand_profiles import _blocks

POLICY_ID = 'cif-selected-native-energy-library-v1'
REPORT = 'energy_library_receipt.json'
ANCHOR = 'energy_library_directory'
LOOKUP = 'mmtbx.monomer_library.server.find_mon_lib_file:ener_lib.cif'
_MODULES = {'mmtbx.monomer_library.server':'mmtbx/monomer_library/server.py',
            'iotbx.cif':'iotbx/cif/__init__.py'}
_FIXED = dict(schema_version=1,policy_id=POLICY_ID,chemical_approval='NOT_ASSESSED',
    parameter_calibration='NOT_RUN',automatic_adoption=False,model_editing='NOT_RUN',
    refinement='NOT_RUN',captured_code_execution='NOT_RUN')

_WORKER = r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,json,sys
home=Path.cwd().resolve();raw=Path('spec.json').read_bytes();spec=json.loads(raw)
root=Path(sys.argv[1]).resolve(strict=True)
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=home]
sys.path.insert(0,str(root/spec['site']))
def pins():
 rows=[]
 for wanted in spec['modules']:
  path=root/wanted['path'];resolved=path.resolve(strict=True)
  assert resolved.is_relative_to(root) and path.is_file() and not path.is_symlink()
  assert path.stat().st_size<=spec['maximum_resource_bytes']
  data=path.read_bytes();row=dict(wanted,sha256=sha256(data).hexdigest(),size=len(data))
  assert row==wanted
  found=importlib.util.find_spec(wanted['module']);assert found is not None and Path(found.origin).resolve(strict=True)==resolved
  module=importlib.import_module(wanted['module']);assert Path(module.__file__).resolve(strict=True)==resolved
  rows.append(row)
 return rows
before=pins()
server=importlib.import_module('mmtbx.monomer_library.server')
found=server.find_mon_lib_file(relative_path_components=['ener_lib.cif'])
if found is None:raise ValueError('Native numerical library is unavailable')
path=Path(found).resolve(strict=True)
if not path.is_relative_to(root):raise ValueError('Unselected numerical library')
if not path.is_file() or path.stat().st_size>spec['maximum_resource_bytes']:raise ValueError('Oversized or nonregular numerical library')
data=path.read_bytes();assert len(data)<=spec['maximum_resource_bytes']
loaded=server.mon_lib_ener_lib_cif(path=str(path))
assert Path(loaded.path).resolve(strict=True)==path
def table(category):
 stem='_lib_'+category+'.';rows=[]
 for block in loaded.cif.values():
  columns={str(k).lower()[len(stem):]:[v] if isinstance(v,str) else list(v) for k,v in block.items() if str(k).lower().startswith(stem)}
  if columns:
   assert len({len(v) for v in columns.values()})==1
   rows.extend({k:str(v[i]) for k,v in columns.items()} for i in range(len(next(iter(columns.values())))))
 return sorted(rows,key=lambda row:json.dumps(row,sort_keys=True))
tables={name:table(name) for name in ('atom','bond')}
fingerprint=sha256(json.dumps(tables,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
assert path.read_bytes()==data
assert Path(server.find_mon_lib_file(relative_path_components=['ener_lib.cif'])).resolve(strict=True)==path
after=pins();assert before==after
Path('energy-library.cif').write_bytes(data)
result=dict(spec_sha256=sha256(raw).hexdigest(),modules=before,modules_after=after,
 lookup=spec['lookup'],resource=dict(anchor='phenix_installation',path=path.relative_to(root).as_posix(),sha256=sha256(data).hexdigest(),size=len(data)),parsed_tables_sha256=fingerprint)
Path('native-result.json').write_text(json.dumps(result,sort_keys=True,allow_nan=False)+'\n')
'''


def _tables_digest(path):
    blocks=_blocks(path)
    tables={name:sorted(_library_table(blocks,name,fields),key=lambda r:json.dumps(r,sort_keys=True))
            for name,fields in [('atom',['type','element','valency','sp']),
                ('bond',['atom_type_1','atom_type_2','type','length','value_esd','const'])]}
    return sha256(json.dumps(tables,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def _valid_pin(row):
    return (isinstance(row,dict) and set(row)=={'anchor','path','sha256','size'}
        and row['anchor']=='phenix_installation' and _safe(row['path'])
        and isinstance(row['sha256'],str) and len(row['sha256'])==64
        and all(c in '0123456789abcdef' for c in row['sha256'])
        and type(row['size']) is int and 0<row['size']<=MAX_SOURCE_BYTES)


def _validate_spec(spec):
    _need(isinstance(spec,dict) and set(spec)=={'policy_id','consumer','site','modules','lookup','maximum_resource_bytes'},'Incomplete energy-library specification')
    _need(spec['policy_id']==POLICY_ID and spec['lookup']==LOOKUP
          and type(spec['maximum_resource_bytes']) is int and spec['maximum_resource_bytes']==MAX_SOURCE_BYTES,'Unsupported energy-library lookup')
    consumer=spec['consumer'];_consumer(consumer)
    _need(set(consumer)=={'name','version','executable_sha256','api_sources','energy_sources'},'Unexpected energy-library consumer fields')
    site=_library_anchor(consumer['api_sources']).as_posix()
    _need(_safe(spec['site']) and spec['site']==site,'Energy-library implementation scope differs')
    rows=spec['modules']
    _need(isinstance(rows,list) and len(rows)==len(_MODULES),'Incomplete native library-reader modules')
    for row,(module,suffix) in zip(rows,_MODULES.items()):
        _need(isinstance(row,dict) and row.get('module')==module
              and _valid_pin({k:v for k,v in row.items() if k!='module'})
              and row['path']==site+'/'+suffix,'Invalid native library-reader pin')
    server=next(r for r in consumer['api_sources'] if r['path'].endswith('/mmtbx/monomer_library/server.py'))
    _need(all(rows[0][k]==server[k] for k in ('anchor','path','sha256')),'Library resolver differs from selected consumer')


def _inventory(root):
    return [_ref(root/name,root,ANCHOR) for name in _tree(root) if name!=REPORT]


def _qualification(root,spec):
    result=_json((root/'native-result.json').read_bytes())
    _need(isinstance(result,dict) and set(result)=={'spec_sha256','modules','modules_after','lookup','resource','parsed_tables_sha256'},'Incomplete native library result')
    _need(result['spec_sha256']==sha256((root/'spec.json').read_bytes()).hexdigest()
          and _exact(result['modules'],spec['modules']) and _exact(result['modules_after'],spec['modules'])
          and result['lookup']==LOOKUP and _valid_pin(result['resource']),'Unbound native energy-library lookup')
    data=(root/'energy-library.cif').read_bytes();resource=result['resource']
    _need(len(data)==resource['size'] and sha256(data).hexdigest()==resource['sha256']
          and _tables_digest(root/'energy-library.cif')==result['parsed_tables_sha256'],
          'Native parsed library differs from frozen numerical tables')
    return dict(status='SELECTED_NATIVE_ENERGY_LIBRARY_CAPTURED',resource=resource,
        snapshot=_ref(root/'energy-library.cif',root,ANCHOR),parsed_tables_sha256=result['parsed_tables_sha256'])


def capture_energy_library(phenix,consumer,output,*,timeout_seconds=60,_process_runner=None):
    """Capture one actual selected SDK lookup through the caller's existing owner.

    The installation is a live argument, not a saved operational path. A failed
    lookup stays REVIEW; uncertain cleanup escapes without sealing a receipt.
    No ligand or coordinates are needed, so the result can serve many references.
    """
    _need(type(timeout_seconds) is int and 1<=timeout_seconds<=120,'Invalid energy-library timeout')
    selected=deepcopy(phenix);consumer=deepcopy(consumer);_consumer(consumer)
    root=Path(selected.root).resolve(strict=True);site=_library_anchor(consumer['api_sources'])
    verify_current_consumer(selected,selected.executables['phenix.ready_set'],consumer)
    modules=[dict(_pin(root/site/name,root,source=True),module=module) for module,name in _MODULES.items()]
    spec=dict(policy_id=POLICY_ID,consumer=consumer,site=site.as_posix(),modules=modules,
              lookup=LOOKUP,maximum_resource_bytes=MAX_SOURCE_BYTES);_validate_spec(spec)
    output=Path(output).expanduser().absolute()
    _need(not output.exists() and not any(p.is_symlink() for p in (output,*output.parents))
          and not output.is_relative_to(root) and not root.is_relative_to(output),'Require fresh separate library evidence')
    output.mkdir(parents=True,exist_ok=False)
    (output/'spec.json').write_bytes(_bytes(spec));(output/'worker.py').write_text(_WORKER)
    report=dict(_FIXED,timeout_seconds=timeout_seconds,new_native_calls=0)
    started=time.monotonic()
    try:
        code=_run_native_command([str(selected.executables['phenix.python']),'-B','worker.py',str(root)],
            cwd=output,log_path=output/'native.log',environment=dict(selected.environment,PYTHONDONTWRITEBYTECODE='1'),
            timeout_seconds=timeout_seconds,process_runner=_process_runner,on_started=lambda:report.update(new_native_calls=1))
    except subprocess.TimeoutExpired as exc:
        execution=dict(status='TIMED_OUT',returncode=exc.returncode)
    else:execution=dict(status='COMPLETED' if code==0 else 'FAILED',returncode=code)
    execution['elapsed_seconds']=time.monotonic()-started;report['execution']=execution
    verify_current_consumer(selected,selected.executables['phenix.ready_set'],consumer)
    _need(phenix==selected and all(dict(_pin(root/r['path'],root,source=True),module=r['module'])==r for r in modules),
          'Selected energy-library implementation changed during capture')
    _need((output/'spec.json').read_bytes()==_bytes(spec) and (output/'worker.py').read_text()==_WORKER,'Prepared library job changed')
    q=_qualification(output,spec) if execution['status']=='COMPLETED' else {'status':'NOT_RUN'}
    if execution['status']=='COMPLETED':
        resource=q['resource'];_need(_pin(root/resource['path'],root,source=True)==resource,'Installed numerical library changed during capture')
    report.update(qualification=q,status=q['status'] if execution['status']=='COMPLETED' else 'REVIEW',outputs=_inventory(output))
    with (output/REPORT).open('xb') as stream:stream.write(_bytes(report))
    return read_energy_library(output)


def read_energy_library(directory):
    """Validate frozen lookup and numerical tables without an SDK or execution."""
    try:
        root=_path(directory,directory=True);files=_tree(root)
        report=_json(files[REPORT]);spec=_json(files['spec.json']);_validate_spec(spec)
        _need(set(report)==set(_FIXED)|{'timeout_seconds','new_native_calls','execution','qualification','status','outputs'}
              and all(_exact(report.get(k),v) for k,v in _FIXED.items()),'Unsupported energy-library receipt')
        _need((root/'worker.py').read_text()==_WORKER and (root/'spec.json').read_bytes()==_bytes(spec),'Unmaintained saved library job')
        _need(_exact(report['outputs'],_inventory(root)) and not any(p.is_dir() for p in root.iterdir())
              and {r['path'] for r in report['outputs']}<={'spec.json','worker.py','native.log','native-result.json','energy-library.cif'},'Unexpected library evidence')
        execution=report['execution'];state=execution['status']
        _need(type(report['new_native_calls']) is int and report['new_native_calls']==1
              and type(report['timeout_seconds']) is int and 1<=report['timeout_seconds']<=120
              and set(execution)=={'status','returncode','elapsed_seconds'}
              and state in {'COMPLETED','FAILED','TIMED_OUT'} and type(execution['returncode']) is int
              and (state!='COMPLETED' or execution['returncode']==0) and (state!='FAILED' or execution['returncode']!=0)
              and type(execution['elapsed_seconds']) in (int,float) and math.isfinite(execution['elapsed_seconds'])
              and execution['elapsed_seconds']>=0 and (root/'native.log').is_file(),'Invalid library execution evidence')
        q=_qualification(root,spec) if state=='COMPLETED' else {'status':'NOT_RUN'}
        _need(_exact(report['qualification'],q) and report['status']==(q['status'] if state=='COMPLETED' else 'REVIEW'),'Energy-library qualification differs')
        _need(files==_tree(root),'Library evidence changed during readback')
        return report
    except (KeyError,TypeError,IndexError,OverflowError) as exc:raise ValueError('Incomplete energy-library evidence') from exc


def qualify_energy_reference(source,dictionary,component,reference,directory,*,consumer):
    """Bind complete source-selected reference rows to the exact observed library.

    This establishes numerical provenance only. It does not approve the source
    chemistry, existing ESDs, a candidate dictionary or any refinement result.
    """
    root=_path(directory,directory=True);source=_path(source);dictionary=_path(dictionary)
    frozen=(source.read_bytes(),dictionary.read_bytes(),(root/REPORT).read_bytes())
    report=read_energy_library(root)
    spec=_json((root/'spec.json').read_bytes());_consumer(consumer)
    _need(report['status']=='SELECTED_NATIVE_ENERGY_LIBRARY_CAPTURED' and _exact(consumer,spec['consumer']),
          'Reference library belongs to another or unqualified consumer')
    actual=energy_library_linear_reference(source,dictionary,component,root/'energy-library.cif')
    _need(_exact(actual,reference),'Supplied reference does not reproduce from the selected native library')
    _need(frozen==(source.read_bytes(),dictionary.read_bytes(),(root/REPORT).read_bytes()),'Reference inputs changed during qualification')
    return dict(policy_id='cif-selected-library-linear-reference-v1',component=component,
        source_sha256=actual['query']['source_sha256'],dictionary_sha256=sha256(frozen[1]).hexdigest(),
        reference_sha256=sha256(json.dumps(actual,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        evidence=_ref(root/REPORT,root,ANCHOR),resource=report['qualification']['resource'],
        reference_authority='EXACT_ROWS_FROM_SELECTED_NATIVE_LIBRARY',
        supported_bonds=[r['atoms'] for r in actual['bonds'] if r['status']=='SUPPORTED'],
        unsupported_bonds=[r['atoms'] for r in actual['bonds'] if r['status']=='UNSUPPORTED'],
        source_chemical_qualification='CALLER_REQUIRED',
        parameter_calibration='NOT_RUN',chemical_approval='NOT_ASSESSED',automatic_adoption=False)


def qualify_bond_attribution_reference(attribution_directory,library_directory,*,consumer):
    """Join a durable target attribution and library provenance without selection."""
    from .cif_captured_bond_attribution import read_captured_bond_attribution, REPORT as BOND_REPORT, ANCHOR as BOND_ANCHOR
    from .cif_captured_mixed_gradients import _inputs
    from .cif_postmr_cached_model import _consumer_matches
    root=_path(attribution_directory,directory=True);_consumer(consumer)
    job=read_captured_bond_attribution(root);control=job['controls']
    entries=[_inputs(root/'inputs'/side) for side in ('before','after')]
    _need(all(_consumer_matches(e[0],consumer,None) for e in entries),
          'Bond attribution and reference library require the same complete native consumer')
    reference=_json((root/'inputs/reference.json').read_bytes())
    qualification=qualify_energy_reference(root/'inputs/source.cif',entries[0][2][control['dictionary_index']],
        control['component'],reference,library_directory,consumer=consumer)
    return dict(policy_id='cif-library-bound-bond-attribution-v1',dictionary_index=control['dictionary_index'],
        status='LIBRARY_BOUND_BOND_ATTRIBUTION_PASS' if job['status']=='CAPTURED_BOND_TARGET_ATTRIBUTION_PASS' else 'REVIEW',
        attribution=_ref(root/BOND_REPORT,root,BOND_ANCHOR),reference=qualification,
        source_chemical_qualification='CALLER_REQUIRED',derivative_qualification='NOT_RUN',
        achieved_geometry='NOT_ASSESSED',automatic_adoption=False)
