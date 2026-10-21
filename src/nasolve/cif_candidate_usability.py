"""Verified isolated-component usability and explicit nonconvergence decisions.

No dictionary, model, target or native kernel is changed here. A source 'both'
volume term does not choose a hand, but its omission remains a mechanical delta
requiring complete native tetrahedral bond/angle coverage.
"""
from collections import Counter
from itertools import combinations
from hashlib import sha256
import json,math
from pathlib import Path

from .cif_doctor import _comparison_inventory,_ORDERS
from .cif_generation import inspect_component_generation,_explicit_formal_charges
from .cif_source_candidate import complete_candidate_stereo
from .cif_stereochemistry_audit import _values,_graph,reader_stereo_inventory
from .cif_terminal_qualification import definition_projection_checks,_rows

POLICY_ID='cif-isolated-candidate-native-usability-v1'
ENERGY_POLICY_ID='cif-fixed-native-usability-energy-v1'


def reassess_complete_candidate(source,candidate,code):
    """Retain raw inspection while distinguishing fixed hand from 'both' terms."""
    raw=inspect_component_generation(source,candidate,code);stereo=complete_candidate_stereo(source,candidate,code)
    left=raw['source_assessment']['components'];right=raw['generated_assessment']['components']
    if len(left)!=1 or len(right)!=1:raise ValueError('Require one source and candidate component')
    a,b=(_comparison_inventory(v)['signed_chirality'] for v in [left[0],right[0]])
    ca,cb=Counter(a),Counter(b);missing=list((ca-cb).elements());extra=list((cb-ca).elements())
    values=_values(source,code);neighbors=_graph(values)[3];inventory=reader_stereo_inventory(source,code)
    labelled={n for n,r in inventory['atoms'].items() if r['declared_stereo'] in {'R','S'}}
    fixed_a=Counter(r for r in a if r[2]!='both');fixed_b=Counter(r for r in b if r[2]!='both')
    missing_fixed=list((fixed_a-fixed_b).elements())
    allowed=bool(missing) and not extra and not missing_fixed and all(sign=='both' and center not in labelled
        and len(neighbors.get(center,set()))==4 and len(set(names))==3 and set(names)<=neighbors[center]
        for center,names,sign in missing)
    reasons=list(raw['rejection_reasons'])
    if allowed:reasons=[s for s in reasons if s!='generated-declared-chirality-changed']
    if missing_fixed:reasons.append('required-fixed-chirality-missing-or-changed')
    if labelled-{r[0] for r in fixed_b}:reasons.append('labelled-stereocenter-without-fixed-restraint')
    if {r[0] for r in fixed_b}-({r[0] for r in fixed_a}|labelled):reasons.append('generated-unaccounted-fixed-chirality')
    if missing and not allowed and not missing_fixed:reasons.append('unassessed-signed-chirality-change')
    charges_ok=bool(_explicit_formal_charges(left[0])) and _explicit_formal_charges(left[0])==_explicit_formal_charges(right[0])
    if not charges_ok:reasons.append('source-explicit-formal-charges-not-preserved')
    if stereo['stereochemistry']=='INVERTED':reasons.append('finished-source-relative-configuration-opposed')
    omissions=[{'center':c,'ordered_neighbors':list(n),'source_volume_sign':s,'all_neighbors':sorted(neighbors[c])}
               for c,n,s in missing] if allowed else []
    return {'schema_version':1,'policy_id':POLICY_ID,'component':code,'legacy_inspection':raw,'finished_stereo':stereo,
        'candidate_status':'REJECTED' if reasons else 'CANDIDATE_REVIEW','rejection_reasons':sorted(set(reasons)),
        'formal_charges_preserved':charges_ok,'unoriented_volume_omissions':omissions,
        'requires_native_tetrahedral_coverage':bool(omissions),'native_usability':'NOT_RUN',
        'absolute_cip_assignment':'NOT_RUN','requires_cif_review':False,'automatic_adoption':False,
        'scope':'SEPARATE_DICTIONARY; NO MECHANICAL EQUIVALENCE CLAIM'}


