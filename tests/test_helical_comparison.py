"""Explicit state identity, partial correspondence and local geometry changes."""
from dataclasses import replace
from hashlib import sha256
import json
import math
from pathlib import Path
import pytest

from nasolve.helical_geometry import HelicalSite, DeclaredPair, PairedRegion
from nasolve.helical_comparison import HelicalState, PairCorrespondence, compare_helical_states
from .helpers import pdb_record


def region(offset=0, chains=('A', 'B'), prefix='p'):
    return PairedRegion('edge', tuple(DeclaredPair(f'{prefix}{i}',
        HelicalSite(chains[0], offset+i, 'DA'),
        HelicalSite(chains[1], offset+4-i, 'DT')) for i in range(1, 4)))


def phosphates(declaration, widths=(10, 12, 14)):
    lines = []
    for i, (pair, width) in enumerate(zip(declaration.pairs, widths)):
        for site, x in ((pair.strand_i, 0), (pair.strand_ii, width)):
            lines.append(pdb_record('ATOM', len(lines)+1, 'P', site.component,
                site.chain, site.residue_number, x=x, y=0, z=3*i))
    return ''.join(lines)


def state(tmp_path, name, declaration=None, text=None):
    declaration = declaration or region()
    path = tmp_path/f'{name}.pdb'
    path.write_text(phosphates(declaration) if text is None else text)
    return HelicalState(name, path, declaration, sha256(path.read_bytes()).hexdigest())


def mappings(reference, candidate):
    return tuple(PairCorrespondence(f'logical-{i}', a.pair_id, b.pair_id)
        for i, (a, b) in enumerate(zip(reference.region.pairs, candidate.region.pairs)))


def compare(reference, candidate, correspondence=None, **kwargs):
    return compare_helical_states(reference, candidate,
        correspondence=mappings(reference, candidate) if correspondence is None else correspondence,
        strand_correspondence='I_TO_I_II_TO_II', **kwargs)


def test_renumbered_split_chain_sites_are_explicit_and_source_bound(tmp_path):
    a = state(tmp_path, 'parent')
    b = state(tmp_path, 'candidate', region(100, ('X', 'Z'), 'q'))
    r = compare(a, b, include_half_span=True)
    assert [p['phosphate_span']['delta'] for p in r['pairs']] == [0, 0, 0]
    assert [p['half_span']['delta'] for p in r['pairs']] == [0, 0, 0]
    assert r['states']['candidate']['region']['pairs'][0]['strand_i']['residue_number'] == 101
    assert r['correspondence_authority'] == 'CALLER_DECLARED'
    assert r['physical_correspondence_validated'] is False
    assert r['runtime_authority'] is False and r['coordinate_changes'] is False
    assert r['axis_radii']['status'] == r['helix_bending']['status'] == 'NOT_MEASURED'
    assert str(tmp_path) not in json.dumps(r)
    assert json.loads(json.dumps(r, allow_nan=False)) == r


def test_phosphate_change_and_missing_mapping_are_not_silently_zero(tmp_path):
    a = state(tmp_path, 'parent')
    b = state(tmp_path, 'candidate', text=phosphates(region(), (11, 12, 14)))
    rows = (PairCorrespondence('left', 'p1', 'p1'),
            PairCorrespondence('missing', 'p2', None),
            PairCorrespondence('new', None, 'p2'),
            PairCorrespondence('right', 'p3', 'p3'))
    r = compare(a, b, rows)
    assert [p['phosphate_span']['delta'] for p in r['pairs']] == [1, None, None, 0]
    assert r['pairs'][1]['phosphate_span']['reason'] == 'CANDIDATE_PAIR_UNMAPPED'
    assert r['pairs'][2]['phosphate_span']['reason'] == 'REFERENCE_PAIR_UNMAPPED'
    assert r['coverage']['matched_pairs'] == 2
    assert all(s['logical_pair_ids'] != ['left', 'right'] for s in r['steps'])


