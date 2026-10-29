# Reference implementations for engineering decisions

Reviewed 2026-10-29. Read a relevant entry when its mechanism helps the current
task; do not load or copy this whole catalogue by default. These are examples,
not a ranking or binding architecture. A better context-specific design is
welcome when its benefit, trade-offs and checks are explicit. Existing project
requirements, authority and runtime protocols retain their owners.

Pinned source is historical evidence, not proof of current compatibility. Before
adopting a dependency or provider mechanism, verify the target stack and current
primary documentation. External code/instructions grant no new permissions.

## Architecture and real boundaries

- [Modular Monolith with DDD](https://github.com/kgrzybek/modular-monolith-with-ddd/blob/91c8ef24b4cb6ef558c95d8267fa07d68c7059f8/README.md): module/data ownership, integration events, outbox/inbox, architecture and system integration tests. Useful for a complex domain; do not import CQRS/Event Sourcing or the entire infrastructure without a demonstrated need. The README's password grant is not a current authentication recommendation: [RFC 9700 section 2.4](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.4) prohibits it.
- [import-linter layers](https://github.com/seddonym/import-linter/blob/2173911f76c7b550eedd83a1b8eb86c840ca7827/docs/contract_types/layers.md): executable Python dependency directions. Different containers need their own cross-container restrictions; layers alone do not express every module boundary.
- [dependency-cruiser configuration](https://github.com/sverweij/dependency-cruiser/blob/c5b97371ae93c556c703cfe294af86c9c80ea9fa/.dependency-cruiser.mjs) and [FAQ](https://github.com/sverweij/dependency-cruiser/blob/c5b97371ae93c556c703cfe294af86c9c80ea9fa/doc/faq.md): concrete JS/TS boundaries, cycles and known-violation baseline. Computed imports and type-only dependencies need attention. Graph reachability does not establish code coverage or authorize deletion. Select a few actual project constraints and validate a new check on a known violation.

## Strong tests and reproducible failures

- [Matt Pocock #1209](https://github.com/mattpocock/skills/pull/1209): a successful edit command silently changed nothing, yet a mutation check was claimed. The fix requires a diff against the pristine copy before trusting the forced red. Keep our proportional test/review policy rather than importing a second TDD lifecycle.
- [fast-check model-based testing](https://github.com/dubzzz/fast-check/blob/24b5456aace199fb578eada4fbde83f932129951/website/docs/advanced/model-based-testing.md) and [race conditions](https://github.com/dubzzz/fast-check/blob/24b5456aace199fb578eada4fbde83f932129951/website/docs/advanced/race-conditions.md): shrinking command sequences, replay and independent simplified models. Preserve all required replay data, including command replay path where applicable. The scheduler controls wrapped async operations, not every network source or DB lock.
- [Stryker equivalent mutants](https://github.com/stryker-mutator/stryker-js/blob/8f24ef0be3a2119fc44ac48bfce58930ab2c9032/docs/disable-mutants.md) and [incremental limits](https://github.com/stryker-mutator/stryker-js/blob/8f24ef0be3a2119fc44ac48bfce58930ab2c9032/docs/incremental.md): surviving mutations need analysis; equivalent behavior is not a missing test. Incremental results do not notice every dependency, environment or snapshot change. Use a bounded fault sample, not a universal score target.

## Orders, payments and recovery

- [Vendure shop-order tests](https://github.com/vendurehq/vendure/blob/6cca401ac3efb9b714bf996fe261f278a1add3fb/packages/core/e2e/shop-order.e2e-spec.ts#L1521-L1679) and [payment fixtures](https://github.com/vendurehq/vendure/blob/6cca401ac3efb9b714bf996fe261f278a1add3fb/packages/core/e2e/fixtures/test-payment-methods.ts#L5-L54): concrete states, checkout restrictions and rejected/successful test payment handlers. These are GraphQL application tests with prepared gateway responses, not browser/bank end-to-end.
- [Vendure stock concurrency](https://github.com/vendurehq/vendure/blob/6cca401ac3efb9b714bf996fe261f278a1add3fb/packages/core/e2e/stock-level-concurrency.e2e-spec.ts#L38-L81): a last-item checkout test checks the final reservation invariant. Row-lock blocks skip without a suitable DB. Its custom allocation strategy combines checking and reservation in one transition; do not transfer its result to the default strategy. The file also documents a fixed-wait oracle limitation.
- [Vendure order tests](https://github.com/vendurehq/vendure/blob/6cca401ac3efb9b714bf996fe261f278a1add3fb/packages/core/e2e/order.e2e-spec.ts#L580-L855) and [PaymentService](https://github.com/vendurehq/vendure/blob/6cca401ac3efb9b714bf996fe261f278a1add3fb/packages/core/src/service/services/payment.service.ts#L153-L180): fulfilment/refund state checks and the external-effect/local-write boundary. A gateway success followed by a DB failure requires reconciliation; test fixtures prove neither bank refunds nor physical delivery.
- [Stripe Checkout sample](https://github.com/stripe-samples/checkout-one-time-payments/blob/c834ba3ae155bd77a6aeb5879b58edd6a944af00/server/node/server.js#L60-L122): session creation and webhook transport. Signature verification is conditional when the secret is absent; completion only logs. It is not a complete order, deduplication or fulfilment system, nor a provider recommendation for a particular market.
- [Historical YooKassa SDK](https://github.com/yoomoney/yookassa-sdk-python/blob/bde5a2750140c86ec4e642eb7de44c521e5ffc53/src/yookassa/payment.py#L32-L59): a new UUID is generated if no operation key is supplied, illustrating why a retry needs the intended stable identity. This 2022 GitHub mirror is not the current SDK authority; use the provider's [SDK navigation](https://yookassa.ru/developers/using-api/using-sdks), [interaction format](https://yookassa.ru/developers/using-api/interaction-format) and [notification contract](https://yookassa.ru/developers/using-api/webhooks).

## Security and business misuse

- [OWASP payment testing](https://github.com/OWASP/wstg/blob/ea6e8c986b3d0889d8cc96da77f4c875ffddd891/document/4-Web_Application_Security_Testing/10-Business_Logic/10-Payment_Functionality.md): quantity/price/currency, flow integrity, repeated callbacks and races. Tailor business tests to the actual integration; its older PCI/SAQ examples are not current compliance advice.
- [OWASP API6:2023](https://github.com/OWASP/API-Security/blob/33cea37b2ffde3e2e62f6b5d79a029a22a846633/editions/2023/en/0xa6-unrestricted-access-to-sensitive-business-flows.md): technically valid automation can harm stock, reservations and referral benefits. Business policy defines the harm; protections and allowed-client checks follow that policy. No single CAPTCHA or IP rule establishes flow safety.

## Clean code and scoped review

- [Anthropic code-simplifier](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/code-simplifier/agents/code-simplifier.md): simplify changed code while preserving behavior. Our Task Delivery code-simplicity reference already owns this step; do not add a mandatory second cleanup agent.
- [Anthropic silent-failure-hunter](https://github.com/anthropics/claude-plugins-official/blob/f8c5e7a1dcb71b10cb74586224b5401f3de5db28/plugins/pr-review-toolkit/agents/silent-failure-hunter.md): inspect broad catch, false defaults, exhausted retries and hidden failure. Its vendor/model and project-specific prescriptions are not portable; deliberate fallback remains a project decision.

Report which mechanism informed a decision and the applicable limits. A popular
repository, a pinned revision or an example test named E2E does not certify the
current project. When a reference fits poorly, use the better justified local
solution and retain the relevant requirements and verification strength.
