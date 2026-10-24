"""Read installed CCD chemistry separately from numerical monomer resources.

No resource selection calls ReadySet, molecule generation, a chiral constructor
or an optimizer. Captured route helpers are text evidence, never executable code.
"""
from hashlib import sha256
import ast
import json
import math
import os
from pathlib import Path
import re
import subprocess

from .cif_doctor import assess_dictionaries,compare_dictionaries
from .cif_generation import _CHEMICAL_FIELDS,_terminate_owned_group
from .cif_elbow_chirality import _library_anchor
from .cif_elbow_contract import _inside,MAX_SOURCE_BYTES
from .cif_stereochemistry_audit import _values,_graph,reader_stereo_inventory
from .cif_triple_bond_audit import audit_triple_bonds

POLICY_ID='cif-installed-monomer-ccd-source-catalogue-v1'
PROOF_PATHS=('mmtbx/monomer_library/server.py','mmtbx/monomer_library/cif_types.py','elbow/utilities/Utilities.py')
ROUTE_MODULES=(('elbow/utilities/geostd_utils.py',),('elbow/utilities/mmtbx_utils.py',),
    ('mmtbx/chemical_components.py','mmtbx/chemical_components/__init__.py'))


def compare_installed_ccd(reference,installed,code):
    """Compare declarations and descriptor text without inferring SMILES graphs."""
    reference,installed=Path(reference),Path(installed);before=reference.read_bytes(),installed.read_bytes()
    values=_values(installed,code);assessment=assess_dictionaries([installed],stage='installed-ccd-source')
    if len(assessment['components'])!=1:raise ValueError('Require one exact installed CCD component')
    comparison=compare_dictionaries([reference],[installed]);differences=[r for r in comparison['differences'] if r['field'] in _CHEMICAL_FIELDS]
    def descriptors(v):
        stem='_pdbx_chem_comp_descriptor.';columns={k[len(stem):]:x for k,x in v.items() if k.startswith(stem)}
        if not columns:return []
        if len({len(x) for x in columns.values()})!=1:raise ValueError('Inconsistent installed descriptor columns')
        rows=[{k:x[i] for k,x in columns.items()} for i in range(len(next(iter(columns.values()))))]
        return sorted([r for r in rows if 'SMILES' in r.get('type','').upper()],key=lambda r:json.dumps(r,sort_keys=True))
    sm=descriptors(values);old=descriptors(_values(reference,code));orders=_graph(values)[1]
    result={'schema_version':1,'policy_id':POLICY_ID,'component':code,'status':'REVIEW',
        'reference_sha256':sha256(before[0]).hexdigest(),'installed_sha256':sha256(before[1]).hexdigest(),
        'chemical_declarations':'REVIEW' if differences else 'EXACT_DECLARATIONS','chemical_differences':differences,
        'assessment':assessment,'triple_bonds':[list(p) for p,o in sorted(orders.items()) if o=='TRIPLE'],
        'triple_screen':audit_triple_bonds(reference,code,dictionary=installed),
        'stereochemistry':reader_stereo_inventory(installed,code),'descriptors':sm,'reference_descriptors':old,
        'descriptor_text_comparison':'UNAVAILABLE' if not sm or not old else 'TEXT_IDENTICAL' if sm==old else 'TEXT_DIFFERENT',
        'mapped_smiles_graph_comparison':'NOT_RUN','dictionary_parameterization':assessment['components'][0]['verdicts']['numerical'],
        'optimization':'NOT_RUN','dictionary_generation':'NOT_RUN','automatic_adoption':False,
        'limitations':['CCD declarations and SMILES text are source evidence, not native numerical restraint targets.',
            'Equal descriptor text does not independently establish a mapped molecular graph or historical correctness.',
            'No tautomer, protonation, atom naming, stereo or restraint target is repaired.']}
    if before!=(reference.read_bytes(),installed.read_bytes()):raise ValueError('Installed CCD comparison input changed')
    return result


