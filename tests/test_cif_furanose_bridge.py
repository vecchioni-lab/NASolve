"""Graph-bound furanose seed kinematics; synthetic poses are not refinement proof."""
from pathlib import Path
import json
from unittest.mock import patch
import pytest
from tests.test_cif_base_anchored_furanose import inputs,run
from tests.test_cif_catalogue import snapshot


def control(tmp_path, *, bridged=False, rename=False, hand='D', edit_frame=None):
    from nasolve.cif_stereochemistry_audit import _values,_coordinates
    paths,c=inputs(tmp_path,bridged=bridged,rename=rename,hand=hand)
    _,xyz=_coordinates(_values(paths[1],'Z99'),source=False)
    virtual=xyz[c['ports']['phosphate']['leaving_atom']]
    lines=paths[4].read_text().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line[:6]!='ATOM  ':continue
        if line[21:26]=='A  11':line=line[:46]+f'{-float(line[46:54]):8.3f}'+line[54:]
        if line[21:26]=='A  10' and line[12:16].strip()==c['ports']['phosphate']['partner']['atom_id']:
            point=[-virtual[1]+55,virtual[0]+10,virtual[2]+2]
            line=line[:30]+''.join(f'{x:8.3f}' for x in point)+line[54:]
        lines[i]=line
    if edit_frame is not None:edit_frame(lines)
    paths[4].write_text(''.join(lines));run(paths,c)
    return paths[-1]


def seed(placement,out,**kw):
    from nasolve.cif_furanose_bridge import prepare_furanose_bridge_seed
    return prepare_furanose_bridge_seed(placement,out,endpoint_weight=1000.,max_base_displacement=2.,**kw)


def test_source_phosphate_arm_roles_survive_renaming_but_refuse_a_ring_or_double_bond(tmp_path):
    from nasolve.cif_attachment_profiles import inspect_attachment_profile
    from nasolve.cif_furanose_bridge import phosphate_arm_rotors
    from nasolve.cif_stereochemistry_audit import _values, _graph

    paths, context = inputs(tmp_path, bridged=True, rename=True)
    roles = inspect_attachment_profile(paths[0], "Z99", workbook=paths[3])["bindings"]
    _, bonds, _, graph = _graph(_values(paths[0], "Z99"))
    leaving = context["ports"]["phosphate"]["leaving_atom"]
    groups = phosphate_arm_rotors(roles, graph, bonds, leaving_atom=leaving)
    ester, phosphorus = groups[-1]["axis_atoms"]
    assert (ester, phosphorus) == (roles["five_o"], roles["phosphate"])
    assert leaving in groups[-1]["moving_source_atoms"]
    assert roles["ring_c4"] not in set().union(*(set(r["moving_source_atoms"]) for r in groups))
    with pytest.raises(ValueError, match="single bond"):
        phosphate_arm_rotors(roles, graph, {**bonds, tuple(sorted([ester, phosphorus])): "DOUBLE"}, leaving_atom=leaving)
    graph[roles["ring_c4"]].add(leaving)
    graph[leaving].add(roles["ring_c4"])
    with pytest.raises(ValueError, match="ring bond"):
        phosphate_arm_rotors(roles, graph, bonds, leaving_atom=leaving)


@pytest.mark.parametrize('bridged,rename,hand',[(False,False,'D'),(False,True,'L'),(True,False,'D'),(True,True,'D')])
def test_general_seed_preserves_all_source_hands_and_bystanders(tmp_path,bridged,rename,hand):
    from nasolve.cif_furanose_bridge import read_furanose_bridge_seed
    placement=control(tmp_path,bridged=bridged,rename=rename,hand=hand);before=snapshot(tmp_path);out=tmp_path/'seed'
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):
        q=seed(placement,out);assert read_furanose_bridge_seed(out)==q
    assert q['status']=='FURANOSE_BRIDGE_SEED_REVIEW' and not q['automatic_adoption']
    assert q['native_linkage']=='NOT_ASSESSED' and not q['virtual_atom_written']
    assert q['search']['evaluations']<=27*(1+5*8*6)+1
    assert q['preservation']['max_bond_length_error']<1e-9
    assert q['preservation']['max_angle_error_degrees']<1e-8
    assert q['max_base_displacement_angstrom']<.01
    assert q['virtual_partner_error']<.002
    assert all(abs(j['pdb_rounded']-j['before'])<.002 for j in q['junctions'])
    assert not q['search']['global_minimum_claimed']
    assert len({r['center'] for r in q['source_hands']})==4
    assert len(q['source_hands'])==(7 if bridged else 4)
    unchanged=lambda p:[l for l in p.read_text().splitlines() if not(l[:6] in {'ATOM  ','HETATM'} and l[21:26]=='A  11')]
    assert unchanged(placement/'model.pdb')==unchanged(out/'model.pdb')
    assert all(snapshot(tmp_path)[k]==v for k,v in before.items())
    assert str(tmp_path) not in json.dumps(q)


