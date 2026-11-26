"""Canonical sugar scope admission; native scalar arithmetic stays Cedar-owned."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.helpers import pdb_record
from nasolve.topostitch_recipe import model_atom_rows


def fixture(reverse=False):
    sugar=("O5'","C5'","C4'","O4'","C3'","O3'","C2'","C1'")
    names=[(1,'DC',n) for n in ('P','OP1','OP2',*sugar,'N1','C2','C6')]
    names += [(7,'DA',n) for n in ('P','OP1','OP2',*sugar,'N9','C8','C4')]
    names += [(2,'DA',n) for n in ('P','OP1','OP2')]
    raw=''.join(pdb_record('ATOM',i+1,n,c,'B',r,x=i+.1,y=1,z=2,element=n[0]) for i,(r,c,n) in enumerate(names)).encode()
    source=model_atom_rows(raw);order=list(range(len(source)))
    if reverse:order.reverse()
    native_index={j:i for i,j in enumerate(order)}
    lookup={(f'B:{r}',n):i for i,(r,c,n) in enumerate(names)}
    atoms=[]
    for i,j in enumerate(order):
        r,c,n=names[j]
        atoms.append(dict(i_seq=i,atom_id=n,label=f'{r}:{n}',identity=dict(model_id='',chain_id='B',resseq=str(r),icode='',resname=c,altloc=''),element=n[0],xyz=[j+.1,1.,2.],occupancy=1.))
    def indices(site,ns):return [native_index[lookup[site,n]] for n in ns]
    bonds=[]
    def bond(left,right):
        ix=[native_index[lookup[k]] for k in (left,right)]
        bonds.append(dict(i_seqs=ix,atoms=[atoms[i]['label'] for i in ix],distance_ideal=1.5,weight=1.,symmetry_operation=None))
    ring=("C1'","C2'","C3'","C4'","O4'")
    for site,base in [('B:1','N1'),('B:7','N9')]:
        for a,b in zip(ring,ring[1:]+ring[:1]):bond((site,a),(site,b))
        for a,b in [("O5'","C5'"),("C5'","C4'"),("C3'","O3'"),("C1'",base),('P',"O5'")]:bond((site,a),(site,b))
        for n in ('OP1','OP2'):bond((site,'P'),(site,n))
    bond(('B:1',"O3'"),('B:2','P'))
    hands=[];planes=[]
    for site,base in [('B:1','N1'),('B:7','N9')]:
        for center,neighbors in [("C1'",["C2'","O4'",base]),("C3'",["C2'","C4'","O3'"]),("C4'",["C3'","O4'","C5'"])]:
            ix=indices(site,[center,*neighbors]);hands.append(dict(i_seqs=ix,both_signs=False,target=1.,weight=1.,observed=1.,status='MEASURED',sign_agreement=True))
        ix=indices(site,["C1'",base,'C2' if site=='B:1' else 'C8','C6' if site=='B:1' else 'C4'])
        planes.append(dict(i_seqs=ix,atoms=[atoms[i]['label'] for i in ix],weights=[1.]*4))
    native=dict(atom_count=len(atoms),atoms=atoms,geometry=dict(proxy_details=dict(bond_simple=bonds,planarity=planes,parallelity=[])),measurements=dict(chirality=hands))
    attachment=SimpleNamespace(_native_atoms=lambda n,raw: ([(f"{a['identity']['chain_id']}:{a['identity']['resseq']}",a['identity']['resname'],a['atom_id']) for a in n['atoms']],None))
    fixed=SimpleNamespace(review_fixed_coordinates=lambda n,points:dict(measurements=deepcopy(n['measurements'])))
    inspection=dict(phosphate=['B:1','DC','P'],o3=['B:7','DA',"O3'"])
    return raw,inspection,native,attachment,fixed,lookup


@pytest.mark.parametrize('reverse',[False,True])
def test_source_bound_scope_keeps_bases_and_outer_phosphates_held(reverse):
    from nasolve.topostitch_phosphate_scope import prepare_coupled_sugars
    raw,inspection,native,attachment,fixed,lookup=fixture(reverse)
    report=prepare_coupled_sugars(raw,inspection,native,native_owner=attachment,fixed_owner=fixed)
    assert len(report['movable_indices'])==19 and len(report['local_bonds'])==23
    assert len(report['sugar_hands'])==6 and len(report['c1_dependent_planes'])==2
    for key in [('B:1','N1'),('B:7','N9'),('B:7','P'),('B:2','P')]:
        assert lookup[key] not in report['movable_indices']
    assert report['sites']==[dict(site='B:1',component='DC'),dict(site='B:7',component='DA')]
    assert report['scientific_acceptance'] is False


@pytest.mark.parametrize('defect',['ring_bond','duplicate_bond','glycosidic','outer_bond','wrong_hand','both_signs','plane','zero_plane','occupancy','element','same_site'])
def test_incomplete_or_ambiguous_sugar_scope_refuses(defect):
    from nasolve.topostitch_phosphate_scope import prepare_coupled_sugars
    raw,inspection,native,attachment,fixed,lookup=fixture()
    bonds=native['geometry']['proxy_details']['bond_simple']
    if defect=='ring_bond':bonds.pop(0)
    elif defect=='duplicate_bond':bonds.append(deepcopy(bonds[0]))
    elif defect=='glycosidic':bonds[:]=[b for b in bonds if lookup['B:1','N1'] not in b['i_seqs']]
    elif defect=='outer_bond':bonds.pop()
    elif defect=='wrong_hand':native['measurements']['chirality'][0]['sign_agreement']=False
    elif defect=='both_signs':native['measurements']['chirality'][0]['both_signs']=True
    elif defect=='plane':native['geometry']['proxy_details']['planarity'].pop()
    elif defect=='zero_plane':native['geometry']['proxy_details']['planarity'][0]['weights'][0]=0
    elif defect in ('occupancy','element'):
        lines=raw.splitlines(keepends=True);line=lines[lookup['B:1',"C1'"]]
        lines[lookup['B:1',"C1'"]]=line[:54]+b'  0.50'+line[60:] if defect=='occupancy' else line[:76]+b' N'+line[78:]
        raw=b''.join(lines)
    elif defect=='same_site':inspection['o3']=['B:1','DC',"O3'"]
    with pytest.raises(ValueError):prepare_coupled_sugars(raw,inspection,native,native_owner=attachment,fixed_owner=fixed)


@pytest.mark.parametrize('defect',[None,'lost_proxy','changed_weight','extra_proxy','inverted','missing_hand','changed_target'])
def test_return_review_requires_same_native_definitions_and_six_source_hands(defect):
    from collections import Counter
    import json
    from nasolve.topostitch_phosphate_scope import prepare_coupled_sugars,review_coupled_geometry,_points
    raw,inspection,reference,attachment,fixed,lookup=fixture(reverse=True)
    scope=prepare_coupled_sugars(raw,inspection,reference,native_owner=attachment,fixed_owner=fixed)
    details=reference['geometry']['proxy_details']
    for family in ('angle','bond_asu','dihedral'):details[family]=[]
    initial=deepcopy(reference)
    for family,n in [('angle',4),('bond_asu',1),('dihedral',3)]:
        initial['geometry']['proxy_details'][family]=[dict(ordinal=i,weight=1.) for i in range(n)]
    returned=deepcopy(initial)
    if defect=='lost_proxy':returned['geometry']['proxy_details']['bond_simple'].pop()
    elif defect=='changed_weight':returned['geometry']['proxy_details']['bond_simple'][0]['weight']=2.
    elif defect=='extra_proxy':
        for view in (initial,returned):view['geometry']['proxy_details']['angle'].append(dict(ordinal=99,weight=1.))
    elif defect=='inverted':reference['measurements']['chirality'][0]['sign_agreement']=False
    elif defect=='missing_hand':reference['measurements']['chirality'].pop()
    elif defect=='changed_target':reference['measurements']['chirality'][0]['target']=2.
    # This exercises admission around the existing owner, not a substitute for
    # Cedar's separately qualified identity binding or scalar calculation.
    proxy=SimpleNamespace(_proxy_subset=lambda n,changed,family:Counter(json.dumps(r,sort_keys=True) for r in n['geometry']['proxy_details'][family]))
    source_points=_points(raw)
    def checked_measure(n,points):
        assert points==[source_points[i] for i in reversed(range(len(source_points)))]
        return dict(measurements=deepcopy(n['measurements']))
    fixed.review_fixed_coordinates=checked_measure
    if defect:
        with pytest.raises(ValueError):review_coupled_geometry(scope,reference,initial,returned,source_points,fixed_owner=fixed,proxy_owner=proxy)
    else:
        result=review_coupled_geometry(scope,reference,initial,returned,source_points,fixed_owner=fixed,proxy_owner=proxy)
        assert result['proxy_counts']['angle']['added']==4
        assert len(result['sugar_hands'])==6 and result['packing_acceptance']=='UNASSESSED'
        assert result['scientific_acceptance'] is False


@pytest.mark.parametrize('drift',[False,True])
@pytest.mark.parametrize('phase',['preflight','fit'])
def test_native_observer_uses_actual_interpretation_and_restores_hooks(tmp_path,monkeypatch,drift,phase):
    import json,sys
    from types import ModuleType
    from nasolve.topostitch_phosphate_scope import observe_coupled_native
    hierarchy=object();processed=SimpleNamespace(all_chain_proxies=SimpleNamespace(pdb_hierarchy=hierarchy))
    class Model:
        _processed_pdb_file=processed
        def get_hierarchy(self):return hierarchy
        def unset_processed_pdb_file(self):self._processed_pdb_file=None
    class Driver:
        def write_before_run_outputs(self):
            (tmp_path/('actual_final.geo' if phase=='fit' else 'actual.geo')).write_text('native geometry')
    original_unset=Model.unset_processed_pdb_file;original_write=Driver.write_before_run_outputs
    for name in ('mmtbx','mmtbx.model','phenix','phenix.refinement','phenix.refinement.driver'):
        monkeypatch.setitem(sys.modules,name,ModuleType(name))
    sys.modules['mmtbx.model'].manager=Model;sys.modules['phenix.refinement.driver'].refine=Driver
    monkeypatch.chdir(tmp_path)
    current={'weight':1.};seen=[];saved={}
    def collect(model,*,processed):
        seen.append(processed)
        return dict(native_view=dict(geometry=dict(proxy_details=deepcopy(current))))
    model=Model();driver=Driver();driver.model=model
    driver.ofm=SimpleNamespace(get_file_name=lambda ext:str(tmp_path/('actual'+ext)))
    if phase=='fit':
        (tmp_path/'preflight').mkdir()
        (tmp_path/'preflight/coupled-initial.json').write_text(json.dumps(dict(native_view=dict(geometry=dict(proxy_details=deepcopy(current))))))
    def execute():
        with observe_coupled_native(collect,phase=phase,root=tmp_path,save=lambda p,v:saved.update({str(p):v}),read=json.loads) as finish:
            model.unset_processed_pdb_file()
            driver.write_before_run_outputs()
            if drift:current['weight']=2.
            result=finish(driver)
            assert result['anchor']=='phase'
            assert result['path']==('actual_final.geo' if phase=='fit' else 'actual.geo')
    if drift:
        with pytest.raises(ValueError,match='definitions changed'):execute()
    else:
        execute()
        assert 'coupled-returned.json' in saved
    assert seen==[processed,processed]
    assert Model.unset_processed_pdb_file is original_unset
    assert Driver.write_before_run_outputs is original_write