WORKER=r'''from pathlib import Path
from hashlib import sha256
import importlib,importlib.util,json,sys,traceback
spec=json.loads(Path(sys.argv[1]).read_text());directory=Path.cwd().resolve();root=Path(spec['installation']).resolve(strict=True)
sys.path[:]=[p for p in sys.path if Path(p or '.').resolve()!=directory];sys.path.insert(0,spec['library'])
def digest(p):return sha256(Path(p).read_bytes()).hexdigest()
modules={}
for row in spec['sources']:
    path=Path(row['installed']).resolve(strict=True);name=row['module'];found=importlib.util.find_spec(name)
    if found is None or Path(found.origin).resolve(strict=True)!=path or digest(path)!=row['sha256']:
        raise ValueError('Unselected or changed installed monomer API')
    module=importlib.import_module(name)
    if Path(module.__file__).resolve(strict=True)!=path:raise ValueError('Unselected installed monomer import')
    modules[name]=module
server=modules['mmtbx.monomer_library.server']
result={'schema_version':1,'policy_id':spec['policy_id'],'canonical_controls':{},'lookups':{},'library_roots':[],
        'dictionary_generation':'NOT_RUN','optimization':'NOT_RUN','readyset':'NOT_RUN','automatic_adoption':False}
def row(obj):return {k:getattr(obj,k) for k in obj.cif_keywords()}
def roots(library):
    for field in ['root_path','geostd_path']:
        value=getattr(library,field,None)
        if not isinstance(value,str):raise ValueError('Unavailable native monomer-library root')
        path=Path(value).resolve()
        if not path.is_relative_to(root):raise ValueError('Monomer-library root escapes the selected installation')
        record={'field':field,'anchor':'phenix_installation','path':path.relative_to(root).as_posix(),'exists':path.is_dir()}
        if record not in result['library_roots']:result['library_roots'].append(record)
def dump(base,label,full=True):
    if base is None:return {'status':'MISSING'}
    metadata=row(base.chem_comp);record={'status':'RECORDED','metadata':metadata,'source_provenance':getattr(base,'source_info',None)}
    if not full:return record
    record['categories']={k:[row(x) for x in getattr(base,f)] for k,f in {
        'atoms':'atom_list','bonds':'bond_list','angles':'angle_list','torsions':'tor_list','chirality':'chir_list','plane_atoms':'plane_atom_list'}.items()}
    info=record['source_provenance']
    if not isinstance(info,str) or not info.startswith('file: '):record['status']='UNSUPPORTED';return record
    path=Path(info[6:]).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():raise ValueError('Monomer source escapes the selected installation')
    data=path.read_bytes()
    if len(data)>spec['max_bytes']:raise ValueError('Oversized installed monomer resource')
    output=Path('monomers')/(label+'.cif');output.parent.mkdir(exist_ok=True)
    with output.open('xb') as handle:handle.write(data)
    record['resource']={'anchor':'phenix_installation','path':path.relative_to(root).as_posix(),'sha256':sha256(data).hexdigest(),
        'size':len(data),'snapshot':{'anchor':'catalogue_directory','path':output.as_posix()}}
    if path.read_bytes()!=data:raise ValueError('Installed monomer changed')
    return record
library=server.server();roots(library)
for code in ['DG','DC']:
    try:
        base,interpretation=library.get_comp_comp_id_and_atom_name_interpretation(residue_name=code,atom_names=[])
        result['canonical_controls'][code]=dump(base,'canonical_'+code,False)
    except Exception as exc:result['canonical_controls'][code]={'status':'EXCEPTION','error':type(exc).__name__+': '+str(exc)}
for code in spec['components']:
    result['lookups'][code]={}
    for mode in ['wrapped','direct']:
        library=server.server();roots(library)
        try:
            if mode=='wrapped':base,interpretation=library.get_comp_comp_id_and_atom_name_interpretation(residue_name=code,atom_names=[])
            else:base=library.get_comp_comp_id_direct(comp_id=code)
            result['lookups'][code][mode]=dump(base,code+'_'+mode)
        except Exception as exc:result['lookups'][code][mode]={'status':'EXCEPTION','error':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc()}
for item in spec['sources']:
    if digest(item['installed'])!=item['sha256']:raise ValueError('Installed monomer API changed')
Path('source_catalogue_result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
'''


