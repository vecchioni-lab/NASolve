"""An opt-in locked sugar is traceable to the same scaffold, dictionary and pair of neighbours."""
from shutil import rmtree
from unittest.mock import patch

from openpyxl import load_workbook
import pytest

from nasolve.campaign_records import read_record, write_record
from nasolve.cif_dictionary_store import resolve_qualified_dictionary
from nasolve.cif_stereochemistry_audit import _coordinates, _graph, _values
from nasolve.phosphate import sanitize_phosphates
from nasolve.postmr import FURANOSE_METHOD, MutationAction
from nasolve.postmr_furanose import build_substitution, capture_substitution
from nasolve.postmr_lineage import (FURANOSE_POLICY_ID, RECORD_PATH, begin_postmr_construction,
                                    finish_postmr_construction, read_postmr_construction)
from tests.test_cif_base_anchored_furanose import inputs
from tests.test_cif_catalogue import snapshot
from tests.test_cif_complete_request import case
from tests.test_cif_model_context import report
from tests.test_cif_preparation_qualification import POLICY, qualification
from tests.test_cif_stereochemistry_audit import write


def sugar_inputs(root, consumer=None):
    source, candidate, _, workbook, frame, _ = inputs(root, bridged=True)[0]
    host = _values(source, 'Z99')
    for field, column in host.items():
        if field.endswith('.comp_id') or field == '_chem_comp.id':
            host[field] = ['HST'] * len(column)
    host_source = write(root/'host.cif', host)
    book = load_workbook(workbook)
    page = next(sheet for sheet in book if sheet.max_row > 1)
    page.append(['HST', *[cell.value for cell in page[2]][1:]])
    book.save(workbook)
    book.close()
    # Translate two copies so the preceding O3' occupies the virtual leaving
    # oxygen and the following P meets the retained O3'. Only the host is mutated.
    values = _values(candidate, 'Z99')
    xyz = _coordinates(values, source=False)[1]
    elements = _graph(values)[0]
    step = [a-b for a,b in zip(xyz["O3'"], xyz['OXT'], strict=True)]
    lines = []
    for offset, code in [(-1,'X01'), (0,'HST'), (1,'X02')]:
        for atom, point in xyz.items():
            if elements[atom] in {'H','D'} or atom=='OXT' or (offset==-1 and atom in {'P','OP1','OP2'}):
                continue
            position = ''.join(f'{v+offset*s:8.3f}' for v,s in zip(point,step,strict=True))
            lines.append(f'ATOM  {len(lines)+1:5d} {atom:>4} {code:>3} A{11+offset:4d}    '
                         f'{position}  1.00 20.00          {elements[atom]:>2}\n')
    frame.write_text(''.join(lines)+'TER\nEND\n')
    if consumer is None:
        consumer = dict(name='SYNTHETIC',version='TEST',sha256='3'*64)
    directory = root/'snapshot'
    resolve_qualified_dictionary(source,'Z99',root/'store',directory,source_authority='EXPLICIT',
        recipe={'policy_id':'TEST','bond_representation_policy':POLICY}, generator={'name':'FAKE','version':'TEST'},
        consumer=consumer, acquire=lambda: dict(candidate=candidate, qualification=qualification(source,candidate,'Z99'),
            provenance={'converged':False,'stopping':'TEST','notes':['synthetic construction fixture']}))
    return dict(site='A:11',snapshot=directory,host_dictionary=host_source,workbook=workbook), consumer, frame


def sealed(run, selection, consumer, frame):
    choice = capture_substitution(selection, consumer)
    models = run/'PostMR/Model'
    dictionaries = run/'PostMR/Coot/source_dictionaries'
    models.mkdir(parents=True)
    dictionaries.mkdir(parents=True)
    source = dictionaries/'Z99.cif'
    source.write_bytes((choice.snapshot/'entry/source.cif').read_bytes())
    original = models/'mr_solution.pdb'
    original.write_bytes(frame.read_bytes())
    after = models/'after_coot.pdb'
    after.write_bytes(original.read_bytes())
    actions = (MutationAction('A:11', 'HST', 'Z99', FURANOSE_METHOD),)
    started = begin_postmr_construction(run, original, original, {'Z99': source}, actions)
    scaffold = models/'phosphate_checked.pdb'
    sanitize_phosphates(after, scaffold, reference_model=original)
    prepared = models/'prepared_model.pdb'
    build_substitution(choice, scaffold, prepared, run, report())
    return finish_postmr_construction(run,started,prepared,dict(model=after,raw_model=None,coot_log=None))


