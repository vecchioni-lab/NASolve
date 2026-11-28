"""Prepare declared chemistry for selected native reader dialects.

Unknown atom aromaticity/CIP metadata stays unknown. Signed chiral volumes and
all original fields survive; this format adapter is not chemical perception.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .cif_doctor import assess_dictionaries, compare_dictionaries, _number, _ORDERS
from .cif_linked_preparation import component_values
from .ligand_profiles import _emit, _blocks

POLICY_ID = 'cif-declared-chemistry-ccd-reader-projection-v1'
_MISSING = {'', '.', '?'}


def _choice(values, fields, count, normalize):
    columns = [values[k] for k in fields if k in values]
    if any(len(column) != count for column in columns):
        raise ValueError('Incomplete reader-dialect column')
    result = []
    for i in range(count):
        known = {normalize(column[i]) for column in columns if column[i] not in _MISSING}
        if len(known) > 1:
            raise ValueError('Conflicting reader-dialect declarations: '+', '.join(fields))
        result.append(next(iter(known)) if known else '?')
    return result


def _flag(value):
    value = value.upper()
    if value not in {'Y', 'N'}:
        raise ValueError('Unsupported declared aromatic flag')
    return value


def _stereo(value):
    value = value.upper()
    if value not in {'R', 'S', 'N'}:
        raise ValueError('Unsupported declared atom stereo configuration')
    return value


def _charge(value):
    n = _number(value)
    if n is None or not n.is_integer() or abs(n) > 9:
        raise ValueError('Require a representable explicit integer formal charge')
    return str(int(n))


def _order(value):
    normalized = _ORDERS.get(value.upper())
    if normalized not in {'SINGLE', 'DOUBLE', 'TRIPLE'}:
        raise ValueError('CCD reader projection cannot invent a localized bond order')
    return {'SINGLE':'SING', 'DOUBLE':'DOUB', 'TRIPLE':'TRIP'}[normalized]


def _projection(values):
    lookup = {k.lower():v for k,v in values.items()}
    if len(lookup) != len(values):
        raise ValueError('Ambiguous case variants in reader input')
    a, b = '_chem_comp_atom.', '_chem_comp_bond.'
    na, nb = len(lookup[a+'atom_id']), len(lookup[b+'atom_id_1'])
    return {
        a+'charge':_choice(lookup,[a+'charge',a+'pdbx_formal_charge'],na,_charge),
        a+'pdbx_aromatic_flag':_choice(lookup,[a+'pdbx_aromatic_flag',a+'aromatic'],na,_flag),
        a+'pdbx_stereo_config':_choice(lookup,[a+'pdbx_stereo_config',a+'stereo_config'],na,_stereo),
        b+'value_order':_choice(lookup,[b+'value_order',b+'type'],nb,_order),
        b+'pdbx_aromatic_flag':_choice(lookup,[b+'pdbx_aromatic_flag',b+'aromatic'],nb,_flag),
    }


def prepare_elbow_ccd_input(source, code, output):
    """Preserve source bytes and known declarations; add reader aliases/unknowns."""
    source, output = Path(source).resolve(strict=True), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Reader input output already exists')
    if output.resolve() == source or any(p.is_symlink() for p in output.parents):
        raise ValueError('Reader input must be a separate regular output')
    original = source.read_bytes()
    assessment = assess_dictionaries([source], stage='ccd-reader-projection')
    if (len(assessment['components']) != 1 or assessment['components'][0]['component_id'] != code
            or assessment['components'][0]['verdicts']['graph'] != 'PASS'):
        raise ValueError('Require one graph-valid component for reader projection')
    values = component_values(source, code)
    projected = _projection(values)
    lookup = {k.lower():k for k in values}
    converted = deepcopy(values)
    added, changed = [], []
    for key, column in projected.items():
        actual = lookup.get(key, key)
        if actual not in values:
            added.append(key)
        elif values[actual] != column:
            changed.append(key)
        converted[actual] = column
    # Existing aliases and every non-consumer field (including signed chirality,
    # bond stereo, exact IDs, H and coordinates) remain verbatim parsed values.
    if any(converted[k] != v for k,v in values.items() if k.lower() not in projected):
        raise ValueError('Reader projection changed an unrelated declaration')
    if _projection(converted) != projected:
        raise ValueError('Reader projection changed known chemistry')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle:
        handle.write(_emit(converted).encode() if added or changed else original)
    restored = component_values(output, code)
    if (_projection(restored) != projected or any(restored[k] != v for k,v in values.items() if k.lower() not in projected)):
        raise ValueError('Serialized reader projection changed declarations')
    if source.read_bytes() != original:
        raise ValueError('Original graph source changed')
    atom_ids = values['_chem_comp_atom.atom_id']
    return {'schema_version':1, 'policy_id':POLICY_ID, 'component':code,
        'source_sha256':sha256(original).hexdigest(), 'consumer_sha256':sha256(output.read_bytes()).hexdigest(),
        'source_preserved':True, 'known_chemical_declarations':'PRESERVED',
        'added_fields':sorted(added), 'changed_fields':sorted(changed),
        'unknown_atom_metadata':{k:[atom_ids[i] for i,v in enumerate(column) if v=='?']
            for k,column in projected.items() if k.startswith('_chem_comp_atom.') and '?' in column},
        'raw_comparison':compare_dictionaries([source],[output]),
        'signed_chirality':'ORIGINAL_DECLARATIONS_PRESERVED', 'stereochemistry_inferred':False,
        'aromaticity_perceived':False, 'numerical_targets_inferred':False,
        'chemical_qualification':'NOT_RUN', 'automatic_adoption':False}


def prepare_elbow_source_dialect_input(original, graph, code, output):
    """Retain a source's explicit comp_list reader route in a separate input.

    Legacy monomer sources keep signed-volume declarations and coordinate
    aliases. CCD sources retain the existing projection. This opt-in adapter
    does not select a new chemical state or certify the installed parser.
    """
    from .cif_linked_preparation import _render
    from .cif_generation import _CHEMICAL_FIELDS
    from .cif_numerical_recovery import prepare_graph_generation_source
    from tempfile import TemporaryDirectory
    original,graph=Path(original).resolve(strict=True),Path(graph).resolve(strict=True)
    output=Path(output).absolute()
    if output.exists() or output.is_symlink():raise FileExistsError('Reader-dialect output exists')
    if output.resolve() in {original,graph} or any(p.is_symlink() for p in output.parents):
        raise ValueError('Require a separate regular reader-dialect output')
    frozen={p:p.read_bytes() for p in [original,graph]}
    # Require this policy's exact source-derived graph, including the absence
    # of old numerical targets/types. Chemical equality alone cannot prove that.
    with TemporaryDirectory(prefix='cif-reader-graph-check-') as temporary:
        # OS temp roots can be aliases (for example /var -> /private/var on
        # macOS). Canonicalize this newly created, tool-owned directory only;
        # caller-selected outputs must still pass the strict symlink checks.
        expected=Path(temporary).resolve(strict=True)/'graph.cif'
        prepare_graph_generation_source(original,code,expected)
        if expected.read_bytes()!=frozen[graph]:raise ValueError('Reader input is not the exact target-free source graph')
    for path in [original,graph]:
        assessment=assess_dictionaries([path],stage='source-reader-dialect')
        if len(assessment['components'])!=1 or assessment['components'][0]['component_id']!=code or assessment['components'][0]['verdicts']['graph']!='PASS':
            raise ValueError('Require one graph-valid source/graph component')
    comparison=compare_dictionaries([original],[graph])
    if any(r['field'] in _CHEMICAL_FIELDS for r in comparison['differences']):
        raise ValueError('Graph export changed source chemical declarations')
    legacy=any(b.values['data_'].lower()=='comp_list' and code in b.values.get('_chem_comp.id',[])
               for b in _blocks(original))
    aliases=[];projection=None;bond_tokens=None
    if legacy:
        values=component_values(graph,code);source=component_values(original,code)
        a,b='_chem_comp_atom.','_chem_comp_bond.'
        if b+'type' not in values or a+'charge' not in values:
            raise ValueError('Source monomer dialect needs its declared type/charge fields')
        # The selected monomer reader's lookup is case sensitive and silently
        # defaults unknown tokens to single. Translate declared orders only.
        native={'SINGLE':'single','DOUBLE':'double','TRIPLE':'triple',
                'AROMATIC':'aromatic','DELOCALIZED':'deloc'}
        before=list(values[b+'type'])
        try:values[b+'type']=[native[_ORDERS[token.upper()]] for token in before]
        except KeyError:raise ValueError('Unsupported declared monomer bond order') from None
        bond_tokens={'source':before,'consumer':list(values[b+'type']),
                     'policy':'DECLARED_ORDER_TO_CASE_SENSITIVE_MONOMER_TOKEN'}
        # Source metadata stays metadata; no old numerical restraint or energy
        # type is reintroduced into the target-free graph.
        values.update({k:v for k,v in source.items() if k.startswith('_chem_comp.')})
        for axis in 'xyz':
            target=a+axis;seed=a+'pdbx_model_Cartn_'+axis+'_ideal'
            if seed not in values:raise ValueError('Missing complete graph coordinate family')
            if target in values and values[target]!=values[seed]:raise ValueError('Conflicting reader coordinate aliases')
            values[target]=list(values[seed]);aliases.append(target)
        payload=_render(values,code).encode()
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('xb') as handle:handle.write(payload)
        restored=component_values(output,code)
        if restored!=values:raise ValueError('Reader-dialect serialization changed declarations')
        after=compare_dictionaries([graph],[output])
        if any(r['field'] in _CHEMICAL_FIELDS for r in after['differences']):
            raise ValueError('Monomer reader input changed graph chemistry')
        dialect='MONOMER_LIBRARY_CIF'
    else:
        projection=prepare_elbow_ccd_input(graph,code,output)
        dialect='CHEMICAL_COMPONENTS_CIF'
    if any(p.read_bytes()!=d for p,d in frozen.items()):raise ValueError('Reader-dialect source changed')
    return {'schema_version':1,'policy_id':'cif-source-reader-dialect-preservation-v2','component':code,
        'source_reader_dialect':dialect,'consumer_reader_dialect':dialect,
        'original_source_sha256':sha256(frozen[original]).hexdigest(),'graph_sha256':sha256(frozen[graph]).hexdigest(),
        'consumer_sha256':sha256(output.read_bytes()).hexdigest(),'coordinate_aliases':aliases,
        'monomer_bond_tokens':bond_tokens,
        'chemical_declarations':'PRESERVED','stereochemistry_inferred':False,'ccd_projection':projection,
        'source_preserved':True,'graph_preserved':True,'raw_comparison':compare_dictionaries([graph],[output]),
        'native_reader_qualification':'NOT_RUN','automatic_adoption':False}


def prepare_elbow_phosphate_bond_order(source, code, output):
    """Present a declared terminal P=O first to the native monomer reader.

    Some eLBOW monomer paths set the first terminal P--O bond to double even
    when a different double bond is already declared. Permute complete bond
    rows only; never choose a resonance form or repair a generated dictionary.
    Require an explicit four-neighbour P graph with one terminal P=O and all
    other incident bonds single. Unsupported affected sites refuse before output.
    This opt-in input adapter is not native qualification or ordinary adoption.
    """
    from .cif_stereochemistry_audit import _graph
    source, output = Path(source).resolve(strict=True), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Phosphate-order output already exists')
    if output.resolve() == source or any(p.is_symlink() for p in output.parents):
        raise ValueError('Require a separate regular phosphate-order output')
    original = source.read_bytes()
    blocks = _blocks(source)
    targets = [b for b in blocks if any(k.lower() == '_chem_comp_atom.atom_id' for k in b.values)]
    if len(targets) != 1:
        raise ValueError('Require one phosphate-order component')
    target = targets[0]
    others = [b for b in blocks if b is not target]
    if (len(others) != 1 or others[0].values.get('data_', '').lower() != 'comp_list'
            or others[0].values.get('_chem_comp.id') != [code]):
        raise ValueError('Require one explicit monomer component-list block')
    values = target.values
    lookup = {k.lower(): v for k, v in values.items()}
    if len(lookup) != len(values):
        raise ValueError('Ambiguous phosphate-order field aliases')
    a, b = '_chem_comp_atom.', '_chem_comp_bond.'
    for category, identity in ((a, 'atom_id'), (b, 'atom_id_1')):
        count = len(lookup.get(category + identity, []))
        columns = {k: v for k, v in lookup.items() if k.startswith(category)}
        if (not count or any(not isinstance(v, list) or len(v) != count for v in columns.values())
                or set(columns.get(category + 'comp_id', [])) != {code}):
            raise ValueError('Incomplete or mixed phosphate-order category')
    def order(token):
        normalized = _ORDERS.get(token.upper())
        if normalized not in {'SINGLE', 'DOUBLE', 'TRIPLE', 'AROMATIC', 'DELOCALIZED'}:
            raise ValueError('Unsupported explicit bond order')
        return normalized
    count = len(lookup[b + 'atom_id_1'])
    orders = _choice(lookup, [b + 'type', b + 'value_order'], count, order)
    if '?' in orders:
        raise ValueError('Phosphate ordering requires explicit bond orders')
    assessment = assess_dictionaries([source], stage='phosphate-input-order')
    if (len(assessment['components']) != 1 or assessment['components'][0]['component_id'] != code
            or assessment['components'][0]['verdicts']['graph'] != 'PASS'):
        raise ValueError('Require one graph-valid phosphate-order source')
    elements, bonds, _, neighbours = _graph(lookup)
    edges = [tuple(sorted(pair)) for pair in zip(lookup[b + 'atom_id_1'], lookup[b + 'atom_id_2'])]
    if len(set(edges)) != count or any(bonds.get(edge) != value for edge, value in zip(edges, orders)):
        raise ValueError('Ambiguous phosphate-order bond graph')
    indices = list(range(count))
    sites = []
    for center in sorted(n for n, e in elements.items() if e == 'P'):
        oxygens = {n for n in neighbours[center] if elements[n] == 'O'}
        terminal = {n for n in oxygens if len(neighbours[n]) == 1}
        if len(oxygens) < 2 or not terminal:
            continue  # The native first-terminal-oxygen rule cannot apply.
        doubles = {n for n in terminal if bonds[tuple(sorted((center, n)))] == 'DOUBLE'}
        if (len(neighbours[center]) != 4 or len(doubles) != 1
                or any(bonds[tuple(sorted((center, n)))] != ('DOUBLE' if n in doubles else 'SINGLE')
                       for n in neighbours[center])):
            raise ValueError('Require one declared terminal P=O and three single P bonds')
        double = tuple(sorted((center, next(iter(doubles)))))
        slots = [i for i, edge in enumerate(edges) if center in edge and any(n in terminal for n in edge)]
        selected = sorted(slots, key=lambda i: edges[i] != double)
        for slot, selected_index in zip(slots, selected):
            indices[slot] = selected_index
        sites.append({'center': center, 'declared_double_bond': list(double),
                      'input_terminal_bonds': [list(edges[i]) for i in slots],
                      'output_terminal_bonds': [list(edges[i]) for i in selected]})
    converted = deepcopy(values)
    for key, column in values.items():
        if key.lower().startswith(b):
            converted[key] = [column[i] for i in indices]
    changed = indices != list(range(count))
    payload = (''.join(_emit(converted) if block is target else block.text for block in blocks).encode()
               if changed else original)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as handle:
        handle.write(payload)
    if [block.values for block in _blocks(output)] != [converted if block is target else block.values for block in blocks]:
        raise ValueError('Phosphate-order serialization changed declarations; output retained')
    if source.read_bytes() != original:
        raise ValueError('Phosphate-order source changed')
    return {'schema_version': 1, 'policy_id': 'cif-declared-phosphate-bond-row-order-v1',
            'component': code, 'source_sha256': sha256(original).hexdigest(),
            'consumer_sha256': sha256(payload).hexdigest(), 'source_preserved': True,
            'changed': changed, 'sites': sites, 'chemical_declarations': 'PRESERVED',
            'coordinate_values': 'PRESERVED', 'bond_rows': 'COMPLETE_ROW_PERMUTATION_ONLY',
            'reader_dialect': 'MONOMER_LIBRARY_CIF', 'native_qualification': 'NOT_RUN',
            'automatic_adoption': False}
