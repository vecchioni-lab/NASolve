"""Opt-in direct native ownership for a frozen four-family pair contribution.

No refinement runner, persistent artifact, provider selection or global kernel
installation lives here. The existing outer runtime owns trusted helper selection,
process lifetime and correction installation. This owner authenticates its exact
factory, model/manager pair, actual force sites and native-owned accumulation.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import dataclasses
import contextlib
import importlib
import inspect
import json
import math
from pathlib import Path
import sys
from types import CodeType, FunctionType, SimpleNamespace

from . import cif_live_nonbonded_policy as policy
from . import cif_parallelity_correction as correction
from . import cif_parallelity_kernel as kernel_owner
from . import cif_refinement_output as state_owner
from . import cif_gradient_audit as gradient_owner

POLICY_ID = 'cif-owned-counted-contribution-v1'
COUNT_POLICY = 'canonical-pair-one-per-proxy-v1'
# Qualify these records before trusting the native-file digests they contain.
# C331's historical profile and reader semantics are unchanged.
_PROFILE_SHA256 = {
    'nonbonded-native-profile.json': 'd35a0b61dd49a75132d16d3bb53b1c636eefbd30c21d19fe5d50a03d018e6ee6',
    'counted-native-profile.json': 'bf41896cc2269508a5ded1816ef4f5a4ed7bdee2fa5532bd94e38428d4715571',
}
HELPER_MODULES = ('cif_live_nonbonded_policy', 'cif_parallelity_correction',
                  'cif_parallelity_kernel', 'cif_refinement_output', 'cif_gradient_audit')


def _need(value, message):
    if not value:
        raise ValueError(message)


def _detached(value):
    return json.loads(json.dumps(value, allow_nan=False))


def _digest(value):
    return state_owner._digest(value)


def _function(module, function, compiled):
    """Authenticate loaded Python code against qualified source without executing it."""
    _need(type(function) is FunctionType and function.__globals__ is vars(module),
          'Foreign function globals in counted contribution')
    current = compiled
    for part in function.__qualname__.split('.'):
        if part=='<locals>':continue
        matches = [c for c in current.co_consts if isinstance(c, CodeType) and c.co_name == part]
        _need(len(matches) == 1, 'Callable is absent from its qualified source')
        current = matches[0]
    _need(function.__code__ == current, 'Loaded callable differs from qualified source')
    return function, function.__code__, deepcopy(function.__defaults__), deepcopy(function.__kwdefaults__)


def _functions(module, function, compiled):
    unwrapped=inspect.unwrap(function)
    if unwrapped is function:return [_function(module,function,compiled)]
    # Existing output readers use the standard contextmanager decorator. Its
    # closure must call precisely the source-attested body, not a user wrapper.
    sample=contextlib.contextmanager(lambda:None)
    _need(type(function) is FunctionType and function.__globals__ is vars(contextlib)
          and function.__code__ == sample.__code__ and len(function.__closure__ or ())==1
          and function.__closure__[0].cell_contents is unwrapped,
          'Unsupported wrapper around counted helper')
    return [(function,function.__code__,deepcopy(function.__defaults__),deepcopy(function.__kwdefaults__)),
            _function(module,unwrapped,compiled)]


class _Sources:
    """Small process-local binding; hashes alone never authorize a supplied callable."""
    def __init__(self, modules, expected):
        _need(type(expected) is dict and set(expected) == set(modules), 'Incomplete counted helper source pins')
        self.modules = dict(modules); self.expected = dict(expected); self.functions = []; self.attributes = []
        for name,module in self.modules.items():
            raw = Path(module.__file__).read_bytes()
            _need(type(expected[name]) is str and hashlib.sha256(raw).hexdigest() == expected[name],
                  'Changed counted helper source: '+name)
            compiled = compile(raw, str(module.__file__), 'exec', dont_inherit=True)
            for key,value in vars(module).items():
                if type(value) is FunctionType and value.__module__ == module.__name__:
                    self.attributes.append((module,key,value))
                    self.functions.extend(_functions(module,value,compiled))
                elif isinstance(value,type) and value.__module__ == module.__name__:
                    self.attributes.append((module,key,value))
                    for method,fn in vars(value).items():
                        if isinstance(fn,(staticmethod,classmethod)): fn=fn.__func__
                        if type(fn) is FunctionType and fn.__module__ == module.__name__:
                            self.attributes.append((value,method,vars(value)[method]))
                            generated=(dataclasses.is_dataclass(value) and method in
                                ('__init__','__repr__','__eq__','__hash__','__setattr__','__delattr__')
                                and fn.__code__.co_filename in ('<string>',dataclasses.__file__))
                            # Dataclass methods are generated by the standard library,
                            # not code blocks in this source. Preserve their actual
                            # binding/code/defaults; the factory/evaluator stay source-attested.
                            if generated:self.functions.append((fn,fn.__code__,deepcopy(fn.__defaults__),deepcopy(fn.__kwdefaults__)))
                            else:self.functions.extend(_functions(module,fn,compiled))
                elif callable(value):
                    self.attributes.append((module,key,value))
                    unwrapped=inspect.unwrap(value)
                    if type(unwrapped) is FunctionType and unwrapped.__module__ == module.__name__:
                        self.functions.append(_function(module,unwrapped,compiled))

        self.closures=[(fn,tuple(c.cell_contents for c in (fn.__closure__ or ()))) for fn,_,_,_ in self.functions]

    def check(self):
        for name,module in self.modules.items():
            _need(hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() == self.expected[name],
                  'Counted helper source changed: '+name)
        _need(all(vars(obj).get(name) is value for obj,name,value in self.attributes),
              'Counted helper callable binding changed')
        _need(all(fn.__code__ is code and fn.__defaults__ == defaults and fn.__kwdefaults__ == kwdefaults
                  for fn,code,defaults,kwdefaults in self.functions), 'Counted helper callable implementation changed')
        _need(all(len(fn.__closure__ or ())==len(values) and all(c.cell_contents is v
                  for c,v in zip(fn.__closure__ or (),values)) for fn,values in self.closures),
              'Counted helper closure changed')


class _ObservedKernel:
    """Recognize the unchanged v3 runtime closure, never unwrap arbitrary callbacks.

    The enclosing source owner must pin cif_refinement_runtime as an extra helper.
    Records grow only after successful existing wrapper calls. Check new records
    during calls and all retained bytes at lifetime boundaries, without creating
    another writer, journal or correction installer.
    """
    def __init__(self, wrapper):
        runtime=importlib.import_module(__package__+'.cif_refinement_runtime')
        _need(type(wrapper) is FunctionType and
              wrapper.__qualname__=='run_compatible_refinement.<locals>.observed',
              'Require the exact existing refinement observation wrapper')
        self._function=_function(runtime,wrapper,compile(Path(runtime.__file__).read_bytes(),
            str(runtime.__file__),'exec',dont_inherit=True))
        _need(wrapper.__code__.co_freevars==('kernel','observations','seen') and len(wrapper.__closure__ or ())==3,
              'Unsupported refinement observation closure')
        self._cells=tuple((cell,cell.cell_contents) for cell in wrapper.__closure__)
        self.kernel,self._directory,self._seen=(value for _,value in self._cells)
        _need(type(self.kernel) is kernel_owner.ParallelityKernel and type(self._directory) is type(Path())
              and type(self._seen) is set and self._directory.is_dir(), 'Unsupported owned observation state')
        self._resolved=self._directory.resolve(); self._known={}
        self.check(full=True)

    def check(self, *, full=False):
        fn,code,defaults,kwdefaults=self._function
        _need(fn.__code__ is code and fn.__defaults__==defaults and fn.__kwdefaults__==kwdefaults
              and all(cell.cell_contents is value for cell,value in self._cells),
              'Refinement observation callable/closure changed')
        _need(self._directory.resolve()==self._resolved and self._directory.is_dir()
              and len(self._seen)<=4096 and set(self._known)<=self._seen,
              'Refinement observation history/directory changed')
        for identity in self._seen-set(self._known):
            _need(type(identity) is tuple and len(identity)==2 and type(identity[0]) is int and identity[0]>0
                  and type(identity[1]) is str and len(identity[1])==64
                  and all(c in '0123456789abcdef' for c in identity[1]), 'Invalid observation identity')
            path=self._resolved/(str(identity[0])+'-'+identity[1]+'.json')
            _need(path.stat().st_size<=policy.MAX_BYTES, 'Observation record exceeds byte bound')
            raw=path.read_bytes();row=json.loads(raw)
            _need(type(row) is dict and set(row)=={'pid','parent_pid','parameter_sha256','parameters'}
                  and type(row['pid']) is int and row['pid']==identity[0] and type(row['parent_pid']) is int and row['parent_pid']>=0
                  and row['parameter_sha256']==identity[1], 'Observation record identity differs')
            parameters=row['parameters']
            _need(type(parameters) is dict and set(parameters)=={'site_count','proxies'}
                  and type(parameters['proxies']) is list and len(parameters['proxies'])<=policy.MAX_ITEMS,
                  'Invalid observed plane parameters')
            reconstructed=kernel_owner.parallelity_parameters([SimpleNamespace(**p) for p in parameters['proxies']],
                site_count=parameters['site_count'])
            _need(reconstructed==parameters['proxies'] and _digest(parameters)==identity[1],
                  'Observation parameters/digest differ')
            self._known[identity]=(path,hashlib.sha256(raw).hexdigest())
        if full:_check_files(tuple(self._known.values()))


def _check_files(pins):
    """Recheck qualified bytes at lifetime boundaries, without relying on mtimes."""
    for path, expected in pins:
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
        _need(digest.hexdigest()==expected, 'Counted qualified file changed: '+path.name)


def _profile_pins():
    return tuple((Path(__file__).parent/'data'/name,digest) for name,digest in _PROFILE_SHA256.items())


@lru_cache(maxsize=1)
def _native_api():
    profiles=_profile_pins(); _check_files(profiles)
    modules={}; native_files=[]
    for path,_ in profiles:
        profile=json.loads(path.read_text())
        qualified=policy._qualify_modules(profile); modules.update(qualified)
        native_files.extend((Path(module.__file__),profile['modules'][name]['sha256'])
                            for name,module in qualified.items())
    types = policy._native_types()
    from mmtbx.model import manager as Model
    from mmtbx.restraints import manager as Restraints
    from scitbx.restraints import energies as OuterEnergy
    from cctbx import geometry_restraints as gr, xray
    import cctbx_geometry_restraints_ext as ext
    geometry_module=importlib.import_module('cctbx.geometry_restraints.manager')
    energy_module=importlib.import_module('cctbx.geometry_restraints.energies')
    from cctbx.array_family import flex
    methods = [(geometry_module,types['manager'].energies_sites),
               (geometry_module,types['manager'].pair_proxies),
               (energy_module,gr.energies.energies.__init__),
               (modules['mmtbx.restraints'],Restraints.energies_sites),
               (modules['scitbx.restraints'],OuterEnergy.__init__),
               (modules['scitbx.restraints'],OuterEnergy.__iadd__),
               (modules['scitbx.restraints'],OuterEnergy.finalize_target_and_gradients),
               (modules['mmtbx.model.model'],Model.restraints_manager_energies_sites)]
    native_codes=tuple(_function(module,fn,compile(Path(module.__file__).read_bytes(),str(module.__file__),'exec',dont_inherit=True))
                       for module,fn in methods)
    return dict(native_codes=native_codes,native_files=tuple(native_files),profiles=profiles,types=types,Model=Model,Restraints=Restraints,OuterEnergy=OuterEnergy,
        Geometry=types['manager'],GeometryEnergy=gr.energies.energies,gr=gr,flex=flex,ext=ext,Xray=xray.structure,
        pair_proxies=types['manager'].pair_proxies,
        outer=Restraints.energies_sites,inner=types['manager'].energies_sites,
        model_entry=Model.restraints_manager_energies_sites,geometry_init=gr.energies.energies.__init__,
        outer_init=OuterEnergy.__init__,add=OuterEnergy.__iadd__,finalize=OuterEnergy.finalize_target_and_gradients)


def _points(values, count):
    rows = [list(p) for p in values]
    _need(len(rows) == count and all(len(p)==3 and all(type(v) in (float,int) and math.isfinite(v) for v in p) for p in rows),
          'Incomplete finite counted coordinates/gradients')
    return rows


class CountedContributionOwner:
    """One model, fresh trusted factory, instance adapters and explicit lifetime.

    Factory arguments are only the existing frozen packet/model/provider data;
    current native inventory, context and correction are supplied by this owner.
    The existing corrected parallelity kernel must already be installed by its
    outer owner. No caller evaluator, callback, buffer, AFITT or Cartesian NCS.
    A successful direct call is not ordinary-refinement or scientific acceptance.
    Single-owner process access is required; observations are not a thread lock.
    """
    def __init__(self, model, *, factory_module, factory_sources, helper_sources,
                 factory_arguments, frozen_policy):
        self._api = _native_api(); api=self._api
        self._native_files()
        self._model=model; self._manager=model.restraints_manager; self._geo=self._manager.geometry
        _need(type(model) is api['Model'] and type(self._manager) is api['Restraints']
              and type(self._geo) is api['Geometry'], 'Unsupported counted native owners')
        _need(factory_module.__name__.rsplit('.',1)[-1]=='topostitch_native_recipe', 'Require the fixed pair contribution factory module')
        package=factory_module.__package__
        names=tuple(factory_module.CONTRIBUTION_SOURCE_MODULES)+('topostitch_native_coverage',)
        _need(len(names)==len(set(names)), 'Duplicate contribution helper names')
        modules={name:importlib.import_module(package+'.'+name) for name in names}
        _need(modules['topostitch_native_recipe'] is factory_module, 'Foreign factory module')
        self._factory_sources=_Sources(modules,factory_sources)
        self._kernel_binding=api['gr'].parallelity_residual_sum
        wrapped=type(self._kernel_binding) is FunctionType
        _need(wrapped or type(self._kernel_binding) is kernel_owner.ParallelityKernel,
              'Require the existing owned parallelity correction')
        helper_modules={m.__name__.rsplit('.',1)[-1]:m for m in (policy,correction,kernel_owner,state_owner,gradient_owner)}
        if wrapped:helper_modules['cif_refinement_runtime']=importlib.import_module(__package__+'.cif_refinement_runtime')
        self._helper_sources=_Sources(helper_modules,helper_sources)
        self._observer=modules['topostitch_native_coverage']; self._factory=factory_module
        self._baseline=_detached(frozen_policy)
        options=dict(flags=api['types']['flags'](default=True),normalization=False,compute_gradients=False)
        observed=policy.require_live_nonbonded_policy(self._geo,self._baseline,**options)
        self._fixed={k:v for k,v in observed['policy'].items() if k!='invocation'}
        self._normalization=policy._boolean(self._manager.normalization)
        self._context=_detached(factory_arguments['provider_selection']['frozen']['context'])
        _need(self._context['native_exclusion_policy_sha256']==observed['policy_sha256']
              and self._context['crystal_sha256']==_digest(self._fixed['symmetry']), 'Counted context differs from frozen native policy')
        self._kernel_observation=_ObservedKernel(self._kernel_binding) if wrapped else None
        self._kernel=self._kernel_observation.kernel if wrapped else self._kernel_binding
        self._kernel_api=dict(vars(self._kernel._api)); self._kernel_flex=self._kernel._flex
        _need(self._kernel_flex is api['flex'] and self._kernel_api == {name:getattr(api['ext'],name)
            for name in ('parallelity','parallelity_proxy','parallelity_residual_sum')}
            and kernel_owner.correct_parallelity_gradient is correction.correct_parallelity_gradient,
            'Existing correction lacks its qualified native backing')
        self._native_bindings=[(api['Restraints'],'energies_sites',api['outer']),
            (api['Geometry'],'energies_sites',api['inner']),(api['Geometry'],'pair_proxies',api['pair_proxies']),(api['Model'],'restraints_manager_energies_sites',api['model_entry']),
            (api['OuterEnergy'],'__init__',api['outer_init']),(api['OuterEnergy'],'__iadd__',api['add']),
            (api['OuterEnergy'],'finalize_target_and_gradients',api['finalize']),
            (api['GeometryEnergy'],'__init__',api['geometry_init'])]
        self._native_codes=api['native_codes']
        self._state_identity=None; self._origins=None; self._entered=False; self._closed=False; self._poisoned=False; self._call=None
        self._successful=0; self._last=None; self._outer_adapter=self._outer; self._inner_adapter=self._inner
        self._bindings(idle=True)
        state=self._state(); self._state_identity=state['identity']
        terms=self._terms(state['sites']); self._bonded_signature=self._bonded(state['sites'])
        allowed={'packet','model_bytes','expected_recipe_sha256','expected_binding_sha256',
                 'provider_selection','expected_provider_selection_sha256'}
        _need(type(factory_arguments) is dict and set(factory_arguments)==allowed, 'Unsupported contribution factory arguments')
        self._contribution=factory_module.NativePairContribution(**factory_arguments,native_terms=terms,
            current_context=self._context,correction=correction)
        self._report=self._contribution.binding_report(); self._report_digest=_digest(self._report)
        _need(self._report['count_policy']==COUNT_POLICY and type(self._report['supported_count']) is int
              and 0<=self._report['supported_count']<=policy.MAX_ITEMS, 'Unsupported counted contribution semantics')
        self._count=self._report['atom_count']; _need(self._count==len(state['sites']), 'Contribution atom count differs')
        self._identities=_detached(factory_arguments['packet']['atom_identities'])
        self._recipe=self._contribution._recipe; self._recipe_flex=self._recipe._flex
        self._contribution_methods={n:getattr(self._contribution,n).__func__ for n in ('evaluate','revalidate','binding_report')}
        self._contribution.revalidate(terms,current_context=self._context)
        _need(self._state()==state, 'Model changed during contribution admission')
        self._bindings(idle=True)

    def _native_files(self):
        # Large native binaries are checked at admission/entry/exit, not on every
        # minimizer call. Small profiles and loaded bindings are checked each call.
        _check_files(self._api['profiles']); _check_files(self._api['native_files'])
        observed=getattr(self,'_kernel_observation',None)
        if observed is not None:observed.check(full=True)

    def _bindings(self, *, idle=False):
        _check_files(self._api['profiles'])
        api=self._api; m=self._manager; g=self._geo
        _need(self._model.restraints_manager is m and m.geometry is g, 'Counted manager ownership changed')
        _need(m.cartesian_ncs_manager is None and m.use_afitt is False and m.afitt_object is None
              and m.normalization is self._normalization, 'Unsupported/changed outer restraint mode')
        _need(not self._model.use_ias, 'IAS selections are outside counted ownership')
        _need(all(getattr(g,n) is None for n in ('reference_dihedral_manager','ncs_dihedral_manager',
            'den_manager','ramachandran_manager')) and not g.reference_coordinate_proxies,
            'Auxiliary force managers/reference coordinates are outside counted scope')
        _need(g.external_energy_function is None and 'pair_proxies' not in vars(g), 'Competing native callback/override')
        expected={} if idle else {'energies_sites':self._outer_adapter}
        _need(('energies_sites' not in vars(m)) if idle else vars(m).get('energies_sites') is expected['energies_sites'],
              'Outer counted adapter changed')
        _need(('energies_sites' not in vars(g)) if idle else vars(g).get('energies_sites') is self._inner_adapter,
              'Inner counted adapter changed')
        _need('restraints_manager_energies_sites' not in vars(self._model), 'Overridden model energy entry')
        _need(all(getattr(obj,name) is fn for obj,name,fn in self._native_bindings)
              and all(fn.__code__ is code and fn.__defaults__==defaults and fn.__kwdefaults__==kwdefaults
                      for fn,code,defaults,kwdefaults in self._native_codes), 'Native counted call chain changed')
        _need(api['gr'].parallelity_residual_sum is self._kernel_binding and self._kernel._flex is self._kernel_flex
              and vars(self._kernel._api)==self._kernel_api, 'Existing correction owner changed')
        self._factory_sources.check(); self._helper_sources.check()
        if self._kernel_observation is not None:self._kernel_observation.check()

    def _state(self):
        xrs=self._model.get_xray_structure(); api=self._api
        _need(type(xrs) is api['Xray'], 'Unsupported counted scattering owner')
        hierarchy=state_owner._hierarchy(self._model); scattering,projected=state_owner._scattering(xrs)
        labels=self._factory.native_atom_identities(self._model.get_hierarchy())
        encoded=[json.dumps(r,sort_keys=True,separators=(',',':')) for r in labels]
        _need(encoded==self._context['atom_labels'], 'Counted atom order/identity changed')
        stable=lambda rows:[{k:v for k,v in r.items() if k not in ('xyz','b','uij')} for r in rows]
        _need(state_owner._close(stable(hierarchy),stable(projected)), 'Counted hierarchy/scattering identity differs')
        crystal=self._geo.crystal_symmetry
        _need(list(xrs.unit_cell().parameters())==list(crystal.unit_cell().parameters())
              and xrs.space_group()==crystal.space_group(), 'Counted scattering crystal changed')
        identity=stable(projected)
        _need(self._state_identity is None or identity==self._state_identity, 'Counted fixed atom state changed')
        sites=_points(xrs.sites_cart(),len(labels)); fractional=_points(xrs.sites_frac(),len(labels))
        return dict(identity=identity,sites=sites,hierarchy=hierarchy,scattering=scattering,fractional=fractional)

    def _terms(self, sites):
        api=self._observer._native_api()
        terms,origins=self._observer._read_terms(self._geo,self._api['flex'].vec3_double(sites),self._context['atom_labels'],api)
        _need(self._origins is None or origins==self._origins, 'Native restraint origins changed')
        if self._origins is None:self._origins=list(origins)
        return terms

    def _bonded(self, sites):
        # Existing audit owns the broad static fingerprint. This narrow profile
        # additionally refuses torsion/image settings that it does not include.
        gr=self._api['gr']; count=len(sites); constant_alternates=[]
        for kind in ('dihedral','const_dihedral','chirality'):
            proxies=getattr(self._geo,kind+'_proxies')
            if proxies is None:continue
            native_kind='dihedral' if kind=='const_dihedral' else kind
            _need(type(proxies) is getattr(gr,'shared_'+native_kind+'_proxy') and len(proxies)<=policy.MAX_ITEMS,
                  'Unsupported counted bonded container')
            for proxy in proxies:
                _need(type(proxy) is getattr(gr,native_kind+'_proxy') and len(proxy.i_seqs)==4
                      and all(type(i) is int and 0<=i<count for i in proxy.i_seqs), 'Invalid counted bonded proxy')
                if native_kind=='dihedral':
                    _need(proxy.slack==0 and proxy.limit==-1 and proxy.top_out is False,
                          'Nondefault torsion force settings are outside counted scope')
                if kind=='const_dihedral':constant_alternates.append(None if proxy.alt_angle_ideals is None else list(proxy.alt_angle_ideals))
                images=getattr(proxy,'sym_ops',None)
                _need(images is None or all(op.is_unit_mx() for op in images),
                      'Symmetry-bearing torsion/chirality is outside counted scope')
        return dict(signature=gradient_owner.fixed_signature(self._geo,self._api['flex'].vec3_double(sites)),
                    constant_torsion_alternates=constant_alternates)

    def _check(self):
        self._bindings()
        _need(policy._Reader(policy._native_types()).fixed_inputs(self._geo)==self._fixed,
              'Fixed counted native policy changed')
        _need(all(getattr(self._contribution,n).__func__ is fn and n not in vars(self._contribution)
                  for n,fn in self._contribution_methods.items()), 'Contribution instance methods changed')
        _need(self._contribution._recipe is self._recipe and type(self._recipe) is self._factory.NativePairRecipe
              and self._recipe._gr is self._api['gr'] and self._recipe._correction is correction
              and self._recipe._flex is self._recipe_flex
              and all(n not in vars(self._recipe) for n in ('evaluate_terms','_evaluate_proxies','binding_report')),
              'Compiled evaluator ownership changed')
        _need(_digest(self._contribution.binding_report())==self._report_digest, 'Frozen contribution binding changed')
        state=self._state(); _need(self._bonded(state['sites'])==self._bonded_signature, 'Native bonded targets changed')
        self._contribution.revalidate(self._terms(state['sites']),current_context=self._context)
        _need(self._state()==state, 'Native state changed during counted observation')
        return state

    def __enter__(self):
        _need(not self._entered and not self._closed and not self._poisoned, 'Counted owner cannot be reused')
        try:
            self._native_files(); self._bindings(idle=True)
            self._manager.energies_sites=self._outer_adapter
            self._geo.energies_sites=self._inner_adapter
            self._entered=True
            self._check()
        except BaseException:
            self._poisoned=True
            if self._entered:self.__exit__(*sys.exc_info())
            raise
        return self

    def __exit__(self, kind, error, traceback):
        failures=[]; observed_error=None
        try:self._native_files(); self._check()
        except BaseException as exc:
            observed_error=exc; failures.append('lifetime check: '+str(exc))
        # Check failures must never strand our other installed binding or overwrite
        # a foreign replacement. Both owners are independently restored if ours.
        for obj,adapter in ((self._geo,self._inner_adapter),(self._manager,self._outer_adapter)):
            if vars(obj).get('energies_sites') is adapter:del obj.energies_sites
            else:failures.append('foreign adapter preserved')
        if not failures:
            try:self._bindings(idle=True)
            except BaseException as exc:observed_error=exc; failures.append('restoration check: '+str(exc))
        self._closed=True; self._poisoned=self._poisoned or kind is not None or bool(failures)
        if failures:raise ValueError('Counted cleanup failed: '+', '.join(failures)) from (error or observed_error)
        return False

    def _outer(self, *args, **kwargs):
        try:
            _need(self._entered and not self._closed and not self._poisoned and self._call is None,
                  'Inactive, failed or recursive counted call')
            bound=inspect.signature(self._api['outer']).bind(self._manager,*args,**kwargs); bound.apply_defaults(); call=bound.arguments
            _need(call['gradients'] is None and call['external_energy_function'] is None
                  and call['custom_nonbonded_function'] is None and call['force_restraints_model'] is False,
                  'Unsupported caller buffer or custom counted force')
            gradient=policy._boolean(call['compute_gradients']); disable=policy._boolean(call['disable_asu_cache'])
            _need(disable is False, 'Counted ASU-cache override is unsupported')
            default_flags=call['geometry_flags'] is None
            flags=self._api['types']['flags'](default=True) if default_flags else call['geometry_flags']
            _need(type(flags) is self._api['types']['flags'] and all(getattr(flags,n) is True for n in policy.FLAG_FIELDS),
                  'Counted contribution requires complete supported native flags')
            sites=call['sites_cart']; _need(type(sites) is self._api['flex'].vec3_double,'Unsupported counted sites buffer')
            state=self._check(); _need(_points(sites,self._count)==state['sites'], 'Incoming force sites differ from scattering owner')
            self._call=SimpleNamespace(sites=sites,gradient=gradient,state=state,inner=0,extension=0,buffer=None,
                energy=None,raw=None,native_count=None,complete_count=None)
            result=self._api['outer'](self._manager,*args,**kwargs); active=self._call
            _need(active.inner==active.extension==1 and type(result) is self._api['OuterEnergy']
                  and result.geometry is active.energy, 'Counted native call/result multiplicity differs')
            _need(result.number_of_restraints==active.complete_count and result.residual_sum==active.raw['target'],
                  'Counted native aggregation changed')
            factor=1./max(1,active.complete_count) if self._normalization else None
            _need(result.normalization_factor==factor and correction._close(result.target,active.raw['target']*(factor or 1.)),
                  'Counted native normalization differs')
            if gradient:
                _need(result.gradients.id()==active.buffer.id()==result.geometry.gradients.id(), 'Outer gradient storage differs')
                _need(correction._vector_agrees(list(result.gradients.as_double()),
                    [v*(factor or 1.) for row in active.raw['gradients'] for v in row]), 'Counted final gradients differ')
            else:_need(result.gradients is None,'Energy-only outer gradients present')
            _need(self._check()==state, 'Counted evaluation changed model state')
            self._successful+=1; self._last=dict(policy_id=POLICY_ID,native_count=active.native_count,
                supported_count=self._report['supported_count'],complete_count=active.complete_count,
                normalization=factor,compute_gradients=gradient,native_owned_buffer=gradient,
                geometry_flags={n:getattr(flags,n) for n in policy.FLAG_FIELDS},
                default_geometry_flags=default_flags,disable_asu_cache=disable,
                existing_usage_observation=self._kernel_observation is not None,
                inner_calls=active.inner,extension_calls=active.extension,force_sites_sha256=_digest(state['sites']),
                fixed_policy_sha256=_digest(self._fixed),contribution_binding_sha256=self._report_digest)
            return result
        except BaseException:
            self._poisoned=True; raise
        finally:self._call=None

    def _inner(self, *args, **kwargs):
        try:
            active=self._call; _need(active is not None and not self._poisoned and active.inner==0,'Unowned or repeated inner counted call')
            caller=sys._getframe(1)
            _need(caller.f_code is self._api['outer'].__code__ and caller.f_locals.get('self') is self._manager,
                  'Inner buffer did not originate in the trusted outer call')
            outer=caller.f_locals.get('result'); _need(type(outer) is self._api['OuterEnergy'],'Missing actual native outer allocation')
            bound=inspect.signature(self._api['inner']).bind(self._geo,*args,**kwargs); bound.apply_defaults(); values=bound.arguments
            buffer=values['gradients']
            _need(values['sites_cart'] is active.sites and values['compute_gradients'] is active.gradient
                  and values['normalization'] is False and values['external_energy_function'] is None
                  and values['custom_nonbonded_function'] is None and not values['extension_objects']
                  and values['site_labels'] is None, 'Changed native inner invocation')
            if active.gradient:
                _need(type(buffer) is self._api['flex'].vec3_double and buffer.id()==outer.gradients.id()
                      and buffer.id()!=active.sites.id() and len(buffer)==self._count
                      and all(v==0. for v in buffer.as_double()), 'Foreign, aliased or preseeded inner buffer')
            else:_need(buffer is None and outer.gradients is None,'Energy-only inner buffer present')
            active.inner=1; active.buffer=buffer
            values.pop('self'); values['extension_objects']=[self]
            result=self._api['inner'](self._geo,**values)
            _need(active.extension==1 and result is active.energy, 'Counted extension missing or result replaced')
            active.raw=dict(target=result.target,gradients=_points(result.gradients,self._count) if active.gradient else None)
            return result
        except BaseException:self._poisoned=True; raise

    def energies_add(self, *, energies_obj):
        try:
            active=self._call; caller=sys._getframe(1)
            _need(active is not None and not self._poisoned and active.inner==1 and active.extension==0,
                  'Unowned or repeated counted extension')
            _need(caller.f_code is self._api['geometry_init'].__code__ and caller.f_locals.get('self') is energies_obj
                  and type(energies_obj) is self._api['GeometryEnergy'], 'Foreign counted energy object')
            _need(energies_obj.sites_cart is active.sites and energies_obj.compute_gradients is active.gradient
                  and energies_obj.normalization is False and energies_obj.gradients is active.buffer
                  and energies_obj.extension_objects==[self], 'Counted extension context changed')
            before=_points(active.sites,self._count); count=policy._integer(energies_obj.number_of_restraints,minimum=0)
            value=self._contribution.evaluate(before,atom_identities=self._identities,compute_gradients=active.gradient)
            _need(value['supported_count']==self._report['supported_count'] and value['count_policy']==COUNT_POLICY
                  and value['provider_selection_sha256']==self._report['provider_selection_sha256'], 'Contribution count/binding changed')
            target=policy._number(value['target']); gradients=value['gradients']
            _need(_points(active.sites,self._count)==before,'Contribution changed native sites')
            if active.gradient:
                extra=_points(gradients,self._count); old=_points(active.buffer,self._count)
                for i,(a,b) in enumerate(zip(old,extra)):active.buffer[i]=tuple(math.fsum((x,y)) for x,y in zip(a,b))
            else:_need(gradients is None,'Energy-only contribution gradients present')
            energies_obj.residual_sum=math.fsum((policy._number(energies_obj.residual_sum),target))
            energies_obj.number_of_restraints=count+value['supported_count']
            active.native_count=count; active.complete_count=energies_obj.number_of_restraints
            active.extension=1; active.energy=energies_obj
        except BaseException:self._poisoned=True; raise

    def statistics(self):
        return _detached(dict(policy_id=POLICY_ID,successful_calls=self._successful,poisoned=self._poisoned,
            closed=self._closed,last=self._last,runtime_authority=False,scientific_acceptance=False))
