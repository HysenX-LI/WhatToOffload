# Anonymous model design review

Score each dimension 0, 1 or 2 and cite concrete file/excerpt evidence, including
counterevidence. 0 = important omission/unsound choice; 1 = plausible but incomplete
or weakly justified; 2 = grounded, complete and proportionate for this packet.
- boundary: repeatability, variability, investment vs saved supervision; may select
  keep_agent, partial or full offload. One-off ambiguous interaction should not be
  scored lower for having no runner. Do not mechanically demand keep_agent either:
  a tiny justified aid may be proportionate.
- context: preserves identities, ordering/versions, policy, missing facts and relevant
  conversational context; no invented scope or assumptions.
- executor: deterministic work vs open interpretation vs human authority, supported
  by task evidence; no preference for a named model/runtime/library.
- handoff: errors, conflicts, missing information, stale approvals, side effects and
  caller ownership are explicit and safe.
- feasibility: plan/artifacts can actually be used with supplied tools and constraints;
  credible validation, modest scope. Assess a keep-agent operating plan on its own
  merits, not on absence of code. Model judgment is NOT an execution test.

Return JSON {scores:{boundary:{score,evidence},context:{score,evidence},executor:
{score,evidence},handoff:{score,evidence},feasibility:{score,evidence}},limitations:[str]}.
