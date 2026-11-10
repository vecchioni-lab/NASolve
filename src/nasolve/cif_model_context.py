"""Read-only ordinary-model context for explicit dictionary requests.

This compiler checks standard phosphodiester connectivity using the ordinary
phosphate auditor. It does not qualify a source dictionary, edit a model, assign
protonation, interpret NAR stack edges or enable automatic PostMR adoption.
"""
from copy import deepcopy
from hashlib import sha256
from math import dist, isfinite
from pathlib import Path
import re

from .backbone import requested_backbone_policy
from .cif_dictionary_sites import _links, _model_inventory, _need, _read
from .cif_dictionary_store import _bytes, _json
from .phosphate import _atoms, _MAX_PO, audit_phosphates, requested_op3_sites

POLICY_ID = 'cif-prepared-model-context-v1'
_BACKBONE = {"O5'", "C5'", "C3'", "O3'"}
_PHOSPHATE = {'P', 'OP1', 'OP2', 'OP3'}


def _intent(report):
    _need(isinstance(report, dict) and isinstance(report.get('post_mr_plan'), dict),
          'Require a frozen ordinary post-MR plan')
    allowed = requested_op3_sites(report)
    backbone = requested_backbone_policy(report)
    _need(not backbone['experimental_passthrough_sites'],
          'Nonstandard backbone needs a separately qualified context adapter')
    postmr = report.get('postmr')
    _need(postmr is None or isinstance(postmr, dict), 'Malformed frozen PostMR report')
    if isinstance(postmr, dict) and 'backbone_chemistry' in postmr:
        actual = postmr['backbone_chemistry']
        fields = ('schema_version', 'default', 'sites', 'experimental_passthrough_sites')
        _need(isinstance(actual, dict) and all(k in actual for k in fields)
              and _bytes({k: actual[k] for k in fields}) == _bytes({k: backbone[k] for k in fields}),
              'PostMR backbone context differs from frozen intent')
    plan = dict(allow_op3_sites=list(allowed), backbone_policy=backbone)
    if 'phosphate_intent' in report['post_mr_plan']:
        plan['phosphate_intent'] = deepcopy(report['post_mr_plan']['phosphate_intent'])
    return _json(_bytes(dict(post_mr_plan=plan)))


def derive_prepared_model_context(model, report, components):
    """Derive exact selected sites and all audited PDB backbone links, read-only.

    A missing explicit OP3 request is never filled from coordinate presence.
    Numbering, sequence order and NAR pairing/stacking are not covalent evidence.
    This first policy requires canonical atom names, one unambiguous PDB model,
    complete standard backbone endpoints and acyclic unbranched connectivity.
    Source chemistry and full-model native qualification remain separate gates.
    """
    _need(isinstance(components, (list, tuple)) and 1 <= len(components) <= 16
          and all(isinstance(c, str) and re.fullmatch(r'[A-Za-z0-9]{1,3}', c) for c in components)
          and len(set(components)) == len(components), 'Require one to sixteen unique selected components')
    codes = sorted(components); intent = _intent(report)
    model = Path(model); data = _read(model); lines = data.decode('utf-8').splitlines()
    _need(not any(l.startswith(('MODEL ', 'ENDMDL')) for l in lines),
          'Explicit MODEL records need a separately reviewed model selector')
    for line in lines:
        if not line.startswith(('ATOM  ', 'HETATM')): continue
        _need(len(line) >= 54 and all(isfinite(float(line[i:i+8])) for i in (30, 38, 46)),
              'Require finite complete model coordinates')
    sites = _model_inventory(model)
    _need(all(any(r['code'] == c for r in sites.values()) for c in codes),
          'Selected component is absent from the prepared model')
    selected = {s for s, r in sites.items() if r['code'] in codes}
    phosphorus = {s for s, r in sites.items() if 'P' in r['atoms']}
    relevant = selected | phosphorus
    for site, row in sites.items():
        names = row['atoms']
        _need(not names & {'O1P', 'O2P', 'O3P', 'O3*', 'O5*', 'C3*', 'C5*'},
              'Prepared-model context requires canonical backbone atom names')
        if site not in relevant: continue
        _need(re.fullmatch(r'[A-Za-z0-9_]:-?[0-9]+', site) is not None
              and _BACKBONE <= names, 'Incomplete or unsupported standard backbone at '+site)
        _need('P' in names or not names & _PHOSPHATE, 'Incomplete phosphate at '+site)
    plan = intent['post_mr_plan']
    _need(set(plan['backbone_policy']['sites']) <= set(sites), 'Frozen backbone intent names an absent site')
    audit = audit_phosphates(model, allow_op3_sites=tuple(plan['allow_op3_sites']),
                             inspect_sites=tuple(sorted(phosphorus)))
    pairs = sorted([row['incoming_site'], row['site']] for row in audit['checked'] if row['incoming_site'] is not None)
    # The ordinary audit respects chain/TER boundaries. An additional nearby
    # endpoint across such a boundary must not silently become a free terminus.
    atoms = _atoms(lines)
    contacts = sorted([o.site, p.site] for p in atoms if p.name == 'P'
                      for o in atoms if o.name == "O3'" and dist(o.xyz, p.xyz) <= _MAX_PO)
    _need(contacts == pairs, 'Unexplained O3-prime/P contact across a boundary or within a residue')
    _links(model, [], pairs)  # Reuse the complete unbranched-link contract.
    incoming = {b: a for a, b in pairs}; outgoing = {a: b for a, b in pairs}
    for a, b in pairs:
        _need(_BACKBONE <= sites[a]['atoms'], 'Incoming backbone endpoint is incomplete at '+a)
    for site in outgoing:
        visited = set(); current = site
        while current in outgoing:
            _need(current not in visited, 'Cyclic backbone needs a separately qualified context adapter')
            visited.add(current); current = outgoing[current]
    for row in audit['checked']:
        _need(row['outgoing_site'] == outgoing.get(row['site']), 'Audited backbone endpoints disagree')
    contexts = {code: [dict(site=s, incoming_site=incoming.get(s), outgoing_site=outgoing.get(s),
        five_prime_state='linked' if s in incoming else 'phosphate' if s in phosphorus else 'free_OH',
        three_prime_state='linked' if s in outgoing else 'free_OH')
        for s in sorted(selected) if sites[s]['code'] == code] for code in codes}
    _links(model, [c for group in contexts.values() for c in group], pairs)
    digest = sha256(data).hexdigest()
    _need(audit['input_sha256'] == digest and _read(model) == data,
          'Prepared model changed during context derivation')
    return dict(schema_version=1, policy_id=POLICY_ID, model_sha256=digest,
                components=codes, intent=intent, contexts=contexts, expected_links=pairs,
                phosphate_audit=audit, scientific_qualification='NOT_ASSESSED')


def validate_prepared_model_context(model, record):
    """Reconstruct the declaration from the frozen model and minimal intent."""
    _need(isinstance(record, dict) and type(record.get('schema_version')) is int
          and record['schema_version'] == 1 and record.get('policy_id') == POLICY_ID,
          'Unsupported prepared-model context')
    _need('intent' in record and 'components' in record, 'Incomplete prepared-model context')
    expected = derive_prepared_model_context(model, record['intent'], record['components'])
    _need(_bytes(record) == _bytes(expected), 'Prepared-model context differs from its frozen derivation')
    return expected
