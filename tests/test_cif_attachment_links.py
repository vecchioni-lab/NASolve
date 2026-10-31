"""Reciprocal source ports and complete declared link scope, without native claims."""
from copy import deepcopy
from hashlib import sha256
import json
from unittest.mock import patch

import pytest

from nasolve.cli import main
from nasolve.cif_attachment_sites import inspect_attachment_site
from nasolve.cif_linked_preparation import component_values
from .test_cif_catalogue import workbook, row, source, snapshot
from .test_cif_attachment_sites import pdb_atom, projected


def record(path, root):
    data = path.read_bytes()
    return {'anchor': 'manifest_directory', 'path': path.relative_to(root).as_posix(),
            'sha256': sha256(data).hexdigest(), 'size': len(data)}


def case(root, codes=('PDU', 'ATL'), *, candidates=True):
    book = workbook(root, [('thymine', row(code)) for code in sorted(set(codes))])
    sources = {code: source(root / 'sources', code) for code in set(codes)}
    model = root / 'model.pdb'; contexts = []; entries = []; lines = []
    for i, code in enumerate(codes):
        site = f'A:{i+1}'; other = f'A:{2-i}'
        leaving = 'OXT' if code == 'ATL' else 'OP3'
        ports = {'phosphate': {'state': 'source'}, 'alcohol': {'state': 'source'}}
        name = 'alcohol' if i == 0 else 'phosphate'
        ports[name] = {'state': 'linked', 'partner': {'site': other, 'component': codes[1-i],
                       'atom_id': 'P' if i == 0 else "O3'"}, 'symmetry_operation': 'x,y,z'}
        if i == 1: ports[name]['leaving_atom'] = leaving
        context = root / f'context-{i}.json'
        context.write_text(json.dumps({'schema_version': 1, 'site': site, 'ports': ports}))
        contexts.append(context)
        values = component_values(sources[code], code)
        atoms = dict(zip(values['_chem_comp_atom.atom_id'], values['_chem_comp_atom.type_symbol']))
        retained = [(a,e) for a,e in atoms.items() if e not in {'H','D'} and not (i == 1 and a == leaving)]
        lines += [pdb_atom(len(lines)+j+1,a,e,code,site) for j,(a,e) in enumerate(retained)]
        entries.append({'component': code, 'source': record(sources[code], root), 'context': record(context, root)})
    model.write_text(''.join(lines)+'END\n')
    if candidates:
        for i, (entry, context) in enumerate(zip(entries, contexts)):
            code = entry['component']; leaving = 'OXT' if code == 'ATL' else 'OP3'
            # Independently declared source H losses for the two public fixtures.
            removed = ({'HA' if code == 'ATL' else 'H2'} if i == 0 else
                       {leaving, 'HXT' if code == 'ATL' else 'HOP3'})
            candidate = projected((sources[code],book,model,context), removed, root/f'candidate-{i}.cif')
            entry['candidate'] = record(candidate, root)
    manifest = root / 'links.json'
    manifest.write_text(json.dumps({'schema_version': 1, 'model': record(model,root),
                                   'workbook': record(book,root), 'sites': entries}))
    return manifest


def inspect(manifest):
    from nasolve.cif_attachment_links import inspect_attachment_links
    return inspect_attachment_links(manifest)


def edit_manifest(manifest, fn):
    data = json.loads(manifest.read_text()); fn(data); manifest.write_text(json.dumps(data))


def edit_context(manifest, index, fn):
    data = json.loads(manifest.read_text()); entry = data['sites'][index]
    path = manifest.parent/entry['context']['path']; context = json.loads(path.read_text()); fn(context)
    path.write_text(json.dumps(context)); entry['context'] = record(path, manifest.parent)
    manifest.write_text(json.dumps(data))


def test_public_link_cli_fails_before_implementation(tmp_path, capsys):
    manifest = case(tmp_path); before = snapshot(tmp_path)
    with patch('nasolve.cli.discover_phenix') as discover, patch('subprocess.Popen') as process:
        assert main(['cif-doctor','link-plan',str(manifest),'--json']) == 2
    result = json.loads(capsys.readouterr().out)
    assert result['binding_status'] == 'BOUND' and result['plan_status'] == 'PROPOSED'
    assert result['projection_status'] == 'MATCH'
    assert result['status'] == 'REVIEW' and result['native_qualification'] == 'NOT_ASSESSED'
    assert not result['automatic_adoption'] and snapshot(tmp_path) == before
    discover.assert_not_called(); process.assert_not_called()