@pytest.mark.parametrize('key,value',[('endpoint_weight',True),('endpoint_weight',0),('endpoint_weight',1001),('endpoint_weight',float('nan')),('max_base_displacement',True),('max_base_displacement',0),('max_base_displacement',6),('max_base_displacement',float('inf'))])
def test_invalid_bound_refuses_without_output(tmp_path,key,value):
    from nasolve.cif_furanose_bridge import prepare_furanose_bridge_seed
    placement=control(tmp_path);out=tmp_path/'seed';config={'endpoint_weight':1000.,'max_base_displacement':2.};config[key]=value
    with pytest.raises(ValueError):prepare_furanose_bridge_seed(placement,out,**config)
    assert not out.exists()


def test_excessive_motion_never_becomes_a_seed(tmp_path):
    import nasolve.cif_furanose_bridge as module
    placement=control(tmp_path)
    original=module._search
    def shifted(*args):
        points,report=original(*args);return points+10,report
    with patch.object(module,'_search',shifted),pytest.raises(ValueError,match='base displacement'):
        seed(placement,tmp_path/'seed')
    assert not (tmp_path/'seed').exists()


@pytest.mark.parametrize('defect',['model','report','config','extra','empty_directory','receipt','incomplete'])
def test_rehashed_forgery_refuses(tmp_path,defect):
    from nasolve.cif_furanose_bridge import read_furanose_bridge_seed
    from nasolve.cif_fana_component import _digest
    placement=control(tmp_path);out=tmp_path/'seed';seed(placement,out);r=json.loads((out/'receipt.json').read_text());name=None
    if defect=='model':name='model.pdb';(out/name).write_text((out/name).read_text().replace('20.00','99.00'))
    if defect=='report':name='seed.json';q=json.loads((out/name).read_text());q['native_linkage']='PASS';(out/name).write_text(json.dumps(q))
    if defect=='config':name='config.json';q=json.loads((out/name).read_text());q['extra']=True;(out/name).write_text(json.dumps(q))
    if defect=='extra':(out/'extra').write_text('unbound')
    if defect=='empty_directory':(out/'extra').mkdir()
    if defect=='receipt':r['schema_version']=True
    if name:r['files'][name]=_digest(out/name)
    (out/'receipt.json').write_text(json.dumps(r))
    if defect=='incomplete':(out/'receipt.json').unlink()
    with pytest.raises((ValueError,FileNotFoundError)):read_furanose_bridge_seed(out)


def test_relocation_and_interruption_preserve_history(tmp_path):
    import nasolve.cif_furanose_bridge as module
    old=tmp_path/'old';old.mkdir();placement=control(old,bridged=True);out=old/'seed';q=seed(placement,out);before=snapshot(old)
    with pytest.raises(FileExistsError):seed(placement,out)
    assert snapshot(old)==before
    moved=old.rename(tmp_path/'moved')
    with patch('subprocess.Popen',side_effect=AssertionError('offline')):assert module.read_furanose_bridge_seed(moved/'seed')==q
    assert not old.exists() and snapshot(moved)==before
    original=module._seed;calls=0
    def interrupt(*a):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('interrupted')
        return original(*a)
    with patch.object(module,'_seed',interrupt),pytest.raises(RuntimeError):seed(moved/'control',tmp_path/'partial')
    assert (tmp_path/'partial/placement/receipt.json').exists() and not (tmp_path/'partial/receipt.json').exists()
    with pytest.raises(FileExistsError):seed(moved/'control',tmp_path/'partial')


@pytest.mark.parametrize('defect',['reflection','bond_distortion'])
def test_corrupt_search_result_cannot_bypass_chemistry(tmp_path,defect):
    import nasolve.cif_furanose_bridge as module
    placement=control(tmp_path,bridged=True);original=module._search
    def invalid(*args):
        points,report=original(*args)
        if defect=='reflection':points[:,2]=2*points[:,2].mean()-points[:,2]
        else:points[0,0]+=.01
        return points,report
    with patch.object(module,'_search',invalid),pytest.raises(ValueError):
        module.prepare_furanose_bridge_seed(placement,tmp_path/'seed',endpoint_weight=1000.,max_base_displacement=5.)
    assert not (tmp_path/'seed').exists()


