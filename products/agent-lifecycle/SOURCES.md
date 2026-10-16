# Источники и перенос в стандарт

Исследование: 15.10.2026. Ссылки описывают основания решений; они не являются
исполняемыми зависимостями или свидетельством работоспособности этого пака.

## Локальная основа

В Agent Pet Project использованы учебная база `docs/learning/agent-testing`,
контракты поведения/качества, рабочие навыки агента и разборы ошибок проверок.
В базе сохранена пользовательская расшифровка «Как тестировать AI-агента чтоб.txt».
Метаданные не содержат автора, даты выступления и URL оригинала. Исследованы
расшифровка и подробный конспект; просмотр исходного видео не заявляется.
Материал остаётся в своём проекте и не публикуется в паке.

Перенесены четыре объекта проверки: обвязка, модель, память и инструменты;
разделение replay/live, outcome/trajectory, поиск/grounding, проверка оценщика,
повторы, исправления памяти и сбои. Неподтверждённые ссылки и численные
эвристики выступления не превращены в нормативные пороги. В частности,
`pass^5=25%` не означает 75% неудачных одиночных клиентских обращений.

## Научные работы

Версии соответствуют прочитанным текстам. Эксперименты не воспроизводились;
arXiv сам по себе не устанавливает рецензирование. Требования пака являются
нашими инженерными адаптациями, а не универсальными выводами авторов.

| Работа | Изученный материал | Перенос и ограничение |
| --- | --- | --- |
| [τ-bench, v1](https://arxiv.org/abs/2406.12045v1) | §3–4, Discussion | Проверка состояния/ответа и repeatability; reward может пропустить отсутствие согласия, поэтому policy trajectory проверяется отдельно |
| [LongMemEval, v2](https://arxiv.org/abs/2410.10813v2) | Problem Formulation, Experimental Setup/анализ дизайнов, Conclusion/Ethics | Extraction, multi-session, temporal, update, abstention; QA по историям не доказывает безопасность действий |
| [LongMemEval-V2, v1](https://arxiv.org/abs/2605.12493v1) | §3–5, Appendix E | Наблюдения, переходы, workflows/gotchas, latency; не измеряет полный E2E task success или online learning |
| [AgentChaos, v1](https://arxiv.org/abs/2608.06790v1) | Taxonomy, Trigger Verification, Threats to Validity | Доказывать срабатывание faults LLM-response; не приписывать работе проверку всех external-tool retries |
| [Why Do Multi-Agent LLM Systems Fail?, v3](https://arxiv.org/abs/2503.13657v3) | Dataset/annotation methods, taxonomy, interventions/discussion | MAST для диагностики проектирования/координации/проверки; метки не доказывают причинность и не ранжируют frameworks |
| [AgentDojo, v3](https://arxiv.org/abs/2406.13352v3) | Benchmark, utility definition, defenses/results, Conclusion | Раздельные utility/security checks и недоверенные результаты инструментов; ограниченный набор атак не доказывает общую безопасность |
| [MT-Bench/Chatbot Arena, v4](https://arxiv.org/abs/2306.05685v4) | Judge types/limitations/mitigations, agreement setup/results | Bias и калибровка; предпочтение к chat answer не равно правильности внешнего эффекта |
| [Ragas, v2](https://arxiv.org/abs/2309.15217v2) | Полный abstract | Разделять retrieval/context use/generation; полного сравнения современных библиотек не проводилось |

Одноимённые Memora/AgentMemBench не включены как опорное доказательство:
коллизии названий и идентификаторов требуют отдельной идентификации.
Проверки неизвестного исхода внешней записи основаны на инженерном контракте
и локальной практике, а не на утверждении об exactly-once гарантии этих работ.

## Инженерные источники и внешние навыки

- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents):
  простые достаточные patterns, различие workflows и agent-directed решения.
- [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents):
  целостный и избирательный контекст вместо накопления инструкций.
- [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents):
  graders, traces, maintenance и production observation.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence):
  checkpoints/stores; не готовая политика авторизации и данных приложения.
- [LangChain eval-engineering](https://github.com/langchain-ai/langchain-skills/blob/main/config/skills/eval-engineering/SKILL.md):
  изучены SKILL.md и verifier/environment references; заимствован принцип
  независимого проверяющего и управляемой среды, без обязательного Harbor/World Skill.
- [Deep Agents memory](https://github.com/langchain-ai/langchain-skills/blob/main/config/skills/deep-agents-memory/SKILL.md)
  и [LangGraph persistence skill](https://github.com/langchain-ai/langchain-skills/blob/main/config/skills/langgraph-persistence/SKILL.md):
  рассмотрены как опциональные адаптеры хранения.
- [LangSmith evaluator](https://github.com/langchain-ai/langsmith-skills/blob/main/config/skills/langsmith-evaluator/SKILL.md)
  и [trace](https://github.com/langchain-ai/langsmith-skills/blob/main/config/skills/langsmith-trace/SKILL.md):
  изучено содержимое, исполнение и совместимость SDK здесь не проверялись.
- [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md):
  сравнение пользы навыка с baseline; не сертификат E2E продукта.

Внешние `main`-ссылки изменяемы. Код и тексты этих навыков не включены и не
исполняются паком. При будущем подключении фиксируется конкретная ревизия,
проверяются актуальная документация, совместимость и условия распространения.

Существующие внутренние software/business/eval навыки — самостоятельные владельцы
своих исходников. Пак хранит только их имена и маршрутизацию. Отсутствие компаньона
не становится скрытым сетевым запросом или автоматической установкой.
