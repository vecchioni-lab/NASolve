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
    scale_inspect = actions.add_parser('inspect-final-scaling', help='read printed final scaling stages; no native run or model change')
    scale_inspect.add_argument('log', type=Path, help='explicit Phenix refinement log')
    scale_inspect.add_argument('--expected-sha256', help='optional independently retained log checksum')
    scale_inspect.add_argument('--json', action='store_true')
    scale_inspect.set_defaults(output=None)
    child_inputs = actions.add_parser('verify-fdp-child-inputs', help='replay prepared bytes from one protected ordinary parent; no native run')
    child_inputs.add_argument('prepared', type=Path)
    child_inputs.add_argument('--parent-archive', type=Path, required=True)
    child_inputs.add_argument('--request', type=Path, required=True)
    child_inputs.add_argument('--request-id', required=True)
    child_inputs.add_argument('--run-relative', required=True)
    child_inputs.add_argument('--endpoint-relative', required=True)
    child_inputs.add_argument('--reader-control-policy')
    child_inputs.add_argument('--max-parent-disk-bytes', type=int, default=256*1024*1024)
    child_inputs.add_argument('--json', action='store_true')
    child_inputs.set_defaults(output=None)
    audited_inspect = actions.add_parser('inspect-audited-fdp-child', help='read saved session evidence and recheck frozen state without native execution')
    audited_inspect.add_argument('session', type=Path)
    audited_inspect.add_argument('--review-id', required=True)
    audited_inspect.add_argument('--json', action='store_true')
    audited_inspect.set_defaults(output=None)
    audited_child = actions.add_parser('run-audited-fdp-child', help='derive, execute and audit one frozen child; no scientific acceptance')
    audited_child.add_argument('prepared', type=Path)
    audited_child.add_argument('--parent-archive', type=Path, required=True)
    audited_child.add_argument('--request', type=Path, required=True)
    audited_child.add_argument('--request-id', required=True)
    audited_child.add_argument('--run-relative', required=True)
    audited_child.add_argument('--endpoint-relative', required=True)
    audited_child.add_argument('--session', type=Path, required=True)
    audited_child.add_argument('--phenix-root', type=Path)
    audited_child.add_argument('--timeout', type=float, default=240)
    audited_child.add_argument('--reader-control-policy')
    audited_child.add_argument('--max-parent-disk-bytes', type=int, default=256*1024*1024)
    audited_child.add_argument('--max-output-bytes', type=int, default=64*1024*1024)
    audited_child.add_argument('--json', action='store_true')
    audited_child.set_defaults(output=None)
    child_prepare = actions.add_parser('prepare-fdp-child-process', help='pin prepared frozen inputs for a fresh process-only child')
    child_prepare.add_argument('prepared', type=Path)
    child_prepare.add_argument('--parent-manifest-sha256', required=True)
    child_prepare.add_argument('--output', type=Path, required=True)
    child_prepare.add_argument('--json', action='store_true')
    child_run = actions.add_parser('run-fdp-child-process', help='run one owned frozen worker; no scientific acceptance or cleanup')
    child_run.add_argument('prepared', type=Path)
    child_run.add_argument('--request', type=Path, required=True)
    child_run.add_argument('--request-id', required=True)
    child_run.add_argument('--parent-archive', type=Path, required=True)
    child_run.add_argument('--attempt', type=Path, required=True)
    child_run.add_argument('--phenix-root', type=Path)
    child_run.add_argument('--timeout', type=float, default=240)
    child_run.add_argument('--retry-from', type=Path)
    child_run.add_argument('--max-parent-disk-bytes', type=int, default=256*1024*1024)
    child_run.add_argument('--json', action='store_true')
    child_run.set_defaults(output=None)
    child_inspect = actions.add_parser('inspect-fdp-child-process', help='inspect a child outcome without signalling or retrying')
    child_inspect.add_argument('attempt', type=Path)
    child_inspect.add_argument('--request-id', required=True)
    child_inspect.add_argument('--json', action='store_true')
    child_inspect.set_defaults(output=None)
    legacy = actions.add_parser('import-restraints', help='inspect legacy PHIL edits or rebind them to a reusable recipe')
    legacy.add_argument('source', type=Path, help='explicit local PHIL edits file')
    legacy.add_argument('--mapping', type=Path, help='JSON mapping of every selector ID to a logical node')
    legacy.add_argument('--id', dest='recipe_id', help='stable ID for the imported recipe')
    legacy.add_argument('--name', help='display name for the imported recipe')
    legacy.add_argument('--output', type=Path, help='new import record or recipe JSON; never overwrite')
    legacy.add_argument('--json', action='store_true')
    capture = actions.add_parser('capture-workbench', help='capture an explicit offline campaign catalog')
    browse = actions.add_parser('inspect-workbench', help='replay a catalog and inspect linked saved results offline')
    serve = actions.add_parser('serve-workbench', help='open a local read-only viewer of verified saved metal results')
    serve.add_argument('--catalog', type=Path, required=True)
    serve.add_argument('--port', type=int, default=0, help='loopback port; 0 chooses a free port')
    serve.set_defaults(output=None)
    capture.add_argument('--request', type=Path, required=True)
    capture.add_argument('--output', type=Path, required=True, help='new local catalog JSON file')
    browse.add_argument('--catalog', type=Path, required=True)
    browse.add_argument('--selection', type=Path, help='saved catalog-bound navigation selection')
    browse.add_argument('--row', help='open an exact linked result row')
    browse.add_argument('--site', help='explicit site membership when opening a row')
    browse.add_argument('--output', type=Path, help='save view JSON to a new local file')
    for parser in (capture, browse, serve):
        parser.add_argument('--dataset', action='append', required=True, metavar='ID=PATH',
                            help='explicit dataset mount; repeat for each catalog dataset')
        if parser is not serve:
            parser.add_argument('--json', action='store_true')
    recorded = actions.add_parser('inspect-recorded-fdp', help='read one pinned historical result from an input archive; no new audit or native run')
    recorded.add_argument('--archive', type=Path, required=True)
    recorded.add_argument('--archive-sha256', help='independently retained archive checksum')
    recorded.add_argument('--projection-id')
    recorded_selection = recorded.add_mutually_exclusive_group(required=True)
    recorded_selection.add_argument('--trial-id', help='exact saved attempt identity')
    recorded_selection.add_argument('--all-trials', action='store_true',
                                    help='read all attempts from a pinned publication in one archive view')
    recorded.add_argument('--expected-parent', type=Path,
                          help='independently retained parent identity JSON; no original model required')
    recorded.add_argument('--max-input-bytes', type=int, help='tighten the shared archive expansion budget')
    recorded.add_argument('--json', action='store_true', help='print the complete recorded inspection without rounding')
    recorded.set_defaults(output=None)
    recorded.add_argument('--publication', type=Path, help='completed batch receipt, instead of individual archive/projection/parent pins')
    recorded.add_argument('--publication-id', help='independently retained publication identity; required with --publication')
    publish = actions.add_parser('publish-fdp-inputs', help='archive an explicit completed trial batch and publish a pinned review receipt')
    publish.add_argument('run', type=Path)
    publish.add_argument('--trial', type=Path, action='append', required=True)
    publish.add_argument('--archive', type=Path, required=True, help='new archive outside the source run')
    publish.add_argument('--output', type=Path, required=True, help='new publication receipt outside the source run')
    publish.add_argument('--max-trial-bytes', type=int, default=1024**3)
    publish.add_argument('--max-input-bytes', type=int)
    publish.add_argument('--json', action='store_true')
    inspect = actions.add_parser('inspect', help='read one generated W checkpoint and its observation wavelength')
    preview = actions.add_parser('preview', help='bind a recipe to an explicit generated W checkpoint')
    build = actions.add_parser('build', help='add explicitly placed metal sites in a new review bundle')
    verify = actions.add_parser('verify', help='replay a saved hypothesis without native execution')
    geometry = actions.add_parser('geometry', help='prepare bounded metal-only coordinates against explicit recipe targets')
    verify_geometry = actions.add_parser('verify-geometry', help='replay a saved geometry trial without native execution')
    fdp = actions.add_parser('fdp', help='run one audited frozen-coordinate fixed-occupancy f-double-prime trial')
    storage = actions.add_parser('inspect-fdp-storage', help='measure explicit completed trials without scientific replay or cleanup')
    storage.add_argument('--trial', type=Path, action='append', required=True)
    storage.add_argument('--max-bytes', type=int, default=1024**3, help='total sample byte budget (default: 1 GiB)')
    storage.add_argument('--forecast', type=Path, help='JSON with explicit campaign counts and byte allowances')
    project_records = actions.add_parser('project-fdp-records', help='compact view of fully verified frozen trials; no cleanup or cache reuse')
    project_records.add_argument('--trial', type=Path, action='append', required=True)
    verify_records = actions.add_parser('verify-fdp-records', help='replay a compact view against all original trial and parent evidence')
    verify_records.add_argument('--projection', type=Path, required=True)
    for parser in (project_records, verify_records):
        parser.add_argument('--max-bytes', type=int, default=1024**3, help='trial payload preflight budget; excludes parent replay')
        parser.add_argument('--max-projection-bytes', type=int, default=16*1024**2, help='compact JSON byte budget (default: 16 MiB)')
    verify_fdp = actions.add_parser('verify-fdp', help='verify saved fdp inputs and freeze audit without a native run')
    compare_fdp = actions.add_parser('compare-fdp', help='compare audited fdp endpoints without native execution')
    verify_comparison = actions.add_parser('verify-fdp-comparison', help='replay a saved fdp comparison offline')
    inspect_ref = actions.add_parser('inspect-reference', help='inspect an explicit reference PDB snapshot; ignore stored anomalous values')
    inspect_ref.add_argument('model', type=Path)
    inspect_ref.add_argument('--element', action='append', required=True)
    inspect_ref.add_argument('--json', action='store_true')
    inspect_ref.add_argument('--output', type=Path)
    compare_ref = actions.add_parser('compare-reference', help='compare explicitly mapped candidate/reference internal geometry')
    verify_ref = actions.add_parser('verify-reference-comparison', help='replay a captured reference comparison offline')
    count = actions.add_parser('count-fdp', help='save explicit cluster/site atom-equivalent evidence from an audited fit')
    count_verify = actions.add_parser('verify-fdp-count', help='replay saved atom-equivalent evidence offline')
    count.add_argument('--trial', type=Path, required=True)
    count.add_argument('--groups', type=Path, required=True, help='JSON group names with nodes and explicit-sites/unresolved-proxy representation')
    count_verify.add_argument('--count-report', type=Path, required=True)
    count_compare = actions.add_parser('compare-fdp-count', help='compare signed cluster responses across matched frozen fdp trials')
    count_compare_verify = actions.add_parser('verify-fdp-count-comparison', help='replay a matched cluster response comparison offline')
    count_compare.add_argument('--trial', type=Path, action='append', required=True)
    count_compare.add_argument('--groups', type=Path, required=True, help='JSON explicit count groups, as for count-fdp')
    count_compare_verify.add_argument('--comparison', type=Path, required=True)
    scan_plan = actions.add_parser('plan-fdp-scan', help='plan an explicit occupancy grid from one audited seed trial')
    scan = actions.add_parser('run-fdp-scan', help='execute a bounded pass or resume an existing occupancy scan')
    scan_verify = actions.add_parser('verify-fdp-scan', help='verify saved scan results without native execution')
    scan_plan.add_argument('--seed', type=Path, required=True)
    scan_plan.add_argument('--occupancies', action='append', required=True, metavar='NODE=Q,Q,...')
    scan_plan.add_argument('--max-trials', type=int, required=True)
    scan.add_argument('--plan', type=Path, required=True)
    scan.add_argument('--job-budget', type=int, required=True)
    scan.add_argument('--resume', type=Path)
    scan_verify.add_argument('--scan', type=Path, required=True)
    for parser in (project_records, verify_records, storage, count, count_verify, count_compare, count_compare_verify, scan_plan, scan, scan_verify, inspect, preview, build, verify, geometry, verify_geometry, fdp, verify_fdp, compare_fdp, verify_comparison, compare_ref, verify_ref):
        parser.add_argument('run', type=Path, help='explicit NASolve run directory')
        if parser in (inspect, preview, build):
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
    geometry.add_argument('--hypothesis', type=Path, required=True, help='exact source hypothesis, absolute or relative to run')
    geometry.add_argument('--mobile', action='append', help='restrained metal node to move; repeat to lock all other sites')
    geometry.add_argument('--max-iterations', type=int, default=100)
    geometry.add_argument('--max-shift', type=float, default=1., help='maximum displacement per metal in angstrom (default: 1)')
    verify_geometry.add_argument('--geometry', type=Path, required=True, help='exact geometry directory, absolute or relative to run')
    fdp_source = fdp.add_mutually_exclusive_group(required=True)
    fdp_source.add_argument('--geometry', type=Path, help='saved recipe-only geometry trial')
    fdp_source.add_argument('--xyz', type=Path, help='saved native XYZ/ADP endpoint; remains scientifically unaccepted')
    fdp.add_argument('--fit', action='append', required=True, help='placed metal node to fit independently; repeat for additional sites')
    fdp.add_argument('--occupancy', action='append', default=[], metavar='NODE=Q', help='explicit input occupancy override; all q stays fixed during fitting')
    fdp.add_argument('--metal-b-policy', choices=('base-mean','donor-mean','keep'), default='base-mean',
                     help='prepare metal B before frozen trials: equal nucleobase means (no sugar/phosphate), donor mean, or explicit keep')
    fdp.add_argument('--metal-b-environments', type=Path, help='JSON assigning fitted metal nodes to explicit shared donor environments')
    fdp.add_argument('--cycles', type=int, default=3)
    fdp.add_argument('--start-fdp', type=float, default=0.)
    fdp.add_argument('--free-r-test-value', type=int, default=0)
    fdp.add_argument('--timeout', type=int, default=240)
    verify_fdp.add_argument('--trial', type=Path, required=True)
    compare_fdp.add_argument('--trial', type=Path, action='append', required=True, help='exact trial directory; repeat for each existing result')
    verify_comparison.add_argument('--comparison', type=Path, required=True)
    compare_ref.add_argument('--geometry', type=Path, required=True)
    compare_ref.add_argument('--reference', type=Path, required=True)
    compare_ref.add_argument('--mapping', type=Path, required=True)
    verify_ref.add_argument('--comparison', type=Path, required=True)



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
        if args.metal_action == 'inspect-final-scaling':
            from ..refinement_final_scaling import read_final_scaling
            result = read_final_scaling(args.log, expected_sha256=args.expected_sha256)
            if args.json:
                print(json.dumps(result, indent=2, allow_nan=False))
            else:
                print('Printed final scaling: ' + result['status'])
                for row in result['stages']:
                    print(f"{row['stage']}: Rwork={row['r_work']:.6g}; Rfree={row['r_free']:.6g}; reflections={row['n_refl']}")
                shift = result['b_transfer_printed']
                print('Final B transfer: '+(shift+' Å²' if shift is not None else 'unavailable'))
                print('Printed evidence only; no native execution, model change or scientific acceptance.')
            return 0 if result['status']=='OBSERVED' else 2
        if args.metal_action == 'inspect-audited-fdp-child':
            return _inspect_audited_child(args)
        if args.metal_action == 'run-audited-fdp-child':
            return _audited_child(args)
        if args.metal_action == 'verify-fdp-child-inputs':
            return _child_inputs(args)
        if args.metal_action in {'prepare-fdp-child-process','run-fdp-child-process','inspect-fdp-child-process'}:
            return _child_process(args)
        if args.metal_action == 'publish-fdp-inputs':
            return _publish_fdp(args)
        if args.metal_action == 'inspect-recorded-fdp':
            return _recorded_fdp(args)
        if args.metal_action == 'inspect-fdp-storage':
            return _fdp_storage(args)
        if args.metal_action in {'project-fdp-records', 'verify-fdp-records'}:
            return _fdp_records(args)
        if args.metal_action == 'import-restraints':
            return _import_restraints(args)
        if args.metal_action in {'capture-workbench', 'inspect-workbench', 'serve-workbench'}:
            return _workbench(args)
        if args.metal_action in {'plan-fdp-scan', 'run-fdp-scan', 'verify-fdp-scan'}:
            return _fdp_scan(args)
        if args.metal_action in {'inspect-reference', 'compare-reference', 'verify-reference-comparison'}:
            return _reference_snapshot(args)
        if args.metal_action in {'compare-fdp', 'verify-fdp-comparison'}:
            return _fdp_comparison(args)
        if args.metal_action in {'compare-fdp-count', 'verify-fdp-count-comparison'}:
            return _fdp_count_comparison(args)
        if args.metal_action in {'count-fdp', 'verify-fdp-count'}:
            return _fdp_count(args)
        if args.metal_action in {'fdp', 'verify-fdp'}:
            return _fdp(args)
        if args.metal_action in {'build', 'verify'}:
            return _hypothesis(args)
        if args.metal_action in {'geometry', 'verify-geometry'}:
            return _geometry(args)
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


