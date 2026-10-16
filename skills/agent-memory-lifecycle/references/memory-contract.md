# Memory contract

Record these decisions in the existing project owner. Not every category needs
a new schema or separate service.

| Lifecycle | Decision |
| --- | --- |
| Admission | Which observations may be retained; explicit versus inferred; permitted writer and relevant authorization |
| Provenance | Source identity/version, observed/effective time, owner, scope and uncertainty |
| Reconciliation | Corrected/superseded facts, unresolved conflicts, source precedence and historical meaning |
| Retrieval | Who may see what, sufficient evidence, freshness checks and no-evidence behavior |
| Expiration | Product-defined validity, retention and rules for stale facts |
| Deletion | Which original, indexed, cached and derived representations are affected, and how completion is verified |
| Recovery | What survives restart, what can be reconstructed and how authority is rechecked |

Do not use free-form memory as the system of record for confirmed orders,
permissions or irreversible effects. Prefer stable references to those owners.
An observation, a derived interpretation and a reusable procedural lesson should
remain distinguishable; avoid silently promoting a failed run's narrative into
an operational rule.

For RAG, separate corpus admission/versioning, retrieval and answer grounding.
Dynamic prices, availability and permissions belong to their authoritative live
tools where the product specifies them. Empty search, unknown information,
truncated results and an authoritative negative answer differ.

Deletion tests must cover the representations actually used by the agent and
the applicable backup/retention contract. Do not promise total physical erasure
from a successful delete API response alone. Restrict fixtures to synthetic or
otherwise authorized data; no secret or customer-data transfer to new services.

Framework reference: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
distinguishes thread checkpoints and cross-thread stores. It does not choose the
application's business source of truth or its data policy.
