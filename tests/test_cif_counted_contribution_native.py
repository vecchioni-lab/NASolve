"""Opt-in owned native calls on explicit checksum-bound local Willow controls.

No scientific files ship with this test. Caller supplies the exact plan, factory
package and module pin through NASOLVE_COUNTED_*; absence skips collection.
This matrix tests admission/failure lifetime, not refinement or pair chemistry.
"""
import os
if os.environ.get('NASOLVE_TEST_NATIVE_COUNTED')!='1':
    import pytest
    pytest.skip('Explicit native counted-owner control required',allow_module_level=True)
from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import importlib,json,sys,types
import pytest
from nasolve import cif_counted_contribution as owned
from nasolve import cif_live_nonbonded_policy as policy,cif_parallelity_correction as correction
from nasolve import cif_parallelity_kernel as kernel_owner,cif_refinement_output as state_owner
from cctbx import geometry_restraints as gr
from cctbx.array_family import flex
from iotbx import pdb,phil
from mmtbx.model import manager as Model


def digest(path):return sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope='module')
def native_case():
    plan_path=Path(os.environ['NASOLVE_COUNTED_NATIVE_PLAN']);root=plan_path.parent
    plan=json.loads(plan_path.read_text());package=Path(os.environ['NASOLVE_COUNTED_FACTORY_PACKAGE'])
    assert digest(package/'topostitch_native_recipe.py')==os.environ['NASOLVE_COUNTED_FACTORY_SHA256']
    for row in plan['inputs']:assert digest(root/row['path'])==row['sha256']
    name='counted_test_willow';module=types.ModuleType(name);module.__path__=[str(package)];sys.modules[name]=module
    factory=importlib.import_module(name+'.topostitch_native_recipe')
    coverage=importlib.import_module(name+'.topostitch_pair_coverage')
    observer=importlib.import_module(name+'.topostitch_native_coverage')
    rd=importlib.import_module(name+'.topostitch_recipe').recipe_digest
    data=(root/'healthy/model.pdb').read_bytes();packet=json.loads((root/'healthy/recipe.json').read_text())
    expected=json.loads((root/'healthy/native_core-expected.json').read_text())
    text=(root/'healthy/source.phil').read_text()+'\n'+(root/'healthy/native-core.phil').read_text()
    params=Model.get_default_pdb_interpretation_scope().fetch(source=phil.parse(text)).extract();params.pdb_interpretation.sort_atoms=False
    previous=gr.parallelity_residual_sum;kernel=kernel_owner.ParallelityKernel(gr,flex);gr.parallelity_residual_sum=kernel
    try:
        model=Model(model_input=pdb.input(source_info='owned-counted-test',lines=data.decode('ascii')),expand_with_mtrix=False,process_biomt=False,log=sys.stdout)
        model.process(pdb_interpretation_params=params,make_restraints=True,grm_normalization=True)
        modules={n:importlib.import_module(name+'.'+n) for n in (*factory.CONTRIBUTION_SOURCE_MODULES,'topostitch_native_coverage')}
        pins={n:digest(m.__file__) for n,m in modules.items()}
        helpers={n:digest(importlib.import_module('nasolve.'+n).__file__) for n in owned.HELPER_MODULES}
        observed=observer.observe_native_pair_terms(model,frozen_context=expected['context'],frozen_policy=expected['frozen_policy'],policy_owner=policy,expected_policy_owner_sha256=helpers['cif_live_nonbonded_policy'])
        compiled=factory.NativePairRecipe(packet,data,expected_recipe_sha256=rd(packet),correction=correction)
        binding=rd(compiled.binding_report());requested=coverage.describe_compiled_pair_terms(compiled,packet,expected_binding_sha256=binding)['terms']
        selection=coverage.select_pair_providers(requested,observed['terms'],frozen=dict(context=observed['context'],requested_sha256=rd(requested),native_sha256=observed['terms_sha256']),current_context=observed['context'])
        args=dict(packet=packet,model_bytes=data,expected_recipe_sha256=rd(packet),expected_binding_sha256=binding,provider_selection=selection,expected_provider_selection_sha256=rd(selection))
        options=dict(factory_module=factory,factory_sources=pins,helper_sources=helpers,factory_arguments=args,frozen_policy=expected['frozen_policy'])
        def state():
            energy=model.restraints_manager_energies_sites(compute_gradients=True)
            return dict(hierarchy=state_owner._hierarchy(model),scattering=state_owner._scattering(model.get_xray_structure())[0],fractional=list(model.get_xray_structure().sites_frac()),target=energy.target,gradient=list(energy.gradients),count=energy.number_of_restraints)
        before=state()
        yield types.SimpleNamespace(model=model,geo=model.restraints_manager.geometry,options=options,factory=factory,state=state,before=before,kernel=kernel,rd=rd)
        assert state()==before
        assert 'energies_sites' not in vars(model.restraints_manager) and 'energies_sites' not in vars(model.restraints_manager.geometry)
        assert gr.parallelity_residual_sum is kernel
        for row in plan['inputs']:assert digest(root/row['path'])==row['sha256']
    finally:
        assert gr.parallelity_residual_sum is kernel
        gr.parallelity_residual_sum=previous


