"""Source-bound canonical parents retain the incoming sugar and base orientation."""
from pathlib import Path
import math

from Bio.PDB.vectors import Vector, calc_dihedral
import pytest

from nasolve.cif_stereochemistry_audit import _values, _graph, _coordinates
from nasolve.postmr_canonical_seed import canonical_parent_seed
from nasolve.postmr_restoration import _atom_records, source_graph_fragment

FIXTURES = Path(__file__).parent / 'fixtures'


def case(tmp_path, code='PDU', phosphate='internal'):
    source = tmp_path / 'source.cif'
    source.write_bytes((FIXTURES / 'public_ccd' / (code + '.cif')).read_bytes())
    template = tmp_path / 'template.cif'
    template.write_bytes((FIXTURES / 'chemical_reference_DT.cif').read_bytes())
    values = _values(source, code); elements = _graph(values)[0]
    _, xyz = _coordinates(values, source=True)
    remove = {'OP3'} if phosphate == 'internal' else {'P','OP1','OP2','OP3'} if phosphate == 'free' else set()
    rows = []
    for name, element in elements.items():
        if element in {'H','D'} or name in remove:
            continue
        rows.append(f'HETATM{len(rows)+1:5d} {name:>4s} {code:>3s} A   1    '+''.join(f'{x:8.3f}' for x in xyz[name])+f'  0.75 17.00          {element:>2s}\n')
    rows.append('ATOM    901  C1\'  DA B   2       1.000   2.000   3.000  1.00 21.00           C\n')
    model = tmp_path / 'model.pdb'; model.write_text('REMARK retained\n'+''.join(rows)+'END\n')
    return model, source, template


def selected(data, code):
    lines = data.decode().splitlines(keepends=True)
    return _atom_records([l for l in lines if l.startswith(('ATOM  ','HETATM')) and l[21]=='A'], code)


def chi(atoms):
    return math.degrees(calc_dihedral(*(Vector(atoms[n]['xyz']) for n in ["O4'","C1'",'N1','C2'])))


@pytest.mark.parametrize('code', ['PDU','5PC'])
@pytest.mark.parametrize('phosphate', ['internal','free','terminal'])
def test_canonical_seed_preserves_scaffold_and_context_without_name_special_case(tmp_path, code, phosphate):
    model, source, template = case(tmp_path, code, phosphate)
    original = {p:p.read_bytes() for p in (model,source,template)}
    result, report = canonical_parent_seed(model,'A:1',source,code,template,'DT')
    before = selected(original[model],code); after = selected(result,'DT')
    scaffold = set(source_graph_fragment(source,code)['scaffold_atoms']) & before.keys()
    for atom in scaffold | {'N1'}:
        assert before[atom]['xyz'] == after[atom]['xyz']
        assert before[atom]['line'][:17] == after[atom]['line'][:17]
        assert before[atom]['line'][20:] == after[atom]['line'][20:]
    assert set(after) == scaffold | set(source_graph_fragment(template,'DT')['fragment_atoms'])
    assert report['chi_difference_degrees'] < .1
    assert abs((chi(before)-chi(after)+180)%360-180) < .1
    assert report['maximum_template_pair_distance_change_A'] < .002
    assert 'ATOM    901' in result.decode() and result.decode().endswith('END\n')
    assert original == {p:p.read_bytes() for p in original}
    assert (result,report) == canonical_parent_seed(model,'A:1',source,code,template,'DT')
    assert '/Users/' not in str(report) and report['native_qualification'] == 'NOT_RUN'


def test_renamed_source_uses_the_same_graph_rule(tmp_path):
    model, source, template = case(tmp_path)
    source.write_text(source.read_text().replace('PDU','ZZZ'))
    model.write_text(model.read_text().replace('PDU','ZZZ'))
    result, report = canonical_parent_seed(model,'A:1',source,'ZZZ',template,'DT')
    assert selected(result,'DT')['N1']['element'] == 'N'
    assert report['source_component'] == 'ZZZ'


