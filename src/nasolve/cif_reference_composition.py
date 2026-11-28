"""Compose a declared N-glycosidic base with an explicit deoxy-DNA scaffold.

Both sources remain authority for their retained subgraphs. Coordinates are a
constructed seed, never numerical restraints or an independently ideal model.
The fingerprinted ordinary PostMR transport implementation is not modified.
"""
from collections import Counter
from hashlib import sha256
from math import dist, isfinite
from pathlib import Path
import re

from .cif_attachment_sites import _neutral_hydroxyl_hydrogens
from .cif_connected_atom_order import _ordered_values, POLICY_ID as ATOM_ORDER_POLICY
from .cif_stereochemistry_audit import _values, _graph, _stereo, _coordinates, _volume
from .ligand_profiles import _emit
from .postmr_restoration import _SUGAR, _SUGAR_EDGES, _FRAME, _frame, _dot, _sub

POLICY_ID = 'cif-explicit-deoxy-base-source-composition-v1'
_A, _B = '_chem_comp_atom.', '_chem_comp_bond.'
_MISSING = {'', '.', '?'}
_ORDERS = {'SINGLE': 'SING', 'DOUBLE': 'DOUB', 'TRIPLE': 'TRIP', 'AROMATIC': 'AROM'}


def _flag(values, category, fields, index, allowed):
    declared = {values[category + field][index].upper() for field in fields
                if category + field in values and values[category + field][index] not in _MISSING}
    if len(declared) > 1 or declared - allowed:
        raise ValueError('Conflicting or unsupported source declaration')
    return next(iter(declared)) if declared else '?'


