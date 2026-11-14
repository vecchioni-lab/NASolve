"""Explicit amide policy permits only source-declared neutral PNA deltas."""
import json
from unittest.mock import patch

import pytest
from Bio.PDB.mmcifio import MMCIFIO

from nasolve.cif_attachment_links import inspect_attachment_links
from nasolve.cif_linked_preparation import component_values
from nasolve.cli import main
from .test_cif_attachment_profiles import pna
from .test_cif_attachment_sites import pdb_atom
from .test_cif_attachment_links import record, edit_context, edit_manifest
from .test_cif_catalogue import workbook, row, snapshot

OPERATION = 'neutral-pna-amide-v1'


def write_cif(path, values):
    writer = MMCIFIO(); writer.set_dict(values); writer.save(str(path))


def project(path, removed, output):
    # Independent reference filtering; do not use the production projection.
    values = component_values(path, 'Z99')
    for category in {k.split('.')[0] for k in values if '.' in k}:
        fields = [k for k in values if k.startswith(category + '.')]
        refs = [k for k in fields if k.split('.')[1].startswith('atom_id')]
        if refs:
            keep = [i for i in range(len(values[fields[0]]))
                    if all(values[k][i] not in removed for k in refs)]
            for key in fields:
                if keep: values[key] = [values[key][i] for i in keep]
                else: values.pop(key)
    write_cif(output, values)


def case(root, *, charge=0, renamed=False, isotope='H', count=2):
    path = root / 'source.cif'
    names = pna(path, charge=charge, rename=renamed)
    values = component_values(path, 'Z99'); a = '_chem_comp_atom.'; b = '_chem_comp_bond.'
    # The topology-only fixture intentionally lacks acid H; declare it here.
    acid_h = 'QH' if renamed else 'HA'
    for field, value in {'comp_id':'Z99', 'atom_id':acid_h, 'type_symbol':isotope,
                         'charge':'0', 'pdbx_stereo_config':'N'}.items():
        values[a+field].append(value)
    for field, value in {'comp_id':'Z99', 'atom_id_1':names['0OH'],
                         'atom_id_2':acid_h, 'value_order':'SING'}.items():
        values[b+field].append(value)
    values[a+'type_symbol'] = [isotope if x == 'H' else x for x in values[a+'type_symbol']]
    write_cif(path, values)
    book = workbook(root, [('adenine', row('Z99', N1=names['BN'], C5=names['BC']))])
    entries = []; lines = []
    for i in range(count):
        ports = {'amine': {'state':'source'}, 'carboxyl': {'state':'source'}}
        deleted = set()
        if i > 0:
            ports['amine'] = {'state':'linked', 'operation':OPERATION, 'leaving_atom':names['0H0'],
                'partner':{'site':f'A:{i}', 'component':'Z99', 'atom_id':names['0A']}, 'symmetry_operation':'x,y,z'}
            deleted.add(names['0H0'])
        if i < count-1:
            ports['carboxyl'] = {'state':'linked', 'operation':OPERATION, 'leaving_atom':names['0OH'],
                'partner':{'site':f'A:{i+2}', 'component':'Z99', 'atom_id':names['0N']}, 'symmetry_operation':'x,y,z'}
            deleted.update({names['0OH'], acid_h})
        context = root/f'context-{i}.json'
        context.write_text(json.dumps({'schema_version':1, 'site':f'A:{i+1}', 'ports':ports}))
        for atom, element in zip(values[a+'atom_id'], values[a+'type_symbol']):
            if element not in {'H','D'} and atom not in deleted:
                lines.append(pdb_atom(len(lines)+1, atom, element, 'Z99', f'A:{i+1}'))
        candidate = root/f'candidate-{i}.cif'; project(path, deleted, candidate)
        entries.append({'component':'Z99', 'source':record(path,root), 'context':record(context,root),
                        'candidate':record(candidate,root)})
    model = root/'model.pdb'; model.write_text(''.join(lines)+'END\n')
    manifest = root/'links.json'
    manifest.write_text(json.dumps({'schema_version':1,'workbook':record(book,root),
                                   'model':record(model,root),'sites':entries}))
    return manifest, names


