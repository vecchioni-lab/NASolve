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
        yield types.SimpleNamespace(model=model,geo=model.restraints_manager.geometry,options=options,factory=factory,state=state,before=before,kernel=kernel,rd=rd,params=params)
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


@pytest.mark.parametrize('defect',[None,'missing_runtime_pin','wrong_runtime_pin','kernel_cell','directory_cell','seen_cell','shrinking_seen','removed_record'])
def test_existing_observed_wrapper_native_ownership(native_case,tmp_path,defect,prepared=None):
    from nasolve import cif_refinement_runtime as runtime
    c=native_case;directory=tmp_path/'calls';directory.mkdir()
    def cell(value):return (lambda:value).__closure__[0]
    code=next(c for c in runtime.run_compatible_refinement.__code__.co_consts
              if isinstance(c,types.CodeType) and c.co_name=='observed')
    seen=set();values=dict(kernel=c.kernel,observations=directory,seen=seen)
    wrapper=types.FunctionType(code,vars(runtime),'observed',None,tuple(cell(values[n]) for n in code.co_freevars))
    wrapper.__qualname__='run_compatible_refinement.<locals>.observed'
    cells=dict(zip(code.co_freevars,wrapper.__closure__))
    options=dict(c.options);options['helper_sources']=dict(options['helper_sources'],cif_refinement_runtime=digest(runtime.__file__))
    gr.parallelity_residual_sum=wrapper
    try:
        assert c.state()==c.before  # Existing native calls produce an initial genuine record.
        if defect in ('missing_runtime_pin','wrong_runtime_pin'):
            if defect=='missing_runtime_pin':options['helper_sources'].pop('cif_refinement_runtime')
            else:options['helper_sources']['cif_refinement_runtime']='0'*64
            with pytest.raises(ValueError):owned.CountedContributionOwner(c.model,**options)
        else:
            owner=(owned.CountedContributionOwner(c.model,**options) if prepared is None else
                   consume_preparation(c,prepared,helper_sources=options['helper_sources']))
            owner.__enter__()
            if defect=='removed_record':
                c.model.restraints_manager_energies_sites(compute_gradients=True)
                path=next(directory.glob('*.json'));saved=path.read_bytes();path.unlink()
                try:
                    with pytest.raises(ValueError,match='cleanup failed'):owner.__exit__(None,None,None)
                    assert owner.statistics()['closed'] and owner.statistics()['poisoned']
                finally:path.write_bytes(saved)
            else:
                try:
                    if defect is None:
                        first=c.model.restraints_manager_energies_sites(compute_gradients=True)
                        files={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in directory.glob('*.json')}
                        second=c.model.restraints_manager_energies_sites(compute_gradients=False)
                        assert first.target==second.target and first.number_of_restraints==second.number_of_restraints
                        assert files=={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in directory.glob('*.json')}
                        assert owner.statistics()['last']['existing_usage_observation'] is True
                    else:
                        saved_seen=set(seen);key={'kernel_cell':'kernel','directory_cell':'observations','seen_cell':'seen'}.get(defect)
                        original=cells[key].cell_contents if key else None
                        if key:cells[key].cell_contents=object() if key=='kernel' else (tmp_path if key=='observations' else set(seen))
                        else:seen.clear()
                        try:
                            with pytest.raises(ValueError):c.model.restraints_manager_energies_sites(compute_gradients=True)
                            assert owner.statistics()['poisoned']
                        finally:
                            if key:cells[key].cell_contents=original
                            else:seen.update(saved_seen)
                finally:owner.__exit__(None,None,None)
        assert 'energies_sites' not in vars(c.model.restraints_manager) and 'energies_sites' not in vars(c.geo)
        assert c.state()==c.before
    finally:
        assert gr.parallelity_residual_sum is wrapper
        gr.parallelity_residual_sum=c.kernel
    assert c.state()==c.before


