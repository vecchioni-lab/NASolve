"""Opt-in native end-state and custom-restraint checks; no chemistry inference."""
from collections import Counter
from math import isfinite
import json
import re
from copy import deepcopy

POLICY_ID='cif-explicit-site-native-context-v1'
FULL_MODEL_POLICY_ID='cif-explicit-site-native-context-v2'
RETAINED_TERMINAL_POLICY_ID='cif-explicit-site-native-context-v3'
MAPPED_TERMINAL_POLICY_ID='cif-explicit-site-native-context-v4'


def validate_native_context(context):
    retained=isinstance(context,dict) and context.get('policy_id') in (RETAINED_TERMINAL_POLICY_ID,MAPPED_TERMINAL_POLICY_ID)
    full=retained or isinstance(context,dict) and context.get('policy_id')==FULL_MODEL_POLICY_ID
    keys={'policy_id','custom_restraints'}|({'monomer_inventory'} if full else set())
    if retained:keys.add('retained_terminal_phosphates')
    if (not isinstance(context,dict) or set(context)!=keys
            or context['policy_id'] not in (POLICY_ID,FULL_MODEL_POLICY_ID,RETAINED_TERMINAL_POLICY_ID,MAPPED_TERMINAL_POLICY_ID)
            or not isinstance(context['custom_restraints'],str)
            or context['custom_restraints'] not in {'required','absent'}
            or (full and context['monomer_inventory']!='full_model')):
        raise ValueError('Require an explicit supported native site/restraint context')
    if retained:
        rows=context['retained_terminal_phosphates']
        def site(value):
            return isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_]:-?[0-9]+',value) is not None
        if (not isinstance(rows,list) or not rows or any(not isinstance(row,dict)
                or set(row)!={'site','component','outgoing_site'} or not site(row['site'])
                or not isinstance(row['component'],str)
                or re.fullmatch(r'[A-Za-z0-9]{1,3}',row['component']) is None
                or row['outgoing_site']==row['site']
                or (row['outgoing_site'] is not None and not site(row['outgoing_site'])) for row in rows)
                or [r['site'] for r in rows]!=sorted({r['site'] for r in rows})):
            raise ValueError('Require unique ordered explicit retained terminal phosphate declarations')
    return deepcopy(context)


def prepared_native_context(model, model_context, *, custom_restraints, retained_policy=MAPPED_TERMINAL_POLICY_ID):
    """Carry audited, explicitly requested background termini into native checks.

    The caller supplies the existing validated prepared-model context. Coordinates
    identify the component; they never authorize a phosphate absent from intent.
    """
    from .cif_linked_preparation import _model_inventory
    if retained_policy not in (RETAINED_TERMINAL_POLICY_ID,MAPPED_TERMINAL_POLICY_ID):
        raise ValueError('Unsupported retained terminal declaration policy')
    selected={row['site'] for rows in model_context['contexts'].values() for row in rows}
    outgoing=dict(model_context['expected_links'])
    sites=_model_inventory(model)
    retained=[dict(site=site,component=sites[site]['code'],outgoing_site=outgoing.get(site))
        for site in sorted(set(model_context['intent']['post_mr_plan']['allow_op3_sites'])-selected)]
    result=dict(policy_id=FULL_MODEL_POLICY_ID,monomer_inventory='full_model',custom_restraints=custom_restraints)
    if retained:result.update(policy_id=retained_policy,retained_terminal_phosphates=retained)
    return validate_native_context(result)


def native_context_options(context):
    """Exact optional native observations selected by the frozen context."""
    context=validate_native_context(context)
    result={'full_monomer_inventory':True} if context.get('monomer_inventory')=='full_model' else {}
    if context['policy_id']==MAPPED_TERMINAL_POLICY_ID:result['atom_name_mapping']=True
    return result


def _observed_names(native):
    from .cif_native_atom_mapping import bound_name_mappings
    from .cif_linked_qualification import _site
    atoms=native['atoms']
    if any(type(a.get('i_seq')) is not int or a['i_seq']!=i for i,a in enumerate(atoms)):
        raise ValueError('Native name bindings need complete ordered atom indices')
    summary,maps=bound_name_mappings(native,[(_site(a),a['identity']['resname'].strip(),a['atom_id']) for a in atoms])
    if summary['status']!='RECORDED':raise ValueError('Retained terminal native names are unavailable')
    return maps