def native_energy_worker(base):
    """Opt in to two fixed evaluations; historical worker bytes stay unchanged."""
    token='    report["status"] = "REVIEW"\n'
    if base.count(token)!=1:raise ValueError('Native energy inventory insertion differs')
    block=r'''    from cctbx.geometry_restraints import flags as energy_flags, energies as energy_api
    import inspect
    report["energy_inventory"]={"policy_id":"cif-fixed-native-usability-energy-v1","status":"STARTED",
        "normalization":False,"evaluation_calls":0,"snapshots":[],"installed_sources":[]}
    for module in (energy_flags,energy_api,inspect.getmodule(geo.energies_sites)):
        path=Path(module.__file__).resolve(strict=True)
        report["energy_inventory"]["installed_sources"].append({"module":module.__name__,"historical_path":str(path),
            "sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    active=energy_flags.flags(default=True)
    original_sites=[[float(x) for x in p] for p in sites]
    for repeat in range(2):
        energy=geo.energies_sites(sites_cart=sites,flags=active,compute_gradients=True,normalization=False)
        report["energy_inventory"]["evaluation_calls"]+=1
        gradient=[float(x) for x in energy.gradients.as_double()];target=float(energy.target)
        if len(gradient)!=3*len(labels) or not all(math.isfinite(x) for x in [target,*gradient]):
            raise RuntimeError("Nonfinite or incomplete native usability energy/gradient")
        norm=math.sqrt(sum(x*x for x in gradient))
        if not math.isfinite(norm):raise RuntimeError("Nonfinite native usability gradient norm")
        report["energy_inventory"]["snapshots"].append({"target":target,"gradient":gradient,"gradient_norm":norm,
            "terms":{k:float(v) for k,v in vars(energy).items() if k.endswith("_residual_sum") and isinstance(v,(int,float))},
            "proxy_counts":{k:v for k,v in vars(energy).items() if k.startswith("n_") and k.endswith("_proxies") and (v is None or isinstance(v,int))}})
    if original_sites!=[[float(x) for x in p] for p in sites]:raise RuntimeError("Native energy inventory moved coordinates")
    report["energy_inventory"]["status"]="RECORDED"
'''
    return base.replace(token,block+token)


def _close(a,b):
    return type(a) in (float,int) and type(b) in (float,int) and math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8)


def energy_inventory_checks(native):
    """Recompute finite/repeat checks; target magnitude is not an acceptance score."""
    e=native.get('energy_inventory',{});s=e.get('snapshots',[]);n=native.get('atom_count')
    finite=(type(n) is int and len(s)==2 and all(type(v.get('target')) in (float,int) and math.isfinite(v['target'])
        and len(v.get('gradient',[]))==3*n and all(type(x) in (float,int) and math.isfinite(x) for x in v['gradient'])
        and _close(v.get('gradient_norm'),math.sqrt(sum(x*x for x in v['gradient']))) for v in s))
    repeat=finite and _close(s[0]['target'],s[1]['target']) and all(_close(a,b) for a,b in zip(s[0]['gradient'],s[1]['gradient']))
    return {'energy_inventory':e.get('policy_id')==ENERGY_POLICY_ID and e.get('status')=='RECORDED'
            and e.get('normalization') is False and e.get('evaluation_calls')==2,
            'finite_energy_and_gradient':finite,'fixed_coordinate_repeats':repeat}


