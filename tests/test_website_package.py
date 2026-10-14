"""Installability and reference closure of the site package, without live access."""

from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("website_installer", ROOT / "scripts/install.py")
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
SITE_SKILLS = ("website-standards", "web-measurement", "reliable-leads", "seo")


class WebsitePackageTests(unittest.TestCase):
    def test_package_installs_in_relocated_home_with_complete_reference_closure(self):
        self.assertTrue(set(SITE_SKILLS).issubset(installer.SKILLS))
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex"
            home.mkdir()
            protected = home / "config.toml"
            protected.write_text('model = "fixture-user-choice"\n')
            unrelated = home / "skills/unrelated/SKILL.md"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("User-owned unrelated skill\n")
            installer.install_skills_batch([("fixture", home)])
            self.assertEqual(protected.read_text(), 'model = "fixture-user-choice"\n')
            self.assertEqual(unrelated.read_text(), "User-owned unrelated skill\n")
            for name in SITE_SKILLS:
                source = ROOT / "skills" / name
                target = home / "skills" / name
                self.assertEqual(installer.manifest(source), installer.manifest(target))
                for document in target.rglob("*.md"):
                    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text()):
                        if link.startswith(("https://", "http://", "#")):
                            continue
                        path = link.split("#", 1)[0]
                        self.assertFalse(Path(path).is_absolute(), (document, link))
                        resolved = (document.parent / path).resolve()
                        self.assertTrue(resolved.is_relative_to(home / "skills"), (document, link))
                        self.assertTrue(resolved.is_file(), (document, link))
            again = installer.install_skills_batch([("fixture", home)])
            self.assertTrue(all(item["status"] == "in-sync" for item in again[0]["changes"]))
            self.assertIsNone(again[0]["backup"])

    def test_each_entrypoint_has_discoverable_consistent_native_metadata(self):
        for name in SITE_SKILLS:
            folder = ROOT / "skills" / name
            self.assertTrue((folder / "SKILL.md").is_file(), f"Missing skill {name}")
            body = (folder / "SKILL.md").read_text()
            self.assertTrue(body.startswith(f"---\nname: {name}\n"))
            metadata = (folder / "agents/openai.yaml").read_text()
            short = re.search(r'  short_description: "([^"\n]+)"', metadata)
            self.assertIsNotNone(short, name)
            self.assertTrue(25 <= len(short.group(1)) <= 64, name)
            self.assertIn(f"${name}", metadata)
            self.assertNotIn("allow_implicit_invocation: false", metadata)
            self.assertFalse((folder / "graph.json").exists())


if __name__ == "__main__":
    unittest.main()
