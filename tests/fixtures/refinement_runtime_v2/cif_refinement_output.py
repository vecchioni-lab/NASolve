"""Synchronize qualified native final exports with current refined ADPs.

The caller qualifies the native source and owns execution/publication. This
module neither edits saved models nor infers a B-factor correction from logs.
"""
from contextlib import contextmanager
import hashlib
import json
import math

POLICY_ID = 'native-refinement-output-state-v1'
_TOLERANCE = 1.e-8  # In-memory representation agreement, not a chemistry cutoff.


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),
                                    allow_nan=False).encode()).hexdigest()


def _close(a, b):
    if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        return len(a)==len(b) and all(_close(x,y) for x,y in zip(a,b))
    if isinstance(a,dict) and isinstance(b,dict):
        return a.keys()==b.keys() and all(_close(a[k],b[k]) for k in a)
    if type(a) in (float,int) and type(b) in (float,int):
        return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=_TOLERANCE
    return a==b


def _hierarchy(model):
    return [dict(label=a.id_str(),xyz=list(a.xyz),occupancy=float(a.occ),
                 element=a.element.strip(),charge=a.charge.strip(),
                 fp=float(a.fp),fdp=float(a.fdp),b=float(a.b),
                 uij=None if tuple(a.uij)==(-1.,)*6 else list(a.uij))
            for a in model.get_hierarchy().atoms()]


def _scattering(xrs):
    cell=xrs.unit_cell();scatterers=list(xrs.scatterers());sites=list(xrs.sites_cart())
    if not scatterers or len(scatterers)!=len(sites):
        raise ValueError('Incomplete native output atom state')
    projected=[];raw=[]
    for s,xyz in zip(scatterers,sites):
        element,charge=s.element_and_charge_symbols()
        projected.append(dict(label=s.label,xyz=list(xyz),occupancy=float(s.occupancy),
            element=element.strip(),charge=charge.strip(),fp=float(s.fp),fdp=float(s.fdp),
            b=float(s.u_iso_or_equiv(cell))*8*math.pi**2,
            uij=list(s.u_cart_plus_u_iso(cell)) if s.flags.use_u_aniso() else None))
        raw.append(dict(label=s.label,type=s.scattering_type,xyz=list(xyz),
            occupancy=float(s.occupancy),fp=float(s.fp),fdp=float(s.fdp),
            u_iso=float(s.u_iso),u_star=list(s.u_star),
            use_u_iso=s.flags.use_u_iso(),use_u_aniso=s.flags.use_u_aniso()))
    state=dict(cell=list(cell.parameters()),space_group=str(xrs.space_group_info()),atoms=raw)
    _digest(state);_digest(projected)  # Refuse nonfinite inputs before any mutation.
    return state,projected


def _fcalc(fmodel):
    return [[float(v.real),float(v.imag)] for v in fmodel.f_calc().data()]


def synchronize_output(refined):
    """Use the current refined scattering object; only stale ADPs may differ."""
    try:
        model=refined.model;fmodels=refined.fmodels
        if fmodels.fmodel_neutron() is not None:
            raise ValueError('Joint neutron output synchronization is not qualified')
        fmodel=fmodels.fmodel_xray();xrs=model.get_xray_structure()
        state,expected=_scattering(xrs);other,_=_scattering(fmodel.xray_structure)
        if state!=other:raise ValueError('Model and diffraction scattering states differ')
        before=_hierarchy(model);_digest(before)
        unchanged=lambda rows:[{k:v for k,v in r.items() if k not in ('b','uij')} for r in rows]
        if not _close(unchanged(before),unchanged(expected)):
            raise ValueError('Native output mismatch extends beyond ADPs')
        geometry=model.restraints_manager.geometry;fc=_fcalc(fmodel);_digest(fc)
        model.set_xray_structure(xrs)
        after=_hierarchy(model)
        if not _close(after,expected):raise ValueError('Native hierarchy ADPs were not synchronized')
        if (model.get_xray_structure() is not xrs or
                model.restraints_manager.geometry is not geometry or
                _scattering(xrs)[0]!=state or _scattering(fmodel.xray_structure)[0]!=state or
                _fcalc(fmodel)!=fc):
            raise ValueError('Output synchronization changed refined scattering or geometry')
        return dict(policy_id=POLICY_ID,status='SYNCHRONIZED',atom_count=len(expected),
            changed_adp_atoms=sum(not _close(a,b) for a,b in zip(before,expected)),
            scattering_sha256=_digest(state),hierarchy_before_sha256=_digest(before),
            hierarchy_after_sha256=_digest(after),fcalc_sha256=_digest(fc),
            scattering_unchanged=True,geometry_owner_unchanged=True,write_completed=False)
    except (AttributeError,TypeError,OverflowError) as exc:
        raise ValueError('Incomplete native output synchronization interface') from exc


@contextmanager
def synchronized_outputs(driver_class, observe):
    """Temporarily guard the final writer; always restore its original binding."""
    original=driver_class.write_after_run_outputs;events=[]
    def write(refined):
        if events:raise ValueError('Repeated native final output invocation')
        row=synchronize_output(refined);events.append(row);observe(events,False)
        result=original(refined)
        row['write_completed']=True;observe(events,False)
        return result
    driver_class.write_after_run_outputs=write
    try:
        yield
        if driver_class.write_after_run_outputs is not write:
            raise ValueError('Native final output binding changed')
    finally:
        driver_class.write_after_run_outputs=original
        observe(events,driver_class.write_after_run_outputs is original)


def validate_output_observations(rows, *, dry_run, atom_count):
    """Read compact observations without executing native code or repairing files."""
    if not isinstance(rows,list) or len(rows)!=(0 if dry_run else 1):
        raise ValueError('Missing or repeated native output synchronization')
    for row in rows:
        fields={'policy_id','status','atom_count','changed_adp_atoms','scattering_sha256',
                'hierarchy_before_sha256','hierarchy_after_sha256','fcalc_sha256',
                'scattering_unchanged','geometry_owner_unchanged','write_completed'}
        if (not isinstance(row,dict) or set(row)!=fields or row['policy_id']!=POLICY_ID
                or row['status']!='SYNCHRONIZED' or type(row['atom_count']) is not int
                or row['atom_count']!=atom_count or atom_count<=0
                or type(row['changed_adp_atoms']) is not int
                or not 0<=row['changed_adp_atoms']<=atom_count
                or any(row[k] is not True for k in ('scattering_unchanged','geometry_owner_unchanged','write_completed'))
                or any(not isinstance(row[k],str) or len(row[k])!=64 or
                       any(c not in '0123456789abcdef' for c in row[k])
                       for k in ('scattering_sha256','hierarchy_before_sha256','hierarchy_after_sha256','fcalc_sha256'))):
            raise ValueError('Invalid native output synchronization evidence')