def qualify_candidate_native(source,candidate,model,code,native):
    """Require isolated exact definitions, essential proxies and usable numbers."""
    from .cif_fragment_restoration import _model
    from .cif_fixed_geometry import _fixed_policy
    candidate=Path(candidate);assessment=reassess_complete_candidate(source,candidate,code);checks={};evidence={}
    values=_values(candidate,code);elements,orders,_,neighbors=_graph(values)
    checks['source_chemistry_and_configuration']=assessment['candidate_status']=='CANDIDATE_REVIEW'
    checks['native_completed']=native.get('status')=='REVIEW' and native.get('inventory_detail')=='linked'
    checks['no_native_fatal_or_unused']=native.get('fatal_problems') is None and native.get('unused_definitions')==[] and native.get('unsupported_fields')==[]
    try:
        _model(native,Path(model),coordinates_match=True);atoms=native['atoms'];indices={a['i_seq']:a['atom_id'] for a in atoms}
        checks['exact_model_and_component']=(len(indices)==len(elements) and set(indices.values())==set(elements)
            and all(a['identity']['resname'].strip()==code and a['element'].strip().upper()==elements[a['atom_id']] for a in atoms))
        checks['exact_native_sites']=native['geometry'].get('sites_cart_exact')==[a['xyz'] for a in atoms]
        mappings=native['monomer_mappings']['rows'];checks['one_complete_monomer']=(len(mappings)==1 and mappings[0]['resname'].strip()==code
            and all(mappings[0].get(k,{}).get('status')=='RECORDED' and mappings[0][k].get('atom_ids')==[]
                    for k in ['missing_non_hydrogen_atoms','missing_hydrogen_atoms','unexpected_atoms']))
        projections=definition_projection_checks(native,{mappings[0]['site']:(candidate,code)}) if len(mappings)==1 else []
        checks['exact_effective_definitions']=bool(projections) and all(r['status']=='PASS' for r in projections);evidence['definition_checks']=projections
        definition=mappings[0]['metadata']['effective_definition'] if len(mappings)==1 else {}
        expected_charges=_graph(values)[2]
        checks['no_contradictory_native_formal_charges']=all(r.get('charge') is None or _close(float(r['charge']),expected_charges[r['atom_id']]) for r in definition.get('atoms',[]))
        actual_orders={tuple(sorted([r['atom_id_1'],r['atom_id_2']])):_ORDERS.get(str(r['type']).upper()) for r in definition.get('bonds',[])}
        checks['effective_declared_bond_orders']=actual_orders==orders
        details=native['geometry']['proxy_details'];checks['no_competing_native_ss']=_fixed_policy(native)
        kinds={'bond_simple','bond_asu','angle','dihedral','const_dihedral','chirality','planarity','parallelity'}
        checks['proxy_counts_complete']=set(details)==kinds and all(isinstance(rows,list) and native['geometry']['proxy_counts'].get(k)==len(rows) for k,rows in details.items())
        def names(row):
            ids=row['i_seqs']
            if any(type(i) is not int or i not in indices for i in ids) or row['atoms']!=[atoms[i]['label'] for i in ids]:raise ValueError('Invalid native proxy identity')
            return tuple(indices[i] for i in ids)
        def key(a):return min(a,a[::-1])
        def numeric(row,fields):return all(type(row.get(k)) in (float,int) and math.isfinite(row[k]) for k in fields)
        checks['finite_positive_proxy_parameters']=True
        for kind,rows in details.items():
            for row in rows:
                names(row)
                if kind=='planarity':valid=len(row.get('weights',[]))==len(row['i_seqs']) and all(type(w) in (int,float) and math.isfinite(w) and w>0 for w in row['weights'])
                else:
                    fields=['weight']+(['distance_ideal'] if kind in {'bond_simple','bond_asu'} else ['angle_ideal'] if kind in {'angle','dihedral','const_dihedral'} else ['volume_ideal'] if kind=='chirality' else ['target_angle_deg'])
                    valid=numeric(row,fields) and row['weight']>0
                    if kind=='chirality':valid &= type(row.get('both_signs')) is bool and abs(row.get('volume_ideal',0))>0
                checks['finite_positive_proxy_parameters'] &= valid
        def matching(kind,category,size,target,source_target,esd):
            expected=Counter((key(tuple(r['atom_id_'+str(i)] for i in range(1,size+1))),format(float(r[source_target]),'.10g'),format(1/float(r[esd])**2,'.10g')) for r in _rows(values,category))
            actual=Counter((key(names(r)),format(float(r[target]),'.10g'),format(float(r['weight']),'.10g')) for r in details[kind])
            return expected==actual
        checks['exact_active_bonds']=not details['bond_asu'] and matching('bond_simple','_chem_comp_bond',2,'distance_ideal','value_dist','value_dist_esd')
        checks['exact_active_angles']=matching('angle','_chem_comp_angle',3,'angle_ideal','value_angle','value_angle_esd')
        from .dictionary_compatibility import normalize_torsion_block
        normalized,_=normalize_torsion_block(values)
        def angle(x):return format(float(x)%360.,'.10g')
        def alternatives(x):
            if x is None or x in ('','.','?'):return ()
            return tuple(sorted(angle(v) for v in (x if isinstance(x,(list,tuple)) else str(x).split(','))))
        torsions=Counter((key(tuple(r['atom_id_'+str(i)] for i in range(1,5))),angle(r['value_angle']),
            format(1/float(r['value_angle_esd'])**2,'.10g'),int(r['period']),alternatives(r.get('alt_value_angle')))
            for r in _rows(normalized,'_chem_comp_tor'))
        active_torsions=Counter((key(names(r)),angle(r['angle_ideal']),format(float(r['weight']),'.10g'),
            r['periodicity'],alternatives(r.get('alt_angle_ideals'))) for kind in ['dihedral','const_dihedral'] for r in details[kind])
        checks['exact_active_torsions']=torsions==active_torsions
        planes={}
        for r in _rows(values,'_chem_comp_plane_atom'):planes.setdefault(r['plane_id'],[]).append((r['atom_id'],format(1/float(r['dist_esd'])**2,'.10g')))
        expected_planes=Counter(tuple(sorted(rows)) for rows in planes.values())
        actual_planes=Counter(tuple(sorted(zip(names(r),(format(float(w),'.10g') for w in r['weights'])))) for r in details['planarity'])
        checks['exact_active_planes']=expected_planes==actual_planes and not details['parallelity']
        expected=[]
        for r in _rows(values,'_chem_comp_chir'):
            center=r['atom_id_centre'];ns=[r['atom_id_'+str(i)] for i in range(1,4)];sign=r['volume_sign'].lower()
            parity=(-1 if sum(ns[i]>ns[j] for i in range(3) for j in range(i+1,3))%2 else 1)
            expected.append((center,tuple(sorted(ns)),0 if sign=='both' else parity*(1 if sign.startswith('pos') else -1),sign=='both'))
        actual=[]
        for r in details['chirality']:
            center,*ns=names(r);parity=(-1 if sum(ns[i]>ns[j] for i in range(3) for j in range(i+1,3))%2 else 1)
            actual.append((center,tuple(sorted(ns)),0 if r['both_signs'] else parity*(1 if r['volume_ideal']>0 else -1),r['both_signs']))
        checks['exact_fixed_chirality_membership']=Counter(expected)==Counter(actual)
        # All four bonds and six angles must remain active at a source 'both'
        # centre whose generated dictionary omits that unoriented volume term.
        required=[];bondkeys={frozenset(names(r)) for r in details['bond_simple']};anglekeys={key(names(r)) for r in details['angle']}
        for omitted in assessment['unoriented_volume_omissions']:
            c=omitted['center'];ns=omitted['all_neighbors'];ok=all(frozenset([c,a]) in bondkeys for a in ns) and all(key((a,c,b)) in anglekeys for a,b in combinations(ns,2));required.append({'center':c,'complete_tetrahedral_coverage':ok})
        evidence['unoriented_volume_coverage']=required;checks['omitted_unoriented_volume_coverage']=all(r['complete_tetrahedral_coverage'] for r in required)
        # Retain classification and unsupported formal charge access separately;
        # the exact CIF formal declarations are checked before native loading.
        evidence['native_group']=mappings[0]['metadata'].get('group') if len(mappings)==1 else None
        evidence['formal_charge_readback']=mappings[0]['metadata'].get('formal_charge_readback',{'status':'UNSUPPORTED'}) if len(mappings)==1 else {'status':'UNSUPPORTED'}
        checks.update(energy_inventory_checks(native))
    except (KeyError,TypeError,ValueError,IndexError,ZeroDivisionError,OverflowError) as exc:
        checks['complete_native_evidence']=False;evidence['error']=type(exc).__name__+': '+str(exc)
    return {'schema_version':1,'policy_id':POLICY_ID,'component':code,'native_usable':all(checks.values()),
        'status':'ISOLATED_NATIVE_USABILITY_PASS' if all(checks.values()) else 'REVIEW','checks':checks,'evidence':evidence,
        'candidate_sha256':sha256(candidate.read_bytes()).hexdigest(),'source_assessment':assessment,
        'scope':'ISOLATED_COMPONENT_ONLY','linked_context':'NOT_RUN','absolute_cip_assignment':'NOT_RUN',
        'scientific_approval':'NOT_RUN','requires_cif_review':False,'automatic_adoption':False}


