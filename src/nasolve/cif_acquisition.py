"""MTZ-free ordinary source selection and explicit NARestraints compiler checks.

This is acquisition preflight, not automatic repair adoption. No coordinates,
native process or guessed pairing enter these source/role compiler controls.
"""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re
from types import SimpleNamespace

POLICY_ID='cif-ordinary-source-acquisition-controls-v1'
REQUESTED_PAIRS=(('CGY','DX'),('1AP','DT'),('DZ','DP'),('IGU','IMC'),
    ('PDU','DA'),('5PC','DG'),('5CM','S6G'),('DF','DA'))


def _reference(path, root):
    data=path.read_bytes()
    return {'anchor':'acquisition_directory','path':path.relative_to(root).as_posix(),
        'sha256':sha256(data).hexdigest(),'size':len(data)}


def saved_repair_applicability(source, code, authority, snapshot, store_root):
    """Report source-bound lookup only; never authorize adoption from a code."""
    from .cif_dictionary_store import make_dictionary_request,lookup_dictionary,resolve_dictionary_snapshot
    saved=resolve_dictionary_snapshot(snapshot);manifest=saved['manifest'];request=manifest['request']
    if request['component']!=code:raise ValueError('Saved repair component differs')
    current=make_dictionary_request(source,code,source_authority=authority,
        recipe=request['recipe'],generator=request['generator'])
    same=current==request;lookup=lookup_dictionary(store_root,current,manifest['consumer'])
    return {'scope':'SOURCE_APPLICABILITY_ONLY; SAVED_CONSUMER_NOT_FRESHLY_CERTIFIED',
        'entry_id':saved['entry_id'],'source_and_authority_exact':same,'lookup_status':lookup['status'],
        'source_sha256':current['source_sha256'],'saved_source_sha256':request['source_sha256'],
        'source_authority':authority,'saved_source_authority':request['source_authority'],
        'candidate_selected':False,'original_stopping':saved['provenance']['stopping'],
        'original_converged':saved['provenance']['converged'],'original_notes':saved['provenance']['notes'],
        'notes':['A different source/authority cannot be replaced by this saved repair.'] if not same else
            ['Matching isolated numerics remain subject to current native/site qualification.']}


