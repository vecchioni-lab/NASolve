"""Explicit source-preserving DNA derivatives selected by declared connectivity.

These candidates are diagnostic inputs, never an implicit PostMR repair or
adoption. Chemical source and numerical dictionary remain separate authorities.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Sequence

from .cif_doctor import assess_dictionaries
from .cif_generation import inspect_component_generation
from .ligand_profiles import _blocks, _emit, _emit_component_list, COMPONENT_LIST_POLICY

LINKED_PREPARATION_POLICY = 'cif-source-preserving-linked-sites-v1'
MODIFICATION_BLOCK_POLICY = 'cif-native-modification-blocks-v1'
_ATOM = '_chem_comp_atom.'
_BOND = '_chem_comp_bond.'
_MISSING = {'', '.', '?'}


def component_values(path: Path, code: str) -> dict:
    """Select exactly one definition by content, including its list metadata."""
    metadata, definitions = [], []
    for block in _blocks(Path(path)):
        values = block.values
        ids = values.get('_chem_comp.id', [])
        if code in ids:
            if ids.count(code) != 1:
                raise ValueError('Ambiguous component metadata: '+code)
            index = ids.index(code)
            metadata.append({key: [column[index]] for key,column in values.items()
                             if key.startswith('_chem_comp.') and len(column)==len(ids)})
        codes = set(values.get(_ATOM+'comp_id', []))
        if code in codes:
            if codes != {code}:
                raise ValueError('Mixed-component atom block needs explicit preparation')
            definitions.append(deepcopy(values))
    if len(definitions)!=1 or len(metadata)!=1:
        raise ValueError('Require one exact component definition and metadata: '+code)
    result=definitions[0]
    result.update(metadata[0])
    return result


def atom_rows(values: dict) -> dict[str, dict]:
    fields={key[len(_ATOM):]:column for key,column in values.items() if key.startswith(_ATOM)}
    ids=fields.get('atom_id', [])
    if not ids or len(ids)!=len(set(ids)) or any(len(v)!=len(ids) for v in fields.values()):
        raise ValueError('Invalid or ambiguous atom inventory')
    return {name:{key:column[i] for key,column in fields.items()} for i,name in enumerate(ids)}


def hydrogen_neighbors(values: dict, heavy: str) -> list[str]:
    atoms=atom_rows(values)
    neighbors=[]
    for a,b in zip(values.get(_BOND+'atom_id_1',[]),values.get(_BOND+'atom_id_2',[])):
        other=b if a==heavy else a if b==heavy else None
        if other is not None and atoms.get(other,{}).get('type_symbol','').upper() in {'H','D'}:
            neighbors.append(other)
    return sorted(set(neighbors))


def _prune(values: dict, removed: set[str], *, outgoing: bool) -> dict:
    result=deepcopy(values)
    categories={key.split('.')[0] for key in result if key.startswith('_chem_comp_') and '.' in key}
    for category in categories:
        fields={key:column for key,column in result.items() if key.startswith(category+'.')}
        sizes={len(column) for column in fields.values()}
        if len(sizes)!=1: raise ValueError('Ragged component category: '+category)
        count=next(iter(sizes))
        references=[key for key in fields if key.split('.')[1].startswith('atom_id')
                    or key.split('.')[1] in {'atom_back','atom_forward'}]
        keep=[i for i in range(count) if not any(fields[key][i] in removed for key in references)]
        for key,column in fields.items():
            if keep: result[key]=[column[i] for i in keep]
            else: result.pop(key)
    if outgoing:
        index=result[_ATOM+'atom_id'].index("O3'")
        result[_ATOM+'type_energy'][index]='OC2'
    remaining=atom_rows(result)
    for field,count in [('number_atoms_all',len(remaining)),
                        ('number_atoms_nh',sum(row['type_symbol'].upper() not in {'H','D'} for row in remaining.values()))]:
        if '_chem_comp.'+field in result: result['_chem_comp.'+field]=[str(count)]
    return result


def _model_inventory(model: Path) -> dict:
    residues={}
    for line in model.read_text().splitlines():
        if not line.startswith(('ATOM  ','HETATM')): continue
        if line[16:17].strip() or line[26:27].strip():
            raise ValueError('Alternate conformers/insertion codes need a reviewed selector')
        site=(line[21:22].strip() or '_')+':'+line[22:26].strip()
        row=residues.setdefault(site,{'code':line[17:20].strip(),'atoms':set()})
        if row['code']!=line[17:20].strip() or line[12:16].strip() in row['atoms']:
            raise ValueError('Ambiguous model site: '+site)
        row['atoms'].add(line[12:16].strip())
    return residues


def _construction_inventory(model, source, code, contexts, targets):
    """View only canonical scaffold atoms when projecting a future component.

    This does not rename/write a model or assess canonical base geometry. The
    real constructed model must later pass ordinary site/native qualification.
    """
    from collections.abc import Mapping
    from .postmr_restoration import source_graph_fragment, _atom_records
    if (not isinstance(targets, Mapping) or not targets
            or set(targets) != {c['site'] for c in contexts}
            or any(not isinstance(v,str) or v not in {'DA','DC','DG','DT'} for v in targets.values())):
        raise ValueError('Construction projections require exact canonical input identities for every context')
    inventory = _model_inventory(model)
    if any(row['code'] == code for row in inventory.values()):
        raise ValueError('Construction projection requires canonical inputs, not an already constructed target')
    graph = source_graph_fragment(source, code)
    lines = model.read_text().splitlines(keepends=True)
    proof = []
    for site, before in targets.items():
        _selection(site, code)
        if site not in inventory or inventory[site]['code'] != before:
            raise ValueError('Canonical construction input identity differs at ' + site)
        chain, resid = site.split(':')
        atoms = _atom_records([line for line in lines if line[:6] in {'ATOM  ','HETATM'}
            and (line[21:22].strip() or '_') == chain and line[22:26].strip() == resid], before)
        protected = (set(graph['sugar_atoms']) | {'P','OP1','OP2','OP3'}) & atoms.keys()
        if (not protected <= set(graph['scaffold_atoms'])
                or not set(graph['sugar_atoms']) <= protected
                or any(atoms[n]['element'] != graph['elements'][n] for n in protected)
                or any("'" in n and n not in graph['sugar_atoms'] for n in atoms)
                or any(n != atoms[n]['line'][12:16].strip() for n in atoms)):
            raise ValueError('Unsupported canonical sugar/backbone inventory at ' + site)
        inventory[site] = {'code': code, 'atoms': protected}
        proof.append(dict(site=site, before=before, after=code,
            protected_atoms=sorted(protected)))
    return inventory, dict(policy_id='cif-canonical-construction-context-v1',
        scope='PRECONSTRUCTION_ONLY', targets=sorted(proof,key=lambda r:r['site']),
        model_sha256=sha256(model.read_bytes()).hexdigest(),
        source_sha256=sha256(source.read_bytes()).hexdigest(),
        canonical_base_geometry='NOT_ASSESSED', constructed_model='NOT_CREATED')


def _selection(site: str, code: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_]:-?[0-9]+',site) or not re.fullmatch(r'[A-Za-z0-9]{1,3}',code):
        raise ValueError('Unsupported explicit PDB selector')
    chain,resid=site.split(':')
    return "chain '{}' and resid {} and resname {}".format('' if chain=='_' else chain,resid,code)


def _render(values: dict, code: str) -> str:
    metadata={key:column for key,column in values.items() if key.startswith('_chem_comp.')}
    if not metadata or any(len(column)!=1 for column in metadata.values()):
        raise ValueError('Require one exact component metadata row')
    list_block = _emit_component_list(metadata)
    definition={'data_':'comp_'+code,**{key:column for key,column in values.items()
                                      if key!='data_' and not key.startswith('_chem_comp.')}}
    return list_block+'\n'+_emit(definition)


def prepare_linked_component(source: Path, numerical: Path, model: Path,
                             contexts: Sequence[dict], output_directory: Path, *, code: str,
                             native_qualification: dict | None = None,
                             bond_representation_policy: str | None = None,
                             phosphate_atom_policy: str | None = None,
                             construction_targets: dict[str, str] | None = None) -> dict:
    """Prepare a DNA base dictionary, site modifiers and projected assessments.

    Links and end states are explicit caller evidence, never guessed from a
    residue code, adjacency, or spatial contact. Source-state loss must first be
    resolved by independent whole-component generation. OP2 protonation is
    preserved. Outgoing O3' uses the previously reviewed native OC2 type.
    Optional construction_targets maps every selected site to its actual canonical
    input code. Only its verified sugar/phosphate inventory enters projection;
    the input is never relabelled or treated as an already constructed residue.
    This explicit mode requires isolated qualification and later actual-model
    site/native checks, and does not assess the canonical base geometry.
    """
    paths=[Path(source),Path(numerical),Path(model)]
    payloads=[p.read_bytes() for p in paths]
    output=Path(output_directory)
    if output.exists() or output.is_symlink(): raise FileExistsError(output)
    if any(output.resolve()==p.resolve() or p.parent.resolve() in output.resolve().parents for p in paths):
        raise ValueError('Preparation output must be outside every preserved input directory')
    source_values=component_values(paths[0],code)
    type_tokens=source_values.get('_chem_comp.type', [])
    qualified=native_qualification is not None
    binding=None
    if bond_representation_policy is not None:
        from .cif_preparation_qualification import bind_preparation_qualification
        binding=bind_preparation_qualification(paths[0],paths[1],code,native_qualification,
            bond_representation_policy=bond_representation_policy)
        q=native_qualification;fresh=binding['candidate_reassessment']
    elif qualified:
        from .cif_candidate_usability import reassess_complete_candidate,POLICY_ID
        q=native_qualification;fresh=reassess_complete_candidate(paths[0],paths[1],code)
        if (q.get('policy_id')!=POLICY_ID or q.get('native_usable') is not True
                or q.get('component')!=code or q.get('scope')!='ISOLATED_COMPONENT_ONLY' or not q.get('checks')
                or any(v is not True for v in q['checks'].values())
                or q.get('candidate_sha256')!=sha256(payloads[1]).hexdigest()
                or q.get('source_assessment',{}).get('finished_stereo',{}).get('source_sha256')!=sha256(payloads[0]).hexdigest()
                or fresh['candidate_status']!='CANDIDATE_REVIEW'):
            raise ValueError('Require bound independently usable source-preserving candidate evidence')
    if qualified:
        # The explicit isolated bridge also accepts a legacy monomer DNA group.
        # Existing unqualified callers keep their stricter type-only contract.
        if not type_tokens:
            from .cif_source_classification import _source_declarations
            _source_declarations(paths[0],code)
    if binding is not None and type_tokens:
        # Missing type was already validated through the qualified legacy DNA
        # declaration above; an explicit type must still agree with the group.
        # CCD declares L-DNA linking separately. Native group DNA selects the
        # polymer machinery; the bound source graph/configuration owns its hand.
        group=source_values.get('_chem_comp.group',[])
        if (len(type_tokens)!=1 or type_tokens[0].strip().upper() not in {'DNA LINKING','L-DNA LINKING'}
                or len(group)>1 or (group and group[0].strip().upper() not in {'DNA','','.','?'})):
            raise ValueError('Require explicit consistent source DNA or L-DNA LINKING metadata')
    elif (len(type_tokens)!=1 or type_tokens[0].upper()!='DNA LINKING') and not (qualified and not type_tokens):
        raise ValueError('Require explicit source DNA LINKING metadata')
    options={} if bond_representation_policy is None else {'bond_representation_policy':bond_representation_policy}
    inspection=inspect_component_generation(paths[0],paths[1],code,**options)
    if inspection['status']!='CANDIDATE_REVIEW' and not qualified:
        raise ValueError('Require a source-preserving complete numerical candidate: '+', '.join(inspection['rejection_reasons']))
    values=component_values(paths[1],code)
    original_group=values.get('_chem_comp.group')
    values['_chem_comp.group']=['DNA']
    atoms=atom_rows(values)
    from .cif_anionic_phosphate import POLICY_ID as anionic_policy, verify_anionic_projection
    anionic = phosphate_atom_policy == anionic_policy
    if anionic and binding is None:
        raise ValueError("The anionic phosphate operation requires explicit source-bound native qualification")
    aliases = {'OP1':'OP1', 'OP2':'OP2', 'OP3':'OP3'}
    if phosphate_atom_policy is not None:
        from .cif_phosphate_names import POLICY_ID, phosphate_names
        if phosphate_atom_policy not in (POLICY_ID, anionic_policy) or not qualified:
            raise ValueError('Source-named phosphate preparation requires explicit policy and isolated qualification')
        aliases = phosphate_names(values)
        if phosphate_names(source_values) != aliases:
            raise ValueError('Source and numerical phosphate names differ')
        if not contexts or any(not c.get('incoming_site') for c in contexts):
            raise ValueError('Source-named phosphate adapter currently requires internal linked sites')
        if binding is None:
            from .cif_preparation_qualification import qualify_native_backbone_ports
            for context in contexts:
                qualify_native_backbone_ports(values, context, phosphate_names=aliases)
    p1,p2,p3 = (aliases[n] for n in ('OP1','OP2','OP3'))
    required={'P',p1,p2,"O5'","C5'","C3'","O3'"}
    if not required<=atoms.keys() or (phosphate_atom_policy is None and 'O3P' in atoms):
        raise ValueError('Unsupported standard-phosphodiester atom convention')
    bonds={frozenset((a,b)) for a,b in zip(values[_BOND+'atom_id_1'],values[_BOND+'atom_id_2'])}
    if not all(frozenset(pair) in bonds for pair in [('P',p1),('P',p2),('P',"O5'"),("O3'","C3'")]):
        raise ValueError('Selected graph does not support standard phosphodiester chemistry')
    construction = None
    if construction_targets is not None:
        if not qualified or phosphate_atom_policy is not None:
            raise ValueError('Construction projections require isolated qualification and standard phosphate names')
        model_sites, construction = _construction_inventory(paths[2], paths[0], code, contexts, construction_targets)
    else:
        model_sites=_model_inventory(paths[2])
    if not contexts: raise ValueError('Require explicit site contexts')
    if {context['site'] for context in contexts}!={site for site,row in model_sites.items() if row['code']==code}:
        raise ValueError('Require declared contexts for every model site sharing the component code')
    seen=set();plans=[];projected=[];mod_rows=[];phil=[]
    for context in contexts:
        site=context['site']; selection=_selection(site,code)
        if site in seen: raise ValueError('Duplicate site context: '+site)
        seen.add(site)
        if context.get('symmetry_operation') not in {None,'x,y,z'} or context.get('experimental_passthrough'):
            raise ValueError('Unsupported symmetry or experimental backbone context')
        if site not in model_sites or model_sites[site]['code']!=code:
            raise ValueError('Site context differs from model identity: '+site)
        incoming,outgoing=context.get('incoming_site'),context.get('outgoing_site')
        five,three=context.get('five_prime_state'),context.get('three_prime_state')
        if five not in ({'linked'} if incoming else {'free_OH','phosphate'}) or three!=('linked' if outgoing else 'free_OH'):
            raise ValueError('Explicit links and terminal states disagree: '+site)
        for endpoint,atom in [(incoming,"O3'"),(outgoing,'P')]:
            if endpoint and (endpoint==site or endpoint not in model_sites or atom not in model_sites[endpoint]['atoms']):
                raise ValueError('Declared link endpoint absent or self-linked: '+site)
        coordinate_atoms=model_sites[site]['atoms']
        phosphate={'P',p1,p2,p3}
        if phosphate_atom_policy is None and 'O3P' in coordinate_atoms: raise ValueError('Unrequested coordinate O3P')
        if five=='free_OH':
            if coordinate_atoms & phosphate: raise ValueError('Free 5prime OH contains a phosphate: '+site)
        elif five=='phosphate':
            if not phosphate<=coordinate_atoms: raise ValueError('Requested terminal phosphate is incomplete: '+site)
        elif not {'P',p1,p2}<=coordinate_atoms or {p3,'OP3','O3P'} & coordinate_atoms:
            raise ValueError('Internal coordinate phosphate is incomplete or contains OP3: '+site)
        port_qualification=None
        if binding is not None:
            from .cif_preparation_qualification import qualify_native_backbone_ports
            port_qualification=qualify_native_backbone_ports(values,context,phosphate_names=aliases if phosphate_atom_policy is not None else None, anionic_leaving=anionic)
            if anionic:
                source_port = qualify_native_backbone_ports(source_values, context, phosphate_names=aliases, anionic_leaving=True)
                if source_port != port_qualification:
                    raise ValueError("Source and numerical phosphate reaction states differ")
        removed=set()
        if incoming:
            if p3 in atoms:
                heavy_neighbors={next(iter(pair-{p3})) for pair in bonds if p3 in pair
                                 and atoms[next(iter(pair-{p3}))]['type_symbol'].upper() not in {'H','D'}}
                if heavy_neighbors!={'P'}: raise ValueError('OP3 has unsupported heavy-atom adjacency')
                removed.add(p3);removed.update(hydrogen_neighbors(values,p3))
        elif five=='free_OH':
            removed.update(phosphate & atoms.keys())
            for name in phosphate: removed.update(hydrogen_neighbors(values,name))
        if outgoing: removed.update(hydrogen_neighbors(values,"O3'"))
        derivative=_prune(values,removed,outgoing=bool(outgoing))
        actual=atom_rows(derivative)
        configuration_projection=None
        if binding is not None:
            from .cif_preparation_qualification import project_source_configurations
            configuration_projection=project_source_configurations(binding,values,derivative)
        if coordinate_atoms-actual.keys(): raise ValueError('Preparation would remove an existing coordinate atom: '+site)
        mod_id='NASL'+sha256((code+'|'+site+'|'+json.dumps(context,sort_keys=True)).encode()).hexdigest()[:10]
        for atom in sorted(removed): mod_rows.append([mod_id,'delete',atom,'.','.','.','.'])
        if outgoing: mod_rows.append([mod_id,'change',"O3'",'.','.','OC2','.'])
        if removed or outgoing:
            phil.append('refinement.pdb_interpretation.apply_cif_modification {\n'
                        f'  data_mod = {mod_id}\n  residue_selection = {selection}\n}}\n')
        else: mod_id=None
        plan={**dict(context),'component':code,'selection':selection,'modification_id':mod_id,
              'deleted_atoms':sorted(removed),'expected_atoms':sorted(actual),
              'expected_energy_types':{name:row.get('type_energy') for name,row in actual.items()},
              'expected_formal_charges':{name:row.get('charge',row.get('pdbx_formal_charge')) for name,row in actual.items()},
              'retained_op2_hydrogens':hydrogen_neighbors(derivative,p2),
              'expected_hydrogen_attachments':{name:sorted(next(iter(pair-{name})) for pair in bonds
                  if name in pair and not pair & removed) for name,row in actual.items()
                  if row['type_symbol'].upper() in {'H','D'}}}
        if anionic:
            plan["formal_charge_projection"] = verify_anionic_projection(values, derivative, context, port_qualification)
        if configuration_projection is not None:
            plan['source_configuration_projection']=configuration_projection
            plan['source_port_qualification']=port_qualification
        plans.append(plan);projected.append((site,derivative))
    if any(p.read_bytes()!=data for p,data in zip(paths,payloads)):
        raise ValueError('Input changed during preparation')
    output.mkdir(parents=True)
    base=output/'base_dictionary.cif';base.write_text(_render(values,code))
    # Native convert_mod_list registers each modification by its mod_ block
    # suffix, not by the mod_id values inside the atom loop. Keep one exact
    # requested ID per block, including mixed contexts for one residue code.
    mod_blocks=[]
    for identifier in sorted({row[0] for row in mod_rows}):
        rows=[row for row in mod_rows if row[0]==identifier]
        mod_values={'data_':'mod_'+identifier}
        for i,field in enumerate(['mod_id','function','atom_id','new_atom_id','new_type_symbol','new_type_energy','new_partial_charge']):
            mod_values['_chem_mod_atom.'+field]=[row[i] for row in rows]
        mod_blocks.append(_emit(mod_values))
    modifications=output/'site_modifications.cif'
    modifications.write_text('\n'.join(mod_blocks) if mod_blocks else 'data_mod_linked_sites\n# No atom modifications required.\n')
    parameters=output/'site_modifications.phil';parameters.write_text(''.join(phil))
    assessments=[]
    for site,derivative in projected:
        candidate=output/('projected_'+site.replace(':','_')+'.cif')
        candidate.write_text(_render(derivative,code))
        assessment=assess_dictionaries([candidate],stage='linked-site-projection')
        if assessment['status']=='INVALID': raise ValueError('Projected linked dictionary is invalid: '+site)
        assessments.append({'site':site,'assessment':assessment})
    receipt={'schema_version':1,'audit_kind':'cif_linked_site_preparation',
             'policy_id':('cif-source-preserving-linked-sites-v3' if binding is not None else
                          'cif-source-preserving-linked-sites-v2' if qualified else LINKED_PREPARATION_POLICY),'status':'PREPARED_REVIEW','component':code,
             'modification_block_policy':MODIFICATION_BLOCK_POLICY,
             'component_list_policy':COMPONENT_LIST_POLICY,
             'inputs':[{'name':p.name,'sha256':sha256(data).hexdigest(),'size':len(data)} for p,data in zip(paths,payloads)],
             'source_preserved':all(p.read_bytes()==data for p,data in zip(paths,payloads)),
             'source_type':type_tokens[0] if type_tokens else 'legacy group DNA','metadata_change':{'field':'_chem_comp.group','before':original_group,'after':['DNA']},
             'candidate_inspection':inspection,'sites':plans,'projected_assessments':assessments,
             'outputs':{key:{'path':p.name,'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
                        for key,p in [('dictionary',base),('modifications',modifications),('parameters',parameters)]},
             'automatic_adoption':False,'native_validation':'NOT_RUN','experimental_protonation':'UNASSESSED'}
    if qualified:
        receipt['isolated_native_qualification']={'policy_id':q['policy_id'],'candidate_sha256':q['candidate_sha256'],
            'source_sha256':sha256(payloads[0]).hexdigest(),'scope':q['scope'],'checks':q['checks']}
        receipt['candidate_reassessment']=fresh
    if binding is not None:
        receipt['preparation_qualification']=binding
    if phosphate_atom_policy is not None:
        receipt['phosphate_atom_policy']=phosphate_atom_policy
        receipt['phosphate_names']=aliases
    if construction is not None:
        receipt['linked_preparation_policy'] = receipt['policy_id']
        receipt['policy_id'] = 'cif-source-preserving-construction-sites-v1'
        receipt['construction_context'] = construction
    if not receipt['source_preserved']: raise ValueError('Input changed while publishing preparation')
    (output/'preparation_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    return receipt