def covalent_proxy_signature(native):
    """Compare fixed covalent mechanics across coordinate sets by atom name."""
    index={r['i_seq']:r['atom_id'] for r in native['atoms']};result={}
    for kind,rows in native['geometry']['proxy_details'].items():
        records=[]
        for row in rows:
            r={k:v for k,v in row.items() if k not in {'i_seqs','atoms','j_seqs','j_atoms'}}
            ns=tuple(index[i] for i in row['i_seqs'])
            if kind in {'bond_simple','bond_asu','angle','dihedral','const_dihedral'}:ns=min(ns,ns[::-1])
            if kind=='chirality':
                center,*others=ns;parity=(-1 if sum(others[i]>others[j] for i in range(3) for j in range(i+1,3))%2 else 1)
                ns=(center,*sorted(others));r['volume_ideal']=abs(r['volume_ideal']) if r['both_signs'] else parity*r['volume_ideal']
            if kind=='planarity':
                pairs=sorted(zip(ns,r.pop('weights')));ns=tuple(n for n,w in pairs);r['weights']=[w for n,w in pairs]
            r['atom_names']=list(ns)
            def normalize(v):
                if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
                if isinstance(v,(list,tuple)):return [normalize(x) for x in v]
                if type(v) is float:return format(v,'.12g')
                return v
            records.append(json.dumps(normalize(r),sort_keys=True,separators=(',',':')))
        result[kind]=sorted(records)
    return result


