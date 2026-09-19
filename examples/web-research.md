# Example: web research and evidence synthesis

This example offloads a repeatable read-only research pass while keeping changing research direction and credentialed navigation with the current agent.

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

- Duplicate tracking URLs collapse to one canonical source.
- An irrelevant source receives a low relevance result and is excluded by code.
- Conflicting but individually plausible sources return `needs_review` when the policy cannot choose safely.
- Citations in the LLM output are restricted to selected source IDs.
- Missing page text returns `needs_input` rather than guessing from a URL.
- Fetch failure and model failure remain distinguishable in diagnostics.