def _geometry(args):
    from .geometry import prepare_geometry, verify_geometry
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'geometry':
        result = prepare_geometry(args.run, args.hypothesis, mobile_nodes=args.mobile,
                                  max_iterations=args.max_iterations, max_shift_A=args.max_shift)
    else:
        result = verify_geometry(args.run, args.geometry)
    serialized = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(serialized)
    if args.json:
        print(serialized, end='')
    else:
        directory = Path(result['files']['model']['relative_path']).parent
        evidence = _json(args.run.expanduser().resolve()/result['files']['result']['relative_path'])
        print(f'Metal geometry review: {directory}; {evidence["selection"]}')
        print(f'Recipe objective: {evidence["initial"]["objective"]:.6g} -> {evidence["selected"]["objective"]:.6g}')
        print(f'Stopping: {evidence["optimization"]["stopping"]}; local unconstrained dimensions: {evidence["selected"]["local_unconstrained_dimensions"]}')
        if evidence['retained_parent_reason']:
            print('Parent retained: ' + evidence['retained_parent_reason'])
        print('Restraint                 Start        Prepared       Target     Residual (sigma)')
        for initial, final in zip(evidence['initial']['restraints'], evidence['selected']['restraints']):
            print(f'{final["restraint_id"]:<24} {initial["measured"]:>10.4f} {final["measured"]:>13.4f} {final["target"]:>12.4f} {final["z"]:>12.4f} {final["unit"]}')
        print('Recipe-only metal preparation; chemical/clash assessment and diffraction refinement remain separate.')
    return 0


