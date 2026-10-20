"""Read-only screening of declared triple bonds and active native restraints.

Bounds are conservative diagnostic policy, not replacement targets or chemical
approval. Source coordinates never provide the authoritative restraint target.
"""
from hashlib import sha256
import math
import re
from pathlib import Path
from .cif_doctor import _number,_ORDERS
from .cif_stereochemistry_audit import _values,_graph,_coordinates

POLICY_ID='cif-declared-triple-bond-screen-v1'
LENGTH_BOUNDS={('C','C'):(1.10,1.30),('C','N'):(1.05,1.25)}
MAX_BOND_ESD=.05
MAX_ANGLE_ESD=5.
MAX_BEND_DEGREES=5.


def _numeric(value):
    if value is None or isinstance(value,bool):return None
    try:return _number(str(value))
    except (ValueError,TypeError):return None


def _angle(xyz,atoms):
    if any(n not in xyz for n in atoms):return None
    a,b,c=[xyz[n] for n in atoms];u=[x-y for x,y in zip(a,b)];v=[x-y for x,y in zip(c,b)]
    norm=math.sqrt(sum(x*x for x in u)*sum(x*x for x in v))
    if not norm:return None
    return math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v))/norm))))


def _key(atoms):
    atoms=tuple(atoms);return min(atoms,atoms[::-1])


def _rows(values,category,count):
    stem='_chem_comp_'+category+'.';ids=[stem+'atom_id_'+str(i) for i in range(1,count+1)]
    if not all(k in values for k in ids):return []
    return [({'atoms':[values[k][i] for k in ids],**{k[len(stem):]:v[i] for k,v in values.items()
             if k.startswith(stem) and not k.startswith(stem+'atom_id_')}}) for i in range(len(values[ids[0]]))]


