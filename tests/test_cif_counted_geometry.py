"""Final pair observation must not re-enter or change the refinement owner."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest

from nasolve import cif_counted_contribution as counted
from nasolve.topostitch_recipe import recipe_digest
from tests.test_topostitch_pair_geometry import fixture


@pytest.fixture
def case(monkeypatch):
    attribution, declarations, observed, selection = fixture()
    sites = [[1., 2., 3.], [4., 5., 6.]]
    attribution['points_sha256'] = observed['native_state']['force_sites_sha256'] = recipe_digest(sites)
    binding = {'binding': 'test compiled object'}
    declarations['compiled_binding_sha256'] = attribution['binding_sha256'] = recipe_digest(binding)
    prepared = dict(compiled_binding=binding, native_observation=deepcopy(observed),
                    provider_selection=deepcopy(selection))
    # A final native state differs legitimately from its starting preparation.
    prepared['native_observation']['native_state']['force_sites_sha256'] = 'a'*64
    change = []; events = []; kernel_count = [17]; xrs = object(); gr = object(); flex = object()
    class Recipe:
        def describe_terms(self, points, *, atom_identities):
            events.append('measure'); kernel_count[0] += 1
            if change:
                if change[0] == 'state': sites[0][0] += 1
                if change[0] == 'identity': model.get_xray_structure = lambda: object()
                if change[0] == 'lifetime': owner.calls += 1
                if change[0] == 'inventory': observed['origin_ids'][0] += 1
            return deepcopy(attribution)
    recipe = Recipe(); recipe._gr = gr; recipe._flex = flex; recipe._correction = counted.correction
    class Contribution:
        _recipe = recipe
        def evaluate(self): raise AssertionError("No contribution evaluation during capture")
        def _declarations(self): return deepcopy(declarations)
        def binding_report(self): return {'binding': 'unchanged'}
        def revalidate(self, terms, *, current_context):
            assert terms == observed['terms'] and current_context == observed['context']
    contribution = Contribution()
    geometry = object(); manager = NS(geometry=geometry)
    model = NS(restraints_manager=manager, get_xray_structure=lambda: xrs)
    class Owner:
        def __init__(self):
            self._closed = True; self._entered = True; self._poisoned = False; self._call = None; self.calls = 15
            self._model = model; self._manager = manager; self._geo = geometry
            self._recipe = recipe; self._contribution = contribution
            self._contribution_methods={n:getattr(contribution,n).__func__ for n in ("evaluate","revalidate","binding_report")}
            self._factory = NS(NativePairRecipe=Recipe); self._api = {'gr': gr}; self._recipe_flex = flex
            self._report_digest = recipe_digest(contribution.binding_report())
            self._context = observed['context']; self._baseline = {}; self._identities = ['a', 'b']
            self._helper_sources = NS(expected={'cif_live_nonbonded_policy':'a'*64,'cif_refinement_output':'b'*64})
            self._observer = NS(observe_native_pair_terms=lambda *a, **kw: deepcopy(observed))
            self._kernel = NS(statistics=lambda: dict(policy_id='native-parallelity-kernel-adapter-v1',
                successful_calls=kernel_count[0],gradient_calls=0,energy_only_calls=kernel_count[0],maximum_proxy_count=14))
        def statistics(self): return dict(closed=self._closed, poisoned=self._poisoned, successful_calls=self.calls)
        def _native_files(self): events.append('source check')
        def _bindings(self, *, idle): assert idle; events.append('idle bindings')
        def _state(self): return {'sites':deepcopy(sites)}
    monkeypatch.setattr(counted, 'CountedContributionOwner', Owner)
    owner = Owner()
    return NS(owner=owner, prepared=prepared, change=change, observed=observed, recipe=recipe,
              events=events, before=deepcopy(sites))


def capture(c):
    from nasolve.cif_counted_geometry import capture_closed_pair_geometry
    return capture_closed_pair_geometry(c.owner, prepared=c.prepared,
        expected_prepared_sha256=recipe_digest(c.prepared))


def test_closed_owner_reports_once_without_reclassifying_optimizer_calls(case):
    c = case; original = deepcopy(c.prepared); result = capture(c)
    assert c.prepared == original and c.owner._state()['sites'] == c.before
    assert c.events.count('measure') == 1 and c.events.count('idle bindings') == 2
    assert c.owner.statistics()['successful_calls'] == 15
    assert result['diagnostic_kernel_before']['successful_calls'] == 17
    assert result['diagnostic_kernel_after']['successful_calls'] == 18
    assert result['native_state'] == c.observed['native_state']
    assert result['native_state_unchanged'] is True and result['scientific_acceptance'] is False
    assert 'terms' not in result and 'native_observation' not in result
    assert result['prepared_sha256'] == recipe_digest(original)


@pytest.mark.parametrize('defect', ['active','poisoned','recursive','no_calls','inventory','override_describe','override_evaluate'])
def test_unqualified_owner_or_replaced_measurement_refuses(case, defect):
    c = case
    if defect == 'active': c.owner._closed = False
    elif defect == 'poisoned': c.owner._poisoned = True
    elif defect == 'recursive': c.owner._call = object()
    elif defect == 'no_calls': c.owner.calls = 0
    elif defect == 'inventory': c.observed['origin_ids'][0] += 1
    else: setattr(c.recipe, defect.removeprefix('override_') if defect == 'override_evaluate' else 'describe_terms', lambda *a, **kw: {})
    with pytest.raises(ValueError): capture(c)
    assert 'measure' not in c.events


@pytest.mark.parametrize('change', ['state','identity','lifetime','inventory'])
def test_changed_state_during_read_is_not_a_complete_report(case, change):
    case.change.append(change)
    with pytest.raises(ValueError): capture(case)


@pytest.mark.parametrize('name',['evaluate','revalidate','binding_report'])
def test_replaced_contribution_instance_methods_refuse_before_measurement(case,name):
    setattr(case.owner._contribution,name,lambda *a,**kw: {})
    with pytest.raises(ValueError,match='instance methods'):capture(case)
    assert 'measure' not in case.events
