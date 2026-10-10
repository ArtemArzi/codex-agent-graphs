import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


HELPER = Path(__file__).resolve().parents[1] / "skills/software-factory/scripts/factory.py"


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="factory-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.workspace = self.root / "workspace"
        self.git(self.repo, "init", "-b", "main")
        self.git(self.repo, "config", "user.name", "Pilot Test")
        self.git(self.repo, "config", "user.email", "pilot-test@localhost")
        for name, text in {"a.txt": "40\n", "b.txt": "100\n", ".gitignore": "__pycache__/\n"}.items():
            (self.repo / name).write_text(text)
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "Baseline")
        self.base = self.git(self.repo, "rev-parse", "HEAD")

    def git(self, cwd, *args):
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result.stdout.strip()

    def cli(self, *args, expected=0, helper=HELPER):
        result = subprocess.run([sys.executable, str(helper), *map(str, args)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def prepare(self, job="alpha", owns="a.txt", expected=0):
        return self.cli("prepare", "--repo", self.repo, "--workspace", self.workspace,
                        "--job", job, "--owns", owns, "--objective", "Test", expected=expected)

    def commit(self, job, files):
        path = Path(job["path"])
        for name, value in files.items():
            (path / name).write_text(value)
        self.git(path, "add", ".")
        self.git(path, "commit", "-m", "Implement test candidate")

    def verify(self, code="assert True", expected=0):
        return self.cli("verify", "--workspace", self.workspace, "--", sys.executable,
                        "-c", code, expected=expected)

    def status(self):
        return self.cli("status", "--workspace", self.workspace)

    def test_two_jobs_merge_without_changing_main(self):
        a = self.prepare()
        b = self.prepare("beta", "b.txt")
        self.commit(a, {"a.txt": "41\n"})
        self.commit(b, {"b.txt": "101\n"})
        result = self.verify("from pathlib import Path; assert Path('a.txt').read_text() == '41\\n'; assert Path('b.txt').read_text() == '101\\n'")
        self.assertEqual(result["check"], "pass")
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertEqual((self.repo / "a.txt").read_text(), "40\n")
        self.assertTrue(self.status()["verification"]["fresh"])

    def test_copied_skill_folder_runs_full_cycle_without_bundle_root(self):
        source = HELPER.parents[1]
        copied = self.root / "copied-skill"
        shutil.copytree(source, copied)
        helper = copied / "scripts/factory.py"
        context = self.root / "packet.md"
        context.write_text("# Shared contract\nOnly the assigned file may change.\n")
        jobs = []
        for name, owned in (("alpha", "a.txt"), ("beta", "b.txt")):
            job = self.cli("prepare", "--repo", self.repo, "--workspace", self.workspace,
                           "--job", name, "--owns", owned, "--objective", "Portable cycle",
                           "--context", context, helper=helper)
            jobs.append(job)
            brief = (self.workspace / "briefs" / (name + ".md")).read_text()
            self.assertIn(context.read_text(), brief)
            self.commit(job, {owned: "portable\n"})
        result = self.cli("verify", "--workspace", self.workspace, "--", sys.executable,
                          "-c", "from pathlib import Path; assert all(Path(p).read_text() == 'portable\\n' for p in ('a.txt', 'b.txt'))",
                          helper=helper)
        self.assertEqual(result["check"], "pass")
        self.assertTrue(self.cli("status", "--workspace", self.workspace,
                                 helper=helper)["verification"]["fresh"])
        self.assertEqual(self.git(self.repo, "rev-parse", "main"), self.base)
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertFalse((copied.parent / "factory.py").exists())

    def test_duplicate_overlap_escape_and_runtime_paths_rejected(self):
        self.prepare()
        self.assertIn("already exists", self.prepare(expected=2))
        self.assertIn("overlapping", self.prepare("beta", expected=2))
        for path in ("../escape", "/tmp/escape", ".git/config", ".codex/state.json", ".project-start/state.json"):
            self.assertIn("exact repository file", self.prepare("beta", path, expected=2))

    def test_lock_contention(self):
        self.workspace.mkdir()
        (self.workspace / ".lock").mkdir()
        self.assertIn("locked", self.prepare(expected=2))
        self.assertTrue((self.workspace / ".lock").exists())

    def test_dirty_job_and_missing_candidate_rejected(self):
        a = self.prepare()
        self.assertIn("committed candidate", self.verify(expected=2))
        (Path(a["path"]) / "a.txt").write_text("42\n")
        self.assertIn("dirty", self.verify(expected=2))

    def test_unowned_change_rejected(self):
        a = self.prepare()
        self.commit(a, {"b.txt": "outside scope\n"})
        self.assertIn("ownership", self.verify(expected=2))

    def test_rename_checks_both_sides(self):
        a = self.prepare("alpha", "new.txt")
        self.git(a["path"], "mv", "a.txt", "new.txt")
        self.git(a["path"], "commit", "-m", "Rename unowned source")
        self.assertIn("ownership", self.verify(expected=2))

    def test_dirty_source_rejected_at_prepare_and_verify(self):
        (self.repo / "untracked.txt").write_text("unexpected")
        self.assertIn("clean", self.prepare(expected=2))
        (self.repo / "untracked.txt").unlink()
        a = self.prepare()
        self.commit(a, {"a.txt": "41\n"})
        (self.repo / "untracked.txt").write_text("unexpected")
        self.assertIn("dirty", self.verify(expected=2))

    def test_target_movement_invalidates_verification(self):
        a = self.prepare()
        self.commit(a, {"a.txt": "41\n"})
        self.verify()
        (self.repo / "b.txt").write_text("102\n")
        self.git(self.repo, "add", "b.txt")
        self.git(self.repo, "commit", "-m", "Move target")
        self.assertFalse(self.status()["verification"]["fresh"])
        self.assertIn("Source/job changed", self.verify(expected=2))
        self.assertIn("different repository/base", self.prepare("beta", "b.txt", expected=2))

    def test_job_movement_and_dirty_candidate_invalidate_verification(self):
        a = self.prepare()
        self.commit(a, {"a.txt": "41\n"})
        result = self.verify()
        candidate = Path(result["candidate_path"])
        (candidate / "untracked.txt").write_text("unexpected")
        self.assertFalse(self.status()["verification"]["fresh"])
        (candidate / "untracked.txt").unlink()
        self.assertTrue(self.status()["verification"]["fresh"])
        self.commit(a, {"a.txt": "42\n"})
        self.assertFalse(self.status()["verification"]["fresh"])

    def test_combined_behavior_fails_although_each_job_passes(self):
        a = self.prepare()
        b = self.prepare("beta", "b.txt")
        self.commit(a, {"a.txt": "48\n"})
        self.commit(b, {"b.txt": "90\n"})
        check = "from pathlib import Path; assert 2*int(Path('a.txt').read_text()) <= int(Path('b.txt').read_text())"
        for job in (a, b):
            result = subprocess.run([sys.executable, "-c", check], cwd=job["path"])
            self.assertEqual(result.returncode, 0)
        result = self.verify(check, expected=1)
        self.assertEqual(result["check"], "fail")
        self.assertEqual(result["returncode"], 1)
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertTrue(Path(result["candidate_path"]).exists())

    def test_file_directory_ownership_overlap_rejected_before_worktree(self):
        for index, (first, second) in enumerate((("new", "new/file.txt"),
                                                ("new/file.txt", "new"))):
            with self.subTest(first=first):
                self.workspace = self.root / f"geometry-{index}"
                self.prepare("alpha", first)
                self.assertIn("overlapping", self.prepare("beta", second, expected=2))
                self.assertFalse((self.workspace / "jobs" / "beta").exists())

    def test_shared_directory_with_distinct_files_is_allowed(self):
        self.prepare("alpha", "new/a.txt")
        self.prepare("beta", "new/b.txt")
        self.assertEqual(len(self.status()["jobs"]), 2)

    def test_single_job_file_directory_overlap_rejected(self):
        result = self.cli("prepare", "--repo", self.repo, "--workspace", self.workspace,
                          "--job", "alpha", "--owns", "new", "--owns", "new/file.txt",
                          "--objective", "Test", expected=2)
        self.assertIn("overlapping", result)
        self.assertFalse((self.workspace / "jobs" / "alpha").exists())

    def test_context_snapshot_is_per_job_and_survives_source_edits(self):
        original = "# Цель\nОбщий контракт: v1. Проверка: без сети.\n"
        context = self.root / "context.md"
        context.write_bytes(original.encode("utf-8"))
        job = self.cli("prepare", "--repo", self.repo, "--workspace", self.workspace,
                       "--job", "alpha", "--owns", "a.txt", "--objective", "Test",
                       "--context", context)
        digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
        manifest = json.loads((self.workspace / "workspace.json").read_text())
        self.assertEqual(manifest["jobs"]["alpha"]["context_sha256"], digest)
        brief = Path(job["brief"]).read_text()
        self.assertIn(original, brief)
        self.assertIn(digest, brief)
        context.write_text("CHANGED SOURCE")
        self.assertEqual(Path(job["brief"]).read_text(), brief)
        other = self.prepare("beta", "b.txt")
        self.assertNotIn(original, Path(other["brief"]).read_text())
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD"), self.base)

    def test_invalid_context_creates_no_job(self):
        context = self.root / "context.md"
        for content in (b"", b"   \n", b"\xff\xfe"):
            with self.subTest(content=content):
                context.write_bytes(content)
                error = self.cli("prepare", "--repo", self.repo, "--workspace", self.workspace,
                                 "--job", "alpha", "--owns", "a.txt", "--objective", "Test",
                                 "--context", context, expected=2)
                self.assertIn("Context must be", error)
                self.assertFalse((self.workspace / "jobs" / "alpha").exists())
        context.unlink()
        error = self.cli("prepare", "--repo", self.repo, "--workspace", self.workspace,
                         "--job", "alpha", "--owns", "a.txt", "--objective", "Test",
                         "--context", context, expected=2)
        self.assertIn("Context must be", error)
        self.assertFalse((self.workspace / "jobs" / "alpha").exists())

    def test_interrupted_or_invalid_check_never_passes(self):
        a = self.prepare()
        self.commit(a, {"a.txt": "41\n"})
        result = self.cli("verify", "--workspace", self.workspace, "--timeout", "1", "--",
                          sys.executable, "-c", "import time; time.sleep(3)", expected=1)
        self.assertEqual(result["check"], "error")
        self.assertNotEqual(self.status()["verification"]["check"], "pass")

    def test_wrong_source_branch_rejected(self):
        self.git(self.repo, "switch", "-c", "other")
        self.assertIn("selected base", self.prepare(expected=2))

    def test_check_moving_candidate_branch_is_stale(self):
        a = self.prepare()
        self.commit(a, {"a.txt": "41\n"})
        result = self.verify("import subprocess; subprocess.run(['git', 'switch', '-c', 'unexpected'], check=True)", expected=1)
        self.assertEqual(result["check"], "stale")

    def test_max_two_jobs_and_nested_workspace_rejected(self):
        self.prepare()
        self.prepare("beta", "b.txt")
        self.assertIn("at most two", self.prepare("gamma", "third.txt", expected=2))
        result = self.cli("prepare", "--repo", self.repo, "--workspace", self.repo / "nested",
                          "--job", "gamma", "--owns", "a.txt", "--objective", "Test", expected=2)
        self.assertIn("non-nested", result)

    def test_real_filenames_are_not_git_display_escapes(self):
        for index, name in enumerate(("отчёт.txt", "line\nbreak.txt", "cr\rname.txt", " leading space.txt")):
            with self.subTest(name=name):
                self.workspace = self.root / f"filenames-{index}"
                job = self.prepare(owns=name)
                self.commit(job, {name: "owned\n"})
                row = self.status()["jobs"]["alpha"]
                self.assertEqual(row["changed"], [name])
                self.assertEqual(row["outside_scope"], [])
                self.assertEqual(self.verify()["check"], "pass")


if __name__ == "__main__":
    unittest.main()
