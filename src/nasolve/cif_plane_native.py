"""Exact linked native inventory delta for source-supported plane completion.

The pure gate reconstructs the candidate and checks the supplied inventories.
The owned wrapper additionally binds maintained native captures and selected
generation evidence. Neither runs native tools or approves mechanics/adoption.
"""
from copy import deepcopy
from math import isfinite
from pathlib import Path
from tempfile import TemporaryDirectory

from .cif_linked_linear_torsion import _exact, _identity, _need
from .cif_plane_candidate import prepare_trigonal_plane_candidate
from .cif_plane_coverage import _table
from .cif_stereochemistry_audit import _values

POLICY_ID = 'cif-linked-plane-completion-inventory-v1'


def _canonical_proxy(row):
    """Canonicalize a symmetric plane without separating indices/labels/weights."""
    indices, labels, weights = (row[k] for k in ('i_seqs', 'atoms', 'weights'))
    _need(isinstance(indices, list) and isinstance(labels, list) and isinstance(weights, list)
          and len(indices) == len(labels) == len(weights) and len(indices) >= 3,
          'Incomplete native plane arrays')
    _need(all(type(i) is int and i >= 0 for i in indices) and len(set(indices)) == len(indices)
          and all(isinstance(s, str) for s in labels)
          and all(type(w) in (int, float) and isfinite(w) and w > 0 for w in weights),
          'Ambiguous native plane membership or weights')
    result = deepcopy(row)
    rows = sorted(zip(indices, labels, weights))
    for column, key in enumerate(('i_seqs', 'atoms', 'weights')):
        result[key] = [r[column] for r in rows]
    return result


def _qualify(before, after, source, dictionary, support, component, candidate):
    with TemporaryDirectory(prefix='nasolve-plane-replay-') as scratch:
        rebuilt = Path(scratch).resolve()/'candidate.cif'
        plan = prepare_trigonal_plane_candidate(source, dictionary, support, component, rebuilt)
        _need(candidate.read_bytes() == rebuilt.read_bytes(),
              'Candidate differs from the complete source-supported plane plan')
    for native in (before, after):
        _need(native.get('status') == 'REVIEW' and native.get('fatal_problems') is None
              and native.get('unsupported_fields') == [] and native.get('unused_definitions') == []
              and native.get('inventory_detail') == 'linked', 'Require supported linked native inventories')
    expected = deepcopy(before)
    actual = deepcopy(after)
    values = _values(dictionary, component)
    original = [dict(plane_id=r['plane_id'], atom_id=r['atom_id'], dist_esd=float(r['dist_esd']))
                for r in _table(values, 'plane_atom')]
    additions = [dict(plane_id=r['plane'], atom_id=r['atom'], dist_esd=r['dist_esd'])
                 for r in plan['additions']]
    def extend(definition):
        _need(_exact(definition['plane_atoms'], original),
              'Native effective plane definitions differ from the original dictionary')
        definition['plane_atoms'].extend(deepcopy(additions))
    providers = [m for row in expected['dictionary_loading'] for m in row['component_metadata']
                 if m['id'] == component]
    _need(len(providers) == 1, 'Require one native dictionary provider')
    extend(providers[0]['effective_definition'])
    mappings = expected['monomer_mappings']['rows']
    identities = [_identity(row['literal_identity']) for row in mappings]
    _need(len(set(identities)) == len(identities), 'Ambiguous native residue mapping')
    selected = {}
    for row, identity in zip(mappings, identities):
        if identity[-1] == component:
            _need(row['metadata']['id'] == component, 'Mapped native component differs')
            extend(row['metadata']['effective_definition'])
            selected[identity] = row
    _need(bool(selected), 'No modeled occurrence of the requested component')
    index, names = {}, {site: {} for site in selected}
    for atom in before['atoms']:
        i = atom['i_seq'];site = _identity(atom['identity'])
        _need(type(i) is int and i >= 0 and i not in index, 'Invalid or duplicate native atom index')
        index[i] = atom
        if site in names:
            name = atom['atom_id']
            _need(name not in names[site], 'Ambiguous modeled atom identity')
            names[site][name] = i
    _need(before['atom_count'] == len(index), 'Native atom count differs from inventory')
    groups = {}
    for row in additions:
        groups.setdefault(row['plane_id'], []).append(row)
    proxies = expected['geometry']['proxy_details']['planarity']
    after_proxies = actual['geometry']['proxy_details']['planarity']
    used = set();members = 0
    for site, atom_indices in names.items():
        for plane, extra in groups.items():
            old = [r for r in original if r['plane_id'] == plane and r['atom_id'] in atom_indices]
            _need(len(old) >= 3 and all(r['atom_id'] in atom_indices for r in extra),
                  'Incomplete modeled plane members')
            old_indices = {atom_indices[r['atom_id']] for r in old}
            found = [i for i,p in enumerate(proxies) if set(p['i_seqs']) == old_indices]
            _need(len(found) == 1 and found[0] not in used, 'Missing or ambiguous original native plane')
            ordinal = found[0];used.add(ordinal)
            proxy = _canonical_proxy(proxies[ordinal])
            _need(type(proxy.get('origin_id')) is int and proxy['origin_id'] == 0,
                  'Source plane has a non-component native origin')
            weights = {atom_indices[r['atom_id']]: 1/r['dist_esd']**2 for r in old}
            _need(proxy['atoms'] == [index[i]['label'] for i in proxy['i_seqs']]
                  and _exact(proxy['weights'], [weights[i] for i in proxy['i_seqs']]),
                  'Original native plane labels or weights differ from declared atoms')
            for row in extra:
                i = atom_indices[row['atom_id']]
                _need(i not in old_indices, 'Planned native addition already exists')
                proxy['i_seqs'].append(i);proxy['atoms'].append(index[i]['label'])
                proxy['weights'].append(1/row['dist_esd']**2);members += 1
            proxies[ordinal] = _canonical_proxy(proxy)
            if ordinal < len(after_proxies):
                after_proxies[ordinal] = _canonical_proxy(after_proxies[ordinal])
    # Energies can change with a plane's membership and require a separate gate.
    # Every other field, including unknown future categories, remains compared.
    expected.pop('energy_inventory', None);actual.pop('energy_inventory', None)
    checks = {key: key in actual and key in expected and _exact(actual[key], expected[key])
              for key in sorted(set(expected) | set(actual))}
    return dict(schema_version=1, policy_id=POLICY_ID, status='REVIEW',
        inventory_checks_pass=all(checks.values()), checks=checks, plan=plan, component=component,
        modeled_occurrences=len(selected), extended_native_planes=len(used), added_native_members=members,
        candidate_rebuilt_exactly=True, native_provenance='CALLER_MUST_AUTHENTICATE',
        generator_provenance='NOT_VERIFIED', energy_delta_qualification='NOT_RUN',
        derivative_qualification='NOT_RUN', achieved_geometry='NOT_ASSESSED',
        scientific_approval='NOT_RUN', model_editing='NOT_RUN', automatic_adoption=False)


