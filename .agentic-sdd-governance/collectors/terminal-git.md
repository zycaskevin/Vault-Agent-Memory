# Terminal and Git Collectors

## Terminal (`terminal`)

Capture the exact targeted command, exit code, relevant stdout/stderr, runtime/tool version, and working tree state. Avoid full environment dumps and shell history.

```bash
pytest tests/test_target.py > failing-test.log 2>&1
evidence collect <DEP> --collector terminal --input failing-test.log
```

## Git (`git`)

Useful evidence includes:

- `git status --short`
- `git diff --stat` and a scoped diff
- `git log --oneline --decorate -n <small-number>`
- `git blame` for a narrow line range
- `git bisect` outcome using a deterministic test

Store the result in a text file and import it. Do not collect `.git/config`, credential helpers, signed remote URLs, reflogs unrelated to the task, or repository secrets. A commit correlation is a hypothesis until the failing behavior and relevant change are causally verified.
