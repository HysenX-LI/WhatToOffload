# Example: business intake and candidate screening

This example combines multi-label intake with candidate scoring. The normal path is automated; outreach, purchasing, or rejection remains behind human approval.

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

- Missing deadline or required policy evidence returns `needs_input`.
- Structured region mismatch is rejected by code without a model call.
- Several independent true conditions can coexist; the design does not force them into one Choice.
- Near-0.5 Noul values or flat Score distributions route to review according to validated policy.
- Ranking weights are tested independently from semantic judgments.
- No candidate receives outreach, purchase, or rejection automatically.
