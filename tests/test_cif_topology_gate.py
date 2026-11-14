"""Explicit source topology and declared NAR soft terms, never origin-only trust."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest
from .test_cif_attachment_native import fixture, rebind


def base(tmp_path):
    manifest,receipt=fixture(tmp_path)
    native=json.loads(receipt.read_text())['native_validation']
    payload=(manifest.parent/'model.pdb').read_bytes()
    from nasolve.cif_attachment_links import inspect_attachment_links
    expected=inspect_attachment_links(manifest)['links']
    return native,payload,expected


def review(native,payload,expected,**kwargs):
    from nasolve.cif_topology_gate import review_native_topology
    return review_native_topology(native,payload,expected,**kwargs)


def sync(n):
    g=n['geometry']
    g['simple_bonds']=deepcopy(g['proxy_details']['bond_simple'])
    g['asu_bonds']=deepcopy(g['proxy_details']['bond_asu'])
    g['proxy_counts']={k:len(v) for k,v in g['proxy_details'].items()}


def test_exact_links_are_a_separate_nonchemical_gate(tmp_path):
    n,p,e=base(tmp_path);before=deepcopy(n)
    r=review(n,p,e)
    assert r['link_status']=='MATCH' and not r['missing_links'] and not r['unexpected_links']
    assert not r['soft_restraints'] and r['automatic_adoption'] is False
    assert r['chemical_qualification']=='NOT_ESTABLISHED' and n==before


@pytest.mark.parametrize('defect',['missing','extra','duplicate','symmetry','inferred','unclaimed_edit','unclaimed_hbond'])
def test_every_unclaimed_cross_site_bond_is_counted(tmp_path,defect):
    n,p,e=base(tmp_path);d=n['geometry']['proxy_details'];b=d['bond_simple'][0]
    if defect=='missing':d['bond_simple']=[]
    elif defect=='symmetry':b['symmetry_operation']='-x,y,z'
    else:
        extra=deepcopy(b)
        if defect!='duplicate':
            extra['i_seqs'][0]=0;extra['atoms'][0]=n['atoms'][0]['label']
        extra['origin_id']={'inferred':10,'unclaimed_edit':41,'unclaimed_hbond':37}.get(defect,0)
        d['bond_simple'].append(extra)
    sync(n);r=review(n,p,e)
    assert r['link_status']=='REVIEW'
    assert r['missing_links'] or r['unexpected_links'] or r['symmetry_bonds_touching_selected_sites']


@pytest.mark.parametrize('defect',['coordinate','label','weight','counts','empty_plan','duplicate_plan','absent_endpoint'])
def test_malformed_or_ambiguous_evidence_refuses(tmp_path,defect):
    n,p,e=base(tmp_path)
    if defect=='coordinate':n['atoms'][0]['xyz'][0]+=1
    if defect=='label':n['geometry']['proxy_details']['bond_simple'][0]['atoms'][0]='wrong'
    if defect=='weight':n['geometry']['proxy_details']['bond_simple'][0]['weight']=True
    if defect=='empty_plan':e=[]
    if defect=='duplicate_plan':e=e+e
    if defect=='absent_endpoint':e[0]['endpoints'][0]['atom_id']='absent'
    sync(n)
    if defect=='counts':n['geometry']['proxy_counts']['bond_simple']+=1
    with pytest.raises(ValueError):review(n,p,e)


def paired(tmp_path):
    from .test_cif_na_policy import fixture as pair_fixture
    from nasolve.cif_na_policy import compile_na_policy
    model,ph,n=pair_fixture(tmp_path)
    policy=compile_na_policy(model,[ph],n,tmp_path/'compiled')
    for a in n['atoms']:a.update(element=a['atom_id'][0],occupancy=1.)
    n['atom_count']=len(n['atoms'])
    n['restraint_policy']={'secondary_structure_enabled':False,'origin_ids':{'hydrogen bonds':37,'edits':41,'basepair stacking':43,'basepair parallelity':47,'basepair planarity':49}}
    # Synthetic explicit covalent edge, unrelated to the actual generated pair.
    indices=[0,len(n['atoms'])-1]
    edge={'i_seqs':indices,'atoms':[n['atoms'][i]['label'] for i in indices],
          'distance_ideal':1.6,'weight':100.,'origin_id':0,'symmetry_operation':None}
    expected=[{'endpoints':[{'site':'Z:'+n['atoms'][i]['identity']['resseq'],'component':n['atoms'][i]['identity']['resname'],'atom_id':n['atoms'][i]['atom_id']} for i in indices]}]
    n['geometry'].update(status='RECORDED',sites_cart_exact=[a['xyz'] for a in n['atoms']],proxy_details={'bond_simple':[edge],'bond_asu':[]},custom_proxy_requests=deepcopy(policy['compiled_requests']))
    for q in policy['compiled_requests']:
        if q['kind']=='bond':n['geometry']['proxy_details']['bond_simple'].append({**{k:deepcopy(v) for k,v in q.items() if k not in {'kind','action','selections'}},'origin_id':41,'symmetry_operation':None})
    sync(n)
    return n,model.read_bytes(),expected,policy,(tmp_path/'compiled/explicit_na_policy.phil').read_text()


def test_only_exact_frozen_nar_pair_bonds_are_separated(tmp_path):
    n,p,e,policy,phil=paired(tmp_path)
    assert review(n,p,e)['link_status']=='REVIEW'
    r=review(n,p,e,na_policy=policy,na_phil=phil)
    assert r['link_status']=='MATCH' and len(r['soft_restraints'])==2
    assert len(r['links'])==1 and not r['unexpected_links']
    assert r['soft_restraint_authority']=='FROZEN_EXPLICIT_NARESTRAINTS_DECLARATION'


@pytest.mark.parametrize('defect',['origin','target','weight','missing','duplicate','request','request_duplicate','phil','policy_id','authority','relationship','overlap','enabled','origin_collision','omitted_phil'])
def test_soft_exemption_cannot_hide_an_unbound_or_conflicting_bond(tmp_path,defect):
    n,p,e,policy,phil=paired(tmp_path);d=n['geometry']['proxy_details']
    if defect=='origin':d['bond_simple'][1]['origin_id']=10
    if defect=='target':d['bond_simple'][1]['distance_ideal']+=.1
    if defect=='weight':d['bond_simple'][1]['weight']*=2
    if defect=='missing':d['bond_simple'].pop(1)
    if defect=='duplicate':d['bond_simple'].append(deepcopy(d['bond_simple'][1]))
    if defect=='request':n['geometry']['custom_proxy_requests'].pop(0)
    if defect=='request_duplicate':n['geometry']['custom_proxy_requests'].append(deepcopy(n['geometry']['custom_proxy_requests'][0]))
    if defect=='phil':phil=phil.replace('distance_ideal = 2.8','distance_ideal = 2.9')
    if defect=='policy_id':policy['policy_id']='unknown'
    if defect=='authority':policy['policy_authority']='distance guess'
    if defect=='relationship':policy['relationships'][0]['sites']=['Z:1','Z:3']
    if defect=='overlap':
        q=d['bond_simple'][1];e.append({'endpoints':[{'site':'Z:'+n['atoms'][i]['identity']['resseq'],'component':n['atoms'][i]['identity']['resname'],'atom_id':n['atoms'][i]['atom_id']} for i in q['i_seqs']]})
    if defect=='enabled':n['restraint_policy']['secondary_structure_enabled']=True
    if defect=='origin_collision':n['restraint_policy']['origin_ids']['hydrogen bonds']=41
    if defect=='omitted_phil':phil=None
    sync(n)
    with pytest.raises(ValueError):review(n,p,e,na_policy=policy,na_phil=phil)


def test_fana_gate_rejects_old_incoming_only_control_but_keeps_legacy_reader(tmp_path):
    from .test_cif_fana_junction import fixture as junction_fixture, prepare
    from nasolve.cif_fana_topology import inspect_fana_topology, require_fana_topology
    paths,n=junction_fixture(tmp_path)
    # C109 capture is tested separately; this fixture exercises exact source binding.
    occupancies={(line[22:26].strip(),line[12:16].strip()):float(line[54:60])
                 for line in paths[1].read_text().splitlines() if line[:6] in {'ATOM  ','HETATM'}}
    for a in n['atoms']:a['occupancy']=occupancies[a['identity']['resseq'],a['atom_id']]
    with patch('nasolve.cif_fana_topology._capture',return_value=({'phenix_version':'synthetic'},n,{})):
        r=inspect_fana_topology(paths[0],paths[1],paths[2])
        assert r['link_status']=='REVIEW' and len(r['missing_links'])==1
        with pytest.raises(ValueError,match='topology'):require_fana_topology(paths[0],paths[1],paths[2])
    assert prepare(paths)['status']=='JUNCTION_ANGLES_COMPILED'


@pytest.mark.parametrize('mode',['energy','nonbonded','bad_flag','mapping_conflict','missing_energy','worker'])
def test_c109_capture_recognizes_only_maintained_extended_workers(tmp_path,mode):
    from nasolve.cif_attachment_native import _capture
    from nasolve.cif_native_validation import _NATIVE_WORKER
    from nasolve.cif_candidate_usability import native_energy_worker
    from nasolve.cif_native_nonbonded import native_nonbonded_worker
    manifest,path=fixture(tmp_path);spec_path=path.parent/'native_spec.json'
    spec=json.loads(spec_path.read_text());spec['energy_inventory']=True
    worker=native_energy_worker(_NATIVE_WORKER)
    if mode in {'nonbonded','missing_energy'}:
        spec['nonbonded_inventory']=True;worker=native_nonbonded_worker(worker)
    if mode=='bad_flag':spec['energy_inventory']=1
    if mode=='mapping_conflict':spec['atom_name_mapping']=True
    if mode=='missing_energy':del spec['energy_inventory']
    if mode=='worker':worker+='unexpected'
    spec_path.write_text(json.dumps(spec));(path.parent/'native_worker.py').write_text(worker);rebind(path)
    payload=(manifest.parent/'model.pdb').read_bytes()
    if mode in {'energy','nonbonded'}:
        assert _capture(path,payload)[1]['status']=='REVIEW'
    else:
        with pytest.raises(ValueError):_capture(path,payload)


def test_fana_complete_topology_is_required_without_accepting_geometry(tmp_path):
    from .test_cif_fana_junction import fixture as junction_fixture
    from nasolve.cif_fana_topology import inspect_fana_topology,require_fana_topology
    paths,n=junction_fixture(tmp_path)
    occupancies={(line[22:26].strip(),line[12:16].strip()):float(line[54:60])
                 for line in paths[1].read_text().splitlines() if line[:6] in {'ATOM  ','HETATM'}}
    for a in n['atoms']:a['occupancy']=occupancies[a['identity']['resseq'],a['atom_id']]
    ids=[next(a['i_seq'] for a in n['atoms'] if a['identity']['resseq']==site and a['atom_id']==name)
         for site,name in [('2',"O3'"),('3','P')]]
    n['geometry']['proxy_details']['bond_simple'].append({'i_seqs':ids,'atoms':[n['atoms'][i]['label'] for i in ids],
        'distance_ideal':1.607,'weight':1000.,'origin_id':0,'symmetry_operation':None})
    sync(n)
    with patch('nasolve.cif_fana_topology._capture',return_value=({'phenix_version':'synthetic'},n,{})):
        r=require_fana_topology(paths[0],paths[1],paths[2])
        assert r['link_status']=='MATCH' and r['geometry_acceptance']=='NOT_ASSESSED'
        old=tmp_path/'relocated';paths[0].rename(old)
        assert require_fana_topology(old,old/'model.pdb',paths[2])==r
        n['monomer_mappings']['rows'][0]['metadata']['effective_definition']['atoms'].pop()
        with pytest.raises(ValueError,match='projection'):inspect_fana_topology(old,old/'model.pdb',paths[2])


@pytest.mark.parametrize('change',['delete','sigma_zero','sigma_inf','unknown_scope'])
def test_soft_phil_unsupported_actions_and_parameters_refuse(tmp_path,change):
    n,p,e,policy,phil=paired(tmp_path)
    if change=='delete':phil=phil.replace('bond {','bond {\n action = delete',1)
    if change=='sigma_zero':phil=phil.replace('sigma = 0.027','sigma = 0',1)
    if change=='sigma_inf':phil=phil.replace('sigma = 0.027','sigma = inf',1)
    if change=='unknown_scope':phil+='unknown {\n what = ever\n}\n'
    with pytest.raises(ValueError):review(n,p,e,na_policy=policy,na_phil=phil)