def declared_phosphate_check(native,preparations,expected_links,*,retained=(),baseline=None,mapped=False):
    """Authorize OP3 only at a declared, source-preserved terminal phosphate.

    Full definition/projection and active numerical checks remain mandatory in
    the caller. This checks the coordinate identity and native phosphate graph;
    it does not infer protonation or permit the unsupported O3P alias.
    """
    from .cif_linked_qualification import _site
    evidence={};passed=False
    try:
        plans=[p for preparation in preparations for p in preparation['sites']]
        name_maps={}
        if mapped:
            old_names,new_names=_observed_names(baseline),_observed_names(native)
            for row in retained:
                site=row['site']
                if old_names.get(site)!=new_names.get(site):raise ValueError('Retained terminal atom-name binding changed')
                name_maps[site]=new_names[site]
        if len({p['site'] for p in plans})!=len(plans):raise ValueError('Duplicate declared site')
        if retained:
            original={r['site']:r['metadata']['effective_definition'] for r in baseline['monomer_mappings']['rows']}
            current={r['site']:r['metadata']['effective_definition'] for r in native['monomer_mappings']['rows']}
            planned={p['site'] for p in plans}
            for row in retained:
                site=row['site']
                if site in planned:raise ValueError('Retained terminal phosphate overlaps replaced component')
                definition=original.get(site)
                if not isinstance(definition,dict) or current.get(site)!=definition:
                    raise ValueError('Retained terminal phosphate native definition changed or is unavailable')
                plans.append(dict(row,incoming_site=None,five_prime_state='phosphate',
                    three_prime_state='linked' if row['outgoing_site'] is not None else 'free_OH',
                    expected_atoms=[a['atom_id'] for a in definition['atoms']]))
        terminal={p['site']:p for p in plans if p.get('five_prime_state')=='phosphate'}
        expected={'P':'P','OP1':'O','OP2':'O','OP3':'O',"O5'":'O'}
        atoms={};mapping={r['site']:r for r in native['monomer_mappings']['rows']}
        for a in native['atoms']:
            key=(_site(a),a['atom_id'])
            if key in atoms:raise ValueError('Duplicate coordinate identity')
            atoms[key]=a
        observed=sorted(site for site,name in atoms if name=='OP3')
        if any(name=='O3P' for site,name in atoms):raise ValueError('Unrequested coordinate O3P')
        if observed!=sorted(terminal):raise ValueError('Coordinate OP3 differs from declared terminal sites')
        for site,plan in terminal.items():
            names={name:name_maps[site][name] if site in name_maps else name for name in expected}
            if (plan.get('incoming_site') is not None or any(right==site for left,right in expected_links)
                    or [right for left,right in expected_links if left==site] != (
                        [] if plan.get('outgoing_site') is None else [plan['outgoing_site']])
                    or plan.get('three_prime_state')!=('linked' if plan.get('outgoing_site') is not None else 'free_OH')
                    or not set(names.values())<=set(plan['expected_atoms'])):
                raise ValueError('Terminal phosphate conflicts with linkage or source projection')
            definition=mapping[site]['metadata']['effective_definition']
            rows=definition['atoms'];source={r['atom_id']:r for r in rows}
            if len(source)!=len(rows):raise ValueError('Duplicate effective atom')
            for name,element in expected.items():
                atom=atoms[(site,name)]
                if (atom['element'].strip().upper()!=element
                        or atom['identity']['resname'].strip()!=plan['component']
                        or source[names[name]]['type_symbol'].upper()!=element):
                    raise ValueError('Terminal phosphate component or element differs')
            edges=[(r['atom_id_1'],r['atom_id_2']) for r in definition['bonds']]
            phosphorus,leaving=names['P'],names['OP3']
            neighbors=[b if a==phosphorus else a for a,b in edges if phosphorus in (a,b)]
            if Counter(neighbors)!=Counter({names[n]:1 for n in ('OP1','OP2','OP3',"O5'")}):
                raise ValueError('Terminal phosphate does not have the declared four oxygen neighbors')
            if [b if a==leaving else a for a,b in edges if leaving in (a,b)].count(phosphorus)!=1:
                raise ValueError('Terminal oxygen is not attached exactly once to its phosphorus')
            heavy=[n for a,b in edges if leaving in (a,b) for n in [b if a==leaving else a]
                if source[n]['type_symbol'].upper() not in {'H','D'}]
            if heavy!=[phosphorus]:raise ValueError('Terminal oxygen has another heavy-atom attachment')
        evidence.update(declared_terminal_sites=sorted(terminal),observed_op3_sites=observed)
        if retained:evidence['retained_terminal_sites']=[r['site'] for r in retained]
        if mapped:evidence['retained_atom_name_bindings']=name_maps
        passed=True
    except (KeyError,TypeError,ValueError,IndexError,AttributeError) as exc:
        evidence['error']=type(exc).__name__+': '+str(exc)
    return {'check':'declared-terminal-coordinate-phosphates','status':'PASS' if passed else 'REVIEW',**evidence}


