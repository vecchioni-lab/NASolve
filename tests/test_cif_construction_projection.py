"""Canonical-input projections never pretend the future residue already exists."""
from copy import deepcopy
from hashlib import sha256
from itertools import combinations
from pathlib import Path
import json
import shutil
from unittest.mock import patch

import pytest

from nasolve.cif_dictionary_sites import prepare_dictionary_sites, read_dictionary_sites, inspect_dictionary_site_native
from nasolve.cif_dictionary_store import resolve_qualified_dictionary
from nasolve.cif_linked_preparation import component_values, _render
from tests.test_cif_dictionary_sites import inputs
from tests.test_cif_preparation_qualification import qualification, POLICY


def construction_inputs(tmp_path, *, chi_frame=False):
    args=inputs(tmp_path)
    source=tmp_path/'inputs/source.cif';numerical=tmp_path/'inputs/numerical.cif'
    v=component_values(source,'ZZZ');a,b,g='_chem_comp_atom.','_chem_comp_bond.','_chem_comp_angle.'
    additions={"C1'":'C',"C2'":'C',"C4'":'C',"O4'":'O','NX':'N','C6':'C'}
    if chi_frame:
        additions.pop('NX');additions.update(N1='N',C2='C')
    for name,element in additions.items():
        for field in [k for k in v if k.startswith(a)]:
            v[field].append({'comp_id':'ZZZ','atom_id':name,'type_symbol':element,'type_energy':element,'charge':'0'}[field[len(a):]])
    extra=[("C4'","C5'"),("C4'","O4'"),("O4'","C1'"),("C1'","C2'"),("C2'","C3'"),("C3'","C4'"),("C1'",'NX'),('NX','C6')]
    if chi_frame:extra=[tuple('N1' if n=='NX' else n for n in pair) for pair in extra]+[('N1','C2')]
    for first,second in extra:
        for field in [k for k in v if k.startswith(b)]:
            v[field].append({'comp_id':'ZZZ','atom_id_1':first,'atom_id_2':second,'type':'single','value_dist':'1.5','value_dist_esd':'0.02'}[field[len(b):]])
    bonds=list(zip(v[b+'atom_id_1'],v[b+'atom_id_2']))
    for field in [k for k in v if k.startswith(g)]:v[field]=[]
    for center in v[a+'atom_id']:
        near=[y if x==center else x for x,y in bonds if center in (x,y)]
        for first,third in combinations(near,2):
            for field in [k for k in v if k.startswith(g)]:
                v[field].append({'comp_id':'ZZZ','atom_id_1':first,'atom_id_2':center,'atom_id_3':third,'value_angle':'109.47','value_angle_esd':'3.0'}[field[len(g):]])
    source.write_text(_render(v,'ZZZ'));numerical.write_text(_render(v,'ZZZ'))
    q=qualification(source,numerical,'ZZZ');snapshot=tmp_path/'complete-snapshot'
    resolve_qualified_dictionary(source,'ZZZ',tmp_path/'complete-store',snapshot,
        source_authority='EXPLICIT',recipe={'policy_id':'SYNTHETIC_REPAIR','bond_representation_policy':POLICY},
        generator={'name':'FAKE','version':'TEST'},consumer=args['consumer'],
        acquire=lambda:dict(candidate=numerical,qualification=q,provenance={'converged':False,'stopping':'TEST','notes':['Synthetic fixture, not native qualification.']}))
    args['snapshot']=snapshot
    original=args['model'].read_text().splitlines(keepends=True);serial=max(int(l[6:11]) for l in original if l.startswith('HETATM'));lines=[]
    for context in args['contexts']:
        chain,resid=context['site'].split(':')
        selected=[l for l in original if l.startswith('HETATM') and l[21]==chain and int(l[22:26])==int(resid)]
        lines.extend(selected)
        for name,element in additions.items():
            serial+=1;lines.append(f'HETATM{serial:5d} {name:>4} ZZZ {chain}{int(resid):4d}    {serial:8.3f}{1.:8.3f}{2.:8.3f}  1.00 20.00          {element:>2}\n')
    actual=tmp_path/'actual.pdb';actual.write_text(''.join(lines)+'END\n')
    canonical=tmp_path/'canonical.pdb';canonical.write_text(actual.read_text().replace(' ZZZ ', '  DT ').replace('  NX ', '  N1 '))
    args['model']=canonical;args['construction_targets']={c['site']:'DT' for c in args['contexts']}
    return args,actual