def test_closed_sugar_construction_keeps_the_source_ports_and_replays_from_its_declared_files(tmp_path, monkeypatch):
    import tempfile
    original = tmp_path/'inputs'
    original.mkdir()
    selection, consumer, frame = sugar_inputs(original)
    # macOS can spell its private temporary root through /var; reproduce this on Linux as well.
    alias = tmp_path/'temp-alias'
    alias.symlink_to(tmp_path, target_is_directory=True)
    monkeypatch.setattr(tempfile,'tempdir',str(alias))
    run = tmp_path/'run'
    with patch('subprocess.Popen',side_effect=AssertionError('Construction replay started an external tool')):
        record = sealed(run,selection,consumer,frame)
        assert record['policy_id'] == FURANOSE_POLICY_ID and not record['automatic_adoption']
        built = read_postmr_construction(run)
        ctx = built['furanose_substitution']['context']
        assert ctx['site'] == 'A:11' and ctx['ports']['phosphate']['leaving_atom'] == 'OXT'
        assert [ctx['ports'][k]['partner']['site'] for k in ('phosphate','alcohol')] == ['A:10','A:12']
        destination = tmp_path/'relocated'
        for name, data in built['files'].items():
            path = destination/name
            path.parent.mkdir(exist_ok=True,parents=True)
            path.write_bytes(data)
        rmtree(original)
        rmtree(run)
        before = snapshot(destination)
        assert read_postmr_construction(destination)['files'] == built['files'] and snapshot(destination) == before
    unrelated = destination/'PostMR/Coot/furanose/snapshot/scratch'
    unrelated.write_bytes(b'not part of the declared dictionary')
    with pytest.raises(ValueError,match='snapshot members'):
        read_postmr_construction(destination)
    unrelated.unlink()
    # A rehashed report still cannot drop the chemical action or substitute another Coot scaffold.
    path = destination/RECORD_PATH
    forged = read_record(path)
    del forged['furanose_substitution']
    forged['policy_id'] = 'postmr-construction-lineage-v1'
    write_record(path,forged,replace=True)
    with pytest.raises(ValueError,match='evidence and construction action'):
        read_postmr_construction(destination)
    forged['controls']['actions'][0]['method'] = 'coot-parent-overlap'
    write_record(path,forged,replace=True)
    with pytest.raises(ValueError,match='model identities'):
        read_postmr_construction(destination)
    from nasolve.postmr_lineage import _reference
    coot = destination/record['outputs']['after_coot']['path']
    coot.write_bytes(b'REMARK different scaffold\n'+coot.read_bytes())
    record['outputs']['after_coot'] = _reference(coot,destination)
    write_record(path,record,replace=True)
    with pytest.raises(ValueError,match='recorded Coot model'):
        read_postmr_construction(destination)


def test_sugar_choice_verifies_the_current_consumer_and_the_selected_workbook(tmp_path):
    selection, consumer, _ = sugar_inputs(tmp_path)
    with pytest.raises(ValueError,match='selected consumer'):
        capture_substitution(selection,dict(consumer,version='DIFFERENT'))
    choice = capture_substitution(selection,consumer)
    selection['workbook'].write_bytes(b'changed after selection')
    with pytest.raises(ValueError,match='inputs changed'):
        choice.verify()


def test_new_publication_rechecks_the_frozen_sugar_against_current_mutation_intent(tmp_path):
    from nasolve.cif_postmr_publication import _check_new_mutation_intent
    from nasolve.postmr import PostMRPreparationError

    selection, consumer, frame = sugar_inputs(tmp_path)
    run = tmp_path/'run'
    request = run/'PostMR/DictionaryEngine/request'
    frozen = request/'inputs/construction'
    sealed(frozen,selection,consumer,frame)
    exact = {'construction_inputs':read_postmr_construction(frozen)}
    current = dict(post_mr_plan=dict(mutations={'A:11':{'ligand_code':'Z99'}}))
    with patch('subprocess.Popen',side_effect=AssertionError('Publication started a process')):
        _check_new_mutation_intent(run,current,request,exact)
        recorded = exact['construction_inputs']
        seed = dict(recorded['furanose_substitution'], unfitted_pairing_edge_seed=True)
        with pytest.raises(ValueError,match='local fit'):
            _check_new_mutation_intent(run,current,request,{'construction_inputs':dict(recorded,furanose_substitution=seed)})
        for mutations in ({'A:11':{'ligand_code':'DT'}}, {'A:12':{'ligand_code':'Z99'}}, {}):
            with pytest.raises((PostMRPreparationError,ValueError)):
                _check_new_mutation_intent(run,dict(post_mr_plan=dict(mutations=mutations)),request,exact)
        with pytest.raises(PostMRPreparationError,match='unmirrored'):
            _check_new_mutation_intent(run,dict(current,inputs=dict(mirror=True)),request,exact)


