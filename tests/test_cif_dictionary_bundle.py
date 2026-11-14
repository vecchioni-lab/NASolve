"""Frozen multi-component contracts; synthetic inputs do not qualify chemistry."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import shutil
import pytest

CONTEXT=dict(policy_id='cif-explicit-site-native-context-v2',custom_restraints='absent',monomer_inventory='full_model')


def fixture(tmp_path,consumer=None):
    from tests.test_cif_dictionary_sites import inputs
    from tests.test_cif_preparation_qualification import qualification
    from nasolve.cif_dictionary_store import resolve_dictionary_snapshot,resolve_qualified_dictionary
    first=tmp_path/'first';first.mkdir();a=inputs(first,terminal=False)
    saved=resolve_dictionary_snapshot(a['snapshot'])
    if consumer is not None:
        resolve_qualified_dictionary(saved['source'],'ZZZ',tmp_path/'selected-store',tmp_path/'selected-snapshot',
            source_authority='EXPLICIT',recipe=saved['manifest']['request']['recipe'],
            generator=dict(name='FAKE',version='TEST'),consumer=consumer,
            acquire=lambda:dict(candidate=saved['dictionary'],qualification=saved['qualification'],
                provenance=dict(converged=False,stopping='TEST',notes=['Synthetic selected consumer.'])))
        a['snapshot']=tmp_path/'selected-snapshot';a['consumer']=consumer
        saved=resolve_dictionary_snapshot(a['snapshot'])
    other=tmp_path/'second';other.mkdir()
    source=other/'source.cif';candidate=other/'candidate.cif'
    source.write_bytes(saved['source'].read_bytes().replace(b'ZZZ',b'YYY'))
    candidate.write_bytes(saved['dictionary'].read_bytes().replace(b'ZZZ',b'YYY'))
    resolve_qualified_dictionary(source,'YYY',other/'store',other/'snapshot',source_authority='EXPLICIT',
        recipe=saved['manifest']['request']['recipe'],generator=dict(name='FAKE',version='TEST'),consumer=a['consumer'],
        acquire=lambda:dict(candidate=candidate,qualification=qualification(source,candidate,'YYY'),
            provenance=dict(converged=False,stopping='TEST',notes=['Synthetic fixture.'])))
    lines=[l for l in a['model'].read_text().splitlines() if l.startswith(('ATOM  ','HETATM'))]
    copied=[l[:17]+'YYY'+l[20:21]+'B'+l[22:38]+f'{101.:8.3f}'+l[46:] for l in lines]
    model=tmp_path/'model.pdb';model.write_text('\n'.join(l[:6]+str(i+1).rjust(5)+l[11:] for i,l in enumerate(lines+copied))+'\nEND\n')
    contexts=[{k:(v.replace('A:','B:') if isinstance(v,str) else v) for k,v in c.items()} for c in a['contexts']]
    return dict(components=[dict(snapshot=a['snapshot'],contexts=a['contexts']),dict(snapshot=other/'snapshot',contexts=contexts)],
        model=model,consumer=a['consumer'],expected_links=[['A:1','A:2'],['B:1','B:2']],native_context=CONTEXT)


def test_multi_component_bundle_freezes_one_order_and_replays_cold(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle
    args=fixture(tmp_path);out=tmp_path/'bundle';r=prepare_dictionary_bundle(output=out,**args)
    assert r['components']==['YYY','ZZZ'] and r['automatic_adoption'] is False
    b=read_dictionary_bundle(out)
    assert set(b['projections'])=={'A:1','A:2','B:1','B:2'}
    assert len(b['preparations'])==2 and len(b['before_dictionaries'])==2
    assert len(b['after_dictionaries'])==4
    assert b['native_options']==dict(full_monomer_inventory=True)
    frozen={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    out.rename(tmp_path/'moved');out=tmp_path/'moved'
    for name in ['first','second']:shutil.rmtree(tmp_path/name)
    args['model'].unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Reader must not execute')):
        assert read_dictionary_bundle(out)['report']==r
    assert all(((out/p).read_bytes(),(out/p).stat().st_mtime_ns)==value for p,value in frozen.items())


@pytest.mark.parametrize('defect',['duplicate','missing_site','wrong_site','missing_link','bad_context','consumer'])
def test_ambiguous_or_inconsistent_components_do_not_publish(tmp_path,defect):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle
    args=fixture(tmp_path)
    if defect=='duplicate':args['components'][1]=deepcopy(args['components'][0])
    if defect=='missing_site':args['components'][0]['contexts'].pop()
    if defect=='wrong_site':args['components'][1]['contexts'][0]['site']='A:1'
    if defect=='missing_link':args['expected_links'].pop()
    if defect=='bad_context':args['native_context']={**CONTEXT,'monomer_inventory':'guess'}
    if defect=='consumer':args['consumer']['version']='other'
    with pytest.raises(ValueError):prepare_dictionary_bundle(output=tmp_path/'out',**args)
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('defect',['model','component_order','extra_file','rehashed_combined','rehashed_policy',
    'ownership','false_adoption','context','link','symlink'])
def test_readback_rederives_bundle_ownership_and_bytes(tmp_path,defect):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle,_files
    args=fixture(tmp_path);out=tmp_path/'bundle';prepare_dictionary_bundle(output=out,**args)
    p=out/'bundle_receipt.json';r=json.loads(p.read_text())
    if defect=='model':(out/'inputs/model.pdb').write_bytes(args['model'].read_bytes()+b'REMARK changed\n')
    if defect=='component_order':r['components'].reverse()
    if defect=='extra_file':(out/'unexpected').write_text('unrequested')
    if defect=='rehashed_combined':(out/'prepared/dictionaries.cif').write_text('data_bad\n')
    if defect=='rehashed_policy':(out/'prepared/native_interpretation.phil').write_text('pdb_interpretation.use_ncs_to_build_restraints=True')
    if defect=='ownership':r['site_owners']['A:1']='YYY'
    if defect=='false_adoption':r['automatic_adoption']=True
    if defect=='context':r['native_context']['custom_restraints']='required'
    if defect=='link':r['expected_links'].pop()
    if defect=='symlink':
        q=out/'inputs/model.pdb';q.unlink();q.symlink_to(args['model'])
    if defect in {'rehashed_combined','rehashed_policy','extra_file'}:r['files']=_files(out)
    p.write_text(json.dumps(r))
    with pytest.raises((ValueError,OSError)):read_dictionary_bundle(out)


def test_inactive_modifier_placeholders_are_not_registered_as_inputs(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle
    args=fixture(tmp_path)
    args['model'].write_text(''.join(l for l in args['model'].read_text().splitlines(keepends=True)
        if not l.startswith(('ATOM  ','HETATM')) or l[22:26].strip()=='1'))
    for component in args['components']:
        ctx=next(c for c in component['contexts'] if c['site'].endswith(':1'))
        component['contexts']=[{**ctx,'outgoing_site':None,'three_prime_state':'free_OH'}]
    args['expected_links']=[]
    prepare_dictionary_bundle(output=tmp_path/'bundle',**args)
    b=read_dictionary_bundle(tmp_path/'bundle')
    assert len(b['after_dictionaries'])==2 and len(b['after_phils'])==1
    assert all(not p['modification_id'] for r in b['preparations'] for p in r['sites'])


def test_conflicting_component_modifiers_are_refused(tmp_path,monkeypatch):
    import nasolve.cif_dictionary_bundle as module
    original=module.read_dictionary_sites
    def conflicting(path):
        child=original(path)
        child['preparation']['sites'][0]['modification_id']='DUPLICATE'
        return child
    monkeypatch.setattr(module,'read_dictionary_sites',conflicting)
    args=fixture(tmp_path)
    with pytest.raises(ValueError,match='Conflicting site modifier'):
        module.prepare_dictionary_bundle(output=tmp_path/'out',**args)
    assert not (tmp_path/'out').exists()


def select_single_component(args, tmp_path):
    """Declare one synthetic component, retaining both of its linked sites."""
    args=deepcopy(args);args['components']=args['components'][:1]
    args['model'].write_text(''.join(line for line in args['model'].read_text().splitlines(keepends=True)
        if not line.startswith(('ATOM  ','HETATM')) or line[21]=='A'))
    args['expected_links']=[['A:1','A:2']]
    if 'source_selection' in args:
        from nasolve.cif_acquisition_sources import freeze_acquisition_sources
        args['source_selection']=tmp_path/'single-sources'
        freeze_acquisition_sources(['ZZZ'],args['source_selection'],data_root=tmp_path/'data')
    return args


def test_single_component_keeps_all_sites_and_replays_without_originals(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle
    args=select_single_component(fixture(tmp_path),tmp_path);out=tmp_path/'bundle'
    report=prepare_dictionary_bundle(output=out,**args);loaded=read_dictionary_bundle(out)
    assert report['components']==['ZZZ'] and report['site_owners']=={'A:1':'ZZZ','A:2':'ZZZ'}
    assert report['expected_links']==[['A:1','A:2']] and report['automatic_adoption'] is False
    assert len(loaded['before_dictionaries'])==1 and len(loaded['after_dictionaries'])==2
    assert len(loaded['after_phils'])==2 and loaded['native_options']==dict(full_monomer_inventory=True)
    frozen={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    out=out.rename(tmp_path/'relocated');shutil.rmtree(tmp_path/'first');shutil.rmtree(tmp_path/'second');args['model'].unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Read-only replay')):
        assert read_dictionary_bundle(out)['report']==report
    assert all(((out/p).read_bytes(),(out/p).stat().st_mtime_ns)==v for p,v in frozen.items())


@pytest.mark.parametrize('count',[0,17])
def test_composer_keeps_empty_and_oversized_requests_out(tmp_path,count):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle
    args=fixture(tmp_path);args['components']=[args['components'][0]]*count;out=tmp_path/'bundle'
    with pytest.raises(ValueError):prepare_dictionary_bundle(output=out,**args)
    assert not out.exists()


def _legacy_combination_fixture(root):
    """Build synthetic pre-C179 bytes; never alter a historical live artifact."""
    from nasolve.cif_dictionary_bundle import read_dictionary_bundle, _files
    from nasolve.ligand_profiles import combine_dictionary_inputs
    b=read_dictionary_bundle(root)
    from nasolve.cif_dictionary_sites import read_dictionary_sites
    children=[read_dictionary_sites(root/'components'/c) for c in b['report']['components']]
    for filename,inputs in [('sources.cif',[c['snapshot']['source'] for c in children]),
                            ('dictionaries.cif',[c['after_dictionaries'][0] for c in children])]:
        p=root/'prepared'/filename;p.unlink();combine_dictionary_inputs(inputs,p,component_list_policy=None)
    r=b['report'];r.pop('component_list_policy');r['files']=_files(root)
    (root/'bundle_receipt.json').write_text(json.dumps(r))
    return r


def test_singleton_bundle_declares_native_metadata_loop_policy(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle
    from nasolve.ligand_profiles import _blocks,COMPONENT_LIST_POLICY
    args=select_single_component(fixture(tmp_path),tmp_path);out=tmp_path/'bundle'
    r=prepare_dictionary_bundle(output=out,**args);b=read_dictionary_bundle(out)
    assert r['component_list_policy']==COMPONENT_LIST_POLICY
    assert '\nloop_\n_chem_comp.' in _blocks(b['dictionary'])[0].text
    assert _blocks(b['dictionary'])[0].values['_chem_comp.group']==['DNA']


def test_legacy_scalar_bundle_replays_cold_without_rewriting(tmp_path):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle
    from nasolve.ligand_profiles import _blocks
    args=select_single_component(fixture(tmp_path),tmp_path);out=tmp_path/'bundle'
    prepare_dictionary_bundle(output=out,**args);r=_legacy_combination_fixture(out)
    before={p.relative_to(out):(p.read_bytes(),p.stat().st_mtime_ns) for p in out.rglob('*') if p.is_file()}
    out=out.rename(tmp_path/'relocated');shutil.rmtree(tmp_path/'first');shutil.rmtree(tmp_path/'second');args['model'].unlink()
    with patch('subprocess.Popen',side_effect=AssertionError('Replay executed')):
        b=read_dictionary_bundle(out)
    assert b['report']==r and 'component_list_policy' not in r
    assert '\nloop_\n_chem_comp.' not in _blocks(b['dictionary'])[0].text
    assert all(((out/p).read_bytes(),(out/p).stat().st_mtime_ns)==v for p,v in before.items())


@pytest.mark.parametrize('defect', ['unknown','null','stripped','legacy_promoted'])
def test_combination_policy_cannot_relabel_old_or_new_evidence(tmp_path,defect):
    from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle,read_dictionary_bundle
    from nasolve.ligand_profiles import COMPONENT_LIST_POLICY
    args=select_single_component(fixture(tmp_path),tmp_path);out=tmp_path/'bundle'
    r=prepare_dictionary_bundle(output=out,**args)
    if defect=='legacy_promoted':r=_legacy_combination_fixture(out);r['component_list_policy']=COMPONENT_LIST_POLICY
    elif defect=='stripped':r.pop('component_list_policy')
    else:r['component_list_policy']='unreviewed' if defect=='unknown' else None
    (out/'bundle_receipt.json').write_text(json.dumps(r))
    with pytest.raises(ValueError):read_dictionary_bundle(out)
