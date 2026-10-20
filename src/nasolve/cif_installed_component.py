"""Capture a selected installation's exact monomer lookup, without generation."""
from hashlib import sha256
import ast
import json
import math
import os
from pathlib import Path
import re
import subprocess

from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import _inside,MAX_SOURCE_BYTES
from .cif_generation import _terminate_owned_group

POLICY_ID='cif-installed-component-resource-v1'
SOURCE_PATHS=('mmtbx/monomer_library/server.py','mmtbx/monomer_library/cif_types.py')

WORKER=r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,json,sys,traceback
spec=json.loads(Path(sys.argv[1]).read_text());directory=Path.cwd().resolve()
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory]
sys.path.insert(0,spec['library'])
def digest(path):return sha256(Path(path).read_bytes()).hexdigest()
modules={}
for row in spec['sources']:
    path=Path(row['installed']).resolve(strict=True);name=row['module']
    found=importlib.util.find_spec(name)
    if digest(path)!=row['sha256'] or found is None or Path(found.origin).resolve(strict=True)!=path:
        raise ValueError('Unselected or changed installed monomer API')
    module=importlib.import_module(name)
    if Path(module.__file__).resolve(strict=True)!=path:raise ValueError('Unselected monomer import')
    modules[name]=module
result={'schema_version':1,'policy_id':spec['policy_id'],'status':'FAILED','component':spec['component'],
        'dictionary_generation':'NOT_RUN','optimization':'NOT_RUN','readyset':'NOT_RUN','automatic_adoption':False}
class Unsupported(RuntimeError):pass
def row(obj):
    if not callable(getattr(obj,'cif_keywords',None)):raise Unsupported('No native CIF row interface')
    return {key:getattr(obj,key) for key in obj.cif_keywords()}
try:
    library=modules['mmtbx.monomer_library.server'].server()
    method=getattr(library,'get_comp_comp_id_and_atom_name_interpretation',None)
    if not callable(method):raise Unsupported('Missing native residue-name resolver')
    base,interpretation=method(residue_name=spec['component'],atom_names=[])
    if base is None:raise Unsupported('Missing requested installed component')
    metadata=row(base.chem_comp)
    result['resolution']={'method':'get_comp_comp_id_and_atom_name_interpretation','input_atom_names':[],
        'resolved_component_id':metadata.get('id'),'interpreted_residue_name':getattr(interpretation,'residue_name',None)}
    if metadata.get('id')!=spec['component']:raise Unsupported('Native lookup substituted a different component')
    result['metadata']=metadata;result['categories']={}
    for kind,field in {'atoms':'atom_list','bonds':'bond_list','angles':'angle_list','torsions':'tor_list',
                       'chirality':'chir_list','plane_atoms':'plane_atom_list'}.items():
        if not hasattr(base,field):raise Unsupported('Missing native category: '+field)
        result['categories'][kind]=[row(v) for v in getattr(base,field)]
    info=getattr(base,'source_info',None);result['source_provenance']=info
    if not isinstance(info,str) or not info.startswith('file: '):raise Unsupported('Lookup has no exact file source')
    path=Path(info[6:]).resolve(strict=True);root=Path(spec['installation']).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():raise Unsupported('Lookup source is outside the selected installation')
    payload=path.read_bytes()
    if len(payload)>spec['max_bytes']:raise Unsupported('Oversized installed component resource')
    with Path('installed_component.cif').open('xb') as handle:handle.write(payload)
    result['resource']={'anchor':'phenix_installation','path':path.relative_to(root).as_posix(),
        'sha256':sha256(payload).hexdigest(),'size':len(payload),
        'snapshot':{'anchor':'component_directory','path':'installed_component.cif'}}
    if path.read_bytes()!=payload:raise ValueError('Installed component changed during capture')
    result['status']='RECORDED'