def _fdp(args):
    from .fdp import run_fdp, verify_fdp
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'fdp':
        occupancies = {}
        for value in args.occupancy:
            node, separator, q = value.partition('=')
            if not separator or not node or node in occupancies:
                raise RecipeError('Use distinct NODE=Q occupancy overrides')
            occupancies[node] = float(q)
        native = discover_phenix(load_config(), explicit=args.phenix_root)
        result = run_fdp(args.run, args.xyz or args.geometry, native=native, fit_nodes=args.fit,
                         occupancies=occupancies, cycles=args.cycles, start_fdp=args.start_fdp, metal_b_policy=args.metal_b_policy,
                         free_r_test_value=args.free_r_test_value, timeout=args.timeout,
                         metal_b_environments=json.loads(args.metal_b_environments.read_text()) if args.metal_b_environments else None)
    else:
        result = verify_fdp(args.run, args.trial)
    serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle: handle.write(serialized)
    if args.json:
        print(serialized, end='')
    else:
        path = args.run.expanduser().resolve()/result['files']['result.json']['relative_path']
        report = _json(path)
        print(f'Frozen f-double-prime trial: {path.parent.name}; {report["freeze_audit"]} freeze audit')
        print(f'Observation wavelength: {report["wavelength_A"]:.8g} A; f-prime fixed to Sasaki reference')
        print('Site                 Element        q          B         f-prime       fitted fdp    reference fdp')
        for row in report['sites']:
            print(f'{row["node_id"]:<20} {row["element"]:<7} {row["occupancy"]:>8.2f} {row["b_iso"]:>10.2f} {row["f_prime"]:>14.6g} {row["f_double_prime"]:>14.6g} {row["reference_f_double_prime"]:>16.6g}')
        print('Conditional diagnostic only; geometry, count, identity and convergence require review. Checkpoint unchanged.')
    return 0


