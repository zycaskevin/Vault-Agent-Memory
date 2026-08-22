# Verification

## Green command and result

From owner-private checkout
`~/.codex/sddgov-review-checkouts/PR498-builder-20260822`, with mode `0700`,
clean head `d355d32e442e388598b1ee502527839050d63559`, and formal GitHub origin:

```text
umask 022; env PYTHONPATH=. SUBJECT_MISSION_V5_PHASE=candidate GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.abbrev GIT_CONFIG_VALUE_0=40 /tmp/vam-python-path-vam001/python -m pytest -q -p no:cacheprovider tests/test_subject_development_mission_v5.py::test_mission_private_lifecycle_denies_private_file_replacement
```

Result: `1 passed in 0.52s`, exit 0.

## Before/after evidence

- Before: exact Reviewer Local Green below shared `/tmp` exited 2 at the named
  Mission V5 fixture, leaving the checkout clean.
- Deterministic cause: unrelated `/tmp` sibling activity is sufficient to make
  pinned `_repo_inputs` deny while the repo remains unchanged.
- After: the same failing node passes in the private stable checkout after the
  origin is bound to the formal ASCII GitHub URL.

## Remaining limitations

The targeted Green establishes the location/identity remediation. Merge remains
blocked until the Builder exact Local Green passes at the final audit head and
an independent Reviewer separately passes the exact final-head Local Green and
issues the protected Review receipt.
