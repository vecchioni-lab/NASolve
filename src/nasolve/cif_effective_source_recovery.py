"""Select explicit source/native graph recovery without residue exceptions."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .cif_fragment_restoration import _fragment, _model
from .cif_captured_geometry import review_captured_geometry
from .cif_linked_preparation import atom_rows, component_values

RECOVERY_POLICY = 'cif-effective-source-graph-recovery-v1'


def _source_definition(values):
    atoms = atom_rows(values)
    prefix = '_chem_comp_bond.'
    a, b = values.get(prefix+'atom_id_1', []), values.get(prefix+'atom_id_2', [])
    orders = values.get(prefix+'type', values.get(prefix+'value_order', []))
    if not a or len(a) != len(b) or len(a) != len(orders):
        raise ValueError('Source bond graph is incomplete')
    return {'atoms': [{'atom_id': name, 'type_symbol': row['type_symbol']} for name,row in atoms.items()],
            'bonds': [{'atom_id_1': x, 'atom_id_2': y, 'type': order} for x,y,order in zip(a,b,orders)]}


def plan_effective_source_recovery(native: dict, model: Path, source_audit: dict,
                                   resources: dict[str,Path], sites: list[str]) -> dict:
    """Require an unsupported effective graph and a hash-bound supported source.

    Resource keys identify an explicit supplied inventory. Matching uses the
    source audit's component/input index and exact bytes/hash, never filenames.
    Only sites without prior native modifiers are eligible for this recovery
    slice; other composition policies remain visibly blocked.
    """
    review_captured_geometry(native)
    inventory = _model(native, model, coordinates_match=True)
    mappings = native['monomer_mappings']['rows']
    if len({r['site'] for r in mappings}) != len(mappings) or len(sites) != len(set(sites)):
        raise ValueError('Ambiguous recovery site inventory')
    mappings = {r['site']: r for r in mappings}
    resources = {name: Path(path) for name,path in resources.items()}
    payloads = {name: path.read_bytes() for name,path in resources.items() if path.is_file() and not path.is_symlink()}
    selected = {}; unchanged = []; blocked = []
    for site in sorted(sites):
        if site.count(':') != 1 or site not in mappings:
            raise ValueError('Unknown recovery site')
        chain, resid = site.split(':'); row = mappings[site]; code = row['resname']
        atoms = {k[-1]: a for k,a in inventory.items() if k[:2] == (chain,resid)}
        try:
            _fragment(row['metadata']['effective_definition'],atoms)
        except ValueError as exc:
            reason = str(exc)
        else:
            unchanged.append(site); continue
        try:
            mods = row.get('chem_mod_ids',{})
            if mods.get('status') != 'RECORDED' or mods.get('ids') != []:
                raise ValueError('Prior site modifiers require an explicit composition policy')
            definitions = [r for r in source_audit['components'] if r['component_id'] == code]
            if len(definitions) != 1:
                raise ValueError('Require one declared source component')
            records = [r for r in source_audit['inputs'] if r['input_index'] == definitions[0]['input_index'] and r['role'] == 'dictionary']
            if len(records) != 1:
                raise ValueError('Ambiguous declared source input')
            record = records[0]
            matches = [name for name,data in payloads.items() if len(data) == record['size']
                       and hashlib.sha256(data).hexdigest() == record['sha256']]
            if len(matches) != 1:
                raise ValueError('Require one explicit source resource matching the recorded hash/size')
            name = matches[0]; values = component_values(resources[name],code)
            if [v.upper() for v in values.get('_chem_comp.type',[])] != ['DNA LINKING']:
                raise ValueError('Source does not declare DNA LINKING')
            _fragment(_source_definition(values),atoms)
            item = selected.setdefault(code, {'component': code, 'source_resource': name,
                'source_sha256': record['sha256'], 'source_size': record['size'],
                'source_input_index': record['input_index'], 'sites': [], 'effective_graph_reviews': []})
            item['sites'].append(site); item['effective_graph_reviews'].append({'site':site,'reason':reason})
        except (ValueError, KeyError) as exc:
            blocked.append({'site':site,'component':code,'effective_graph_review':reason,'reason':str(exc)})
    # One shared source definition must not silently replace other code contexts.
    for code in list(selected):
        actual = {r['site'] for r in mappings.values() if r['resname'] == code}
        if set(selected[code]['sites']) != actual:
            blocked.append({'component':code,'reason':'Recovery must cover every shared-code model context'})
            del selected[code]
    return {'schema_version':1,'audit_kind':'cif_effective_source_recovery_plan','policy_id':RECOVERY_POLICY,
        'status':'REVIEW','recovery_codes':sorted(selected),'selected':[selected[c] for c in sorted(selected)],
        'unchanged_sites':unchanged,'blocked':blocked,'automatic_adoption':False,
        'limitations':['Supported source scaffold is an eligibility check, not full chemical approval.',
            'Independent whole-component generation and source-state/linked/native qualification remain required.',
            'No dictionary target, charge or atom mapping is inferred from model residuals.']}


def mechanics_can_continue(report: dict) -> bool:
    """Permit only passed checks and the already explicit unavailable charge API.

    This authorizes a separate diagnostic phase, not adoption or a PASS verdict.
    Charge contradictions and all other unsupported/review states stop it.
    """
    checks = report.get('checks')
    return bool(checks) and all(c.get('status') == 'PASS' or (
        c.get('status') == 'UNSUPPORTED' and c.get('check','').startswith('effective-site-formal-charges:')
        and not c.get('contradictions')) for c in checks)


def recovery_modifier_check(before: dict, after: dict, preparations: list[dict]) -> dict:
    expected = {r['site']: r['chem_mod_ids'] for r in before['monomer_mappings']['rows']}
    for preparation in preparations:
        for site in preparation['sites']:
            if expected[site['site']] != {'status':'RECORDED','ids':[]}:
                return {'check':'exact-recovery-modifier-ids','status':'REVIEW','reason':'Prior modifiers are not composable'}
            expected[site['site']] = {'status':'RECORDED','ids':[site['modification_id']]}
    actual = {r['site']: r['chem_mod_ids'] for r in after['monomer_mappings']['rows']}
    return {'check':'exact-recovery-modifier-ids','status':'PASS' if expected == actual else 'REVIEW'}