def test_self_consistent_changed_native_cell_cannot_borrow_original_recipe_images(native_case):
    from io import StringIO
    c=native_case;data=c.options['factory_arguments']['model_bytes'];lines=data.decode('ascii').splitlines(keepends=True)
    index=next(i for i,line in enumerate(lines) if line.startswith('CRYST1'))
    line=lines[index];edge=float(line[6:15])+.1
    lines[index]=line[:6]+f'{edge:9.3f}{edge:9.3f}'+line[24:]
    model=Model(model_input=pdb.input(source_info='changed-cell-negative',lines=''.join(lines)),
        expand_with_mtrix=False,process_biomt=False,log=StringIO())
    model.process(pdb_interpretation_params=deepcopy(c.params),make_restraints=True,grm_normalization=True)
    native_before=c.model.restraints_manager_energies_sites(compute_gradients=True).target
    policy_now=policy.snapshot_live_nonbonded_policy(model.restraints_manager.geometry,
        flags=owned._native_api()['types']['flags'](default=True),normalization=False)
    args=dict(c.options['factory_arguments']);context=deepcopy(args['provider_selection']['frozen']['context'])
    context['native_exclusion_policy_sha256']=policy_now['policy_sha256']
    context['crystal_sha256']=c.rd(policy_now['policy']['symmetry'])
    observer=importlib.import_module(c.factory.__package__+'.topostitch_native_coverage')
    coverage=importlib.import_module(c.factory.__package__+'.topostitch_pair_coverage')
    observed=observer.observe_native_pair_terms(model,frozen_context=context,frozen_policy=policy_now,
        policy_owner=policy,expected_policy_owner_sha256=c.options['helper_sources']['cif_live_nonbonded_policy'])
    compiled=c.factory.NativePairRecipe(args['packet'],data,expected_recipe_sha256=args['expected_recipe_sha256'],correction=correction)
    requested=coverage.describe_compiled_pair_terms(compiled,args['packet'],expected_binding_sha256=args['expected_binding_sha256'])['terms']
    selection=coverage.select_pair_providers(requested,observed['terms'],
        frozen=dict(context=context,requested_sha256=c.rd(requested),native_sha256=observed['terms_sha256']),current_context=context)
    args.update(provider_selection=selection,expected_provider_selection_sha256=c.rd(selection))
    options=dict(c.options,factory_arguments=args,frozen_policy=policy_now)
    assert context['crystal_sha256']!=c.options['factory_arguments']['provider_selection']['frozen']['context']['crystal_sha256']
    with pytest.raises(ValueError,match='recipe crystal'):
        owned.CountedContributionOwner(model,**options)
    with pytest.raises(ValueError,match='recipe crystal'):
        owned.observe_prepared_pair_contribution(model,factory_module=c.factory,
            factory_sources=c.options['factory_sources'],helper_sources=c.options['helper_sources'],
            packet=args['packet'],model_bytes=data,expected_recipe_sha256=args['expected_recipe_sha256'])
    assert 'energies_sites' not in vars(model.restraints_manager) and 'energies_sites' not in vars(model.restraints_manager.geometry)
    assert c.model.restraints_manager_energies_sites(compute_gradients=True).target==native_before
    assert c.state()==c.before


@pytest.mark.parametrize('group,accepted',[('R 3 :H',True),('P 3',False)])
def test_recipe_crystal_group_uses_native_equivalence_not_symbol_text(native_case,group,accepted):
    c=native_case;packet=deepcopy(c.options['factory_arguments']['packet']);packet['crystal']['space_group']=group
    if accepted:owned._require_recipe_crystal(c.geo,packet,owned._native_api())
    else:
        with pytest.raises(ValueError,match='recipe crystal'):
            owned._require_recipe_crystal(c.geo,packet,owned._native_api())
    assert c.state()==c.before