def test_projections_match_actual_model_without_fabricating_coordinates(tmp_path):
    args,actual=construction_inputs(tmp_path);before=args['model'].read_bytes()
    legacy=dict(args,model=actual);legacy.pop('construction_targets')
    prepare_dictionary_sites(output=tmp_path/'actual-sites',**legacy)
    result=prepare_dictionary_sites(output=tmp_path/'construction',**args)
    read=read_dictionary_sites(tmp_path/'construction');old=read_dictionary_sites(tmp_path/'actual-sites')
    assert result['policy_id']=='cif-stored-construction-dictionaries-v1'
    assert result['automatic_adoption'] is False and result['model_editing']=='NOT_RUN'
    assert 'model' not in read and 'before_dictionaries' not in read and 'after_phils' not in read
    assert read['canonical_model'].read_bytes()==before==args['model'].read_bytes()
    assert {s:p.read_bytes() for s,(p,c) in read['projections'].items()}=={s:p.read_bytes() for s,(p,c) in old['projections'].items()}
    proof=read['preparation']['construction_context']
    assert proof['scope']=='PRECONSTRUCTION_ONLY' and proof['constructed_model']=='NOT_CREATED'
    assert all(r['before']=='DT' and r['after']=='ZZZ' and 'N1' not in r['protected_atoms'] for r in proof['targets'])
    assert len(list((tmp_path/'construction').rglob('*.pdb')))==1
    with patch('nasolve.cif_attachment_native._capture',side_effect=AssertionError('Must refuse before native read')):
        with pytest.raises(ValueError,match='real constructed model'):
            inspect_dictionary_site_native(tmp_path/'construction',tmp_path/'missing1',tmp_path/'missing2')


@pytest.mark.parametrize('defect',['empty','nonmapping','missing_site','extra_site','wrong_before','rna',
    'already_modified','missing_sugar','wrong_element','extra_sugar','alias','hydrogen','altloc',
    'phosphate_missing','free_oh_phosphate','wrong_links','native_context','supplementary','stale_qualification'])
def test_bad_canonical_context_cannot_publish(tmp_path,defect):
    args,actual=construction_inputs(tmp_path);model=args['model']
    if defect=='empty':args['construction_targets']={}
    elif defect=='nonmapping':args['construction_targets']=[]
    elif defect=='missing_site':args['construction_targets'].pop('A:1')
    elif defect=='extra_site':args['construction_targets']['C:9']='DT'
    elif defect=='wrong_before':args['construction_targets']['A:1']='DA'
    elif defect=='rna':args['construction_targets']['A:1']='U'
    elif defect=='already_modified':args['model']=actual
    elif defect in {'missing_sugar','phosphate_missing'}:
        name="C4'" if defect=='missing_sugar' else 'P'
        model.write_text(''.join(l for l in model.read_text().splitlines(keepends=True) if l[12:16].strip()!=name))
    elif defect=='wrong_element':
        model.write_text(''.join(l[:76]+' N'+l[78:] if l[12:16].strip()=="O4'" else l for l in model.read_text().splitlines(keepends=True)))
    elif defect in {'extra_sugar','hydrogen','altloc'}:
        l=next(l for l in model.read_text().splitlines(keepends=True) if l[12:16].strip()=="O4'")
        if defect=='extra_sugar':l=l[:12]+" O2'"+l[16:]
        elif defect=='hydrogen':l=l[:12]+' H9 '+l[16:76]+' H'+l[78:]
        else:l=l[:16]+'A'+l[17:]
        model.write_text(model.read_text()+l)
    elif defect=='alias':model.write_text(model.read_text().replace(' OP1',' O1P'))
    elif defect=='free_oh_phosphate':args['contexts'][0]['five_prime_state']='free_OH'
    elif defect=='wrong_links':args['expected_links']=[]
    elif defect=='native_context':args['native_context']={'policy_id':'bogus'}
    elif defect=='supplementary':args['supplementary_phils']=[tmp_path/'unused.phil'];args['supplementary_phils'][0].write_text('')
    elif defect=='stale_qualification':(args['snapshot']/'entry/qualification.json').write_text('{}')
    with pytest.raises((ValueError,KeyError)):
        prepare_dictionary_sites(output=tmp_path/'out',**args)
    assert not (tmp_path/'out').exists()


