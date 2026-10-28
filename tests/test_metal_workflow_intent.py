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


def test_search_inherits_chemistry_and_treats_chi_as_a_structural_branch():
    search = intent()['solution_search']
    assert search['status'] == 'PLANNED_NOT_IMPLEMENTED'
    chemistry = search['ligand_state']
    assert chemistry['default'] == 'inherit_NARestraints_CIF_Doctor_PostMR'
    assert chemistry['ordinary_search_changes_chemistry'] is False
    assert chemistry['state_changes_require_explicit_advanced_branch'] is True
    conformation = search['conformation']
    assert conformation['chi_search_enabled_by_default'] is False
    assert conformation['user_toggle_scoped_to_site_group'] is True
    assert conformation['disabled_preserves_current_conformation'] is True
    assert conformation['w_template_default'] == ['A:12', 'B:4']
    assert conformation['explicit_group_residue_mapping_required'] is True
    assert conformation['chi_states'] == ['anti-anti', 'anti-syn', 'syn-anti', 'syn-syn']
    assert conformation['move_connected_base_and_substituents'] is True
    assert conformation['rebuild_applicable_pairing_and_coordination_restraints'] is True


def test_many_job_search_preserves_branches_and_unique_experiment_accounting():
    search = intent()['solution_search']
    assert search['lineage']['branch_from_any_saved_node'] is True
    assert search['lineage']['overwrite_parent'] is False
    assert search['lineage']['compare_distinct_structures_within_dataset'] is True
    budget = search['budget']
    assert budget['illustrative_jobs_per_case'] == 75
    assert budget['illustration_is_default_or_cap'] is False
    assert budget['declared_jobs_cycles_time_and_processors'] is True
    assert budget['count_unique_new_jobs_separately_from_reused_rows'] is True
    assert budget['staged_adaptive_search_within_declared_budget'] is True


def test_auto_search_can_choose_provisional_work_without_final_acceptance():
    policy = intent()['solution_search']['decisions']
    assert policy['auto_mode_provisional_choice'] is True
    assert policy['auto_mode_can_choose_exact_next_seed'] is True
    assert policy['final_structure_requires_user_validation'] is True
    assert policy['automatic_checkpoint_selection'] is False
    assert policy['retain_multiple_promising_families'] is True
    assert policy['family_trial_count_is_confidence'] is False
    assert policy['support_axes'] == ['count', 'identity', 'occupancy', 'coordination_geometry']
    assert policy['unresolved_is_valid_outcome'] is True
    assert intent()['anomalous_diagnostics']['iteration']['selection_policy_scope'] == 'guided_default'


def test_map_evidence_is_optional_correlated_and_never_adds_a_site_by_color():
    maps = intent()['solution_search']['map_evidence']
    assert maps['display_toggle_changes_ranking'] is False
    assert maps['ranking_use_is_explicit'] is True
    assert maps['matched_region_resolution_phase_and_normalization_policy'] is True
    assert maps['independent_vote_from_fdp'] is False
    assert maps['positive_peak_automatically_adds_metal'] is False
    assert maps['unreliable_evidence_state'] == 'uninformative'
    assert set(maps['layers']) == {'2mFo-DFc', 'mFo-DFc', 'anomalous_difference_or_LLG', 'optional_omit'}


def test_normalized_plot_keeps_reference_and_site_identity_explicit():
    plot = intent()['solution_search']['response_plot']
    assert plot['reference_scope'] == 'element_and_dataset_wavelength'
    assert plot['percent_deviation'] == '100 * (f_double_prime_fit / f_double_prime_reference - 1)'
    assert plot['ratio_at_twice_expected'] == 2
    assert plot['percent_deviation_at_twice_expected'] == 100
    assert plot['candidate_encoding'] == 'soft_color'
    assert plot['site_encoding'] == 'line_width_with_labels_or_markers'
    assert plot['other_occupancies_fixed_or_separate_slices'] is True
    assert plot['site_correspondence_requires_explicit_mapping'] is True
    assert plot['raw_values_remain_available'] is True


