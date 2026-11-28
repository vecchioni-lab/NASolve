"""Read-only, source-relative stereo evidence; never assign absolute CIP labels."""
from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
import re

from .cif_doctor import assess_dictionaries, _number, _ORDERS
from .cif_linked_preparation import component_values

POLICY_ID = 'cif-source-relative-stereochemistry-audit-v1'
VOLUME_EPSILON = 1e-6  # Angstrom cubed; only separates degenerate signed volumes.
_MISSING = {'', '.', '?'}


def _values(path, code):
    assessment = assess_dictionaries([path], stage='stereochemistry-audit')
    selected = [c for c in assessment['components'] if c['component_id'] == code]
    if len(selected) != 1 or selected[0]['verdicts']['graph'] != 'PASS':
        raise ValueError('Require one graph-valid stereo-audit component')
    return {k.lower():v for k,v in component_values(path,code).items()}


def _stereo(v):
    a='_chem_comp_atom.';ids=v[a+'atom_id'];result={}
    for i,atom in enumerate(ids):
        declared={v[k][i].upper() for k in [a+'pdbx_stereo_config',a+'stereo_config']
                  if k in v and v[k][i] not in _MISSING}
        if len(declared)>1 or declared-{'R','S','N'}:
            raise ValueError('Conflicting or unsupported atom stereo declarations')
        result[atom]=next(iter(declared)) if declared else '?'
    return result


def _graph(v):
    a,b='_chem_comp_atom.','_chem_comp_bond.'
    ids=v[a+'atom_id'];elements={n:e.upper() for n,e in zip(ids,v[a+'type_symbol'])}
    neighbors={n:set() for n in ids};bonds={}
    orders=[v[k] for k in [b+'value_order',b+'type'] if k in v]
    for i,(x,y) in enumerate(zip(v[b+'atom_id_1'],v[b+'atom_id_2'])):
        declared={_ORDERS.get(col[i].upper(),col[i].upper()) for col in orders if col[i] not in _MISSING}
        if len(declared)!=1:raise ValueError('Ambiguous stereo-audit bond order')
        bonds[tuple(sorted((x,y)))]=next(iter(declared));neighbors[x].add(y);neighbors[y].add(x)
    charges={}
    for i,atom in enumerate(ids):
        declared={_number(v[k][i]) for k in [a+'charge',a+'pdbx_formal_charge']
                  if k in v and v[k][i] not in _MISSING}
        if len(declared)>1:raise ValueError('Conflicting formal-charge aliases')
        charges[atom]=next(iter(declared)) if declared else None
    return elements,bonds,charges,neighbors


def reader_stereo_inventory(source, code):
    """Describe exact source markers and covalent neighbors without perception."""
    source=Path(source);v=_values(source,code);markers=_stereo(v);neighbors=_graph(v)[3]
    unknown=sorted(n for n,s in markers.items() if s=='?')
    p='_chem_comp_chir.'
    signed=[{'center':center,'ordered_neighbors':[v[p+'atom_id_'+str(k)][i] for k in (1,2,3)],
             'volume_sign':v[p+'volume_sign'][i]} for i,center in enumerate(v.get(p+'atom_id_centre',[]))]
    return {'policy_id':POLICY_ID,'component':code,'source_sha256':sha256(source.read_bytes()).hexdigest(),
        'atoms':{n:{'declared_stereo':markers[n],'declared_neighbors':sorted(neighbors[n])} for n in sorted(markers)},
        'unknown_markers':unknown,
        'unknown_markers_without_four_declared_neighbors':[n for n in unknown if len(neighbors[n])!=4],
        'source_signed_chirality':signed,
        'stereochemistry_inferred':False,'automatic_adoption':False}


def _coordinates(v, *, source):
    a='_chem_comp_atom.'
    families=[('SOURCE_IDEAL',[a+'pdbx_model_cartn_'+x+'_ideal' for x in 'xyz']),
              ('SOURCE_MODEL',[a+'model_cartn_'+x for x in 'xyz']),
              ('RESTRAINT_CARTESIAN',[a+x for x in 'xyz'])]
    if not source:families=families[2:]+families[:2]
    for label,keys in families:
        if all(k in v for k in keys):
            result={atom:[_number(v[k][i]) for k in keys] for i,atom in enumerate(v[a+'atom_id'])}
            # Do not mix coordinate families or silently fill unknown values.
            return label,{n:p for n,p in result.items() if all(x is not None and math.isfinite(x) for x in p)}
    return 'UNAVAILABLE',{}


def _volume(xyz,center,neighbors):
    if any(n not in xyz for n in [center,*neighbors]):return None
    x,y,z=[[xyz[n][i]-xyz[center][i] for i in range(3)] for n in neighbors]
    return x[0]*(y[1]*z[2]-y[2]*z[1])-x[1]*(y[0]*z[2]-y[2]*z[0])+x[2]*(y[0]*z[1]-y[1]*z[0])


