"""Explicit, qualified process-local Phenix refinement compatibility execution.

The caller owns the process, inputs, preflight, immutable round and publication.
This module neither launches processes nor adopts a model or installs SDK files.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import tempfile

from .cif_parallelity_kernel import ParallelityKernel, parallelity_parameters
from .cif_refinement_output import synchronized_outputs, validate_output_observations, _digest, _hierarchy
from .cif_refinement_sites import observe_monomers, unavailable, validate_sites, validate_phase_observation

POLICY_ID = 'explicit-native-parallelity-refinement-v3'


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _save(path, value):
    """Publish a compact observation atomically within its already-owned folder."""
    descriptor, temporary = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(_canonical(value)+b'\n'); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _native_runtime():
    profile = json.loads(Path(__file__).with_name('data').joinpath('parallelity-native-profile.json').read_text())
    if platform.system() != profile['system'] or platform.machine() != profile['machine']:
        raise ValueError('Native parallelity runtime platform is not qualified')
    modules = {name: importlib.import_module(name) for name in profile['modules']}
    def verify():
        for name, module in modules.items():
            path = Path(module.__file__).resolve()
            if hashlib.sha256(path.read_bytes()).hexdigest() != profile['modules'][name]:
                raise ValueError('Native parallelity runtime source differs: '+name)
    verify()
    from cctbx import geometry_restraints as gr
    from cctbx.array_family import flex
    import cctbx_geometry_restraints_ext as extension
    if any(getattr(gr, name) is not getattr(extension, name) for name in (
            'parallelity', 'parallelity_proxy', 'parallelity_residual_sum')):
        raise ValueError('Native parallelity binding was already replaced')
    from iotbx.cli_parser import run_program
    from phenix.programs.phenix_refine import Program, PhenixRefineParser, custom_process_arguments
    driver_class=modules['phenix.refinement.driver'].refine
    writer=driver_class.write_after_run_outputs
    if (writer.__module__!='phenix.refinement.driver' or
            writer.__qualname__!='refine.write_after_run_outputs'):
        raise ValueError('Native final output binding was already replaced')
    def program(arguments, observe_output, observe_final=None):
        with synchronized_outputs(driver_class,observe_output,observe_final=observe_final):
            return run_program(program_class=Program, parser_class=PhenixRefineParser,
                custom_process_arguments=custom_process_arguments,
                unused_phil_raises_sorry=False, args=arguments)
    return gr, flex, program, profile, verify


def _monomer_mapping_class():
    from mmtbx.monomer_library import pdb_interpretation
    klass = pdb_interpretation.monomer_mapping
    if (klass.summary.__module__ != pdb_interpretation.__name__ or
            klass.summary.__qualname__ != 'monomer_mapping.summary'):
        raise ValueError('Native monomer summary binding was already replaced')
    return klass


def _run_observed(program, arguments, observe_output, sites, record, directory):
    """Optional observations share the existing native call and final writer."""
    klass = _monomer_mapping_class(); original = klass.summary
    record['chemistry_binding_restored'] = False
    pending_output = []
    def failed(exc):
        record.update(chemistry_observation=unavailable(sites, type(exc).__name__ + ': ' + str(exc)),
                      chemistry_model=None)
    try:
        with observe_monomers(klass, sites) as observer:
            def observe_final(refined, completed):
                try:
                    if not completed:
                        record['chemistry_observation'] = observer.snapshot(refined.model)
                        # The native writer increments its serial for final .def;
                        # resolve the PDB before that happens, never after return.
                        pending_output.append(Path(refined.ofm.get_file_name(ext='.pdb')))
                    elif record['chemistry_observation']['status'] == 'OBSERVED':
                        if (len(pending_output) != 1 or
                                _digest(_hierarchy(refined.model)) != record['chemistry_observation']['model_state_sha256']):
                            raise ValueError('Native writer changed the observed model state')
                        output = pending_output[0]
                        if not output.is_file() or output.is_symlink():
                            raise ValueError('Native written model is unavailable')
                        data = output.read_bytes()
                        record['chemistry_model'] = dict(sha256=hashlib.sha256(data).hexdigest(),size=len(data))
                except (AttributeError, TypeError, ValueError, OSError, OverflowError) as exc:
                    failed(exc)
                _save(directory/'result.json',record)
            refined = program(arguments, observe_output, observe_final)
            if refined.iparams.refinement.dry_run is True:
                try:
                    record['chemistry_observation'] = observer.snapshot(refined.model)
                except (AttributeError, TypeError, ValueError, OverflowError) as exc:
                    failed(exc)
            elif record['chemistry_observation'] is None:
                failed(ValueError('No final-writer chemistry observation was made'))
            return refined
    finally:
        record['chemistry_binding_restored'] = klass.summary is original


def run_compatible_refinement(arguments, *, evidence_directory, chemistry_sites=None):
    """Run the native program with explicit correction and retained observations.

    Only the recorded native source/platform profile is admitted. Every observed
    process/parameter combination is recorded once; these are usage observations,
    not proof of process ownership or death. The caller must isolate the process
    and bind files/receipts to its run before publication. In particular, actual
    refinement needs a successful caller-owned preflight first.
    """
    if not isinstance(arguments, list) or not all(isinstance(a, str) and a for a in arguments):
        raise ValueError('Require explicit native refinement arguments')
    sites = [dict(row) for row in validate_sites([] if chemistry_sites is None else chemistry_sites)]
    directory = Path(evidence_directory)
    directory.mkdir()  # A previous or partial observation is never overwritten.
    record = dict(schema_version=1, policy_id=POLICY_ID, status='RUNNING',
                  arguments=list(arguments), pid=os.getpid(), parent_pid=os.getppid(),
                  scientific_approval='NOT_RUN', binding_restored=False,
                  output_binding_restored=False,output_synchronization=[],
                  chemistry_observation=None,chemistry_model=None,chemistry_binding_restored=True)
    _save(directory/'result.json', record)
    gr = original = observed = kernel = None
    try:
        gr, flex, program, profile, verify = _native_runtime()
        record['native_profile'] = profile
        kernel = ParallelityKernel(gr, flex)
        original = gr.parallelity_residual_sum
        observations = directory/'calls'; observations.mkdir()
        seen = set()
        def observed(**kwargs):
            parameters = dict(site_count=len(kwargs['sites_cart']),
                proxies=parallelity_parameters(kwargs['proxies'], site_count=len(kwargs['sites_cart'])))
            digest = hashlib.sha256(_canonical(parameters)).hexdigest()
            identity = (os.getpid(), digest)
            if len(seen) >= 4096 and identity not in seen:
                raise ValueError('Native parallelity observation allowance exceeded')
            target = kernel(**kwargs)
            if identity not in seen:
                # Unique by process and complete parameters; never append one
                # duplicate inventory for every optimizer evaluation.
                row = dict(pid=identity[0], parent_pid=os.getppid(),
                           parameter_sha256=digest, parameters=parameters)
                path = observations/(str(identity[0])+'-'+digest+'.json')
                with path.open('xb') as handle: handle.write(_canonical(row)+b'\n')
                seen.add(identity)
            return target
        gr.parallelity_residual_sum = observed
        def observe_output(rows,restored):
            record.update(output_synchronization=rows,output_binding_restored=restored)
            _save(directory/'result.json',record)
        refined = (_run_observed(program,list(arguments),observe_output,sites,record,directory)
                   if sites else program(list(arguments),observe_output))
        if gr.parallelity_residual_sum is not observed:
            raise ValueError('Native parallelity binding changed during refinement')
        model = refined.model
        geo = model.restraints_manager.geometry
        if list(geo.site_symmetry_table.special_position_indices()):
            raise ValueError('Special-position refinement is not qualified for this route')
        labels = [atom.id_str() for atom in model.get_hierarchy().atoms()]
        parameters = parallelity_parameters(geo.parallelity_proxies, site_count=len(labels))
        dry_run = refined.iparams.refinement.dry_run
        if type(dry_run) is not bool:
            raise ValueError('Native program did not report its execution mode')
        cycles = 0 if dry_run else refined.macro_cycle
        if not dry_run and cycles != refined.params.main.number_of_macro_cycles:
            raise ValueError('Native program did not complete its requested cycles')
        if record['output_binding_restored'] is not True:
            raise ValueError('Native final output binding was not restored')
        validate_output_observations(record['output_synchronization'],
                                     dry_run=dry_run,atom_count=len(labels))
        validate_phase_observation(record,sites,dry_run=dry_run,labels=labels)
        verify()
        record.update(status='COMPLETE', dry_run=dry_run, macro_cycles=cycles,
                      atom_labels=labels, parallelity_parameters=parameters)
        return refined
    except BaseException as exc:
        record.update(status='FAILED', error=dict(type=type(exc).__name__, message=str(exc)))
        raise
    finally:
        if original is not None:
            gr.parallelity_residual_sum = original
            record['binding_restored'] = gr.parallelity_residual_sum is original
        if kernel is not None: record['parent_kernel_statistics'] = kernel.statistics()
        record['usage_observations'] = sorted(p.name for p in (directory/'calls').glob('*.json'))
        _save(directory/'result.json', record)
