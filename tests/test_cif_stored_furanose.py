"""A source-qualified sugar can join the stored bundle without relabelling its chemistry."""
from copy import deepcopy
import shutil

import pytest

from nasolve.cif_dictionary_bundle import prepare_dictionary_bundle, read_dictionary_bundle
from nasolve.cif_dictionary_store import resolve_qualified_dictionary
from nasolve.cif_linked_qualification import site_definition_checks
from tests.test_cif_dictionary_bundle import CONTEXT
from tests.test_cif_dictionary_sites import inputs
from tests.test_cif_furanose_reaction import setup
from tests.test_cif_preparation_qualification import qualification, POLICY


def recipe(tmp_path, *, bridged=True):
    pins = tmp_path/'pins'; pins.mkdir()
    consumer = inputs(pins, terminal=False)['consumer']
    data = tmp_path/'data'; data.mkdir()
    (source, numerical, workbook, model, _), contexts, _ = setup(data, bridged=bridged)
    code = 'Z99'
    if not bridged:
        # The ordinary native phosphodiester owner uses these conventional names.
        from nasolve.cif_stereochemistry_audit import _values
        from tests.test_cif_stereochemistry_audit import write
        names = {'O3':"O3'",'O5':"O5'",'P1':'OP1','P2':'OP2'}
        for path in (source,numerical):
            values = _values(path,code)
            for key in values:
                if 'atom_id' in key:
                    values[key] = [names.get(name,name) for name in values[key]]
            write(path,values)
        lines = []
        for line in model.read_text().splitlines(keepends=True):
            atom = line[12:16].strip()
            if line.startswith(('ATOM  ','HETATM')) and atom in names:
                line = line[:12]+names[atom].rjust(4)+line[16:]
            lines.append(line)
        model.write_text(''.join(lines))
        for port in contexts[0]['ports'].values():
            atom = port['partner']['atom_id']
            port['partner']['atom_id'] = names.get(atom,atom)
    snap = data/'snapshot'
    resolve_qualified_dictionary(source, code, data/'store', snap,
        source_authority='EXPLICIT', recipe={'policy_id':'TEST','bond_representation_policy':POLICY},
        generator={'name':'FAKE','version':'TEST'}, consumer=consumer,
        acquire=lambda:dict(candidate=numerical,qualification=qualification(source,numerical,code),
            provenance={'converged':False,'stopping':'TEST','notes':['synthetic fixture']}))
    site = dict(site='A:11', five_prime_state='linked', three_prime_state='linked',
                incoming_site='A:10', outgoing_site='A:12')
    item = dict(snapshot=snap, contexts=[site], furanose_reaction=dict(workbook=workbook, contexts=contexts))
    return dict(components=[item], model=model, consumer=consumer, native_context=CONTEXT,
                expected_links=[['A:10','A:11'],['A:11','A:12']])


@pytest.mark.parametrize('bridged',[True,False])
def test_stored_furanose_replays_the_source_reaction_after_relocation(tmp_path, bridged):
    args = recipe(tmp_path,bridged=bridged)
    out = tmp_path/'bundle'
    first = prepare_dictionary_bundle(output=out, **args)
    moved = out.rename(tmp_path/'relocated')
    shutil.rmtree(tmp_path/'data')
    bundle = read_dictionary_bundle(moved)
    assert bundle['report']==first and first['native_validation']=='NOT_RUN'
    plan = bundle['preparations'][0]['sites'][0]
    assert plan['expected_native_group']=='non-polymer'
    assert plan['expected_native_classification']==('RNA' if bridged else 'DNA')
    assert plan['source_configuration_projection'] and all(
        row['status']=='RETAINED_SOURCE_NEIGHBORS' for row in plan['source_configuration_projection'])
    assert ('OXT' if bridged else 'OP3') in plan['deleted_atoms']
    assert set(plan['deleted_atoms']).isdisjoint(plan['expected_atoms'])
    assert len(bundle['after_dictionaries'])==2 and len(bundle['after_phils'])==2
    assert bundle['projections']['A:11'][0].is_file()
    assert len(list(moved.rglob('*.xlsx')))==1
    assert first['automatic_adoption'] is False


@pytest.mark.parametrize('fault',['wrong_neighbor','wrong_atom','symmetry','source_port','site','ends','classification','extra_option'])
def test_disagreement_cannot_publish_a_stored_reaction(tmp_path, fault):
    args = recipe(tmp_path)
    item = args['components'][0]
    port = item['furanose_reaction']['contexts'][0]['ports']['phosphate']
    if fault=='wrong_neighbor': port['partner']['site']='A:20'
    if fault=='wrong_atom': port['partner']['atom_id']="O5'"
    if fault=='symmetry': port['symmetry_operation']='-x,y,z'
    if fault=='source_port': port['state']='source'
    if fault=='site': item['furanose_reaction']['contexts']=[]
    if fault=='ends': item['contexts'][0]['five_prime_state']='free_OH'
    if fault=='classification': item['furanose_reaction']['expected_native_group']='DNA'
    if fault=='extra_option': item['phosphate_atom_policy']='cif-source-phosphate-aliases-v1'
    with pytest.raises(ValueError):
        prepare_dictionary_bundle(output=tmp_path/'out',**args)
    assert not (tmp_path/'out').exists()


def test_native_readback_requires_both_frozen_group_and_source_classification():
    plan=dict(site='A:11',expected_native_group='non-polymer',expected_native_classification='RNA',
              expected_atoms=[],expected_energy_types={},expected_formal_charges={},expected_hydrogen_attachments={})
    def check(group,classification,expected):
        metadata=dict(group=group,classification=classification,effective_definition={})
        native={'monomer_mappings':{'rows':[{'site':'A:11','metadata':metadata}]}}
        return {row['check']:row['status'] for row in site_definition_checks(native,[dict(sites=[expected])])}
    key='effective-site-polymer-group:A:11'
    rna=dict(status='RECORDED',value='RNA')
    assert check('non-polymer',rna,plan)[key]=='PASS'
    assert check('DNA',rna,plan)[key]=='REVIEW'
    assert check('non-polymer',dict(status='RECORDED',value='DNA'),plan)[key]=='REVIEW'
    assert check('non-polymer',dict(status='UNSUPPORTED',value='RNA'),plan)[key]=='REVIEW'
    original=deepcopy(plan); del original['expected_native_group'],original['expected_native_classification']
    assert check('non-polymer',rna,original)[key]=='REVIEW'
    assert check('DNA',{},original)[key]=='PASS'
