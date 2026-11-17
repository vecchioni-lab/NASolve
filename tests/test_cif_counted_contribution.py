"""No native dependency: source binding and failure-cleanup invariants only."""
from hashlib import sha256
import importlib.util
from types import SimpleNamespace
import pytest
from nasolve.cif_counted_contribution import _Sources,CountedContributionOwner


@pytest.fixture
def source(tmp_path):
    path=tmp_path/'counted_fixture.py'
    path.write_text('def evaluate(x=1):\n    return x+1\n\nclass Factory:\n    def evaluate(self,x):\n        return x+2\n')
    spec=importlib.util.spec_from_file_location('counted_fixture',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,{'fixture':sha256(path.read_bytes()).hexdigest()}


def test_source_guard_matches_loaded_code_and_remains_read_only(source):
    module,pins=source;guard=_Sources({'fixture':module},pins)
    original=module.evaluate;guard.check()
    assert module.evaluate is original and module.evaluate()==2


@pytest.mark.parametrize('defect',['missing_pin','wrong_pin','foreign_function','changed_code','changed_method'])
def test_factory_source_refuses_before_admission(source,defect):
    module,pins=source
    if defect=='missing_pin':pins={}
    elif defect=='wrong_pin':pins={'fixture':'0'*64}
    elif defect=='foreign_function':
        # A foreign callable pretending to be local still has foreign globals.
        def foreign(x=1):return x+1
        foreign.__module__=module.__name__;foreign.__qualname__='evaluate';module.evaluate=foreign
    elif defect=='changed_code':module.evaluate.__code__=(lambda x=1:x+3).__code__
    else:module.Factory.evaluate.__code__=(lambda self,x:x+4).__code__
    with pytest.raises(ValueError):_Sources({'fixture':module},pins)


@pytest.mark.parametrize('defect',['source','binding','code','defaults','method'])
def test_live_helper_changes_refuse(source,defect):
    module,pins=source;guard=_Sources({'fixture':module},pins)
    if defect=='source':
        from pathlib import Path
        p=Path(module.__file__);p.write_text(p.read_text()+'# changed\n')
    elif defect=='binding':module.evaluate=lambda x=1:x+1
    elif defect=='code':module.evaluate.__code__=(lambda x=1:x+1).__code__
    elif defect=='defaults':module.evaluate.__defaults__=(4,)
    else:module.Factory.evaluate=lambda self,x:x+2
    with pytest.raises(ValueError):guard.check()


def owner_at_exit():
    owner=object.__new__(CountedContributionOwner)
    owner._manager=SimpleNamespace();owner._geo=SimpleNamespace()
    owner._outer_adapter=lambda:None;owner._inner_adapter=lambda:None
    owner._manager.energies_sites=owner._outer_adapter;owner._geo.energies_sites=owner._inner_adapter
    owner._closed=False;owner._poisoned=False
    owner._check=lambda:None;owner._bindings=lambda **kwargs:None;owner._native_files=lambda:None
    return owner


@pytest.mark.parametrize('failed',[False,True])
def test_cleanup_restores_only_its_own_instance_bindings(failed):
    owner=owner_at_exit();error=RuntimeError('native failed') if failed else None
    assert owner.__exit__(type(error) if error else None,error,None) is False
    assert 'energies_sites' not in vars(owner._geo) and 'energies_sites' not in vars(owner._manager)
    assert owner._closed and owner._poisoned is failed


@pytest.mark.parametrize('foreign',['outer','inner','both'])
def test_foreign_replacement_survives_while_remaining_owned_binding_cleans_up(foreign):
    owner=owner_at_exit();replacement=lambda:None
    if foreign in ('outer','both'):owner._manager.energies_sites=replacement
    if foreign in ('inner','both'):owner._geo.energies_sites=replacement
    original=RuntimeError('native failed')
    with pytest.raises(ValueError,match='cleanup failed') as caught:
        owner.__exit__(RuntimeError,original,None)
    assert caught.value.__cause__ is original
    for name,obj in [('outer',owner._manager),('inner',owner._geo)]:
        if foreign in (name,'both'):assert obj.energies_sites is replacement
        else:assert 'energies_sites' not in vars(obj)
    assert owner._closed and owner._poisoned


@pytest.mark.parametrize('boundary',['before','after'])
def test_lifetime_check_failure_never_strands_owned_adapters(boundary):
    owner=owner_at_exit()
    def changed(**kwargs):raise ValueError('changed source or policy')
    if boundary=='before':owner._check=changed
    else:owner._bindings=changed
    with pytest.raises(ValueError,match='changed source or policy'):
        owner.__exit__(None,None,None)
    assert 'energies_sites' not in vars(owner._manager) and 'energies_sites' not in vars(owner._geo)
    assert owner._closed and owner._poisoned


def test_existing_standard_contextmanager_helpers_are_source_bound(tmp_path):
    path=tmp_path/'standard_wrapped.py'
    path.write_text('from contextlib import contextmanager\n@contextmanager\ndef owner():\n    yield 1\n')
    spec=importlib.util.spec_from_file_location('standard_wrapped',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    guard=_Sources({'fixture':module},{'fixture':sha256(path.read_bytes()).hexdigest()})
    with module.owner() as value:assert value==1
    guard.check()
    module.owner.__wrapped__.__code__=(lambda:2).__code__
    with pytest.raises(ValueError):guard.check()


def test_foreign_decorator_cannot_borrow_source_attested_body(source):
    module,pins=source;original=module.evaluate
    def wrapper(x=1):return 100
    wrapper.__wrapped__=original;wrapper.__module__=module.__name__
    module.evaluate=wrapper
    with pytest.raises(ValueError,match='wrapper'):_Sources({'fixture':module},pins)


def test_standard_wrapper_closure_cannot_be_replaced(tmp_path):
    path=tmp_path/'wrapped_cell.py'
    path.write_text('from contextlib import contextmanager\n@contextmanager\ndef owner():\n    yield 1\n')
    spec=importlib.util.spec_from_file_location('wrapped_cell',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    guard=_Sources({'fixture':module},{'fixture':sha256(path.read_bytes()).hexdigest()})
    module.owner.__closure__[0].cell_contents=lambda:None
    with pytest.raises(ValueError,match='closure'):guard.check()


@pytest.mark.parametrize('boundary',['profile','native'])
def test_qualified_bytes_are_rechecked_despite_unchanged_file_size_and_timestamp(tmp_path,boundary):
    import os
    from nasolve.cif_counted_contribution import _check_files
    path=tmp_path/(boundary+'.bin');path.write_bytes(b'original')
    saved=path.stat();pins=((path,sha256(path.read_bytes()).hexdigest()),)
    _check_files(pins)
    path.write_bytes(b'modified');os.utime(path,ns=(saved.st_atime_ns,saved.st_mtime_ns))
    assert path.stat().st_size==saved.st_size and path.stat().st_mtime_ns==saved.st_mtime_ns
    with pytest.raises(ValueError,match='qualified file changed'):_check_files(pins)


def test_packaged_native_profiles_match_owner_source_pins():
    from nasolve.cif_counted_contribution import _profile_pins,_check_files
    pins=_profile_pins();assert len(pins)==2
    _check_files(pins)


def test_changed_native_bytes_at_exit_never_strand_instance_adapters():
    owner=owner_at_exit()
    def changed():raise ValueError('native bytes changed')
    owner._native_files=changed
    with pytest.raises(ValueError,match='native bytes changed'):owner.__exit__(None,None,None)
    assert 'energies_sites' not in vars(owner._manager) and 'energies_sites' not in vars(owner._geo)
    assert owner._closed and owner._poisoned


def test_failed_entry_without_adapters_cannot_be_reused():
    owner=owner_at_exit()
    del owner._manager.energies_sites;del owner._geo.energies_sites
    owner._entered=False
    def changed():raise ValueError('entry source changed')
    owner._native_files=changed
    with pytest.raises(ValueError,match='entry source changed'):owner.__enter__()
    assert owner._poisoned and not owner._entered
    assert 'energies_sites' not in vars(owner._manager) and 'energies_sites' not in vars(owner._geo)
    owner._native_files=lambda:None
    with pytest.raises(ValueError,match='reused'):owner.__enter__()


def observed_wrapper(tmp_path):
    from types import CodeType,FunctionType
    from nasolve import cif_refinement_runtime as runtime
    from tests.test_cif_parallelity_kernel import setup,Buffer
    points,proxy,gr,flex=setup();kernel=runtime.ParallelityKernel(gr,flex)
    def cell(value):return (lambda:value).__closure__[0]
    code=next(c for c in runtime.run_compatible_refinement.__code__.co_consts
              if isinstance(c,CodeType) and c.co_name=='observed')
    seen=set();values=dict(kernel=kernel,observations=tmp_path,seen=seen)
    wrapper=FunctionType(code,vars(runtime),'observed',None,tuple(cell(values[n]) for n in code.co_freevars))
    wrapper.__qualname__='run_compatible_refinement.<locals>.observed'
    return wrapper,kernel,seen,dict(sites_cart=Buffer(points),proxies=[proxy],gradient_array=None)


def test_exact_existing_runtime_wrapper_keeps_unique_original_records(tmp_path):
    from nasolve import cif_counted_contribution as owned
    from nasolve.refinement_parallelity import _code
    wrapper,kernel,seen,call=observed_wrapper(tmp_path)
    guard=owned._ObservedKernel(wrapper);assert guard.kernel is kernel
    first=wrapper(**call);guard.check()
    files=list(tmp_path.glob('*.json'));assert len(files)==len(seen)==1
    before=files[0].read_bytes();stamp=files[0].stat().st_mtime_ns
    assert wrapper(**call)==first;guard.check(full=True)
    assert files[0].read_bytes()==before and files[0].stat().st_mtime_ns==stamp
    assert len(list(tmp_path.glob('*.json')))==1
    assert _code()  # The currently qualified v3 helper bytes still match exactly.


@pytest.mark.parametrize('defect',['foreign','code','kernel_cell','directory_cell','seen_cell','unknown_cell'])
def test_unqualified_existing_wrapper_shape_is_refused(tmp_path,defect):
    from nasolve import cif_counted_contribution as owned
    wrapper,kernel,seen,call=observed_wrapper(tmp_path)
    if defect=='foreign':
        def foreign(**kwargs):return 0.
        foreign.__wrapped__=wrapper;wrapper=foreign
    elif defect=='code':
        def changed():
            return lambda **kwargs:(kernel,seen,tmp_path)
        wrapper.__code__=changed().__code__
    else:
        values=dict(zip(wrapper.__code__.co_freevars,wrapper.__closure__))
        if defect=='kernel_cell':values['kernel'].cell_contents=object()
        elif defect=='directory_cell':values['observations'].cell_contents='not a Path'
        elif defect=='seen_cell':values['seen'].cell_contents=[]
        else:wrapper.__qualname__='some_other_owner.<locals>.observed'
    with pytest.raises(ValueError):owned._ObservedKernel(wrapper)


@pytest.mark.parametrize('defect',['kernel','directory','seen','shrinking_seen','changed_record','deleted_record'])
def test_observed_wrapper_lifetime_drift_is_refused(tmp_path,defect):
    from nasolve import cif_counted_contribution as owned
    wrapper,kernel,seen,call=observed_wrapper(tmp_path);guard=owned._ObservedKernel(wrapper)
    wrapper(**call);guard.check()
    values=dict(zip(wrapper.__code__.co_freevars,wrapper.__closure__))
    if defect=='kernel':values['kernel'].cell_contents=object()
    elif defect=='directory':values['observations'].cell_contents=tmp_path/'other'
    elif defect=='seen':values['seen'].cell_contents=set(seen)
    elif defect=='shrinking_seen':seen.clear()
    elif defect=='changed_record':next(tmp_path.glob('*.json')).write_text('{}')
    else:next(tmp_path.glob('*.json')).unlink()
    with pytest.raises((ValueError,OSError)):guard.check(full=True)


def test_observation_growth_requires_matching_record_bytes(tmp_path):
    from nasolve import cif_counted_contribution as owned
    wrapper,kernel,seen,call=observed_wrapper(tmp_path);guard=owned._ObservedKernel(wrapper)
    seen.add((123,'0'*64))
    with pytest.raises((ValueError,OSError)):guard.check()
