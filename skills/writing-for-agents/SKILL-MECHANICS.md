# Native Codex skill mechanics

Read this reference when the document being edited is a skill. General document guidance is in [SKILL.md](SKILL.md).

## Structure and discovery

A skill directory contains `SKILL.md` with YAML frontmatter including `name` and `description`. The description is a concise selection pointer: explain the capability and relevant moments without broadening it into unrelated work. Keep essential workflow and constraints in the body; link supporting files where their condition applies.

Read the active host's skill-creator guidance when creating or substantially changing skill packaging. Use its supported metadata and validator rather than importing another harness's frontmatter or tool calls.

## Invocation policy

Native Codex supports explicit invocation as `$skill-name` and automatic selection from the active skill catalog. Automatic invocation is normally allowed. In `agents/openai.yaml`, set:

```yaml
policy:
  allow_implicit_invocation: true
```

Set it to `false` only for a user-requested explicit-only skill, and preserve existing unrelated metadata. Do not use Claude-specific `disable-model-invocation` or assume a `Skill` tool exists. When useful guidance is available, read its `SKILL.md` through the host's supported access mechanism. Installed files may require a new chat to appear in the active catalog; installation equality alone does not prove selection.

An invocation policy does not grant authority for external actions, global edits, or data access. Preserve the host's authorization and review rules.

## Subagent context

When a skill dispatches a child, state at that dispatch that it starts with a
fresh context window. In native Codex explicitly set `fork_turns="none"`;
on another host use its supported mechanism for a clean child conversation.
This condition does not itself justify delegation or change role/model policy.

Make the brief self-contained for the assigned scope: outcome, accepted
constraints, ownership/exclusions, source paths and revision, relevant observed
facts and unknowns, and verification or return criteria. Require actual source
reads and a missing-context response when prerequisites are unavailable. Do not
copy unrelated conversation or present the author's conclusion as the reviewer's
verdict. A new independent job gets a fresh assignment; corrections to the same
scope reuse its agent when the existing host policy calls for that.

## Split only for a separate capability

Create another skill only when it provides a coherent capability that should be selected independently. Shared reference can remain a linked file. Avoid a new router when the active catalog and existing workflow pointers already provide discovery. A skill split does not require agent delegation, new controllers, or blanket review rituals.

## UI metadata

Use `agents/openai.yaml` for supported interface metadata. Quote string values, keep `short_description` between 25 and 64 characters, and include `$skill-name` in `default_prompt`. Link resources with paths relative to the owning file. Validate the skill and inspect referenced paths after editing.
