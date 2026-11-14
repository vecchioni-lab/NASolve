"""Explicit linked-O3 candidates from curated sources and captured native evidence.

Only a graph-identified O3 hydrogen and its dependent rows are removed. The O3
energy type comes from a captured canonical outgoing site. Existing modifiers,
remaining numerical targets, formal/partial charges and source files survive.
This diagnostic layer does not adopt dictionaries or change model coordinates.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import shutil
from tempfile import TemporaryDirectory
from typing import Sequence

from .cif_doctor import assess_dictionaries
from .cif_linked_preparation import (
    _model_inventory, _prune, _render, _selection, atom_rows,
    component_values, hydrogen_neighbors,
)
from .cif_linked_qualification import _site, native_backbone_links
from .cif_terminal_qualification import definition_projection_checks, projection_site_plan
from .ligand_profiles import _emit

OUTGOING_PREPARATION_POLICY = 'cif-native-linked-oxygen-v1'


def _safe(name):
    return isinstance(name,str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(
        p not in {'','.','..'} for p in name.split('/'))


def _anchored(directory,record):
    if record.get('anchor')!='native_directory' or not _safe(record.get('path')):
        raise ValueError('Unsupported captured native anchor/path')
    path=directory/PurePosixPath(record['path'])
    if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError('Captured native artifact escapes its receipt directory')
    data=path.read_bytes()
    if len(data)!=record.get('size') or sha256(data).hexdigest()!=record.get('sha256'):
        raise ValueError('Captured native artifact changed')
    return data


def load_outgoing_authority(receipt_path: Path, model: Path, expected_links, authority_site: str) -> dict:
    """Verify a complete linked inventory and an explicit canonical O3 control."""
    receipt_path=Path(receipt_path);payload=receipt_path.read_bytes();receipt=json.loads(payload)
    if (receipt.get('schema_version')!=1 or receipt.get('audit_kind')!='cif_native_bundle_inspection'
            or receipt.get('policy_id')!='cif-native-bundle-inventory-v1' or receipt.get('status')!='REVIEW'
            or receipt.get('execution',{}).get('status')!='COMPLETED' or receipt['execution'].get('returncode')!=0
            or receipt.get('frozen_inputs_preserved') is not True or receipt.get('source_preserved') is not True):
        raise ValueError('Require a completed preserved native linked inventory')
    outputs=receipt.get('outputs',[]);inputs=receipt.get('inputs',[])
    if sum(r.get('path')=='native_validation.json' for r in outputs)!=1:
        raise ValueError('Missing exact captured native validation artifact')
    for record in outputs+inputs:_anchored(receipt_path.parent,record)
    native=receipt.get('native_validation',{})
    if native!=json.loads((receipt_path.parent/'native_validation.json').read_text()):
        raise ValueError('Captured native report disagrees with its receipt')
    models=[r for r in inputs if r.get('role')=='model']
    if len(models)!=1 or Path(model).read_bytes()!=_anchored(receipt_path.parent,models[0]):
        raise ValueError('Model differs from the captured native input')
    if native.get('inventory_detail')!='linked' or native.get('status')!='REVIEW':
        raise ValueError('Require detailed captured native definitions')
    links=[tuple(pair) for pair in expected_links]
    if not links or len(links)!=len(set(links)) or any(a==b for a,b in links):
        raise ValueError('Require unique explicitly declared backbone links')
    if set(native_backbone_links(native))!=set(links):
        raise ValueError('Declared links disagree with the captured native backbone')
    mappings=native.get('monomer_mappings',{}).get('rows',[])
    by_site={r['site']:r for r in mappings}
    if len(by_site)!=len(mappings):raise ValueError('Ambiguous captured native site')
    inventory=_model_inventory(Path(model))
    model_atoms={(site,name) for site,r in inventory.items() for name in r['atoms']}
    native_atoms=[(_site(a),a['atom_id']) for a in native['atoms']]
    if len(native_atoms)!=len(set(native_atoms)) or set(native_atoms)!=model_atoms:
        raise ValueError('Captured native atom identities differ from the model')
    if set(inventory)!=set(by_site) or any(by_site[s].get('resname')!=r['code'] for s,r in inventory.items()):
        raise ValueError('Captured native residue identities differ from the model')
    row=by_site.get(authority_site,{})
    definition=row.get('metadata',{}).get('effective_definition',{})
    atoms={r['atom_id']:r for r in definition.get('atoms',[])}
    if (row.get('resname') not in {'DA','DC','DG','DT'} or row.get('metadata',{}).get('group')!='DNA'
            or authority_site not in {left for left,_ in links}
            or atoms.get("O3'",{}).get('type_symbol')!='O'
            or atoms.get("C3'",{}).get('type_symbol')!='C'
            or atoms.get("O3'",{}).get('type_energy')!='OC2'):
        raise ValueError('Require the reviewed canonical outgoing O3 OC2 authority')
    neighbors=[r['atom_id_2'] if r['atom_id_1']=="O3'" else r['atom_id_1']
               for r in definition.get('bonds',[]) if "O3'" in {r['atom_id_1'],r['atom_id_2']}]
    if neighbors!=["C3'"]:
        raise ValueError('Canonical outgoing oxygen has unsupported adjacency')
    return {'policy_id':OUTGOING_PREPARATION_POLICY,'native_receipt_sha256':sha256(payload).hexdigest(),
        'authority_site':authority_site,'canonical_component':row['resname'],
        'type_energy':atoms["O3'"]['type_energy'],'atom_id':"O3'",
        'phenix_version':receipt.get('phenix_version'),'partial_charge_copied':False,
        'native':native}


def prepare_outgoing_component(source: Path, model: Path, contexts: Sequence[dict],
        native_receipt: Path, output_directory: Path, *, code: str,
        expected_links: Sequence[tuple[str,str]], authority_site: str) -> dict:
    """Add per-site modifiers; preserve the curated base and existing site mods.

    Every same-code site needs an explicit context. True free 3' ends remain
    untouched. Selected source projections must first match all recorded native
    rows; this is not a whole-component generation or broader chemistry gate.
    """
    paths=[Path(source),Path(model),Path(native_receipt)]
    payloads=[p.read_bytes() for p in paths];output=Path(output_directory)
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    if any(output.resolve()==p.resolve() or p.parent.resolve() in output.resolve().parents for p in paths):
        raise ValueError('Outgoing preparation must be outside preserved input directories')
    authority=load_outgoing_authority(paths[2],paths[1],expected_links,authority_site)
    native=authority['native'];mappings={r['site']:r for r in native['monomer_mappings']['rows']}
    inventory=_model_inventory(paths[1]);values=component_values(paths[0],code)
    if values.get('_chem_comp.group')!=['DNA']:raise ValueError('Require explicit curated DNA metadata')
    atoms=atom_rows(values)
    if {c['site'] for c in contexts}!={s for s,r in inventory.items() if r['code']==code}:
        raise ValueError('Require declared contexts for every model site sharing the component code')
    if len(contexts)!=len({c['site'] for c in contexts}):raise ValueError('Duplicate explicit site context')
    links=[tuple(pair) for pair in expected_links];incoming={};outgoing={}
    for left,right in links:
        if left in outgoing or right in incoming:raise ValueError('Unsupported branching backbone context')
        outgoing[left]=right;incoming[right]=left
    plans=[];unchanged=[];modifications=[];parameters=[];assessments=[]
    with TemporaryDirectory(prefix='nasolve-outgoing-prepare-') as temporary:
        work=Path(temporary)
        for context in contexts:
            site=context['site'];selection=_selection(site,code)
            if context.get('incoming_site')!=incoming.get(site) or context.get('outgoing_site')!=outgoing.get(site):
                raise ValueError('Explicit site context differs from declared native links: '+site)
            five,three=context.get('five_prime_state'),context.get('three_prime_state')
            if (five not in ({'linked'} if site in incoming else {'free_OH','phosphate'})
                    or three!=('linked' if site in outgoing else 'free_OH')
                    or context.get('symmetry_operation') not in {None,'x,y,z'} or context.get('experimental_passthrough')):
                raise ValueError('Unsupported explicit backbone/end context: '+site)
            if site not in outgoing:
                unchanged.append(site);continue
            if five=='free_OH':raise ValueError('Free 5prime treatment requires its separate terminal preparation')
            if not {'P','OP1','OP2',"O5'","C3'","O3'"}<=atoms.keys():
                raise ValueError('Unsupported standard phosphodiester atom convention')
            baseline_removed={'OP3'} & atoms.keys() if site in incoming else set()
            before=_prune(values,set(baseline_removed),outgoing=False)
            before_path=work/('baseline_projected_'+site.replace(':','_')+'.cif')
            before_path.write_text(_render(before,code))
            checks=definition_projection_checks(native,{site:(before_path,code)})
            if any(c['status']!='PASS' for c in checks):
                raise ValueError('Curated source projection differs from captured native rows: '+site)
            hydrogens=hydrogen_neighbors(before,"O3'")
            if not hydrogens:
                unchanged.append(site);continue
            bonds=list(zip(before.get('_chem_comp_bond.atom_id_1',[]),before.get('_chem_comp_bond.atom_id_2',[])))
            def neighbors(name):return [b if a==name else a for a,b in bonds if name in {a,b}]
            o3_bonds=[i for i,(a,b) in enumerate(bonds) if "O3'" in {a,b}]
            bond_types=before.get('_chem_comp_bond.type',[])
            if (len(hydrogens)!=1 or len(neighbors("O3'"))!=2 or set(neighbors("O3'"))!={"C3'",hydrogens[0]}
                    or neighbors(hydrogens[0])!=["O3'"] or atoms["O3'"]['type_symbol']!='O'
                    or atoms["O3'"]['type_energy']!='OH1' or atoms["C3'"]['type_symbol']!='C'
                    or len(bond_types)!=len(bonds) or any(bond_types[i].lower() not in {'single','sing'} for i in o3_bonds)):
                raise ValueError('Unsupported source hydroxyl graph or typing: '+site)
            if set(hydrogens)&inventory[site]['atoms']:
                raise ValueError('Correction would remove an existing coordinate hydrogen: '+site)
            after=_prune(before,set(hydrogens),outgoing=True)
            after['_chem_comp_atom.type_energy'][after['_chem_comp_atom.atom_id'].index("O3'")]=authority['type_energy']
            projected=work/('projected_'+site.replace(':','_')+'.cif');projected.write_text(_render(after,code))
            identifier='NALO'+sha256((sha256(payloads[0]).hexdigest()+'|'+authority['native_receipt_sha256']+'|'+
                json.dumps(context,sort_keys=True)).encode()).hexdigest()[:10]
            operations=[('delete',hydrogens[0],'.'),('change',"O3'",authority['type_energy'])]
            mod={'data_':'mod_'+identifier}
            for field,column in {'mod_id':[identifier]*2,'function':[r[0] for r in operations],
                'atom_id':[r[1] for r in operations],'new_atom_id':['.']*2,'new_type_symbol':['.']*2,
                'new_type_energy':[r[2] for r in operations],'new_partial_charge':['.']*2}.items():
                mod['_chem_mod_atom.'+field]=column
            modifications.append(_emit(mod))
            parameters.append('refinement.pdb_interpretation.apply_cif_modification {\n'
                f'  data_mod = {identifier}\n  residue_selection = {selection}\n}}\n')
            prior=mappings[site].get('chem_mod_ids',{})
            if prior.get('status')!='RECORDED' or not isinstance(prior.get('ids'),list):
                raise ValueError('Prior native modification IDs are unavailable: '+site)
            plan={**dict(context),**projection_site_plan(projected,code,site),'selection':selection,
                'modification_id':identifier,'prior_modification_ids':sorted(prior['ids']),
                'deleted_atoms':hydrogens,'existing_projection_deletions':sorted(baseline_removed),
                'retained_op2_hydrogens':hydrogen_neighbors(after,'OP2'),
                'outgoing_correction':{'oxygen':"O3'",'before_type':'OH1','after_type':authority['type_energy'],
                    'deleted_hydrogen_elements':[atoms[n]['type_symbol'] for n in hydrogens],
                    'native_receipt_sha256':authority['native_receipt_sha256'],
                    'retained_formal_and_partial_charges':'UNCHANGED','new_numerical_targets':[]},
                'baseline_projection_checks':checks}
            plans.append(plan)
            assessments.append({'site':site,'before':assess_dictionaries([before_path],stage='outgoing-before'),
                'after':assess_dictionaries([projected],stage='outgoing-candidate')})
        if not plans:raise ValueError('No explicitly linked source hydroxyl requires a correction')
        (work/'site_modifications.cif').write_text('\n'.join(modifications))
        (work/'site_modifications.phil').write_text(''.join(parameters))
        if any(p.read_bytes()!=data for p,data in zip(paths,payloads)):
            raise ValueError('Input changed during outgoing preparation')
        verified=load_outgoing_authority(paths[2],paths[1],expected_links,authority_site)
        if verified['native_receipt_sha256']!=authority['native_receipt_sha256']:
            raise ValueError('Captured native authority changed during preparation')
        receipt={'schema_version':1,'audit_kind':'cif_outgoing_site_preparation',
            'policy_id':OUTGOING_PREPARATION_POLICY,'status':'PREPARED_REVIEW','component':code,
            'inputs':[{'name':p.name,'sha256':sha256(data).hexdigest(),'size':len(data)} for p,data in zip(paths,payloads)],
            'contexts':list(contexts),'sites':plans,'unchanged_sites':sorted(unchanged),
            'outgoing_type_authority':{k:v for k,v in authority.items() if k!='native'},
            'projected_assessments':assessments,'source_preserved':True,
            'outputs':{p.name:{'path':p.name,'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
                for p in sorted(work.iterdir())},
            'numerical_target_policy':'Retain every row not referencing the deleted hydrogen; copy no targets or partial charges.',
            'automatic_adoption':False,'native_validation':'NOT_RUN','model_editing':'NOT_RUN',
            'experimental_protonation':'UNASSESSED','scientific_approval':'NOT_RUN'}
        output.parent.mkdir(parents=True,exist_ok=True)
        output.mkdir()
        for p in work.iterdir():shutil.copyfile(p,output/p.name)
        (output/'preparation_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return receipt
