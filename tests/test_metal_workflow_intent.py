"""Keep the planned metal workflow's scientific controls explicit, not runtime policy."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def intent():
    return json.loads((ROOT / "docs/metal-restraint-builder-intent.json").read_text())


def test_design_supports_three_metals_without_claiming_runtime_authority():
    spec = intent()
    assert spec["runtime_authority"] is False
    assert spec["status"] == "PLANNED_NOT_IMPLEMENTED"
    assert spec["metal_counts"] == [1, 2, 3]
    assert spec["zero_metal_control"] is True
    assert spec["preview_changes_coordinates"] is False
    assert spec["preview_changes_covalent_topology"] is False


def test_fdp_scan_separates_fixed_and_fitted_parameters():
    scan = intent()["anomalous_diagnostics"]
    assert scan["fitted_parameters"] == ["f_double_prime"]
    assert set(scan["fixed_atomic_parameters"]) == {"xyz", "adp", "occupancy", "f_prime"}
    assert scan["occupancy_changes_between_trials_only"] is True
    assert scan["verify_effective_parameters_and_output_atoms"] is True
    assert scan["independent_siblings"] is True
    assert scan["requires_anomalous_observations"] is True
    assert scan["preserve_free_r"] is True


def test_ambiguity_and_selection_are_not_hidden_by_the_sweep():
    scan = intent()["anomalous_diagnostics"]
    assert scan["fdp_response_proves_identity"] is False
    assert scan["fdp_is_atom_count"] is False
    assert scan["allow_unresolved_result"] is True
    assert scan["automatic_checkpoint_selection"] is False
    assert scan["same_site_mixture_occupancy_sum_max"] == 1
    assert scan["independent_sites_share_occupancy_budget"] is False
    assert scan["native_job_budget_required"] is True
    assert scan["table_rows_bind_exact_trial_and_artifacts"] is True


def test_development_contracts_resolve_in_this_checkout():
    spec = intent()
    for path in [spec["contract"], spec["anomalous_diagnostics"]["contract"]]:
        assert not Path(path).is_absolute()
        assert (ROOT / path).is_file()