def test_reciprocal_exact_graph_ports_and_terminal_retention(tmp_path):
    result = inspect(case(tmp_path))
    assert len(result['links']) == 1
    link = result['links'][0]
    assert link['kind'] == 'alcohol_phosphate'
    assert link['endpoints'] == [
        {'site':'A:1','component':'PDU','port':'alcohol','atom_id':"O3'"},
        {'site':'A:2','component':'ATL','port':'phosphate','atom_id':'P'}]
    plans = result['permitted_source_projections']
    assert plans['A:1']['deleted_atoms'] == ['H2']
    assert plans['A:2']['deleted_atoms'] == ['HXT','OXT']
    assert 'OP3' in plans['A:1']['retained_atoms']
    assert 'HO2P' in plans['A:2']['retained_atoms']
    assert result['covered_sites'] == ['A:1','A:2']
    assert result['unselected_model_sites'] == []


def test_same_element_wrong_partner_was_not_a_two_end_contract(tmp_path):
    manifest = case(tmp_path)
    edit_context(manifest,1,lambda c:c['ports']['phosphate']['partner'].update(atom_id="O5'"))
    data = json.loads(manifest.read_text()); entry=data['sites'][1]
    # C107 correctly makes no partner-chemistry claim; C108 must close this gap.
    one = inspect_attachment_site(tmp_path/entry['source']['path'],entry['component'],
         workbook=tmp_path/data['workbook']['path'],model=tmp_path/data['model']['path'],context=tmp_path/entry['context']['path'])
    assert one['plan_status'] == 'PROPOSED' and one['partner_chemistry'] == 'NOT_ASSESSED'
    with pytest.raises(ValueError,match='port'): inspect(manifest)


def test_nonreciprocal_declaration_does_not_invent_other_half(tmp_path):
    manifest = case(tmp_path)
    edit_context(manifest,0,lambda c:c['ports'].update(alcohol={'state':'source'}))
    with pytest.raises(ValueError,match='reciprocal'): inspect(manifest)


def test_same_code_requires_one_source_authority(tmp_path):
    manifest = case(tmp_path,('PDU','PDU'))
    assert inspect(manifest)['plan_status'] == 'PROPOSED'
    data = json.loads(manifest.read_text()); original=tmp_path/data['sites'][1]['source']['path']
    second=tmp_path/'different.cif';second.write_bytes(original.read_bytes()+b'\n# distinct authority\n')
    edit_manifest(manifest,lambda d:d['sites'][1].update(source=record(second,tmp_path)))
    with pytest.raises(ValueError,match='source authority'): inspect(manifest)


@pytest.mark.parametrize('mode',['duplicate_site','outside_scope','unknown_field','wrong_anchor','absolute','parent_escape',
                                 'symlink','parent_symlink','stale_hash','stale_size','bool_size','bad_schema','empty','limit'])
def test_manifest_is_explicit_bounded_and_hash_bound(tmp_path, mode):
    manifest=case(tmp_path)
    def change(d):
        ref=d['sites'][0]['source']
        if mode=='duplicate_site': d['sites'].append(deepcopy(d['sites'][0]))
        if mode=='outside_scope': d['sites'].pop()
        if mode=='unknown_field': d['discover_partners']=True
        if mode=='wrong_anchor': ref['anchor']='repository'
        if mode=='absolute': ref['path']=str(tmp_path/ref['path'])
        if mode=='parent_escape': ref['path']='../'+ref['path']
        if mode=='symlink':
            (tmp_path/'alias.cif').symlink_to(tmp_path/ref['path']);ref['path']='alias.cif'
        if mode=='parent_symlink':
            (tmp_path/'alias').symlink_to(tmp_path/'sources',target_is_directory=True);ref['path']=ref['path'].replace('sources/','alias/')
        if mode=='stale_hash':ref['sha256']='0'*64
        if mode=='stale_size':ref['size']+=1
        if mode=='bool_size':ref['size']=True
        if mode=='bad_schema':d['schema_version']=True
        if mode=='empty':d['sites']=[]
        if mode=='limit':d['sites']*=129
    edit_manifest(manifest,change)
    with pytest.raises(ValueError):inspect(manifest)