def test_actual_owned_calls_and_clean_exit(native_case):
    c=native_case;owner=owned.CountedContributionOwner(c.model,**c.options)
    with owner:
        a=c.model.restraints_manager_energies_sites(compute_gradients=True)
        b=c.model.restraints_manager_energies_sites(compute_gradients=False)
        assert a.target==b.target and b.gradients is None
        assert a.number_of_restraints==c.before['count']+17
        record=owner.statistics()['last'];assert record['inner_calls']==record['extension_calls']==1
        assert record['default_geometry_flags'] and record['disable_asu_cache'] is False
        assert record['geometry_flags']=={n:True for n in policy.FLAG_FIELDS}
        c.model.restraints_manager_energies_sites(geometry_flags=owned._native_api()['types']['flags'](default=True))
        assert owner.statistics()['last']['default_geometry_flags'] is False
        with pytest.raises(ValueError):policy.snapshot_live_nonbonded_policy(c.geo,flags=owned._native_api()['types']['flags'](default=True),normalization=False)
    assert c.state()==c.before and owner.statistics()['successful_calls']==3
    with pytest.raises(ValueError,match='reused'):owner.__enter__()


@pytest.mark.parametrize('defect',['factory_pin','helper_pin','source_model','provider_digest','afitt','ncs','callback','outer_override','inner_override','unsupported_manager'])
def test_admission_refuses_without_installing_or_replacing(native_case,defect):
    c=native_case;options=dict(c.options);undo=lambda:None
    if defect in ('factory_pin','helper_pin'):
        key='factory_sources' if defect=='factory_pin' else 'helper_sources'
        options[key]=dict(options[key]);options[key][next(iter(options[key]))]='0'*64
    elif defect in ('source_model','provider_digest'):
        options['factory_arguments']=dict(options['factory_arguments'])
        if defect=='source_model':options['factory_arguments']['model_bytes']+=b'REMARK wrong\n'
        else:options['factory_arguments']['expected_provider_selection_sha256']='0'*64
    else:
        obj,attr,value={'afitt':(c.model.restraints_manager,'use_afitt',True),'ncs':(c.model.restraints_manager,'cartesian_ncs_manager',object()),'callback':(c.geo,'external_energy_function',lambda:0.),'outer_override':(c.model.restraints_manager,'energies_sites',lambda **k:None),'inner_override':(c.geo,'energies_sites',lambda **k:None),'unsupported_manager':(c.geo,'den_manager',object())}[defect]
        present=attr in vars(obj);old=vars(obj).get(attr);setattr(obj,attr,value)
        def undo():
            if present:setattr(obj,attr,old)
            else:delattr(obj,attr)
    try:
        with pytest.raises(ValueError):owned.CountedContributionOwner(c.model,**options)
        if defect=='outer_override':assert c.model.restraints_manager.energies_sites is value
        else:assert 'energies_sites' not in vars(c.model.restraints_manager)
        if defect=='inner_override':assert c.geo.energies_sites is value
        else:assert 'energies_sites' not in vars(c.geo)
    finally:undo()


@pytest.mark.parametrize('defect',['outer_buffer','inner_entry','extension_entry','wrong_sites','flags','mode','recipe_method','recipe_correction','recipe_flex','torsions','policy','identity'])
def test_failed_call_is_poisoned_and_cannot_return_another_score(native_case,defect):
    c=native_case;owner=owned.CountedContributionOwner(c.model,**c.options);undo=lambda:None
    with owner:
        call=lambda:c.model.restraints_manager_energies_sites(compute_gradients=True)
        if defect=='outer_buffer':call=lambda:c.model.restraints_manager_energies_sites(compute_gradients=True,gradients=flex.vec3_double(c.model.size()))
        elif defect=='inner_entry':call=lambda:c.geo.energies_sites(sites_cart=c.model.get_xray_structure().sites_cart())
        elif defect=='extension_entry':call=lambda:owner.energies_add(energies_obj=object())
        elif defect=='wrong_sites':
            sites=c.model.get_xray_structure().sites_cart();sites[0]=tuple(v+.01 for v in sites[0])
            call=lambda:c.model.restraints_manager.energies_sites(sites_cart=sites)
        elif defect=='flags':call=lambda:c.model.restraints_manager_energies_sites(geometry_flags=owned._native_api()['types']['flags'](default=False))
        elif defect=='mode':call=lambda:c.model.restraints_manager_energies_sites(compute_gradients=1)
        else:
            if defect=='recipe_method':obj,attr,value=owner._recipe,'evaluate_terms',lambda *a,**k:dict(target=0.)
            elif defect=='recipe_correction':obj,attr,value=owner._recipe,'_correction',object()
            elif defect=='recipe_flex':obj,attr,value=owner._recipe,'_flex',object()
            elif defect=='torsions':obj,attr,value=c.geo,'dihedral_proxies',gr.shared_dihedral_proxy(list(c.geo.dihedral_proxies)[1:])
            elif defect=='policy':obj,attr,value=c.geo,'nonbonded_buffer',c.geo.nonbonded_buffer+.1
            else:obj,attr,value=c.model.get_hierarchy().atoms()[0],'name',' BAD'
            present=defect!='recipe_method';old=getattr(obj,attr)
            setattr(obj,attr,value)
            def undo():
                if present:setattr(obj,attr,old)
                else:delattr(obj,attr)
        try:
            with pytest.raises(ValueError):call()
            assert owner.statistics()['poisoned']
        finally:undo()
        with pytest.raises(ValueError,match='failed'):c.model.restraints_manager_energies_sites(compute_gradients=True)
    assert owner.statistics()['closed'] and owner.statistics()['successful_calls']==0
    assert c.state()==c.before


