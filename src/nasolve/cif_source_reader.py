"""Bounded native source-format reads, with no chiral-constructor request."""
from __future__ import annotations
import ast
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess

from .cif_elbow_contract import _inside,MAX_SOURCE_BYTES
from .cif_elbow_chirality import _library_anchor
from .cif_generation import _terminate_owned_group
from .cif_stereochemistry_audit import _values,_graph,_coordinates,reader_stereo_inventory

POLICY_ID='cif-installed-source-reader-inventory-v1'
SOURCE_PATHS=('elbow/chemistry/any_chemical_format_reader.py','elbow/formats/monomer_library_cif_parser.py')

WORKER=r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,inspect,json,sys,traceback
spec=json.loads(Path(sys.argv[1]).read_text());directory=Path.cwd().resolve()
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory]
sys.path.insert(0,spec['library'])
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()
modules={}
for row in spec['sources']:
    path=Path(row['installed']).resolve(strict=True)
    if digest(path)!=row['sha256']:raise ValueError('Installed reader source changed')
    found=importlib.util.find_spec(row['module'])
    if found is None or found.origin is None or Path(found.origin).resolve(strict=True)!=path:
        raise ValueError('Unselected installed reader source')
    module=importlib.import_module(row['module'])
    if Path(module.__file__).resolve(strict=True)!=path:raise ValueError('Unselected installed reader import')
    modules[row['module']]=module
api=modules['elbow.chemistry.any_chemical_format_reader']
reader=api.any_chemical_format_reader
if not {'data','simple','return_all_restraints','do_not_check_for_smiles'}<=set(inspect.signature(reader).parameters):
    raise ValueError('Unsupported source reader signature')
source=Path('source.cif');original=digest(source)
def scalar(v):
    if type(v) in (str,bool,int,float,type(None)):return v
    return 'UNSUPPORTED_NATIVE_TYPE:'+type(v).__name__
result={'execution':'NOT_RUN','atoms':[],'bonds':[],'dictionary_generation':'NOT_RUN',
        'whole_molecule_optimization':'NOT_REQUESTED','chiral_constructor':'NOT_REQUESTED',
        'parser_internal_operations':'NOT_INSTRUMENTED',
        'independent_absolute_cip_validation':'NOT_RUN','captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN'}
try:
    result['dispatch_is_chemical_components']=bool(api.is_chemical_components_file(source.read_text()))
    molecule=reader(str(source.resolve()),simple=True,return_all_restraints=True,do_not_check_for_smiles=True)
    # The captured dispatcher explicitly supports lists of parsed molecules.
    # This input is one component: unwrap one, refuse multiple or empty lists.
    result['component_container']='SINGLE_MOLECULE'
    if type(molecule) is list:
        if len(molecule)!=1:raise ValueError('Require one native parsed component')
        molecule=molecule[0];result['component_container']='SINGLETON_LIST'
    result['format']=molecule.GetOriginalFormat()
    result['molecule_attribute_names']=sorted(vars(molecule))
    for atom in molecule:
        result['atoms'].append({'atom':atom.name.strip(),'element':atom.symbol,
            'native_atom_charge':scalar(atom.charge),'native_chiral_marker':scalar(getattr(atom,'chiral',None)),
            'native_volume_sign':scalar(getattr(atom,'volume_sign',None)),
            'xyz':[float(atom.xyz.x),float(atom.xyz.y),float(atom.xyz.z)]})
    for bond in molecule.bonds:
        a,b=bond
        result['bonds'].append({'atoms':sorted([a.name.strip(),b.name.strip()]),'native_order':scalar(bond.order)})
    result['execution']='COMPLETED'
