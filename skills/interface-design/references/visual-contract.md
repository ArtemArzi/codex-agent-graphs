# Share a visual contract, not a universal preset

Use when several selected tools or edits must preserve one project's visual
decisions. Keep them in the existing DESIGN.md, surface brief or equivalent;
do not create a second design authority, registry or token system unnecessarily.

Record the direction/reference roles, typography roles, color meanings, spacing
rhythm, image/crop roles, interaction behavior and reduced-motion treatment.
Values come from the selected world and actual implementation. This file does
not choose fonts, prescribe a palette, snap all type down to Tailwind defaults,
or require a particular framework.

For a small page a few CSS custom properties may be enough. In a larger existing
system distinguish raw values, semantic roles and component-specific decisions
where that distinction helps. A component layer is optional; no universal
component-count threshold decides whether one is needed. Dark and light schemes
must be checked together with real content, not created by blind color inversion.

Before migrating, map existing values to the intended tokens and identify any
deliberate visual change. Add tokens alongside the current implementation, then
update affected consumers within the accepted scope. A nearest numeric value can
still change hierarchy or wrapping; inspect rendered output before calling the
migration equivalent. Preserve incumbent identity for a narrow refinement.

Pass the same accepted contract to the single visual owner, implementation and
verification path. Reconcile conflicts with product facts, accessibility and the
user's design policy. Consistency is a means to clarity, not proof of usability.

Source basis: Meshcode design-design-system and design-homepage, pinned in
[the selected source library](sources.lock.json). Its raw material, upstream
attribution and license remain unmodified; the procedure above is an independently
written adaptation without its fixed counts or mandatory full token architecture.