@pytest.mark.parametrize('mode',['none','partial','mismatch'])
def test_candidate_coverage_never_becomes_silent_qualification(tmp_path,mode):
    manifest=case(tmp_path,candidates=mode!='none')
    if mode=='partial':edit_manifest(manifest,lambda d:d['sites'][0].pop('candidate'))
    if mode=='mismatch':
        # The whole source still contains the receiving leaving O/H.
        edit_manifest(manifest,lambda d:d['sites'][1].update(candidate=deepcopy(d['sites'][1]['source'])))
    result=inspect(manifest)
    assert result['projection_status']=={'none':'NOT_REQUESTED','partial':'PARTIAL_MATCH','mismatch':'MISMATCH'}[mode]
    assert result['plan_status']==('UNRESOLVED' if mode=='mismatch' else 'PROPOSED')
    if mode=='mismatch':assert result['permitted_source_projections'] is None
    assert not result['automatic_adoption']


def test_input_changes_during_composition_cannot_receive_a_receipt(tmp_path):
    import nasolve.cif_attachment_links as module
    manifest=case(tmp_path);original=module.inspect_attachment_site
    def mutate(*args,**kwargs):
        result=original(*args,**kwargs);manifest.write_bytes(manifest.read_bytes()+b'\n');return result
    with patch.object(module,'inspect_attachment_site',mutate),pytest.raises(ValueError,match='changed'):
        inspect(manifest)


def test_fresh_site_report_must_match_manifest_evidence(tmp_path):
    import nasolve.cif_attachment_links as module
    manifest=case(tmp_path);original=module.inspect_attachment_site
    def alter(*args,**kwargs):
        result=original(*args,**kwargs);result['inputs']['model']['sha256']='0'*64;return result
    with patch.object(module,'inspect_attachment_site',alter),pytest.raises(ValueError,match='evidence'):
        inspect(manifest)


def test_exact_relocation_no_original_reads_or_processes(tmp_path):
    original=tmp_path/'original';original.mkdir();manifest=case(original)
    report=inspect(manifest);moved=tmp_path/'moved';original.rename(moved);before=snapshot(moved)
    with patch('subprocess.Popen',side_effect=AssertionError('No subprocess')):
        assert inspect(moved/manifest.name)==report
    assert not original.exists() and snapshot(moved)==before
    assert str(tmp_path) not in json.dumps(report)


def test_duplicate_json_keys_text_summary_and_error(tmp_path,capsys):
    manifest=case(tmp_path)
    assert main(['cif-doctor','link-plan',str(manifest)])==2
    assert 'native linkage remains unqualified' in capsys.readouterr().out
    manifest.write_text(manifest.read_text().replace('"schema_version": 1','"schema_version": 1, "schema_version": 1',1))
    assert main(['cif-doctor','link-plan',str(manifest)])==1
    assert 'Duplicate' in capsys.readouterr().err


@pytest.mark.parametrize('charge',[0,1])
def test_pna_reciprocity_binds_ports_without_inventing_protonation(tmp_path,charge):
    from .test_cif_attachment_profiles import pna
    path=tmp_path/'pna.cif';pna(path,charge=charge)
    book=workbook(tmp_path,[('adenine',row('Z99',N1='BN',C5='BC'))])
    values=component_values(path,'Z99');atoms=[(a,e) for a,e in zip(values['_chem_comp_atom.atom_id'],values['_chem_comp_atom.type_symbol']) if e!='H']
    model=tmp_path/'pna.pdb';lines=[];entries=[]
    for i in range(2):
        site=f'A:{i+1}';other=f'A:{2-i}'
        lines += [pdb_atom(len(lines)+j+1,a,e,'Z99',site) for j,(a,e) in enumerate(atoms)]
        ports={'amine':{'state':'source'},'carboxyl':{'state':'source'}}
        port='carboxyl' if i==0 else 'amine'
        ports[port]={'state':'linked','partner':{'site':other,'component':'Z99','atom_id':'0N' if i==0 else '0A'},'symmetry_operation':'x,y,z'}
        context=tmp_path/f'pna-{i}.json';context.write_text(json.dumps({'schema_version':1,'site':site,'ports':ports}))
        entries.append({'component':'Z99','source':record(path,tmp_path),'context':record(context,tmp_path),'candidate':record(path,tmp_path)})
    model.write_text(''.join(lines)+'END\n')
    manifest=tmp_path/'links.json';manifest.write_text(json.dumps({'schema_version':1,'model':record(model,tmp_path),'workbook':record(book,tmp_path),'sites':entries}))
    report=inspect(manifest)
    assert report['binding_status']=='BOUND' and report['links'][0]['kind']=='carboxyl_amine'
    assert report['plan_status']=='UNRESOLVED' and report['permitted_source_projections'] is None
    assert report['projection_status']=='NOT_ASSESSED'
    assert all(s['source_profile']['ports']['amine']['formal_charge']==charge for s in report['site_reports'].values())


