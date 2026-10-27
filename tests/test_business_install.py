#!/usr/bin/env python3
"""Cross-root business installation contracts, using isolated synthetic homes."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


installer = module("business_test_installer", REPO / "scripts/install.py")
business = module("business_test_pack", REPO / "scripts/business_pack.py")


class BusinessInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.names = ["business-work", "example-skill"]
        self.pack = {"schema_version": 1, "id": business.PACK_ID, "version": "1.0.0",
                     "entrypoint": self.names[0], "managed_skills": self.names,
                     "update_owner": "canonical-repository-first",
                     "upstream_pins": {"example": {"repository": "https://github.com/example/source",
                                                    "commit": "a" * 40}}}
        self.pack_path = self.repo / "products/business-automation/pack.json"
        self.pack_path.parent.mkdir(parents=True)
        self.pack_path.write_text(json.dumps(self.pack))
        for name in self.names:
            source = self.repo / "skills" / name
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\nNew {name}\n")
        self.metadata = self.repo / "skills/business-work/references/installation.json"
        self.metadata.parent.mkdir()
        self.metadata.write_text(json.dumps({"schema_version": 2, "package_id": business.PACK_ID,
                                            "package_version": "1.0.0", "skills": self.names,
                                            "update_owner": "canonical-repository-first",
                                            "pins": {"example": {"repo": "example/source", "commit": "a" * 40}}}))
        self.wsl = self.base / "wsl-user/.codex"
        self.desktop = self.base / "desktop-user/.codex"
        for home in (self.wsl, self.desktop):
            home.mkdir(parents=True)
            (home / "config.toml").write_text("model='unchanged'\n")
            (home / "auth.json").write_text('{"test":"protected"}')
            (home / "AGENTS.md").write_text("owned instructions")
        self.root = self.desktop / ".agents/skills"
        self.root.mkdir(parents=True)
        self.alias = self.wsl.parent / ".agents/skills"
        self.alias.parent.mkdir()
        self.alias.symlink_to(self.root, target_is_directory=True)
        self.homes = [("wsl", self.wsl), ("desktop", self.desktop)]
        self.prior = self.root / self.names[0]
        self.prior.mkdir()
        (self.prior / "SKILL.md").write_text("local old skill")
        self.original = installer.manifest(self.prior)
        (self.root / "unrelated").mkdir()
        (self.root / "unrelated/SKILL.md").write_text("user skill")
        self.protected = {p: p.read_bytes() for home in (self.wsl, self.desktop)
                          for p in home.iterdir() if p.is_file()}
        self.protected[self.root / "unrelated/SKILL.md"] = b"user skill"
        self.patches = [mock.patch.object(installer, "REPO_ROOT", self.repo),
                        mock.patch.object(installer, "SKILLS_ROOT", self.repo / "skills")]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.temp.cleanup()

    def run_pack(self, action="install", homes=None, root=None):
        return business.run(action, self.homes if homes is None else homes, root, api=installer)

    def assert_unchanged(self):
        self.assertEqual(self.original, installer.manifest(self.prior))
        self.assertFalse((self.root / self.names[1]).exists())
        self.assertEqual(self.protected, {p: p.read_bytes() for p in self.protected})

    def test_shared_alias_installs_once_and_second_run_preserves_mtime(self):
        with mock.patch.object(installer, "replace_directory", wraps=installer.replace_directory) as writes:
            with mock.patch.object(installer, "skills_install_lock", wraps=installer.skills_install_lock) as locks:
                result = self.run_pack()
        self.assertEqual(len(self.names), writes.call_count)
        self.assertEqual([mock.call(self.root.parent)], locks.call_args_list)
        self.assertTrue(self.alias.is_symlink())
        self.assertEqual(str(self.root), result["resolved_root"])
        self.assertEqual("1.0.0", result["version"])
        times = {p: p.stat().st_mtime_ns for p in self.root.rglob("*")}
        second = self.run_pack()
        self.assertTrue(all(change["status"] == "in-sync" for change in second["changes"]))
        self.assertIsNone(second["backup"])
        self.assertEqual(times, {p: p.stat().st_mtime_ns for p in times})
        self.assertEqual("ok", self.run_pack("verify")["status"])
        self.assertFalse((self.wsl / "skills").exists())
        self.assertFalse((self.desktop / "skills").exists())
        self.assertEqual(self.protected, {p: p.read_bytes() for p in self.protected})

    def test_plan_and_verify_use_same_resolution_without_writes(self):
        with mock.patch.object(installer, "replace_directory") as writes:
            plan = self.run_pack("plan")
            verify = self.run_pack("verify")
        writes.assert_not_called()
        self.assertEqual(plan["resolved_root"], verify["resolved_root"])
        self.assertEqual("failed", verify["status"])
        self.assertFalse((self.root.parent / "backups").exists())
        self.assert_unchanged()

    def test_legacy_duplicate_rejects_before_lock_or_any_write(self):
        duplicate = self.wsl / "skills" / self.names[0]
        duplicate.mkdir(parents=True)
        (duplicate / "SKILL.md").write_text("legacy skill")
        with mock.patch.object(installer, "skills_install_lock") as locks:
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        locks.assert_not_called()
        self.assertEqual("legacy skill", (duplicate / "SKILL.md").read_text())
        self.assert_unchanged()

    def renamed_skill(self, root, declaration):
        skill = root / "renamed-custom-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {declaration}\ndescription: existing user skill\n---\nUser content\n")
        return skill

    def test_same_root_renamed_frontmatter_duplicate_rejects_before_write(self):
        duplicate = self.renamed_skill(self.root, "business-work")
        before = installer.manifest(duplicate)
        with mock.patch.object(installer, "skills_install_lock") as locks:
            with self.assertRaises(installer.InstallError):
                self.run_pack("plan")
        locks.assert_not_called()
        self.assertEqual(before, installer.manifest(duplicate))
        self.assert_unchanged()

    def test_cross_root_renamed_quoted_frontmatter_duplicate_rejects_before_write(self):
        for declaration in ('"business-work"', "'business-work'", '"business-work" # retained alias'):
            with self.subTest(declaration=declaration):
                duplicate = self.renamed_skill(self.wsl / "skills", declaration)
                before = installer.manifest(duplicate)
                with mock.patch.object(installer, "skills_install_lock") as locks:
                    with self.assertRaises(installer.InstallError):
                        self.run_pack()
                locks.assert_not_called()
                self.assertEqual(before, installer.manifest(duplicate))
                shutil.rmtree(duplicate)
        self.assert_unchanged()

    def test_renamed_frontmatter_duplicate_introduced_during_staging_prevents_replacement(self):
        (self.wsl / "skills").mkdir()
        with self.stage_hook(lambda: self.renamed_skill(self.wsl / "skills", '"business-work"')):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assert_unchanged()
        self.assertTrue((self.wsl / "skills/renamed-custom-skill/SKILL.md").is_file())

    def test_same_root_nested_frontmatter_duplicate_rejects_before_write(self):
        duplicate = self.renamed_skill(self.root / "group/inner", '"business-work"')
        before = installer.manifest(duplicate)
        with mock.patch.object(installer, "skills_install_lock") as locks:
            with self.assertRaises(installer.InstallError):
                self.run_pack("plan")
        locks.assert_not_called()
        self.assertEqual(before, installer.manifest(duplicate))
        self.assert_unchanged()

    def test_cross_root_nested_frontmatter_duplicate_rejects_before_write(self):
        duplicate = self.renamed_skill(self.wsl / "skills/group/inner", "'business-work'")
        before = installer.manifest(duplicate)
        with mock.patch.object(installer, "skills_install_lock") as locks:
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        locks.assert_not_called()
        self.assertEqual(before, installer.manifest(duplicate))
        self.assert_unchanged()

    def test_nested_frontmatter_duplicate_introduced_during_staging_prevents_replacement(self):
        (self.wsl / "skills/group").mkdir(parents=True)
        with self.stage_hook(lambda: self.renamed_skill(self.wsl / "skills/group/inner", '"business-work"')):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assert_unchanged()
        self.assertTrue((self.wsl / "skills/group/inner/renamed-custom-skill/SKILL.md").is_file())

    def test_nested_duplicate_inside_existing_skill_boundary_is_discovered(self):
        outer = self.root / "unrelated/SKILL.md"
        outer.write_text("---\nname: unrelated-native-skill\n---\n")
        duplicate = self.renamed_skill(outer.parent / "inner", "business-work")
        before = installer.manifest(duplicate)
        with mock.patch.object(installer, "skills_install_lock") as locks:
            with self.assertRaises(installer.InstallError):
                self.run_pack("plan")
        locks.assert_not_called()
        self.assertEqual(before, installer.manifest(duplicate))
        outer.write_bytes(self.protected[outer])
        self.assert_unchanged()

    def test_hidden_nested_duplicate_is_ignored_like_native_discovery(self):
        duplicate = self.renamed_skill(self.root / ".hidden/group", "business-work")
        before = installer.manifest(duplicate)
        self.assertEqual("ok", self.run_pack("plan")["status"])
        self.run_pack()
        self.assertEqual("ok", self.run_pack("verify")["status"])
        self.assertEqual(before, installer.manifest(duplicate))

    def test_internal_directory_aliases_and_cycles_deduplicate_physical_discovery(self):
        group = self.root / "group"
        unrelated = self.renamed_skill(group, "unrelated-native-skill")
        (self.root / "group-alias").symlink_to(group, target_is_directory=True)
        (group / "cycle").symlink_to(self.root, target_is_directory=True)
        context = business.resolve(self.homes, None, installer)
        roots = {entry[0] for entry in context["identities"].values()}
        discovered = list(business.discovered_skills(roots, installer))
        self.assertEqual(1, discovered.count(unrelated / "SKILL.md"))
        self.assertEqual(len(discovered), len(set(discovered)))
        self.assertEqual("ok", self.run_pack("plan")["status"])
        self.assert_unchanged()

    def test_internal_alias_to_managed_skill_does_not_create_another_native_identity(self):
        self.run_pack()
        alias = self.root / "business-alias"
        alias.symlink_to(self.prior, target_is_directory=True)
        self.assertEqual("ok", self.run_pack("verify")["status"])
        context = business.resolve(self.homes, None, installer)
        roots = {entry[0] for entry in context["identities"].values()}
        discovered = list(business.discovered_skills(roots, installer))
        self.assertEqual(1, discovered.count(self.prior / "SKILL.md"))
        self.assertTrue(alias.is_symlink())

    def test_internal_skill_file_alias_deduplicates_native_identity(self):
        self.run_pack()
        alias = self.root / "a-file-alias/SKILL.md"
        alias.parent.mkdir()
        alias.symlink_to(self.prior / "SKILL.md")
        self.assertEqual("ok", self.run_pack("verify")["status"])
        context = business.resolve(self.homes, None, installer)
        roots = {entry[0] for entry in context["identities"].values()}
        discovered = list(business.discovered_skills(roots, installer))
        self.assertEqual(1, discovered.count(self.prior / "SKILL.md"))
        self.assertNotIn(alias, discovered)
        self.assertTrue(alias.is_symlink())

    def test_external_skill_file_alias_rejected_before_content_read_or_lock(self):
        external = self.base / "external-file-source"
        external.mkdir()
        target = external / "SKILL.md"
        target.write_bytes(b"\xffoutside content must not be read")
        alias = self.root / "group/file-alias/SKILL.md"
        alias.parent.mkdir(parents=True)
        alias.symlink_to(target)
        real = business.declared_name
        def bounded_read(skill, api):
            self.assertFalse(skill.resolve().is_relative_to(external))
            return real(skill, api)
        with mock.patch.object(business, "declared_name", side_effect=bounded_read):
            with mock.patch.object(installer, "skills_install_lock") as locks:
                with self.assertRaises(installer.InstallError):
                    self.run_pack()
        locks.assert_not_called()
        self.assertTrue(alias.is_symlink())
        self.assert_unchanged()

    def test_external_directory_alias_fails_closed_before_lock_without_scanning_target(self):
        external = self.base / "external-discovery-source"
        external.mkdir()
        (external / "SKILL.md").write_text("---\nname: business-work\n---\n")
        alias = self.root / "group/external-alias"
        alias.parent.mkdir()
        alias.symlink_to(external, target_is_directory=True)
        real = business.declared_name
        def bounded_read(skill, api):
            self.assertFalse(skill.is_relative_to(external))
            return real(skill, api)
        with mock.patch.object(business, "declared_name", side_effect=bounded_read):
            with mock.patch.object(installer, "skills_install_lock") as locks:
                with self.assertRaises(installer.InstallError):
                    self.run_pack()
        locks.assert_not_called()
        self.assertTrue(alias.is_symlink())
        self.assert_unchanged()

    def test_native_name_scalar_forms_and_unrelated_nested_name_are_inventory_safe(self):
        unrelated = self.root / "unrelated/SKILL.md"
        for scalar in ("other-name # comment", "'other-name' # comment", '"other-name" # comment',
                       '"other\\u002dname"'):
            with self.subTest(scalar=scalar):
                unrelated.write_text(f"---\nname: {scalar}\nmetadata:\n  name: business-work\n---\nname: business-work\n")
                self.assertEqual("other-name", business.declared_name(unrelated, installer))
                self.assertEqual("ok", self.run_pack("plan")["status"])
        for key in ('"name"', "'name'"):
            unrelated.write_text(f"---\n{key}: other-name\n---\n")
            self.assertEqual("other-name", business.declared_name(unrelated, installer))
        unrelated.write_bytes(self.protected[unrelated])
        self.assert_unchanged()

    def test_ambiguous_native_name_declarations_fail_closed_before_lock(self):
        skill = self.root / "renamed-custom-skill"
        skill.mkdir()
        source = skill / "SKILL.md"
        fronts = ("name: >-\n  business-work", "name: &alias business-work", "name: *alias",
                  'name: "business\\x2dwork"', "name: unrelated\nname: business-work",
                  '{"name": "business-work"}', '"na\\u006de": business-work')
        for front in fronts:
            with self.subTest(front=front):
                source.write_text(f"---\n{front}\n---\n")
                with mock.patch.object(installer, "skills_install_lock") as locks:
                    with self.assertRaises(installer.InstallError):
                        self.run_pack()
                locks.assert_not_called()
                self.assert_unchanged()

    def test_canonical_frontmatter_name_must_match_manifest_member(self):
        source = self.repo / "skills" / self.names[1] / "SKILL.md"
        source.write_text("---\nname: business-work\n---\n")
        with mock.patch.object(installer, "skills_install_lock") as locks:
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        locks.assert_not_called()
        self.assert_unchanged()

    def test_conflicting_modern_root_requires_explicit_but_cannot_duplicate_names(self):
        other = self.wsl / ".agents/skills"
        other.mkdir(parents=True)
        with self.assertRaises(installer.InstallError):
            self.run_pack()
        self.run_pack("plan", root=self.root)
        (other / self.names[1]).mkdir()
        (other / self.names[1] / "SKILL.md").write_text("other version")
        with self.assertRaises(installer.InstallError):
            self.run_pack(root=self.root)
        self.assert_unchanged()

    def test_explicit_new_root_rejected_if_existing_members_elsewhere(self):
        target = self.base / "new/skills"
        with self.assertRaises(installer.InstallError):
            self.run_pack(root=target)
        self.assertFalse(target.parent.exists())
        self.assert_unchanged()

    def fresh_homes(self):
        return [("fresh-one", self.base / "fresh-one/.codex"),
                ("fresh-two", self.base / "fresh-two/.codex")]

    def test_one_fresh_environment_defaults_user_modern_root(self):
        fresh = self.fresh_homes()[:1]
        expected = fresh[0][1].parent / ".agents/skills"
        plan = self.run_pack("plan", homes=fresh)
        self.assertEqual(str(expected), plan["resolved_root"])
        self.assertFalse(expected.exists())
        self.run_pack(homes=fresh)
        self.assertEqual("ok", self.run_pack("verify", homes=fresh)["status"])

    def test_multiple_fresh_environments_need_explicit_shared_root(self):
        fresh = self.fresh_homes()
        with self.assertRaises(installer.InstallError):
            self.run_pack(homes=fresh)
        self.assertFalse(fresh[0][1].parent.exists())
        explicit = self.base / "shared-modern/skills"
        result = self.run_pack(homes=fresh, root=explicit)
        self.assertEqual(str(explicit), result["requested_root"])
        self.assertEqual("ok", self.run_pack("verify", homes=fresh, root=explicit)["status"])

    def test_existing_root_lock_preserved(self):
        lock = self.root.parent / ".skills-install.lock"
        lock.write_text("other owner")
        with self.assertRaises(installer.InstallError):
            self.run_pack()
        self.assertEqual("other owner", lock.read_text())
        self.assert_unchanged()

    def test_failed_second_member_rolls_back_first_member(self):
        real = installer.replace_directory
        def failure(source, target, backup, **kwargs):
            if target.name == self.names[1]:
                raise OSError("injected failure")
            return real(source, target, backup, **kwargs)
        with mock.patch.object(installer, "replace_directory", side_effect=failure):
            with self.assertRaises(installer.InstallError) as raised:
                self.run_pack()
        self.assertEqual([], raised.exception.partial_install["rollback_conflicts"])
        self.assertFalse((self.root.parent / ".skills-install.lock").exists())
        self.assert_unchanged()

    def test_rollback_preserves_external_concurrent_edit_and_backup(self):
        real = installer.replace_directory
        def failure(source, target, backup, **kwargs):
            if target.name == self.names[1]:
                (self.prior / "external.txt").write_text("concurrent owner")
                raise OSError("injected failure")
            return real(source, target, backup, **kwargs)
        with mock.patch.object(installer, "replace_directory", side_effect=failure):
            with self.assertRaises(installer.InstallError) as raised:
                self.run_pack()
        self.assertIn(str(self.prior), raised.exception.partial_install["rollback_conflicts"])
        self.assertEqual("concurrent owner", (self.prior / "external.txt").read_text())
        backups = list((self.root.parent / "backups").rglob("business-work/SKILL.md"))
        self.assertEqual(["local old skill"], [p.read_text() for p in backups])

    def stage_hook(self, hook):
        real = installer.shutil.copytree
        def staged(source, target, *args, **kwargs):
            result = real(source, target, *args, **kwargs)
            if Path(source).name == self.names[0]:
                hook()
            return result
        return mock.patch.object(installer.shutil, "copytree", side_effect=staged)

    def test_preimage_changed_during_staging_is_preserved(self):
        with self.stage_hook(lambda: (self.prior / "SKILL.md").write_text("external change")):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assertEqual("external change", (self.prior / "SKILL.md").read_text())
        self.assertFalse((self.root / self.names[1]).exists())
        self.assertFalse(list(self.root.glob(".*graph-install*")))

    def test_source_changed_during_staging_has_no_installed_write(self):
        source = self.repo / "skills" / self.names[0] / "SKILL.md"
        with self.stage_hook(lambda: source.write_text("source changed")):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assert_unchanged()

    def test_all_sources_and_preimages_rechecked_after_lock(self):
        real = installer.skills_install_lock
        @contextlib.contextmanager
        def lock(parent):
            with real(parent):
                (self.repo / "skills" / self.names[1] / "SKILL.md").write_text("source race")
                yield
        with mock.patch.object(installer, "skills_install_lock", side_effect=lock):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assert_unchanged()

    def test_target_preimage_rechecked_after_lock(self):
        real = installer.skills_install_lock
        @contextlib.contextmanager
        def lock(parent):
            with real(parent):
                (self.prior / "SKILL.md").write_text("external lock race")
                yield
        with mock.patch.object(installer, "skills_install_lock", side_effect=lock):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assertEqual("external lock race", (self.prior / "SKILL.md").read_text())
        self.assertFalse((self.root / self.names[1]).exists())

    def test_alias_retarget_during_staging_is_rejected(self):
        other = self.base / "different-root"
        other.mkdir()
        def retarget():
            self.alias.unlink()
            self.alias.symlink_to(other, target_is_directory=True)
        with self.stage_hook(retarget):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assertEqual([], list(other.iterdir()))
        self.assert_unchanged()

    def test_new_legacy_duplicate_during_staging_prevents_replacement(self):
        duplicate = self.wsl / "skills" / self.names[0]
        def add_duplicate():
            duplicate.mkdir(parents=True)
            (duplicate / "SKILL.md").write_text("concurrent legacy skill")
        with self.stage_hook(add_duplicate):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assert_unchanged()
        self.assertEqual("concurrent legacy skill", (duplicate / "SKILL.md").read_text())

    def test_backup_parent_retarget_during_staging_prevents_replacement(self):
        other = self.base / "other-backups"
        other.mkdir()
        def redirect():
            (self.root.parent / "backups").symlink_to(other, target_is_directory=True)
        with self.stage_hook(redirect):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assertEqual([], list(other.iterdir()))
        self.assert_unchanged()

    def test_physical_root_replacement_preserves_foreign_tree_during_rollback(self):
        moved = self.root.with_name("moved-original")
        real = installer.replace_directory
        def replace_root(source, target, backup, **kwargs):
            if target.name == self.names[1]:
                self.root.rename(moved)
                # Even byte-identical foreign content must not be rolled back.
                shutil.copytree(moved, self.root)
                (self.root / "foreign-owner.txt").write_text("external root")
                raise OSError("external root replacement")
            return real(source, target, backup, **kwargs)
        with mock.patch.object(installer, "replace_directory", side_effect=replace_root):
            with self.assertRaises(installer.InstallError) as raised:
                self.run_pack()
        self.assertIn(str(self.prior), raised.exception.partial_install["rollback_conflicts"])
        self.assertEqual("external root", (self.root / "foreign-owner.txt").read_text())
        self.assertEqual(installer.manifest(self.repo / "skills" / self.names[0]), installer.manifest(self.prior))
        self.assertEqual(installer.manifest(self.prior), installer.manifest(moved / self.names[0]))
        self.assertTrue(list((self.root.parent / "backups").rglob("business-work/SKILL.md")))

    def test_source_root_replaced_by_symlink_after_lock_is_rejected(self):
        source = self.repo / "skills" / self.names[1]
        moved = source.with_name("source-original")
        real = installer.skills_install_lock
        @contextlib.contextmanager
        def lock(parent):
            with real(parent):
                source.rename(moved)
                source.symlink_to(moved, target_is_directory=True)
                yield
        with mock.patch.object(installer, "skills_install_lock", side_effect=lock):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assert_unchanged()

    def test_individual_source_and_target_symlinks_are_rejected(self):
        source = self.repo / "skills" / self.names[1]
        parked = source.with_name("parked")
        source.rename(parked)
        source.symlink_to(parked, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            self.run_pack()
        source.unlink()
        parked.rename(source)
        target = self.root / self.names[1]
        target.symlink_to(source, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            self.run_pack()
        self.assertTrue(target.is_symlink())
        self.assertEqual(self.original, installer.manifest(self.prior))

    def test_member_file_symlinks_rejected(self):
        source = self.repo / "skills" / self.names[1]
        (source / "alias.md").symlink_to(source / "SKILL.md")
        with self.assertRaises(installer.InstallError):
            self.run_pack()
        self.assert_unchanged()

    def test_backup_is_outside_discovery_roots_and_same_filesystem(self):
        result = self.run_pack()
        backup = Path(result["backup"])
        self.assertEqual(self.root.stat().st_dev, backup.stat().st_dev)
        roots = business.resolve(self.homes, None, installer)["identities"]
        self.assertTrue(all(not backup.is_relative_to(identity[0]) for identity in roots.values()))
        self.assertEqual("local old skill", (backup / "business-work/SKILL.md").read_text())

    def test_symlinked_backup_parent_rejected(self):
        external = self.base / "external-backups"
        external.mkdir()
        (self.root.parent / "backups").symlink_to(external, target_is_directory=True)
        with self.assertRaises(installer.InstallError):
            self.run_pack()
        self.assertEqual([], list(external.iterdir()))
        self.assert_unchanged()

    def test_pack_metadata_version_members_pins_and_owner_must_agree(self):
        original = json.loads(self.metadata.read_text())
        for field, value in (("package_version", "2.0.0"), ("skills", self.names[:1]),
                             ("pins", {"example": {"repo": "example/source", "commit": "b" * 40}}),
                             ("update_owner", "upstream-direct")):
            with self.subTest(field=field):
                self.metadata.write_text(json.dumps({**original, field: value}))
                with mock.patch.object(installer, "skills_install_lock") as locks:
                    with self.assertRaises(ValueError):
                        self.run_pack()
                locks.assert_not_called()
        self.metadata.write_text(json.dumps(original))
        self.assert_unchanged()

    def test_cli_flags_and_failure_exit_status(self):
        args = ["--skills-only", "--pack", business.PACK_ID, "--all", "--wsl-home", str(self.wsl),
                "--desktop-home", str(self.desktop)]
        # CLI lazily loads its implementation from the candidate scripts.
        (self.repo / "scripts").mkdir()
        shutil.copyfile(REPO / "scripts/business_pack.py", self.repo / "scripts/business_pack.py")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(2, installer.main(["verify", *args]))
        self.assertEqual("failed", json.loads(output.getvalue())["status"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, installer.main(["install", *args]))
            self.assertEqual(0, installer.main(["verify", *args]))
            self.assertEqual(2, installer.main(["plan", "--pack", business.PACK_ID]))
            self.assertEqual(2, installer.main(["plan", "--skills-only", "--business-root", str(self.root)]))

    def test_actual_repository_manifest_is_valid_and_legacy_scope_is_unchanged(self):
        pack = business.load_pack(REPO)
        self.assertEqual(12, len(pack["managed_skills"]))
        self.assertFalse(set(pack["managed_skills"]) & set(installer.SKILLS))
        self.assertTrue(set(pack["reused_capabilities"]["skills"]).issubset(installer.SKILLS))
        with mock.patch.object(installer, "SKILLS_ROOT", REPO / "skills"):
            items = installer.skills_preflight(self.wsl)
        self.assertEqual({*installer.SKILLS, installer.GRAPH_RUNTIME_TARGET}, {item["name"] for item in items})
        self.assertEqual({"skills", installer.GRAPH_RUNTIME_TARGET}, {item["relative"].parts[0] for item in items})


if __name__ == "__main__":
    unittest.main()