@pytest.mark.parametrize('renamed,isotope,count', [(False,'H',2),(True,'H',2),(False,'D',2),(False,'H',3)])
def test_explicit_neutral_pna_projection_and_reciprocal_links(tmp_path, renamed, isotope, count):
    manifest,names=case(tmp_path,renamed=renamed,isotope=isotope,count=count)
    before=snapshot(tmp_path)
    with patch('subprocess.Popen',side_effect=AssertionError('read only')):
        result=inspect_attachment_links(manifest)
    assert result['policy_id']=='cif-reciprocal-source-links-v2'
    assert result['plan_status']=='PROPOSED' and result['projection_status']=='MATCH'
    assert len(result['links'])==count-1
    assert all(link['kind']=='carboxyl_amine' for link in result['links'])
    assert result['native_qualification']=='NOT_ASSESSED' and not result['automatic_adoption']
    plans=result['permitted_source_projections']
    assert plans['A:1']['deleted_atoms']==sorted([names['0OH'], 'QH' if renamed else 'HA'])
    assert plans[f'A:{count}']['deleted_atoms']==[names['0H0']]
    assert names['0H1'] in plans[f'A:{count}']['retained_atoms']
    assert names['0OH'] in plans[f'A:{count}']['retained_atoms']
    assert names['0H0'] in plans['A:1']['retained_atoms']
    for site, plan in plans.items():
        assert plan['formal_charge_changes']==[] and plan['added_atoms']==[]
        assert plan['retained_stereo_declarations'][names['0F']]=='R'
        assert plan['chemical_state_operations']
        assert all(op['policy_id']==OPERATION for op in plan['chemical_state_operations'])
    assert snapshot(tmp_path)==before


def mutate_source(manifest, change):
    d=json.loads(manifest.read_text()); path=manifest.parent/d['sites'][0]['source']['path']
    values=component_values(path,'Z99'); change(values); write_cif(path,values)
    for entry in d['sites']: entry['source']=record(path,manifest.parent)
    manifest.write_text(json.dumps(d))


@pytest.mark.parametrize('atom,charge', [('0N','1'),('0N','?'),('0OH','-1'),('0A','1'),('0O','-1'),('0H0','1'),('0H1','1'),('HA','1')])
def test_reactive_charge_changes_never_receive_partial_permission(tmp_path,atom,charge):
    manifest,_=case(tmp_path)
    def change(v): v['_chem_comp_atom.charge'][v['_chem_comp_atom.atom_id'].index(atom)]=charge
    mutate_source(manifest,change)
    result=inspect_attachment_links(manifest)
    assert result['plan_status']=='UNRESOLVED'
    assert result['permitted_source_projections'] is None


def test_charged_three_h_amine_is_not_implicitly_neutralized(tmp_path):
    manifest,_=case(tmp_path,charge=1)
    result=inspect_attachment_links(manifest)
    assert result['plan_status']=='UNRESOLVED'
    assert result['site_reports']['A:2']['permitted_source_projection'] is None
    # A charged unreacted terminal N can remain while its other end is proposed.
    first=result['site_reports']['A:1']['permitted_source_projection']
    assert first['retained_formal_charges']['0N']==1
    assert {'0H0','0H1','0H2'}<=set(first['retained_atoms'])


@pytest.mark.parametrize('mode', ['absent_policy','unknown_policy','missing_choice','wrong_h','carbonyl_o','extra_field','nonreciprocal'])
def test_explicit_authority_and_exact_leaving_choice_required(tmp_path,mode):
    manifest,_=case(tmp_path)
    def change(c):
        port=c['ports']['amine']
        if mode=='absent_policy': port.pop('operation'); port.pop('leaving_atom')
        if mode=='unknown_policy': port['operation']='neutralize-anything'
        if mode=='missing_choice': port.pop('leaving_atom')
        if mode=='wrong_h': port['leaving_atom']='HA'
        if mode=='extra_field': port['neutralize']=True
        if mode=='nonreciprocal': c['ports']['amine']={'state':'source'}
    if mode=='carbonyl_o': edit_context(manifest,0,lambda c:c['ports']['carboxyl'].update(leaving_atom='0O'))
    else: edit_context(manifest,1,change)
    if mode=='absent_policy':
        result=inspect_attachment_links(manifest)
        assert result['plan_status']=='UNRESOLVED' and result['permitted_source_projections'] is None
    else:
        with pytest.raises(ValueError): inspect_attachment_links(manifest)