@pytest.mark.parametrize('defect', ['missing_base','extra_atom','partial_phosphate','altloc','wrong_component','wrong_element','mirror','degenerate','duplicate_serial','conect','model_record','hydrogen'])
def test_ambiguous_or_incompatible_model_is_not_relabelled(tmp_path, defect):
    model, source, template = case(tmp_path);lines=model.read_text().splitlines(keepends=True)
    chosen = [i for i,l in enumerate(lines) if l.startswith('HETATM')]
    atom = lambda name:next(i for i in chosen if lines[i][12:16].strip()==name)
    if defect=='missing_base':lines.pop(atom('N3'))
    elif defect=='extra_atom':lines[atom('N3')]=lines[atom('N3')][:12]+' XXX'+lines[atom('N3')][16:]
    elif defect=='partial_phosphate':lines.pop(atom('OP2'))
    elif defect=='altloc':lines[chosen[0]]=lines[chosen[0]][:16]+'A'+lines[chosen[0]][17:]
    elif defect=='wrong_component':lines[chosen[0]]=lines[chosen[0]][:17]+'ZZZ'+lines[chosen[0]][20:]
    elif defect=='wrong_element':lines[atom('N1')]=lines[atom('N1')][:76]+' C\n'
    elif defect=='mirror':
        for i in chosen:lines[i]=lines[i][:30]+f'{-float(lines[i][30:38]):8.3f}'+lines[i][38:]
    elif defect=='degenerate':lines[atom('C2')]=lines[atom('C2')][:30]+lines[atom('N1')][30:54]+lines[atom('C2')][54:]
    elif defect=='duplicate_serial':lines[chosen[1]]=lines[chosen[1]][:6]+lines[chosen[0]][6:11]+lines[chosen[1]][11:]
    elif defect=='conect':lines.insert(0,'CONECT    1    2\n')
    elif defect=='model_record':lines.insert(0,'MODEL        1\n')
    else:lines[atom('N3')]=lines[atom('N3')][:76]+' H\n'
    model.write_text(''.join(lines));before=model.read_bytes()
    with pytest.raises(ValueError):canonical_parent_seed(model,'A:1',source,'PDU',template,'DT')
    assert model.read_bytes()==before


@pytest.mark.parametrize('defect', ['wrong_parent','partial_coordinates','mirror','rna'])
def test_incompatible_template_or_source_fails(tmp_path, defect):
    model, source, template=case(tmp_path);parent='DT'
    if defect=='wrong_parent':parent='DG'
    elif defect=='partial_coordinates':template.write_text(template.read_text().replace('_chem_comp_atom.pdbx_model_Cartn_y_ideal','_chem_comp_atom.not_y'))
    elif defect=='rna':source.write_text(source.read_text().replace('DNA linking','RNA linking'))
    else:
        from nasolve.ligand_profiles import _emit
        values=_values(template,'DT')
        key='_chem_comp_atom.pdbx_model_cartn_x_ideal';values[key]=[str(-float(v)) for v in values[key]]
        template.write_text(_emit(values))
    with pytest.raises(ValueError, match='sugar hand' if defect=='mirror' else None):canonical_parent_seed(model,'A:1',source,'PDU',template,parent)


def test_serials_preserve_unrelated_records_and_do_not_reuse_ter(tmp_path):
    model, source, template = case(tmp_path)
    # PDU lacks DT's C7; a genuinely new atom requires an unused serial.
    text = model.read_text().replace('END\n', 'TER     950       DA B   2\nEND\n')
    model.write_text(text)
    result, _ = canonical_parent_seed(model, 'A:1', source, 'PDU', template, 'DT')
    assert selected(result, 'DT')['C7']['line'][6:11].strip() == '951'
    assert 'TER     950       DA B   2\nEND\n' in result.decode()


def test_source_change_during_construction_is_rejected(tmp_path, monkeypatch):
    import nasolve.postmr_canonical_seed as module
    model, source, template = case(tmp_path)
    original = module._seed
    def changed(*args):
        result = original(*args)
        source.write_bytes(source.read_bytes() + b'\n# concurrent source change\n')
        return result
    monkeypatch.setattr(module, '_seed', changed)
    with pytest.raises(ValueError, match='input changed'):
        canonical_parent_seed(model, 'A:1', source, 'PDU', template, 'DT')


@pytest.mark.parametrize('bad_site', ['A:1A', 'AB:1', 'A:999', 'A:', 'A:1:2'])
def test_only_an_exact_unambiguous_site_is_accepted(tmp_path, bad_site):
    model, source, template = case(tmp_path)
    with pytest.raises(ValueError):
        canonical_parent_seed(model, bad_site, source, 'PDU', template, 'DT')


def test_selected_ter_follows_the_new_component_identity(tmp_path):
    model, source, template = case(tmp_path)
    model.write_text(model.read_text().replace('ATOM    901', 'TER     900      PDU A   1\nATOM    901'))
    output, _ = canonical_parent_seed(model, 'A:1', source, 'PDU', template, 'DT')
    assert 'TER     900       DT A   1\n' in output.decode()


def test_decimal_serial_exhaustion_does_not_overwrite_existing_atoms(tmp_path):
    model, source, template = case(tmp_path)
    model.write_text(model.read_text().replace('ATOM    901', 'ATOM  99999'))
    with pytest.raises(ValueError, match='serial capacity'):
        canonical_parent_seed(model, 'A:1', source, 'PDU', template, 'DT')


def test_bare_chain_terminators_are_retained(tmp_path):
    model, source, template = case(tmp_path)
    model.write_text(model.read_text().replace('ATOM    901', 'TER\nATOM    901'))
    output, _ = canonical_parent_seed(model, 'A:1', source, 'PDU', template, 'DT')
    assert 'TER\nATOM    901' in output.decode()


def test_immutable_bytes_match_path_construction_exactly(tmp_path):
    model, source, template = case(tmp_path)
    assert canonical_parent_seed(model.read_bytes(), 'A:1', source, 'PDU', template, 'DT') == canonical_parent_seed(model, 'A:1', source, 'PDU', template, 'DT')