def test_iodine_is_an_independent_control_before_optional_calibration():
    iodine = intent()['solution_search']['iodine_control']
    assert iodine['independent_recovery_before_optional_constrained_reference'] is True
    assert iodine['forced_reference_agreement_is_validation'] is False
    assert iodine['individual_and_joint_omission_controls'] is True
    assert iodine['retain_occupancy_adp_and_wavelength_assumptions'] is True
    assert iodine['I_Ag_recovery_guarantees_Ag_Ag_separation'] is False


def test_decision_logic_has_a_distinct_future_validation_milestone():
    validation = intent()['solution_search']['logic_validation']
    assert validation['status'] == 'PLANNED_NOT_IMPLEMENTED'
    assert validation['construction_success_proves_decision_quality'] is False
    assert validation['solved_answers_hidden_from_decision_engine'] is True
    assert validation['held_out_cases_for_threshold_evaluation'] is True
    assert set(validation['outcomes']) == {'correct_provisional_choice', 'appropriate_deferral', 'confident_wrong_choice', 'budget_and_resume_correctness'}


def test_multiple_site_groups_are_views_over_a_complete_structural_hypothesis():
    groups = intent()['solution_search']['site_groups']
    assert groups['status'] == 'PLANNED_NOT_IMPLEMENTED'
    assert groups['arbitrary_explicit_atom_and_residue_mapping'] is True
    assert groups['supports_multiple_groups_per_structure'] is True
    assert groups['global_pair_is_fixed_to_W_positions'] is False
    assert groups['view_switch_changes_scientific_selection'] is False
    assert groups['other_anomalous_sites_retained_with_explicit_policy'] is True
    assert groups['joint_or_separate_fit_scope_is_declared'] is True
    assert groups['reuse_key_includes_complete_model_and_groups'] is True


def test_context_expansion_does_not_change_scientific_inputs():
    context = intent()['solution_search']['context_expansion']
    assert context['status'] == 'PLANNED_NOT_IMPLEMENTED'
    assert context['neighbor_bases_groove_atoms_and_metals'] is True
    assert context['view_expansion_changes_parameters'] is False
    assert context['view_expansion_changes_recipe_or_experiment_key'] is False
    assert context['cross_group_edge_requires_explicit_recipe_revision'] is True
    assert context['shared_atom_and_edge_deduplication'] is True
    assert context['concrete_only_binding_when_no_reusable_role'] is True
    assert context['symmetry_context_requires_exact_operator_and_qualification'] is True


def test_storage_policy_preserves_recovery_without_faking_complete_cache_hits():
    storage = intent()['solution_search']['storage_retention']
    assert storage['status'] == 'PLANNED_NOT_IMPLEMENTED'
    assert storage['disk_budget_applies_across_campaign'] is True
    assert storage['reserve_peak_space_before_launch'] is True
    assert storage['stop_scheduling_if_safe_space_unavailable'] is True
    assert storage['tree_pruning_deletes_lineage'] is False
    assert storage['existing_numbered_runs_are_cleanup_targets'] is False
    assert storage['retained_inputs_must_be_self_contained_or_in_protected_verified_store'] is True
    assert storage['retain_resolved_parameters_commands_versions_and_seeds'] is True
    assert storage['retain_structured_values_freeze_audit_and_failures'] is True
    assert storage['retention_receipts_are_append_only'] is True
    assert storage['protect_active_selected_pinned_and_referenced_outputs'] is True
    assert storage['summary_reuse_distinct_from_full_artifact_reuse'] is True
    assert storage['missing_maps_or_models_are_complete_cache_hit'] is False
    assert storage['regeneration_creates_new_attempt'] is True
    assert storage['native_regeneration_guarantees_identical_bytes'] is False
    assert storage['validate_recovery_before_enabling_destructive_compaction'] is True
    assert storage['relocation_and_shared_reference_tests_required'] is True