def _fdp_comparison(args):
    from .fdp_compare import build_comparison, verify_comparison
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'compare-fdp':
        result = build_comparison(args.run, args.trial)
    else:
        result = verify_comparison(args.run, args.comparison)
    serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(serialized)
    if args.json:
        print(serialized, end='')
    else:
        path = args.run.expanduser().resolve()/result['files']['report']['relative_path']
        report = _json(path)
        print(f'F-double-prime comparison: {path.parent.name}; {len(report["trials"])} audited trials')
        print('Trial        Site        q     Start  Cycles    Fitted fdp    Ref. deviation')
        for row in report['rows']:
            trial = Path(row['trial_manifest']['relative_path']).parent.name
            deviation = row['reference_deviation_fraction']
            label = f'{deviation:+.1%}' if deviation is not None else 'undefined'
            print(f'{trial:<12} {row["node_id"]:<8} {row["occupancy"]:>5.2f} {row["settings"]["start_fdp"]:>9.3g} {row["settings"]["cycles"]:>7} {row["f_double_prime"]:>13.6g} {label:>17}')
        for axis, groups in report['sensitivity'].items():
            compared = sum(g['status']=='COMPARED' for g in groups)
            print(f'{axis}: {compared} matched comparisons; {len(groups)-compared} groups not tested')
        print(f'Full vectors, settings and endpoint ranges: {path}')
        print('Endpoint agreement does not prove convergence or identify the correct structure. Checkpoint unchanged.')
    return 0


