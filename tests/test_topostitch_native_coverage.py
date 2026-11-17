"""Native inventory boundary tests; actual C++ qualification is recorded separately."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from nasolve.topostitch_recipe import recipe_digest


def fixture(monkeypatch):
    from nasolve import topostitch_native_coverage as module
    class Proxy:
        def __init__(self,**values):self.__dict__.update(values)
    class Model:pass
    class Operation:
        def __init__(self,text='x,y,z'):self.text=text
        def as_xyz(self):return self.text
        def mod_positive(self):return self
        def r(self):return NS(num=lambda:[1,0,0,0,1,0,0,0,1],den=lambda:1)
        def t(self):return NS(num=lambda:[24 if self.text=='x+1,y,z' else 0,0,0],den=lambda:24)
        def __eq__(self,other):return self.text==other.text
    identities=[dict(chain='A',residue_number=1,insertion_code='',residue_code='DA',atom_name=str(i),altloc='') for i in range(6)]
    labels=[json.dumps(v,sort_keys=True,separators=(',',':')) for v in identities]
    points=[(float(i),0.,0.) for i in range(6)]
    bond=Proxy(i_seqs=[0,3],rt_mx_ji=None,distance_ideal=2.8,weight=25.,slack=0.,limit=-1.,top_out=False,origin_id=4)
    angle=Proxy(i_seqs=[0,1,3],angle_ideal=116.,weight=25.,slack=0.,sym_ops=None,origin_id=0)
    plane=Proxy(i_seqs=list(range(6)),weights=[25.]*6,sym_ops=None,origin_id=0)
    parallel=Proxy(i_seqs=[0,1,2],j_seqs=[3,4,5],weight=25.,target_angle_deg=0.,slack=0.,limit=1.,top_out=False,sym_ops=None,origin_id=0)
    bonds=NS(simple=[bond],asu=[],asu_mappings=lambda:None)
    crystal=NS(unit_cell=lambda:NS(parameters=lambda:[10.,10.,10.,90.,90.,90.]),space_group=lambda:[Operation()])
    geo=NS(pair_proxies=lambda **kwargs:NS(bond_proxies=bonds),angle_proxies=[angle],planarity_proxies=[plane],parallelity_proxies=[parallel],crystal_symmetry=crystal)
    model=Model();model.restraints_manager=NS(geometry=geo);model.get_sites_cart=lambda:points;model.get_hierarchy=lambda:identities
    policy=dict(symmetry=dict(cell=[10.,10.,10.,90.,90.,90.],site_indices=[0]*6,site_table=[dict(matrices=[{}],multiplicity=1)]))
    baseline=dict(policy=policy,policy_sha256=recipe_digest(policy))
    calls=[]
    def require(g,expected,**options):
        calls.append('require');assert g is geo
        if expected!=baseline:raise ValueError('Changed policy')
        return deepcopy(baseline)
    owner=NS(__file__=__file__,require_live_nonbonded_policy=require)
    context=dict(source_model_sha256='a'*64,recipe_sha256='b'*64,atom_labels=labels,crystal_sha256=recipe_digest(policy['symmetry']),native_exclusion_policy_sha256=baseline['policy_sha256'])
    monkeypatch.setattr(module,'_native_api',lambda:dict(Model=Model,gr=NS(bond_simple_proxy=Proxy,bond_asu_proxy=Proxy,angle_proxy=Proxy,planarity_proxy=Proxy,parallelity_proxy=Proxy),Operation=Operation,flags=lambda **kw:kw,identities=lambda v:v))
    kwargs=dict(frozen_context=context,frozen_policy=deepcopy(baseline),policy_owner=owner,expected_policy_owner_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    return module,model,geo,kwargs,calls


def test_native_observer_binds_complete_terms_context_and_coordinates(monkeypatch):
    module,model,geo,kwargs,calls=fixture(monkeypatch)
    before=deepcopy(kwargs['frozen_context']);out=module.observe_native_pair_terms(model,**kwargs)
    assert [v['kind'] for v in out['terms']]==['bond','angle','planarity','parallelity']
    assert out['terms'][0]['term_id']=='bond_simple:0'
    assert out['terms'][0]['parameters']['limit']==-1.
    assert out['origin_ids']==[4,0,0,0]
    assert out['context']==before and kwargs['frozen_context']==before
    assert out['points_sha256']==recipe_digest(model.get_sites_cart())
    assert calls==['require','require']
    assert not out['runtime_authority'] and not out['scientific_acceptance']


@pytest.mark.parametrize('drift',['labels','policy','owner','special_position','count','nonfinite','proxy_type','proxy_index','images','group','mid_read'])
def test_native_observer_refuses_context_or_inventory_drift(monkeypatch,drift):
    module,model,geo,kwargs,calls=fixture(monkeypatch)
    if drift=='labels':kwargs['frozen_context']['atom_labels'].reverse()
    elif drift=='policy':kwargs['frozen_policy']['policy_sha256']='c'*64
    elif drift=='owner':kwargs['expected_policy_owner_sha256']='d'*64
    elif drift=='special_position':
        # Isolate general-position check, retaining matched policy fingerprint.
        kwargs['frozen_policy']['policy']['symmetry']['site_table'][0]['matrices']=[{},{}]
        kwargs['policy_owner'].require_live_nonbonded_policy=lambda *a,**k:deepcopy(kwargs['frozen_policy'])
        kwargs['frozen_context']['crystal_sha256']=recipe_digest(kwargs['frozen_policy']['policy']['symmetry'])
        kwargs['frozen_policy']['policy_sha256']=recipe_digest(kwargs['frozen_policy']['policy'])
        kwargs['frozen_context']['native_exclusion_policy_sha256']=kwargs['frozen_policy']['policy_sha256']
    elif drift=='count':model.get_sites_cart=lambda:[(0.,0.,0.)]
    elif drift=='nonfinite':model.get_sites_cart=lambda:[(float('nan'),0.,0.)]*6
    elif drift=='proxy_type':geo.angle_proxies=[NS(**vars(geo.angle_proxies[0]))]
    elif drift=='proxy_index':geo.angle_proxies[0].i_seqs=[0,1,99]
    elif drift=='images':geo.angle_proxies[0].sym_ops=['invalid']
    elif drift=='group':geo.crystal_symmetry.space_group=lambda:[]
    else:
        original=geo.pair_proxies;counter=[]
        def changed(**kw):
            counter.append(1)
            if len(counter)>1:geo.angle_proxies[0].angle_ideal=117.
            return original(**kw)
        geo.pair_proxies=changed
    with pytest.raises(ValueError):module.observe_native_pair_terms(model,**kwargs)


def test_native_membership_uses_exact_rationals_and_retains_lattice_translation(monkeypatch):
    module,model,geo,kwargs,calls=fixture(monkeypatch)
    operation=module._native_api()['Operation']
    class Group(list):
        def __contains__(self,value):raise RuntimeError('Native denominator-sensitive membership must not be called')
    geo.crystal_symmetry.space_group=lambda:Group([operation()])
    geo.pair_proxies().bond_proxies.simple[0].rt_mx_ji=operation('x+1,y,z')
    result=module.observe_native_pair_terms(model,**kwargs)
    assert result['terms'][0]['atoms'][1]['translation']==['1','0','0']


def dual_fixture(monkeypatch):
    module, model, geo, kwargs, calls = fixture(monkeypatch)
    class Xray:
        def __init__(self):
            self.frac = [(p[0]/10., 0., 0.) for p in model.get_sites_cart()]
            self.cart = list(model.get_sites_cart())
        def sites_frac(self): return self.frac
        def sites_cart(self): return self.cart
        def unit_cell(self): return geo.crystal_symmetry.unit_cell()
        def space_group(self): return geo.crystal_symmetry.space_group()
    xrs = Xray(); model.get_xray_structure = lambda: xrs
    original_api = module._native_api()
    monkeypatch.setattr(module, '_native_api', lambda: dict(original_api, XrayStructure=Xray))
    def hierarchy(m):
        return [dict(label=str(i), xyz=list(p), occupancy=1., element='C', charge='',
                     fp=0., fdp=0., b=10., uij=None) for i,p in enumerate(m.get_sites_cart())]
    def scattering(x):
        rows = hierarchy(model)
        for r,p in zip(rows,x.cart): r['xyz']=list(p)
        return dict(cell=list(x.unit_cell().parameters()), space_group='P 1', atoms=deepcopy(rows)), rows
    def close(a,b):
        if isinstance(a,dict):return a.keys()==b.keys() and all(close(a[k],b[k]) for k in a)
        if isinstance(a,(list,tuple)):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
        if type(a) in (float,int):return abs(a-b)<=1e-8
        return a==b
    owner=NS(__file__=__file__, POLICY_ID='native-refinement-output-state-v1',
             _hierarchy=hierarchy,_scattering=scattering,_close=close)
    kwargs.update(state_owner=owner,expected_state_owner_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    return module,model,geo,kwargs,calls,xrs


def test_dual_state_observation_retains_legacy_and_binds_both_representations(monkeypatch):
    module,model,geo,kwargs,calls,xrs=dual_fixture(monkeypatch)
    legacy_kwargs={k:v for k,v in kwargs.items() if k not in ('state_owner','expected_state_owner_sha256')}
    before=module.observe_native_pair_terms(model,**legacy_kwargs)
    actual=module.observe_native_pair_terms(model,**kwargs)
    assert actual['policy_id']=='topostitch-native-pair-observation-v2'
    assert {k:v for k,v in actual.items() if k not in ('policy_id','native_state')}=={k:v for k,v in before.items() if k!='policy_id'}
    state=actual['native_state']
    assert state['fractional_sites_sha256']==recipe_digest(xrs.frac)
    assert state['force_sites_sha256']==recipe_digest(xrs.cart)
    assert state['hierarchy_sha256']==recipe_digest(kwargs['state_owner']._hierarchy(model))
    assert state['scattering_sha256']==recipe_digest(kwargs['state_owner']._scattering(xrs)[0])
    # The hierarchy-only legacy fingerprint misses fractional/force round trips.
    xrs.frac[1]=(xrs.frac[1][0]+1e-16,0.,0.)
    xrs.cart[1]=(xrs.cart[1][0]+1e-15,0.,0.)
    changed=module.observe_native_pair_terms(model,**kwargs)
    assert changed['points_sha256']==actual['points_sha256']
    assert changed['native_state']['fractional_sites_sha256']!=state['fractional_sites_sha256']
    assert changed['native_state']['force_sites_sha256']!=state['force_sites_sha256']
    assert module.observe_native_pair_terms(model,**legacy_kwargs)==before


@pytest.mark.parametrize('drift',['owner_missing','digest_missing','owner_hash','owner_policy',
    'wrong_xray','fractional_count','fractional_nan','cartesian_mismatch','label_order',
    'scatterer_count','cell','group','mid_read_fractional','mid_read_owner','mid_read_xray'])
def test_dual_state_observation_refuses_incomplete_or_changed_state(monkeypatch,drift):
    module,model,geo,kwargs,calls,xrs=dual_fixture(monkeypatch)
    owner=kwargs['state_owner']
    if drift=='owner_missing':kwargs['state_owner']=None
    elif drift=='digest_missing':kwargs['expected_state_owner_sha256']=None
    elif drift=='owner_hash':kwargs['expected_state_owner_sha256']='d'*64
    elif drift=='owner_policy':owner.POLICY_ID='unknown'
    elif drift=='wrong_xray':model.get_xray_structure=lambda:NS()
    elif drift=='fractional_count':xrs.frac.pop()
    elif drift=='fractional_nan':xrs.frac[0]=(float('nan'),0.,0.)
    elif drift=='cartesian_mismatch':xrs.cart[0]=(.1,0.,0.)
    elif drift in ('label_order','scatterer_count'):
        original=owner._scattering
        def altered(x):
            state,projected=original(x)
            if drift=='label_order':projected.reverse()
            else:state['atoms'].pop()
            return state,projected
        owner._scattering=altered
    elif drift=='cell':xrs.unit_cell=lambda:NS(parameters=lambda:[11.,10.,10.,90.,90.,90.])
    elif drift=='group':xrs.space_group=lambda:[]
    else:
        original=geo.pair_proxies
        def changed(**options):
            if drift=='mid_read_fractional':xrs.frac[0]=(.01,0.,0.)
            elif drift=='mid_read_owner':kwargs['expected_state_owner_sha256']='e'*64;owner.__file__=__file__+'.missing'
            else:model.get_xray_structure=lambda:deepcopy(xrs)
            return original(**options)
        geo.pair_proxies=changed
    with pytest.raises(ValueError):module.observe_native_pair_terms(model,**kwargs)


def test_dual_state_observation_records_stale_adps_without_synchronizing(monkeypatch):
    module,model,geo,kwargs,calls,xrs=dual_fixture(monkeypatch)
    original=kwargs['state_owner']._scattering
    def stale(x):
        state,projected=original(x)
        for row in state['atoms']:row['b']=20.
        for row in projected:row['b']=20.
        return state,projected
    kwargs['state_owner']._scattering=stale
    actual=module.observe_native_pair_terms(model,**kwargs)
    assert actual['native_state']['hierarchy_sha256']==recipe_digest(kwargs['state_owner']._hierarchy(model))
    assert actual['native_state']['scattering_sha256']==recipe_digest(stale(xrs)[0])
    assert kwargs['state_owner']._hierarchy(model)[0]['b']==10.
    assert not actual['runtime_authority']