def test_changed_acquisition_source_refuses_before_allocating_postmr_or_launching_coot(tmp_path, monkeypatch):
    from nasolve import curated_ligands
    from nasolve.cif_ordinary_postmr import initialize_ordinary_postmr_request
    from tests.test_cif_phenix_configuration import configure, sdk_at

    sdk, _ = sdk_at(tmp_path/'sdk')
    selection, _, _ = sugar_inputs(tmp_path,configure(sdk).consumer)
    local = tmp_path/'local'
    (local/'ligands').mkdir(parents=True)
    (local/'ligands/Z99.cif').write_bytes((selection['snapshot']/'entry/source.cif').read_bytes()+b'# changed\n')
    monkeypatch.setattr(curated_ligands,'_registered_record',lambda code: {'Ligand code':code})
    run = tmp_path/'untouched-run'
    with patch('nasolve.postmr._prepare_postmr',side_effect=AssertionError('Coot stage entered')), \
         pytest.raises(ValueError,match='selected chemical source'):
        initialize_ordinary_postmr_request(run,sdk,data_root=local,expected_dialect='CHEMICAL_COMPONENTS_CIF',
                                           furanose_substitution=selection)
    assert not run.exists()


def test_site_only_plan_resolves_the_two_chemical_sources_and_reuses_the_exact_current_dictionary(tmp_path, monkeypatch):
    from pathlib import Path
    from restraints import residue_library
    from nasolve import curated_ligands, postmr
    from nasolve.cif_acquisition_attempt import read_acquisition_result
    from nasolve.cif_dictionary_store import make_dictionary_request, publish_dictionary, resolve_dictionary_snapshot
    from nasolve.cif_generation_acquisition import generation_dictionary_options
    from nasolve.postmr_furanose import plan_catalogue_substitution
    from tests.test_cif_phenix_configuration import configure, sdk_at

    sdk, _ = sdk_at(tmp_path/'sdk')
    cfg = configure(sdk)
    selection, consumer, model = sugar_inputs(tmp_path,cfg.consumer)
    saved = resolve_dictionary_snapshot(selection['snapshot'])
    local = tmp_path/'library'
    (local/'ligands').mkdir(parents=True)
    (local/'ligands/Z99.cif').write_bytes(saved['source'].read_bytes())
    (local/'ligands/HST.cif').write_bytes(selection['host_dictionary'].read_bytes())
    package = tmp_path/'restraints'
    (package/'data').mkdir(parents=True)
    book = package/'data/Ligands.xlsx'
    book.write_bytes(selection['workbook'].read_bytes())
    module_file = package/'residue_library.py'
    module_file.write_bytes(Path(residue_library.__file__).read_bytes())
    monkeypatch.setattr(residue_library,'__file__',str(module_file))
    monkeypatch.setattr(curated_ligands,'_registered_record',lambda code: {'Ligand code':code})
    run = tmp_path/'run'
    intent = dict(post_mr_plan=dict(mutations={'A:11':{'ligand_code':'Z99'}}))
    monkeypatch.setattr(postmr,'_read_report',lambda path:(run,intent))
    monkeypatch.setattr(postmr,'_solution_model',lambda path, report:model)
    store = tmp_path/'catalogue-store'
    plan = plan_catalogue_substitution(run,'A:11',cfg,sdk,store,local,{})
    assert plan.code == 'Z99' and plan.host.name=='HST.cif' and plan.workbook==book
    assert plan.generation['source_input_policy'] == 'cif-source-reader-preparation-v1'
    params = generation_dictionary_options(plan.generation)
    request = make_dictionary_request(plan.source,plan.code,source_authority=plan.source_authority,**params)
    actual = qualification(plan.source,saved['dictionary'],plan.code,policy=plan.generation['bond_representation_policy'])
    expected = publish_dictionary(store,request,plan.source,saved['dictionary'],actual,
                                  consumer=consumer,provenance=saved['provenance'])
    with patch('nasolve.cif_acquisition_attempt.generate_source_candidate_attempt',side_effect=AssertionError('Cache hit regenerated the dictionary')), \
         patch('nasolve.cif_acquisition_attempt.execute_candidate_qualification',side_effect=AssertionError('Cache hit requalified the dictionary')):
        choice = plan.acquire(tmp_path/'acquisition')
    assert choice.entry_id == expected['entry_id']
    assert read_acquisition_result(tmp_path/'acquisition',1)['report']['status']=='REUSED'
    assert not (tmp_path/'acquisition/generation').exists()
    with pytest.raises(ValueError,match='frozen mutation'):
        plan_catalogue_substitution(run,'A:12',cfg,sdk,store,local,{})
    book.write_bytes(b'workbook replaced after planning')
    with pytest.raises(ValueError,match='changed before acquisition'):
        plan.acquire(tmp_path/'never-started')
    assert not (tmp_path/'never-started').exists()


