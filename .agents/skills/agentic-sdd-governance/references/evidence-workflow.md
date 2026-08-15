# Evidence Workflow

## Red

Record expected versus actual behavior, SDD/Issue reference, deterministic reproduction, commit, branch, runtime, and environment. Preserve the failing check before changing code.

## Evidence

Select only the collectors required to distinguish plausible causes. Collect into `private/raw`, run local redaction, and record supporting and contradicting facts. Do not dump unrelated logs.

## Fix

Write one falsifiable Root Cause Hypothesis. Define the smallest sufficient Fix Scope, explicit non-scope, and blast radius. Classify L2 and prepare a Decision Package only when the proposed fix changes approved behavior, acceptance criteria, user-visible promises, privacy/cost/public contracts, or authority boundaries. An ordinary bug fix is not L2 solely because the observed broken behavior changes after the implementation is corrected.

## Green

Rerun the original failing check. Run targeted regression checks for the affected boundary. Do not delete or weaken a failing test to create green output.

## Proof

Complete verification, regression, limitations, and rollback. Confirm that only `shareable/artifacts` are referenced. Run strict verification, then generate the required local attachment block.

Advance phases exactly once with:

```bash
evidence transition <DEP> evidence
evidence transition <DEP> fix
evidence transition <DEP> green
evidence transition <DEP> proof
```