def _reference_snapshot(args):
    from .reference import inspect_reference, compare_reference, verify_reference_comparison
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'inspect-reference':
        result = inspect_reference(args.model.expanduser().read_bytes(), elements=args.element)
        report = None
    elif args.metal_action == 'compare-reference':
        result = compare_reference(args.run, args.geometry, args.reference, _json(args.mapping))
        report = _json(args.run.expanduser().resolve()/result['files']['report']['relative_path'])
    else:
        result = verify_reference_comparison(args.run, args.comparison)
        report = _json(args.run.expanduser().resolve()/result['files']['report']['relative_path'])
    serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle: handle.write(serialized)
    if args.json:
        print(serialized,end='')
    elif report is None:
        print(f'Reference snapshot: {result["atom_count"]} atoms; {result["anisou_atom_count"]} ANISOU records')
        print('Elements: '+', '.join(f'{e}={n}' for e,n in result['element_counts'].items()))
        for row in result['atoms_of_interest']:
            k=row['key']
            print(f'{k["chain_id"]}:{k["residue_id"]}:{k["atom_name"]} {row["element"]} q={row["occupancy"]:g} reported B={row["reported_b_A2"]:g} {row["adp_representation"]}')
        print('Recorded XYZ/q/ADP snapshot; stored anomalous parameters ignored and untrusted.')
    else:
        print(f'Reference comparison: {len(report["nodes"])} explicit atom correspondences')
        print('Nodes                        Candidate A   Reference A     Difference A')
        for row in report['pair_distances']:
            label=' / '.join(row['node_ids'])
            values = [f'{row[key]:.4f}' if row[key] is not None else 'undefined'
                      for key in ('candidate', 'reference', 'candidate_minus_reference')]
            print(f'{label:<28} {values[0]:>11} {values[1]:>13} {values[2]:>16}')
        print('\n'.join(_reference_state_lines(report)))
        print(f'Complete XYZ/q/ADP snapshots and recipe angles: {result["files"]["report"]["relative_path"]}')
        print('Stored-coordinate internal geometry; no alignment, symmetry expansion, scattering fit or checkpoint adoption.')
    return 0


def _reference_atom_label(atom):
    """Keep case and all disambiguating fields visible in ordinary text."""
    key = atom['key']
    names = [('model', 'model_id'), ('chain', 'chain_id'), ('residue', 'residue_id'),
             ('component', 'component_id'), ('atom', 'atom_name')]
    names += [(label, field) for label, field in
              [('ins', 'insertion_code'), ('alt', 'altloc'), ('seg', 'segment_id')]
              if key[field]]
    if key['symmetry'] != 'x,y,z':
        names.append(('symmetry', 'symmetry'))
    return ' '.join(f'{label}={key[field]!r}' for label, field in names)


def _reference_state_lines(report):
    """Present verified recorded fields; do not recalculate or mutate the report."""
    adps = {'REPORTED_B_ONLY': 'reported B only',
            'ANISOU_AND_REPORTED_B': 'ANISOU + reported B'}
    lines = ['', 'Recorded atomic snapshots (q; reported B in A^2; C-R = candidate minus reference)',
             'Node          Source     Element         q   Reported B  ADP representation']
    for row in report['nodes']:
        for source in ('candidate', 'reference'):
            atom = row[source]
            label = row['node_id'] if source == 'candidate' else ''
            lines.append(f'{label:<13} {source:<10} {atom["element"]:<8} {atom["occupancy"]:>8.3f} '
                         f'{atom["reported_b_A2"]:>12.3f}  {adps[atom["adp_representation"]]}')
        lines.append(f'{"":13} {"C-R":<10} {"":8} {row["candidate_minus_reference_occupancy"]:>+8.3f} '
                     f'{row["candidate_minus_reference_reported_b_A2"]:>+12.3f}')
        lines.append('  C: '+_reference_atom_label(row['candidate']))
        lines.append('  R: '+_reference_atom_label(row['reference']))
        flags = []
        if not row['element_agrees']:
            flags.append('element differs')
        if not row['adp_representation_agrees']:
            flags.append('ADP representation differs')
        if flags:
            lines.append('  Review: '+', '.join(flags))
    if report['unmapped_candidate_nodes']:
        lines.append('Unmapped candidate nodes: '+', '.join(report['unmapped_candidate_nodes']))
    extra = report['unmapped_reference_atoms_of_interest']
    lines.append(f'Unmapped reference atoms of interest: {len(extra)}')
    for atom in extra:
        lines.append('  '+atom['element']+' '+_reference_atom_label(atom))
        lines.append(f'    q={atom["occupancy"]:.3f}; reported B={atom["reported_b_A2"]:.3f}; '
                     +adps[atom['adp_representation']])
    warnings = report['reference_inventory']['warnings']
    if any(warnings.values()):
        lines.append('Reference field warnings: '
                     f'{warnings["occupancies_outside_zero_to_one"]} occupancy values outside [0,1]; '
                     f'{warnings["negative_reported_b"]} negative reported B values')
    lines.append('Recorded fields only; reported-B differences do not compare ANISOU tensors.')
    lines.append('Stored anomalous parameters: untrusted and ignored.')
    return lines


def _fdp_scan(args):
    from .fdp_scan import create_plan, pending_count, run_scan, verify_scan
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'plan-fdp-scan':
        axes = {}
        for value in args.occupancies:
            node,sep,values = value.partition('=')
            if not sep or not node or node in axes:
                raise RecipeError('Use distinct NODE=Q,Q,... occupancy axes')
            axes[node] = [float(q) for q in values.split(',')]
        result = create_plan(args.run,args.seed,axes,max_trials=args.max_trials)
        report = None
    elif args.metal_action == 'run-fdp-scan':
        native = None
        if args.job_budget > 0 and pending_count(args.run,args.plan,args.resume):
            native = discover_phenix(load_config(),explicit=args.phenix_root)
        result = run_scan(args.run,args.plan,native=native,job_budget=args.job_budget,resume=args.resume)
        report = _json(args.run.expanduser().resolve()/result['files']['report']['relative_path'])
    else:
        result = verify_scan(args.run,args.scan)
        report = _json(args.run.expanduser().resolve()/result['files']['report']['relative_path'])
    serialized = json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle: handle.write(serialized)
    if args.json:
        print(serialized,end='')
    elif report is None:
        print(f'Occupancy scan planned: {len(result["points"])} points; limit {result["max_trials"]}')
        print('Plan: '+str(args.run.expanduser().resolve()/result['directory']['relative_path']))
        print('Plan ID: '+result['plan_id'])
        for point in result['points']:
            print('  '+', '.join(f'{n}={q:.2f}' for n,q in point['occupancies'].items()))
        print('Fitting settings fixed to the seed; no native jobs run.')
    else:
        print(f'Occupancy scan: {report["status"]}; {report["new_completed"]} new, {report["reused"]} reused, {report["pending"]} pending')
        for point in report['points']:
            vector=', '.join(f'{n}={q:.2f}' for n,q in point['occupancies'].items())
            trial=Path(point['trial']['relative_path']).parent.name if point['trial'] else '-'
            print(f'{point["state"]:<13} {trial:<12} {vector}')
            for site in point['sites']:
                print(f'  {site["node_id"]} {site["element"]}: fdp={site["f_double_prime"]:.6g}; reference={site["reference_f_double_prime"]:.6g}')
        if report['failure']: print('Stopped: '+report['failure']['error'])
        print('Report: '+str(args.run.expanduser().resolve()/result['files']['report']['relative_path']))
        print('Fixed-q diagnostic grid; no automatic structural choice or convergence claim.')
    return 2 if report and report['failure'] else 0


