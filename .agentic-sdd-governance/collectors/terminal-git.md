# Terminal and Git Collectors

## Terminal (`terminal`)

Capture the exact targeted command, exit code, relevant stdout/stderr, runtime/tool version, and working tree state. Avoid full environment dumps and shell history.

```bash
umask 077
if ! mkdir -p <DEP>/private/raw; then exit 1; fi
if ! chmod 700 <DEP>/private/raw; then exit 1; fi
pytest tests/test_target.py > <DEP>/private/raw/failing-test.log 2>&1
status=$?
{
  printf '%s\n' 'command=pytest tests/test_target.py'
  printf 'exit status=%s\n' "$status"
  pytest --version
  git status --short
} > <DEP>/private/raw/failing-test-context.txt
collection_status=0
evidence collect <DEP> --collector terminal --input <DEP>/private/raw/failing-test.log || collection_status=$?
evidence collect <DEP> --collector terminal --input <DEP>/private/raw/failing-test-context.txt || collection_status=$?
if [ "$collection_status" -ne 0 ]; then
  exit "$collection_status"
fi
exit "$status"
```

Keep `status` and `collection_status` separate: a failing test must stay failing, and a failed evidence import must never be hidden by the original command's exit status.

## Git (`git`)

Useful evidence includes:

- `git status --short`
- `git diff --stat` and a scoped diff
- `git log --oneline --decorate -n <small-number>`
- `git blame` for a narrow line range
- `git bisect` outcome using a deterministic test

Store the result in a text file and import it. Do not collect `.git/config`, credential helpers, signed remote URLs, reflogs unrelated to the task, or repository secrets. A commit correlation is a hypothesis until the failing behavior and relevant change are causally verified.
