from dataclasses import replace
from hashlib import sha256
import json,math,subprocess,sys
import pytest
from nasolve.helical_geometry import HelicalSite,DeclaredPair,PairedRegion,inspect_phosphate_spans
from nasolve.helical_twist import inspect_helical_region
from .helpers import pdb_record

pytest.importorskip("gemmi")

# Independent published canonical A/T ring coordinates; tests generate rigid frames.
RINGS={'DA':{'N1':(-.668,.532,0),'C2':(-1.912,1.023,0),'N3':(-2.320,2.290,0),'C4':(-1.267,3.124,0),'C5':(.071,2.771,0),'C6':(.369,1.398,0),'N7':(.877,3.902,0),'C8':(.024,4.897,0),'N9':(-1.291,4.498,0),"C1'":(-2.479,5.346,0),'P':(-5,6,0)},'DT':{'N1':(-1.284,4.500,0),'C2':(-1.462,3.135,0),'N3':(-.298,2.407,0),'C4':(.994,2.897,0),'C5':(1.106,4.338,0),'C6':(-.024,5.057,0),"C1'":(-2.481,5.354,0),'P':(-5,6,0)}}

def region():
 return PairedRegion('helix',tuple(DeclaredPair(f'p{i}',HelicalSite('A',i,'DA'),HelicalSite('B',4-i,'DT'),role='flank'if i in (1,3)else'core')for i in range(1,4)))

def model(angle=30,transform=lambda x:x,rise=3.4):
 lines=[]
 for i in range(1,4):
  theta=math.radians((i-1)*angle)
  for chain,num,code,hand in [('A',i,'DA',1),('B',4-i,'DT',-1)]:
   for name,xyz in RINGS[code].items():
    x,y,z=xyz;x=hand*x-5*hand;z=hand*z+(i-1)*rise
    point=transform((math.cos(theta)*x-math.sin(theta)*y,math.sin(theta)*x+math.cos(theta)*y,z))
    lines.append(pdb_record('ATOM',len(lines)+1,name,code,chain,num,x=point[0],y=point[1],z=point[2],element=name[0]))
 return ''.join(lines)

def inspect(tmp_path,text=None,declaration=None,**kw):
 path=tmp_path/'model.pdb';path.write_text(model()if text is None else text);pin=sha256(path.read_bytes()).hexdigest()
 return inspect_helical_region(path,declaration or region(),expected_model_sha256=pin,max_ring_fit_rmsd_angstrom=.15,**kw)

@pytest.mark.parametrize('angle',[0,30,-30,90,-90])
def test_signed_twist_from_whole_model(tmp_path,angle):
 r=inspect(tmp_path,model(angle));twist=r['simple_step_twist']
 assert [s['twist_deg']for s in twist['steps']]==pytest.approx([angle,angle],abs=.02)
 assert twist['coverage']=={'declared_steps':2,'measured_steps':2,'unavailable_steps':0}
 assert r['axis_radii']['status']=='NOT_MEASURED' and r['pairing_validated'] is False
 assert all(f['status']=='AVAILABLE'for f in twist['pair_frames'])
 assert all(b['fit_rmsd_angstrom']<.002 for f in twist['pair_frames']for b in f['base_frames'])
 assert json.loads(json.dumps(r,allow_nan=False))==r


def test_rigid_movement_and_mirror_have_correct_effects(tmp_path):
 a=inspect(tmp_path);b=inspect(tmp_path,model(transform=lambda p:(-p[1]+10,p[2]-3,-p[0]+4)))
 c=inspect(tmp_path,model(transform=lambda p:(-p[0],p[1],p[2])))
 av=[s['twist_deg']for s in a['simple_step_twist']['steps']]
 assert [s['twist_deg']for s in b['simple_step_twist']['steps']]==pytest.approx(av,abs=1e-7)
 assert [s['twist_deg']for s in c['simple_step_twist']['steps']]==pytest.approx([-x for x in av],abs=1e-7)
 assert [p['distance_angstrom']for p in a['pairs']]==[p['distance_angstrom']for p in c['pairs']]