def _workbench(args):
    from .workbench import capture_catalog, open_workbench
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    mounts = {}
    for value in args.dataset:
        key, sep, path = value.partition('=')
        if not sep or not key or not path or key in mounts:
            raise RecipeError('Use distinct ID=PATH dataset mounts')
        mounts[key] = Path(path)
    if args.metal_action == 'serve-workbench':
        from .viewer import open_viewer, serve
        serve(open_viewer(_json(args.catalog), mounts), port=args.port)
        return 0
    if args.metal_action == 'capture-workbench':
        result = capture_catalog(_json(args.request), mounts)
    else:
        if args.site and not args.row:
            raise RecipeError('--site requires --row')
        workbench = open_workbench(_json(args.catalog), mounts)
        selection = _json(args.selection) if args.selection else workbench.initial_selection()
        if args.row:
            selection = workbench.select_row(selection, args.row, site_id=args.site)
        result = workbench.view(selection)
    serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(serialized)
    if args.json:
        print(serialized, end='')
    elif args.metal_action == 'capture-workbench':
        print(f'Workbench catalog: {result["label"]}; {len(result["datasets"])} datasets')
        print('Catalog: '+str(args.output))
        print('Verified saved evidence; dataset mount paths are not stored.')
    else:
        print(f'Workbench: {len(result["rows"])} visible linked rows')
        for row in result['rows']:
            scope = ' / '.join(row[key] for key in ('dataset_id','structure_id','hypothesis_id','result_id'))
            data = row['data']
            value = f"; fdp={data['f_double_prime']:.6g}" if 'f_double_prime' in data else ''
            print(f'{row["row_id"]}: {scope}; node={data["node_id"]}{value}')
        for detail in result['details']:
            report = detail.get('report', {})
            if 'pending' in report:
                print(f'{detail["dataset_id"]} / {detail["result_id"]}: {report["pending"]} pending scan points')
        print('Navigation snapshot only; reopen to reverify sources. No jobs, ranking or checkpoint selection.')
    return 0


def _import_restraints(args):
    from .phil_import import inspect_restraints, import_recipe
    raw = args.source.read_bytes()
    if args.mapping:
        if not args.recipe_id or not args.name:
            raise RecipeError('Mapping requires --id and --name')
        result = import_recipe(raw, _json(args.mapping), recipe_id=args.recipe_id, name=args.name).to_dict()
    else:
        if args.recipe_id or args.name:
            raise RecipeError('--id and --name require --mapping')
        result = inspect_restraints(raw)
    serialized = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(serialized)
    if args.json:
        print(serialized, end='')
    else:
        print(f"Imported {len(result['restraints'])} restraint terms; chemistry unqualified.")
        if not args.mapping:
            for selector in result['selectors']:
                print(f"{selector['id']}: {selector['selection']}")
            print('Map selectors explicitly before reuse; old residue numbers are not applied automatically.')
    return 0


def _fdp_count(args):
    from .fdp_count import capture_count, verify_count
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'count-fdp':
        result = capture_count(args.run,args.trial,_json(args.groups))
    else:
        result = verify_count(args.run,args.count_report)
    serialized = json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle: handle.write(serialized)
    if args.json:
        print(serialized,end='')
    else:
        path=args.run.expanduser().resolve()/result['files']['report']['relative_path']
        report=_json(path)
        print(f'Anomalous count evidence: {report["wavelength_A"]:.8g} A')
        for group in report['groups']:
            print(f'{group["group_id"]}: {group["modeled_site_count"]} modeled sites; {group["representation"]}')
            for row in group['elements']:
                equiv='unavailable' if row['effective_atom_equivalents'] is None else f'{row["effective_atom_equivalents"]:.6g}'
                ratio='unavailable' if row['response_ratio'] is None else f'{row["response_ratio"]:.6g}'
                print(f'  {row["element"]}: sum Q (occ)={row["occupancy_sum"]:.6g}; sum Q*fdp={row["q_weighted_fdp_e"]:.6g} e; expected={row["q_weighted_reference_e"]:.6g} e; ratio={ratio}; atom equivalents={equiv}')
            if group['warnings']: print('  Review: '+', '.join(group['warnings']))
        print('Conditional atom-equivalent evidence; no integer atom count or automatic structural choice.')
        print('Report: '+str(path))
    return 0


