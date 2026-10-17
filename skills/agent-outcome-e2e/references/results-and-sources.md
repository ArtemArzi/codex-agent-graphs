# Results and evidence

| Status | Meaning |
| --- | --- |
| PASS | Applicable required criteria have sufficient supporting evidence on this candidate and scope |
| FAIL | A valid observation contradicts a required property |
| INCONCLUSIVE | Available evidence cannot establish the result, including an uncertain effect |
| INVALID | Setup, fixture, leakage, injection or verifier conditions prevent using the run for the intended measurement |
| NOT RUN | The check was not executed |

Several statuses can apply to different criteria in one run. For example, an
infrastructure problem does not erase an independently observed forbidden effect.
Define aggregation before running. Required unknown/invalid/not-run evidence
cannot silently become an overall PASS. Record how exclusions affect denominators.

Report per-case and critical failures before aggregate success, then regressions,
cost per successful process, useful-response/completion latency, retries and human
interventions. Include the raw evidence locations and candidate/environment identity.
Compare baseline and candidate on the same relevant workload and configuration.
If conditions differ, state the resulting uncertainty.

`pass@k` asks whether at least one of k trials succeeds; `pass^k` asks whether all
k succeed. With four tasks achieving 5, 4, 1 and 0 successes in five trials,
these are 75% and 25%, while individual-trial success is 50%. None directly
predicts the failure rate of a differently distributed client workload. Repeated
trials, paraphrases and reordered context test different questions; report them
separately. Use the project's thresholds and uncertainty appropriate to its risk.

Turn confirmed failures into targeted regression cases without rewriting prior
results. Diagnose agent, harness, environment and verifier separately. A known bad
baseline is evidence of an unresolved problem, not a reason to lower the bar.

Scientific and engineering sources read during pack research:

- [τ-bench v1, §3–4/Discussion](https://arxiv.org/abs/2406.12045v1): state/outcome and
  repeatability; correct reward can still miss consent-policy violation.
- [AgentDojo v3](https://arxiv.org/abs/2406.13352v3): separate utility/security checks
  using state and answers; bounded attacks do not prove general safety.
- [AgentChaos v1](https://arxiv.org/abs/2608.06790v1): verified fault triggering at
  LLM response layer. It does not establish external-write retry safety.
- [MAST v3](https://arxiv.org/abs/2503.13657v3): system design, coordination and task
  verification failure taxonomy, not proof of a particular cause or framework rank.
- [MT-Bench v4](https://arxiv.org/abs/2306.05685v4): judge bias and agreement for chat
  preferences; calibration does not replace effect checks.
- [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents):
  graders, trace inspection and ongoing evaluation alongside production observation.

Applicable method sections and limitations were read; experiments were not
reproduced. Requirements here are our engineering adaptations. Their inclusion
does not certify this skill or any downstream agent.