def audit_ordinary_acquisition(ready_set_executable, output, *, data_root=None,
                               pairs=REQUESTED_PAIRS, saved_snapshots=None, store_root=None):
    """Use ordinary source priority; freeze bytes and compile declared role pairs.

    Saved repairs are compared against the selected source and authority through
    the shared store request API. They never replace that selection in this
    preflight. Saved consumer fingerprints are not fresh runtime qualification.
    """
    from .curated_ligands import ligand_source,ligand_definition,validate_ligand_dictionary
    from .component_records import resolve_component_record
    from .ligand_profiles import _parameterized_codes
    from .cif_stereochemistry_audit import _values,_graph
    from .cif_dictionary_store import default_dictionary_store
    from .postmr import _patch_narestraints_records
    from .cif_na_policy import _requests
    from restraints.residue_library import load_residue_records
    from restraints.builder import pair_residue_from_pdb
    from restraints.phenix import generate_pair_restraints
    from restraints.recipe_library import recipe_for
    from restraints.stacking import _manual_parallelity
    if (not 1<=len(pairs)<=8 or len(set(pairs))!=len(pairs)
            or any(len(p)!=2 or p[0]==p[1] or any(not isinstance(c,str) or re.fullmatch('[A-Z0-9]{1,3}',c) is None for c in p) for p in pairs)):
        raise ValueError('Require one to eight explicit distinct component pairs')
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    if any(p.is_symlink() for p in output.parents):raise ValueError('Acquisition output cannot traverse a symlink')
    saved_snapshots={} if saved_snapshots is None else saved_snapshots
    codes=sorted({c for p in pairs for c in p})
    if not set(saved_snapshots)<=set(codes):raise ValueError('Saved snapshots exceed declared acquisition scope')
    # Read the workbook once and keep every original record for alias evidence.
    originals=load_residue_records();records,corrections=_patch_narestraints_records(originals,set(codes))
    output.mkdir(parents=True);sources={};paths={};mapped={};pair_results=[]
    store=default_dictionary_store() if store_root is None else Path(store_root)
    for code in codes:
        row={'component':code,'status':'REVIEW'};sources[code]=row
        try:
            selected=ligand_source(code,data_root,ready_set_executable=Path(ready_set_executable))
            before=selected.path.read_bytes();validate_ligand_dictionary(code,selected.path)
            destination=output/'sources'/(code+'.cif');destination.parent.mkdir(exist_ok=True)
            with destination.open('xb') as handle:handle.write(before)
            if selected.path.read_bytes()!=before:raise ValueError('Ordinary source changed during acquisition')
            values=_values(destination,code);elements=_graph(values)[0]
            record,proof=resolve_component_record(originals,code)
            operational,_=resolve_component_record(records,code)
            identity=SimpleNamespace(get_resname=lambda c=code:c,has_id=lambda n,e=elements:n in e,
                id=('',1,''),get_parent=lambda:SimpleNamespace(get_id=lambda:'A'))
            mapping=pair_residue_from_pdb([operational],identity)
            missing=sorted(set(mapping.atoms.values())-set(elements))
            if missing:raise ValueError('Declared NARestraints role atoms absent: '+', '.join(missing))
            row.update(status='SOURCE_ACQUISITION_PASS',authority=selected.authority,source_kind=selected.kind,
                source=_reference(destination,output),historical_source_path=str(selected.path),
                historical_source_path_role='PROVENANCE_ONLY; FROZEN_SOURCE_IS_OPERATIONAL',
                definition=asdict(ligand_definition(code)),role_resolution=proof,
                mapped_base_class=mapping.base_class,numerically_parameterized=code in _parameterized_codes(destination),
                source_bytes_preserved=True,requires_cif_review=False)
            paths[code]=destination;mapped[code]=(operational,set(elements))
            if code in saved_snapshots:
                row['saved_repair']=saved_repair_applicability(destination,code,selected.authority,saved_snapshots[code],store)
        except (OSError,ValueError,KeyError) as exc:
            row.update(status='REVIEW',error=str(exc),requires_cif_review=False)
    for number,pair in enumerate(pairs,1):
        row={'components':list(pair),'status':'REVIEW','scope':'DECLARED_ROLE_COMPILER_ONLY; NO_OBSERVED_COORDINATES'}
        pair_results.append(row)
        try:
            objects=[];atoms=[]
            for chain,code in zip(('A','B'),pair):
                record,elements=mapped[code]
                identity=SimpleNamespace(get_resname=lambda c=code:c,has_id=lambda n,e=elements:n in e,
                    id=('',1,''),get_parent=lambda c=chain:SimpleNamespace(get_id=lambda:c))
                objects.append(pair_residue_from_pdb([record],identity))
                for name in sorted(elements):
                    atoms.append({'i_seq':len(atoms),'atom_id':name,'label':chain+':1:'+name,
                        'identity':{'chain_id':chain,'resseq':'1'}})
            recipe=recipe_for(objects[0].base_class,objects[1].base_class)
            if recipe is None:raise ValueError('No declared NARestraints recipe for this exact pair')
            wrap=lambda body:'refinement {\n geometry_restraints {\n edits {\n'+body+'\n }\n }\n}\n'
            text=wrap(generate_pair_restraints(*objects,planes=False))
            requests=_requests(text,atoms)
            if not requests:raise ValueError('Configured pair emitted no restraints')
            stacks=[wrap(_manual_parallelity(*order)) for order in (objects,objects[::-1])]
            stack_requests=[_requests(t,atoms) for t in stacks]
            if any(len(r)!=1 or r[0]['kind']!='parallelity' for r in stack_requests):raise ValueError('Incomplete mapped stacking')
            folder=output/'pairs'/str(number);folder.mkdir(parents=True)
            p=folder/'pair.phil';p.write_text(text)
            stack_refs=[]
            for i,t in enumerate(stacks):
                f=folder/('stack_'+str(i)+'.phil');f.write_text(t);stack_refs.append(_reference(f,output))
            row.update(status='DECLARED_PAIR_AND_STACK_COMPILER_PASS',recipe=recipe.name,
                base_classes=[o.base_class for o in objects],pair_requests=requests,stack_requests=stack_requests,
                pair_phil=_reference(p,output),stack_phils=stack_refs)
        except (ValueError,KeyError,TypeError) as exc:row['error']=str(exc)
    passed=all(r['status']=='SOURCE_ACQUISITION_PASS' for r in sources.values()) and all(r['status']=='DECLARED_PAIR_AND_STACK_COMPILER_PASS' for r in pair_results)
    result={'schema_version':1,'policy_id':POLICY_ID,'status':'ORDINARY_ACQUISITION_CONTROLS_PASS' if passed else 'REVIEW',
        'scope':'ORDINARY_SOURCE_SELECTION_AND_EXPLICIT_ROLE_COMPILER_PREFLIGHT',
        'sources':sources,'declared_pairs':pair_results,'record_corrections':corrections,'policy_authority':'NARestraints',
        'requires_cif_review':False,'native_execution':'NOT_RUN','dictionary_generation':'NOT_RUN',
        'model_editing':'NOT_RUN','model_optimization':'NOT_RUN','readyset_execution':'NOT_RUN',
        'production_adoption':'NOT_RUN','scientific_qualification':'NOT_ASSESSED',
        'limitations':['Compiler controls have no observed coordinates or active native proxies.',
            'Selected sources may lack numerical restraints; ordinary recovery/adoption remains separate.',
            'C66 saved repairs bind different source projections/authority; no same-code substitution is permitted.']}
    (output/'acquisition.json').write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return result