except Unsupported as exc:result.update(status='UNSUPPORTED',error=str(exc))
except Exception as exc:result.update(status='FAILED',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
for row in spec['sources']:
    if digest(row['installed'])!=row['sha256']:raise ValueError('Installed monomer API changed')
Path('component_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def verify_component_capture(root,report,output):
    root=Path(root).resolve(strict=True);output=Path(output).resolve(strict=True)
    rows=list(report['sources']);resource=report.get('result',{}).get('resource')
    if len(rows)!=2 or {r['snapshot']['path'] for r in rows}!={p+'.txt' for p in SOURCE_PATHS}:
        raise ValueError('Unexpected installed-component API capture')
    if resource:rows.append(resource)
    for row in rows:
        if row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='component_directory':
            raise ValueError('Unsupported installed-component anchor')
        for path in [_inside(root,row['path']),_inside(output,row['snapshot']['path'])]:
            data=path.read_bytes()
            if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:
                raise ValueError('Installed component or captured source changed')
    return True


def capture_installed_component(root,executable,api_sources,code,output,*,environment,timeout_seconds=30):
    """Capture lookup rows and exact source bytes from selected Phenix only."""
    if not re.fullmatch(r'[A-Z0-9]{1,3}',code):raise ValueError('Require an explicit representable component code')
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=60:
        raise ValueError('Require a component-resource timeout in (0,60]')
    root=Path(root).resolve(strict=True);executable=Path(executable).resolve(strict=True);output=Path(output).absolute()
    if (not executable.is_relative_to(root) or output.resolve().is_relative_to(root) or output.exists()
            or output.is_symlink() or any(p.is_symlink() for p in output.parents)):
        raise ValueError('Require selected Phenix Python and a fresh separate resource directory')
    dispatcher=executable.read_bytes();site=_library_anchor(api_sources);rows=[];payloads={}
    for name in SOURCE_PATHS:
        relative=(site/name).as_posix();data=_inside(root,relative).read_bytes()
        if len(data)>MAX_SOURCE_BYTES:raise ValueError('Oversized installed monomer API')
        ast.parse(data,filename=name);payloads[name]=data
        prior=[r for r in api_sources if r.get('path')==relative]
        if prior and (len(prior)!=1 or prior[0]['sha256']!=sha256(data).hexdigest()):raise ValueError('Previously captured monomer API changed')
        rows.append({'anchor':'phenix_installation','path':relative,'sha256':sha256(data).hexdigest(),'size':len(data),
            'snapshot':{'anchor':'component_directory','path':name+'.txt'}})
    output.mkdir(parents=True,exist_ok=False)
    for name,data in payloads.items():
        p=output/(name+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    spec={'policy_id':POLICY_ID,'component':code,'installation':str(root),'library':str(root/site),'max_bytes':MAX_SOURCE_BYTES,
        'sources':[{'installed':str(root/r['path']),'sha256':r['sha256'],'module':name[:-3].replace('/','.')}
                   for name,r in zip(SOURCE_PATHS,rows)]}
    (output/'component_spec.json').write_text(json.dumps(spec,indent=2)+'\n');(output/'component_worker.py').write_text(WORKER)
    report={'policy_id':POLICY_ID,'sources':rows,'dispatcher_sha256':sha256(dispatcher).hexdigest(),'result':{}}
    verify_component_capture(root,report,output)
    with (output/'component.log').open('xb') as log:
        process=subprocess.Popen([str(executable),'component_worker.py','component_spec.json'],cwd=output,env=dict(environment),
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
        try:rc=process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_owned_group(process);raise ValueError('Installed component capture timed out')
        except BaseException:
            _terminate_owned_group(process);raise
    if rc!=0:raise ValueError('Installed component worker failed; inspect component.log')
    p=output/'component_result.json'
    if p.is_symlink() or not p.is_file():raise ValueError('Missing exact installed component result')
    report['result']=json.loads(p.read_text())
    if (report['result'].get('policy_id')!=POLICY_ID or report['result'].get('component')!=code
            or report['result'].get('status') not in {'RECORDED','UNSUPPORTED','FAILED'}):raise ValueError('Invalid installed component result')
    if report['result']['status']=='RECORDED' and (report['result'].get('resolution',{}).get('resolved_component_id')!=code
            or not report['result'].get('resource')):raise ValueError('Incomplete installed component provenance')
    if executable.read_bytes()!=dispatcher:raise ValueError('Selected dispatcher changed')
    verify_component_capture(root,report,output)
    report['installed_sources_preserved']=True
    (output/'component_receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
