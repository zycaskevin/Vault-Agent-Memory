# Engineering Records

## Issue

Include Evidence ID, Expected/Actual, Reproduction, SDD Reference, Risk, Non-scope, and Verification Plan.

## Commit

Use trailers when applicable:

```text
Evidence: DEP-...
Issue: #...
SDD: CAP-...
```

## PR

Include Problem Evidence, confirmed Root Cause, Fix Scope, Non-scope, Verification Evidence, Regression Evidence, limitations, and Rollback.

## Changelog

Describe the user-visible change. Reference the Evidence ID under an internal Evidence subsection; do not paste raw logs or internal secrets.

## Root Cause Hypothesis

State hypothesis, supporting evidence, contradicting evidence, falsification test, and conclusion.

## Fix Scope

State smallest sufficient change, in-scope components, explicit non-scope, and blast radius.

## Regression Evidence

Record the regression test, related checks, unaffected paths sampled, and any unverified boundary.

## Rollback

Record trigger, reversible steps, data compatibility, and post-rollback verification.
