"""Prepare an owned dictionary request from ordinary sources and model intent.

This entry point freezes inputs only. The existing complete request owns cache
lookup, bounded generation, qualification, repair, recovery and immutable output.
It does not run ReadySet, replace a checkpoint or infer missing chemical intent.
"""
from copy import deepcopy
from pathlib import Path

from .cif_acquisition_sources import _codes, freeze_acquisition_sources
from .cif_complete_request import _LIMITS, _continuation_fields, initialize_dictionary_request
from .cif_dictionary_sites import _consumer, _need
from .cif_generation_acquisition import generation_dictionary_options
from .cif_acquisition_attempt import _generation_binding
from .cif_model_context import derive_prepared_model_context
from .cif_native_context import FULL_MODEL_POLICY_ID
from .cif_repair_attempt import _root
from .cif_restraint_context import derive_restraint_context


def initialize_postmr_dictionary_request(model, report, components, source_output, output, *,
        consumer, ready_set_executable, supplementary_phils, data_root=None, continuation_options=None, **execution_limits):
    """Freeze ordinary sources and derived contexts for one existing request.

    Components specify code/generation and optional retained_snapshot,
    terminal_resource or phosphate_atom_policy. Site/link declarations are
    derived, never supplied as overrides. supplementary_phils is an explicit
    ordered sequence; an empty sequence declares absent custom restraints.
    Required but unsupported inputs must be converted faithfully, never omitted.

    Both destinations must be fresh, disjoint and outside input/SDK trees.
    Failure preserves all partial work. Resume a published request through
    execute_dictionary_request_attempt at the same output, without reinitializing
    or reselecting sources. Current native qualification, including independent
    original qualification and the existing optional-failure policy, is mandatory.
    The caller still supplies the selected consumer and generation recipe/pins.
    Optional continuation_options freezes one selected-runtime continuation under
    the same owner; initialization never runs it. Ordinary PostMR defaults are unchanged.
    """
    _need(isinstance(components, (list, tuple)) and components,
          'Require explicit PostMR component generation settings')
    components = deepcopy(components)
    for item in components:
        _need(isinstance(item, dict) and {'code', 'generation'} <= item.keys()
              and item.keys() <= {'code', 'generation', 'retained_snapshot',
                                  'terminal_resource', 'phosphate_atom_policy'},
              'Unsupported PostMR component settings or manual context override')
        generation_dictionary_options(item['generation'])
        _generation_binding(item['generation'])
    codes = _codes([item['code'] for item in components])
    _consumer(consumer)
    bounds = {**_LIMITS, 'max_attempts': 5}
    _need(set(execution_limits) <= set(bounds)
          and all(type(v) is int and 1 <= v <= bounds[k] for k, v in execution_limits.items()),
          'Unsupported or unbounded PostMR request limit')
    _continuation_fields(continuation_options,_LIMITS)
    _need(isinstance(supplementary_phils, (list, tuple)), 'Require an explicit ordered PHIL sequence')
    phils = list(supplementary_phils)
    sources = _root(source_output); request = _root(output)
    for destination in (sources, request):
        if destination.exists(): raise FileExistsError(destination)
    _need(not sources.is_relative_to(request) and not request.is_relative_to(sources),
          'Source selection and complete request must be separate')
    protected = [_root(item['generation']['installation_root']) for item in components]
    if data_root is not None: protected.append(_root(data_root))
    protected += [_root(item['retained_snapshot']) for item in components
                  if item.get('retained_snapshot') is not None]
    inputs = [Path(model), *map(Path, phils)]
    inputs += [Path(item['terminal_resource']) for item in components
               if item.get('terminal_resource') is not None]
    _need(all(not d.is_relative_to(p) and not p.is_relative_to(d)
              for d in (sources, request) for p in protected)
          and all(not p.absolute().is_relative_to(d) for d in (sources, request) for p in inputs),
          'PostMR request destinations overlap an input or installation')
    model_context = derive_prepared_model_context(model, report, codes)
    restraint_context = derive_restraint_context(model, phils) if phils else None
    native_context = dict(policy_id=FULL_MODEL_POLICY_ID, monomer_inventory='full_model',
                          custom_restraints='required' if phils else 'absent')
    for item in components: item['contexts'] = model_context['contexts'][item['code']]
    freeze_acquisition_sources(codes, sources, data_root=data_root,
                               ready_set_executable=ready_set_executable)
    return initialize_dictionary_request(sources, components, model, request,
        consumer=consumer, expected_links=model_context['expected_links'], native_context=native_context,
        supplementary_phils=phils, model_context=model_context, restraint_context=restraint_context,
        continuation_options=continuation_options,
        **execution_limits)