def test_conflicting_nar_authority_blocks_the_whole_network(tmp_path):
    manifest=case(tmp_path)
    book=workbook(tmp_path,[('thymine',row('PDU')),('thymine',row('PDU',N1='C5')),('thymine',row('ATL'))])
    edit_manifest(manifest,lambda d:d.update(workbook=record(book,tmp_path)))
    report=inspect(manifest)
    assert report['binding_status']=='UNRESOLVED' and report['links']==[]
    assert report['permitted_source_projections'] is None
    assert report['projection_status']=='NOT_ASSESSED'


def test_real_partner_outside_scope_is_not_discovered(tmp_path):
    manifest=case(tmp_path);data=json.loads(manifest.read_text());model=tmp_path/data['model']['path']
    model.write_text(model.read_text().replace('END\n',pdb_atom(999,'P','P','DT','A:9')+'END\n'))
    edit_manifest(manifest,lambda d:d.update(model=record(model,tmp_path)))
    edit_context(manifest,0,lambda c:c['ports']['alcohol']['partner'].update(site='A:9',component='DT'))
    with pytest.raises(ValueError,match='outside'):inspect(manifest)


def test_two_sites_cannot_claim_the_same_receiving_port(tmp_path):
    manifest=case(tmp_path);data=json.loads(manifest.read_text());model=tmp_path/data['model']['path']
    lines=model.read_text().splitlines(keepends=True)
    extra=[line[:22]+'   3'+line[26:] for line in lines if line[17:20]=='PDU']
    model.write_text(''.join(lines[:-1]+extra+lines[-1:]))
    entry=deepcopy(data['sites'][0]);context=json.loads((tmp_path/entry['context']['path']).read_text());context['site']='A:3'
    path=tmp_path/'context-3.json';path.write_text(json.dumps(context));entry['context']=record(path,tmp_path)
    edit_manifest(manifest,lambda d:(d.update(model=record(model,tmp_path)),d['sites'].append(entry)))
    with pytest.raises(ValueError,match='reciprocal'):inspect(manifest)


def test_unselected_bystander_is_reported_not_qualified(tmp_path):
    manifest=case(tmp_path);model=tmp_path/'model.pdb'
    model.write_text(model.read_text().replace('END\n',pdb_atom(999,'P','P','DT','A:9')+'END\n'))
    edit_manifest(manifest,lambda d:d.update(model=record(model,tmp_path)))
    report=inspect(manifest)
    assert report['unselected_model_sites']==['A:9'] and report['covered_sites']==['A:1','A:2']
    assert report['plan_status']=='PROPOSED' and len(report['links'])==1


@pytest.mark.parametrize('limit',['MAX_MANIFEST_BYTES','MAX_TOTAL_INPUT_BYTES'])
def test_resource_limits_fail_before_composition(tmp_path,limit):
    import nasolve.cif_attachment_links as module
    manifest=case(tmp_path)
    with patch.object(module,limit,1),patch.object(module,'inspect_attachment_site') as site,pytest.raises(ValueError,match='limit'):
        inspect(manifest)
    site.assert_not_called()


