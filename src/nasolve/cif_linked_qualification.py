"""Checks on actual native site definitions and exact custom proxy coverage."""
from __future__ import annotations

from collections import Counter
import json
from math import isfinite


def _site(atom: dict) -> str:
    identity=atom['identity']
    return (identity['chain_id'].strip() or '_')+':'+identity['resseq'].strip()+identity['icode'].strip()


def _number(value):
    if value is None: raise ValueError('Native target/weight unavailable')
    value=float(value)
    if not isfinite(value): raise ValueError('Native target/weight nonfinite')
    return format(value,'.12g')


def proxy_signature(kind: str, row: dict) -> tuple:
    """Canonicalize equivalent endpoint orders without losing target or weight."""
    atoms=tuple(row['atoms'])
    if kind in {'bond','bond_simple'}:
        return ('bond',tuple(sorted(atoms)),_number(row['distance_ideal']),_number(row['weight']))
    if kind=='angle':
        return (kind,min(atoms,atoms[::-1]),_number(row['angle_ideal']),_number(row['weight']))
    if kind=='planarity':
        return (kind,tuple(sorted((atom,_number(weight)) for atom,weight in zip(atoms,row['weights']))))
    if kind=='parallelity':
        planes=tuple(sorted((tuple(sorted(atoms)),tuple(sorted(row['j_atoms'])))))
        return (kind,planes,_number(row['target_angle_deg']),_number(row['weight']))
    if kind=='dihedral':
        return (kind,atoms,_number(row['angle_ideal']),_number(row['weight']),row['periodicity'])
    # Preserve full native conventions for non-custom/rest-of-manager checks.
    return (kind,json.dumps({key:value for key,value in row.items()
                            if key not in {'i_seqs','j_seqs'}},sort_keys=True))


def declared_linear_links(chains: dict[str, list[str]]) -> list[tuple[str,str]]:
    """Expand an explicit linear-strand contract, never infer it from distances."""
    return [(chain+':'+left,chain+':'+right) for chain,sites in chains.items()
            for left,right in zip(sites,sites[1:])]


def native_backbone_links(native: dict) -> dict:
    atoms={row['i_seq']:row for row in native['atoms']}
    links={}
    for proxy in native['geometry']['simple_bonds']:
        endpoints=[atoms[index] for index in proxy['i_seqs']]
        if {row['atom_id'] for row in endpoints}!={"O3'",'P'}: continue
        left=next(row for row in endpoints if row['atom_id']=="O3'")
        right=next(row for row in endpoints if row['atom_id']=='P')
        if _site(left)==_site(right): continue
        key=(_site(left),_site(right))
        if key in links: raise ValueError('Duplicate native backbone link')
        links[key]={'target':proxy['distance_ideal'],'weight':proxy['weight']}
    for proxy in native['geometry'].get('asu_bonds',[]):
        endpoints=[atoms[index] for index in proxy['i_seqs']]
        if {row['atom_id'] for row in endpoints}=={"O3'",'P'}:
            raise ValueError('Symmetry backbone linkage requires a separate reviewed context')
    return links


def site_definition_checks(linked: dict, preparations: list[dict]) -> list[dict]:
    """Validate actual effective chemistry for each independently selected site."""
    checks=[]
    def check(name,passes,**evidence): checks.append({'check':name,'status':'PASS' if passes else 'REVIEW',**evidence})
    mappings={row['site']:row for row in linked['monomer_mappings']['rows']}
    for preparation in preparations:
        for expected in preparation['sites']:
            site=expected['site']
            actual=mappings.get(site,{})
            metadata=actual.get('metadata',{})
            definition=metadata.get('effective_definition',{})
            atoms={row['atom_id']:row for row in (definition.get('atoms') or [])}
            expected_atoms=set(expected['expected_atoms'])
            check('effective-site-atoms:'+site,set(atoms)==expected_atoms,
                  missing=sorted(expected_atoms-set(atoms)),extra=sorted(set(atoms)-expected_atoms))
            check('effective-site-polymer-group:'+site,metadata.get('group')=='DNA',
                  expected='DNA',observed=metadata.get('group'),
                  native_classification=metadata.get('classification',{'status':'NOT_RECORDED'}))
            check('effective-site-energy-types:'+site,all(atoms.get(name,{}).get('type_energy')==energy
                  for name,energy in expected['expected_energy_types'].items()))
            formal_unavailable=[];formal_contradictions=[]
            for name,charge in expected['expected_formal_charges'].items():
                observed=atoms.get(name,{}).get('charge')
                evidence={'atom_id':name,'expected':charge,'observed':observed}
                try:
                    if _number(observed)!=_number(charge):formal_contradictions.append(evidence)
                except (TypeError,ValueError):formal_unavailable.append(evidence)
            checks.append({'check':'effective-site-formal-charges:'+site,
                'status':'REVIEW' if formal_contradictions else 'UNSUPPORTED' if formal_unavailable
                         or not expected['expected_formal_charges'] else 'PASS',
                'unavailable':formal_unavailable,'contradictions':formal_contradictions,
                'native_readback':metadata.get('formal_charge_readback',{'status':'NOT_RECORDED'}),
                'partial_charge_substituted':False})
            bonds=definition.get('bonds') or []
            hydrogen_neighbors={name:sorted(row['atom_id_2'] if row['atom_id_1']==name else row['atom_id_1']
                for row in bonds if name in (row['atom_id_1'],row['atom_id_2']))
                for name,atom in atoms.items() if atom.get('type_symbol','').upper() in {'H','D'}}
            check('effective-site-hydrogen-adjacency:'+site,hydrogen_neighbors==expected['expected_hydrogen_attachments'])
            dangling=[]
            for category,rows in definition.items():
                if rows is None: dangling.append(category+':unavailable');continue
                for row in rows:
                    dangling.extend(value for key,value in row.items() if key.startswith('atom_id') and value not in atoms)
            check('no-dangling-site-references:'+site,not dangling,dangling=dangling)
    return checks