def prepared_observation(c):
    args=c.options['factory_arguments']
    return owned.observe_prepared_pair_contribution(c.model,
        factory_module=c.factory,factory_sources=c.options['factory_sources'],
        helper_sources=c.options['helper_sources'],packet=args['packet'],
        model_bytes=args['model_bytes'],expected_recipe_sha256=args['expected_recipe_sha256'])


@pytest.mark.parametrize('native_kernel',[False,True])
def test_prepared_pair_observation_is_force_free_and_reuses_existing_selection(native_case,native_kernel):
    c=native_case;calls=[]
    watched={Model.restraints_manager_energies_sites.__code__,
        c.model.restraints_manager.energies_sites.__func__.__code__,
        c.geo.energies_sites.__func__.__code__,c.factory.NativePairRecipe.evaluate_terms.__code__,
        kernel_owner.ParallelityKernel.__call__.__code__}
    def profile(frame,event,arg):
        if event=='call' and frame.f_code in watched:calls.append(frame.f_code.co_name)
    binding=c.kernel._api.parallelity_residual_sum if native_kernel else c.kernel
    gr.parallelity_residual_sum=binding
    previous=sys.getprofile();sys.setprofile(profile)
    try:
        result=prepared_observation(c)
        assert gr.parallelity_residual_sum is binding
    finally:
        sys.setprofile(previous);gr.parallelity_residual_sum=c.kernel
    assert calls==[]
    assert result['provider_selection']==c.options['factory_arguments']['provider_selection']
    assert c.rd(result['compiled_binding'])==c.options['factory_arguments']['expected_binding_sha256']
    observed=result['native_observation']
    assert observed['policy_id']=='topostitch-native-pair-observation-v2'
    assert observed['native_state']['force_sites_sha256']==c.rd(list(c.model.get_xray_structure().sites_cart()))
    assert observed['runtime_authority'] is observed['scientific_acceptance'] is False
    assert result['frozen_policy']['policy_sha256']==c.options['frozen_policy']['policy_sha256']
    assert c.state()==c.before
    assert 'energies_sites' not in vars(c.geo) and 'energies_sites' not in vars(c.model.restraints_manager)


def test_prepared_pair_observation_reads_changed_actual_inventory(native_case):
    c=native_case;original=c.geo.parallelity_proxies
    try:
        c.geo.parallelity_proxies=gr.shared_parallelity_proxy()
        result=prepared_observation(c)
        assert len(result['provider_selection']['additive'])>len(c.options['factory_arguments']['provider_selection']['additive'])
        assert not any(t['kind']=='parallelity' for t in result['native_observation']['terms'])
        # It is a new initial selection, not a mutation of the old supplied record.
        assert len(c.options['factory_arguments']['provider_selection']['additive'])==17
        assert result['provider_selection']['frozen']['native_sha256']!=c.options['factory_arguments']['provider_selection']['frozen']['native_sha256']
    finally:c.geo.parallelity_proxies=original
    assert c.state()==c.before


def test_prepared_pair_observation_refuses_unsynchronized_force_sites(native_case):
    c=native_case;xrs=c.model.get_xray_structure();sites=xrs.sites_frac().deep_copy()
    shifted=sites.deep_copy();shifted[0]=tuple(v+(.001 if i==0 else 0.) for i,v in enumerate(shifted[0]))
    try:
        xrs.set_sites_frac(shifted)
        with pytest.raises(ValueError,match='Hierarchy and scattering'):
            prepared_observation(c)
        assert list(xrs.sites_frac())==list(shifted)
        assert state_owner._hierarchy(c.model)==c.before['hierarchy']
    finally:xrs.set_sites_frac(sites)
    assert c.state()==c.before


def counted_preparation(c):
    args=c.options['factory_arguments']
    return owned.observe_prepared_pair_contribution(c.model,
        factory_module=c.factory,factory_sources=c.options['factory_sources'],
        helper_sources=c.options['helper_sources'],packet=args['packet'],
        model_bytes=args['model_bytes'],expected_recipe_sha256=args['expected_recipe_sha256'],
        counted_baseline=True)