def qualify_linked_plane_candidate(before, after, source, dictionary, support, component, candidate):
    """Allow only reconstructed plane additions in the complete linked inventory.

    Callers must authenticate captures against identical ordered model/PHIL/tool
    inputs, except for this exact dictionary replacement. Symmetric plane arrays
    are compared by index/label/weight association; all other ordering is exact.
    No capture, receipt or plan alone authenticates native execution or chemistry.
    """
    paths = [Path(p) for p in (source, dictionary, support, candidate)]
    frozen = [p.read_bytes() for p in paths]
    try:
        return _qualify(before, after, *paths[:3], component, paths[-1])
    except (KeyError, TypeError, IndexError, OverflowError) as exc:
        raise ValueError('Incomplete native plane qualification evidence') from exc
    finally:
        if [p.read_bytes() for p in paths] != frozen:
            raise ValueError('Plane qualification input changed')


def qualify_owned_plane_captures(source, component, request_directory, attempt_number,
        candidate, model, before_receipt, after_receipt, *, dictionaries,
        dictionary_index, phil_files=()):
    """Bind owned support and exact ordered native inputs to the plane delta.

    ``dictionaries`` is the complete ordered original bundle; exactly the explicit
    zero-based slot is replaced by ``candidate``. Both captures must use the same
    recorded consumer and options. No native process runs and no current installed
    consumer, energy/derivative, achieved geometry or automatic adoption is approved.
    """
    try:
        return _qualify_owned_captures(source, component, request_directory, attempt_number,
            candidate, model, before_receipt, after_receipt, dictionaries, dictionary_index, phil_files)
    except (KeyError, TypeError, IndexError, AttributeError, OverflowError) as exc:
        raise ValueError('Incomplete owned plane capture evidence') from exc


