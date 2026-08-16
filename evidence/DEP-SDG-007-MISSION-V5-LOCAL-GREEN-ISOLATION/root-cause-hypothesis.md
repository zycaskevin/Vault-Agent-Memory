# Root Cause Hypothesis

## Hypothesis

Mission V5 imports retained sibling validator modules whose globals are
deliberately manipulated by adversarial tests. Running the file late inside one
shared pytest remainder process permits earlier test modules to leave a
different pinned-validator state than a clean Mission V5 process expects.

## Supporting evidence

- The 301 already-isolated lifecycle nodes all passed.
- Only one Mission V5 derivation test failed in the shared remainder.
- The exact failing node passed in a clean process.
- The complete 75-node Mission V5 collection passes when every node receives a
  fresh process and isolated HOME/TMPDIR/basetemp.

## Contradicting evidence

No production authorization acceptance changed, and the failure remained
fail-closed. The defect is deterministic gate reliability, not a security
bypass.

## Falsification test

Pin the Mission V5 collection count, execute every node through the existing
fresh-process harness, remove only that file from the remainder, and require
376/376 PASS. Any missing, duplicate, extra, or failing node falsifies the
hypothesis.

## Conclusion

Confirmed. Process isolation is the smallest sufficient fix; changing frozen
validator logic or weakening assertions is unnecessary and out of scope.
