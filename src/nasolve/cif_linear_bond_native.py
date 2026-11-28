"""Source-rebuilt target-only dictionary changes in complete native inventories.

This gate checks delivery, not reference authority, parameter calibration or
chemical survival. It reuses existing captures and never executes native code.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_doctor import _ORDERS
from .cif_linear_bond_reference import prepare_linear_bond_candidate, _pair
from .cif_linked_linear_torsion import _exact, _identity, _need
from .cif_native_monomers import review_full_monomers

POLICY_ID = 'cif-linked-linear-bond-target-inventory-v1'


def _qualify(before, after, source, dictionary, component, reference, candidate, bonds):
    with TemporaryDirectory(prefix='nasolve-bond-target-replay-') as scratch:
        rebuilt=Path(scratch).resolve()/'candidate.cif'
        plan=prepare_linear_bond_candidate(source,dictionary,component,reference,rebuilt,bonds=bonds)
        _need(candidate.read_bytes()==rebuilt.read_bytes(),
              'Candidate differs from the exact source/reference target plan')
    for native in (before,after):
        _need(native.get('status')=='REVIEW' and native.get('fatal_problems') is None
              and native.get('unsupported_fields')==[] and native.get('unused_definitions')==[]
              and native.get('inventory_detail')=='linked','Require supported linked native inventories')
        review_full_monomers(native)
    expected=deepcopy(before);actual=deepcopy(after)
    changes={tuple(row['atoms']):row for row in plan['changes']}

    def update_definition(metadata):
        _need(metadata['id']==component,'Mapped native component differs')
        rows=metadata['effective_definition']['bonds']
        for pair,change in changes.items():
            matches=[row for row in rows if _pair([row['atom_id_1'],row['atom_id_2']])==pair]
            _need(len(matches)==1,'Missing or ambiguous effective native bond definition')
            row=matches[0]
            _need(_exact(row['value_dist'],change['target_angstrom'])
                  and _exact(row['value_dist_esd'],change['dictionary_esd_angstrom'])
                  and _ORDERS.get(str(row['type']).upper())==change['declared_order']
                  and row.get('value_dist_neutron') is None,
                  'Effective native definition differs from the selected dictionary bond')
            row['value_dist']=change['reference_equilibrium_angstrom']

    providers=[m for row in expected['dictionary_loading'] for m in row['component_metadata'] if m['id']==component]
    _need(len(providers)==1,'Require one native dictionary provider for the component')
    update_definition(providers[0]);selected={}
    for row in expected['monomer_mappings']['rows']:
        identity=_identity(row['literal_identity'])
        if identity[-1]==component:
            _need(identity not in selected,'Ambiguous native component mapping')
            update_definition(row['metadata']);selected[identity]={}
    _need(bool(selected),'No modeled occurrence of the component')
    index={}
    for atom in before['atoms']:
        i=atom['i_seq'];identity=_identity(atom['identity'])
        _need(type(i) is int and 0<=i<before['atom_count'] and i not in index,
              'Invalid or duplicate native atom index')
        index[i]=atom
        if identity in selected:
            names=selected[identity];name=atom['atom_id']
            _need(name not in names,'Ambiguous modeled atom identity');names[name]=i
    _need(len(index)==before['atom_count'],'Incomplete native atom indices')
    chosen={}
    for names in selected.values():
        for pair,change in changes.items():
            _need(all(a in names for a in pair),'Selected bond has missing modeled atoms')
            key=tuple(sorted(names[a] for a in pair))
            _need(key not in chosen,'Repeated selected native bond');chosen[key]=change
    geometry=expected['geometry']
    _need(not any(tuple(sorted(p['i_seqs'])) in chosen for p in geometry['proxy_details']['bond_asu']),
          'Selected bond has an unqualified symmetry-related proxy')
    for rows in (geometry['simple_bonds'],geometry['proxy_details']['bond_simple']):
        for pair,change in chosen.items():
            matches=[row for row in rows if tuple(sorted(row['i_seqs']))==pair]
            _need(len(matches)==1,'Missing or ambiguous selected native simple bond')
            row=matches[0]
            _need(type(row.get('origin_id')) is int and row['origin_id']==0
                  and row.get('symmetry_operation') in (None,'x,y,z')
                  and row['atoms']==[index[i]['label'] for i in row['i_seqs']]
                  and _exact(row['distance_ideal'],change['target_angstrom'])
                  and _exact(row['weight'],1/change['dictionary_esd_angstrom']**2),
                  'Selected native bond target, strength, labels or origin differ')
            row['distance_ideal']=change['reference_equilibrium_angstrom']
    # Changed energies require separate attribution/derivative qualification.
    # Everything else, including future unknown categories, must remain exact.
    expected.pop('energy_inventory',None);actual.pop('energy_inventory',None)
    checks={k:k in expected and k in actual and _exact(expected[k],actual[k]) for k in sorted(set(expected)|set(actual))}
    passed=all(checks.values())
    return dict(schema_version=1,policy_id=POLICY_ID,status='REVIEW',component=component,
        inventory_checks_pass=passed,checks=checks,plan=plan,modeled_occurrences=len(selected),
        changed_native_bonds=len(chosen),component_origin_preserved=passed,
        candidate_rebuilt_exactly=True,native_provenance='CALLER_MUST_AUTHENTICATE',
        reference_authority='NOT_QUALIFIED',source_chemical_qualification='CALLER_REQUIRED',
        energy_delta_qualification='NOT_RUN',derivative_qualification='NOT_RUN',
        achieved_geometry='NOT_ASSESSED',scientific_approval='NOT_RUN',automatic_adoption=False)


def qualify_linked_linear_bond_candidate(before, after, source, dictionary, component,
                                        reference, candidate, *, bonds):
    """Check every modeled copy and all unselected definitions/proxies exactly.

    Caller supplies authenticated inventories; the captured wrapper below binds
    those to the actual ordered inputs and native consumer. No reference provider
    or restraint strength acquires scientific approval from this inventory gate.
    """
    paths=[Path(p) for p in (source,dictionary,candidate)]
    frozen=[p.read_bytes() for p in paths]
    try:
        return _qualify(before,after,*paths[:2],component,reference,paths[2],bonds)
    except (KeyError,TypeError,IndexError,AttributeError,OverflowError) as exc:
        raise ValueError('Incomplete native bond-target qualification evidence') from exc
    finally:
        _need([p.read_bytes() for p in paths]==frozen,'Bond-target qualification input changed')


def qualify_captured_linear_bond_candidate(source, component, reference, candidate,
        before_receipt, after_receipt, *, dictionary_index, bonds):
    """Bind two maintained captures, changing only the explicit dictionary slot.

    Uses the existing complete capture reader and repair-chain context. Returned
    hashes refer to exact supplied roots; no host path is operational authority.
    Stored native workers are never executed and no new capture or owner is made.
    """
    from .cif_captured_mixed_gradients import _inputs
    from .cif_repair_chain import _context
    from .cif_native_monomers import POLICY_ID as MONOMER_POLICY
    from .cif_dictionary_store import _regular
    source,candidate=Path(source),Path(candidate)
    receipts=[Path(p) for p in (before_receipt,after_receipt)]
    frozen={p:_regular(p) for p in (source,candidate,*receipts)}
    try:
        _need(all(p.name=='native_receipt.json' for p in receipts),'Require exact native capture receipts')
        entries=[_inputs(p.parent) for p in receipts];first,last=entries
        _need(type(dictionary_index) is int and 0<=dictionary_index<len(first[2]),'Invalid dictionary slot')
        for entry in entries:
            _need(entry[0].get('full_monomer_inventory_policy')==MONOMER_POLICY,
                  'Require captured complete monomer mappings')
        producer=first[0];digest=producer.get('executable_sha256')
        _need(isinstance(digest,str) and len(digest)==64
              and all(c in '0123456789abcdef' for c in digest)
              and isinstance(producer.get('api_sources'),list) and bool(producer['api_sources']),
              'Incomplete captured native producer identity')
        _need(_exact(_context(first),_context(last)),'Native model, PHIL or consumer context differs')
        # Keep all capture flags exact as well as the repair-chain context.
        from .cif_dictionary_store import _json
        options=[]
        for p in receipts:
            spec=_json((p.parent/'native_spec.json').read_bytes())
            options.append({k:v for k,v in spec.items() if k not in ('model','dictionaries','phil_files')})
        _need(_exact(*options),'Native capture options differ')
        original=[_regular(p) for p in first[2]];expected=list(original)
        expected[dictionary_index]=frozen[candidate]
        _need([_regular(p) for p in last[2]]==expected,'Native ordered dictionaries differ from the single candidate replacement')
        result=qualify_linked_linear_bond_candidate(first[4],last[4],source,first[2][dictionary_index],component,
                                                  reference,candidate,bonds=bonds)
        _need(result['inventory_checks_pass'],'Native changes exceed the selected dictionary bond targets')
        _need(entries==[_inputs(p.parent) for p in receipts], 'Native capture evidence changed during review')
        return dict(schema_version=1,policy_id='cif-captured-linear-bond-target-inventory-v1',status='REVIEW',
            component=component,dictionary_index=dictionary_index,inventory_qualification=result,
            capture_checks_pass=True,inventory_checks_pass=True,
            captures={label:dict(anchor=label+'_native_directory',path=p.name,sha256=sha256(frozen[p]).hexdigest(),size=len(frozen[p]))
                      for label,p in zip(('before','after'),receipts)},
            native_execution='PRESERVED_COMPLETED_CAPTURES; NOT_RERUN',reference_authority='NOT_QUALIFIED',
            energy_delta_qualification='NOT_RUN',derivative_qualification='NOT_RUN',
            achieved_geometry='NOT_ASSESSED',scientific_approval='NOT_RUN',automatic_adoption=False)
    except (KeyError,TypeError,IndexError,AttributeError,OverflowError) as exc:
        raise ValueError('Incomplete captured bond-target evidence') from exc
    finally:
        _need(all(_regular(p)==data for p,data in frozen.items()),'Captured bond-target inputs changed during review')