def qualify_linked_bundle(baseline: dict, linked: dict, preparations: list[dict],
                         expected_links: list[tuple[str,str]], free_five_prime_sites: list[str]) -> dict:
    """Mechanics qualification only; numerical geometry/protonation stay reviewable."""
    checks=[]
    def check(name,passes,**evidence): checks.append({'check':name,'status':'PASS' if passes else 'REVIEW',**evidence})
    if baseline.get('inventory_detail')!='linked' or linked.get('inventory_detail')!='linked':
        return {'schema_version':1,'status':'REVIEW','checks':[{'check':'detailed-native-inventory','status':'UNSUPPORTED'}]}
    check('native-interpreter',linked.get('status')=='REVIEW' and linked.get('fatal_problems') is None
          and not linked.get('unused_definitions') and not linked.get('unsupported_fields'))
    check('unchanged-native-model',baseline.get('atoms')==linked.get('atoms'))
    check('zero-unrequested-coordinate-OP3',not any(a['atom_id'] in {'OP3','O3P'} for a in linked['atoms']))
    before_links,after_links=native_backbone_links(baseline),native_backbone_links(linked)
    check('exact-backbone-links',set(after_links)==set(expected_links) and after_links==before_links,
          expected=len(expected_links),observed=len(after_links))
    mappings={row['site']:row for row in linked['monomer_mappings']['rows']}
    check('all-monomer-mappings',len(mappings)==len(baseline['monomer_mappings']['rows'])
          and all(not r.get('unexpected_atoms',{}).get('atom_ids') and not r.get('missing_non_hydrogen_atoms',{}).get('atom_ids')
                  for r in mappings.values()))
    check('declared-free-five-prime-ends',all(site in mappings and not
          {'P','OP1','OP2','OP3','O3P'} & set(mappings[site]['metadata']['atom_ids']) for site in free_five_prime_sites))
    checks.extend(site_definition_checks(linked,preparations))
    affected={site['site'] for preparation in preparations for site in preparation['sites']}
    try:
        expected=linked['geometry']['custom_proxy_requests']
        previous=baseline['geometry']['custom_proxy_requests']
        counts=Counter(row['kind'] for row in expected)
        failures=[]
        for request in expected:
            kind=request['kind'];proxy_kind='bond_simple' if kind=='bond' else kind
            signature=proxy_signature(kind,request)
            matches=sum(proxy_signature(kind,row)==signature for row in linked['geometry']['proxy_details'][proxy_kind])
            if matches!=1: failures.append({'kind':kind,'atoms':request['atoms'],'matches':matches})
        # Exact requested atom selections, targets and weights must remain the
        # same between the old manager and the source-preserving derivative.
        requests_equal=Counter(proxy_signature(row['kind'],row) for row in expected)==Counter(
            proxy_signature(row['kind'],row) for row in previous)
        check('exact-custom-restraint-coverage',bool(expected) and requests_equal and not failures,
              requested=dict(counts),failures=failures)
        before=Counter(proxy_signature('parallelity',row) for row in baseline['geometry']['proxy_details']['parallelity'])
        after=Counter(proxy_signature('parallelity',row) for row in linked['geometry']['proxy_details']['parallelity'])
        check('preserved-pair-and-stacking-parallelities',before==after,
              missing=sum((before-after).values()),extra=sum((after-before).values()))
        # Retained components' internal definitions are outside this change.
        unchanged_before={row['site']:row['metadata'].get('effective_definition') for row in baseline['monomer_mappings']['rows'] if row['site'] not in affected}
        unchanged_after={row['site']:row['metadata'].get('effective_definition') for row in linked['monomer_mappings']['rows'] if row['site'] not in affected}
        check('preserved-other-component-definitions',unchanged_before==unchanged_after)
    except (KeyError,TypeError,ValueError) as exc:
        check('native-proxy-coverage-available',False,error=str(exc))
    return {'schema_version':1,'audit_kind':'cif_linked_native_qualification',
            'status':'LINKED_MECHANICS_PASS' if all(row['status']=='PASS' for row in checks) else 'REVIEW',
            'checks':checks,'automatic_adoption':False,'scientific_approval':'NOT_RUN',
            'numerical_geometry':'REVIEW_REQUIRED','experimental_protonation':'UNASSESSED',
            'achieved_model_geometry':'NOT_RUN','generated_stereochemical_metadata':'REVIEW_REQUIRED'}