def test_complete_request_binds_the_same_workbook_reaction_and_qualified_component(tmp_path, case):
    from nasolve.cif_acquisition_sources import freeze_acquisition_sources
    from nasolve.cif_model_context import derive_prepared_model_context

    owner, base, output, _, _, generations, calls = case
    origin = tmp_path/'sugar'
    origin.mkdir()
    selection, consumer, frame = sugar_inputs(origin, base['consumer'])
    run = origin/'run'
    sealed(run,selection,consumer,frame)
    built = read_postmr_construction(run)
    placed = built['furanose_substitution']
    local = origin/'local'
    (local/'ligands').mkdir(parents=True)
    (local/'ligands/Z99.cif').write_bytes(placed['snapshot']['source'].read_bytes())
    sources = origin/'sources'
    freeze_acquisition_sources(['Z99'],sources,data_root=local)
    context = derive_prepared_model_context(built['model'],report(),['Z99'])
    generation = dict(next(iter(generations.values())),bond_representation_policy=POLICY)
    reaction = dict(workbook=placed['workbook'],contexts=[placed['context']])
    component = dict(code='Z99',generation=generation,contexts=context['contexts']['Z99'],
                     retained_snapshot=selection['snapshot'],furanose_reaction=reaction)
    args = dict(base,source_selection=sources,components=[component],model=built['model'],model_context=context,
                consumer=consumer,expected_links=context['expected_links'],construction_inputs=run,
                native_context=dict(policy_id='cif-explicit-site-native-context-v2',
                                    monomer_inventory='full_model',custom_restraints='absent'))
    with patch('subprocess.Popen',side_effect=AssertionError('Input verification launched an external tool')):
        changed = origin/'another-workbook.xlsx'
        workbook = load_workbook(placed['workbook'])
        workbook.properties.title = 'Independent workbook with the same atom roles'
        workbook.save(changed)
        workbook.close()
        for i, change in enumerate([dict(furanose_reaction=dict(reaction,workbook=changed)),
                                    dict(furanose_reaction=None),dict(retained_snapshot=None)]):
            target = tmp_path/f'not-sealed-{i}'
            with pytest.raises(ValueError,match='constructed component'):
                owner.initialize_dictionary_request(output=target,**dict(args,components=[dict(component,**change)]))
            assert not (target/'request.json').exists()
        saved = owner.initialize_dictionary_request(output=output,**args)
        assert saved['configuration']['construction_inputs']['policy_id'] == FURANOSE_POLICY_ID
        rmtree(origin)
        moved = output.rename(tmp_path/'cold-complete')
        state = owner.inspect_dictionary_request(moved)
        assert state['availability']=='AVAILABLE' and not state['attempts'] and not calls


def test_explicit_sugar_seed_requires_both_puckers_and_the_compiled_pairing_edge(tmp_path):
    from nasolve.cif_rna_pucker import ETHER_PUCKER_PERMISSION
    from nasolve.cif_whole_furanose import MODEL_EDGE_POLICY_ID
    from nasolve.postmr_furanose import _placement_policy
    from tests.test_cif_pyrimidine_placement import inputs as edge_inputs

    correct = tmp_path/'current'
    correct.mkdir()
    source, _, _, workbook, _ = edge_inputs(correct)
    tables = {m: dict(anchor='phenix_installation',size=120,sha256='1'*64,
        path=f'lib/python3.11/site-packages/chem_data/geostd/rna_dna/mod_{m}.cif')
        for m in ('rna2p','rna3p')}
    permission = dict(policy_id=ETHER_PUCKER_PERMISSION,tables=tables)
    request = dict(component='UY1',recipe=dict(rna_pucker_table=permission))
    selected = dict(source=source,manifest=dict(request=request))
    assert _placement_policy(selected,workbook) == MODEL_EDGE_POLICY_ID
    wrong = tmp_path/'other'
    wrong.mkdir()
    _, _, _, wrong_workbook, _ = edge_inputs(wrong, wrong_edge=True)
    with pytest.raises(ValueError,match='pairing'):
        _placement_policy(selected,wrong_workbook)
    for insufficient in (None, tables['rna2p'], dict(permission,tables={'rna2p':tables['rna2p']})):
        request['recipe'] = dict(rna_pucker_table=insufficient) if insufficient is not None else {}
        with pytest.raises(ValueError,match='pucker|sugar'):
            _placement_policy(selected,workbook)
