"""Explicit 5'-hydroxyl candidates using captured installed native parameters.

The existing linked preparation remains the base authority. Only declared free
5'-OH sites receive a native numerical fragment; added-H formal charge stays
unknown because native partial charge is not formal-charge evidence.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Sequence

from .cif_doctor import assess_dictionaries
from .cif_linked_preparation import (
    _prune, _render, atom_rows, component_values, hydrogen_neighbors,
    prepare_linked_component,
)
from .ligand_profiles import _blocks, _emit

TERMINAL_PREPARATION_POLICY = 'cif-native-five-prime-hydroxyl-v1'


def _safe(name):
    return isinstance(name,str) and not name.startswith('/') and '\\' not in name and ':' not in name and all(
        part not in {'','.','..'} for part in name.split('/'))


def load_terminal_recipe(path: Path) -> dict:
    """Require successful, preserved native evidence and its exact anchored report."""
    path=Path(path);payload=path.read_bytes();receipt=json.loads(payload)
    if (receipt.get('schema_version')!=1 or receipt.get('audit_kind')!='cif_native_terminal_resource_inventory'
            or receipt.get('policy_id')!='cif-installed-terminal-resources-v2'
            or receipt.get('status')!='REVIEW' or receipt.get('execution',{}).get('status')!='COMPLETED'
            or receipt['execution'].get('returncode')!=0):
        raise ValueError('Require a completed reviewed native terminal-resource receipt')
    outputs=receipt.get('outputs',[])
    if not any(row.get('path')=='native_resources.json' for row in outputs):
        raise ValueError('Missing exact native resource artifact')
    for row in outputs:
        if row.get('anchor')!='native_directory' or not _safe(row.get('path')):
            raise ValueError('Unsupported native resource anchor/path')
        file=path.parent/PurePosixPath(row['path'])
        if file.is_symlink() or not file.resolve().is_relative_to(path.parent.resolve()):
            raise ValueError('Native resource path escapes its receipt directory')
        data=file.read_bytes()
        if sha256(data).hexdigest()!=row.get('sha256') or len(data)!=row.get('size'):
            raise ValueError('Native resource artifact changed')
    native=receipt.get('native_resources',{})
    if json.loads((path.parent/'native_resources.json').read_text())!=native:
        raise ValueError('Native resource report disagrees with its receipt')
    if (native.get('policy_id')!=receipt['policy_id'] or native.get('status')!='REVIEW'
            or not native.get('source_files') or not native.get('api_sources')
            or any(row.get('preserved_after_capture') is not True for row in native['source_files'])):
        raise ValueError('Require preserved native numerical-source evidence')
    control=native.get('canonical_control',{})
    if (control.get('base_preserved') is not True or control.get('applied_modification_ids')!=['5*END']
            or any(control.get(state,{}).get('metadata',{}).get('group')!='DNA' for state in ['base','effective'])):
        raise ValueError('Require a preserved canonical DNA terminal control')
    mod=native.get('modifications',{}).get('5*END',{})
    if (mod.get('metadata',{}).get('id')!='5*END' or len(mod.get('atoms',[]))!=5
            or any(mod.get(category) for category in ['torsions','chirality','plane_atoms'])):
        raise ValueError('Unsupported native terminal modification shape')
    deleted=[r.get('atom_id') for r in mod['atoms'] if r.get('function')=='delete']
    changed=[r for r in mod['atoms'] if r.get('function')=='change']
    added=[r for r in mod['atoms'] if r.get('function')=='add']
    if set(deleted)!={'P','OP1','OP2'} or len(deleted)!=3 or len(changed)!=1 or len(added)!=1:
        raise ValueError('Unsupported native terminal atom operations')
    oxygen,hydrogen=changed[0],added[0];name=hydrogen.get('new_atom_id')
    if (oxygen.get('atom_id')!="O5'" or oxygen.get('new_atom_id') not in {None,'',"O5'"}
            or oxygen.get('new_type_symbol') not in {None,'','O'}
            or hydrogen.get('new_type_symbol')!='H' or not isinstance(name,str)
            or not name or name in {'.','?'}
            or any(row.get('new_type_energy') in {None,'','.','?'} for row in [oxygen,hydrogen])):
        raise ValueError('Unsupported native hydroxyl identity or typing')
    if len(mod.get('bonds',[]))!=1 or len(mod.get('angles',[]))!=1:
        raise ValueError('Require exactly one explicit native hydroxyl bond and angle')
    bond,angle=mod['bonds'][0],mod['angles'][0]
    if (bond.get('function')!='add' or bond.get('new_type')!='single' or {bond.get('atom_id_1'),bond.get('atom_id_2')}!={"O5'",name}
            or angle.get('function')!='add' or angle.get('atom_id_2')!="O5'"
            or {angle.get('atom_id_1'),angle.get('atom_id_3')}!={"C5'",name}):
        raise ValueError('Native terminal numerical references differ')
    for row,keys in [(bond,['new_value_dist','new_value_dist_esd','new_value_dist_neutron']),
                     (angle,['new_value_angle','new_value_angle_esd'])]:
        if any(not isfinite(float(row[k])) or float(row[k])<=0 for k in keys):
            raise ValueError('Require finite positive native hydroxyl targets/uncertainties')
    for row in [oxygen,hydrogen]:
        if not isfinite(float(row['new_partial_charge'])):raise ValueError('Native partial charge is nonfinite')
    effective=control['effective'];actual={r['atom_id']:r for r in effective['atoms']}
    if any(actual.get(atom,{}).get('type_energy')!=row['new_type_energy']
           for atom,row in [("O5'",oxygen),(name,hydrogen)]):
        raise ValueError('Native canonical control does not demonstrate the hydroxyl types')
    expected_bond={k.removeprefix('new_'):v for k,v in bond.items() if k!='function'}
    expected_angle={k.removeprefix('new_'):v for k,v in angle.items() if k!='function'}
    if expected_bond not in effective['bonds'] or expected_angle not in effective['angles']:
        raise ValueError('Native canonical control does not demonstrate the exact hydroxyl targets')
    return {'policy_id':TERMINAL_PREPARATION_POLICY,'resource_receipt_sha256':sha256(payload).hexdigest(),
        'resource_policy_id':receipt['policy_id'],'phenix_version':receipt['phenix_version'],
        'modification_id':'5*END','oxygen':oxygen,'hydrogen':hydrogen,'bond':bond,'angle':angle,
        'source_files':native['source_files'],'api_sources':native['api_sources'],
        'added_hydrogen_formal_charge':'UNASSESSED','partial_charge_substituted_for_formal_charge':False}


def _append(values,category,row):
    prefix=category+'.';fields=[k for k in values if k.startswith(prefix)]
    size=len(values[fields[0]]) if fields else 0
    for name in row:
        if prefix+name not in values:values[prefix+name]=['.']*size
    for key in [k for k in values if k.startswith(prefix)]:
        value=row.get(key[len(prefix):],'.')
        values[key].append('.' if value is None or value=='' else str(value))


def _change(values,category,identifier,row):
    prefix=category+'.';size=len(values[prefix+'atom_id'])
    index=values[prefix+'atom_id'].index(identifier)
    for key,value in row.items():
        if prefix+key not in values:values[prefix+key]=['.']*size
        values[prefix+key][index]=str(value)


def _adapt_projection(values,code,recipe):
    atoms=atom_rows(values);name=recipe['hydrogen']['new_atom_id']
    if name in atoms:raise ValueError('Native hydroxyl hydrogen identity collides with a source atom')
    if atoms.get("O5'",{}).get('type_symbol')!='O' or atoms.get("C5'",{}).get('type_symbol')!='C':
        raise ValueError('Require the declared carbon/oxygen hydroxyl endpoints')
    bonds=list(zip(values.get('_chem_comp_bond.atom_id_1',[]),values.get('_chem_comp_bond.atom_id_2',[])))
    neighbors={b if a=="O5'" else a for a,b in bonds if "O5'" in {a,b}}
    if neighbors!={"C5'"}:raise ValueError('Free O5 endpoint has unsupported adjacency')
    oxygen,hydrogen=recipe['oxygen'],recipe['hydrogen']
    _change(values,'_chem_comp_atom',"O5'",{'type_energy':oxygen['new_type_energy'],'partial_charge':oxygen['new_partial_charge']})
    _append(values,'_chem_comp_atom',{'comp_id':code,'atom_id':name,'type_symbol':'H',
        'type_energy':hydrogen['new_type_energy'],'partial_charge':hydrogen['new_partial_charge']})
    # Preserve all existing formal charges. The native source supplies partial
    # charges only, so the new H remains explicitly unknown in each formal field.
    for field in ['charge','pdbx_formal_charge']:
        if '_chem_comp_atom.'+field in values:values['_chem_comp_atom.'+field][-1]='?'
    _append(values,'_chem_comp_bond',{'comp_id':code,**{k.removeprefix('new_'):v
        for k,v in recipe['bond'].items() if k!='function'}})
    _append(values,'_chem_comp_angle',{'comp_id':code,**{k.removeprefix('new_'):v
        for k,v in recipe['angle'].items() if k!='function'}})
    return _prune(values,set(),outgoing=False)


def prepare_terminal_component(source: Path, numerical: Path, model: Path,
        contexts: Sequence[dict], resource_receipt: Path, output_directory: Path, *, code: str,
        native_qualification: dict | None = None,
        bond_representation_policy: str | None = None) -> dict:
    """Prepare selected free 5'-OH sites without changing internal/phosphate contexts."""
    paths=[Path(p) for p in [source,numerical,model,resource_receipt]]
    payloads=[p.read_bytes() for p in paths];output=Path(output_directory)
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    if any(output.resolve()==p.resolve() or p.parent.resolve() in output.resolve().parents for p in paths):
        raise ValueError('Terminal output must be outside preserved input directories')
    if not any(c.get('five_prime_state')=='free_OH' for c in contexts):
        raise ValueError('Require at least one explicitly declared free_OH site')
    recipe=load_terminal_recipe(paths[3]);name=recipe['hydrogen']['new_atom_id']
    if name in atom_rows(component_values(paths[1],code)):
        raise ValueError('Native hydroxyl hydrogen identity collides with a source atom')
    with TemporaryDirectory(prefix='nasolve-terminal-prepare-') as temporary:
        work=Path(temporary)/'linked'
        options={}
        if native_qualification is not None:options['native_qualification']=native_qualification
        if bond_representation_policy is not None:options['bond_representation_policy']=bond_representation_policy
        result=prepare_linked_component(*paths[:3],contexts,work,code=code,**options)
        blocks=_blocks(work/'site_modifications.cif');replacements={}
        assessments=[]
        for plan in result['sites']:
            site=plan['site'];projected=work/('projected_'+site.replace(':','_')+'.cif')
            if plan['five_prime_state']=='free_OH':
                values=_adapt_projection(component_values(projected,code),code,recipe)
                old_id=plan['modification_id']
                new_id='NAOH'+sha256((old_id+'|'+recipe['resource_receipt_sha256']).encode()).hexdigest()[:10]
                mod=deepcopy(next(b.values for b in blocks if b.values['data_']=='mod_'+old_id))
                mod['data_']='mod_'+new_id
                mod['_chem_mod_atom.mod_id']=[new_id]*len(mod['_chem_mod_atom.mod_id'])
                for operation in [recipe['oxygen'],recipe['hydrogen']]:
                    _append(mod,'_chem_mod_atom',{'mod_id':new_id,**operation})
                _append(mod,'_chem_mod_bond',{'mod_id':new_id,**recipe['bond']})
                _append(mod,'_chem_mod_angle',{'mod_id':new_id,**recipe['angle']})
                replacements[old_id]=(new_id,_emit(mod))
                actual=atom_rows(values)
                plan.update(modification_id=new_id,expected_atoms=sorted(actual),
                    expected_energy_types={n:r.get('type_energy') for n,r in actual.items()},
                    expected_formal_charges={n:r.get('charge',r.get('pdbx_formal_charge')) for n,r in actual.items()},
                    expected_hydrogen_attachments={n:sorted(b if a==n else a for a,b in zip(
                        values['_chem_comp_bond.atom_id_1'],values['_chem_comp_bond.atom_id_2']) if n in {a,b})
                        for n,r in actual.items() if r['type_symbol'].upper() in {'H','D'}},
                    terminal_hydroxyl={'hydrogen':name,'oxygen':"O5'",'resource_receipt_sha256':recipe['resource_receipt_sha256'],
                        'bond':{k.removeprefix('new_'):v for k,v in recipe['bond'].items() if k!='function'},
                        'angle':{k.removeprefix('new_'):v for k,v in recipe['angle'].items() if k!='function'},
                        'new_hydrogen_formal_charge':'UNASSESSED'})
                projected.write_text(_render(values,code))
            assessment=assess_dictionaries([projected],stage='native-terminal-projection')
            if assessment['status']=='INVALID':raise ValueError('Invalid projected terminal dictionary: '+site)
            assessments.append({'site':site,'assessment':assessment})
        (work/'site_modifications.cif').write_text('\n'.join(
            replacements[b.values['data_'][4:]][1] if b.values['data_'][4:] in replacements else b.text for b in blocks))
        phil=(work/'site_modifications.phil').read_text()
        for old_id,(new_id,_) in replacements.items():phil=phil.replace('data_mod = '+old_id+'\n','data_mod = '+new_id+'\n')
        (work/'site_modifications.phil').write_text(phil)
        if any(p.read_bytes()!=data for p,data in zip(paths,payloads)) or load_terminal_recipe(paths[3])!=recipe:
            raise ValueError('Preserved terminal input changed')
        policy='cif-native-five-prime-hydroxyl-v2' if native_qualification is not None or bond_representation_policy is not None else TERMINAL_PREPARATION_POLICY
        result.update(policy_id=policy,linked_preparation_policy=result['policy_id'],
            terminal_resource=recipe,projected_assessments=assessments,
            inputs=[{'name':p.name,'sha256':sha256(data).hexdigest(),'size':len(data)} for p,data in zip(paths,payloads)])
        output.mkdir(parents=True)
        for path in work.iterdir():
            if path.name=='preparation_receipt.json':continue
            with (output/path.name).open('xb') as handle:handle.write(path.read_bytes())
        for key,row in result['outputs'].items():
            data=(output/row['path']).read_bytes();row.update(sha256=sha256(data).hexdigest(),size=len(data))
        result['source_preserved']=all(p.read_bytes()==data for p,data in zip(paths,payloads)) and load_terminal_recipe(paths[3])==recipe
        if not result['source_preserved']:raise ValueError('Preserved terminal input changed during publication')
        with (output/'preparation_receipt.json').open('x') as handle:
            json.dump(result,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')
        return result
