"""Positive and violating implementations exercise the same public oracle."""

from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


FIXTURE = Path(__file__).parent / "fixtures" / "architecture-contract"
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "architecture_update", ROOT / "docs/tasks/TD-ARCHITECTURE-CONTRACT/install_update.py"
)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class ArchitectureOracleTests(unittest.TestCase):
    def run_candidate(self, source: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            shutil.copytree(FIXTURE, root)
            (root / "notifications.py").write_text(source, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "check.py"], cwd=root, text=True,
                capture_output=True, check=False,
            )

    def test_public_contract_passes(self) -> None:
        result = self.run_candidate(
            "from payments.public import payment_label\n"
            "def render_payment(payment_id):\n"
            "    return 'Payment: ' + payment_label(payment_id)\n"
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_same_behavior_through_private_storage_is_rejected(self) -> None:
        for statement in (
            "from payments._store import LABELS",
            "from payments import _store",
            "import payments._store",
        ):
            with self.subTest(statement=statement):
                result = self.run_candidate(
                    statement + "\ndef render_payment(payment_id):\n"
                    "    return 'Payment: ' + ('paid' if payment_id == 1 else 'unknown')\n"
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn("E1: notifications must use payments.public", result.stderr)

    def test_boundary_compliance_does_not_hide_wrong_behavior(self) -> None:
        result = self.run_candidate(
            "from payments.public import payment_label\n"
            "def render_payment(payment_id):\n"
            "    return 'Payment: paid'\n"
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("AssertionError", result.stderr)


class ScopedInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary.name) / "codex"
        update.install.install_environment(self.home)
        # Preserve a user setting which the general installer would normalize.
        self.config = self.home / "config.toml"
        self.config.write_text(self.config.read_text() + "\n# user-owned marker\n")
        old = self.home / "skills/task-delivery/SKILL.md"
        old.write_text(old.read_text() + "\nPrior installed revision.\n")
        self.receipt = Path(self.temporary.name) / "prepared.json"

    def tearDown(self):
        self.temporary.cleanup()

    def invoke(self, action):
        with mock.patch.object(sys, "argv", ["install_update.py", action, "--home", str(self.home), "--receipt", str(self.receipt)]):
            update.main()

    def test_scoped_install_preserves_configuration_and_verifies(self):
        before_config = self.config.read_bytes()
        self.invoke("prepare")
        self.invoke("apply")
        self.invoke("verify")
        self.assertEqual(before_config, self.config.read_bytes())

    def test_intervening_installed_drift_is_not_overwritten(self):
        self.invoke("prepare")
        path = self.home / "skills/task-delivery/SKILL.md"
        path.write_text(path.read_text() + "Concurrent user edit.\n")
        with self.assertRaisesRegex(ValueError, "Installed targets changed"):
            self.invoke("apply")
        self.assertTrue(path.read_text().endswith("Concurrent user edit.\n"))

    def test_symlinked_parent_is_rejected_before_prepare(self):
        external = Path(self.temporary.name) / "external-agents"
        (self.home / "agents").rename(external)
        (self.home / "agents").symlink_to(external, target_is_directory=True)
        with self.assertRaises(update.install.InstallError):
            self.invoke("prepare")
        self.assertFalse(self.receipt.exists())

    def test_failure_restores_exact_prepared_targets(self):
        self.invoke("prepare")
        before = update.snapshot(self.home)
        config = self.config.read_bytes()
        with mock.patch.object(update.install, "replace_generated", side_effect=RuntimeError("injected failure")):
            with self.assertRaisesRegex(RuntimeError, "injected failure"):
                self.invoke("apply")
        self.assertEqual(before, update.snapshot(self.home))
        self.assertEqual(config, self.config.read_bytes())


class BundledArchitecturePlaybookTests(unittest.TestCase):
    def test_playbook_is_portable_linked_and_installed(self) -> None:
        relative = Path("skills/project-start/references/architecture-playbook.md")
        bundled = ROOT / relative
        self.assertTrue(bundled.is_file())

        content = bundled.read_text(encoding="utf-8")
        self.assertNotIn("/home/artem/projects", content)
        self.assertIn("## Иерархия оснований", content)
        self.assertIn("## Формат архитектурного предложения", content)

        skill = (ROOT / "skills/project-start/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/architecture-playbook.md", skill)
        self.assertLess(
            skill.index("пользовательский архитектурный справочник"),
            skill.index("references/architecture-playbook.md"),
        )

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex"
            update.install.install_environment(home)
            installed = home / relative
            self.assertEqual(bundled.read_bytes(), installed.read_bytes())


if __name__ == "__main__":
    unittest.main()