def _source(path, code, *, backbone):
    values = _values(path, code)
    types = values.get('_chem_comp.type', [])
    allowed = {'DNA LINKING', 'L-DNA LINKING'} if backbone else {'NON-POLYMER'}
    if len(types) != 1 or types[0].upper() not in allowed:
        raise ValueError('Require explicit source type for its composition role')
    groups = [x.upper() for x in values.get('_chem_comp.group', []) if x not in _MISSING]
    if groups and (not backbone or groups != ['DNA']):
        raise ValueError('Conflicting source polymer group')
    if any(k.startswith(('_chem_comp_angle.', '_chem_comp_tor.', '_chem_comp_plane_atom.', '_chem_comp_chir.'))
           or k in {_B+'value_dist', _B+'value_dist_esd', _A+'type_energy'} for k in values):
        raise ValueError('Require chemical sources without numerical restraint categories')
    elements, bonds, charges, neighbors = _graph(values)
    stereo = _stereo(values)
    if any(q is None or not isfinite(q) or not float(q).is_integer() for q in charges.values()):
        raise ValueError('Require explicit finite integer source formal charges')
    total = values.get('_chem_comp.pdbx_formal_charge', [])
    if total and (len(total) != 1 or total[0] in _MISSING or float(total[0]) != sum(charges.values())):
        raise ValueError('Source total charge conflicts with its atom charges')
    if any(elements.get(n) != e for n,e in _SUGAR.items()):
        raise ValueError('Require conventionally named complete deoxy sugar')
    sugar_edges = {frozenset(p) for p in bonds if set(p) <= _SUGAR.keys()}
    if sugar_edges != _SUGAR_EDGES or any(bonds[tuple(sorted(p))] != 'SINGLE' for p in sugar_edges):
        raise ValueError('Unsupported sugar connectivity')
    scaffold = set(_SUGAR)
    if backbone:
        phosphate = {'P','OP1','OP2','OP3'}
        if (elements.get('P') != 'P' or any(elements.get(n) != 'O' for n in phosphate-{'P'})
                or neighbors['P'] != {"O5'",'OP1','OP2','OP3'}
                or any(bonds.get(tuple(sorted(('P',n)))) != ('DOUBLE' if n=='OP1' else 'SINGLE')
                       for n in neighbors['P']) or charges['P'] != 0):
            raise ValueError('Require a declared conventional phosphate source')
        for n in ('OP1','OP2','OP3'):
            if {x for x in neighbors[n] if elements[x] not in {'H','D'}} != {'P'}:
                raise ValueError('Unsupported phosphate substituent')
            hs = {x for x in neighbors[n] if elements[x] in {'H','D'}}
            if n == 'OP1':
                valid = charges[n] == 0 and not hs
            else:
                valid = ((charges[n] == -1 and not hs) or
                         (charges[n] == 0 and _neutral_hydroxyl_hydrogens(n,elements,bonds,charges,neighbors) is not None))
            if not valid:
                raise ValueError('Unqualified declared phosphate H/charge state')
        scaffold |= phosphate
    elif any(e == 'P' for e in elements.values()):
        raise ValueError('Reference must be a free nucleoside without phosphate')
    expected_h = {"C1'":1,"C2'":2,"C3'":1,"C4'":1,"C5'":2,"O4'":0,"O3'":1,"O5'":0 if backbone else 1}
    for n,count in expected_h.items():
        hs = {x for x in neighbors[n] if elements[x] in {'H','D'}}
        if charges[n] != 0 or len(hs) != count:
            raise ValueError('Require explicit neutral deoxy sugar hydrogen state')
    for n,e in elements.items():
        if e in {'H','D'} and (charges[n] != 0 or len(neighbors[n]) != 1
                              or bonds[tuple(sorted((n,next(iter(neighbors[n])))))] != 'SINGLE'):
            raise ValueError('Require singly attached neutral source hydrogen/isotope')
    heavy = {n for n,e in elements.items() if e not in {'H','D'}}
    boundary = [(a,b) for a in scaffold for b in neighbors[a] if b in heavy-scaffold]
    if (len(boundary) != 1 or boundary[0][0] != "C1'" or elements[boundary[0][1]] != 'N'
            or charges[boundary[0][1]] != 0 or bonds[tuple(sorted(boundary[0]))] != 'SINGLE'):
        raise ValueError('Require one neutral N-glycosidic base attachment')
    anchor = boundary[0][1]
    if len(neighbors[anchor]) != 3 or any(bonds[tuple(sorted((anchor,n)))] != 'SINGLE' for n in neighbors[anchor]):
        raise ValueError('Require a neutral three-coordinate N-glycosidic anchor')
    pending = [anchor]; fragment = set()
    while pending:
        n = pending.pop()
        if n in fragment: continue
        fragment.add(n)
        pending.extend(neighbors[n] - scaffold - fragment)
    if heavy-scaffold != fragment & heavy or any(neighbors[n] & scaffold - {"C1'"} for n in fragment):
        raise ValueError('Require a single complete unbridged base fragment')
    hand = tuple(stereo[n] for n in ("C1'","C3'","C4'"))
    if hand not in {('R','S','R'),('S','R','S')} or any(
            s in {'R','S'} and n not in {"C1'","C3'","C4'"} for n,s in stereo.items()):
        raise ValueError('Require declared beta-deoxy hand without additional source stereocentres')
    if backbone and ((types[0].upper() == 'L-DNA LINKING') != (hand == ('S','R','S'))):
        raise ValueError('Declared backbone hand conflicts with its polymer type')
    # A partial preferred family is not filled from another source/family.
    family, xyz = _coordinates(values, source=True)
    for keys in ((_A+'pdbx_model_cartn_'+x+'_ideal' for x in 'xyz'), (_A+'model_cartn_'+x for x in 'xyz')):
        keys = list(keys)
        if any(k in values for k in keys):
            if not all(k in values for k in keys): raise ValueError('Incomplete preferred coordinate family')
            break
    if set(xyz) != set(elements): raise ValueError('Require complete finite source coordinates')
    atoms = {}
    for i,n in enumerate(values[_A+'atom_id']):
        atoms[n] = dict(element=elements[n],charge=int(charges[n]),stereo=stereo[n],
            aromatic=_flag(values,_A,('aromatic','pdbx_aromatic_flag'),i,{'Y','N'}))
    edges = {}
    for i,(a,b) in enumerate(zip(values[_B+'atom_id_1'],values[_B+'atom_id_2'])):
        edge = tuple(sorted((a,b))); order = bonds[edge]
        if order not in _ORDERS: raise ValueError('Unsupported explicit source bond order')
        edges[edge] = dict(order=order,aromatic=_flag(values,_B,('aromatic','pdbx_aromatic_flag'),i,{'Y','N'}),
            stereo=_flag(values,_B,('stereo_config','pdbx_stereo_config'),i,{'N'}))
    return dict(values=values,elements=elements,bonds=bonds,atoms=atoms,edges=edges,neighbors=neighbors,
                stereo=stereo,xyz=xyz,coordinate_family=family,fragment=fragment,anchor=anchor,hand=hand)


