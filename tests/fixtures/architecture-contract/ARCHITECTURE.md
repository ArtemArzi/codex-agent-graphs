# Accepted architecture

Decision A1: one process with payments and notifications business modules.
Payments owns payment data. Notifications can call payments.public.payment_label;
it must not import payments._store or access that storage by another route.
No change to this decision is authorized by the notification task.

Accepted and implemented: payments exposes a read-only public function.
Planned: notifications formats the public label as `Payment: paid` for payment 1.

New-module route: define its public contract and owned state, implement the
smallest scenario, register only if required, add behavior and boundary checks.
This fixture needs no persistent store, external integration or registration.

The project decisions above are self-contained. No external architecture lookup
is required to implement this existing contract.