except Exception as exc:
    result.update(execution='EXCEPTION',exception_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
if digest(source)!=original:raise ValueError('Native source reader changed frozen input')
for row in spec['sources']:
    if digest(row['installed'])!=row['sha256']:raise ValueError('Installed reader source changed')
Path(sys.argv[2]).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def verify_source_reader_capture(installation_root,report,output):
    root=Path(installation_root).resolve(strict=True);output=Path(output).resolve(strict=True)
    if len(report['sources'])!=2 or {r['snapshot']['path'] for r in report['sources']}!={p+'.txt' for p in SOURCE_PATHS}:
        raise ValueError('Unexpected source-reader snapshot scope')
    for row in report['sources']:
        if row.get('anchor')!='phenix_installation' or row['snapshot'].get('anchor')!='reader_directory':
            raise ValueError('Unsupported source-reader anchor')
        for path in [_inside(root,row['path']),_inside(output,row['snapshot']['path'])]:
            data=path.read_bytes()
            if len(data)!=row['size'] or sha256(data).hexdigest()!=row['sha256']:raise ValueError('Installed/captured source reader changed')
    return True


def audit_source_reader(installation_root,python_executable,api_sources,source,code,output,*,environment,expected_dialect,timeout_seconds=30):
    if expected_dialect not in {'MONOMER_LIBRARY_CIF','CHEMICAL_COMPONENTS_CIF'}:raise ValueError('Unsupported explicit reader dialect')
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=30:
        raise ValueError('Require a source-reader timeout in (0,30]')
    root=Path(installation_root).resolve(strict=True);python_executable=Path(python_executable).resolve(strict=True)
    source=Path(source).resolve(strict=True);output=Path(output).absolute()
    if (not python_executable.is_relative_to(root) or output.resolve().is_relative_to(root)
            or output.resolve().is_relative_to(source.parent) or output.exists() or output.is_symlink()
            or any(p.is_symlink() for p in output.parents)):
        raise ValueError('Require selected Phenix Python and fresh separate reader evidence')
    original=source.read_bytes();dispatcher=python_executable.read_bytes();site=_library_anchor(api_sources)
    values=_values(source,code);elements,bonds,charges,_=_graph(values);family,xyz=_coordinates(values,source=True)
    rows=[];data={}
    for name in SOURCE_PATHS:
        path=(site/name).as_posix();payload=_inside(root,path).read_bytes()
        if len(payload)>MAX_SOURCE_BYTES:raise ValueError('Oversized installed reader source')
        ast.parse(payload,filename=name);data[name]=payload
        rows.append({'anchor':'phenix_installation','path':path,'sha256':sha256(payload).hexdigest(),'size':len(payload),
                     'snapshot':{'anchor':'reader_directory','path':name+'.txt'}})
    output.mkdir(parents=True,exist_ok=False)
    for name,payload in data.items():
        p=output/(name+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(payload)
    (output/'source.cif').write_bytes(original);(output/'reader_worker.py').write_text(WORKER)
    spec={'library':str(root/site),'sources':[{'installed':str(root/r['path']),'sha256':r['sha256'],
          'module':name[:-3].replace('/','.')} for name,r in zip(SOURCE_PATHS,rows)]}
    (output/'reader_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    report={'schema_version':1,'policy_id':POLICY_ID,'component':code,'sources':rows,'expected_dialect':expected_dialect,
        'source_sha256':sha256(original).hexdigest(),'dispatcher_sha256':sha256(dispatcher).hexdigest(),
        'timeout_seconds':timeout_seconds,'source_stereo_inventory':reader_stereo_inventory(source,code),
        'dictionary_generation':'NOT_RUN','whole_molecule_optimization':'NOT_REQUESTED','chiral_constructor':'NOT_REQUESTED',
        'parser_internal_operations':'NOT_INSTRUMENTED',
        'independent_absolute_cip_validation':'NOT_RUN','signed_stereo_native_qualification':'NOT_RUN',
        'native_formal_charge_semantics':'REQUIRES_CAPTURED_PARSER_REVIEW',
        'installed_phenix_edits':'NOT_RUN','captured_code_execution':'NOT_RUN','pickle_loading':'NOT_RUN','automatic_adoption':False}
    verify_source_reader_capture(root,report,output)
    with (output/'reader_worker.log').open('xb') as log:
        process=subprocess.Popen([str(python_executable),'reader_worker.py','reader_spec.json','reader_result.json'],
            cwd=output,env=dict(environment),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
        try:rc=process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_owned_group(process);raise ValueError('Source reader audit timed out')
        except BaseException:
            _terminate_owned_group(process);raise
    if rc!=0:raise ValueError('Source reader worker failed; inspect reader_worker.log')
    result=json.loads((output/'reader_result.json').read_text());checks={}
    if result['execution']=='COMPLETED':
        observed={r['atom']:r for r in result['atoms']}
        checks['atom_identities']=len(observed)==len(result['atoms'])==len(elements) and set(observed)==set(elements)
        checks['reader_route']=(result['format']==('CIF' if expected_dialect=='MONOMER_LIBRARY_CIF' else 'CHEMICAL COMPONENTS')
            and result['dispatch_is_chemical_components'] is (expected_dialect=='CHEMICAL_COMPONENTS_CIF'))
        checks['atom_elements']=checks['atom_identities'] and all(observed[n]['element'].upper()==e for n,e in elements.items())
        checks['atom_charge_values']=checks['atom_identities'] and all(type(observed[n]['native_atom_charge']) in (int,float) and q is not None and observed[n]['native_atom_charge']==q for n,q in charges.items())
        checks['source_coordinates']=checks['atom_identities'] and len(xyz)==len(elements) and all(all(math.isclose(a,b,abs_tol=1e-9,rel_tol=0) for a,b in zip(observed[n]['xyz'],xyz[n])) for n in observed)
        actual={tuple(r['atoms']):r['native_order'] for r in result['bonds']}
        normalized={'SINGLE':1,'DOUBLE':2,'TRIPLE':3,'AROMATIC':1.5}
        checks['declared_bond_orders']=(len(actual)==len(result['bonds'])==len(bonds) and set(actual)==set(bonds)
            and all(actual[p]==normalized.get(order) for p,order in bonds.items()))
    if source.read_bytes()!=original or (output/'source.cif').read_bytes()!=original or python_executable.read_bytes()!=dispatcher:
        raise ValueError('Source-reader input or selected dispatcher changed')
    verify_source_reader_capture(root,report,output)
    report.update(status='READER_ROUTE_AND_INVENTORY_PASS' if checks and all(checks.values()) else 'REVIEW',
        checks=checks,result=result,coordinate_family=family,source_preserved=True,installed_sources_preserved=True,
        limitations=['Reader inventory matches are not signed-stereo, absolute CIP, generator or scientific qualification.',
                    'Native atom charge values are recorded; their formal-charge semantics await captured parser review.',
                    'No chiral constructor, whole-molecule optimizer or dictionary writer is requested.'])
    (output/'reader_receipt.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
