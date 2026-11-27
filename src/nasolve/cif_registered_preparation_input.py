"""Frozen registered-backbone role for local component preparation intake.

Image endpoints remain separate registered roles. This carrier does not authorize
native execution, image forces or ordinary publication. Modified image endpoints
need their own qualified projection consumer; they cannot use the local view.
"""
from hashlib import sha256
from pathlib import Path

from .cif_dictionary_sites import _need, _read, _model_inventory
from .cif_dictionary_store import _bytes, _json
from .cif_registered_preparation_context import POLICY_ID as CONTEXT_POLICY, derive_registered_preparation_context

POLICY_ID = 'registered-local-component-intake-v1'
FILES = dict(registration_model='source.pdb', registration='registration.json',
             discovery='discovery.json', continuations='continuations.json')
ROLE = 'registered_backbone'


def local_component_view(model, record):
    """Project only freshly rederived local selected sites; keep image roles out."""
    _need(record.get('policy_id') == CONTEXT_POLICY and record.get('schema_version') == 1
          and sha256(_read(model)).hexdigest() == record.get('model_sha256'),
          'Registered component view differs from its model/context')
    sites = _model_inventory(model)
    for row in record['image_links']:
        _need(all(sites[site]['code'] in {'DA','DC','DG','DT'}
                  for site in (row['o3_site'],row['phosphate_site'])),
              'Modified image endpoint requires separate projection qualification')
    contexts = {}
    for code, rows in record['site_contexts'].items():
        contexts[code] = []
        for row in rows:
            edges = [row['incoming'], row['outgoing']]
            _need(all(edge is None or (edge['relation']=='local' and edge['operator_xyz']=='x,y,z')
                      for edge in edges), 'Selected image endpoint requires separate projection qualification')
            contexts[code].append(dict(site=row['site'],
                incoming_site=row['incoming']['site'] if row['incoming'] else None,
                outgoing_site=row['outgoing']['site'] if row['outgoing'] else None,
                five_prime_state=row['five_prime_state'],three_prime_state=row['three_prime_state']))
    # This is deliberately not a cif-prepared-model-context-v1 record.
    return dict(policy_id=POLICY_ID, components=record['components'], intent=record['intent'],
                contexts=contexts, expected_links=record['local_links'])


def _reference(record):
    return dict(anchor='dictionary_request_directory', path='inputs/'+ROLE,
                policy_id=POLICY_ID, context_sha256=sha256(_bytes(record)).hexdigest())


def capture_registered_backbone(model, components, declaration):
    """Capture explicit inputs for the existing complete-request file owner."""
    _need(isinstance(declaration,dict) and set(declaration)=={'report',*FILES},
          'Require exact registered preparation input roles')
    paths = {key:Path(declaration[key]) for key in FILES}
    originals = {path:_read(path) for path in paths.values()}
    record = derive_registered_preparation_context(model,declaration['report'],components,**paths)
    view = local_component_view(model,record)
    _need(all(_read(path)==raw for path,raw in originals.items()), 'Registered preparation source changed')
    files = {ROLE+'/'+name:originals[paths[key]] for key,name in FILES.items()}
    files[ROLE+'/intent.json'] = _bytes(record['intent'])
    return dict(files=files, originals=originals, reference=_reference(record), view=view, context=record)


def read_registered_backbone(model, components, inputs, reference):
    """Reconstruct from fixed role paths, including source frame and both images."""
    root=Path(inputs)/ROLE
    _need(isinstance(reference,dict) and reference.get('anchor')=='dictionary_request_directory'
          and reference.get('path')=='inputs/'+ROLE and reference.get('policy_id')==POLICY_ID,
          'Invalid registered preparation role')
    expected={*FILES.values(),'intent.json'}
    _need({p.name for p in root.iterdir()}==expected and all(p.is_file() for p in root.iterdir()),
          'Unrequested registered preparation input')
    paths={key:root/name for key,name in FILES.items()}
    record=derive_registered_preparation_context(model,_json(_read(root/'intent.json')),components,**paths)
    _need(reference==_reference(record), 'Frozen registered preparation context changed')
    return local_component_view(model,record), record
