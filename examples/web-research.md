# Example: web research and evidence synthesis

This example offloads a repeatable read-only research pass while keeping changing research direction and credentialed navigation with the current agent.

## Worked scenario: preparing an SDK migration decision

A platform team must decide whether three services can migrate to an SDK before their next maintenance window. They need to establish the supported release, the support end date, the applicable runtime requirements, and whether a deprecated authentication method has a supported replacement. The supplied pack includes release notes, an API migration guide, a support matrix, archived documentation, an issue discussion, a vendor announcement and duplicate snapshots reached through tracking URLs.

The sources disagree in ways that require explicit handling. An old support table concerns the previous major release. A newer announcement describes a planned feature rather than a shipped one. Two URLs reproduce the same vendor statement and therefore do not provide independent corroboration. A community workaround is useful context but cannot establish the vendor's support commitment. One service runs on a runtime version that the migration guide no longer supports.

The workflow produces a claim-by-claim evidence matrix and a migration brief:

1. Validate the service inventory, migration questions, snapshot dates and required evidence policy.
2. Normalize URLs and deduplicate copied content while retaining provenance. Count underlying sources rather than URLs when assessing independence.
3. Extract candidate passages for each claim: release availability, support window, runtime compatibility and authentication migration.
4. Ask a separate support or relevance judgment for each claim/passage pair. A page relevant to one claim is not automatically evidence for the other three.
5. Apply version, date and source-authority rules in code. Retain incompatible claims in a conflict set instead of silently dropping them.
6. Join established requirements to the supplied service inventory. Exact runtime comparisons belong in code.
7. Generate a brief from selected passages, then validate that its citations resolve and its stated conclusions match the evidence matrix.
8. Return unresolved claims and the next evidence needed. A human or agent decides whether the investigation should expand beyond the original question.

| Claim | Evidence requirement | Expected boundary |
| --- | --- | --- |
| Release is available | Shipped release record for the correct version | Planned announcements do not satisfy this claim |
| Support lasts until a stated date | Applicable vendor support policy | Archive entries for another major version are excluded |
| Service can use the target SDK | Current runtime matrix plus supplied service version | An incompatible service gets a blocker, not a positive migration recommendation |
| Authentication replacement is supported | Current migration or API documentation | A community workaround alone routes to review |

The output includes a decision per claim, retained and rejected source IDs with reasons, per-service blockers, unresolved questions, and a cited brief. Successful completion means the bounded research pass is finished; it does not mean every migration question has a positive answer.

## Before

The agent repeatedly opens candidate pages, extracts the same fields, removes duplicates, judges relevance, checks whether claims have evidence, and summarizes the useful sources.

## Proposed boundary

```text
research brief + allowed sources
  -> fetch or receive page snapshots
  -> normalize and deduplicate
  -> judge relevance and evidence support
  -> select sources
  -> synthesize a cited summary
  -> completed | needs_review | needs_input | failed
```

Input:

```json
{
  "question": "Which public sources describe the release and current support window?",
  "pages": [
    {
      "url": "https://example.com/release-notes",
      "title": "Release notes",
      "text": "..."
    }
  ],
  "source_policy": {
    "prefer_primary": true,
    "minimum_independent_sources": 1
  }
}
```

The browser or connector can gather page content before invoking the runner. If automated fetching is part of the target project, it remains an existing-tool node with its own authorization, robots, login, and network policy.

## Node map

| Node | Location | Capability role | Concrete implementation | Why |
| --- | --- | --- | --- | --- |
| Fetch supplied URLs | Runner or current agent | Existing browser/API tool | Available connector or project client | Data access depends on the environment |
| Normalize and deduplicate | Runner | Deterministic code | Canonical URLs and content hashes | Exact, cheap, and testable |
| Judge relevance | Runner | Jev | Score with concrete relevance levels | Bounded semantic comparison between question and source |
| Check claim support | Runner | Jev | Noul per claim/evidence pair | Returns a reusable probability for each support condition |
| Select usable sources | Runner | Deterministic code | Policy thresholds and source rules | Policy belongs in code |
| Write cited synthesis | Runner | Smaller or stronger LLM | OpenAI-compatible chat completion | Open-ended prose generation from selected evidence |
| Change the research question | Current agent | Agent/user judgment | Host conversation | The goal is still being negotiated |

## Key implementation shape

```python
def research_pass(payload, dependencies):
    pages = normalize_and_deduplicate(payload["pages"])
    if not pages:
        return needs_input(["pages"])

    judgments = dependencies.jev.judge_sources(
        question=payload["question"],
        pages=pages,
    )
    selected = apply_source_policy(
        pages=pages,
        judgments=judgments,
        policy=payload["source_policy"],
    )

    if selected.review_required:
        return needs_review(
            summary="No source cleanly satisfies the evidence policy.",
            result={"leading_sources": selected.leading_sources},
        )

    synthesis = dependencies.llm.summarize_with_citations(
        question=payload["question"],
        sources=selected.sources,
    )
    return completed({"summary": synthesis, "sources": selected.sources})
```

Jev questions over the same source state should be batched when independent. The runner must not ask Jev to fetch pages, write the summary, or decide whether it has permission to use a credentialed source.

## Representative tests

- Several URLs copying one statement count as one underlying source.
- Conflicting claims about different versions are separated; unresolved same-version conflicts stay visible.
- A citation that exists but does not support its associated claim fails the semantic case evaluation.
- A report preserves incompatible services and unknown claims even when the majority of evidence is favorable.
- Duplicate tracking URLs collapse to one canonical source.
- An irrelevant source receives a low relevance result and is excluded by code.
- Conflicting but individually plausible sources return `needs_review` when the policy cannot choose safely.
- Citations in the LLM output are restricted to selected source IDs.
- Missing page text returns `needs_input` rather than guessing from a URL.
- Fetch failure and model failure remain distinguishable in diagnostics.
