"""One descriptive observation after counted ownership closes.

The enclosing refinement owner establishes that this is the returned final model.
This observer neither re-enters that owner nor authenticates a written PDB by itself.
The existing native recipe supplies measurements; the controller owns cold review
and compact storage. No force provider is selected or installed here.
"""
from . import cif_counted_contribution as counted

POLICY_ID = 'closed-counted-pair-observation-v1'


def capture_closed_pair_geometry(owner, *, prepared, expected_prepared_sha256):
    need = counted._need
    need(type(owner) is counted.CountedContributionOwner,
         'Require the existing counted owner')
    need(owner._closed and owner._entered and not owner._poisoned and owner._call is None,
         'Pair geometry requires a successfully closed counted owner')
    need(counted._digest(prepared) == expected_prepared_sha256,
         'Changed sealed pair preparation')
    before_stats = owner.statistics()
    need(before_stats['successful_calls'] > 0, 'No completed counted evaluations')
    model, manager, geo = owner._model, owner._manager, owner._geo
    xrs = model.get_xray_structure()
    recipe = owner._recipe

    def unchanged_bindings():
        owner._native_files()
        owner._bindings(idle=True)
        need(model is owner._model and model.restraints_manager is manager
             and manager.geometry is geo and model.get_xray_structure() is xrs,
             'Pair observation changed native owner identity')
        need(owner._contribution._recipe is recipe
             and type(recipe) is owner._factory.NativePairRecipe
             and recipe._gr is owner._api['gr'] and recipe._flex is owner._recipe_flex
             and recipe._correction is counted.correction
             and not any(name in vars(recipe) for name in
                 ('describe_terms', 'evaluate', 'evaluate_terms', '_evaluate_proxies', 'binding_report'))
             and '_declarations' not in vars(owner._contribution),
             'Pair measurement callable or compiled ownership changed')
        need(all(getattr(getattr(owner._contribution, name), '__func__', None) is method
                 and name not in vars(owner._contribution)
                 for name, method in owner._contribution_methods.items()),
             'Contribution instance methods changed during pair observation')
        need(counted._digest(owner._contribution.binding_report()) == owner._report_digest,
             'Pair observation changed frozen contribution')
        need(owner.statistics() == before_stats, 'Pair observation changed counted lifetime')

    unchanged_bindings()
    before = owner._state()
    options = dict(frozen_context=owner._context, frozen_policy=owner._baseline,
        policy_owner=counted.policy,
        expected_policy_owner_sha256=owner._helper_sources.expected['cif_live_nonbonded_policy'],
        state_owner=counted.state_owner,
        expected_state_owner_sha256=owner._helper_sources.expected['cif_refinement_output'])
    observed = owner._observer.observe_native_pair_terms(model, **options)
    original = prepared['native_observation']
    # Only coordinates/native atom state may have moved. Retain the complete
    # original inventory once and record its exact final-state agreement.
    fixed = lambda row: {k:v for k,v in row.items() if k not in ('native_state', 'points_sha256')}
    need(fixed(observed) == fixed(original), 'Final pair inventory differs from sealed preparation')
    owner._contribution.revalidate(observed['terms'], current_context=owner._context)
    declarations = owner._contribution._declarations()
    need(declarations['compiled_binding_sha256'] == counted._digest(prepared['compiled_binding']),
         'Final pair declarations differ from sealed preparation')
    kernel_before = owner._kernel.statistics()
    attribution = recipe.describe_terms(before['sites'], atom_identities=owner._identities)
    kernel_after = owner._kernel.statistics()
    need(attribution['points_sha256'] == observed['native_state']['force_sites_sha256']
         == counted._digest(before['sites']), 'Pair measurement uses different force coordinates')
    need(owner._observer.observe_native_pair_terms(model, **options) == observed
         and owner._state() == before, 'Pair observation changed native atom state')
    unchanged_bindings()
    return counted._detached(dict(schema_version=1, policy_id=POLICY_ID,
        prepared_sha256=expected_prepared_sha256,
        attribution=attribution, compiled_declarations=declarations,
        native_state=observed['native_state'], points_sha256=observed['points_sha256'],
        fixed_observation_sha256=counted._digest(fixed(observed)),
        provider_selection_sha256=counted._digest(prepared['provider_selection']),
        counted_lifetime_sha256=counted._digest(before_stats),
        diagnostic_kernel_before=kernel_before, diagnostic_kernel_after=kernel_after,
        native_state_unchanged=True, scientific_acceptance=False))