def test_missing_atom_retains_per_state_reason(tmp_path):
    a = state(tmp_path, 'parent')
    text = phosphates(region()).splitlines(keepends=True)
    text[1] = text[1][:12]+" C1'"+text[1][16:]
    b = state(tmp_path, 'candidate', text=''.join(text))
    r = compare(a, b)
    row = r['pairs'][0]['phosphate_span']
    assert row['delta'] is None and row['reference_value'] == 10
    assert row['candidate_status'] == 'UNAVAILABLE'
    assert r['states']['candidate']['pairs'][0]['phosphates'][1]['reason'] == 'MISSING_PHOSPHATE'
    assert r['pairs'][1]['phosphate_span']['delta'] == 0


def test_component_and_role_changes_are_visible_not_canonicalized(tmp_path):
    a = state(tmp_path, 'parent')
    d = region(); d = replace(d, pairs=(replace(d.pairs[0], role='flank',
        strand_ii=replace(d.pairs[0].strand_ii, component='PDU')), *d.pairs[1:]))
    b = state(tmp_path, 'candidate', d)
    r = compare(a, b)
    assert r['pairs'][0]['component_changes'] == ['strand_ii']
    assert r['pairs'][0]['role_changed'] is True
    assert r['pairs'][0]['phosphate_span']['delta'] == 0


@pytest.mark.parametrize('fault', ['omit', 'unknown', 'reuse', 'duplicate', 'empty', 'both_missing', 'policy', 'same_name'])
def test_ambiguous_or_incomplete_declarations_refuse(tmp_path, fault):
    a, b = state(tmp_path, 'parent'), state(tmp_path, 'candidate')
    m = list(mappings(a, b)); kwargs = {}
    if fault == 'omit': m.pop()
    if fault == 'unknown': m[0] = replace(m[0], candidate_pair_id='not-present')
    if fault == 'reuse': m[0] = replace(m[0], candidate_pair_id='p2')
    if fault == 'duplicate': m[0] = replace(m[0], logical_pair_id=m[1].logical_pair_id)
    if fault == 'empty': m = []
    if fault == 'policy': kwargs['strand_correspondence'] = 'guess'
    if fault == 'same_name': b = replace(b, name=a.name)
    with pytest.raises(ValueError):
        if fault == 'both_missing': PairCorrespondence('none', None, None)
        else: compare_helical_states(a, b, correspondence=m,
            **{'strand_correspondence': 'I_TO_I_II_TO_II', **kwargs})