def replay_ordinary_acquisition(members,output):
    """Replay returned source/role evidence with captured bytes and no native call."""
    from pathlib import PurePosixPath
    from .cif_dictionary_store import resolve_dictionary_snapshot
    from .curated_ligands import curated_dictionary
    expected=json.loads(members['ordinary_acquisition/acquisition.json'])
    report=json.loads(members['ordinary_acquisition_audit.json'])
    if expected!={k:v for k,v in report.items() if k not in {'directory','dispatcher'}}:
        raise ValueError('Ordinary acquisition report copies differ')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    executable=output/'installation/bin/phenix.ready_set';executable.parent.mkdir(parents=True)
    executable.write_text('Captured-source selection fixture only; never execute.\n')
    def read(ref,prefix):
        name=ref['path']
        if (not isinstance(name,str) or name.startswith('/') or '\\' in name or ':' in name
                or any(p in {'','.','..'} for p in name.split('/'))):raise ValueError('Unsafe source/role reference')
        data=members[prefix+name]
        if len(data)!=ref['size'] or sha256(data).hexdigest()!=ref['sha256']:raise ValueError('Source/role reference differs')
        return data
    for code,row in expected['sources'].items():
        ref=row['source']
        if ref['anchor']!='acquisition_directory':raise ValueError('Wrong acquisition source anchor')
        data=read(ref,'ordinary_acquisition/')
        if row['authority']=='CURATED':
            if data!=curated_dictionary(code).read_bytes():raise ValueError('Curated source differs from returned source')
        elif row['authority']=='NATIVE':
            p=executable.parent.parent/'lib/python3.11/site-packages/chem_data/chemical_components'/code[0].lower()/('data_'+code+'.cif')
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        else:raise ValueError('Unsupported returned ordinary source authority')
    reuse=json.loads(members['inputs/review/dictionary_reuse_audit.json']);snapshots={}
    for code,row in reuse['cases'].items():
        ref=row['first_snapshot'];read(ref,'inputs/review/dictionary_reuse/')
        if ref['anchor']!='dictionary_reuse_directory':raise ValueError('Wrong projection snapshot anchor')
        snapshots[code]=output/'snapshots'/code
    # Copy the complete snapshots through their declared prefix (including entry).
    for code,row in reuse['cases'].items():
        prefix='inputs/review/dictionary_reuse/'+str(PurePosixPath(row['first_snapshot']['path']).parent)+'/'
        folder=snapshots[code]
        for n,d in members.items():
            if not n.startswith(prefix):continue
            relative=n.removeprefix(prefix)
            if relative not in {'resolution.json','entry/source.cif','entry/dictionary.cif','entry/manifest.json','entry/provenance.json','entry/qualification.json'}:
                raise ValueError('Unexpected projection snapshot member')
            p=folder/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(d)
        resolve_dictionary_snapshot(folder)
    fresh=audit_ordinary_acquisition(executable,output/'replay',saved_snapshots=snapshots,store_root=output/'absent_cache')
    left,right=json.loads(json.dumps(fresh)),json.loads(json.dumps(expected))
    for value in [left,right]:
        for row in value['sources'].values():row.pop('historical_source_path')
    if left!=right:raise ValueError('Maintained ordinary source/compiler evidence differs')
    files={p.relative_to(output/'replay').as_posix():p for p in (output/'replay').rglob('*') if p.is_file()}
    if set(files)!={n.removeprefix('ordinary_acquisition/') for n in members if n.startswith('ordinary_acquisition/')}:
        raise ValueError('Ordinary source/role inventory differs')
    for name,path in files.items():
        if name!='acquisition.json' and path.read_bytes()!=members['ordinary_acquisition/'+name]:raise ValueError('Ordinary source/role bytes differ')
    return True
