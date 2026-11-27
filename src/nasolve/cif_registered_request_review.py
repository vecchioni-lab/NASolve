"""Read-only binding of genuine construction to a separate original diagnostic.

This is not a complete-request attempt or publication adapter. It cannot invent
execution ancestry for a separate diagnostic, even when every input agrees.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

from .cif_dictionary_sites import _need, _read

POLICY_ID = 'registered-request-original-runtime-review-v1'


def review_registered_request_runtime(directory, *, runtime):
    """Bind an unattempted registered request to its unchanged original runtime.

    Existing readers validate construction, compiled restraints, registered
    topology, component numerics and native evidence. This join additionally
    requires the same selected source bytes, acquisition recipe/consumer, site
    contexts and ordered shared restraints. No children or checkpoint are made.
    Retained overrides, furanose/terminal resources, extra interpretation controls
    and automatic plane/bond additions need separate qualification and refuse.
    ReadySet/changed-model selections remain outside this original-only policy.
    Returned references are relative to the request and runtime anchors.
    """
    from .cif_complete_request import inspect_dictionary_request
    from .cif_acquisition_sources import read_acquisition_sources
    from .cif_runtime_bundle import resolve_runtime_bundle
    from .cif_registered_preparation_native import _review_original_selection
    from .cif_component_runtime import component_runtime_evidence, verify_component_runtime_resources
    from .cif_dictionary_bundle import read_dictionary_bundle
    from .cif_dictionary_sites import read_dictionary_sites

    root = Path(directory).absolute(); state = inspect_dictionary_request(root)
    _need(state['state'] == 'RECORDED' and not state['attempts'],
          'Registered request review requires an unattempted frozen request')
    request = state['request']; config = request['configuration']; controls = config['controls']
    compiler_keys = [k for k in ('explicit_na_policy', 'literal_na_inputs') if k in config]
    _need('registered_backbone' in config and 'construction_inputs' in config and len(compiler_keys) == 1,
          'Registered review requires genuine construction and one compiled restraint source')
    _need(not set(config).intersection({'plane_support','plane_generation_policy','bond_targets','bond_discovery_policy'})
          and 'interpretation_controls' not in controls
          and all(s['retained'] is None and s['terminal_resource'] is None and 'furanose_reaction' not in s
                  for s in controls['sites'].values()),
          'Registered runtime request review does not qualify these additional input roles')
    raw_request = _read(root/'request.json'); inputs = root/'inputs'
    codes = sorted(config['components'])
    sources = read_acquisition_sources(inputs/'sources')['sources']
    selected = resolve_runtime_bundle(runtime)
    review = _review_original_selection(inputs, codes, config['registered_backbone'], selected)
    manifest = selected['manifest']; path = selected['manifest_path']; raw_runtime = _read(path)
    _need(sha256(raw_runtime).hexdigest() == review['runtime']['sha256']
          and manifest['source_selection']['bundle'] == 'evidence/bundle',
          'Registered runtime or embedded bundle role changed')
    entries = {}
    with component_runtime_evidence(path.parent, manifest, subtree='bundle') as evidence:
        bundle = evidence/'evidence/bundle'; prepared = read_dictionary_bundle(bundle); report = prepared['report']
        _need(report['components'] == codes
              and all(report[k] == controls[k] for k in ('consumer','native_context','expected_links')),
              'Runtime component coverage or native context differs from the request')
        _need(_read(prepared['model']) == _read(inputs/'model.pdb'),
              'Runtime bundle model differs from the request')
        _need([_read(bundle/n) for n in report['supplementary_phils']]
              == [_read(inputs/n) for n in controls['supplementary_phils']],
              'Runtime shared restraints or their order differ from the request')
        for code in codes:
            child = read_dictionary_sites(bundle/'components'/code)
            site = child['report']; snapshot = child['snapshot']; intent = controls['sites'][code]
            _need(_read(snapshot['source']) == _read(sources[code]['source'])
                  and snapshot['manifest']['request'] == config['components'][code]['dictionary_request']
                  and snapshot['manifest']['consumer'] == controls['consumer'],
                  'Runtime component source, acquisition recipe or consumer differs from the request')
            _need(site['contexts'] == intent['contexts'] and site['terminal_resource'] is None
                  and site.get('phosphate_atom_policy') == intent['phosphate_atom_policy']
                  and 'furanose_reaction' not in site and 'construction_targets' not in site,
                  'Runtime component site or phosphate context differs from the request')
            entries[code] = snapshot['entry_id']
    verify_component_runtime_resources(path, manifest)
    final_state = inspect_dictionary_request(root)
    _need(final_state == state and _read(root/'request.json') == raw_request and _read(path) == raw_runtime,
          'Registered request or runtime changed during source binding')
    return dict(schema_version=1, policy_id=POLICY_ID, status='REGISTERED_REQUEST_RUNTIME_BOUND_FOR_REVIEW',
        request=dict(anchor='dictionary_request_directory',path='request.json',sha256=sha256(raw_request).hexdigest(),
                     record_sha256=request['record_sha256']),
        construction_inputs=deepcopy(config['construction_inputs']),
        **{key:deepcopy(config[key]) for key in compiler_keys}, entries=entries,
        original_runtime_review=review, execution_ancestry='SEPARATE_DIAGNOSTIC',
        ordinary_admission=False, refinement='NOT_RUN', scientific_qualification='NOT_ASSESSED')