def consume_preparation(c,prepared,**changes):
    args=c.options['factory_arguments']
    options=dict(factory_module=c.factory,factory_sources=c.options['factory_sources'],
        helper_sources=c.options['helper_sources'],packet=args['packet'],
        model_bytes=args['model_bytes'],expected_recipe_sha256=args['expected_recipe_sha256'],
        prepared=prepared,expected_prepared_sha256=c.rd(prepared))
    options.update(changes)
    return owned.owner_from_prepared_pair_contribution(c.model,**options)


def test_prepared_counted_admission_reuses_selection_without_forces_or_replanning(native_case):
    c=native_case;prepared=counted_preparation(c);original=deepcopy(prepared)
    coverage=importlib.import_module(c.factory.__package__+'.topostitch_pair_coverage')
    watched={coverage.select_pair_providers.__code__,c.factory.NativePairRecipe.evaluate_terms.__code__,
        Model.restraints_manager_energies_sites.__code__,kernel_owner.ParallelityKernel.__call__.__code__}
    calls=[];previous=sys.getprofile()
    def profile(frame,event,arg):
        if event=='call' and frame.f_code in watched:calls.append(frame.f_code.co_name)
    sys.setprofile(profile)
    try:owner=consume_preparation(c,prepared)
    finally:sys.setprofile(previous)
    assert calls==[] and prepared==original and c.state()==c.before
    assert owner.statistics()['successful_calls']==0
    assert 'energies_sites' not in vars(c.geo) and 'energies_sites' not in vars(c.model.restraints_manager)
    # Returned ownership has detached its input, not retained mutable caller authority.
    prepared['provider_selection'].clear();prepared['counted_baseline'].clear()
    with owner:
        result=c.model.restraints_manager_energies_sites(compute_gradients=True)
        assert result.number_of_restraints==c.before['count']+17
    assert c.state()==c.before


@pytest.mark.parametrize('defect',['torsion','chirality','normalization','hierarchy_b','scattering_b'])
def test_prepared_counted_admission_refuses_changed_start_before_construction(native_case,defect):
    c=native_case;prepared=counted_preparation(c)
    if defect in ('torsion','chirality'):
        field='dihedral_proxies' if defect=='torsion' else 'chirality_proxies'
        old=getattr(c.geo,field);assert old and len(old)>1
        setattr(c.geo,field,type(old)(list(old)[1:]))
        def restore():setattr(c.geo,field,old)
    elif defect=='normalization':
        old=c.model.restraints_manager.normalization;c.model.restraints_manager.normalization=not old
        def restore():c.model.restraints_manager.normalization=old
    elif defect=='hierarchy_b':
        atom=c.model.get_hierarchy().atoms()[0];old=atom.b;atom.b=old+1
        def restore():atom.b=old
    else:
        xrs=c.model.get_xray_structure();old=xrs.scatterers()[0].u_iso;xrs.scatterers()[0].u_iso=old+.01
        def restore():xrs.scatterers()[0].u_iso=old
    try:
        with pytest.raises(ValueError,match='[Pp]repared|baseline'):
            consume_preparation(c,prepared)
        assert 'energies_sites' not in vars(c.geo) and 'energies_sites' not in vars(c.model.restraints_manager)
    finally:restore()
    assert c.state()==c.before


@pytest.mark.parametrize('defect',['missing_baseline','digest','normalization_type','bonded_signature','native_state','extra_field'])
def test_prepared_counted_admission_refuses_rehashed_incomplete_or_changed_records(native_case,defect):
    c=native_case;prepared=counted_preparation(c);options={}
    if defect=='missing_baseline':prepared.pop('counted_baseline')
    elif defect=='digest':options['expected_prepared_sha256']='0'*64
    elif defect=='normalization_type':prepared['counted_baseline']['outer_normalization']=int(prepared['counted_baseline']['outer_normalization'])
    elif defect=='bonded_signature':prepared['counted_baseline']['bonded']['signature']='0'*64
    elif defect=='native_state':prepared['native_observation']['native_state']['force_sites_sha256']='0'*64
    else:prepared['authority']=True
    with pytest.raises(ValueError):consume_preparation(c,prepared,**options)
    assert 'energies_sites' not in vars(c.geo) and 'energies_sites' not in vars(c.model.restraints_manager)
    assert c.state()==c.before


