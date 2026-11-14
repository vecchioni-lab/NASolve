"""Selection dependency is not chemical acceptance or a native residual estimate."""
from copy import deepcopy
from unittest.mock import patch
import math
import pytest
from tests.test_cif_native_nonbonded import capture as pair_capture


def capture():
    n=pair_capture()
    n.update(monomer_mappings=[],installed_api_sources=[],restraint_policy={})
    return n


def test_all_three_scopes_partition_actual_pairs_and_preserve_every_scalar_row():
    from nasolve.cif_selected_environment import review_selected_environment
    n=capture();before=deepcopy(n)
    for selected,expected in [([0,1],{'selected_only':16.,'boundary':0.,'fixed_only':0.}),
                              ([0],{'selected_only':0.,'boundary':16.,'fixed_only':0.}),
                              ([3],{'selected_only':0.,'boundary':0.,'fixed_only':16.})]:
        with patch('subprocess.Popen',side_effect=AssertionError('read-only')):r=review_selected_environment(n,selected)
        assert {k:v['native_residual'] for k,v in r['nonbonded']['groups'].items()}==expected
        assert sum(v['pair_count'] for v in r['nonbonded']['groups'].values())==2
        assert sum(len(v['rows']) for v in r['geometry']['bond_simple'].values())==1
        assert r['nonbonded']['total_native_residual']==16.
        assert r['total_objective_partition']=='NOT_ESTABLISHED' and not r['geometry_accepted'] and not r['automatic_adoption']
    assert n==before


def test_full_gradient_is_projected_by_selection_without_declaring_convergence():
    from nasolve.cif_selected_environment import review_selected_environment
    r=review_selected_environment(capture(),[0])
    assert r['gradient']['selected_norm']==64. and r['gradient']['fixed_norm']==64.
    assert r['gradient']['full_norm']==pytest.approx(math.sqrt(2)*64.)
    r=review_selected_environment(capture(),[3])
    assert r['gradient']['selected_norm']==0. and r['gradient']['fixed_norm']>0.
    assert r['convergence']=='NOT_ASSESSED'


@pytest.mark.parametrize('selected',[[],[True],[0,0],[-1],[4],[0,1,2,3]])
def test_invalid_selections_refuse(selected):
    from nasolve.cif_selected_environment import review_selected_environment
    with pytest.raises(ValueError):review_selected_environment(capture(),selected)


@pytest.mark.parametrize('defect',['pair_residual','pair_gradient','native_gradient','native_norm','geometry_identity'])
def test_reuses_raw_native_checks_instead_of_trusting_summaries(defect):
    from nasolve.cif_selected_environment import review_selected_environment
    n=capture()
    if defect=='pair_residual':n['nonbonded_inventory']['snapshots'][0]['pairs'][0]['residual']+=1
    if defect=='pair_gradient':n['nonbonded_inventory']['snapshots'][0]['pairs'][0]['gradient'][0]+=1
    if defect=='native_gradient':n['energy_inventory']['snapshots'][0]['gradient'][0]=math.nan
    if defect=='native_norm':
        for e in n['energy_inventory']['snapshots']:e['gradient_norm']=1.
    if defect=='geometry_identity':n['geometry']['proxy_details']['angle'][0]['atoms'][0]='wrong'
    with pytest.raises(ValueError):review_selected_environment(n,[0])


def test_unmeasurable_rows_and_deferred_categories_are_not_silently_dropped():
    from nasolve.cif_selected_environment import review_selected_environment
    n=capture();n['geometry']['proxy_details']['bond_simple'][0]['weight']=None
    n['geometry']['proxy_details']['dihedral']=[{'unassessed':'unknown convention'}];n['geometry']['proxy_counts']['dihedral']=1
    r=review_selected_environment(n,[0])
    row=r['geometry']['bond_simple']['boundary']['rows'][0]
    assert row['status']=='UNSUPPORTED' and row['nominal_deviation'] is None
    assert r['geometry']['bond_simple']['boundary']['unranked_count']==1
    assert r['deferred_proxy_kinds']['dihedral']['count']==1
    assert r['covalent_native_residuals']=='UNASSESSED'


@pytest.mark.parametrize('mode',['valid','review','candidate_changed','receipt_changed'])
def test_fana_binding_cannot_relabel_failed_gates_or_changed_inputs(tmp_path,monkeypatch,mode):
    from hashlib import sha256
    import nasolve.cif_selected_environment as g
    trial=tmp_path/'trial';trial.mkdir();(trial/'candidate.pdb').write_bytes(b'synthetic candidate')
    pair=tmp_path/'pairs.json';pair.write_bytes(b'synthetic bound receipt')
    bound={'trial':{'candidate_sha256':sha256((trial/'candidate.pdb').read_bytes()).hexdigest(),'moving_indices':[0],
                    'stopping_classification':'NOT_CONVERGED_LIMIT'},
           'candidate_checks_pass':mode!='review','checks':{'source':mode!='review'},
           'bindings':{'pair_receipt':g._digest(pair.read_bytes())}}
    if mode=='candidate_changed':(trial/'candidate.pdb').write_bytes(b'changed')
    if mode=='receipt_changed':pair.write_bytes(b'changed')
    monkeypatch.setattr(g,'inspect_fana_selected_geometry',lambda *args:deepcopy(bound))
    monkeypatch.setattr(g,'_capture',lambda *args:({},capture(),{pair:pair.read_bytes()}))
    if mode.endswith('changed'):
        with pytest.raises(ValueError):g.inspect_fana_environment(None,None,trial,None,pair)
    else:
        r=g.inspect_fana_environment(None,None,trial,None,pair)
        assert r['fana_endpoint']['candidate_checks_pass'] is (mode=='valid')
        assert r['fana_endpoint']['stopping_classification']=='NOT_CONVERGED_LIMIT'
        assert not r['geometry_accepted'] and not r['automatic_adoption']
