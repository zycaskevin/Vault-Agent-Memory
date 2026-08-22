# Regression Evidence

## Regression test added or strengthened

No new test was needed. The existing baseline compatibility test already
detected the wording regression, and the VAM-001 boundary tests continue to
protect the extraction decision and frozen artifacts.

## Related tests executed

- `tests/test_subject_baseline.py::test_public_package_has_no_stale_private_governance_metadata`
- `tests/test_agent_setup.py`
- `tests/test_subject_sbe_traceability.py::test_real_collection_can_bind_synthetic_selected_nodes_without_writing`
- `tests/test_subject_progress_v2.py::test_real_git_completion_reconstructs_progress_prefix_and_passes_final_overlay`
- Complete `sddgov ci local-gate .`

## Unaffected paths sampled

The complete gate covered README commands, release parity, all 446
identity-isolated Subject nodes, and the disjoint repository suite. Frozen
Subject artifacts, agent setup, package behavior, and unrelated tests remained
green.
