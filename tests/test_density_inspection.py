import base64
import copy
import gzip
import json
import re

import pytest

from nasolve.density_inspection import density_inspection_html, write_density_inspection


def scene():
    return dict(kind='local-backbone-density-display', schema_version=1,
                center=[0, 0, 0], extent=[4, 4, 4],
                atoms=[dict(key=['Z', 9, 'C'], label='Z9 C', element='C', native=[0, 0, 0], full=[0, 1, 0], movement_A=99),
                       dict(key=['Z', 9, 'O'], label='Z9 O', element='O', native=[1, 0, 0], full=[1, 1, 0])],
                bonds=[dict(indices=[0, 1])], layers=dict(native=[], full=[]))


NOTES = dict(title='Model comparison', subtitle='Two supplied states',
             source_note='Saved source, no map available', frame_note='Frame evidence unassessed')


def unpack(page):
    text = re.search(r'<script id="packed" type="application/octet-stream">(.*?)</script>', page, re.S).group(1)
    return json.loads(gzip.decompress(base64.b64decode(text)))


def test_plain_model_comparison_is_offline_and_preserves_inputs_and_coordinates(tmp_path):
    data = scene(); before = copy.deepcopy(data)
    out = tmp_path/'inspection.html'
    write_density_inspection(data, out, **NOTES, model_labels=('Start', 'Endpoint'))
    page = out.read_text(); displayed = unpack(page)
    assert data == before
    assert displayed['atoms'][0]['movement_A'] == 1
    assert displayed['display_labels'] == dict(native='Start', full='Endpoint')
    assert displayed['layers'] == {'native': [], 'full': []}
    assert displayed['atoms'][0]['native'] == before['atoms'][0]['native']
    assert 'connect-src \'none\'' in page
    assert not re.search(r'\b(fetch|XMLHttpRequest|WebSocket)\s*\(', page)
    assert 'No saved density for this map selection' in page
    with pytest.raises(FileExistsError):write_density_inspection(data, out, **NOTES)
    assert out.read_text() == page


def test_labels_and_notes_cannot_execute_html_or_replace_template_tokens():
    attack = '</script><script>alert(1)</script> __PACKED_SCENE__ &'
    data = scene(); data['atoms'][0]['label'] = attack
    page = density_inspection_html(data, **dict(NOTES, title=attack), model_labels=(attack, 'End'))
    assert '</script><script>alert(1)' not in page
    assert '&lt;/script&gt;' in page
    assert unpack(page)['atoms'][0]['label'] == attack
    assert unpack(page)['display_labels']['native'] == attack


@pytest.mark.parametrize('change', [
    lambda s:s.update(schema_version=True),
    lambda s:s.update(atoms=[]),
    lambda s:s['atoms'][0].update(native=[float('nan'), 0, 0]),
    lambda s:s['atoms'][1].update(key=s['atoms'][0]['key']),
    lambda s:s['bonds'][0].update(indices=[0, 2]),
    lambda s:s['bonds'].append(dict(indices=[1, 0])),
    lambda s:s.update(extent=[0, 1, 1]),
    lambda s:s.update(layers={'native': []}),
    lambda s:s['layers'].update(native=[dict(type='mFo-DFc', level=3.5, vertices=[], triangles=[])]),
    lambda s:s.update(atom_samples={'native': {'mFo-DFc': [0, 0]}}),
])
def test_invalid_display_data_fails_before_output_creation(tmp_path, change):
    data = scene(); change(data); out = tmp_path/'bad.html'
    with pytest.raises(ValueError):write_density_inspection(data, out, **NOTES)
    assert not out.exists()


def meshes():
    levels = [('2mFo-DFc', i/2) for i in range(2, 13)]
    levels += [('mFo-DFc', sign*i/2) for i in range(3, 13) for sign in (-1, 1)]
    return [dict(type=kind, level=value, vertices=[0, 0, 0, 1, 0, 0, 0, 1, 0], triangles=[0, 1, 2])
            for kind, value in levels]


def test_saved_meshes_and_signed_samples_are_preserved_exactly():
    data = scene(); data['layers']['native'] = meshes()
    data['atom_samples'] = {'native': {'mFo-DFc': [-4.25, 1.75]}}
    out = unpack(density_inspection_html(data, **NOTES))
    assert out['layers'] == data['layers']
    assert out['atom_samples'] == data['atom_samples']


@pytest.mark.parametrize('change', [
    lambda m:m[0].update(triangles=[0, 1, 99]),
    lambda m:m[0].update(vertices=[0, 0]),
    lambda m:m[0].update(level=2),
])
def test_bad_triangle_or_duplicated_level_is_refused(change):
    data = scene(); data['layers']['native'] = meshes(); change(data['layers']['native'])
    with pytest.raises(ValueError):density_inspection_html(data, **NOTES)


def test_missing_installed_template_does_not_leave_empty_output(tmp_path, monkeypatch):
    import nasolve.density_inspection as module
    monkeypatch.setattr(module, 'files', lambda _:tmp_path/'absent-package')
    out = tmp_path/'view.html'
    with pytest.raises(FileNotFoundError):write_density_inspection(scene(), out, **NOTES)
    assert not out.exists()


@pytest.mark.parametrize('case', ['huge_integer', 'depth', 'crop', 'generated_bands'])
def test_display_envelope_and_generated_work_are_bounded(tmp_path, case):
    data = scene()
    if case == 'huge_integer':
        data['atoms'][0]['native'][0] = 10**400
    elif case == 'depth':
        data['extent'] = [120, 120, 120]
        data['atoms'][0]['native'] = [0, 0, 60]
    elif case == 'crop':
        data['extent'] = [.1, .1, .1]
    else:
        data['extent'] = [80, 80, 80]
        data['layers']['native'] = meshes()
        data['layers']['native'][0]['vertices'] = [-35, 0, 0, 35, 0, 0, 0, 1, 0]
        data['layers']['native'][0]['triangles'] = [0, 1, 2] * 20_000
    out = tmp_path/'over-budget.html'
    with pytest.raises(ValueError):write_density_inspection(data, out, **NOTES)
    assert not out.exists()


def test_map_labels_can_name_a_fixed_control_independently_of_coordinates(tmp_path):
    data = scene(); data['layers']['native'] = meshes()
    before = copy.deepcopy(data)
    page = density_inspection_html(data, **NOTES, model_labels=('Displaced', 'Recovered'),
                                  map_labels=('Relaxed control', 'Unavailable'))
    displayed = unpack(page)
    assert displayed['display_labels'] == dict(native='Displaced', full='Recovered')
    assert displayed['display_map_labels'] == dict(native='Relaxed control', full='Unavailable')
    assert re.search(r'<button id="native"[^>]*>Displaced</button>', page)
    assert '<option value="native">Relaxed control</option>' in page
    assert displayed['layers'] == before['layers'] and displayed['atoms'][0]['native'] == before['atoms'][0]['native']
    assert data == before
    default = unpack(density_inspection_html(data, **NOTES, model_labels=('One', 'Two')))
    assert default['display_map_labels'] == default['display_labels']
    attack = '</option><script>bad()</script> __TITLE__ &'
    escaped = density_inspection_html(data, **NOTES, map_labels=(attack, 'Other'))
    assert '</option><script>bad()' not in escaped
    assert unpack(escaped)['display_map_labels']['native'] == attack
    for invalid in (('Only one',), ('', 'Other'), 'AB', (3, 'Other')):
        target = tmp_path/'invalid.html'
        with pytest.raises(ValueError):write_density_inspection(data, target, **NOTES, map_labels=invalid)
        assert not target.exists()
