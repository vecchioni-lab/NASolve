"""Prepare an owned dictionary request from ordinary sources and model intent.

This entry point freezes inputs only. The existing complete request owns cache
lookup, bounded generation, qualification, repair, recovery and immutable output.
It does not run ReadySet, replace a checkpoint or infer missing chemical intent.
"""
from copy import deepcopy
from pathlib import Path

from .cif_acquisition_sources import _codes, freeze_acquisition_sources, read_acquisition_sources
from .cif_complete_request import _LIMITS, _compiler_input, _compiler_references, _continuation_fields, _construction_input, initialize_dictionary_request
from .cif_dictionary_sites import _consumer, _need, _read
from .cif_generation_acquisition import generation_dictionary_options
from .cif_acquisition_attempt import _generation_binding
from .cif_model_context import derive_prepared_model_context
from .cif_native_context import FULL_MODEL_POLICY_ID
from .cif_repair_attempt import _root
from .cif_restraint_context import derive_restraint_context


def initialize_postmr_dictionary_request(model, report, components, source_output, output, *,
        consumer, ready_set_executable, supplementary_phils, data_root=None, continuation_options=None, literal_na_inputs=None, explicit_na_policy=None, frozen_sources=None, construction_inputs=None, **execution_limits):
    """Freeze ordinary sources and derived contexts for one existing request.

    Components specify code/generation and optional retained_snapshot,
    terminal_resource or phosphate_atom_policy. Site/link declarations are
    derived, never supplied as overrides. supplementary_phils is an explicit
    ordered sequence; an empty sequence declares absent custom restraints.
    Required but unsupported inputs must be converted faithfully, never omitted.
    With literal_na_inputs, supplementary_phils names the original ordered inputs;
    the frozen compiler artifact must match them and the exact model before its
    compiled PHIL is selected. Original evidence accompanies the owned request.
    The literal artifact may use native-capture or source-bound PDB identities;
    the latter also binds overlapping source bytes at complete intake. Neither
    mode replaces final native qualification or invents native capture indices.
    Alternatively explicit_na_policy binds an existing C80 artifact to the exact
    supplied compiled PHIL and model, without re-guessing or compiling relationships.
    Its selected component source bytes must agree with ordinary acquisition.

    Optional frozen_sources consumes a previously frozen ordinary source selection
    without rediscovery. Its complete component set must match. In this mode,
    source_output, ready_set_executable and data_root must all be None; only output
    is a fresh destination. This preserves source evidence, not proof that a model
    was constructed from it. Optional construction_inputs supplies the ordinary
    run's C196 record and binds that producer join through the complete request.
    Only its declared files are frozen; old runs without a record cannot acquire
    construction claims retroactively. This does not enable ordinary adoption.

    Destinations must be fresh, disjoint and outside input/SDK trees.
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
    _compiler_references(literal_na_inputs,explicit_na_policy)
    phils = list(supplementary_phils); literal_originals = []
    if literal_na_inputs is not None:
        literal_root = _root(literal_na_inputs)
        literal = _compiler_input('literal_na_inputs',literal_root)
        literal_originals = [(Path(p),_read(p)) for p in phils]
        _need(_read(model) == _read(literal['model'])
              and [data for _,data in literal_originals] == [_read(literal_root/r['path']) for r in literal['report']['original_phils']],
              'Literal provenance differs from original model or ordered PHIL inputs')
        phils = literal['phils']
    if explicit_na_policy is not None:
        compiled = _compiler_input('explicit_na_policy',_root(explicit_na_policy))
        _need(_read(model) == _read(compiled['model'])
              and [_read(p) for p in phils] == [_read(p) for p in compiled['phils']],
              'Explicit compiler differs from supplied model or compiled PHIL')
    if frozen_sources is not None:
        _need(source_output is None and ready_set_executable is None and data_root is None,
              'Frozen sources cannot be combined with source discovery settings')
    else:
        _need(source_output is not None, 'Require a fresh source selection destination')
    sources = _root(frozen_sources if frozen_sources is not None else source_output)
    request = _root(output)
    destinations = (request,) if frozen_sources is not None else (sources, request)
    for destination in destinations:
        if destination.exists(): raise FileExistsError(destination)
    _need(not sources.is_relative_to(request) and not request.is_relative_to(sources),
          'Source selection and complete request must be separate')
    protected = [_root(item['generation']['installation_root']) for item in components]
    if data_root is not None: protected.append(_root(data_root))
    if frozen_sources is not None: protected.append(sources)
    for value in _compiler_references(literal_na_inputs,explicit_na_policy).values(): protected.append(_root(value))
    protected += [_root(item['retained_snapshot']) for item in components
                  if item.get('retained_snapshot') is not None]
    inputs = [Path(model), *map(Path, phils)]
    inputs += [Path(item['terminal_resource']) for item in components
               if item.get('terminal_resource') is not None]
    _need(all(not d.is_relative_to(p) and not p.is_relative_to(d)
              for d in destinations for p in protected)
          and all(not p.absolute().is_relative_to(d) for d in destinations for p in inputs),
          'PostMR request destinations overlap an input or installation')
    model_context = derive_prepared_model_context(model, report, codes)
    restraint_context = derive_restraint_context(model, phils) if phils else None
    if construction_inputs is not None:
        # Read only the declared construction closure. Ordinary runs may contain
        # unrelated or unpublished artifacts; none are discovered or captured.
        _construction_input(construction_inputs, model, {}, model_context)
    native_context = dict(policy_id=FULL_MODEL_POLICY_ID, monomer_inventory='full_model',
                          custom_restraints='required' if phils else 'absent')
    for item in components: item['contexts'] = model_context['contexts'][item['code']]
    if frozen_sources is None:
        freeze_acquisition_sources(codes, sources, data_root=data_root,
                                   ready_set_executable=ready_set_executable)
    else:
        selected = read_acquisition_sources(sources)
        _need(selected['report']['components'] == codes,
              'Frozen source components differ from the complete prepared-model request')
    _need(all(_read(p) == data for p,data in literal_originals),
          'Literal original PHIL changed during source freezing')
    return initialize_dictionary_request(sources, components, model, request,
        consumer=consumer, expected_links=model_context['expected_links'], native_context=native_context,
        supplementary_phils=phils, model_context=model_context, restraint_context=restraint_context,
        continuation_options=continuation_options, literal_na_inputs=literal_na_inputs, explicit_na_policy=explicit_na_policy, construction_inputs=construction_inputs,
        **execution_limits)

def prepare_postmr_literal_inputs(model, supplementary_phils, frozen_sources, output, *,
                                 data_root=None, ready_set_executable=None):
    """Assemble source-bound literal intake using ordinary source precedence.

    Previously frozen component sources are authoritative and never rediscovered.
    Only additional codes named by explicit pair/stack declarations are selected
    from the ordinary catalogue/selected SDK. The existing C21/C80 compiler owns
    parsing, role checks and emitted bytes; no pairing guesses, native identities,
    numerical qualification, process ownership or new artifact schema are added.
    Inputs and live selection must remain unchanged through publication. A failed
    call preserves partial output and requires a fresh destination.
    """
    from .cif_acquisition_sources import _authority
    from .cif_explicit_na_policy import _model
    from .cif_literal_na_inputs import prepare_source_literal_na_inputs
    from .cif_na_policy import _literal_declarations
    from .curated_ligands import ligand_source

    root = _root(output)
    if root.exists(): raise FileExistsError(root)
    _need(isinstance(supplementary_phils, (list, tuple))
          and 1 <= len(supplementary_phils) <= 63, 'Require ordered original PHIL inputs')
    frozen_root = _root(frozen_sources)
    protected = [frozen_root] + ([_root(data_root)] if data_root is not None else [])
    _need(all(not root.is_relative_to(p) and not p.is_relative_to(root) for p in protected),
          'Literal output overlaps frozen sources or source catalogue')
    inputs = [Path(model), *map(Path, supplementary_phils)]
    _need(all(not p.absolute().is_relative_to(root) for p in inputs), 'Literal output overlaps original inputs')
    originals = {p: _read(p) for p in inputs}
    frozen = read_acquisition_sources(frozen_root)
    site_codes = _model(model)[3]
    declarations = _literal_declarations(supplementary_phils)[0]
    sites = {':'.join(site) for row in declarations for site in row['sites']}
    _need(sites <= site_codes.keys(), 'Literal declaration names an absent model site')
    _need(frozen['sources'].keys() <= set(site_codes.values()), 'Frozen source component is absent from model')
    codes = sorted({site_codes[site] for site in sites})
    choices = {}; sources = {}; selected_bytes = {}
    for code in codes:
        if code in frozen['sources']:
            sources[code] = frozen['sources'][code]['source']
        else:
            choice = ligand_source(code, data_root, ready_set_executable=ready_set_executable)
            _need(choice.code == code, 'Ordinary literal source component differs')
            _authority(code, choice.authority, choice.kind)
            choices[code] = choice; sources[code] = choice.path
        selected_bytes[code] = _read(sources[code])
    def unchanged():
        _need(all(_read(p) == data for p, data in originals.items()), 'Original literal input changed during source selection')
        _need(read_acquisition_sources(frozen_root)['report'] == frozen['report'], 'Frozen literal sources changed')
        _need(all(ligand_source(code, data_root, ready_set_executable=ready_set_executable) == choice
                  for code, choice in choices.items())
              and all(_read(sources[c]) == data for c, data in selected_bytes.items()),
              'Ordinary literal source selection changed')
    unchanged()
    result = prepare_source_literal_na_inputs(model, list(supplementary_phils), sources, root)
    unchanged()
    return result