def _signature(native,kind,row):
    from .cif_terminal_qualification import _proxy_subset
    if kind not in {'bond','angle','dihedral','planarity','parallelity'}:
        raise ValueError('Unsupported explicit restraint kind')
    wrapped={**native,'geometry':{'proxy_details':{kind:[row]}}}
    _proxy_subset(wrapped,set(),kind)  # Bind every label and both planes to actual indices.
    ids=row['i_seqs'];atoms=tuple(row['atoms'])
    count={'bond':2,'angle':3,'dihedral':4}.get(kind)
    if len(ids)!=len(set(ids)) or (count is not None and len(ids)!=count):
        raise ValueError('Repeated or incomplete custom restraint endpoints')
    def number(value,positive=False):
        if type(value) not in (int,float) or not isfinite(value) or (positive and value<=0):
            raise ValueError('Invalid custom target or weight')
        return value
    if kind=='planarity':
        weights=row['weights']
        if len(atoms)<3 or len(weights)!=len(atoms):raise ValueError('Incomplete custom plane')
        return kind,tuple(sorted((a,number(w,True)) for a,w in zip(atoms,weights)))
    weight=number(row['weight'],True)
    if kind=='bond':return kind,tuple(sorted(atoms)),number(row['distance_ideal'],True),weight
    if kind=='parallelity':
        other=tuple(row['j_atoms']);indices=row['j_seqs']
        if len(atoms)<3 or len(other)<3 or len(indices)!=len(set(indices)) or set(ids)&set(indices):
            raise ValueError('Incomplete parallelity plane')
        if row.get('slack',0)!=0 or row.get('top_out',False) is not False:
            raise ValueError('Unsupported parallelity slack or top-out')
        return kind,tuple(sorted((tuple(sorted(atoms)),tuple(sorted(other))))),number(row['target_angle_deg']),weight
    target=number(row['angle_ideal'])
    if kind=='angle':return kind,min(atoms,atoms[::-1]),target,weight
    if type(row['periodicity']) is not int or row['periodicity']<0 or row.get('alt_angle_ideals') not in (None,[]):
        raise ValueError('Unsupported custom torsion convention')
    return kind,atoms,target,weight,row['periodicity']


def custom_restraint_check(before,after,context):
    """Require a one-to-one exact realization of the declared native edits.

    NARestraints/explicit PHIL own the targets. No tolerance, origin-only waiver,
    dropped request or duplicate proxy may substitute for faithful consumption.
    An explicit absent declaration requires zero requests and zero edit proxies.
    """
    from .cif_construction_native import NATIVE_KINDS
    from .cif_fixed_geometry import _fixed_policy
    context=validate_native_context(context);evidence={};passed=False
    try:
        raw=[]
        for label,native in [('before',before),('after',after)]:
            if not _fixed_policy(native):raise ValueError('Competing or incomplete native restraint policy')
            requests=native['geometry']['custom_proxy_requests']
            if not isinstance(requests,list):raise ValueError('Missing explicit custom request inventory')
            expected=Counter()
            for request in requests:
                if request.get('action')!='add' or not isinstance(request.get('selections'),list) or not request['selections']:
                    raise ValueError('Unsupported or unbound custom action')
                if any(not isinstance(s,str) or not s.strip() for s in request['selections']):
                    raise ValueError('Empty custom selection')
                expected[_signature(native,request['kind'],request)]+=1
            if any(count!=1 for count in expected.values()):raise ValueError('Duplicate custom request')
            details=native['geometry']['proxy_details']
            if set(details)!=NATIVE_KINDS:raise ValueError('Incomplete native proxy families')
            actual=Counter();origin=native['restraint_policy']['origin_ids']['edits']
            for kind,rows in details.items():
                if not isinstance(rows,list):raise ValueError('Missing native proxy family')
                for row in rows:
                    if type(row.get('origin_id')) is not int:raise ValueError('Unrecorded native proxy origin')
                    if row['origin_id']!=origin:continue
                    if kind=='bond_simple' and row.get('symmetry_operation') not in (None,'x,y,z'):
                        raise ValueError('Custom symmetry restraint requires separate qualification')
                    actual[_signature(native,'bond' if kind=='bond_simple' else kind,row)]+=1
            if actual!=expected:raise ValueError('Custom requests and native edit proxies differ')
            if bool(expected)!=(context['custom_restraints']=='required'):
                raise ValueError('Custom restraint presence differs from frozen intent')
            evidence[label+'_requests']=sum(expected.values())
            raw.append(json.dumps(requests,sort_keys=True,allow_nan=False))
        if raw[0]!=raw[1]:raise ValueError('Custom selections, actions or targets changed')
        passed=True
    except (KeyError,TypeError,ValueError,IndexError,AttributeError) as exc:
        evidence['error']=type(exc).__name__+': '+str(exc)
    return {'check':'declared-custom-restraint-realization','status':'PASS' if passed else 'REVIEW',
        'custom_restraints':context['custom_restraints'],**evidence}
