"""Development selectors cannot silently narrow the full regression gate."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/run_tests.py'


def load_runner():
    spec = importlib.util.spec_from_file_location('nasolve_test_runner', RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_collects_new_tests_without_profile_registration(tmp_path):
    runner = load_runner()
    (tmp_path / 'tests').mkdir()
    (tmp_path / 'tests/test_new_family.py').write_text('def test_new_family(): pass\n')
    assert runner.select_paths(['full'], tmp_path) == ['tests']
    with pytest.raises(ValueError, match='alone'):
        runner.select_paths(['full', 'chemistry'], tmp_path)


def test_profiles_are_explicit_unique_and_include_current_workflow_contracts():
    runner = load_runner()
    chemistry = runner.select_paths(['chemistry'], ROOT)
    workflow = runner.select_paths(['workflow'], ROOT)
    assert 'tests/test_cif_preparation_qualification.py' in chemistry
    assert 'tests/test_cif_postmr_cache.py' in workflow
    assert 'tests/test_postmr_cache_workflow.py' in workflow
    assert 'tests/test_test_suites.py' in runner.select_paths(['smoke'], ROOT)
    combined = runner.select_paths(['chemistry', 'workflow', 'chemistry'], ROOT)
    assert combined == sorted(set(chemistry + workflow))
    assert all(Path(p).parts[0] == 'tests' and (ROOT / p).is_file() for p in combined)


def test_missing_profile_member_is_an_error_not_a_smaller_pass(tmp_path):
    runner = load_runner()
    (tmp_path / 'tests').mkdir()
    with pytest.raises(ValueError, match='matched no tests'):
        runner.select_paths(['chemistry'], tmp_path)
    with pytest.raises(ValueError, match='Unknown'):
        runner.select_paths(['typo'], tmp_path)


def test_runner_is_relocatable_and_does_not_inherit_hidden_filters(tmp_path):
    root = tmp_path / 'owned-original'
    (root / 'scripts').mkdir(parents=True)
    (root / 'src').mkdir()
    (root / 'tests').mkdir()
    shutil.copy2(RUNNER, root / 'scripts/run_tests.py')
    (root / 'tests/test_canary.py').write_text(
        'import os\nfrom pathlib import Path\n'
        'def test_canary():\n'
        '    assert Path(os.environ["PYTHONPATH"]) == Path.cwd() / "src"\n'
        '    assert os.environ["PYTHONDONTWRITEBYTECODE"] == "1"\n')
    relocated = tmp_path / 'relocated'
    root.rename(relocated)
    env = {**os.environ, 'PYTEST_ADDOPTS': '-k definitely_not_a_test', 'PYTHONPATH': '/absent/original/src'}
    p = subprocess.run([sys.executable, str(relocated / 'scripts/run_tests.py'), 'full'],
                       cwd=tmp_path, env=env, text=True, capture_output=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert '1 passed' in p.stdout and not root.exists()
    # The same command must return pytest's failure, never a successful wrapper status.
    (relocated / 'tests/test_canary.py').write_text('def test_canary(): assert False\n')
    p = subprocess.run([sys.executable, str(relocated / 'scripts/run_tests.py'), 'full'],
                       cwd=tmp_path, env=env, text=True, capture_output=True)
    assert p.returncode == 1 and '1 failed' in p.stdout


def test_list_is_read_only_and_unknown_options_cannot_filter_full(tmp_path):
    p = subprocess.run([sys.executable, str(RUNNER), 'full', '--list'],
                       cwd=tmp_path, text=True, capture_output=True)
    assert p.returncode == 0 and json.loads(p.stdout)['paths'] == ['tests']
    p = subprocess.run([sys.executable, str(RUNNER), 'full', '-k', 'never'],
                       cwd=tmp_path, text=True, capture_output=True)
    assert p.returncode == 2


def test_campaign_fixture_class_is_collected_only_in_its_own_module():
    p = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q', '-p', 'no:cacheprovider',
                        'tests/test_campaign_full_auto_pipeline.py', 'tests/test_campaign_pipeline.py'],
                       cwd=ROOT, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT / 'src'), 'PYTEST_ADDOPTS': ''},
                       text=True, capture_output=True)
    assert p.returncode == 0, p.stdout + p.stderr
    nodes = [line for line in p.stdout.splitlines() if '::CampaignPipelineTests::' in line]
    assert len(nodes) == 5
    assert all(line.startswith('tests/test_campaign_pipeline.py::') for line in nodes)