def test_cold_replay_rederives_projection_after_original_sources_are_removed(tmp_path):
    args,_=construction_inputs(tmp_path);out=tmp_path/'bundle';prepare_dictionary_sites(output=out,**args)
    frozen={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    moved=tmp_path/'relocated/bundle';moved.parent.mkdir();out.rename(moved)
    for p in list(tmp_path.iterdir()):
        if p==moved.parent:continue
        if p.is_dir():shutil.rmtree(p)
        else:p.unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Cold replay must not execute')):
        result=read_dictionary_sites(moved)
    assert result['report']['construction_targets']=={'A:1':'DT','A:2':'DT','B:1':'DT'}
    assert {p.relative_to(moved):(p.read_bytes(),p.stat().st_mtime_ns) for p in moved.rglob('*') if p.is_file()}==frozen


@pytest.mark.parametrize('defect',['omit_targets','wrong_targets','old_policy','false_geometry','projection'])
def test_reader_refuses_edited_scope_or_derivation(tmp_path,defect):
    args,_=construction_inputs(tmp_path);out=tmp_path/'bundle';prepare_dictionary_sites(output=out,**args)
    receipt=out/'site_receipt.json';r=json.loads(receipt.read_text())
    if defect=='omit_targets':r.pop('construction_targets')
    elif defect=='wrong_targets':r['construction_targets']['A:1']='DA'
    elif defect=='old_policy':r['policy_id']='cif-stored-dictionary-sites-v1'
    elif defect=='false_geometry':r['canonical_geometry_qualified']=True
    else:
        p=out/'prepared/projected_A_2.cif';p.write_bytes(p.read_bytes()+b'# forged\n')
        for row in r['files']:
            if row['path']=='prepared/projected_A_2.cif':row.update(sha256=sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size)
    receipt.write_text(json.dumps(r))
    with pytest.raises((ValueError,KeyError)):read_dictionary_sites(out)


def test_preconstruction_cannot_hide_a_phosphate_atom_missing_from_source(tmp_path):
    from nasolve.cif_linked_preparation import _construction_inventory, _prune
    args,_=construction_inputs(tmp_path);source=tmp_path/'inputs/source.cif'
    v=component_values(source,'ZZZ');source.write_text(_render(_prune(v,{'OP3','leaveH'},outgoing=False),'ZZZ'))
    with pytest.raises(ValueError,match='sugar/backbone'):
        _construction_inventory(args['model'],source,'ZZZ',args['contexts'],args['construction_targets'])


def test_preconstruction_requires_bound_isolated_qualification(tmp_path):
    from nasolve.cif_linked_preparation import prepare_linked_component
    args,_=construction_inputs(tmp_path)
    model=tmp_path/'inputs/canonical.pdb';model.write_bytes(args['model'].read_bytes())
    with pytest.raises(ValueError,match='isolated qualification'):
        prepare_linked_component(tmp_path/'inputs/source.cif',tmp_path/'inputs/numerical.cif',
            model,args['contexts'],tmp_path/'unqualified',code='ZZZ',
            construction_targets=args['construction_targets'])
    assert not (tmp_path/'unqualified').exists()
