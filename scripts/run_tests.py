#!/usr/bin/env python3
"""Explicit developer test profiles; plain pytest and the full gate stay unfiltered.

Run from any directory with this checkout's test-enabled Python. These profiles
are starting points, not change-impact analysis. Add affected tests separately
with pytest; shared infrastructure and integration changes require the full gate.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    'smoke': (
        'test_test_suites', 'test_cif_doctor_selection', 'test_cif_preparation_qualification',
        'test_cif_postmr_cache', 'test_postmr_cache_workflow', 'test_checkpoints', 'test_run_context',
    ),
    'chemistry': (
        'test_cif_preparation_qualification', 'test_cif_linked_preparation',
        'test_cif_linked_usability_bridge', 'test_cif_terminal_preparation',
        'test_cif_candidate_usability', 'test_cif_purine_representation',
        'test_cif_linked_torsion_energy', 'test_cif_linked_linear_torsion', 'test_cif_linear_torsion_candidate',
        'test_cif_whole_furanose', 'test_cif_fana_placement', 'test_cif_fana', 'test_cif_fana_enantiomer', 'test_cif_fana_component',
        'test_cif_stereochemistry_audit', 'test_cif_terminal_qualification',
        'test_cif_source_classification', 'test_cif_attachment_profiles',
        'test_cif_attachment_sites', 'test_cif_attachment_links', 'test_cif_pna_operations',
        'test_cif_topology_gate', 'test_phosphate', 'test_recipe_phosphates',
    ),
    'workflow': (
        'test_test_suites', 'test_cif_doctor_selection', 'test_cif_dictionary_store',
        'test_cif_source_reuse', 'test_cif_dictionary_policy', 'test_cif_dictionary_sites', 'test_cif_dictionary_bundle', 'test_cif_dictionary_bundle_readyset', 'test_cif_readyset_atom_order', 'test_cif_component_runtime', 'test_cif_runtime_bundle', 'test_cif_mixed_runtime_bundle', 'test_cif_phosphate_names', 'test_cif_native_context', 'test_cif_native_monomers', 'test_cif_postmr_cache', 'test_postmr_cache_workflow',
        'test_postmr_component_inputs', 'test_cif_postmr_cached_model',
        'test_postmr', 'test_postmr_phosphate', 'test_postmr_context',
        'test_checkpoints', 'test_run_context', 'test_campaign_pipeline',
        'test_campaign_full_auto_pipeline', 'test_sequence_family_integration',
    ),
    'delivery': ('test_cedar*_delivery', 'test_*probe', 'test_cif_doctor_ccd_shuttle'),
}


def select_paths(profiles, root=ROOT):
    """Expand explicit profiles, rejecting stale entries rather than losing coverage."""
    if not profiles or any(name not in {*PROFILES, 'full'} for name in profiles):
        raise ValueError('Unknown or missing test profile')
    if 'full' in profiles:
        if profiles != ['full']:
            raise ValueError('The full suite must be requested alone')
        if not (root / 'tests').is_dir():
            raise ValueError('Full test directory is missing')
        # Let pytest collect the entire directory, including future tests that
        # are not registered in any development profile.
        return ['tests']
    paths = set()
    for profile in profiles:
        for pattern in PROFILES[profile]:
            matched = sorted((root / 'tests').glob(pattern + '.py'))
            if not matched:
                raise ValueError(f'{profile}: {pattern} matched no tests')
            paths.update(path.relative_to(root).as_posix() for path in matched)
    return sorted(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profiles', nargs='+', choices=[*PROFILES, 'full'])
    parser.add_argument('--list', action='store_true', help='Print expanded file selection as JSON; do not run pytest')
    parser.add_argument('--collect-only', action='store_true', help='Ask pytest to collect the selected cases without execution')
    parser.add_argument('--junitxml', type=Path, help='Write timings/results to a new XML file; refuses an existing path')
    args = parser.parse_args(argv)
    try:
        paths = select_paths(args.profiles)
    except ValueError as exc:
        parser.error(str(exc))
    if args.list:
        print(json.dumps({'profiles': args.profiles, 'paths': paths, 'full_regression': args.profiles == ['full']}, indent=2))
        return 0
    command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'addopts=', '--durations=20']
    if args.collect_only:
        command.append('--collect-only')
    if args.junitxml is not None:
        output = args.junitxml.absolute()
        if output.exists() or output.is_symlink():
            parser.error('JUnit output already exists; select a new filename')
        command.append('--junitxml=' + str(output))
    command.extend(paths)
    environment = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(ROOT / 'src'), 'PYTEST_ADDOPTS': ''}
    print('Profiles: ' + ', '.join(args.profiles), flush=True)
    print('Scope: ' + ('FULL REGRESSION' if args.profiles == ['full'] else 'FOCUSED DEVELOPMENT; not the merge gate'), flush=True)
    print('Command: ' + shlex.join(command), flush=True)
    return subprocess.call(command, cwd=ROOT, env=environment)


if __name__ == '__main__':
    raise SystemExit(main())
