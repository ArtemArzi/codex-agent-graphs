# Scoped project routing changes

These patches preserve the reviewed configuration-only changes from the four
owning checkouts. Base commits and checksums are recorded in `manifest.json`.
They exclude unrelated dirty files, home configuration, authentication and
private resume material. Each owning checkout also receives a scoped local commit.

The CRM checkouts contain hundreds of unpublished development commits; ECC has
only a local marketplace origin and AI marketing has no remote. These portable
patches are published with the canonical routing source without publishing that
unrelated history or creating new project remotes.

Patches use zero context to avoid treating patch context markers as trailing
whitespace. Apply only against the recorded base in a clean disposable checkout:
`git apply --check --unidiff-zero <patch>` followed by
`git apply --unidiff-zero <patch>`. Preserve and inspect local changes first.
