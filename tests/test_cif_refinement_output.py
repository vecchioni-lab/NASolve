"""A stale hierarchy must never export pre-scaling displacement parameters."""
from copy import deepcopy
from types import SimpleNamespace as NS
import math
import pytest


class Atom:
    def __init__(self, label, b=61.0, aniso=False):
        self.label=label;self.xyz=(1.,2.,3.);self.occ=1.;self.b=b
        self.element='C';self.charge='';self.fp=0.;self.fdp=0.
        self.uij=(b/(8*math.pi**2),)*3+(0.,)*3 if aniso else (-1.,)*6
    def id_str(self):return self.label


class Scatterer:
    def __init__(self, atom):
        self.label=atom.label;self.scattering_type='C';self.occupancy=atom.occ
        self.fp=atom.fp;self.fdp=atom.fdp;self.u_iso=atom.b/(8*math.pi**2)
        self.u_star=atom.uij;self.aniso=atom.uij!=(-1.,)*6
        self.flags=NS(use_u_iso=lambda:not self.aniso,use_u_aniso=lambda:self.aniso)
    def element_and_charge_symbols(self):return ('C','')
    def u_iso_or_equiv(self, cell):return self.u_iso
    def u_cart_plus_u_iso(self, cell):return self.u_star


def model(aniso=False):
    atoms=[Atom('a',61.,aniso),Atom('b',71.,aniso)]
    current=[Scatterer(Atom('a',11.,aniso)),Scatterer(Atom('b',21.,aniso))]
    cell=NS(parameters=lambda:(20.,20.,20.,90.,90.,90.))
    xrs=NS(scatterers=lambda:current,sites_cart=lambda:[a.xyz for a in atoms],
           unit_cell=lambda:cell,space_group_info=lambda:'P 1')
    hierarchy=NS(atoms=lambda:atoms)
    geo=object()
    m=NS(get_xray_structure=lambda:xrs,get_hierarchy=lambda:hierarchy,
         restraints_manager=NS(geometry=geo))
    def sync(x):
        assert x is xrs
        for a,s in zip(atoms,current):
            a.b=s.u_iso_or_equiv(cell)*8*math.pi**2
            a.uij=s.u_cart_plus_u_iso(cell) if s.aniso else (-1.,)*6
    m.set_xray_structure=sync
    fc=[1.+2.j,3.+4.j]
    fm=NS(xray_structure=xrs,f_calc=lambda:NS(data=lambda:fc))
    result=NS(model=m,fmodels=NS(fmodel_xray=lambda:fm,fmodel_neutron=lambda:None))
    return result,atoms,current,fc


@pytest.mark.parametrize('aniso',[False,True])
def test_native_current_adps_reach_output_without_changing_refined_state(aniso):
    from nasolve.cif_refinement_output import synchronize_output
    result,atoms,current,fc=model(aniso);saved=deepcopy(fc)
    record=synchronize_output(result)
    assert [a.b for a in atoms]==pytest.approx([11.,21.])
    assert record['changed_adp_atoms']==2 and record['atom_count']==2
    assert record['status']=='SYNCHRONIZED' and fc==saved
    assert record['scattering_unchanged'] and record['geometry_owner_unchanged']
    if aniso:assert atoms[0].uij==current[0].u_star


def test_already_synchronized_output_is_idempotent():
    from nasolve.cif_refinement_output import synchronize_output
    result,*_=model();synchronize_output(result);record=synchronize_output(result)
    assert record['changed_adp_atoms']==0


@pytest.mark.parametrize('defect',['atom_order','coordinates','occupancy','element','charge','anomalous','nonfinite','neutron','fmodel'])
def test_unqualified_mismatch_refuses_before_synchronizing(defect):
    from nasolve.cif_refinement_output import synchronize_output
    result,atoms,current,fc=model();called=[]
    result.model.set_xray_structure=lambda x:called.append(x)
    if defect=='atom_order':atoms.reverse()
    elif defect=='coordinates':result.model.get_xray_structure().sites_cart=lambda:[(9.,2.,3.),(1.,2.,3.)]
    elif defect=='occupancy':atoms[0].occ=.5
    elif defect=='element':atoms[0].element='N'
    elif defect=='charge':atoms[0].charge='1+'
    elif defect=='anomalous':atoms[0].fp=1.
    elif defect=='nonfinite':current[0].u_iso=float('nan')
    elif defect=='neutron':result.fmodels.fmodel_neutron=lambda:object()
    else:result.fmodels.fmodel_xray().xray_structure=NS()
    with pytest.raises(ValueError):synchronize_output(result)
    assert not called


