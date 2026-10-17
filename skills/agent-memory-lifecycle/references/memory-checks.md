# Check memory behavior

Select cases from requirements, incidents and the affected change. Define initial
state, clock, owner and independent expected meaning before candidate runs.

| Case | Observe |
| --- | --- |
| Fact A, explicit correction B, new session | Current answer uses B; historical question may still require A |
| Service changes, unrelated time condition is omitted | Only the explicitly affected field changes |
| Relative date near midnight; replay next day | Date follows original message time and product timezone rules |
| Policy/corpus changes | Applicable version is used; old agreement/history is not silently rewritten |
| Unknown fact or false premise | Agent abstains or corrects the premise instead of inventing evidence |
| Same words from another owner | No foreign retrieval, output or derived-memory leakage |
| Summary or malicious source conflicts with authority | Instructions remain data; permission and business state are rechecked |
| Delete/correct, then retrieve in a later session | Active indexes/caches/derived paths follow the accepted lifecycle |
| Restart or forced compaction | Required facts survive through their real owner; no new consent is inferred |

Evaluate storage, retrieval and reading separately. Preserve evidence references
so an incorrect answer can be distinguished from missing context. A language
model choosing the query is a nondeterministic part even when search itself is
deterministic. Add source-grounding and integrated task checks as appropriate.

Use held-out variations for real-model evaluation; fix configuration and isolate
independent attempts. Measure useful answer quality, freshness and latency/cost.
Do not choose a memory implementation from recall alone or turn small-sample
success into a reliability guarantee.

Scientific basis:

- [LongMemEval, v2](https://arxiv.org/abs/2410.10813v2): extraction, multi-session,
  temporal, update and abstention abilities; indexing/retrieval/reading. Its QA
  benchmark does not establish agent action safety or a universal retention TTL.
- [LongMemEval-V2, v1](https://arxiv.org/abs/2605.12493v1): memory of web state,
  transitions, workflows and gotchas, with an accuracy/latency tradeoff. Fixed
  trajectories and reader do not measure online learning or full task success.

The lifecycle choices above are engineering adaptations of these findings and
product requirements, not a claim that the papers validate this skill.
