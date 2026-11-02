---
name: memory-governance
description: "Governance layer for persistent memory: decides what deserves long-term storage, requires evidence before promotion, deduplicates and prunes stale entries. Use when a task proposes writing new persistent memory, promoting notes or logs into reusable memory, or cleaning up the memory store."
---

# Memory Governance

## Purpose

Use this skill when a task proposes to:

- write new persistent memory
- promote notes, traces, logs, summaries, or "lessons learned" into reusable memory
- consolidate memory through review or dreaming
- resolve contradictory memory records
- decide whether a candidate memory is safe to reuse

This skill is governance-first.
It does not assume that repeated observations are independent evidence.

## Canonical References

Read these documents first and treat them as canonical:

1. `docs/architecture/memory-governance.md`
2. `docs/architecture/verification-contract.md`
3. `docs/architecture/state-coherence-model.md`
4. `docs/evals/openclaw-task-evals.md`
5. `docs/evals/baseline-scorecard-2026-08.md`

If they disagree with older notes or historical artifacts, prefer the canonical
documents plus the current live state.

## Hard Gate

Memory expansion is allowed only after:

1. `verification contract`
2. `state inspection`
3. `eval baseline`

If any gate is missing, do not auto-promote memory.

Use only:

- `reject`, or
- `needs-review`

Never silently overwrite contradictory memory.
Never use `memory-core` dreaming as a bypass if the candidate remains incoherent with
the governance policy or if the required gates are not demonstrated.

## Memory Classes

Classify every candidate before deciding:

- `M0`: working trace, local scratch, non-persistent reasoning
- `M1`: evidence record, timestamped and scoped
- `M2`: scoped fact, reusable only inside declared scope
- `M3`: procedure or policy memory, normative and document-backed
- `M4`: derived heuristic, lesson learned or generalization from multiple traces

Default conservatism:

- `M0`: do not promote
- `M1`: promote only as evidence, not as global truth
- `M2`: promote only with full gate satisfaction
- `M3`: promote only if tied to a canonical document
- `M4`: default to `needs-review`

## Standard Procedure

Follow this order every time:

1. Identify the candidate claim exactly.
2. Classify the memory class `M0`-`M4`.
3. Check whether the source task satisfies the verification contract.
4. Inspect the relevant state layer and source of truth.
5. Check whether an eval baseline exists for this family of memory behavior.
6. Read the current activation config and verify whether memory is still
   `gated-requirements-not-satisfied` or has explicit evidence for
   `gated-requirements-satisfied`.
7. If activation remains gated, verify that `memory-core` dreaming is not enabled as
   an operational bypass.
8. Search for contradictions, duplicates, stale records, or correlated traces.
9. Return one `write_decision`: `promote`, `reject`, or `needs-review`.
10. Always record scope, `valid_from`, `validity_status`, source refs, and
    contradiction status.

## State Inspection Rules

Before storing memory, identify which layer the claim belongs to:

- requested
- session selected
- configured default
- effective runtime
- observed evidence

Do not collapse these layers into one fact.

If the claim is about the present operational state, the live runtime wins.
If the claim is historical, preserve timestamp and treat it as evidence history.

## Contradiction Handling

Classify contradictions before any write:

- `C1`: same-scope contradiction
- `C2`: temporal supersession
- `C3`: scope narrowing
- `C4`: evidence conflict

Required actions:

- `C1`: block promotion and request adjudication
- `C2`: mark older memory as superseded or stale, do not erase history
- `C3`: narrow the broader claim and prefer the specific one in retrieval
- `C4`: re-read the primary source of truth for the correct layer

No contradictory record may remain implicitly valid.

## Decision Rules

### Promote

Use `promote` only if all are true:

- memory class is explicit
- source refs are concrete
- verification contract is satisfied
- state inspection is complete
- eval baseline exists or the behavior is already covered by the baseline family
- contradictions are resolved or explicitly non-blocking
- scope is narrow enough to be reused safely

### Reject

Use `reject` when any of these apply:

- boilerplate or generic filler
- duplicated claim with no added evidence
- stale or already superseded fact
- no primary source of truth
- unsupported generalization from correlated traces
- not reusable outside the original task

### Needs-Review

Use `needs-review` when the candidate may be valuable but one of these remains open:

- contradiction not adjudicated
- independence of evidence unclear
- scope still ambiguous
- baseline coverage too weak for auto-promotion
- derived heuristic with possible downstream harm

## Required Output

Return the review in this format:

```text
memory class: M0 | M1 | M2 | M3 | M4
claim: ...
source refs:
- ...
- ...
source of truth: ...
scope: ...
valid_from: ISO-8601 timestamp | date | unknown
validity_status: valid | scope-limited | stale | uncertain | retracted
contradictions: none | C1 | C2 | C3 | C4
write_decision: promote | reject | needs-review
rationale:
- ...
- ...
activation_state: gated-requirements-not-satisfied | gated-requirements-satisfied | unknown
activation_config_refs:
- ...
- ...
```

## Do Not

- do not write memory just because it appears multiple times
- do not treat logs as present truth if live inspection is possible
- do not convert a task summary into reusable memory without proof quality
- do not promote `M4` heuristics as automatic truth by default
- do not enable broad memory expansion while activation remains
  `gated-requirements-not-satisfied`
- do not leave `memory-core` dreaming enabled while activation remains
  `gated-requirements-not-satisfied`

## Gated Activation State

If the workspace later enables broader memory expansion, require explicit evidence that
the activation state can move from `gated-requirements-not-satisfied` to
`gated-requirements-satisfied`:

- the verification contract is active in task closure
- state inspection is used for truth classification
- eval baseline exists and is maintained
- false promotion risk is controlled
- no dreaming-derived candidate bypasses the governance policy

Until then, memory must remain controlled and conservative.