def audit_candidate_stereochemistry(source, candidate, code):
    """Compare labels, signed targets and coordinate hands, keeping every gate."""
    source,candidate=Path(source),Path(candidate)
    before,after=source.read_bytes(),candidate.read_bytes()
    sv,gv=_values(source,code),_values(candidate,code)
    sm,gm=_stereo(sv),_stereo(gv);sg,gg=_graph(sv),_graph(gv)
    chemical_equal=sg[:3]==gg[:3]
    sf,sxyz=_coordinates(sv,source=True);gf,gxyz=_coordinates(gv,source=False)
    p='_chem_comp_chir.';terms=[]
    fields=[p+'atom_id_centre',p+'atom_id_1',p+'atom_id_2',p+'atom_id_3',p+'volume_sign']
    if any(k in gv for k in fields):
        if not all(k in gv for k in fields) or len({len(gv[k]) for k in fields})!=1:
            raise ValueError('Incomplete generated chirality loop')
        for i,center in enumerate(gv[fields[0]]):
            neighbors=[gv[k][i] for k in fields[1:4]]
            valid=(center in sg[3] and len(sg[3][center])==4 and len(set(neighbors))==3
                   and all(n in sg[3][center] for n in neighbors))
            sign=gv[fields[4]][i].lower();target={'positiv':1,'positive':1,'negativ':-1,'negative':-1}.get(sign)
            vs,vg=(_volume(xyz,center,neighbors) for xyz in [sxyz,gxyz]) if valid else (None,None)
            hand=('UNASSESSED' if vs is None or vg is None else 'DEGENERATE' if min(abs(vs),abs(vg))<=VOLUME_EPSILON
                  else 'PRESERVED' if vs*vg>0 else 'INVERTED')
            target_match=(None if target is None or vs is None or vg is None else
                          min(target*vs,target*vg)>VOLUME_EPSILON)
            terms.append({'center':center,'ordered_neighbors':neighbors,'target_sign':sign,
                'valid_declared_tetrahedron':valid,'source_volume':vs,'candidate_volume':vg,
                'coordinate_handedness':hand,'target_matches_both_coordinates':target_match})
    centers=[];rejected=not chemical_equal;review=False
    for center,label in sorted(sm.items()):
        if label not in {'R','S'}:continue
        current=gm.get(center,'?');state='OMITTED' if current=='?' else 'PRESERVED' if current==label else 'CONFLICT'
        rows=[t for t in terms if t['center']==center]
        rejected |= state=='CONFLICT' or any(not t['valid_declared_tetrahedron'] or t['coordinate_handedness'] in {'INVERTED','DEGENERATE'}
                    or t['target_matches_both_coordinates'] is False for t in rows)
        review |= state=='OMITTED' or not rows or any(t['coordinate_handedness']=='UNASSESSED' or t['target_matches_both_coordinates'] is None for t in rows)
        centers.append({'center':center,'source_atom_label':label,'candidate_atom_label':current,'atom_label':state,'terms':rows})
    extra=[t for t in terms if sm.get(t['center']) not in {'R','S'}]
    # Undeclared generated centres are retained for separate review, never approved by absence.
    review |= bool(extra) or not centers
    if source.read_bytes()!=before or candidate.read_bytes()!=after:raise ValueError('Stereo-audit input changed')
    return {'schema_version':1,'policy_id':POLICY_ID,'component':code,
        'status':'REJECTED' if rejected else 'REVIEW' if review else 'SOURCE_RELATIVE_STEREO_PASS',
        'source_sha256':sha256(before).hexdigest(),'candidate_sha256':sha256(after).hexdigest(),
        'graph_elements_orders_formal_charges_equal':chemical_equal,'centres':centers,'other_generated_terms':extra,
        'source_coordinate_family':sf,'candidate_coordinate_family':gf,'volume_epsilon_angstrom_cubed':VOLUME_EPSILON,
        'absolute_cip_assignment':'NOT_RUN','convergence':'NOT_ASSESSED','native_proxy_validation':'NOT_RUN',
        'automatic_adoption':False,'inputs_preserved':True,
        'limitations':['Source-coordinate handedness is not an independent absolute CIP assignment.',
                       'Omitted R/S metadata remains review even when signed volumes agree.',
                       'No target, coordinate or chemical declaration is changed.']}


def audit_optimizer_log(log):
    """Summarize one printed native trajectory; energies are descriptive evidence."""
    lines=log.splitlines();tables=[i for i,s in enumerate(lines) if re.match(r'^Time\s+Energy\s+delta E',s)]
    rows=[]
    if len(tables)==1:
        pattern=re.compile(r'^\s*\d+:\d+\s+(\d+)\.?\s+(-?\d+(?:\.\d+)?)\b')
        for lineno,line in enumerate(lines[tables[0]+1:],tables[0]+2):
            if line.startswith('DONE'):break
            match=pattern.match(line)
            if match:rows.append({'iteration':int(match[1]),'printed_energy':float(match[2]),'line':lineno})
    sequential=bool(rows) and [r['iteration'] for r in rows]==list(range(1,len(rows)+1))
    rises=[{'from_iteration':a['iteration'],'to_iteration':b['iteration'],
            'energy_change':b['printed_energy']-a['printed_energy']} for a,b in zip(rows,rows[1:])
           if b['printed_energy']-a['printed_energy']>1e-4] if sequential else []
    return {'policy_id':'cif-printed-optimizer-trajectory-audit-v1','status':'RECORDED' if sequential else 'REVIEW',
        'table_count':len(tables),'rows':len(rows),'sequential':sequential,
        'lowest_printed_energy':min(rows,key=lambda r:r['printed_energy']) if sequential else None,
        'final_printed_energy':rows[-1] if sequential else None,'increases_above_print_rounding':len(rises),
        'largest_adjacent_increase':max(rises,key=lambda r:r['energy_change']) if rises else None,
        'stopping':'NOT_CONVERGED_REPORTED' if 'geometry not converged' in log.lower() else 'NOT_REPORTED',
        'convergence_claimed':False,'coordinate_trajectory':'NOT_CAPTURED',
        'interpretation':'Printed native energy trace only; no mechanism, optimum or convergence inference.'}