def test_missing_phosphate_does_not_hide_twist(tmp_path):
 text=''.join(l for l in model().splitlines(keepends=True)if not(l[12:16].strip()=='P'and l[21:26]=='A   2'))
 r=inspect(tmp_path,text)
 assert r['pairs'][1]['distance_angstrom'] is None
 assert r['simple_step_twist']['coverage']['measured_steps']==2

@pytest.mark.parametrize('fault,reason',[('c1','MISSING_ATOM'),('ring','MISSING_ATOM'),('modified','UNSUPPORTED_COMPONENT'),('alt','ALTERNATE_CONFORMER_REQUIRED'),('occupancy','UNUSABLE_OCCUPANCY'),('fit','RING_FIT_EXCEEDS_LIMIT'),('collinear','DEGENERATE_RING_FIT')])
def test_unavailable_frames_leave_independent_measurements(tmp_path,fault,reason):
 lines=model().splitlines(keepends=True);decl=region()
 if fault in ('c1','ring'):
  name="C1'"if fault=='c1'else'N9';lines=[l for l in lines if not(l[12:16].strip()==name and l[21:26]=='A   1')]
 if fault=='modified':
  lines=[l[:17]+'PDU'+l[20:]if l[21:26]=='A   1'else l for l in lines]
  decl=replace(decl,pairs=(replace(decl.pairs[0],strand_i=replace(decl.pairs[0].strand_i,component='PDU')),*decl.pairs[1:]))
 if fault in ('alt','occupancy','fit'):
  for i,l in enumerate(lines):
   if l[21:26]=='A   1'and l[12:16].strip()=='N9':
    if fault=='alt':lines[i]=l[:16]+'A'+l[17:]
    if fault=='occupancy':lines[i]=l[:54]+'  0.00'+l[60:]
    if fault=='fit':lines[i]=l[:30]+'  20.000'+l[38:]
 if fault=='collinear':
  lines=[l[:30]+f'{i*.1:8.3f}{0:8.3f}{0:8.3f}'+l[54:]if l[21:26]=='A   1'and l[12:16].strip()not in ('P',"C1'")else l for i,l in enumerate(lines)]
 r=inspect(tmp_path,''.join(lines),decl)
 assert r['pairs'][0]['status']=='MEASURED'
 frame=r['simple_step_twist']['pair_frames'][0]
 assert frame['status']=='UNAVAILABLE' and frame['base_frames'][0]['reason']==reason
 first,second=r['simple_step_twist']['steps'];assert first['twist_deg']is None and second['status']=='MEASURED'


def test_declared_break_is_not_bridged(tmp_path):
 d=region();d=replace(d,pairs=(d.pairs[0],replace(d.pairs[1],break_before=True),d.pairs[2]))
 r=inspect(tmp_path,declaration=d);assert r['simple_step_twist']['steps'][0]['reason']=='DECLARED_BREAK'
 assert r['simple_step_twist']['steps'][1]['status']=='MEASURED'


def test_coincident_origins_and_wrap_are_unavailable(tmp_path):
 r=inspect(tmp_path,model(angle=0,rise=0));assert all(s['reason']=='COINCIDENT_PAIR_ORIGINS'for s in r['simple_step_twist']['steps'])
 r=inspect(tmp_path,model(angle=180));assert all(s['reason']=='AMBIGUOUS_TWIST_WRAP'for s in r['simple_step_twist']['steps'])


def test_empty_step_inventory_is_not_a_zero_twist(tmp_path):
 d=replace(region(),pairs=region().pairs[:1]);r=inspect(tmp_path,declaration=d)
 assert r['simple_step_twist']['steps']==[] and r['simple_step_twist']['coverage']['declared_steps']==0


def test_default_phosphate_report_unchanged_and_no_optional_import(tmp_path,monkeypatch):
 import builtins
 old=builtins.__import__
 def no_gemmi(name,*args,**kw):
  if name=='gemmi':raise ImportError('test no topology dependency')
  return old(name,*args,**kw)
 monkeypatch.setattr(builtins,'__import__',no_gemmi)
 p=tmp_path/'model.pdb';p.write_text(model());pin=sha256(p.read_bytes()).hexdigest()
 assert inspect_phosphate_spans(p,region(),expected_model_sha256=pin)['simple_step_twist']=={'status':'NOT_MEASURED'}
 with pytest.raises(RuntimeError,match='topology'):
  inspect_helical_region(p,region(),expected_model_sha256=pin,max_ring_fit_rmsd_angstrom=.15)

