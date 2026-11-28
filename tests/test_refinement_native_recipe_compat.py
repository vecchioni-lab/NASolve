"""Old execution policies keep original helper bytes after a live helper upgrade."""
from hashlib import sha256
import json
from pathlib import Path

import pytest
from nasolve import refinement_parallelity as runtime


@pytest.mark.parametrize('policy', runtime._COUNTED_POLICIES)
def test_old_counted_payload_keeps_exact_native_recipe(policy):
    payload=runtime._code(policy)
    assert {name:sha256(raw).hexdigest() for name,raw in payload.items()} == runtime._expected_code(policy)
    frozen=payload['code/_nasolve_refinement/topostitch_native_recipe.py']
    live=(Path(runtime.__file__).parent/'topostitch_native_recipe.py').read_bytes()
    assert sha256(frozen).hexdigest() == '1739b2a7cf11d802bfa9293d7b79b9edcf7bb1ad868b53d4c1b1996b461d7748'
    assert frozen != live
    assert b'def _native_crystal_binding(' in live
    assert b'def _native_crystal_binding(' not in frozen


@pytest.mark.parametrize('damage', ['bytes','extra','missing'])
def test_frozen_recipe_damage_cannot_fall_back_to_live_module(tmp_path,monkeypatch,damage):
    package=Path(runtime.__file__).parent
    archives = {str(path.relative_to(package)) for path in (package/'data').glob('refinement-runtime-*.json')}
    for name in {*runtime._V8_SOURCE_DIGESTS, *archives}:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((package/name).read_bytes())
    archive=tmp_path/'data/refinement-runtime-native-recipe-sources.json'
    record=json.loads(archive.read_text())
    if damage=='bytes':record['topostitch_native_recipe.py']+='\n# unqualified\n'
    elif damage=='extra':record['other.py']=''
    else:record={}
    archive.write_text(json.dumps(record))
    monkeypatch.setattr(runtime,'__file__',str(tmp_path/'refinement_parallelity.py'))
    with pytest.raises(ValueError, match='frozen native-recipe|qualified runtime'):
        runtime._code(runtime.V8_POLICY_ID)