def isolated_candidate_decision(source,candidate,code,qualification,stopping):
    """Feed verified adapter evidence to the existing core, without adoption."""
    from .cif_doctor_selection import ComponentCandidate,select_component_candidate
    q=qualification;a=q['source_assessment'];v=_values(source,code);elements,orders,charges,_=_graph(v)
    stereo=reader_stereo_inventory(source,code)
    fixed=[r for r in _comparison_inventory(a['legacy_inspection']['source_assessment']['components'][0])['signed_chirality'] if r[2]!='both']
    state={'component':code,'elements':elements,'bonds':[[list(k),o] for k,o in sorted(orders.items())],'charges':charges,
        'atom_stereo':{n:r['declared_stereo'] for n,r in stereo['atoms'].items()},'fixed_signed_chirality':fixed}
    chemistry=sha256(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    notes=['Isolated component checks passed; linked scaffold qualification and independent absolute CIP remain separate.'
        if q['native_usable'] else 'Isolated native usability was not established; existing production dictionaries remain in use.']
    if a['unoriented_volume_omissions']:notes.append('Generated output omits a source unoriented volume term; complete native tetrahedral bond/angle coverage is required for selection.')
    if any(r['role']=='generated' for r in a['legacy_inspection']['numerical_issues']):notes.append('Dictionary geometry findings remain recorded with the candidate.')
    converged=False if stopping=='NOT_CONVERGED_REPORTED' else None
    if converged is None:notes.append('The optimizer log does not provide a qualified convergence verdict.')
    record=ComponentCandidate(candidate_id='source_native_generated',component=code,source_priority=0,
        artifact_sha256=q['candidate_sha256'],chemistry_sha256=chemistry,integrity_verified=True,native_usable=q['native_usable'],
        chemistry_preserved=a['candidate_status']=='CANDIDATE_REVIEW',essential_restraints_present=q['native_usable'],
        finite_parameters=q['checks'].get('finite_positive_proxy_parameters',False),stereochemistry=a['finished_stereo']['stereochemistry'],
        converged=converged,warnings=tuple(notes))
    result=select_component_candidate([record]);result.update(scope='ISOLATED_COMPONENT_ONLY',linked_adoption='NOT_RUN',production_pipeline='UNCHANGED')
    if not result['continue_solving']:result['report_text']='The generated candidate was not selected by this isolated check; existing production dictionaries were preserved.'
    return result
