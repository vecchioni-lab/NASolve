"""Keep the planned metal workflow's scientific controls explicit, not runtime policy."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def intent():
    return json.loads((ROOT / "docs/metal-restraint-builder-intent.json").read_text())


def test_design_supports_three_metals_without_claiming_runtime_authority():
    spec = intent()
    assert spec["runtime_authority"] is False
    assert spec["status"] == "AUTHORING_CORE_IMPLEMENTED_GUI_PLANNED"
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


def test_camera_and_draft_edges_do_not_edit_scientific_coordinates():
    view = intent()["molecular_view"]
    assert set(view["camera_controls"]) >= {"zoom", "rotate_3d", "fit"}
    assert view["camera_changes_coordinates"] is False
    assert view["draft_edge_requires_explicit_add"] is True
    assert view["depth_preserved_for_six_site_cluster"] is True


def test_occupancy_iteration_retains_per_site_locks_and_parameter_roles():
    iteration = intent()["anomalous_diagnostics"]["iteration"]
    assert iteration["stages"] == ["broad_fdp_profile", "focused_fdp_profile", "conditional_occupancy_refinement"]
    assert iteration["default_local_step"] == 0.1
    assert iteration["per_site_centers_and_locks"] is True
    assert iteration["requires_explicit_seed_trial"] is True
    assert iteration["automatically_selects_next_center"] is False
    assert iteration["occupancy_refinement_fixes_fdp"] is True
    assert iteration["iteration_budget_required"] is True


def test_reuse_depends_on_the_complete_experiment_not_only_the_metal_tuple():
    reuse = intent()["anomalous_diagnostics"]["result_reuse"]
    assert reuse["complete_verified_results_only"] is True
    assert reuse["validate_artifact_checksums"] is True
    assert reuse["retain_original_execution_and_iteration_lineage"] is True
    assert reuse["metal_position_occ_fdp_alone_is_sufficient"] is False
    assert set(reuse["identity_inputs"]) >= {
        "full_model", "observations", "free_r", "wavelength_and_references",
        "restraints_and_dictionaries", "resolved_selections_and_groups",
        "effective_parameters_and_starts", "software_and_protocol_versions",
    }


def test_generated_model_integration_keeps_pair_order_and_fixed_fprime():
    contract=intent()['integration']
    assert contract['ordered_pair']=={'first':'A:12','second':'B:4'}
    assert contract['supplied_solved_model_required'] is False
    assert contract['f_prime_policy']=='fixed-reference'
    assert contract['first_control']=='one Hg'
    assert contract['second_control']=='mixed Au/Ag'


def test_campaign_switching_is_a_view_action_and_retains_distinct_inputs():
    campaign=intent()['integration']['campaign']
    assert campaign['switch_datasets_and_structures'] is True
    assert campaign['switch_changes_scientific_selection'] is False
    assert campaign['independent_dataset_observations'] is True
    assert set(campaign['identities']) >= {'campaign','dataset','run','checkpoint','context','hypothesis','round','trial'}
    assert campaign['retain_prior_and_phase_provenance'] is True
