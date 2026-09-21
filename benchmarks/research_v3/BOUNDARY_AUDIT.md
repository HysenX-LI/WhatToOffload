# Historical boundary audit, separate from historical scores

Inspected four sources: `public_v1/data/final/inputs.json`, its frozen `gold.json`,
`public_v1/TASK.md`, and `codex_v2/studies.py` semantic prompt. Historical files and
all recorded scores remain unchanged.

In `final-contact-partial-eligibility`, vendor e's profile says its team translated
regulated medical-device instructions and patient materials. The reference says:
“We commissioned unrelated marketing slogans only; no regulated document work was
in scope.” Neither text names a shared project, client engagement or quoted claim.
The profile is a broad capability assertion. Reference delivery in the same vendor
record establishes attribution to a supplier, not identity of a specific project.

The old task routes unrelated work to ineligible and explicit disputes to review.
The old semantic prompt likewise says “establishes other work only” versus “disputes
claimed scope”, without defining when the two scopes refer to the same claim.
The old gold says unrelated. Bounded Codex said conflict. That mismatch alone is
not evidence that the model made an objectively wrong judgment; the annotation
contract lacked this important identity boundary. The other vendor remains supported.

Under the prospectively declared v3 rules, e is unrelated: affirmative slogans-only
work on an unlinked engagement does not refute the broad capability claim. This is
a new rule interpretation recorded in exposed-regression.json, NOT a correction of
old gold or post-hoc regrading. The old 7/8 acceptance and no observed Skill build gain
remain exactly as published. The entire old final is now exposed regression material.

The v3 paired fixtures distinguish identical/different contracts, explicit project
aliases, partial support versus explicit denial, an unlinked bare denial versus
positive other work, and broad capability versus project-specific claims. Missing
linkage is never filled from the fact that a document was submitted as a reference.
Both direct-task and bounded-node prompts embed the same SEMANTIC_RULES.md verbatim.
