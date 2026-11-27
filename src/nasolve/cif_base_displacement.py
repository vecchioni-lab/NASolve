"""Starting isotropic B values for two source-equivalent bases in a sugar substitution."""
from collections import defaultdict
from math import isfinite

from .cif_stereochemistry_audit import _graph, _stereo
from .cif_whole_furanose import base_fragment_atoms

POLICY_ID = 'cif-source-equivalent-base-isotropic-b-v1'


class _Unavailable(ValueError):
    """The seed remains usable with its existing B values."""


def _annotations(values, category, index, names):
    return tuple(str(values[category+key][index]).upper() if category+key in values else None for key in names)


def _base_signature(profile, values):
    roles = profile['bindings']
    elements, orders, charges, neighbors = _graph(values)
    fragment = base_fragment_atoms(roles,neighbors)
    heavy = {n for n in fragment if elements[n] not in {'H','D'}}
    labels = defaultdict(list)
    for role, name in profile['operational_signature']['atom_roles'].items():
        if name in heavy:
            labels[name].append(role)
    if set(labels)!=heavy:
        raise _Unavailable('The workbook does not identify every heavy atom of the separated base')
    roles_by_atom = {n:tuple(sorted(labels[n])) for n in heavy}
    stereo = _stereo(values)
    if (any(stereo[n]!='N' for n in heavy) or heavy.intersection(values.get('_chem_comp_chir.atom_id_centre',[]))):
        raise _Unavailable('Base stereochemistry is ambiguous or requires a separate correspondence')
    if any(charges[n] is None for n in fragment) or fragment==heavy:
        raise _Unavailable('Complete base charge and explicit hydrogen evidence are required')
    atom_indices = {n:i for i,n in enumerate(values['_chem_comp_atom.atom_id'])}
    atom_fields = ('pdbx_aromatic_flag','aromatic','pdbx_mass_number','pdbx_isotope','isotope')
    def atom_record(n):
        return (elements[n],charges[n],stereo[n],_annotations(values,'_chem_comp_atom.',atom_indices[n],atom_fields))
    atoms = {}
    light = fragment-heavy
    for n in heavy:
        hydrogens = neighbors[n] & light
        if any(neighbors[h]!={n} for h in hydrogens):
            raise _Unavailable('Unresolved base hydrogen attachment')
        attached = sorted((atom_record(h),orders[tuple(sorted((h,n)))]) for h in hydrogens)
        atoms[roles_by_atom[n]] = (atom_record(n),attached)
    bonds = {}
    for i,(a,b) in enumerate(zip(values['_chem_comp_bond.atom_id_1'],values['_chem_comp_bond.atom_id_2'])):
        if a in heavy and b in heavy:
            edge = tuple(sorted((roles_by_atom[a],roles_by_atom[b])))
            bonds[edge] = (orders[tuple(sorted((a,b)))],_annotations(values,'_chem_comp_bond.',i,
                           ('pdbx_aromatic_flag','aromatic','pdbx_stereo_config')))
    root = roles_by_atom[roles['base']]
    attachment = orders[tuple(sorted((roles['base'],roles['anomeric'])))]
    return (root,attachment,atoms,bonds), {v:k for k,v in roles_by_atom.items()}


def _site_lines(lines, site):
    selected = {}
    chain, resid = site.split(':')
    for i,line in enumerate(lines):
        if (line[21:22].strip() or '_',line[22:26].strip())!=(chain,resid):
            continue
        if line[:6].strip() in {'ANISOU','SIGATM','SIGUIJ'}:
            raise _Unavailable('Selected site has associated displacement or uncertainty records')
        if line[:6] in {'ATOM  ','HETATM'}:
            name = line[12:16].strip()
            if name in selected or line[16:17].strip() or line[26:27].strip():
                raise _Unavailable('Selected atom identities are ambiguous')
            selected[name] = (i,line)
    return selected


def inherit_base_displacement(host_profile, target_profile, host_values, target_values, host_model, model, site):
    """Transfer only complete role- and graph-matched base B fields, preserving occupancy and XYZ."""
    record = dict(policy_id=POLICY_ID,site=site,scope='STARTING_ISOTROPIC_B_ONLY')
    try:
        host_signature, host_names = _base_signature(host_profile,host_values)
        target_signature, target_names = _base_signature(target_profile,target_values)
        if host_signature!=target_signature:
            raise _Unavailable('The complete workbook-bound base chemistry differs')
        lines = model.splitlines(keepends=True)
        source = _site_lines(host_model.splitlines(),site)
        target = _site_lines(lines,site)
        applied = []
        for roles in sorted(host_names):
            donor, name = host_names[roles], target_names[roles]
            if donor not in source or name not in target:
                raise _Unavailable('A matched atom is absent from the model')
            _, before = source[donor]; pos, after = target[name]
            element = host_signature[2][roles][0][0]
            try:
                q, b = float(before[54:60]), float(before[60:66])
                target_q = float(after[54:60])
            except ValueError as exc:
                raise _Unavailable('Invalid host B or occupancy') from exc
            if (before[76:78].strip().upper()!=element or after[76:78].strip().upper()!=element
                    or not 0<q<=1 or q!=target_q or not isfinite(b) or b<0):
                raise _Unavailable('Incompatible element, occupancy or isotropic B')
            lines[pos] = after[:60]+before[60:66]+after[66:]
            applied.append(dict(roles=list(roles),host_atom=donor,target_atom=name,initial_b=b))
    except _Unavailable as exc:
        return model, dict(record,status='RETAINED_SEED',reason=str(exc),atoms=[])
    return ''.join(lines), dict(record,status='MATCHED_HOST_BASE',atoms=applied)