@pytest.mark.parametrize('defect',['no_sync','geometry','scattering','fcalc'])
def test_failed_sync_is_not_reported_as_success(defect):
    from nasolve.cif_refinement_output import synchronize_output
    result,atoms,current,fc=model();original=result.model.set_xray_structure
    def broken(x):
        if defect!='no_sync':original(x)
        if defect=='geometry':result.model.restraints_manager.geometry=object()
        if defect=='scattering':current[0].u_iso+=1
        if defect=='fcalc':fc[0]+=1
    result.model.set_xray_structure=broken
    with pytest.raises(ValueError):synchronize_output(result)


@pytest.mark.parametrize('fail',[False,True])
def test_writer_observes_current_adps_and_binding_is_restored(fail):
    from nasolve.cif_refinement_output import synchronized_outputs
    result,atoms,*_=model();events=[];written=[]
    class Driver:
        def write_after_run_outputs(self):
            written.append([a.b for a in atoms])
            if fail:raise RuntimeError('disk full')
            return 'written'
    original=Driver.write_after_run_outputs
    def observe(rows,restored):events.append((deepcopy(rows),restored))
    try:
        with synchronized_outputs(Driver,observe):
            assert Driver.write_after_run_outputs(result)=='written'
    except RuntimeError:
        assert fail
    assert Driver.write_after_run_outputs is original
    assert written[0]==pytest.approx([11.,21.])
    assert events[-1][1] is True
    assert events[-1][0][0]['write_completed'] is (not fail)


def test_hook_replacement_is_refused_and_original_restored():
    from nasolve.cif_refinement_output import synchronized_outputs
    class Driver:
        def write_after_run_outputs(self):pass
    original=Driver.write_after_run_outputs
    with pytest.raises(ValueError,match='binding'):
        with synchronized_outputs(Driver,lambda *args:None):
            Driver.write_after_run_outputs=lambda s:None
    assert Driver.write_after_run_outputs is original


@pytest.mark.parametrize('defect',['nan','inf','fraction','bool','negative','excess','unknown','unfinished','false_binding'])
def test_output_evidence_requires_complete_finite_counts_and_invariants(defect):
    from nasolve.cif_refinement_output import validate_output_observations
    from tests.test_cif_refinement_runtime import output_row
    row=output_row(2)
    if defect in ('nan','inf','fraction','bool','negative','excess'):
        row['changed_adp_atoms']={'nan':float('nan'),'inf':float('inf'),'fraction':1.5,'bool':True,'negative':-1,'excess':3}[defect]
    elif defect=='unknown':row['extra']='unknown'
    elif defect=='unfinished':row['write_completed']=False
    else:row['geometry_owner_unchanged']=1
    with pytest.raises(ValueError):validate_output_observations([row],dry_run=False,atom_count=2)


def test_no_output_is_allowed_during_zero_cycle_preflight():
    from nasolve.cif_refinement_output import validate_output_observations
    from tests.test_cif_refinement_runtime import output_row
    validate_output_observations([],dry_run=True,atom_count=2)
    with pytest.raises(ValueError):validate_output_observations([output_row(2)],dry_run=True,atom_count=2)


def test_optional_final_observer_surrounds_the_original_writer():
    from nasolve.cif_refinement_output import synchronized_outputs
    result,atoms,*_=model();events=[]
    class Driver:
        def write_after_run_outputs(self):
            events.append('written')
            return 'unchanged result'
    def final(refined,completed):
        assert refined is result and atoms[0].b==pytest.approx(11.)
        events.append(completed)
    with synchronized_outputs(Driver,lambda *args:None,observe_final=final):
        assert Driver.write_after_run_outputs(result)=='unchanged result'
    assert events==[False,'written',True]