def test_workbench_navigation_is_separate_from_execution_and_scientific_state():
    workbench=intent()['integration']['campaign']['workbench']
    assert workbench['status']=='implemented'
    assert workbench['explicit_dataset_mounts'] and workbench['replay_existing_artifact_verifiers']
    assert workbench['result_requires_exact_geometry'] and workbench['overlapping_view_groups']
    assert workbench['selection_bound_to_catalog'] and workbench['parent_switch_clears_children']
    assert workbench['row_opens_exact_parent_scope']
    assert not any(workbench[k] for k in ('mount_paths_persisted','groups_change_scientific_parameters',
        'camera_and_layout_in_scientific_state','native_execution','checkpoint_adoption','ranking','production_gui'))


def test_local_viewer_keeps_presentation_outside_scientific_authority():
    viewer=intent()['integration']['campaign']['viewer']
    assert viewer['shared_navigation_controller'] and viewer['verified_actual_coordinates']
    assert viewer['exact_atom_keys'] and viewer['saved_distance_restraint_overlays']
    assert viewer['camera_state_separate'] and viewer['loopback_only']
    assert not any(viewer[k] for k in ('scientific_edits','native_execution','checkpoint_adoption',
                                      'reference_coordinate_overlay'))


def test_environmental_b_is_branch_preparation_not_posthoc_scaling():
    policy=intent()['integration']['environmental_metal_b']
    assert policy['stage']=='after_fixed_geometry_before_fdp_occupancy_trials'
    assert policy['base_excludes_sugar_phosphate'] and policy['retain_separate_base_means']
    assert policy['default_cli_policy']=='base-mean'
    assert not policy['weighted_by_occupancy'] and not policy['native_worker_changed']


def test_planned_metal_screen_is_explicit_and_starts_from_discovered_sites():
    screen = intent()['integration']['metal_screen']
    assert screen['status'] == 'PLANNED_NOT_IMPLEMENTED'
    assert screen['explicit_recipe_required'] and not screen['changes_standard_autosol_gate']
    assert screen['initial_site_source'] == 'AutoSol'
    assert screen['initial_count'] == 'discovered_supported_free_metal_sites'
    assert screen['count_search_directions'] == ['fewer', 'more']
    assert screen['retain_covalent_anomalous_anchors']
    assert screen['use_autosol_phase_lineage']
    assert screen['solve_if_no_metal']['default'] is False
    assert screen['solve_if_no_metal']['separate_metal_free_branch']
    assert not screen['solve_if_no_metal']['failure_proves_absence']


def test_planned_refined_endpoint_and_ratio_trigger_preserve_scientific_boundaries():
    screen = intent()['integration']['metal_screen']
    assert screen['environment_b_source'] == 'completed_xyz_adp_open_refinement_endpoint'
    assert screen['parent_scaffold_b_is_quantitative_source'] is False
    assert screen['phase_policy_changes_require_new_comparison_basis']
    assert screen['production_endpoint_bridge_implemented'] is False
    trigger = screen['extra_site_trigger']
    assert trigger['suggested_ratio'] == 1.3 and trigger['configurable']
    assert trigger['requires_prepared_b_and_valid_fit']
    assert not trigger['proves_extra_metal']
    assert trigger['retain_parent_candidate']
    table = intent()['integration']['campaign']['viewer']['table_design']
    assert table['status'] == 'OPEN_PENDING_REAL_DATA'
    assert table['one_table_per_trial'] is False
    assert table['proposed_rows_per_multisite_trial'] == [1, 2]
    assert table['side_by_side_geometries'] and not table['implemented']


def test_planned_symmetry_mapping_preserves_sites_and_cluster_geometry():
    mapping = intent()['integration']['metal_screen']['symmetry_mapping']
    assert mapping['status'] == 'PLANNED_NOT_IMPLEMENTED'
    assert mapping['multiple_cell_offsets'] and mapping['retain_raw_sites_and_exact_transform']
    assert mapping['tied_matches_require_review']
    assert mapping['unambiguous_closest_copy_selected_automatically']
    assert mapping['target'] == 'closest_actual_model_atoms_or_declared_intended_site'
    assert mapping['connected_clusters_preserve_geometry']
    assert mapping['independent_sites_may_map_to_different_groups']
    assert not mapping['nearest_distance_proves_bond']
    assert not mapping['overwrite_autosol_output']