@pytest.mark.parametrize('limit',[0,-1,float('nan'),float('inf'),True,None])
def test_invalid_fit_policy_refuses(tmp_path,limit):
 with pytest.raises(ValueError,match='fit'):
  inspect_helical_region(tmp_path/'absent',region(),expected_model_sha256='0'*64,max_ring_fit_rmsd_angstrom=limit)


def test_relocation_and_installed_cli(tmp_path):
 from dataclasses import asdict
 old=tmp_path/'old';old.mkdir();p=old/'input.pdb';p.write_text(model());pin=sha256(p.read_bytes()).hexdigest();(old/'region.json').write_text(json.dumps(asdict(region())))
 expected=inspect_helical_region(p,region(),expected_model_sha256=pin,max_ring_fit_rmsd_angstrom=.15)
 new=tmp_path/'new';old.rename(new);assert not old.exists()
 actual=inspect_helical_region(new/'input.pdb',region(),expected_model_sha256=pin,max_ring_fit_rmsd_angstrom=.15);assert actual==expected
 cmd=[sys.executable,'-B','-m','nasolve.helical_geometry','--model',str(new/'input.pdb'),'--region',str(new/'region.json'),'--sha256',pin,'--simple-twist','--max-ring-fit-rmsd','.15']
 cp=subprocess.run(cmd,capture_output=True,text=True,check=True);assert json.loads(cp.stdout)==expected


def test_perpendicular_base_normals_remain_ambiguous(tmp_path):
 lines=[]
 for l in model().splitlines(keepends=True):
  if l[21:26]=='B   3':
   x,y,z=(float(l[a:b])for a,b in ((30,38),(38,46),(46,54)))
   l=l[:30]+f'{x:8.3f}{-z:8.3f}{y:8.3f}'+l[54:]
  lines.append(l)
 r=inspect(tmp_path,''.join(lines))
 assert r['simple_step_twist']['pair_frames'][0]['reason']=='AMBIGUOUS_PAIR_NORMAL'
 assert r['simple_step_twist']['steps'][1]['status']=='MEASURED'


def test_zero_c1_direction_does_not_make_an_axis(tmp_path):
 lines=model().splitlines(keepends=True);xyz=next(l[30:54]for l in lines if l[21:26]=='A   1'and l[12:16].strip()=="C1'")
 lines=[l[:30]+xyz+l[54:]if l[21:26]=='B   3'and l[12:16].strip()=="C1'"else l for l in lines]
 r=inspect(tmp_path,''.join(lines));assert r['simple_step_twist']['pair_frames'][0]['reason']=='DEGENERATE_C1_DIRECTION'
 assert r['pairs'][0]['status']=='MEASURED'


def test_step_direction_in_base_plane_remains_ambiguous(tmp_path):
 lines=[]
 for l in model(angle=0,rise=0).splitlines(keepends=True):
  if l[21:26]in ('A   2','B   2'):l=l[:30]+f'{float(l[30:38])+10:8.3f}'+l[38:]
  lines.append(l)
 r=inspect(tmp_path,''.join(lines));assert all(s['reason']=='AMBIGUOUS_STEP_DIRECTION'for s in r['simple_step_twist']['steps'])


def test_coordinate_drift_during_frame_fit_refuses(tmp_path,monkeypatch):
 import nasolve.helical_twist as module
 p=tmp_path/'model.pdb';p.write_text(model());pin=sha256(p.read_bytes()).hexdigest();original=module._base_frame
 def drift(*args):
  p.write_text(model()+'REMARK changed\n')
  return original(*args)
 monkeypatch.setattr(module,'_base_frame',drift)
 with pytest.raises(ValueError,match='changed during frame'):
  inspect_helical_region(p,region(),expected_model_sha256=pin,max_ring_fit_rmsd_angstrom=.15)