def _fdp_count_comparison(args):
    from .fdp_count_compare import build_count_comparison, verify_count_comparison
    if args.output and not args.output.parent.is_dir():
        raise RecipeError('Output parent directory must already exist')
    if args.metal_action == 'compare-fdp-count':
        result = build_count_comparison(args.run, args.trial, _json(args.groups))
    else:
        result = verify_count_comparison(args.run, args.comparison)
    serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x') as handle: handle.write(serialized)
    if args.json:
        print(serialized, end='')
    else:
        path = args.run.expanduser().resolve()/result['files']['report']['relative_path']
        report = _json(path)
        print(f'Cluster response comparison: {len(report["snapshots"])} audited trials; {report["wavelength_A"]:.8g} A')
        print('Trial / group: sum Q (occ); sum Q*fdp (e); expected (e); ratio; cancellation')
        for snapshot in report['snapshots']:
            trial = Path(snapshot['manifest']['relative_path']).parent.name
            for group in snapshot['groups']:
                ratio = 'undefined' if group['response_ratio'] is None else f'{group["response_ratio"]:.6g}'
                cancellation = 'undefined' if group['cancellation_fraction'] is None else f'{group["cancellation_fraction"]:.1%}'
                print(f'{trial} / {group["group_id"]}: {group["occupancy_sum"]:.6g}; {group["q_weighted_fdp_e"]:.6g}; '
                      f'{group["q_weighted_reference_e"]:.6g}; {ratio}; {cancellation}')
                if group['warnings']: print('  Review: '+', '.join(group['warnings']))
        compared = sum(p['status']=='COMPARED' for p in report['profiles'])
        print(f'{compared} matched one-variable profiles; full Q vectors, per-site values and controls: {path}')
        print('Coefficient diagnostics only; no integer count, convergence claim or checkpoint selection.')
    return 0


def _publish_fdp(args):
    from .publication import publish_fdp_inputs
    options = {} if args.max_input_bytes is None else {'max_input_bytes': args.max_input_bytes}
    receipt = publish_fdp_inputs(args.run, args.trial, args.archive, args.output,
                                max_trial_bytes=args.max_trial_bytes, **options)
    if args.json:
        print(json.dumps(receipt, indent=2, allow_nan=False))
    else:
        print(f"Published {len(receipt['attempts'])} recorded attempts; {len(receipt['parents'])} shared parents.")
        print('Publication identity: ' + receipt['record_sha256'])
        print('Historical review only; no new fit, reuse or retirement authority.')
    return 0


def _recorded_fdp(args):
    from .compact import read_projection
    from .input_archive import inspect_recorded_fdp
    options = {} if args.max_input_bytes is None else {'max_input_bytes': args.max_input_bytes}
    explicit = (args.archive_sha256, args.projection_id, args.expected_parent)
    if args.publication is not None:
        from .publication import inspect_published_fdp, inspect_published_fdp_batch, MAX_PUBLICATION_BYTES
        if not args.publication_id or any(p is not None for p in explicit):
            raise RecipeError('Publication requires its independent identity and cannot mix individual pins')
        publication = read_projection(args.publication, max_projection_bytes=MAX_PUBLICATION_BYTES)
        if args.all_trials:
            report = inspect_published_fdp_batch(args.archive, publication,
                publication_id=args.publication_id, **options)
        else:
            report = inspect_published_fdp(args.archive, publication,
                publication_id=args.publication_id, trial_id=args.trial_id, **options)
    else:
        if args.all_trials:
            raise RecipeError('--all-trials requires a pinned publication receipt')
        if args.publication_id is not None or any(p is None for p in explicit):
            raise RecipeError('Require archive/projection/parent pins or a pinned publication receipt')
        # Parent references are data, not instructions to reopen the source run.
        try:
            parent = read_projection(args.expected_parent, max_projection_bytes=16 * 1024)
        except RecipeError as exc:
            raise RecipeError('Cannot read expected parent JSON: ' + str(exc)) from exc
        report = inspect_recorded_fdp(args.archive, args.archive_sha256,
            projection_id=args.projection_id, trial_id=args.trial_id,
            expected_parent=parent, **options)
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
    else:
        # Build every row before printing: late failure must not leak a partial table.
        reports = report if args.all_trials else [report]
        lines = [f'{len(reports)} historical attempts'] if args.all_trials else []
        for row in reports:
            result = row['record']['result']
            lines.extend(['Historical result: ' + row['record']['trial_id'],
                          'Site / element | Q (occ) | B (Å²) | f″ (e) | Expected f″ (e)'])
            for site in result['sites']:
                lines.append(f"{site['node_id']} / {site['element']} | {site['occupancy']} | {site['b_iso']} | {site['f_double_prime']} | {site['reference_f_double_prime']}")
            lines.append(f"Rwork {result['r_work']}; Rfree {result['r_free']}; wavelength {result['wavelength_A']} Å")
        lines.extend(['No new scientific audit; current parent and native environment are not verified.',
                      'Scientific acceptance not assessed. No execution, reuse or retirement authority.'])
        print('\n'.join(lines))
    return 0


def _fdp_storage(args):
    from .storage import inspect_storage
    if args.output:
        if not args.output.parent.is_dir():
            raise RecipeError('Output parent directory must already exist')
        # An inventory must never add a file to an immutable trial directory.
        if args.output.resolve().is_relative_to(args.run.expanduser().resolve() / 'Metal'):
            raise RecipeError('Storage report must be outside the immutable Metal tree')
    report = inspect_storage(args.run, args.trial, max_bytes=args.max_bytes,
                             forecast=_json(args.forecast) if args.forecast else None)
    serialized = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x') as handle:
            handle.write(serialized)
    if args.json:
        print(serialized, end='')
    else:
        print(f"Frozen f″ storage: {len(report['samples'])} explicit trials; {report['logical_bytes']:,} logical bytes")
        print(f"Repeated content: {report['repeated_content_bytes']:,} bytes; not an estimate of safe deletion")
        print('Trial payload integrity only; parents excluded; no scientific replay or cleanup.')
        if report['forecast']:
            print(f"Current-layout scenario peak: {report['forecast']['scenario_peak_bytes']:,} bytes; not a guaranteed bound or disk reservation.")
    return 0


