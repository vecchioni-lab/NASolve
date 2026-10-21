"""ATL is an independent public bridged-sugar control, never a scaffold edit."""
from pathlib import Path
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[1]

def test_atl_keeps_bridge_four_source_centres_and_existing_narestraints_roles():
    from nasolve.cif_component_controls import assess_component_control
    from nasolve.cif_stereochemistry_audit import reader_stereo_inventory,_values,_graph
    p=ROOT/'tests/fixtures/public_ccd/ATL.cif';original=p.read_bytes()
    assert len(original)==9245 and sha256(original).hexdigest()=='2c42f8acb1ba85ca16ee63e6c4cddc9cc85032db13b0d0674791da2350e66a9b'
    r=assess_component_control(p,'ATL');stereo=reader_stereo_inventory(p,'ATL');_,bonds,_,neighbors=_graph(_values(p,'ATL'))
    assert r['graph_status']==r['policy_status']=='PASS' and r['mapped_base_class']=='T'
    assert r['policy_controls']['pair_recipe']=='AT' and len(r['policy_controls']['stack_requests'])==2
    assert r['atom_stereo']=={"C1'":'R',"C2'":'S',"C3'":'R',"C4'":'S'}
    assert all(len(neighbors[n])==4 for n in r['atom_stereo'])
    assert bonds[tuple(sorted(("C4'","C6'")))]==bonds[tuple(sorted(("C6'","O2'")))]=='SINGLE'
    assert stereo['stereochemistry_inferred'] is False and not r['automatic_adoption'] and p.read_bytes()==original


def test_three_explicit_public_controls_bundle_exact_sources_without_nar_edits(tmp_path):
    import importlib.util,restraints
    path=ROOT/'scripts/build_synthetic_dna_shuttle.py';spec=importlib.util.spec_from_file_location('atl_builder',path);builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    metadata=builder.build(ROOT,Path(restraints.__file__).resolve().parents[1],tmp_path/'runner.py',template_name='cif_numerical_recovery_probe_template.py',delivery_prefix='51_Cedar',component_controls=('PDU','5PC','ATL'))
    controls={c['component']:c for c in metadata['component_controls']}
    assert set(controls)=={'PDU','5PC','ATL'} and controls['ATL']['sha256']=='2c42f8acb1ba85ca16ee63e6c4cddc9cc85032db13b0d0674791da2350e66a9b'
    assert controls['PDU']['sha256']=='cd192f18964a28c628544ae1c0b4b1f2aed124e1b90a21b9c6ca0aa4458c0292'
    assert controls['5PC']['sha256']=='cea88a7236f4775310e0d997a063c00c4dfc5982d89f1dc27c59593fb4c71650'
