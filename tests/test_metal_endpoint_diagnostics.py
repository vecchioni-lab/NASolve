"""Recipe residuals must describe the refined endpoint, including disabled terms."""
import json
import pytest
from nasolve.metal.context import parse_pdb
from nasolve.metal.materialize import build_hypothesis
from nasolve.metal.xyz import _recipe_diagnostics
from tests.test_metal_materialize import control


def test_endpoint_geometry_uses_final_coordinates_and_preserves_term_identity(tmp_path):
    c,recipe,placement=control(tmp_path);h=build_hypothesis(c,recipe,placement)
    preview=json.loads((c.run/h['files']['preview']['relative_path']).read_text())
    raw=(c.run/h['files']['model']['relative_path']).read_bytes()
    original=_recipe_diagnostics(preview,raw)
    lines=raw.decode().splitlines(keepends=True)
    for i,line in enumerate(lines):
        if line[0:6].strip()=='HETATM' and line[76:78].strip()=='HG':
            lines[i]=line[:30]+f'{float(line[30:38])+1.0:8.3f}'+line[38:]
    moved=''.join(lines).encode()
    report=_recipe_diagnostics(preview,moved)
    assert report['model_sha256']!=original['model_sha256']
    assert report['restraints'][0]['measured']!=original['restraints'][0]['measured']
    a=report['restraints'][0]
    assert a['signed_sigma_deviation']==pytest.approx((a['measured']-a['target'])/a['sigma'])
    assert a['restraint_id']==original['restraints'][0]['restraint_id']
    assert report['scientific_acceptance']=='NOT_ASSESSED'
    assert report['scope']=='explicit_recipe_only_excludes_inherited_and_nonbonded_terms'


def test_disabled_recipe_is_reported_without_becoming_an_active_score(tmp_path):
    c,recipe,placement=control(tmp_path);h=build_hypothesis(c,recipe,placement)
    preview=json.loads((c.run/h['files']['preview']['relative_path']).read_text())
    raw=(c.run/h['files']['model']['relative_path']).read_bytes()
    for term in preview['inputs']['recipe']['restraints']:term['enabled']=False
    report=_recipe_diagnostics(preview,raw)
    assert report['active_resolved_count']==0
    assert report['maximum_absolute_sigma_deviation'] is None
    assert all(r['signed_sigma_deviation'] is None for r in report['restraints'])