def _fdp_records(args):
    from .compact import project_trials, verify_projection, read_projection, encode
    if args.output:
        if not args.output.parent.is_dir():
            raise RecipeError('Output parent directory must already exist')
        if args.output.resolve().is_relative_to(args.run.expanduser().resolve() / 'Metal'):
            raise RecipeError('Projection must be outside the immutable Metal tree')
    options = dict(max_bytes=args.max_bytes, max_projection_bytes=args.max_projection_bytes)
    if args.metal_action == 'project-fdp-records':
        report = project_trials(args.run, args.trial, **options)
    else:
        report = verify_projection(args.run, read_projection(args.projection,
                                   max_projection_bytes=args.max_projection_bytes), **options)
    serialized = encode(report)
    if args.output:
        with args.output.open('xb') as handle:
            handle.write(serialized)
    if args.json:
        print(serialized.decode('utf-8'), end='')
    else:
        print(f"Frozen f″ projection: {len(report['records'])} attempts; {len(report['bases'])} shared experiment bases; {len(report['requests'])} input descriptors")
        print(f"Projection: {len(serialized):,} bytes; source trial payload: {report['source_trial_bytes']:,} bytes (parents excluded)")
        print('Full original source replay; no retirement or reuse authority. Original parents and native evidence remain required.')
    return 0


def _child_process(args):
    from .child_process import make_request, run_child, inspect_child, MAX_REQUEST_BYTES
    from .compact import read_projection
    if args.metal_action == 'prepare-fdp-child-process':
        report = make_request(args.prepared,parent_manifest_sha256=args.parent_manifest_sha256)
        if not args.output.parent.is_dir():raise RecipeError('Output parent directory must exist')
        if args.output.resolve().is_relative_to(args.prepared.expanduser().resolve()):
            raise RecipeError('Request output must be outside prepared inputs')
        with args.output.open('x') as handle:json.dump(report,handle,indent=2);handle.write('\n')
    elif args.metal_action == 'inspect-fdp-child-process':
        report = inspect_child(args.attempt,request_id=args.request_id)
    else:
        request = read_projection(args.request,max_projection_bytes=MAX_REQUEST_BYTES)
        native = discover_phenix(load_config(),explicit=args.phenix_root)
        report = run_child(args.prepared,args.parent_archive,request,request_id=args.request_id,
            attempt_directory=args.attempt,native=native,timeout_seconds=args.timeout,
            retry_from=args.retry_from,max_parent_disk_bytes=args.max_parent_disk_bytes)
    if args.json:print(json.dumps(report,indent=2,allow_nan=False))
    elif args.metal_action == 'prepare-fdp-child-process':
        print('Prepared child request: '+report['request_id'])
    else:
        print('Child process: '+report['status'])
        print('Stopped verified: '+str(report['stopped_verified']))
        print('Fresh explicit retry eligible: '+str(report['fresh_retry_eligible']))
        if not report['worker_bundle_pinned']:
            print('Legacy request: prepare a new helper-pinned request before execution.')
        print('Process evidence only; no scientific acceptance or retirement authority.')
    return 0 if args.metal_action=='prepare-fdp-child-process' or (report['status']=='COMPLETED' and report['stopped_verified']) else 2


def _child_inputs(args):
    from .child_inputs import verify_child_inputs
    from .child_process import MAX_REQUEST_BYTES
    from .compact import read_projection
    request=read_projection(args.request,max_projection_bytes=MAX_REQUEST_BYTES)
    report=verify_child_inputs(args.prepared,args.parent_archive,request,request_id=args.request_id,
        run_relative=args.run_relative,endpoint_relative=args.endpoint_relative,
        reader_control_policy=args.reader_control_policy,max_parent_disk_bytes=args.max_parent_disk_bytes)
    if args.json:print(json.dumps(report,indent=2,allow_nan=False))
    else:
        print('Protected parent/input derivation: verified')
        print('Source checkpoint: '+report['root_checkpoint_id'])
        print('Source kind: '+report['source_kind'])
        print('No fresh Free-R/scattering acquisition, native run or scientific acceptance.')
    return 0


def _audited_child(args):
    from .child_session import run_audited_child
    from .child_process import MAX_REQUEST_BYTES
    from .compact import read_projection
    request=read_projection(args.request,max_projection_bytes=MAX_REQUEST_BYTES)
    native=discover_phenix(load_config(),explicit=args.phenix_root)
    report=run_audited_child(args.prepared,args.parent_archive,request,request_id=args.request_id,
        run_relative=args.run_relative,endpoint_relative=args.endpoint_relative,
        session_directory=args.session,native=native,timeout_seconds=args.timeout,
        reader_control_policy=args.reader_control_policy,max_parent_disk_bytes=args.max_parent_disk_bytes,
        max_output_bytes=args.max_output_bytes)
    if args.json:print(json.dumps(report,indent=2,allow_nan=False))
    else:
        print('Frozen child audit: '+report['result']['freeze_audit'])
        print('Review: '+report['record_sha256'])
        print('Geometry, identity, count and fit remain for scientific review.')
    return 0


def _inspect_audited_child(args):
    from .child_session import inspect_audited_child
    report=inspect_audited_child(args.session,review_id=args.review_id)
    if args.json:print(json.dumps(report,indent=2,allow_nan=False))
    else:
        result=report['result']
        print('Saved conditional fit: '+report['review_id'])
        print(f"Rwork {result['r_work']:.4f}  Rfree {result['r_free']:.4f}  wavelength {result['wavelength_A']:.5f} Å")
        print('Site  Element  Q (occ)  B (Å²)  f″ (e)  Expected f″ (e)')
        for row in result['sites']:
            print(f"{row['node_id']}  {row['element']}  {row['occupancy']:.2f}  {row['b_iso']:.2f}  {row['f_double_prime']:.6f}  {row['reference_f_double_prime']:.6f}")
        flags=report['recorded_free_r']
        print(f"Recorded Free-R: {flags['label']} = {flags['test_value']} ({flags['status']})")
        print('Saved freeze audit replayed; no fresh parent, Free-R or scattering acquisition. Scientific review remains open.')
    return 0