def audit_triple_bonds(reference,code,*,dictionary=None,native=None):
    """Compare every explicit source triple against dictionary or native terms."""
    if (dictionary is None)==(native is None):raise ValueError('Require exactly one dictionary or native inventory')
    reference=Path(reference);original=reference.read_bytes();rv=_values(reference,code)
    elements,orders,_,neighbors=_graph(rv)
    triples=sorted(p for p,o in orders.items() if o=='TRIPLE')
    report={'schema_version':1,'policy_id':POLICY_ID,'component':code,'source_sha256':sha256(original).hexdigest(),
        'status':'UNASSESSED','triple_bonds':[],'linear_axis_torsions':[],'findings':[],
        'screen_policy':{'length_bounds_angstrom':{'-'.join(k):list(v) for k,v in LENGTH_BOUNDS.items()},
            'max_bond_esd_angstrom':MAX_BOND_ESD,'max_angle_esd_degrees':MAX_ANGLE_ESD,'max_bend_degrees':MAX_BEND_DEGREES},
        'scientific_approval':'NOT_RUN','optimization':'NOT_RUN','automatic_adoption':False,
        'limitations':['Screen bounds are review thresholds, not generated targets or universal chemical limits.',
            'Source/seed coordinates are descriptive, not independent validation.',
            'Native membership in this isolated component is not a complete ReadySet/refinement replay.']}
    if not triples:return report
    def issue(rule,atoms,**details):report['findings'].append({'rule':rule,'atoms':list(atoms),**details})
    if dictionary is not None:
        dictionary=Path(dictionary);before=dictionary.read_bytes();v=_values(dictionary,code)
        actual_orders=_graph(v)[1];_,xyz=_coordinates(v,source=False)
        bonds=_rows(v,'bond',2);angles=_rows(v,'angle',3);torsions=_rows(v,'tor',4)
        report['dictionary_sha256']=sha256(before).hexdigest();report['scope']='DICTIONARY_TERMS_AND_COORDINATES'
    else:
        report['scope']='ACTIVE_NATIVE_PROXIES_AND_COORDINATES';before=None
        atoms=native.get('atoms',[]);selected=[a for a in atoms if a.get('identity',{}).get('resname')==code]
        identities={tuple(a['identity'].get(k) for k in ['model_id','chain_id','resseq','icode','altloc']) for a in selected}
        if len(identities)!=1 or len({a['atom_id'] for a in selected})!=len(selected):issue('ambiguous-native-site',[])
        index={a['i_seq']:a['atom_id'] for a in selected};xyz={a['atom_id']:a['xyz'] for a in selected}
        if len(index)!=len(selected):issue('ambiguous-native-indices',[])
        if set(xyz)!=set(elements) or any(a.get('element','').upper()!=elements.get(a['atom_id']) for a in selected):
            issue('native-atom-inventory-differs',[])
        for name,point in list(xyz.items()):
            if len(point)!=3 or any(_numeric(x) is None for x in point):
                issue('invalid-native-coordinate',[name]);del xyz[name]
            else:xyz[name]=[float(x) for x in point]
        actual_orders={}
        mappings=native.get('monomer_mappings',{}).get('rows',[])
        if len(mappings)!=1:issue('ambiguous-effective-definition',[])
        for row in mappings:
            for b in row.get('metadata',{}).get('effective_definition',{}).get('bonds') or []:
                p=_key([b['atom_id_1'],b['atom_id_2']]);value=_ORDERS.get(str(b.get('type','')).upper())
                if p in actual_orders:issue('duplicate-effective-bond',p)
                actual_orders[p]=value
        details=native.get('geometry',{}).get('proxy_details',{})
        def proxies(kind,target):
            rows=details.get(kind)
            if rows is None:issue('unavailable-native-category',[],category=kind);return []
            result=[]
            for r in rows:
                if any(i not in index for i in r['i_seqs']):continue
                weight=r.get('weight');esd=1/math.sqrt(weight) if type(weight) in (int,float) and math.isfinite(weight) and weight>0 else None
                result.append({'atoms':[index[i] for i in r['i_seqs']], 'value_dist' if kind=='bond_simple' else 'value_angle':r.get(target),
                    'value_dist_esd' if kind=='bond_simple' else 'value_angle_esd':esd,'native_proxy':r})
            return result
        bonds=proxies('bond_simple','distance_ideal');angles=proxies('angle','angle_ideal')
        torsions=proxies('dihedral','angle_ideal')+proxies('const_dihedral','angle_ideal')
        for r in details.get('bond_asu') or []:
            if all(i in index for i in r['i_seqs']) and _key([index[i] for i in r['i_seqs']]) in triples:
                issue('symmetry-bond-needs-review',[index[i] for i in r['i_seqs']])
    linear=set();target_ok=True;coordinate_ok=True
    for pair in triples:
        bounds=LENGTH_BOUNDS.get(tuple(sorted(elements[n] for n in pair)))
        if bounds is None:issue('unsupported-triple-element-pair',pair)
        if actual_orders.get(pair)!='TRIPLE':issue('triple-order-not-preserved',pair,observed=actual_orders.get(pair))
        matched=[r for r in bonds if _key(r['atoms'])==pair]
        target=esd=None
        if len(matched)==1:
            target=_numeric(matched[0].get('value_dist'));esd=_numeric(matched[0].get('value_dist_esd'))
        passed=len(matched)==1 and bounds is not None and target is not None and bounds[0]<=target<=bounds[1] and esd is not None and 0<esd<=MAX_BOND_ESD
        if not passed:issue('triple-distance-target-or-membership',pair,matches=len(matched),target=target,esd=esd)
        target_ok &= passed
        observed=math.dist(xyz[pair[0]],xyz[pair[1]]) if all(n in xyz for n in pair) else None
        if observed is None or bounds is None or not bounds[0]<=observed<=bounds[1]:
            issue('triple-coordinate-distance',pair,observed=observed);coordinate_ok=False
        record={'atoms':list(pair),'declared_order':actual_orders.get(pair),'distance':{'target':target,'esd':esd,'observed':observed,'membership_count':len(matched)},'angles':[]}
        for center,other in [pair,pair[::-1]]:
            flanks=sorted(neighbors[center]-{other})
            if len(flanks)>1:issue('unsupported-linear-center-connectivity',[center],neighbors=flanks)
            for flank in flanks:
                atoms=[flank,center,other];linear.add(_key(atoms));matched=[r for r in angles if _key(r['atoms'])==_key(atoms)]
                ideal=sigma=None
                if len(matched)==1:ideal=_numeric(matched[0].get('value_angle'));sigma=_numeric(matched[0].get('value_angle_esd'))
                passed=len(matched)==1 and ideal is not None and 180-MAX_BEND_DEGREES<=ideal<=180 and sigma is not None and 0<sigma<=MAX_ANGLE_ESD
                if not passed:issue('linear-angle-target-or-membership',atoms,matches=len(matched),target=ideal,esd=sigma)
                target_ok &= passed
                actual=_angle(xyz,atoms)
                if actual is None or 180-actual>MAX_BEND_DEGREES:
                    issue('linear-coordinate-bending',atoms,observed=actual);coordinate_ok=False
                record['angles'].append({'atoms':atoms,'target':ideal,'esd':sigma,'observed':actual,'membership_count':len(matched)})
        report['triple_bonds'].append(record)
    for row in torsions:
        a=row['atoms']
        if len(a)==4 and any(_key(a[i:i+3]) in linear for i in [0,1]):
            report['linear_axis_torsions'].append(row);issue('torsion-through-linear-axis',a)
    report.update(target_screen='PASS' if target_ok else 'REVIEW',coordinate_screen='PASS' if coordinate_ok else 'REVIEW',
        status='REVIEW' if report['findings'] else 'TRIPLE_SCREEN_PASS')
    if reference.read_bytes()!=original or dictionary is not None and dictionary.read_bytes()!=before:raise ValueError('Triple-audit input changed')
    return report


def write_component_control_model(source,code,output):
    """Write a separate single-residue PDB from complete declared ideal seeds."""
    source,output=Path(source).resolve(strict=True),Path(output).absolute();original=source.read_bytes()
    v=_values(source,code);elements=_graph(v)[0];family,xyz=_coordinates(v,source=True)
    if (not re.fullmatch(r'[A-Z0-9]{1,3}',code) or len(xyz)!=len(elements) or len(elements)>99999
            or output.resolve().is_relative_to(source.parent) or output.exists() or output.is_symlink()
            or any(p.is_symlink() for p in output.parents)):
        raise ValueError('Require a fresh output and complete representable component coordinates')
    lines=[]
    for i,(name,element) in enumerate(elements.items(),1):
        if not re.fullmatch(r"[A-Za-z0-9'*]+",name) or len(name)>4 or len(element)>2 or any(not math.isfinite(x) or abs(x)>=999 for x in xyz[name]):raise ValueError('Unrepresentable isolated control atom')
        x,y,z=xyz[name];lines.append(f'HETATM{i:5d} {name:>4s} {code:>3s} A   1    {x:8.3f}{y:8.3f}{z:8.3f}  1.00 20.00          {element:>2s}\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f:f.write(''.join(lines)+'END\n')
    if source.read_bytes()!=original:raise ValueError('Component control source changed')
    return {'coordinate_origin':family,'source_sha256':sha256(source.read_bytes()).hexdigest(),'model_sha256':sha256(output.read_bytes()).hexdigest(),
            'scope':'SEPARATE_SOURCE_SEED_COMPONENT_CONTROL_PDB_ROUNDED','experimental_model_used':False}
