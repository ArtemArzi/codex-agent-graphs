# Review integrity and skill selection

The 18 November audit covered the repository's 71 skill entrypoints, five versioned workflows, 20 Codex roles and two installations. The sum of skill sizes measures stored text. Codex loads the selected skills on demand.

## What changed

| Situation | Required behavior | Evidence |
| --- | --- | --- |
| A Research reviewer rejects a report | The obligation survives repair and resume until an independent pass applies to the current work and output. | [Research regression tests](../../skills/research/scripts/test_research_graph.py) |
| An accepted marketing document is edited or removed before archiving | History records the accepted digest and the observed file state separately. An available matching copy can be preserved. An inconsistent old archive with retained evidence is held. | [Archive tests](../../tests/test_artifact_lifecycle.py) |
| An ordinary tracked task needs review | The admitted scope and pinned graph version determine the reviewer. Material-risk acceptance still requires separate independent plan and result decisions. | [Routing contracts](../../tests/test_routing_workflow_contracts.py), [delivery integration](../../tests/test_ci_delivery_integration.py) |
| An existing role gets a deterministic settings update | Read back the expected value and the other affected settings. Changes to installer logic retain independent engineering review. The verified local baseline and published preimages protect customizations. | [Installer tests](../../tests/test_install.py), [Desktop normalization](../../tests/test_sync_desktop.py) |
| A brief already specifies the market, audience and output | Return the short answer directly. Load the full research procedure for a full study. The local last30days launcher and its source availability continue to govern evidence collection. | [NMT entrypoint](../../skills/nmt-market-research/SKILL.md), [business package checks](../../tests/test_business_package.py) |
| An interviewer, provider or external guide is optional | Use one default interview route, resolve project delivery conventions before provider tools, and consult an external design guide when a decision actually depends on it. | [Behavioral case inputs and rubrics](../../tests/fixtures/skill-cases/cases.json) |

A completed graph reports what was checked for its particular artifact. Model quality, live provider coverage and speed on production work need separate measurements. The migration keeps old run identities and does not rewrite archived acceptance records.