def test_state_drift_after_first_measurement_refuses(tmp_path, monkeypatch):
    import nasolve.helical_comparison as module
    a, b = state(tmp_path, 'parent'), state(tmp_path, 'candidate')
    original = module.inspect_phosphate_spans
    def reader(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if Path(path) == b.model_path: a.model_path.write_text('END\n')
        return result
    monkeypatch.setattr(module, 'inspect_phosphate_spans', reader)
    with pytest.raises(ValueError, match='changed'):
        compare(a, b)


def twist_states(tmp_path, first=30, second=30):
    pytest.importorskip('gemmi')
    from .test_helical_twist import model, region as twist_region
    return (state(tmp_path, 'parent', twist_region(), model(first)),
            state(tmp_path, 'candidate', twist_region(), model(second)))


def test_wrap_safe_twist_changes_and_reverse_comparison(tmp_path):
    a, b = twist_states(tmp_path, 179, -179)
    r = compare(a, b, simple_twist=True, max_ring_fit_rmsd_angstrom=.15)
    reverse = compare(b, a, simple_twist=True, max_ring_fit_rmsd_angstrom=.15)
    assert [s['simple_step_twist']['delta'] for s in r['steps']] == pytest.approx([2, 2], abs=.02)
    assert [s['simple_step_twist']['delta'] for s in reverse['steps']] == pytest.approx([-2, -2], abs=.02)


def test_breaks_reordering_and_half_turn_changes_are_unavailable(tmp_path):
    # Serialized coordinates may leave tiny deviations from 180; a controlled
    # +/-90 model has exact opposite C1 directions at PDB precision.
    a, b = twist_states(tmp_path, 90, -90)
    r = compare(a, b, simple_twist=True, max_ring_fit_rmsd_angstrom=.15)
    assert all(s['simple_step_twist']['reason'] == 'AMBIGUOUS_ANGLE_DELTA' for s in r['steps'])
    d = b.region; b = replace(b, region=replace(d, pairs=(d.pairs[0],replace(d.pairs[1],break_before=True),d.pairs[2])))
    r = compare(a, b, simple_twist=True, max_ring_fit_rmsd_angstrom=.15)
    assert r['steps'][0]['simple_step_twist']['candidate_reason'] == 'DECLARED_BREAK'
    b = replace(b, region=replace(d, pairs=tuple(reversed(d.pairs))))
    mapping = tuple(PairCorrespondence(p.pair_id,p.pair_id,p.pair_id) for p in a.region.pairs)
    r = compare(a, b, mapping, simple_twist=True, max_ring_fit_rmsd_angstrom=.15)
    assert all(s['simple_step_twist']['delta'] is None for s in r['steps'])
    assert len(r['steps']) == 4  # Reversed adjacency is retained, not sign-guessed.


def test_single_pair_rotation_changes_only_its_two_neighbor_steps(tmp_path):
    a, b = twist_states(tmp_path)
    lines = []
    for line in b.model_path.read_text().splitlines(keepends=True):
        if line[21:26] in ('A   2', 'B   2'):
            x,y = float(line[30:38]),float(line[38:46]);t=math.radians(10)
            line=line[:30]+f'{math.cos(t)*x-math.sin(t)*y:8.3f}{math.sin(t)*x+math.cos(t)*y:8.3f}'+line[46:]
        lines.append(line)
    b.model_path.write_text(''.join(lines));b=replace(b,expected_model_sha256=sha256(b.model_path.read_bytes()).hexdigest())
    r=compare(a,b,simple_twist=True,max_ring_fit_rmsd_angstrom=.15)
    assert [s['simple_step_twist']['delta']for s in r['steps']]==pytest.approx([10,-10],abs=.02)
    assert [p['phosphate_span']['delta']for p in r['pairs']]==pytest.approx([0,0,0],abs=.002)


def test_relocation_preserves_report(tmp_path):
    a,b=state(tmp_path,'parent'),state(tmp_path,'candidate')
    expected=compare(a,b)
    moved=tmp_path/'relocated';moved.mkdir()
    for s in (a,b):s.model_path.rename(moved/s.model_path.name)
    actual=compare(replace(a,model_path=moved/a.model_path.name),replace(b,model_path=moved/b.model_path.name))
    assert actual==expected


def stacking_compare(a,b,correspondence=None,**kw):
 return compare(a,b,correspondence,simple_twist=True,max_ring_fit_rmsd_angstrom=.15,include_stacking=True,**kw)


def test_stacking_comparison_preserves_defaults_and_explicit_renaming(tmp_path):
 from .test_helical_twist import model, _translate_pairs
 a,b=twist_states(tmp_path,0,0)
 text=_translate_pairs(model(angle=0),{2:(2,0,0),3:(4,0,0)})
 text=''.join(l[:21]+('X'if l[21]=='A'else'Z')+f'{int(l[22:26])+100:4d}'+l[26:]for l in text.splitlines(keepends=True))
 b=state(tmp_path,'candidate',region(100,('X','Z'),'q'),text)
 plain=compare(a,b,simple_twist=True,max_ring_fit_rmsd_angstrom=.15)
 r=stacking_compare(a,b);reverse=stacking_compare(b,a)
 for step,back in zip(r['steps'],reverse['steps']):
  assert [row['strand']for row in step['stacking_geometry']]==['strand_i','strand_ii']
  for row,rev in zip(step['stacking_geometry'],back['stacking_geometry']):
   assert row['lateral_offset_angstrom']['delta']==pytest.approx(2)
   assert rev['lateral_offset_angstrom']['delta']==pytest.approx(-2)
   assert row['normal_spacing_angstrom']['delta']==pytest.approx(0)
   assert row['plane_angle_deg']['delta']==pytest.approx(0,abs=1e-6)
 assert r['coverage']['stacking_changes']==dict(plane_angle_deg=4,centroid_distance_angstrom=4,normal_spacing_angstrom=4,lateral_offset_angstrom=4)
 # No default mutation or silent report migration.
 for embedded in r['states'].values():embedded.pop('stacking_geometry')
 for step in r['steps']:step.pop('stacking_geometry')
 r['coverage'].pop('stacking_changes');r.pop('stacking_delta_convention')
 assert r==plain


@pytest.mark.parametrize('fault',['missing_atom','break','reversed','unmapped'])
def test_stacking_comparison_respects_missing_strands_and_directed_adjacency(tmp_path,fault):
 a,b=twist_states(tmp_path);mapping=None
 if fault=='missing_atom':
  text=''.join(l for l in b.model_path.read_text().splitlines(keepends=True)if not(l[21:26]=='A   2'and l[12:16].strip()=='N9'))
  b=state(tmp_path,'candidate',b.region,text)
 if fault=='break':b=replace(b,region=replace(b.region,pairs=(b.region.pairs[0],replace(b.region.pairs[1],break_before=True),b.region.pairs[2])))
 if fault=='reversed':
  b=replace(b,region=replace(b.region,pairs=tuple(reversed(b.region.pairs))))
  mapping=tuple(PairCorrespondence(p.pair_id,p.pair_id,p.pair_id)for p in a.region.pairs)
 if fault=='unmapped':mapping=(PairCorrespondence('left','p1','p1'),PairCorrespondence('missing','p2',None),PairCorrespondence('new',None,'p2'),PairCorrespondence('right','p3','p3'))
 r=stacking_compare(a,b,mapping)
 if fault=='missing_atom':
  for step in r['steps']:
   assert step['stacking_geometry'][0]['plane_angle_deg']['delta']is None
   assert step['stacking_geometry'][1]['plane_angle_deg']['delta']==pytest.approx(0)
 elif fault=='break':
  assert all(x['normal_spacing_angstrom']['candidate_reason']=='DECLARED_BREAK'for x in r['steps'][0]['stacking_geometry'])
  assert all(x['normal_spacing_angstrom']['delta']==pytest.approx(0)for x in r['steps'][1]['stacking_geometry'])
 else:
  assert len(r['steps'])==4
  assert all(x['plane_angle_deg']['delta']is None for step in r['steps']for x in step['stacking_geometry'])
  assert all(v==0 for v in r['coverage']['stacking_changes'].values())


def test_stacking_comparison_keeps_partial_angle_and_distance(tmp_path):
 a,b=twist_states(tmp_path,0,0);lines=[]
 for l in b.model_path.read_text().splitlines(keepends=True):
  if l[21:26]=='A   2':
   x,y,z=(float(l[a:b])for a,b in ((30,38),(38,46),(46,54)))
   l=l[:30]+f'{x:8.3f}{-(z-3.4):8.3f}{y+3.4:8.3f}'+l[54:]
  lines.append(l)
 b=state(tmp_path,'candidate',b.region,''.join(lines));r=stacking_compare(a,b)
 for step in r['steps']:
  row=step['stacking_geometry'][0]
  assert row['plane_angle_deg']['delta']==pytest.approx(90,abs=1e-6)
  assert row['centroid_distance_angstrom']['status']=='MEASURED'
  assert row['normal_spacing_angstrom']['delta']is None
  assert row['normal_spacing_angstrom']['candidate_reason']=='AMBIGUOUS_MIDPLANE_NORMAL'
  assert step['stacking_geometry'][1]['normal_spacing_angstrom']['delta']==pytest.approx(0)


@pytest.mark.parametrize('options',[{'include_stacking':1},{'include_stacking':None},{'include_stacking':True}])
def test_stacking_comparison_rejects_implicit_frame_policy(tmp_path,options):
 a,b=state(tmp_path,'parent'),state(tmp_path,'candidate')
 with pytest.raises(ValueError,match='boolean|simple_twist'):
  compare(a,b,**options)