def compose_dna_source(backbone_source, backbone_code, reference_source, reference_code, *, component):
    """Return new CIF bytes and provenance; neither source nor a model is written.

    The caller chooses both chemical authorities. This first rule supports an
    unbridged, conventionally named beta-deoxy sugar of matching hand, a neutral
    N-glycosidic attachment and explicit source phosphate H/charge state. It does
    not assign a pH, infer a link, activate a mutation or generate restraint targets.
    """
    if not isinstance(component,str) or not re.fullmatch('[A-Z0-9]{1,3}',component):
        raise ValueError('Require a distinct explicit PDB-compatible output identity')
    paths = [Path(backbone_source),Path(reference_source)]; originals = [p.read_bytes() for p in paths]
    try:
        t,r = [_source(p,c,backbone=i==0) for i,(p,c) in enumerate(zip(paths,(backbone_code,reference_code)))]
        if t['hand'] != r['hand']: raise ValueError('Source sugars have different declared hands')
        for n in set(_SUGAR)-{"O5'"}:
            isotopes=[Counter(s['elements'][h] for h in s['neighbors'][n] if s['elements'][h] in {'H','D'}) for s in (t,r)]
            if isotopes[0] != isotopes[1]: raise ValueError('Source sugar isotope inventories differ')
        terms = [("C1'",["O4'","C2'",None]),("C3'",["C2'","C4'","O3'"]), ("C4'",["C3'","O4'","C5'"])]
        configuration=[]
        for centre,adjacent in terms:
            volumes=[_volume(s['xyz'],centre,[s['anchor'] if n is None else n for n in adjacent]) for s in (t,r)]
            if min(abs(v) for v in volumes)<1e-6 or volumes[0]*volumes[1]<=0:
                raise ValueError('Source coordinate configurations disagree or are degenerate')
            configuration.append(dict(centre=centre,state='PRESERVED',declared=t['stereo'][centre],source_volumes=volumes))
        kept=set(t['atoms'])-t['fragment']; base=r['fragment']
        if kept & base: raise ValueError('Source atom names collide; explicit remapping is required')
        left,right=(_frame([s['xyz'][n] for n in _FRAME]) for s in (r,t))
        moved={}
        for n in base:
            local=[_dot(_sub(r['xyz'][n],r['xyz']["C1'"]),axis) for axis in left]
            moved[n]=[t['xyz']["C1'"][i]+sum(local[j]*right[j][i] for j in range(3)) for i in range(3)]
        xyz={**{n:t['xyz'][n] for n in kept},**moved}
        origin={n:'backbone' for n in kept};origin.update({n:'reference' for n in base})
        atoms={**{n:t['atoms'][n] for n in kept},**{n:r['atoms'][n] for n in base}}
        edges={e:row for e,row in t['edges'].items() if set(e)<=kept}
        edges.update({e:row for e,row in r['edges'].items() if set(e)<=base})
        bridge=tuple(sorted(("C1'",r['anchor'])));edges[bridge]=r['edges'][bridge]
        counts=Counter(a['element'] for a in atoms.values());symbols=sorted(counts,key=lambda x:(0 if x=='C' else 1 if x=='H' else 2,x))
        names=sorted(atoms);pairs=sorted(edges)
        v={'data_':'comp_'+component,'_chem_comp.id':[component], '_chem_comp.type':t['values']['_chem_comp.type'],
           '_chem_comp.name':['Explicit two-source deoxy nucleotide '+component],
           '_chem_comp.formula':[' '.join(e+(str(counts[e]) if counts[e]!=1 else '') for e in symbols)],
           '_chem_comp.pdbx_formal_charge':[str(sum(a['charge'] for a in atoms.values()))],
           _A+'comp_id':[component]*len(names),_A+'atom_id':names,_A+'type_symbol':[atoms[n]['element'] for n in names],
           _A+'charge':[str(atoms[n]['charge']) for n in names],_A+'pdbx_stereo_config':[atoms[n]['stereo'] for n in names],
           _A+'pdbx_aromatic_flag':[atoms[n]['aromatic'] for n in names],
           _B+'comp_id':[component]*len(pairs),_B+'atom_id_1':[e[0] for e in pairs],_B+'atom_id_2':[e[1] for e in pairs],
           _B+'value_order':[_ORDERS[edges[e]['order']] for e in pairs],_B+'pdbx_aromatic_flag':[edges[e]['aromatic'] for e in pairs]}
        for i,axis in enumerate('xyz'):v[_A+'model_Cartn_'+axis]=[format(xyz[n][i],'.14g') for n in names]
        v,input_order,output_order=_ordered_values(v,component)
        payload=_emit(v).encode()
        attached=sorted(base|{"C1'"})
        distance_error=max(abs(dist(r['xyz'][a],r['xyz'][b])-dist(xyz[a],xyz[b])) for i,a in enumerate(attached) for b in attached[i+1:])
        if distance_error>1e-10:raise ValueError('Rigid source-base transport changed internal distances')
        report=dict(schema_version=1,policy_id=POLICY_ID,status='COMPOSED_SOURCE_REQUIRES_QUALIFICATION',component=component,
            source_pins={role:dict(component=code,sha256=sha256(data).hexdigest(),size=len(data)) for role,code,data in zip(('backbone','reference'),(backbone_code,reference_code),originals)},
            atom_origins={n:dict(role=origin[n],source_atom=n) for n in names},removed_backbone_base=sorted(t['fragment']),
            unused_reference_scaffold=sorted(set(r['atoms'])-base),attachment=list(bridge),sugar_configuration=configuration,
            coordinate_families=dict(backbone=t['coordinate_family'],reference=r['coordinate_family']),
            coordinate_authority='CONSTRUCTED_SEED_NOT_INDEPENDENT_IDEAL',base_pair_distance_max_change=distance_error,
            bond_stereo_encoding='NO_E_Z_DECLARATIONS_PERMITTED; UNASSERTED_COLUMN_OMITTED',
            atom_order=dict(policy_id=ATOM_ORDER_POLICY,input_order=input_order,output_order=output_order),
            output_sha256=sha256(payload).hexdigest(),model_editing='NOT_RUN',native_qualification='NOT_RUN',
            restraint_generation='NOT_RUN',linked_state_qualification='NOT_RUN',automatic_adoption=False)
        return payload,report
    finally:
        if [p.read_bytes() for p in paths] != originals:raise ValueError('Composition source changed while reading')
