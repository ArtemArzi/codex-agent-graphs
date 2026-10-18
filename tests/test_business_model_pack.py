"""Business Model source and installation contracts on disposable homes."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load_module("model_test_installer", "scripts/install.py")
packs = load_module("model_test_packs", "scripts/business_pack.py")


class BusinessModelSourceTests(unittest.TestCase):
    def test_members_are_shared_original_sources_and_companions_are_optional(self):
        pack = packs.load_pack(ROOT, "business-model")
        self.assertEqual(pack["entrypoint"], "business-work")
        self.assertEqual(len(pack["managed_skills"]), 4)
        self.assertFalse(set(pack["managed_skills"]) & set(pack["reused_capabilities"]["skills"]))
        self.assertIs(pack["reused_capabilities"]["required"], False)
        self.assertEqual(pack["runtime_dependencies"], [])
        self.assertFalse(list((ROOT / "products/business-model").rglob("SKILL.md")))
        self.assertEqual(pack["default_market"], "RU")
        for name in pack["managed_skills"]:
            source = ROOT / "skills" / name
            self.assertEqual(packs.declared_name(source / "SKILL.md", installer), name)
            metadata = (source / "agents/openai.yaml").read_text()
            values = {}
            for line in metadata.splitlines():
                match = re.fullmatch(r'  (display_name|short_description|default_prompt): (".*")', line)
                if match:
                    values[match[1]] = json.loads(match[2])
            self.assertEqual(set(values), {"display_name", "short_description", "default_prompt"})
            self.assertTrue(25 <= len(values["short_description"]) <= 64)
            self.assertIn("$" + name, values["default_prompt"])

    def test_authored_links_are_portable_and_resolve(self):
        docs = list((ROOT / "products/business-model").rglob("*.md"))
        for name in packs.load_pack(ROOT, "business-model")["managed_skills"]:
            docs.extend((ROOT / "skills" / name).rglob("*.md"))
        for doc in docs:
            for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                self.assertFalse(Path(relative).is_absolute(), (doc, target))
                self.assertTrue((doc.parent / relative).is_file(), (doc, target))


class BusinessModelInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.model = packs.load_pack(ROOT, "business-model")
        self.automation = packs.load_pack(ROOT)
        for pack in (self.model, self.automation):
            product = self.repo / "products" / pack["id"]
            product.mkdir(parents=True)
            (product / "pack.json").write_text(json.dumps(pack))
        names = set(self.model["managed_skills"] + self.automation["managed_skills"])
        for name in names:
            shutil.copytree(ROOT / "skills" / name, self.repo / "skills" / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        self.wsl = self.base / "wsl/.codex"
        self.desktop = self.base / "desktop/.codex"
        self.homes = [("wsl", self.wsl), ("desktop", self.desktop)]
        self.skill_root = self.base / "shared/skills"
        self.skill_root.mkdir(parents=True)
        self.protected = {}
        for _, home in self.homes:
            home.mkdir(parents=True)
            for name, value in (("config.toml", "model='preserve'\n"),
                                ("AGENTS.md", "local policy"),
                                ("auth.json", '{"synthetic":true}')):
                target = home / name
                target.write_text(value)
                self.protected[target] = target.read_bytes()
        unrelated = self.skill_root / "unrelated/SKILL.md"
        unrelated.parent.mkdir()
        unrelated.write_text("---\nname: unrelated\ndescription: local\n---\n")
        self.protected[unrelated] = unrelated.read_bytes()
        for attribute, value in (("REPO_ROOT", self.repo), ("SKILLS_ROOT", self.repo / "skills")):
            patch = mock.patch.object(installer, attribute, value)
            patch.start()
            self.addCleanup(patch.stop)

    def run_pack(self, action="install", pack_id="business-model"):
        return packs.run(action, self.homes, self.skill_root, api=installer, pack_id=pack_id)

    def assert_protected(self):
        self.assertEqual(self.protected, {path: path.read_bytes() for path in self.protected})

    def test_clean_install_contains_only_four_members_and_is_idempotent(self):
        plan = self.run_pack("plan")
        self.assertEqual({item["status"] for item in plan["items"]}, {"missing"})
        result = self.run_pack()
        self.assertEqual(len(result["changes"]), 4)
        self.assertEqual({path.name for path in self.skill_root.iterdir()},
                         set(self.model["managed_skills"]) | {"unrelated"})
        before = {path: path.stat().st_mtime_ns for path in self.skill_root.rglob("*")}
        second = self.run_pack()
        self.assertIsNone(second["backup"])
        self.assertTrue(all(item["status"] == "in-sync" for item in second["changes"]))
        self.assertEqual(before, {path: path.stat().st_mtime_ns for path in before})
        self.assertEqual(self.run_pack("verify")["status"], "ok")
        self.assert_protected()

    def test_both_pack_orders_share_one_source_at_the_same_revision(self):
        for first, second in (("business-model", "business-automation"),
                              ("business-automation", "business-model")):
            with self.subTest(first=first):
                self.skill_root = self.base / first / "skills"
                self.skill_root.mkdir(parents=True)
                self.run_pack(pack_id=first)
                shared = self.skill_root / "business-work"
                before = installer.manifest(shared)
                modified = (shared / "SKILL.md").stat().st_mtime_ns
                self.run_pack(pack_id=second)
                self.assertEqual(before, installer.manifest(shared))
                self.assertEqual(modified, (shared / "SKILL.md").stat().st_mtime_ns)
                for pack_id in (first, second):
                    self.assertEqual(self.run_pack("verify", pack_id)["status"], "ok")
                    self.assertIsNone(self.run_pack(pack_id=pack_id)["backup"])
        self.assert_protected()

    def test_local_drift_rejects_before_any_install_write(self):
        self.run_pack()
        target = self.skill_root / "business-work/SKILL.md"
        target.write_text(target.read_text() + "\nlocal owner edit\n")
        before = installer.directory_preimage(self.skill_root)
        with mock.patch.object(installer, "replace_directory") as writes:
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        writes.assert_not_called()
        self.assertEqual(before, installer.directory_preimage(self.skill_root))
        self.assert_protected()

    def test_duplicate_name_in_legacy_root_rejects_without_writes(self):
        duplicate = self.wsl / "skills/renamed/SKILL.md"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text("---\nname: business-economics\ndescription: local\n---\n")
        with mock.patch.object(installer, "replace_directory") as writes:
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        writes.assert_not_called()
        self.assertFalse((self.skill_root / "business-economics").exists())
        self.assert_protected()

    def test_pack_owner_members_and_runtime_contract_are_validated(self):
        path = self.repo / "products/business-model/pack.json"
        for field, value in (("update_owner", "other"), ("runtime_dependencies", ["server"]),
                             ("managed_skills", ["business-work"]),
                             ("reused_capabilities", {"required": True, "skills": []})):
            with self.subTest(field=field):
                path.write_text(json.dumps({**self.model, field: value}))
                with self.assertRaises(ValueError):
                    packs.load_pack(self.repo, "business-model")
        path.write_text(json.dumps(self.model))
        self.assert_protected()

    def test_source_edit_during_staging_is_rejected_and_targets_preserved(self):
        original = installer.shutil.copytree
        source = self.repo / "skills/business-economics/SKILL.md"
        changed = False

        def stage_and_change(*args, **kwargs):
            nonlocal changed
            staged = original(*args, **kwargs)
            if not changed:
                changed = True
                source.write_text(source.read_text() + "\nconcurrent source edit\n")
            return staged

        before = installer.directory_preimage(self.skill_root)
        with mock.patch.object(installer.shutil, "copytree", side_effect=stage_and_change):
            with self.assertRaises(installer.InstallError):
                self.run_pack()
        self.assertEqual(before, installer.directory_preimage(self.skill_root))
        self.assert_protected()

    def test_public_cli_selects_new_pack_and_keeps_scope_boundary(self):
        args = ["--skills-only", "--pack", "business-model", "--all",
                "--wsl-home", str(self.wsl), "--desktop-home", str(self.desktop),
                "--skill-root", str(self.skill_root)]
        scripts = self.repo / "scripts"
        scripts.mkdir()
        shutil.copyfile(ROOT / "scripts/business_pack.py", scripts / "business_pack.py")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(["plan", *args]), 0)
            self.assertEqual(installer.main(["install", *args]), 0)
            self.assertEqual(installer.main(["verify", *args]), 0)
            self.assertEqual(installer.main(["plan", "--pack", "business-model"]), 2)
        self.assert_protected()


if __name__ == "__main__":
    unittest.main()