def test_prepared_counted_admission_refuses_state_drift_before_entry(native_case):
    c=native_case;owner=consume_preparation(c,counted_preparation(c))
    atom=c.model.get_hierarchy().atoms()[0];old=atom.b;atom.b=old+1
    try:
        with pytest.raises(ValueError,match='[Pp]repared'):owner.__enter__()
        assert owner.statistics()['poisoned'] and owner.statistics()['successful_calls']==0
        assert 'energies_sites' not in vars(c.geo) and 'energies_sites' not in vars(c.model.restraints_manager)
    finally:atom.b=old
    with pytest.raises(ValueError,match='reused'):owner.__enter__()
    assert c.state()==c.before


def test_prepared_counted_admission_accepts_fresh_same_input_model(native_case):
    c=native_case;prepared=counted_preparation(c);data=c.options['factory_arguments']['model_bytes']
    model=Model(model_input=pdb.input(source_info='fresh-prepared-consumer',lines=data.decode('ascii')),
        expand_with_mtrix=False,process_biomt=False,log=sys.stdout)
    model.process(pdb_interpretation_params=c.params,make_restraints=True,grm_normalization=True)
    fresh=types.SimpleNamespace(**dict(vars(c),model=model,geo=model.restraints_manager.geometry))
    owner=consume_preparation(fresh,prepared)
    with owner:result=model.restraints_manager_energies_sites(compute_gradients=True)
    assert result.number_of_restraints==c.before['count']+17
    assert 'energies_sites' not in vars(model.restraints_manager.geometry)
    assert c.state()==c.before


def test_prepared_counted_admission_preserves_legacy_pair_only_observation(native_case):
    c=native_case;legacy=prepared_observation(c);strong=counted_preparation(c)
    assert set(legacy)=={'frozen_policy','compiled_binding','native_observation','provider_selection'}
    assert {k:v for k,v in strong.items() if k!='counted_baseline'}==legacy
    old=c.geo.dihedral_proxies;c.geo.dihedral_proxies=gr.shared_dihedral_proxy(list(old)[1:])
    try:
        # Historical pair-only observation never claimed full bonded-phase admission.
        assert prepared_observation(c)==legacy
        assert counted_preparation(c)['counted_baseline']!=strong['counted_baseline']
        with pytest.raises(ValueError):consume_preparation(c,strong)
    finally:c.geo.dihedral_proxies=old
    assert c.state()==c.before


def test_prepared_counted_admission_works_with_existing_usage_wrapper(native_case,tmp_path):
    c=native_case
    test_existing_observed_wrapper_native_ownership(c,tmp_path,None,prepared=counted_preparation(c))


def test_prepared_counted_admission_allows_optimizer_movement_after_entry(native_case):
    c=native_case;owner=consume_preparation(c,counted_preparation(c))
    xrs=c.model.get_xray_structure();original=xrs.sites_frac().deep_copy()
    shifted=original.deep_copy();shifted[0]=tuple(v+(.0001 if i==0 else 0.) for i,v in enumerate(shifted[0]))
    with owner:
        first=c.model.restraints_manager_energies_sites(compute_gradients=True)
        try:
            xrs.set_sites_frac(shifted)
            second=c.model.restraints_manager_energies_sites(compute_gradients=True)
            assert first.target!=second.target and first.number_of_restraints==second.number_of_restraints
            assert owner.statistics()['successful_calls']==2
        finally:xrs.set_sites_frac(original)
    assert c.state()==c.before
