"""Prepare a branch's isotropic metal B before its frozen XYZ/Q/fdp trials."""
import hashlib
import json
from .binding import AtomKey
from .context import parse_pdb
from .recipe import RecipeError, canonical, _identifier
from .chemistry import base_names, dictionaries

POLICIES = ('base-mean', 'donor-mean', 'keep')


def residue(key):
    return canonical({k:v for k,v in key.to_dict().items() if k != 'atom_name'})


def _environments(value, nodes, placed, fit_nodes):
    """Normalize explicit, disjoint assignments without inventing coordination."""
    if not isinstance(value, dict) or not value or len(value) > 12:
        raise RecipeError('Environmental B requires 1 to 12 named environments')
    result, assigned = {}, set()
    for name in value:
        _identifier(name, 'B environment')
    for name, group in sorted(value.items()):
        if not isinstance(group, dict) or set(group) != {'metal_nodes','donor_nodes'}:
            raise RecipeError('B environment requires metal_nodes and donor_nodes only')
        for field in ('metal_nodes','donor_nodes'):
            members = group[field]
            if (not isinstance(members, list) or not members or
                    any(not isinstance(n, str) for n in members) or len(members) != len(set(members))):
                raise RecipeError('B environment members must be distinct node identifiers')
        metals, donors = set(group['metal_nodes']), set(group['donor_nodes'])
        if metals - placed.keys() or metals - set(fit_nodes):
            raise RecipeError('B environment metals must be explicitly placed fitted nodes')
        if assigned & metals:
            raise RecipeError('A metal cannot belong to multiple B environments')
        if any(nodes.get(n, {}).get('kind') != 'donor' for n in donors):
            raise RecipeError('B environment donor nodes must be explicit recipe donors')
        assigned.update(metals)
        result[name] = dict(metal_nodes=sorted(metals), donor_nodes=sorted(donors))
    return result


def calibrate_b(raw, sites, preview, fit_nodes, policy, *, resources=(), environments=None):
    """Use exact connected ligand identities; never change a parent or its XYZ.

    Base means are equally weighted across distinct bases. Donor means weight
    each unique coordinating atom equally. Neither method uses occupancy weights.
    Explicit environments can share named donors across cluster members without
    adding geometric restraints. Unassigned metals still require direct donors.
    Missing chemistry requires an explicit alternate policy, never a guessed B.
    """
    if policy not in POLICIES:
        raise RecipeError('Unknown metal B policy')
    report = dict(policy=policy, protocol='metal-environment-b-v1',
                  source_model_sha256=hashlib.sha256(raw).hexdigest(), sites=[])
    if policy == 'keep':
        if environments is not None:
            raise RecipeError('Explicit B environments cannot be combined with keep')
        return report, raw
    parsed = parse_pdb(raw)
    atoms = parsed.snapshot.atoms
    states = parsed.to_dict()['atomic_state']
    inventory = {a.key:(i,a,states[i]) for i,a in enumerate(atoms)}
    placed = {s['node_id']:AtomKey(**s['key']) for s in sites}
    if not fit_nodes or len(set(fit_nodes)) != len(fit_nodes) or set(fit_nodes)-placed.keys():
        raise RecipeError('Require distinct placed metal nodes for environmental B')
    nodes = {n['node_id']:n for n in (preview or {}).get('nodes', [])}
    assignments = {}
    if environments is not None:
        normalized = _environments(environments, nodes, placed, fit_nodes)
        report.update(protocol='metal-environment-b-v2', environments=normalized)
        assignments = {n:(name,group['donor_nodes']) for name,group in normalized.items() for n in group['metal_nodes']}
    chemistry = dictionaries(resources) if policy == 'base-mean' else {}
    updates = {}
    for node in sorted(fit_nodes):
        if placed[node] not in inventory:
            raise RecipeError('Environmental B metal is missing from the geometry')
        index,metal,state = inventory[placed[node]]
        if state['anisou'] is not None:
            raise RecipeError('Environmental B requires an isotropic metal; review anisotropic ADPs explicitly')
        donor_ids = set()
        if node in assignments:
            donor_ids.update(assignments[node][1])
        else:
            for term in (preview or {}).get('restraints', []):
                if (term.get('kind') == 'distance' and term.get('enabled') and
                        term.get('status') == 'resolved' and node in term['node_ids']):
                    donor_ids.update(other for other in term['node_ids']
                                     if other != node and nodes.get(other, {}).get('kind') == 'donor')
        donor_keys = set()
        for other in sorted(donor_ids):
            ligand = nodes[other]
            if not ligand.get('atom'):
                raise RecipeError('Environmental B ligand is unresolved')
            key = AtomKey(**ligand['atom']['key'])
            if key not in inventory or inventory[key][1].element in {'H','D'}:
                raise RecipeError('Environmental B ligand identity is missing or unsupported')
            donor_keys.add(key)
        if not donor_keys:
            raise RecipeError('No connected ligand atoms for environmental B at '+node)
        groups = {}
        for key in sorted(donor_keys, key=lambda k:canonical(k.to_dict())):
            groups.setdefault(residue(key), []).append(key)
        source_atoms, base_rows = [], []
        for identity, keys in sorted(groups.items()):
            members = [a for a in atoms if residue(a.key) == identity and a.element not in {'H','D'}]
            if policy == 'base-mean':
                names, authority = base_names(keys[0].component_id, chemistry)
                if any(k.atom_name not in names for k in keys):
                    raise RecipeError('Coordinating ligand is outside the nucleobase; select donor-mean explicitly')
                members = [a for a in members if a.key.atom_name in names]
            else:
                authority = 'explicit_recipe_donors'
                members = [a for a in members if a.key in keys]
            rows = [dict(key=a.key.to_dict(), b_A2=inventory[a.key][2]['b_iso'],
                         anisou_present=inventory[a.key][2]['anisou'] is not None) for a in members]
            if not rows or any(r['b_A2'] < 0 for r in rows):
                raise RecipeError('Missing or invalid ligand B values')
            source_atoms.extend(rows)
            base_rows.append(dict(residue=json.loads(identity), mean_b_A2=sum(r['b_A2'] for r in rows)/len(rows),
                                  atom_count=len(rows), selection_authority=authority))
        means = [r['mean_b_A2'] for r in base_rows]
        mean = sum(means)/len(means) if policy == 'base-mean' else sum(r['b_A2'] for r in source_atoms)/len(source_atoms)
        applied = round(mean, 2)
        if not 0 <= applied <= 999.99:
            raise RecipeError('Environmental B cannot be represented in the PDB B column')
        updates[index] = applied
        report['sites'].append(dict(node_id=node, key=metal.key.to_dict(), policy=policy,
            previous_b_A2=state['b_iso'], mean_b_A2=mean, applied_b_A2=applied,
            base_means_A2=means, base_mean_spread_A2=max(means)-min(means), bases=base_rows,
            atoms=source_atoms, weighting='equal_bases' if policy=='base-mean' else 'equal_unique_donors'))
        if node in assignments:
            report['sites'][-1].update(environment_id=assignments[node][0], donor_node_ids=sorted(donor_ids))
    lines=raw.decode('ascii').splitlines(keepends=True); index=0
    for position,line in enumerate(lines):
        if line[:6].strip() in {'ATOM','HETATM'}:
            if index in updates:
                lines[position]=line[:60]+f'{updates[index]:6.2f}'+line[66:]
            index+=1
    return report, ''.join(lines).encode('ascii')
