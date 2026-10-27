"""Observation-associated wavelengths and explicit offline reference values."""
import json
import re
import subprocess

from .recipe import RecipeError, checksum, element, number


def observation_metadata(output: str) -> dict:
    """Select one populated anomalous amplitude quartet within one MTZ dataset.

    HKL_base wavelengths never supply an observation wavelength. Multiple
    competing complete quartets require a future explicit array selector.
    """
    datasets, current = [], None
    crystal = None
    resolution, symmetry = None, None
    for line in output.splitlines():
        stripped = line.strip()
        if line.startswith('Resolution range:'):
            try: resolution = number(float(stripped.split()[-1]), 'resolution')
            except ValueError: raise RecipeError('Invalid MTZ resolution')
        elif line.startswith('Space group from matrices:'):
            symmetry = stripped.split(':', 1)[1].strip()
        elif line.startswith('Crystal '):
            current = None
            crystal = stripped
        elif re.match(r'^\s+Dataset \d+:', line):
            current = {'crystal': crystal, 'dataset_name': None, 'dataset_id': None, 'wavelength_A': None, 'columns': {}}
            datasets.append(current)
        elif current is not None:
            if stripped.startswith('Name:'): current['dataset_name'] = stripped.split(':', 1)[1].strip()
            elif stripped.startswith('Id:'): current['dataset_id'] = int(stripped.split(':', 1)[1])
            elif stripped.startswith('Wavelength:'):
                try: current['wavelength_A'] = float(stripped.split(':', 1)[1])
                except ValueError: current['wavelength_A'] = None
            else:
                match = re.match(r'^\s*(\S+)\s+(\d+)\s+[\d.]+%\s+\S+\s+\S+\s+([A-Z]):', line)
                if match:
                    label, valid, kind = match.groups()
                    if label in current['columns']:
                        raise RecipeError('Duplicate MTZ column label within dataset')
                    current['columns'][label] = {'valid': int(valid), 'type': kind}
    quartet = ['F(+)', 'SIGF(+)', 'F(-)', 'SIGF(-)']
    matches = [d for d in datasets if all(label in d['columns'] for label in quartet)]
    if len(matches) != 1:
        raise RecipeError('Require exactly one explicit anomalous amplitude quartet dataset')
    selected = matches[0]
    wavelength = number(selected['wavelength_A'], 'observation wavelength')
    if wavelength <= 0 or wavelength == 9.999:
        raise RecipeError('Missing or placeholder observation wavelength')
    for label, kind in zip(quartet, 'GLGL'):
        if selected['columns'][label]['type'] != kind or selected['columns'][label]['valid'] == 0:
            raise RecipeError('Anomalous amplitude quartet is empty or has incorrect column types')
    flags = [(d, d['columns']['FreeR_flag']) for d in datasets if 'FreeR_flag' in d['columns']]
    if len(flags) != 1 or flags[0][1]['type'] != 'I' or flags[0][1]['valid'] == 0:
        raise RecipeError('Require one populated integer FreeR_flag column')
    if selected['dataset_id'] is None or resolution is None or resolution <= 0 or symmetry is None:
        raise RecipeError('Missing explicit MTZ dataset, resolution or symmetry metadata')
    return {'wavelength_A': wavelength, 'dataset_id': selected['dataset_id'],
            'dataset_name': selected['dataset_name'], 'crystal': selected['crystal'],
            'anomalous_labels': quartet, 'free_r_label': 'FreeR_flag',
            'free_r_dataset_id': flags[0][0]['dataset_id'],
            'columns': selected['columns'], 'd_min_A': resolution, 'symmetry': symmetry,
            'source': 'selected observation dataset in phenix.mtz.dump',
            'qualification': 'Header/column presence only; no reflection-level or refinement qualification'}


def _run(command, environment):
    try:
        result = subprocess.run([str(x) for x in command], env=environment, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecipeError(f'Native input inspection failed: {exc}') from exc
    if result.returncode:
        raise RecipeError(f'Native input inspection failed ({result.returncode}): {result.stderr[-1000:]}')
    return result.stdout


def inspect_observations(path, *, executable, environment=None):
    return observation_metadata(_run([executable, path], environment))


def reference_scattering(elements, wavelength, *, executable, version, table='sasaki', environment=None):
    """Use the configured Phenix Python and record exact provider/version/inputs."""
    elements = sorted({element(item) for item in elements})
    wavelength = number(wavelength, 'wavelength')
    if wavelength <= 0 or table not in {'sasaki', 'henke'}:
        raise RecipeError('Require positive wavelength and an explicit Sasaki or Henke provider')
    if not elements:
        return []
    script = ('import json,hashlib\nfrom pathlib import Path\nfrom phenix import phenix_info\nfrom cctbx.eltbx import ' + table + '\n'
              'table_hash=hashlib.sha256(Path(' + table + '.ext.__file__).read_bytes()).hexdigest()\n'
              'release=phenix_info.version_and_release_tag()\n'
              'native_version="-".join(str(v) for v in release if v) or "unknown"\n'
              'rows=[]\nfor name in ' + repr(elements) + ':\n'
              ' value=' + table + '.table(name).at_angstrom(' + repr(wavelength) + ')\n'
              ' if not (value.is_valid_fp() and value.is_valid_fdp()): raise ValueError("Reference out of range")\n'
              ' rows.append({"element":name,"f_prime":value.fp(),"f_double_prime":value.fdp(),"table_sha256":table_hash,"native_version":native_version})\n'
              'print("NASOLVE_SCATTERING="+json.dumps(rows))\n')
    output = _run([executable, '-c', script], environment)
    markers = [line.split('=', 1)[1] for line in output.splitlines() if line.startswith('NASOLVE_SCATTERING=')]
    try:
        if len(markers) != 1: raise ValueError('missing reference marker')
        rows = json.loads(markers[0])
        if not isinstance(rows, list) or [r['element'] for r in rows] != elements:
            raise ValueError('element inventory mismatch')
        for row in rows:
            checksum(row['table_sha256'], 'native scattering table')
            if not isinstance(row['native_version'], str):
                raise ValueError('missing native version')
            number(row['f_prime'], 'reference f prime')
            if number(row['f_double_prime'], 'reference f double prime') < 0:
                raise ValueError('negative reference fdp')
            row.update(wavelength_A=wavelength, provider='cctbx-' + table,
                       phenix_version=version, f_prime_policy='fixed', refined=False)
        return rows
    except (KeyError, TypeError, ValueError) as exc:
        raise RecipeError(f'Invalid native reference output: {exc}') from exc