def verify_installed_sources(root,report,output):
    root=Path(root).resolve(strict=True);output=Path(output).resolve(strict=True);rows=list(report['sources'])+[report['readyset_dispatcher']]
    for case in report['components'].values():
        if case.get('resource'):rows.append(case['resource'])
    for case in report.get('native_resources',{}).get('lookups',{}).values():
        for lookup in case.values():
            if lookup.get('resource'):rows.append(lookup['resource'])
    for r in rows:
        if r.get('anchor')!='phenix_installation' or r['snapshot'].get('anchor')!='catalogue_directory':raise ValueError('Unsafe installed catalogue anchor')
        for p in [_inside(root,r['path']),_inside(output,r['snapshot']['path'])]:
            data=p.read_bytes()
            if len(data)!=r['size'] or sha256(data).hexdigest()!=r['sha256']:raise ValueError('Installed or captured catalogue source changed')
    return True


def audit_installed_sources(root,executable,readyset,api_sources,source_proofs,references,output,*,environment,timeout_seconds=30):
    """Freeze exact installed CCD paths and distinguish both monomer APIs."""
    if type(timeout_seconds) not in (int,float) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=60:raise ValueError('Require bounded source-catalogue timeout')
    if not references or len(references)>3 or any(not re.fullmatch(r'[A-Z0-9]{1,3}',c) for c in references):raise ValueError('Require one to three explicit component codes')
    root=Path(root).resolve(strict=True);executable=Path(executable).resolve(strict=True);readyset=Path(readyset).resolve(strict=True);output=Path(output).absolute()
    originals={Path(p).resolve(strict=True):Path(p).read_bytes() for p in references.values()}
    if (not executable.is_relative_to(root) or not readyset.is_relative_to(root) or output.resolve().is_relative_to(root)
            or any(output.resolve().is_relative_to(p.parent) for p in originals) or output.exists() or output.is_symlink()
            or any(p.is_symlink() for p in output.parents)):raise ValueError('Require selected executables and fresh separate source evidence')
    site=_library_anchor(api_sources);proof={r['path']:r for r in source_proofs};wanted={(site/n).as_posix() for n in PROOF_PATHS}
    if len(proof)!=len(source_proofs) or set(proof)!=wanted or any(r.get('anchor')!='phenix_installation' for r in proof.values()):raise ValueError('Require exact prior monomer and route-helper source proofs')
    rows=[];payloads={};unavailable=[]
    for choices in [(n,) for n in PROOF_PATHS]+list(ROUTE_MODULES):
        matches=[n for n in choices if (root/site/n).is_file()]
        if len(matches)>1:raise ValueError('Ambiguous installed Python module source')
        if not matches:
            if choices[0] in PROOF_PATHS:raise ValueError('Missing previously verified source')
            unavailable.append(list(choices));continue
        name=matches[0];relative=(site/name).as_posix();data=_inside(root,relative).read_bytes()
        if len(data)>MAX_SOURCE_BYTES:raise ValueError('Oversized installed catalogue API')
        ast.parse(data,filename=name)
        if relative in proof and (sha256(data).hexdigest()!=proof[relative]['sha256'] or len(data)!=proof[relative]['size']):raise ValueError('Prior installed resource API changed')
        payloads[name]=data;rows.append({'anchor':'phenix_installation','path':relative,'sha256':sha256(data).hexdigest(),'size':len(data),
            'snapshot':{'anchor':'catalogue_directory','path':name+'.txt'}})
    dispatcher=executable.read_bytes();ready_bytes=readyset.read_bytes()
    if len(ready_bytes)>MAX_SOURCE_BYTES:raise ValueError('Oversized ReadySet dispatcher')
    output.mkdir(parents=True)
    for name,data in payloads.items():
        p=output/(name+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    (output/'ready_set_dispatcher.txt').write_bytes(ready_bytes)
    report={'schema_version':1,'policy_id':POLICY_ID,'status':'REVIEW','sources':rows,'unavailable_source_layouts':unavailable,
        'readyset_dispatcher':{'anchor':'phenix_installation','path':readyset.relative_to(root).as_posix(),'sha256':sha256(ready_bytes).hexdigest(),
            'size':len(ready_bytes),'snapshot':{'anchor':'catalogue_directory','path':'ready_set_dispatcher.txt'}},
        'components':{},'readyset_execution':'NOT_RUN','dictionary_generation':'NOT_RUN','optimization':'NOT_RUN','automatic_adoption':False,
        'route_helpers':'STATIC_SOURCE_CAPTURE_ONLY_NOT_EXECUTED','mapped_smiles_graph_comparison':'NOT_RUN'}
    for code,reference in references.items():
        relative=(site/'chem_data/chemical_components'/code[0].lower()/('data_'+code+'.cif')).as_posix()
        case={'status':'MISSING','requested_resource':{'anchor':'phenix_installation','path':relative}}
        report['components'][code]=case
        if (root/relative).is_file():
            data=_inside(root,relative).read_bytes()
            if len(data)>MAX_SOURCE_BYTES:raise ValueError('Oversized installed CCD component')
            target=output/'ccd'/(code+'.cif');target.parent.mkdir(exist_ok=True);target.write_bytes(data)
            case['resource']={'anchor':'phenix_installation','path':relative,'sha256':sha256(data).hexdigest(),'size':len(data),
                'snapshot':{'anchor':'catalogue_directory','path':target.relative_to(output).as_posix()}}
            try:case['comparison']=compare_installed_ccd(reference,target,code);case['status']='RECORDED'
            except ValueError as exc:case.update(status='REVIEW',error=str(exc))
    verify_installed_sources(root,report,output)
    spec={'policy_id':POLICY_ID,'installation':str(root),'library':str(root/site),'components':sorted(references),'max_bytes':MAX_SOURCE_BYTES,
        'sources':[{'installed':str(root/site/name),'module':name[:-3].replace('/','.'),'sha256':sha256(payloads[name]).hexdigest()} for name in PROOF_PATHS[:2]]}
    (output/'source_catalogue_spec.json').write_text(json.dumps(spec,indent=2)+'\n');(output/'source_catalogue_worker.py').write_text(WORKER)
    with (output/'source_catalogue.log').open('xb') as log:
        process=subprocess.Popen([str(executable),'source_catalogue_worker.py','source_catalogue_spec.json'],cwd=output,env=dict(environment),
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=os.name=='posix')
        try:rc=process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_owned_group(process);raise ValueError('Installed source catalogue timed out')
        except BaseException:
            _terminate_owned_group(process);raise
    if rc!=0:raise ValueError('Installed source catalogue worker failed; inspect source_catalogue.log')
    p=output/'source_catalogue_result.json'
    if not p.is_file() or p.is_symlink():raise ValueError('Missing exact source catalogue result')
    report['native_resources']=json.loads(p.read_text())
    if (report['native_resources'].get('policy_id')!=POLICY_ID or set(report['native_resources'].get('lookups',{}))!=set(references)
            or set(report['native_resources'].get('canonical_controls',{}))!={'DG','DC'}):raise ValueError('Invalid source catalogue result')
    if executable.read_bytes()!=dispatcher or any(p.read_bytes()!=data for p,data in originals.items()):raise ValueError('Catalogue dispatcher/reference changed')
    verify_installed_sources(root,report,output)
    (output/'source_catalogue_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
    return report
