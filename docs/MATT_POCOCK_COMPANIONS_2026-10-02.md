# Native Matt Pocock companions

The user authorized installation and native, conditional use in Project Start
and Task Delivery on 2 October 2026. The capabilities remain separate skills;
the owning workflows select them for a concrete task rather than run a new
pipeline.

| Companion | When it helps |
| --- | --- |
| writing-for-agents | Creating or substantially changing instructions, skills or document navigation |
| retro | An explicit retrospective or repeated observed environment/navigation/tool/check failure |
| to-questionnaire | A material answer belongs to a client or another knowledge owner |
| pr | Writing a PR description for already authorized work |
| grilling | Material unresolved outcome/ownership decisions, grouped with recommendations |
| domain-modeling | Resolving business terminology or durable decisions in existing owning documents |
| codebase-design | A concrete interface/module/dependency decision under project architecture |

## Sources and adaptations

The four new trees come from
[mattpocock/skills](https://github.com/mattpocock/skills) at
`d81f3a183412e71a5b1e84ca21bc1a35eea03a60` (29 September 2026). Complete useful
resources and the upstream MIT notice are preserved; `pr/CREDITS.md` retains
the upstream attribution to Humanlayer's show-me skill. The new bodies and
Codex metadata are local adaptations, not an unmodified upstream release.

The three existing helpers were admitted from the byte-identical Windows and
WSL installations observed on 2 October. Their original import commit is
unknown. Grilling now asks short rounds of material questions rather than
forcing one question at a time or a universal final confirmation. Domain
modeling resolves the project map first, supports both GLOSSARY and legacy
CONTEXT conventions, and preserves one glossary/decision owner. Codebase
design retains its technical resources and follows owning architecture plus
plain-language user communication.

All seven include native `agents/openai.yaml` with automatic invocation enabled.
Descriptions contain specific selection conditions. Retro diagnoses and
proposes changes; it does not apply them merely by being selected. Questionnaire
drafts are not automatically transmitted. PR formatting does not create a PR.
Existing host authorization, review and delegation policy remain authoritative.

No graph identities, schemas, roles or orchestration controllers were added.
The existing explicit-only grill-with-docs, to-spec, to-tickets, wayfinder and
setup-matt-pocock-skills retain their invocation policies and fallbacks. Existing
architectural examples and playbook precedence are preserved.

## Packaging and verification

The canonical installer and structural validator now include all seven complete
trees. Installer tests compare installed tree manifests, including metadata,
licenses and reference resources, in a temporary home. The skill-creator
validator checks supported structure, not model behavior.

For this installation, only these seven trees plus Project Start and Task
Delivery are selected for synchronization. The ordinary full installer also
manages configuration/runtime/roles, so it is not the live command for this
bounded update. Target preimages, backups, a replacement journal and reverse
conditional restoration protect user drift. Configuration and global
instructions remain separate surfaces.

Run `python3 scripts/check_all.py` before committing. Verify selected content
hashes in each home and keep the canonical source aligned with installed
adaptations. New conversations load the updated full instruction context;
on-disk eligibility does not prove automatic selection in future real work.

The MIT notices in these imported directories do not change the licensing of
unrelated repository content.
