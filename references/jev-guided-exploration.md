# Jev-guided bounded exploration

Use this pattern when a workflow must search a broad candidate space: websites, documents, links, products, people, repositories, or other sources whose useful paths are not known in advance. The runner should expose many plausible options to Jev while keeping deterministic control of retrieval, state, budgets, and stopping.

## Separate discovery from direction choice

```text
goal + unresolved fields
  -> code and tools generate candidate directions
  -> normalize, deduplicate, and retain provenance
  -> pack context-bounded Jev judgments
  -> code updates a bounded frontier
  -> fetch selected pages or sources
  -> judge evidence and whether each page is worth expanding
  -> repeat until resolved, exhausted, or stopped
```

Code and existing search or browser tools should create the candidate set. Jev judges supplied candidates; it does not fetch pages, invent missing candidates, own the queue, or decide whether a budget may be exceeded. Give it as many relevant options as safely fit while preserving the goal, entity identity, unresolved field, candidate labels, local snippets, source ownership, and decision definition.

When the candidate set exceeds the context budget, split it into multiple self-contained calls. Repeat the stable goal and required identity context in every call. Record which candidates appeared in which batch, and verify that every eligible candidate was judged or explicitly excluded before pruning.

## Choose a judgment that matches the decision

- Use an independent Noul or Score for each candidate when several candidates may be useful or results from separate batches must remain comparable. Independent questions over the same state may be batched into one request.
- Use Choice when the next step is mutually exclusive and the supplied options form the intended choice set.
- For a large mutually exclusive set, shortlist within batches, then run a final Choice over the surviving candidates with their original evidence. A hierarchical or beam search can repeat this process at later depths.
- Do not directly add, maximize, or otherwise compare Choice probabilities from disjoint batches. Each probability is conditional on the options in its own call. Use identically defined per-candidate judgments or a final common comparison instead.
- Keep identity matching, evidence support, and exploration value separate when one answer could hide another failure. A page may match the entity while providing no useful evidence, or contain a useful term while referring to the wrong entity.

A narrow page-expansion question can ask whether a supplied page provides, or links to, likely primary evidence for a named unresolved field of a specified entity. The answer should drive a code-owned threshold and queue update. It should not authorize side effects or silently convert absence from one page into a global no-match.

## Maintain an explicit exploration state

The runner should maintain:

- the goal, entity identity, and unresolved required fields;
- a frontier of candidate directions with stable IDs, source, parent, depth, and priority evidence;
- a canonical visited-source set and duplicate mapping;
- selected and rejected candidates with the Jev question version, answer, probability or score, and reason;
- retrieved evidence and which requirement it may satisfy;
- current depth, page, call, time, token, and cost counters;
- the reason each branch or the complete run stopped.

For durable workflows, persist this state at replay-safe boundaries. For bounded workflows, keep it in the runner result or private trace so missing evidence can be attributed to discovery, batching, judgment, pruning, fetch, or validation.

## Bound breadth, depth, and recovery

Set budgets from the task's quality target and economics rather than choosing one universal number:

- maximum exploration depth;
- maximum pages or frontier expansions;
- maximum Jev calls and candidates per call;
- maximum active branches or beam width;
- maximum elapsed time, tokens, and model cost;
- maximum consecutive rounds without new candidates or validated evidence;
- bounded fetch and provider retries.

Stop when all required fields have accepted evidence, the frontier is empty, no candidate clears a calibrated continuation threshold, a configured budget is exhausted, or repeated rounds yield no new information. Canonical URL and content deduplication must prevent cycles. Budget exhaustion returns unresolved fields and the best remaining candidates; it must not be reported as a verified no-match.

Use a stronger LLM or the current agent only on an explicit exception path, such as generating a new search strategy after candidate generators are exhausted or resolving evidence that cannot be reduced to a typed judgment. Give that path its own trigger, context, budget, output contract, and measured benefit.

## Log enough to improve the search

For each expansion, record the run ID, candidate and batch IDs, parent and depth, normalized source, context and question versions, Jev output, selection or pruning reason, budget state, fetch result, new evidence, and stop cause. Keep source text and sensitive data in private traces; publish only sanitized aggregates unless the data is explicitly approved for release.

Measure result quality before celebrating fewer calls. Useful measures include required-field recall, asserted-field precision, evidence validity, candidate coverage before judgment, pages fetched, Jev and fallback calls, wall time, cost, and validated evidence added per expansion. Compare these measures on frozen cases and on unseen cases. Join gold answers only after the run so evaluation data cannot guide exploration.

## Test the control policy

At minimum, cover these behaviors with provider fakes and representative semantic cases:

- candidates beyond one context window are all included exactly once or explicitly excluded;
- each batch retains the goal, identity, unresolved field, provenance, and decision definition;
- disjoint Choice probabilities are never treated as globally comparable;
- a final common comparison or comparable per-item judgment can retain a useful candidate from any batch;
- low-value pages are pruned while pages likely to contain or link to primary evidence remain eligible;
- duplicate and cyclic links do not consume depth indefinitely;
- maximum depth, page, Jev-call, time, cost, and no-improvement limits stop predictably;
- budget exhaustion remains distinct from a complete searched-scope no-match;
- accepted evidence is preserved when another branch fails or escalates;
- trace data identifies whether a miss came from candidate generation, context packing, Jev judgment, pruning, fetch, or validation.
