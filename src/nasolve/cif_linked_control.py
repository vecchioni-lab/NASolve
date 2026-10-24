"""Separate three-residue DNA linkage controls; no scaffold adoption or optimizer."""
from collections import Counter
from hashlib import sha256
from itertools import combinations
import json,math,re
from pathlib import Path

from .cif_construction_provenance import _pdb_inventory
from .cif_effective_source_recovery import _source_definition,mechanics_can_continue
from .cif_fragment_restoration import _SCAFFOLD,_FRAME,_fragment,_frame,_dot,_sub,_model
from .cif_linked_preparation import component_values,atom_rows
from .cif_linked_qualification import _site,native_backbone_links,site_definition_checks
from .cif_terminal_qualification import definition_projection_checks,_proxy_subset,_rows
from .cif_candidate_usability import _torsion_signature,_torsion_weight,energy_inventory_checks
from .cif_fixed_geometry import _fixed_policy
from .cif_stereochemistry_audit import _values,_coordinates,_graph
from .dictionary_compatibility import normalize_torsion_block

POLICY_ID='cif-qualified-dna-linked-control-v1'
SITES=(('A','1'),('A','2'),('A','3'))


def prepare_linked_control_models(frame,numerical,code,output):
    """Keep template backbone coordinates; graft one graph-selected base rigidly.

    The explicitly selected three residues are a synthetic linkage test, not a
    new diffraction model. No numerical dictionary coordinate/target is edited.
    """
    frame,numerical,output=Path(frame),Path(numerical),Path(output)
    if not re.fullmatch(r'[A-Za-z0-9]{1,3}',code):raise ValueError('Unsupported control component code')
    if output.exists() or output.is_symlink():raise FileExistsError(output)
    if any(p.is_symlink() for p in output.parents):raise ValueError('Output parent cannot traverse a symlink')
    if any(p.parent.resolve()==output.resolve() or p.parent.resolve() in output.resolve().parents for p in [frame,numerical]):raise ValueError('Control output must be separate from inputs')
    snapshots=[p.read_bytes() for p in [frame,numerical]];inventory=_pdb_inventory(frame)
    selected={k:r for k,r in inventory.items() if k[:2] in SITES}
    if {k[:2] for k in selected}!=set(SITES) or any(k[2] or k[3] or r['element'] in {'H','D'} for k,r in selected.items()):raise ValueError('Require unambiguous heavy-atom template sites A:1-3')
    if any(r['code'] not in {'DA','DC','DG','DT'} for r in selected.values()):raise ValueError('Require canonical DNA reference sites')
    center={k[-1]:r for k,r in selected.items() if k[:2]==SITES[1]}
    if any(n not in center or center[n]['element']!=e for n,e in _SCAFFOLD.items()):raise ValueError('Require a complete template DNA scaffold')
    if any(k[-1] in {'P','OP1','OP2','OP3','O3P'} for k in selected if k[:2]==SITES[0]):raise ValueError('Reference first residue must have a free 5-prime end')
    values=_values(numerical,code);atoms=atom_rows(values);family,xyz=_coordinates(values,source=False)
    heavy={n:{'element':a['type_symbol'].upper()} for n,a in atoms.items() if a['type_symbol'].upper() not in {'H','D'} and n!='OP3'}
    if set(heavy)-xyz.keys():raise ValueError('Require complete finite numerical heavy-atom coordinates')
    fragment,anchor=_fragment(_source_definition(values),heavy)
    source_points=[xyz[n] for n in _FRAME];target_points=[center[n]['xyz'] for n in _FRAME]
    source_basis,target_basis=_frame(source_points),_frame(target_points)
    moved={}
    for n in fragment:
        local=[_dot(_sub(xyz[n],source_points[0]),axis) for axis in source_basis]
        moved[n]=[target_points[0][i]+sum(local[j]*target_basis[j][i] for j in range(3)) for i in range(3)]
    moved.update({n:center[n]['xyz'] for n in _SCAFFOLD})
    if set(moved)!=set(heavy):raise ValueError('Control graft has an unaccounted heavy atom')
    lines=[line for line in frame.read_text().splitlines() if line.startswith(('ATOM  ','HETATM')) and ((line[21:22].strip() or '_'),line[22:26].strip()) in SITES]
    reference='\n'.join(lines)+'\nTER\nEND\n';candidate=[];serial=0;inserted=False
    for line in lines:
        if ((line[21:22].strip() or '_'),line[22:26].strip())==SITES[1]:
            if inserted:continue
            inserted=True
            for n in sorted(moved):
                if len(n)>4:raise ValueError('Unsupported PDB atom name')
                serial+=1;x,y,z=moved[n];element=heavy[n]['element']
                candidate.append(f'HETATM{serial:5d} {n:>4} {code:>3} A{2:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {element:>2}')
        else:
            serial+=1;candidate.append(line[:6]+f'{serial:5d}'+line[11:])
    output.mkdir(parents=True);ref=output/'reference.pdb';model=output/'candidate.pdb';ref.write_text(reference);model.write_text('\n'.join(candidate)+'\nTER\nEND\n')
    actual=_pdb_inventory(model)
    if any(actual[k]['xyz']!=r['xyz'] for k,r in selected.items() if k[:2]!=SITES[1]):raise ValueError('Control changed a flanking coordinate')
    if any(actual[('A','2','','',n)]['xyz']!=center[n]['xyz'] for n in _SCAFFOLD):raise ValueError('Control changed a backbone coordinate')
    if snapshots!=[p.read_bytes() for p in [frame,numerical]]:raise ValueError('Control preparation changed an input')
    r={'schema_version':1,'policy_id':POLICY_ID,'component':code,'scope':'SEPARATE_SYNTHETIC_THREE_RESIDUE_CONTROL',
       'frame_sha256':sha256(snapshots[0]).hexdigest(),'dictionary_sha256':sha256(snapshots[1]).hexdigest(),
       'sites':['A:1','A:2','A:3'],'expected_links':[['A:1','A:2'],['A:2','A:3']],
       'context':{'site':'A:2','incoming_site':'A:1','outgoing_site':'A:3','five_prime_state':'linked','three_prime_state':'linked'},
       'coordinate_family':family,'base_atoms':fragment,'attachment_atom':anchor,'rigid_frame_atoms':list(_FRAME),
       'backbone_and_flanks_preserved':True,'hydrogens_in_model':False,'model_optimization':'NOT_RUN',
       'outputs':{name:{'anchor':'control_directory','path':p.name,'sha256':sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for name,p in [('reference',ref),('model',model)]},
       'automatic_adoption':False,'scientific_approval':'NOT_RUN'}
    (output/'control_receipt.json').write_text(json.dumps(r,indent=2)+'\n');return r


def _heavy_proxy_checks(native,projected,code,site):
    values,_=normalize_torsion_block(component_values(projected,code));atoms={a['i_seq']:a for a in native['atoms']}
    heavy={a['atom_id'] for a in atoms.values() if _site(a)==site}
    details=native['geometry']['proxy_details'];checks={};key=lambda ns:min(tuple(ns),tuple(ns)[::-1])
    def names(row):return tuple(atoms[i]['atom_id'] for i in row['i_seqs'])
    def selected(kind):return [r for r in details[kind] if all(_site(atoms[i])==site for i in r['i_seqs'])]
    for kind,category,size,target,field,esd in [('bond_simple','_chem_comp_bond',2,'distance_ideal','value_dist','value_dist_esd'),('angle','_chem_comp_angle',3,'angle_ideal','value_angle','value_angle_esd')]:
        expected=Counter((key([r['atom_id_'+str(i)] for i in range(1,size+1)]),format(float(r[field]),'.10g'),format(1/float(r[esd])**2,'.10g')) for r in _rows(values,category) if all(r['atom_id_'+str(i)] in heavy for i in range(1,size+1)))
        actual=Counter((key(names(r)),format(float(r[target]),'.10g'),format(float(r['weight']),'.10g')) for r in selected(kind))
        checks['exact-heavy-'+kind]=expected==actual
    expected=Counter(('const_dihedral' if int(r['period'])==0 else 'dihedral',_torsion_signature([r['atom_id_'+str(i)] for i in range(1,5)],r['value_angle'],r['period'],r.get('alt_value_angle')),format(_torsion_weight(r),'.10g')) for r in _rows(values,'_chem_comp_tor') if all(r['atom_id_'+str(i)] in heavy for i in range(1,5)))
    actual=Counter((kind,_torsion_signature(names(r),r['angle_ideal'],r['periodicity'],r.get('alt_angle_ideals')),format(float(r['weight']),'.10g')) for kind in ['dihedral','const_dihedral'] for r in selected(kind))
    checks['exact-heavy-torsions']=expected==actual
    planes={}
    for r in _rows(values,'_chem_comp_plane_atom'):
        if r['atom_id'] in heavy:planes.setdefault(r['plane_id'],[]).append((r['atom_id'],format(1/float(r['dist_esd'])**2,'.10g')))
    checks['exact-heavy-planes']=Counter(tuple(sorted(p)) for p in planes.values() if len(p)>=3)==Counter(tuple(sorted(zip(names(r),(format(float(w),'.10g') for w in r['weights'])))) for r in selected('planarity'))
    def chir(center,ns,sign,both):
        parity=-1 if sum(ns[i]>ns[j] for i in range(3) for j in range(i+1,3))%2 else 1
        return center,tuple(sorted(ns)),0 if both else parity*sign,both
    expected=Counter(chir(r['atom_id_centre'],[r['atom_id_'+str(i)] for i in range(1,4)],1 if r['volume_sign'].lower().startswith('pos') else -1,r['volume_sign'].lower()=='both') for r in _rows(values,'_chem_comp_chir') if all(r['atom_id_'+str(i)] in heavy for i in range(1,4)))
    actual=Counter(chir(names(r)[0],list(names(r)[1:]),1 if r['volume_ideal']>0 else -1,r['both_signs']) for r in selected('chirality'))
    checks['exact-heavy-fixed-chirality']=expected==actual
    return checks


def qualify_linked_control(reference,native,model,preparation,projected,code):
    """Require exact declared links/projections and unchanged flanking mechanics."""
    from .cif_triple_bond_audit import audit_triple_bonds
    checks=[]
    def check(name,ok,**evidence):checks.append({'check':name,'status':'PASS' if ok else 'REVIEW',**evidence})
    try:
        _model(native,Path(model),coordinates_match=True)
        check('exact-control-model',True)
        points=native['geometry']['sites_cart_exact'];positions=[a['xyz'] for a in native['atoms']]
        check('native-coordinate-roundtrip',len(points)==len(positions) and all(len(p)==3 and all(type(x) in (int,float) and math.isfinite(x) and abs(x-y)<=1e-12 for x,y in zip(p,q)) for p,q in zip(points,positions)))
        check('native-interpreter',native.get('status')=='REVIEW' and native.get('inventory_detail')=='linked' and native.get('fatal_problems') is None and native.get('unused_definitions')==[] and native.get('unsupported_fields')==[])
        check('no-competing-secondary-structure',_fixed_policy(reference) and _fixed_policy(native))
        before=native_backbone_links(reference);after=native_backbone_links(native)
        check('exact-declared-backbone-links',set(after)=={('A:1','A:2'),('A:2','A:3')} and after==before,reference=repr(before),candidate=repr(after))
        mappings={r['site']:r for r in native['monomer_mappings']['rows']};old={r['site']:r for r in reference['monomer_mappings']['rows']}
        check('three-complete-heavy-sites',set(mappings)=={'A:1','A:2','A:3'} and all(r.get('missing_non_hydrogen_atoms',{}).get('status')=='RECORDED' and r['missing_non_hydrogen_atoms']['atom_ids']==[] and r.get('unexpected_atoms',{}).get('status')=='RECORDED' and r['unexpected_atoms']['atom_ids']==[] for r in mappings.values()))
        metadata=mappings.get('A:2',{}).get('metadata',{})
        check('native-dna-metadata',metadata.get('group')=='DNA' and metadata.get('classification')=={'status':'RECORDED','value':'DNA'})
        check('unchanged-flanking-definitions',{s:r['metadata']['effective_definition'] for s,r in mappings.items() if s!='A:2'}=={s:r['metadata']['effective_definition'] for s,r in old.items() if s!='A:2'})
        for kind in reference['geometry']['proxy_details']:
            check('unaffected-native-proxies:'+kind,_proxy_subset(reference,{'A:2'},kind)==_proxy_subset(native,{'A:2'},kind))
        checks.extend(site_definition_checks(native,[preparation]));checks.extend(definition_projection_checks(native,{'A:2':(Path(projected),code)}))
        plan=preparation['sites'][0];check('exact-site-modifier',mappings['A:2'].get('chem_mod_ids')=={'status':'RECORDED','ids':[plan['modification_id']]})
        check('no-outgoing-oxygen-hydrogen',not any(a['atom_id'] in plan['deleted_atoms'] and _site(a)=='A:2' for a in native['atoms']))
        for name,ok in _heavy_proxy_checks(native,projected,code,'A:2').items():check(name,ok)
        # The incoming backbone oxygen replaces OP3 as P's fourth neighbor.
        atoms={a['i_seq']:a for a in native['atoms']};p=next(i for i,a in atoms.items() if _site(a)=='A:2' and a['atom_id']=='P')
        ns={next(i for i in r['i_seqs'] if i!=p) for r in native['geometry']['proxy_details']['bond_simple'] if p in r['i_seqs']}
        angles={min(tuple(r['i_seqs']),tuple(r['i_seqs'])[::-1]) for r in native['geometry']['proxy_details']['angle']}
        expected={(('A:1',"O3'")),(('A:2',"O5'")),(('A:2','OP1')),(('A:2','OP2'))}
        check('linked-phosphate-tetrahedral-coverage',{(_site(atoms[i]),atoms[i]['atom_id']) for i in ns}==expected and all(min((a,p,b),(b,p,a)) in angles for a,b in combinations(ns,2)),bonds=len(ns),required_angles=6)
        for label,record in [('reference',reference),('candidate',native)]:
            for name,ok in energy_inventory_checks(record).items():check(label+':'+name,ok)
        finite=True
        for kind,rows in native['geometry']['proxy_details'].items():
            for row in rows:
                weights=row.get('weights',[row.get('weight')])
                finite &= all(type(w) in (int,float) and math.isfinite(w) and (w>0 or kind=='const_dihedral' and w==0 and row.get('periodicity')==0) for w in weights)
                fields=[] if kind=='planarity' else ['distance_ideal'] if kind in {'bond_simple','bond_asu'} else ['angle_ideal'] if kind in {'angle','dihedral','const_dihedral'} else ['volume_ideal'] if kind=='chirality' else ['target_angle_deg']
                finite &= all(type(row.get(f)) in (int,float) and math.isfinite(row[f]) for f in fields)
        check('finite-positive-active-proxy-weights',finite)
        check('complete-proxy-counts',set(native['geometry']['proxy_details'])=={'bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity'} and all(native['geometry']['proxy_counts'].get(k)==len(v) for k,v in native['geometry']['proxy_details'].items()))
        triple=audit_triple_bonds(projected,code,dictionary=projected)
        check('retained-triple-targets',not triple['triple_bonds'] or triple['target_screen']=='PASS')
    except (KeyError,TypeError,ValueError,OSError,IndexError,StopIteration,ZeroDivisionError,OverflowError) as exc:
        check('complete-linked-evidence',False,error=type(exc).__name__+': '+str(exc));triple={'status':'UNASSESSED'}
    result={'schema_version':1,'policy_id':POLICY_ID,'checks':checks,'scope':'SEPARATE_SYNTHETIC_THREE_RESIDUE_CONTROL',
        'triple_dictionary_screen':triple,'formal_charge_readback':'UNSUPPORTED_UNLESS_RECORDED','nonbonded_pair_identity':'NOT_ASSESSED',
        'scientific_approval':'NOT_RUN','automatic_adoption':False,'requires_cif_review':False,'production_pipeline':'UNCHANGED'}
    result['status']='LINKED_CONTROL_MECHANICS_PASS' if mechanics_can_continue(result) else 'REVIEW'
    return result