def test_renamed_source_port_and_nonsequential_sites_transfer(tmp_path):
    from Bio.PDB.mmcifio import MMCIFIO
    manifest=case(tmp_path);data=json.loads(manifest.read_text());entry=data['sites'][1]
    values=component_values(tmp_path/entry['source']['path'],'ATL')
    names={atom:f'R{i:03}' for i,atom in enumerate(values['_chem_comp_atom.atom_id'])}
    for role in ['source','candidate']:
        path=tmp_path/entry[role]['path'];v=component_values(path,'ATL')
        for key,column in v.items():
            if '.' in key and key.split('.')[1].startswith('atom_id'):v[key]=[names.get(x,x) for x in column]
        writer=MMCIFIO();writer.set_dict(v);writer.save(str(path));entry[role]=record(path,tmp_path)
    model=tmp_path/data['model']['path'];lines=[]
    for line in model.read_text().splitlines(keepends=True):
        if line.startswith('HETATM'):
            old=line[22:26].strip();chain,resid=('Z',42) if old=='1' else ('B',-3)
            if line[17:20]=='ATL':line=line[:12]+f'{names[line[12:16].strip()]:>4}'+line[16:]
            line=line[:21]+chain+f'{resid:4d}'+line[26:]
        lines.append(line)
    model.write_text(''.join(lines));data['model']=record(model,tmp_path)
    for i,entry in enumerate(data['sites']):
        path=tmp_path/entry['context']['path'];c=json.loads(path.read_text());c['site']='Z:42' if i==0 else 'B:-3'
        port=c['ports']['alcohol' if i==0 else 'phosphate'];port['partner']['site']='B:-3' if i==0 else 'Z:42'
        if i==0:port['partner']['atom_id']=names['P']
        else:port['leaving_atom']=names['OXT']
        path.write_text(json.dumps(c));entry['context']=record(path,tmp_path)
    book=workbook(tmp_path,[('thymine',row('PDU')),('thymine',row('ATL',N1=names['N1'],C5=names['C5']))]);data['workbook']=record(book,tmp_path)
    manifest.write_text(json.dumps(data));report=inspect(manifest)
    assert report['plan_status']=='PROPOSED' and report['projection_status']=='MATCH'
    assert [p['site'] for p in report['links'][0]['endpoints']]==['Z:42','B:-3']
    assert report['links'][0]['endpoints'][1]['atom_id']==names['P']


def test_order_and_identical_source_copies_do_not_change_bound_links(tmp_path):
    manifest=case(tmp_path,('PDU','PDU'));expected=inspect(manifest)
    data=json.loads(manifest.read_text());source_path=tmp_path/data['sites'][0]['source']['path']
    copy=tmp_path/'same-source.cif';copy.write_bytes(source_path.read_bytes())
    data['sites'][0]['source']=record(copy,tmp_path);data['sites'].reverse();manifest.write_text(json.dumps(data))
    report=inspect(manifest)
    assert report['links']==expected['links'] and report['permitted_source_projections']==expected['permitted_source_projections']
    assert len(report['source_authorities'])==1


def test_three_site_chain_composes_middle_site_without_double_counting(tmp_path):
    manifest=case(tmp_path,candidates=False)
    edit_context(manifest,1,lambda c:c['ports'].update(alcohol={'state':'linked',
        'partner':{'site':'A:3','component':'PDU','atom_id':'P'},'symmetry_operation':'x,y,z'}))
    data=json.loads(manifest.read_text());pdu_path=tmp_path/data['sites'][0]['source']['path']
    values=component_values(pdu_path,'PDU');atoms=[(a,e) for a,e in zip(values['_chem_comp_atom.atom_id'],values['_chem_comp_atom.type_symbol']) if e not in {'H','D'} and a!='OP3']
    model=tmp_path/data['model']['path'];extra=''.join(pdb_atom(500+i,a,e,'PDU','A:3') for i,(a,e) in enumerate(atoms))
    model.write_text(model.read_text().replace('END\n',extra+'END\n'));data['model']=record(model,tmp_path)
    context=tmp_path/'context-3.json';context.write_text(json.dumps({'schema_version':1,'site':'A:3','ports':{
        'phosphate':{'state':'linked','leaving_atom':'OP3','partner':{'site':'A:2','component':'ATL','atom_id':"O3'"},'symmetry_operation':'x,y,z'},
        'alcohol':{'state':'source'}}}))
    data['sites'].append({'component':'PDU','source':deepcopy(data['sites'][0]['source']),'context':record(context,tmp_path)})
    manifest.write_text(json.dumps(data));report=inspect(manifest)
    assert report['plan_status']=='PROPOSED' and len(report['links'])==2
    assert report['permitted_source_projections']['A:2']['deleted_atoms']==['HA','HXT','OXT']
    assert report['source_authorities'].keys()=={'PDU','ATL'}


def test_no_link_is_inferred_from_two_nearby_source_states(tmp_path):
    manifest=case(tmp_path,candidates=False)
    for i in range(2):edit_context(manifest,i,lambda c:c.update(ports={'phosphate':{'state':'source'},'alcohol':{'state':'source'}}))
    data=json.loads(manifest.read_text());model=tmp_path/data['model']['path']
    model.write_text(model.read_text().replace('END\n',pdb_atom(999,'OXT','O','ATL','A:2')+'END\n'))
    edit_manifest(manifest,lambda d:d.update(model=record(model,tmp_path)))
    with pytest.raises(ValueError,match='at least one'):inspect(manifest)
