"""Prepare a branch's isotropic metal B before its frozen XYZ/Q/fdp trials."""
import hashlib
import json
from .binding import AtomKey
from .context import parse_pdb
from .recipe import RecipeError, canonical
from .chemistry import base_names, dictionaries

POLICIES = ('base-mean', 'donor-mean', 'keep')


def residue(key):
    return canonical({k:v for k,v in key.to_dict().items() if k != 'atom_name'})


def calibrate_b(raw, sites, preview, fit_nodes, policy, *, resources=()):
    """Use exact connected ligand identities; never change a parent or its XYZ.

    Base means are equally weighted across distinct bases. Donor means weight
    each unique coordinating atom equally. Neither method uses occupancy weights.
    Missing chemistry requires an explicit alternate policy, never a guessed B.
    """
    if policy not in POLICIES:
        raise RecipeError('Unknown metal B policy')
    report = dict(policy=policy, protocol='metal-environment-b-v1',
                  source_model_sha256=hashlib.sha256(raw).hexdigest(), sites=[])
    if policy == 'keep':
        return report, raw
    parsed = parse_pdb(raw)
    atoms = parsed.snapshot.atoms
    states = parsed.to_dict()['atomic_state']
    inventory = {a.key:(i,a,states[i]) for i,a in enumerate(atoms)}
    placed = {s['node_id']:AtomKey(**s['key']) for s in sites}
    if not fit_nodes or len(set(fit_nodes)) != len(fit_nodes) or set(fit_nodes)-placed.keys():
        raise RecipeError('Require distinct placed metal nodes for environmental B')
    nodes = {n['node_id']:n for n in (preview or {}).get('nodes', [])}
    chemistry = dictionaries(resources) if policy == 'base-mean' else {}
    updates = {}
    for node in sorted(fit_nodes):
        if placed[node] not in inventory:
            raise RecipeError('Environmental B metal is missing from the geometry')
        index,metal,state = inventory[placed[node]]
        if state['anisou'] is not None:
            raise RecipeError('Environmental B requires an isotropic metal; review anisotropic ADPs explicitly')
        donor_keys = set()
        for term in (preview or {}).get('restraints', []):
            if (term.get('kind') != 'distance' or not term.get('enabled') or
                    term.get('status') != 'resolved' or node not in term['node_ids']):
                continue
            for other in term['node_ids']:
                ligand = nodes.get(other)
                if other == node or not ligand or ligand.get('kind') != 'donor':
                    continue
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
    lines=raw.decode('ascii').splitlines(keepends=True); index=0
    for position,line in enumerate(lines):
        if line[:6].strip() in {'ATOM','HETATM'}:
            if index in updates:
                lines[position]=line[:60]+f'{updates[index]:6.2f}'+line[66:]
            index+=1
    return report, ''.join(lines).encode('ascii')
