"""CLI surfaces over the same run context and preview used by future GUI panels."""
import json
from pathlib import Path
import sys

from ..config import load_config, ConfigError
from ..phenix_runtime import discover_phenix, PhenixDiscoveryError
from ..run_context import resolve_artifact_path
from .binding import AtomKey
from .context import load_run_context
from .export import export_restraints
from .recipe import Recipe, RecipeError
from .scattering import inspect_observations, reference_scattering


def configure(subparsers):
    metal = subparsers.add_parser('metal', help='inspect generated models and preview explicit metal restraints')
    actions = metal.add_subparsers(dest='metal_action', required=True)
    inspect = actions.add_parser('inspect', help='read one generated W checkpoint and its observation wavelength')
    preview = actions.add_parser('preview', help='bind a recipe to an explicit generated W checkpoint')
    build = actions.add_parser('build', help='add explicitly placed metal sites in a new review bundle')
    verify = actions.add_parser('verify', help='replay a saved hypothesis without native execution')
    for parser in (inspect, preview, build, verify):
        parser.add_argument('run', type=Path, help='explicit NASolve run directory')
        if parser is not verify:
            parser.add_argument('--checkpoint', default='postmr', help='exact checkpoint/bookmark (default: postmr)')
            parser.add_argument('--dataset-id', help='explicit campaign dataset identifier for linked views')
        parser.add_argument('--json', action='store_true')
        parser.add_argument('--output', type=Path, help='save JSON to a new file; never overwrite')
    inspect.add_argument('--element', action='append', default=[], help='reference scattering element; repeat as needed')
    inspect.add_argument('--table', choices=['sasaki', 'henke'], default='sasaki')
    preview.add_argument('--recipe', type=Path, required=True)
    preview.add_argument('--bindings', type=Path, help='exact non-donor atom bindings with source_model_sha256')
    preview.add_argument('--export', type=Path, help='write proposed PHIL restraints to a new file; no refinement')
    build.add_argument('--recipe', type=Path, required=True)
    build.add_argument('--placement', type=Path, required=True, help='explicit source-bound metal-placement-plan JSON')
    verify.add_argument('--hypothesis', type=Path, required=True, help='exact directory, absolute or relative to run')


def _json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RecipeError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs)


def execute(args):
    try:
        outputs = [p for p in (args.output, getattr(args, 'export', None)) if p is not None]
        if len({p.resolve() for p in outputs}) != len(outputs) or any(p.exists() or p.is_symlink() for p in outputs):
            raise RecipeError('Outputs must be distinct new files')
        if args.metal_action in {'build', 'verify'}:
            return _hypothesis(args)
        context = load_run_context(args.run, checkpoint=args.checkpoint, dataset_id=args.dataset_id)
        export = None
        if args.metal_action == 'inspect':
            result = context.to_dict()
            native = discover_phenix(load_config(), explicit=args.phenix_root)
            observations = resolve_artifact_path(result['sources']['observations'], context.run)
            if observations is None:
                raise RecipeError('Observations changed before inspection')
            result['observations'] = inspect_observations(observations,
                executable=native.executables['phenix.mtz.dump'], environment=native.environment)
            result['reference_scattering'] = reference_scattering(args.element,
                result['observations']['wavelength_A'], executable=native.executables['phenix.python'],
                version=native.version, table=args.table, environment=native.environment)
            if resolve_artifact_path(result['sources']['observations'], context.run) is None:
                raise RecipeError('Observations changed during inspection')
        else:
            recipe = Recipe.from_json(args.recipe.read_text())
            bindings = {}
            if args.bindings:
                raw = _json(args.bindings)
                if not isinstance(raw, dict) or set(raw) != {'source_model_sha256', 'atoms'}:
                    raise RecipeError('Bindings require source_model_sha256 and atoms')
                if raw['source_model_sha256'] != context.imported.snapshot.source_sha256:
                    raise RecipeError('Bindings belong to a different source model')
                if not isinstance(raw['atoms'], dict):
                    raise RecipeError('Bindings atoms must be an object keyed by node ID')
                bindings = {key: AtomKey(**value) for key, value in raw['atoms'].items()}
            result = context.preview(recipe, atom_bindings=bindings)
            if args.export:
                export = export_restraints(result)
        # Revalidate all captured input bytes after work and before publication.
        sources = context.to_dict()['sources']
        refs = [sources[k] for k in ('model', 'observations', 'report')]
        refs += sources['restraints'] + ([sources['phases']] if sources['phases'] else [])
        if any(resolve_artifact_path(ref, context.run) is None for ref in refs):
            raise RecipeError('Context input changed during inspection/preview')
        serialized = json.dumps(result, indent=2, allow_nan=False) + '\n'
        if export is not None:
            with args.export.open('x') as handle: handle.write(export)
        if args.output:
            with args.output.open('x') as handle: handle.write(serialized)
        if args.json:
            print(serialized, end='')
        elif args.metal_action == 'inspect':
            print(f'Metal context: {result["dataset_id"]} / {result["run_id"]} / {result["checkpoint_id"]}')
            print('Ordered pair: A:12 first; B:4 second')
            print(f'Observation wavelength: {result["observations"]["wavelength_A"]:.8g} A')
            for row in result['reference_scattering']:
                print(f'{row["element"]}: fixed reference f\'={row["f_prime"]:.6g}; reference f\"={row["f_double_prime"]:.6g} ({row["provider"]})')
            print('Generated-model inspection only; metal placement/refinement not performed.')
        else:
            print('Metal preview: ' + result['status'])
            print(f'{len(result["restraints"])} declared restraints; native/chemical qualification pending.')
        return 0 if args.metal_action == 'inspect' or result['status'] == 'resolved' else 2
    except (RecipeError, ConfigError, PhenixDiscoveryError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f'Metal integration error: {exc}', file=sys.stderr)
        return 2


def _hypothesis(args):
    from .materialize import build_hypothesis, verify_hypothesis
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'build':
        context = load_run_context(args.run, checkpoint=args.checkpoint, dataset_id=args.dataset_id)
        result = build_hypothesis(context, Recipe.from_json(args.recipe.read_text()), _json(args.placement))
    else:
        result = verify_hypothesis(args.run, args.hypothesis)
    serialized = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(serialized)
    if args.json:
        print(serialized, end='')
    else:
        directory = str(Path(result['files']['model']['relative_path']).parent)
        print(f'Metal hypothesis {args.metal_action}: {directory}')
        print(f'{len(result["sites"])} explicit sites; status {result["status"]}')
        if result['unrestrained_metal_nodes']:
            print('Unrestrained metal nodes: ' + ', '.join(result['unrestrained_metal_nodes']))
        print('Review model only; no optimization, anomalous fit or checkpoint selection.')
    return 0
