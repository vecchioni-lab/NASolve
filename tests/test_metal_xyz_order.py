"""Native atom sorting must preserve exact identity and group membership."""
import copy
import pytest
from nasolve.metal import RecipeError
from tests.test_metal_xyz import prepared,evidence


def reorder(raw,e):
    permutation=list(reversed(range(len(e['atoms']))))
    inverse={old:new for new,old in enumerate(permutation)}
    e=copy.deepcopy(e)
    e['atoms']=[e['atoms'][i] for i in permutation]
    e['normal_scattering_before']=[e['normal_scattering_before'][i] for i in permutation]
    for g in e['groups']:g['indices']=sorted(inverse[i] for i in g['indices'])
    lines=raw.decode().splitlines(keepends=True)
    atoms=[l for l in lines if l[:6].strip() in {'ATOM','HETATM'}]
    it=iter(atoms[i] for i in permutation)
    final=''.join(next(it) if l[:6].strip() in {'ATOM','HETATM'} else l for l in lines).encode()
    return e,final,permutation


def test_native_sorting_is_a_bijection_over_exact_atom_keys(tmp_path):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    e,final,permutation=reorder(raw,evidence(p,raw))
    out=xyz.audit_result(p,raw,e,final)
    assert out['fixed_state_audit']=='PASS'
    assert out['atom_order_mapping']['input_to_native']==permutation
    assert out['atom_order_mapping']['input_to_serialized']==permutation
    assert all(s['displacement_A']==0 for s in out['sites'])
    assert 'atom_order_mapping' not in xyz.audit_result(p,raw,evidence(p,raw),raw)


@pytest.mark.parametrize('change',['duplicate','missing','stale_group_indices','q','fp','charge','serialized_q','serialized_element'])
def test_sorting_never_hides_changes_or_stale_indices(tmp_path,change):
    xyz,c,h,raw,p,ref=prepared(tmp_path)
    e,final,_=reorder(raw,evidence(p,raw))
    if change=='duplicate':e['atoms'][0]['key']=copy.deepcopy(e['atoms'][1]['key'])
    elif change=='missing':e['atoms'][0]['key']['atom_name']='NEW'
    elif change=='stale_group_indices':e['groups'][0]['indices']=p['groups'][0]['indices']
    elif change in {'q','fp','charge'}:
        key={'q':'occupancy','fp':'fp','charge':'charge'}[change]
        e['atoms'][0][key]='2+' if change=='charge' else e['atoms'][0][key]+.1
    elif change=='serialized_q':final=final.replace(b'  0.60',b'  0.50',1)
    elif change=='serialized_element':final=final.replace(b'AG  \n',b'AU  \n',1)
    with pytest.raises(RecipeError):xyz.audit_result(p,raw,e,final)


def test_sorted_xyz_replays_and_seeds_frozen_fdp_by_identity(tmp_path,monkeypatch):
    import gzip,json
    from tests.test_metal_xyz import fake_execution
    from tests.test_metal_fdp import native_result
    from nasolve.metal import fdp
    xyz,c,h,ref,native=fake_execution(tmp_path,monkeypatch)
    original=xyz._native
    def sorted_native(directory,*args):
        e=original(directory,*args)
        e,final,_=reorder((directory/'final.pdb').read_bytes(),e)
        (directory/'final.pdb').write_bytes(final)
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        return e
    monkeypatch.setattr(xyz,'_native',sorted_native)
    doc=xyz.run_xyz(c.run,'Metal/hypothesis_001',native=native,phases=ref,phase_labels=['HLAM','HLBM','HLCM','HLDM'])
    assert xyz.verify_xyz(c.run,'Metal/xyz_001')==doc
    for name in ('inspect_observations','reference_scattering','audit_free_r_flags'):
        monkeypatch.setattr(fdp,name,getattr(xyz,name))
    def fit(directory,*args):
        p=json.loads((directory/'plan.json').read_text());raw=(directory/'input.pdb').read_bytes()
        e=native_result(p,raw)
        (directory/'final.pdb').write_bytes(raw);(directory/'native.log').write_text('synthetic fdp')
        (directory/'native-result.json.gz').write_bytes(gzip.compress(json.dumps(e).encode()))
        return e
    monkeypatch.setattr(fdp,'_native',fit)
    frozen=fdp.run_fdp(c.run,'Metal/xyz_001',native=native,fit_nodes=['m1','m2'],metal_b_policy='keep')
    assert fdp.verify_fdp(c.run,'Metal/fdp_001')==frozen
    p=json.loads((c.run/frozen['files']['plan.json']['relative_path']).read_text())
    assert p['groups'][0]['indices']==[1] and p['groups'][1]['indices']==[0]