@pytest.mark.parametrize('occupancy,transfers',[(1.0,True),(0.5,False)])
def test_source_equivalent_base_can_inherit_nonuniform_starting_b(tmp_path,occupancy,transfers):
    from nasolve.cif_furanose_bridge import prepare_furanose_bridge_seed, read_furanose_bridge_seed

    def add_b_values(lines):
        for i,line in enumerate(lines):
            if line.startswith('ATOM  ') and line[21:26]=='A  11':
                name=line[12:16].strip()
                if name in ('BN','BC','BX'):
                    donor={'BN':65.31,'BC':89.14,'BX':124.29}[name]
                    q=occupancy if name=='BC' else 1.
                    lines[i]=line[:54]+f'{q:6.2f}{donor:6.2f}'+line[66:]

    placement=control(tmp_path,edit_frame=add_b_values)
    original=tmp_path/'old'; seed(placement,original)
    out=tmp_path/'new'
    result=prepare_furanose_bridge_seed(placement,out,endpoint_weight=1000.,max_base_displacement=2.,
                                        inherit_equivalent_base_b=True)
    moved=out.rename(tmp_path/'relocated')
    assert read_furanose_bridge_seed(moved)==result
    before=(original/'model.pdb').read_text().splitlines()
    after=(moved/'model.pdb').read_text().splitlines()
    assert len(before)==len(after)
    changed=[]
    for a,b in zip(before,after):
        assert a[:60]+a[66:]==b[:60]+b[66:]
        if a!=b:
            assert a[21:26]=='A  11'
            changed.append((a[12:16].strip(),float(b[60:66])))
    assert dict(changed)==({'BN':65.31,'BC':89.14,'BX':124.29} if transfers else {})
    assert result['base_displacement']['status']==('MATCHED_HOST_BASE' if transfers else 'RETAINED_SEED')
    assert result['source_hands']==read_furanose_bridge_seed(original)['source_hands']
    assert not result['automatic_adoption']


@pytest.mark.parametrize('defect',[None,'missing_role','element','bond_order','charge','hydrogen','isotope','chirality','anisotropic'])
def test_matched_base_uses_catalogue_names_and_the_complete_source_graph(defect):
    from copy import deepcopy
    from nasolve.cif_base_displacement import inherit_base_displacement
    from tests.test_cif_fana import molecule

    host,_=molecule(); target=deepcopy(host)
    # A new dictionary may spell an equivalent atom differently.
    for key in target:
        if 'atom_id' in key:
            target[key]=['QB' if n=='BC' else n for n in target[key]]
    roles={'base':'BN','anomeric':'C1'}
    donor=dict(bindings=roles,operational_signature={'atom_roles':{'N1':'BN','C2':'BC','C6':'BX'}})
    acceptor=dict(bindings=roles,operational_signature={'atom_roles':{'N1':'BN','C2':'QB','C6':'BX'}})
    def pdb(names,bs):
        return ''.join(f'ATOM  {i:5d} {n:>4} Z99 A  11    '+3*f'{0.:8.3f}'+f'{1.:6.2f}{b:6.2f}           {el}\n'
                       for i,(n,b,el) in enumerate(zip(names,bs,['N','C','C']),1))
    original=pdb(['BN','BC','BX'],[80.,90.,100.]); seed_model=pdb(['BN','QB','BX'],[20.]*3)
    ai=target['_chem_comp_atom.atom_id'].index('QB')
    if defect=='missing_role':del acceptor['operational_signature']['atom_roles']['C6']
    if defect=='element':target['_chem_comp_atom.type_symbol'][ai]='N'
    if defect=='bond_order':target['_chem_comp_bond.value_order'][1]='SING'
    if defect=='charge':target['_chem_comp_atom.charge'][ai]='1'
    if defect=='isotope':
        table=target['_chem_comp_atom.pdbx_mass_number']=['.']*len(target['_chem_comp_atom.atom_id'])
        table[ai]='13'
    if defect=='hydrogen':
        idx=target['_chem_comp_bond.atom_id_2'].index('BCH0')
        target['_chem_comp_bond.atom_id_1'][idx]='BX'
    if defect=='chirality':target['_chem_comp_atom.pdbx_stereo_config'][ai]='?'
    if defect=='anisotropic':original+='ANISOU'+original.splitlines()[0][6:]+'\n'
    final, evidence=inherit_base_displacement(donor,acceptor,host,target,original,seed_model,'A:11')
    if defect:
        assert final==seed_model and evidence['status']=='RETAINED_SEED' and not evidence['atoms']
    else:
        assert evidence['status']=='MATCHED_HOST_BASE'
        assert {r['target_atom']:r['initial_b'] for r in evidence['atoms']}=={'BN':80.,'QB':90.,'BX':100.}
        assert next(r for r in evidence['atoms'] if r['target_atom']=='QB')['host_atom']=='BC'
