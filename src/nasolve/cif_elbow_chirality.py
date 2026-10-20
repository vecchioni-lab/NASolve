"""Bounded installed-reader chirality controls, without numerical generation."""
from __future__ import annotations

import ast
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

from .cif_elbow_contract import _inside, _safe, MAX_SOURCE_BYTES
from .cif_generation import _terminate_owned_group
from .cif_stereochemistry_audit import reader_stereo_inventory

POLICY_ID='cif-installed-elbow-chirality-control-v1'
SOURCE_PATHS=('elbow/utilities/Utilities.py','elbow/chemistry/MoleculeClass.py',
              'elbow/chemistry/TopologyMixins.py','elbow/chemistry/ChiralClass.py')

WORKER=r'''from hashlib import sha256
import importlib,importlib.util,inspect,json,traceback,sys
from pathlib import Path
spec=json.loads(Path(sys.argv[1]).read_text())
def digest(path):return sha256(Path(path).read_bytes()).hexdigest()
# Captured modules are .txt evidence. Remove the worker directory and select
# the verified installed library ahead of ambient import paths.
directory=Path.cwd().resolve()
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory]
sys.path.insert(0,spec['library'])
modules={}
for row in spec['sources']:
    path=Path(row['installed']).resolve(strict=True)
    if digest(path)!=row['sha256']:raise ValueError('Installed chirality source changed')
    name=row['module'];found=importlib.util.find_spec(name)
    if found is None or found.origin is None or Path(found.origin).resolve(strict=True)!=path:
        raise ValueError('Unselected installed chirality module')
    module=importlib.import_module(name)
    if Path(module.__file__).resolve(strict=True)!=path:raise ValueError('Unselected installed chirality module')
    modules[name]=module
reader=modules['elbow.utilities.Utilities'].get_elbow_molecule_from_chemical_components
if not {'code','filename','chirals'}<=set(inspect.signature(reader).parameters):
    raise ValueError('Unsupported installed reader signature')
source=Path('source.cif');original=digest(source)
result={'reader_atoms':[], 'constructor_probe':{'status':'NOT_RUN'},
        'dictionary_generation':'NOT_RUN','optimization_execution':'NOT_RUN',
        'captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN'}
molecule=reader(spec['component'],filename=str(source.resolve()),chirals=False)
if molecule is None:raise ValueError('Installed reader returned no molecule')
for atom in molecule:
    marker=atom.chiral
    if type(marker) not in (str,bool,int,type(None)):raise ValueError('Unsupported native stereo marker')
    result['reader_atoms'].append({'atom':atom.name.strip(),'native_chiral_marker':marker})
if (len(result['reader_atoms'])!=len(spec['atoms']) or
    {r['atom'] for r in result['reader_atoms']}!=set(spec['atoms']) or
    len(molecule.bonds)!=spec['bond_count']):raise ValueError('Native reader changed atom/bond inventory')
# This is the reader's own explicit chirals=True entry point. It is not the
# complete builder pipeline, and invokes no optimizer or dictionary writer.
try:
    control=reader(spec['component'],filename=str(source.resolve()),chirals=True)
    result['constructor_probe']={'status':'COMPLETED','atom_count':len(control)}
except Exception as exc:
    result['constructor_probe']={'status':'EXCEPTION','exception_type':type(exc).__name__,
        'message':str(exc),'traceback':traceback.format_exc()}
if digest(source)!=original:raise ValueError('Chirality control changed its frozen input')
for row in spec['sources']:
    if digest(row['installed'])!=row['sha256']:raise ValueError('Installed chirality source changed')
Path(sys.argv[2]).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def _library_anchor(api_sources):
    rows=[r for r in api_sources if r.get('anchor')=='phenix_installation' and _safe(r.get('path')) and r['path'].endswith('/iotbx/phil.py')]
    if len(rows)!=1:raise ValueError('Require one verified installed library anchor')
    return PurePosixPath(rows[0]['path']).parent.parent


def verify_chirality_sources(installation_root, report, output):
    root=Path(installation_root).resolve(strict=True);output=Path(output).resolve(strict=True)
    if len(report['sources'])!=len(SOURCE_PATHS) or {r['snapshot']['path'] for r in report['sources']}!={p+'.txt' for p in SOURCE_PATHS}:
        raise ValueError('Installed chirality source scope differs')
    for row in report['sources']:
        if row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='chirality_directory':
            raise ValueError('Unsupported chirality source anchor')
        for path in [_inside(root,row['path']),_inside(output,row['snapshot']['path'])]:
            data=path.read_bytes()
            if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:
                raise ValueError('Installed or captured chirality source changed')
    return True


def audit_installed_chirality(installation_root, python_executable, api_sources, source, code, output, *, environment, timeout_seconds=30):
    """Record actual reader markers and its isolated chirals=True control."""
    if type(timeout_seconds) not in (int,float) or not 0<timeout_seconds<=60:
        raise ValueError('Require a chirality-control timeout in (0,60]')
    root=Path(installation_root).resolve(strict=True);python_executable=Path(python_executable).resolve(strict=True)
    source=Path(source).resolve(strict=True);output=Path(output).absolute()
    if not python_executable.is_relative_to(root) or output.resolve().is_relative_to(root):
        raise ValueError('Require selected Phenix Python and separate chirality evidence')
    if output.resolve()==source.parent or output.resolve().is_relative_to(source.parent):
        raise ValueError('Chirality evidence must be outside its input directory')
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError('Require a fresh regular chirality-control directory')
    inventory=reader_stereo_inventory(source,code);original=source.read_bytes();dispatcher=python_executable.read_bytes()
    site=_library_anchor(api_sources);rows=[];payloads={}
    for name in SOURCE_PATHS:
        relative=(site/name).as_posix();data=_inside(root,relative).read_bytes()
        if len(data)>MAX_SOURCE_BYTES:raise ValueError('Oversized installed chirality source')
        ast.parse(data,filename=name);payloads[name]=data
        rows.append({'anchor':'phenix_installation','path':relative,'sha256':sha256(data).hexdigest(),'size':len(data),
                     'snapshot':{'anchor':'chirality_directory','path':name+'.txt'}})
    output.mkdir(parents=True,exist_ok=False)
    for name,data in payloads.items():
        path=output/(name+'.txt');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    (output/'source.cif').write_bytes(original);(output/'chirality_worker.py').write_text(WORKER)
    bond_count=sum(len(r['declared_neighbors']) for r in inventory['atoms'].values())//2
    spec={'component':code,'atoms':sorted(inventory['atoms']),'bond_count':bond_count,'library':str(root/site),
          'sources':[{'installed':str(root/PurePosixPath(r['path'])),'sha256':r['sha256'],
                      'module':name[:-3].replace('/','.')} for name,r in zip(SOURCE_PATHS,rows)]}
    (output/'chirality_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    report={'schema_version':1,'policy_id':POLICY_ID,'component':code,'sources':rows,'source_inventory':inventory,
            'status':'REVIEW','installed_module_execution':'READER_AND_ITS_CHIRAL_CONSTRUCTOR_ONLY',
            'constructor_scope':'READER_CHIRALS_TRUE_NOT_FULL_BUILDER_REPLAY',
            'absolute_cip_assignment':'NOT_RUN','optimization_execution':'NOT_RUN','dictionary_generation':'NOT_RUN',
            'installed_phenix_edits':'NOT_RUN','captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN','automatic_adoption':False}
    verify_chirality_sources(root,report,output)
    with (output/'chirality_worker.log').open('xb') as log:
        process=subprocess.Popen([str(python_executable),'chirality_worker.py','chirality_spec.json','chirality_result.json'],
            cwd=output,env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
        try:returncode=process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_owned_group(process);raise ValueError('Installed chirality control timed out')
        except BaseException:
            _terminate_owned_group(process);raise
    if returncode!=0:raise ValueError('Installed chirality control failed; inspect chirality_worker.log')
    result=json.loads((output/'chirality_result.json').read_text())
    if (source.read_bytes()!=original or (output/'source.cif').read_bytes()!=original or python_executable.read_bytes()!=dispatcher):
        raise ValueError('Chirality input or selected dispatcher changed')
    verify_chirality_sources(root,report,output)
    unknown=set(inventory['unknown_markers']);observed={r['atom']:r['native_chiral_marker'] for r in result['reader_atoms']}
    if set(observed)!=set(inventory['atoms']):raise ValueError('Incomplete native stereo marker readback')
    conflicts=[n for n,row in inventory['atoms'].items()
        if (row['declared_stereo'] in {'R','S'} and observed[n]!=row['declared_stereo'])
        or (row['declared_stereo']=='N' and observed[n] not in (None,False,0,''))]
    unknown_marked=sorted(n for n in unknown if observed[n] not in (None,False,0,''))
    report.update(result=result,unknown_inputs_marked_chiral=unknown_marked,declared_marker_conflicts=sorted(conflicts),
        status='READER_MARKERS_PASS' if not unknown_marked and not conflicts and result['constructor_probe']['status']=='COMPLETED' else 'REVIEW',
        source_preserved=True,installed_sources_preserved=True,dispatcher_sha256=sha256(dispatcher).hexdigest())
    (output/'chirality_receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
