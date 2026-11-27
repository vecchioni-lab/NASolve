"""Explicit original-only registered preparation under the existing request owner.

The native reader qualifies exact input interpretation, not applied image forces
or a publication topology. Historical intake-only requests remain held.
"""
from pathlib import Path
from .cif_dictionary_sites import _need

POLICY_ID = 'registered-original-preparation-execution-v1'


def execution_fields(policy, registered_backbone, qualify_no_repair, continuation_options):
    if policy is None:
        return {}
    _need(policy == POLICY_ID and registered_backbone is not None
          and qualify_no_repair is True and continuation_options is None,
          'Registered execution requires its explicit original-only policy, context and qualification; no ReadySet continuation')
    return dict(registered_execution_policy=POLICY_ID)


def review_execution_runtime(root, config, runtime):
    """Called only after the enclosing owner has bound acquisition and inputs.

    A no-usable result stays no-usable. Any selected runtime must pass original
    selection, exact frozen model/CIF/PHIL and registered native interpretation.
    Repaired/ReadySet selections refuse; no incomplete result becomes publishable.
    """
    if runtime is None:
        return None
    from .cif_registered_preparation_native import _review_original_selection
    return _review_original_selection(Path(root)/'inputs', sorted(config['components']),
                                      config['registered_backbone'], runtime)