@pytest.mark.parametrize('replacement',['outer','inner','kernel','policy'])
def test_change_after_last_call_refuses_close_and_preserves_foreign_bindings(native_case,replacement):
    c=native_case;owner=owned.CountedContributionOwner(c.model,**c.options);foreign=lambda **k:None
    owner.__enter__();c.model.restraints_manager_energies_sites(compute_gradients=False)
    if replacement=='outer':obj,attr,value=c.model.restraints_manager,'energies_sites',foreign
    elif replacement=='inner':obj,attr,value=c.geo,'energies_sites',foreign
    elif replacement=='kernel':obj,attr,value=gr,'parallelity_residual_sum',foreign
    else:obj,attr,value=c.geo,'nonbonded_buffer',c.geo.nonbonded_buffer+.1
    old=getattr(obj,attr);setattr(obj,attr,value)
    try:
        with pytest.raises(ValueError,match='cleanup failed'):owner.__exit__(None,None,None)
        assert getattr(obj,attr) is value if replacement!='policy' else getattr(obj,attr)==value
        for target in (c.geo,c.model.restraints_manager):
            if target is not obj:assert 'energies_sites' not in vars(target)
        assert owner.statistics()['closed'] and owner.statistics()['poisoned']
    finally:
        if replacement in ('outer','inner'):delattr(obj,attr)
        else:setattr(obj,attr,old)
    assert c.state()==c.before


@pytest.mark.parametrize('defect',['code','defaults','class_binding'])
def test_cached_native_qualification_cannot_admit_changed_loaded_function(native_case,defect):
    c=native_case;api=owned._native_api();function=api['outer']
    if defect=='class_binding':obj,attr,value=api['Restraints'],'energies_sites',lambda *a,**k:None
    elif defect=='code':obj,attr,value=function,'__code__',(lambda *a,**k:None).__code__
    else:obj,attr,value=function,'__defaults__',('changed',)
    original=getattr(obj,attr);setattr(obj,attr,value)
    try:
        with pytest.raises(ValueError,match='call chain changed'):owned.CountedContributionOwner(c.model,**c.options)
        assert 'energies_sites' not in vars(c.model.restraints_manager) and 'energies_sites' not in vars(c.geo)
    finally:setattr(obj,attr,original)
    assert c.state()==c.before


def test_policy_drift_before_entry_poisoned_without_installing(native_case):
    c=native_case;owner=owned.CountedContributionOwner(c.model,**c.options)
    old=c.geo.nonbonded_buffer;c.geo.nonbonded_buffer=old+.1
    try:
        with pytest.raises(ValueError):owner.__enter__()
    finally:c.geo.nonbonded_buffer=old
    assert owner.statistics()['poisoned']
    assert 'energies_sites' not in vars(c.model.restraints_manager) and 'energies_sites' not in vars(c.geo)
    with pytest.raises(ValueError,match='reused'):owner.__enter__()
    assert c.state()==c.before


def test_explicit_unnormalized_native_call_keeps_raw_target_and_gradient(native_case):
    c=native_case;manager=c.model.restraints_manager;original=manager.normalization
    manager.normalization=False
    try:
        native=c.model.restraints_manager_energies_sites(compute_gradients=True)
        owner=owned.CountedContributionOwner(c.model,**c.options)
        extra=owner._contribution.evaluate([list(p) for p in c.model.get_xray_structure().sites_cart()],
            atom_identities=owner._identities,compute_gradients=True)
        with owner:
            actual=c.model.restraints_manager_energies_sites(compute_gradients=True)
            assert actual.normalization_factor is None and owner.statistics()['last']['normalization'] is None
            assert actual.target==pytest.approx(native.target+extra['target'],rel=1e-12,abs=1e-10)
            assert actual.number_of_restraints==native.number_of_restraints+extra['supported_count']
            expected=[x+y for a,b in zip(native.gradients,extra['gradients']) for x,y in zip(a,b)]
            assert list(actual.gradients.as_double())==pytest.approx(expected,rel=1e-11,abs=1e-10)
    finally:manager.normalization=original
    assert c.state()==c.before
