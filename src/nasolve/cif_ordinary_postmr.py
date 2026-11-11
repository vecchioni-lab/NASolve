"""Ordinary construction/NAR input entry into the existing immutable request.

This initializer is not an execution owner or a refinement-ready outcome. Resume
the published request with the existing complete-request executor, not this entry.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .cif_acquisition_sources import freeze_acquisition_sources
from .cif_phenix_configuration import configure_dictionary_engine
from .cif_postmr_request import initialize_postmr_dictionary_request, prepare_postmr_literal_inputs
from .phenix_runtime import PhenixInstallation


@dataclass(frozen=True)
class PreparedPostMRRequest:
    """Live execution arguments; the existing request owns durable evidence.

    Generation settings contain the caller environment and must not be serialized.
    No completed execution, selected model or checkpoint is implied by this value.
    """
    run_directory: Path
    request_directory: Path
    request: dict
    generation: dict = field(repr=False)


def initialize_ordinary_postmr_request(run_directory, phenix: PhenixInstallation, *,
        expected_dialect, coot_executable=None, data_root=None, allow_mr_review=False,
        modified_pairs_only=False, restraint_scope=None, allow_unreviewed_backbone=False,
        narestraints_builder=None, modified_pair_builder=None, generation_options=None,
        continuation_options=None, **execution_limits) -> PreparedPostMRRequest:
    """Prepare ordinary inputs once and publish a fresh complete request.

    Configuration/chemical permissions remain explicit. Existing constructors,
    source authority, literal compiler and request context gates own their rules.
    The default CLI remains unchanged. No legacy modifiers, cache adapter, ReadySet
    or request execution runs on this route. Failure retains all partial outputs;
    an existing PostMR directory cannot be prepared again in place.
    """
    from .postmr import _prepare_postmr
    if generation_options is not None and not isinstance(generation_options,dict):
        raise ValueError('Require explicit generation options')
    options = dict(generation_options or {})
    allowed = {'single_block_steps','timeout_seconds','max_attempts','bond_representation_policy'}
    if set(options)-allowed:
        raise ValueError('Unsupported ordinary generation option')
    configured = configure_dictionary_engine(phenix,expected_dialect=expected_dialect,**options)
    def initialize(inputs):
        root = inputs.run_directory/'PostMR'/'DictionaryEngine'
        sources, literal, request = [root/name for name in ('sources','literal','request')]
        if root.exists() or root.is_symlink():raise FileExistsError(root)
        freeze_acquisition_sources(list(inputs.components),sources,data_root=data_root,
            ready_set_executable=configured.ready_set_executable)
        literal_inputs = None
        if inputs.supplementary_phils:
            prepare_postmr_literal_inputs(inputs.model_path,list(inputs.supplementary_phils),sources,literal,
                data_root=data_root,ready_set_executable=configured.ready_set_executable)
            literal_inputs = literal
        components = [dict(code=code,generation=configured.generation) for code in inputs.components]
        record = initialize_postmr_dictionary_request(inputs.model_path,inputs.run_report,components,None,request,
            consumer=configured.consumer,ready_set_executable=None,supplementary_phils=list(inputs.supplementary_phils),
            literal_na_inputs=literal_inputs,frozen_sources=sources,construction_inputs=inputs.run_directory,
            continuation_options=continuation_options,**execution_limits)
        return PreparedPostMRRequest(inputs.run_directory,request,record,
            {code:dict(configured.generation) for code in inputs.components})
    result = _prepare_postmr(run_directory,configured.ready_set_executable,phenix_installation=phenix,
        coot_executable=coot_executable,environment=phenix.environment,data_root=data_root,
        allow_mr_review=allow_mr_review,modified_pairs_only=modified_pairs_only,restraint_scope=restraint_scope,
        allow_unreviewed_backbone=allow_unreviewed_backbone,narestraints_builder=narestraints_builder,
        modified_pair_builder=modified_pair_builder,_dictionary_handler=initialize)
    if not isinstance(result,PreparedPostMRRequest):raise ValueError('Ordinary request boundary was not reached')
    return result
