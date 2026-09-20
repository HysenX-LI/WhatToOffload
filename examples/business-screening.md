# Example: business intake and candidate screening

This example combines multi-label intake with candidate scoring. The normal path is automated; outreach, purchasing, or rejection remains behind human approval.

## Worked scenario: three regional launch projects

A launch team needs a procurement recommendation across several regional projects. Each project has its own document domain, required regions, budget and delivery window. Candidates submit a profile, a reference letter, an operations confirmation and revised quotations. The deliverable is a review of every candidate, an ordered shortlist for each project, a traceable cost comparison and a list of outstanding evidence requests.

The difficult cases are ordinary business cases: an attractive price belongs to a superseded quotation; a worldwide marketing claim conflicts with the signed coverage confirmation; a reference confirms general translation work but not the required regulated-document experience; a client explicitly disputes a vendor's claimed scope; and a quotation omits its currency. None of these should disappear from the final review merely because another candidate is easy to recommend.

1. Build a manifest of candidates and their project assignments, then validate required documents and identifiers.
2. Reconcile signed quotation revisions. Preserve the selected revision and exclude the superseded amount from comparisons.
3. Normalize currencies using supplied policy rates, apply inclusive budget and deadline limits, and compare verified coverage against required regions.
4. Compare the vendor's experience claim with its independent reference for the assigned domain. Distinguish corroborated experience, clearly unrelated work, explicit contradiction and insufficient evidence.
5. Route ambiguous semantic judgments through the chosen review path. Keep confidence separate from eligibility, and measure how often review is needed.
6. Combine those signals with hard constraints using an explicit precedence rule. Missing inputs, unresolved evidence and disqualification remain distinguishable.
7. Rank only eligible candidates, using a documented order and deterministic tie-breaker. A low price cannot compensate for a failed mandatory requirement.
8. Generate the evidence table, shortlists, exception queue and narrative brief. Validate totals, citations and counts before returning the package.

| Situation | Result | Evidence retained |
| --- | --- | --- |
| Corroborated domain experience and all hard gates pass | Eligible for ranking | Profile, reference, operational confirmation and current quote |
| Candidate explicitly lacks relevant experience | Excluded under the domain gate | The actual scope statement and reference |
| Candidate claims qualifying work but client disputes that scope | Needs review | Both conflicting statements |
| Reference does not establish what work was performed | Needs review | Missing evidence and the next question |
| Currency absent from the authoritative quotation | Needs input; no invented conversion | Current quote and missing field |
| Coverage or final delivery fails a mandatory condition | Excluded with every applicable reason | Signed confirmation and governing requirement |

The complete result must account for every candidate and every project. It can finish with some records awaiting input or review. The business decision to award work remains outside this bounded task.

This walkthrough describes the workflow pattern. The larger local benchmark's exact documents, task-specific Skill, reference answers and runner are intentionally not published; only its measurements and methodology appear under `benchmarks/results/`.

## Before

An agent reads an incoming opportunity, checks several independent eligibility conditions, compares possible vendors, writes a shortlist, and asks the user what to do. The same judgments and formatting recur for each intake.

## Proposed boundary

```text
opportunity + policy + vendor records
  -> validate required facts
  -> evaluate independent eligibility conditions
  -> score candidate dimensions
  -> apply code-owned policy and weights
  -> produce shortlist
  -> completed | needs_review | needs_input

approved shortlist
  -> prepare outreach or purchase
  -> needs_approval
```

Input:

```json
{
  "opportunity": {
    "summary": "Need a regional translation vendor for a regulated product launch.",
    "deadline": "2026-10-30",
    "regions": ["CN", "SG"]
  },
  "policy": {
    "requires_regulated_domain_experience": true,
    "requires_cn_coverage": true
  },
  "vendors": [
    {
      "id": "vendor-a",
      "profile": "...",
      "verified_regions": ["CN", "SG"],
      "price_band": "medium"
    }
  ]
}
```

## Node map

| Node | Location | Capability role | Concrete implementation | Why |
| --- | --- | --- | --- | --- |
| Validate dates and required fields | Runner | Deterministic code | Existing project language | Exact validation |
| Verify known region coverage | Runner | Deterministic code | Structured field lookup | Do not ask a model about supplied facts |
| Judge stated domain experience | Runner | Jev | Noul over profile and policy definition | Multiple candidates may independently satisfy the condition |
| Score communication fit and evidence quality | Runner | Jev | Separate Score questions | Each dimension has ordered, concrete levels |
| Apply hard gates and weights | Runner | Deterministic code | Policy configuration | Business policy stays explicit and auditable |
| Explain the shortlist | Runner | Smaller LLM | OpenAI-compatible completion | Generates readable prose from retained signals |
| Approve outreach or purchase | Human/current agent | Approval | Existing business process | Consequential external action |

## Key implementation shape

```python
def screen_candidates(payload, dependencies):
    missing = validate_business_input(payload)
    if missing:
        return needs_input(missing)

    judgments = dependencies.jev.evaluate_candidates(
        opportunity=payload["opportunity"],
        policy=payload["policy"],
        vendors=payload["vendors"],
    )
    ranked = rank_with_explicit_policy(
        vendors=payload["vendors"],
        judgments=judgments,
        policy=payload["policy"],
    )

    if ranked.review_rate_reason:
        return needs_review(
            summary=ranked.review_rate_reason,
            result={"leading_candidates": ranked.leading_candidates},
        )

    explanation = dependencies.llm.explain_shortlist(ranked.safe_signals)
    return completed({
        "shortlist": ranked.shortlist,
        "explanation": explanation,
        "next_action": "request_approval_before_outreach",
    })
```

The Jev layer produces reusable signals. Code controls disqualifying conditions and weights so a policy change does not require rewriting a semantic prompt.

## Result and approval

The screening invocation can complete with a shortlist. A separate invocation that prepares an email, submits an order, changes a CRM record, or rejects a vendor must return `needs_approval` before the external action.

## Representative tests

- A later signed quote replaces an earlier cheaper one; a missing currency cannot inherit an older revision's currency.
- Exact deadline and budget equality pass; one-day or one-cent excess fails.
- Missing input and disputed evidence cannot enter the shortlist, even at the lowest price.
- Status totals cover every input candidate once; every recommendation has the required evidence chain.
- Missing deadline or required policy evidence returns `needs_input`.
- Structured region mismatch is rejected by code without a model call.
- Several independent true conditions can coexist; the design does not force them into one Choice.
- Near-0.5 Noul values or flat Score distributions route to review according to validated policy.
- Ranking weights are tested independently from semantic judgments.
- No candidate receives outreach, purchase, or rejection automatically.