def _qualify_owned_captures(source, component, request_directory, attempt_number,
        candidate, model, before_receipt, after_receipt, dictionaries, index, phils):
    from hashlib import sha256
    from .campaign_records import path_in
    from .cif_attachment_native import _capture, _json, _native_atoms, _xyz_match
    from .cif_dictionary_sites import _read, _bind_capture_inputs
    from .cif_plane_generation import read_owned_plane_support
    dictionaries = [Path(p).absolute() for p in dictionaries]
    phils = [Path(p).absolute() for p in phils]
    _need(type(index) is int and 0 <= index < len(dictionaries),
          'Require an explicit original dictionary slot')
    source, candidate, model = [Path(p).absolute() for p in (source, candidate, model)]
    receipts = [Path(p).absolute() for p in (before_receipt, after_receipt)]
    original = {p:_read(p) for p in [source,candidate,model,*dictionaries,*phils,*receipts]}
    support = read_owned_plane_support(source, component, request_directory, attempt_number)
    captures = [_capture(p, original[model]) for p in receipts]
    records = [r[0] for r in captures]; inventories = [r[1] for r in captures]
    after_dictionaries = list(dictionaries);after_dictionaries[index] = candidate
    options = []
    for receipt_path, record, native, snapshot, ordered in zip(receipts,records,inventories,
            [r[2] for r in captures],(dictionaries,after_dictionaries)):
        _need(record['status'] == 'REVIEW' and record['execution']['status'] == 'COMPLETED'
              and type(record['execution']['returncode']) is int and record['execution']['returncode'] == 0,
              'Require two completed native captures')
        _bind_capture_inputs(record, model, ordered, phils)
        _native_atoms(native, original[model])
        sites = native['geometry']['sites_cart_exact']
        _need(len(sites) == native['atom_count'] and all(_xyz_match(p,a['xyz']) for p,a in zip(sites,native['atoms'])),
              'Captured geometry coordinates differ from selected model')
        spec_path = receipt_path.resolve(strict=True).parent/'native_spec.json'
        spec = _json(snapshot[spec_path])
        _need(spec.get('policy_inventory') is True and spec.get('inventory_detail') == 'linked',
              'Require explicit linked policy inventories')
        options.append({k:v for k,v in spec.items() if k not in ('model','dictionaries','phil_files')})
    _need(_exact(options[0], options[1]), 'Native capture options differ')
    producer_fields = ('phenix_version','executable_sha256','api_sources',
                       'dictionary_source_policy','phil_namespace_policy')
    for field in producer_fields:
        _need(field in records[0] and _exact(records[0][field], records[1].get(field)),
              'Native capture producer/context differs: '+field)
    digest = records[0]['executable_sha256']
    _need(isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest)
          and bool(records[0]['api_sources']), 'Incomplete captured native producer identity')
    result = qualify_linked_plane_candidate(*inventories, source, dictionaries[index],
        path_in(Path(request_directory).absolute(), support['support']['path']), component, candidate)
    _need(result['inventory_checks_pass'], 'Native changes exceed the supported plane completion')
    _need(read_owned_plane_support(source, component, request_directory, attempt_number) == support
          and all(_read(p)==data for p,data in original.items())
          and all(_read(p)==data for _,_,snapshot in captures for p,data in snapshot.items()),
          'Owned plane qualification inputs changed during review')
    return dict(schema_version=1, policy_id='cif-owned-plane-capture-qualification-v1', status='REVIEW',
        component=component, support_generation=support, inventory_qualification=result,
        capture_checks_pass=True, inventory_checks_pass=True, dictionary_index=index,
        model_sha256=sha256(original[model]).hexdigest(), candidate_sha256=sha256(original[candidate]).hexdigest(),
        captures={label:dict(anchor=label+'_native_directory',path=p.name,
            sha256=sha256(original[p]).hexdigest(),size=len(original[p])) for label,p in zip(('before','after'),receipts)},
        captured_consumer={k:records[0][k] for k in producer_fields}, native_options=options[0],
        native_execution='PRESERVED_COMPLETED_CAPTURES; NOT_RERUN',
        energy_delta_qualification='NOT_RUN', derivative_qualification='NOT_RUN', achieved_geometry='NOT_ASSESSED',
        scientific_approval='NOT_RUN', automatic_adoption=False,
        scope='OWNED_SOURCE_SUPPORT_AND_EXACT_CAPTURE_DELTA; NOT_CURRENT_CONSUMER_OR_SCIENTIFIC_APPROVAL')