@pytest.mark.parametrize('mode', ['missing_acid_h','extra_carbonyl_h','wrong_n_h_bond','wrong_n_h_parent','leaving_stereo'])
def test_hydrogen_valence_and_stereo_are_explicit(tmp_path,mode):
    manifest,_=case(tmp_path)
    def change(v):
        a='_chem_comp_atom.'; b='_chem_comp_bond.'
        if mode=='missing_acid_h':
            i=v[b+'atom_id_2'].index('HA')
            v[b+'atom_id_1'][i]='0G'
        if mode=='extra_carbonyl_h':
            i=v[b+'atom_id_2'].index('HA'); v[b+'atom_id_1'][i]='0O'
        if mode=='wrong_n_h_bond': v[b+'value_order'][v[b+'atom_id_2'].index('0H1')]='DOUB'
        if mode=='wrong_n_h_parent': v[b+'atom_id_1'][v[b+'atom_id_2'].index('0H1')]='0F'
        if mode=='leaving_stereo': v[a+'pdbx_stereo_config'][v[a+'atom_id'].index('0OH')]='R'
    mutate_source(manifest,change)
    result=inspect_attachment_links(manifest)
    assert result['plan_status']=='UNRESOLVED' and result['permitted_source_projections'] is None


@pytest.mark.parametrize('mode', ['extra_h_loss','charge','stereo','bond','numeric_type'])
def test_candidate_deltas_remain_exact(tmp_path,mode):
    manifest,_=case(tmp_path); d=json.loads(manifest.read_text()); entry=d['sites'][1]
    path=tmp_path/entry['candidate']['path']; v=component_values(path,'Z99'); a='_chem_comp_atom.'
    if mode=='extra_h_loss': project(path,{'0H1'},tmp_path/'bad.cif'); path.write_bytes((tmp_path/'bad.cif').read_bytes())
    else:
        if mode=='charge': v[a+'charge'][v[a+'atom_id'].index('0N')]='1'
        if mode=='stereo': v[a+'pdbx_stereo_config'][v[a+'atom_id'].index('0F')]='S'
        if mode=='bond': v['_chem_comp_bond.value_order'][0]='DOUB'
        if mode=='numeric_type': v[a+'type_energy']=['X']*len(v[a+'atom_id'])
        write_cif(path,v)
    entry['candidate']=record(path,tmp_path); manifest.write_text(json.dumps(d))
    result=inspect_attachment_links(manifest)
    assert result['projection_status']=='MISMATCH' and result['permitted_source_projections'] is None


def test_model_cannot_keep_deleted_hydrogen(tmp_path):
    manifest,_=case(tmp_path); d=json.loads(manifest.read_text()); path=tmp_path/d['model']['path']
    path.write_text(path.read_text().replace('END\n',pdb_atom(999,'0H0','H','Z99','A:2')+'END\n'))
    edit_manifest(manifest,lambda c:c.update(model=record(path,tmp_path)))
    with pytest.raises(ValueError,match='inventory'): inspect_attachment_links(manifest)


def test_public_cli_and_relocated_inputs_are_read_only(tmp_path,capsys):
    original=tmp_path/'original'; original.mkdir(); manifest,_=case(original)
    result=inspect_attachment_links(manifest)
    moved=tmp_path/'moved'; original.rename(moved); before=snapshot(moved)
    with patch('nasolve.cli.discover_phenix') as native, patch('subprocess.Popen',side_effect=AssertionError('no execution')):
        assert main(['cif-doctor','link-plan',str(moved/manifest.name),'--json'])==2
    assert json.loads(capsys.readouterr().out)==result
    assert snapshot(moved)==before and not original.exists()
    native.assert_not_called()
    assert str(tmp_path) not in json.dumps(result)


def test_other_explicit_amine_hydrogen_choice_is_preserved(tmp_path):
    manifest,_=case(tmp_path)
    edit_context(manifest,1,lambda c:c['ports']['amine'].update(leaving_atom='0H1'))
    candidate=tmp_path/'candidate-1.cif'
    project(tmp_path/'source.cif',{'0H1'},candidate)
    edit_manifest(manifest,lambda c:c['sites'][1].update(candidate=record(candidate,tmp_path)))
    result=inspect_attachment_links(manifest)
    assert result['projection_status']=='MATCH'
    plan=result['permitted_source_projections']['A:2']
    assert plan['deleted_atoms']==['0H1'] and '0H0' in plan['retained_atoms']


def test_reactive_stereochemical_declaration_requires_separate_authority(tmp_path):
    manifest,_=case(tmp_path)
    def change(v): v['_chem_comp_atom.pdbx_stereo_config'][v['_chem_comp_atom.atom_id'].index('0N')]='R'
    mutate_source(manifest,change)
    result=inspect_attachment_links(manifest)
    assert result['plan_status']=='UNRESOLVED' and result['permitted_source_projections'] is None
