from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import portable_bundle as bundles
import portable_install as installer


class PortableInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='portable-install-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / 'home'
        self.count = 0

    def bundle(self, skills=('alpha',), version='one'):
        self.count += 1
        root = self.root / f'bundle-{self.count}'
        payload = root / 'payload'
        payload.mkdir(parents=True)
        for name in ('skills', 'agents', 'agent-graph-runtime', 'knowledge'):
            (payload / name).mkdir()
        for name in skills:
            directory = payload / 'skills' / name
            directory.mkdir()
            (directory / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: fixture\n---\n{version}\n')
        (payload / 'agents' / 'worker.toml').write_text('name="fixture"\n')
        (payload / 'agent-graph-runtime' / 'run.py').write_text('print("fixture")\n')
        (payload / 'knowledge' / 'selected.txt').write_text('Selected knowledge\n')
        (payload / 'AGENTS.md').write_text('Fixture policy\n')
        (payload / 'config.toml').write_text('model="fixture"\n')
        for name in bundles.BOOTSTRAP:
            shutil.copyfile(REPO / 'scripts' / name, root / name)
        lock = {'schema_version': 1, 'files': bundles.manifest_files(payload),
                'bootstrap': {name: bundles.manifest_files(root)[name] for name in bundles.BOOTSTRAP},
                'skills': [{'name': name} for name in skills], 'diagnostics': {'fixture': version}}
        lock['id'] = bundles.bundle_id(lock)
        (root / 'manifest.json').write_text(json.dumps(lock))
        self.assertEqual(bundles.verify_bundle(root), lock)
        return root, lock

    def install(self, skills=('alpha',), version='one'):
        root, lock = self.bundle(skills, version)
        installer.install(root, self.target)
        return root, lock

    def release(self, lock):
        return self.target / '.portable-kit' / 'releases' / lock['id']

    def three(self):
        releases = []
        for names, version in ((('alpha', 'shared'), 'a'), (('beta', 'shared'), 'b'), (('gamma', 'shared'), 'c')):
            releases.append(self.install(names, version)[1])
        return releases

    def test_plan_absent_and_empty_is_nonmutating(self):
        root, lock = self.bundle()
        self.assertEqual(installer.plan(root, self.target)['action'], 'install')
        self.assertFalse(self.target.exists())
        self.target.mkdir()
        self.assertEqual(installer.plan(root, self.target)['release_id'], lock['id'])
        self.assertEqual(list(self.target.iterdir()), [])

    def test_install_noop_describe_and_relocate_bundle(self):
        root, lock = self.bundle()
        moved = self.root / 'relocated-bundle'
        root.rename(moved)
        first = installer.install(moved, self.target)
        self.assertEqual(first['status'], 'installed')
        self.assertEqual(first['release_id'], lock['id'])
        self.assertFalse((self.target / 'skills').is_symlink())
        link = self.target / 'skills' / 'alpha'
        self.assertEqual(os.readlink(link), '../.portable-kit/current/skills/alpha')
        inode = link.lstat().st_ino
        self.assertEqual(installer.install(moved, self.target)['status'], 'unchanged')
        self.assertEqual(link.lstat().st_ino, inode)
        self.assertEqual(installer.plan(moved, self.target)['action'], 'unchanged')
        self.assertEqual(installer.describe(self.target)['manifest'], lock)
        self.assertEqual(installer.verify(self.target)['releases'], [lock['id']])

    def test_update_rollback_and_native_mutable_preservation(self):
        _, first = self.install(('alpha', 'removed'), 'a')
        protected = {}
        for relative in ('skills/.system/native/SKILL.md', 'skills/foreign/SKILL.md', 'auth.json', 'sessions/entry.json', 'logs/local.txt'):
            path = self.target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Owner data ' + relative)
            protected[path] = (path.read_bytes(), path.stat().st_ino)
        _, second = self.install(('alpha', 'added'), 'b')
        self.assertEqual((self.target / 'skills' / 'alpha' / 'SKILL.md').read_text().splitlines()[-1], 'b')
        self.assertTrue((self.target / 'skills' / 'removed').is_symlink())
        self.assertFalse((self.target / 'skills' / 'removed' / 'SKILL.md').exists())
        self.assertTrue((self.target / 'skills' / 'added' / 'SKILL.md').exists())
        self.assertEqual(installer.rollback(self.target)['release_id'], first['id'])
        self.assertFalse((self.target / 'skills' / 'added' / 'SKILL.md').exists())
        self.assertEqual(installer.rollback(self.target, second['id'])['release_id'], second['id'])
        for path, expected in protected.items():
            self.assertEqual((path.read_bytes(), path.stat().st_ino), expected)
        installer.verify(self.target)

    def test_foreign_skill_collision_even_matching_symlink(self):
        self.install()
        second, lock = self.bundle(('alpha', 'foreign'), 'b')
        entry = self.target / 'skills' / 'foreign'
        entry.symlink_to('../.portable-kit/current/skills/foreign')
        for operation in (installer.plan, installer.install):
            with self.assertRaisesRegex(bundles.KitError, 'Foreign skill name collision'):
                operation(second, self.target)
        self.assertTrue(entry.is_symlink())
        self.assertFalse(self.release(lock).exists())

    def test_foreign_skill_directory_collision_preserved(self):
        self.install()
        entry = self.target / 'skills' / 'foreign'
        entry.mkdir()
        (entry / 'SKILL.md').write_text('Foreign owner')
        second, _ = self.bundle(('foreign',), 'b')
        with self.assertRaisesRegex(bundles.KitError, 'collision'):
            installer.install(second, self.target)
        self.assertEqual((entry / 'SKILL.md').read_text(), 'Foreign owner')

    def test_refuses_unowned_nonempty_home_and_symlink_target(self):
        root, _ = self.bundle()
        self.target.mkdir()
        (self.target / 'auth.json').write_text('Owner data')
        with self.assertRaisesRegex(bundles.KitError, 'unowned'):
            installer.install(root, self.target)
        self.assertEqual((self.target / 'auth.json').read_text(), 'Owner data')
        alias = self.root / 'alias'
        alias.symlink_to(self.target, target_is_directory=True)
        with self.assertRaises(bundles.KitError):
            installer.install(root, alias)

    def test_refuses_active_and_default_global_homes(self):
        root, _ = self.bundle()
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(self.target)}):
            for operation in (installer.plan, installer.install):
                with self.assertRaisesRegex(bundles.KitError, 'global CODEX_HOME'):
                    operation(root, self.target)
        with mock.patch.object(Path, 'home', return_value=self.root):
            with self.assertRaisesRegex(bundles.KitError, 'global CODEX_HOME'):
                installer.install(root, self.root / '.codex')
        self.assertFalse(self.target.exists())

    def test_bundle_corruption_symlink_and_hardlink_rejected(self):
        for corruption in ('content', 'symlink', 'hardlink'):
            with self.subTest(corruption=corruption):
                root, _ = self.bundle(version=corruption)
                file = root / 'payload' / 'skills' / 'alpha' / 'SKILL.md'
                if corruption == 'content':
                    file.write_text('Changed')
                else:
                    file.unlink()
                    external = self.root / ('external-' + corruption)
                    external.write_text('Foreign file')
                    if corruption == 'symlink':
                        file.symlink_to(external)
                    else:
                        os.link(external, file)
                with self.assertRaises(bundles.KitError):
                    installer.install(root, self.target)
                self.assertFalse(self.target.exists())

    def test_release_file_drift_and_extra_empty_directory_rejected(self):
        _, lock = self.install()
        directory = self.release(lock)
        (directory / 'skills' / 'unknown-empty').mkdir()
        with self.assertRaisesRegex(bundles.KitError, 'Unowned directory'):
            installer.verify(self.target)
        (directory / 'skills' / 'unknown-empty').rmdir()
        (directory / 'skills' / 'alpha' / 'SKILL.md').write_text('Tampered')
        with self.assertRaisesRegex(bundles.KitError, 'drift'):
            installer.verify(self.target)

    def test_release_native_system_data_is_not_ignored(self):
        _, lock = self.install()
        native = self.release(lock) / 'skills' / '.system'
        native.mkdir()
        (native / 'owner').write_text('Unexpected native state')
        with self.assertRaisesRegex(bundles.KitError, 'drift'):
            installer.verify(self.target)
        self.assertTrue((native / 'owner').exists())

    def test_release_symlink_and_hardlink_drift_rejected(self):
        _, lock = self.install()
        file = self.release(lock) / 'skills' / 'alpha' / 'SKILL.md'
        external = self.root / 'owner-copy'
        external.write_bytes(file.read_bytes())
        file.unlink()
        file.symlink_to(external)
        with self.assertRaisesRegex(bundles.KitError, 'Symlink'):
            installer.verify(self.target)
        file.unlink()
        os.link(external, file)
        with self.assertRaisesRegex(bundles.KitError, 'Hard link'):
            installer.verify(self.target)
        self.assertTrue(external.exists())

    def test_stable_skill_root_replacement_rejected(self):
        self.install()
        (self.target / 'skills').rename(self.target / 'owner-skills')
        (self.target / 'skills').symlink_to('owner-skills', target_is_directory=True)
        with self.assertRaisesRegex(bundles.KitError, 'real directory'):
            installer.verify(self.target)
        self.assertTrue((self.target / 'owner-skills' / 'alpha').is_symlink())

    def test_parent_replacement_during_staging_preserves_both_homes(self):
        parent = self.root / 'parent'
        parent.mkdir()
        self.target = parent / 'home'
        root, _ = self.bundle()
        original = installer._copy_payload
        moved = self.root / 'moved-parent'

        def replace(source, destination):
            original(source, destination)
            parent.rename(moved)
            parent.mkdir()
            (parent / 'owner.txt').write_text('New owner')

        with mock.patch.object(installer, '_copy_payload', side_effect=replace):
            with self.assertRaises(bundles.KitError):
                installer.install(root, self.target)
        self.assertEqual((parent / 'owner.txt').read_text(), 'New owner')
        self.assertTrue(next((moved / 'home' / '.portable-kit').glob('.stage-*')).exists())
        self.assertFalse((parent / 'home').exists())

    def test_all_existing_home_operations_respect_lock(self):
        root, lock = self.install()
        with installer._locked(self.target):
            operations = (lambda: installer.plan(root, self.target), lambda: installer.install(root, self.target),
                          lambda: installer.verify(self.target), lambda: installer.describe(self.target),
                          lambda: installer.rollback(self.target), lambda: installer.retire(self.target, lock['id']),
                          lambda: installer.run(self.target, [sys.executable, '-c', 'pass']))
            for operation in operations:
                with self.subTest(operation=operation):
                    with self.assertRaisesRegex(bundles.KitError, 'lock is held'):
                        operation()
        installer.verify(self.target)

    def test_run_holds_lock_until_real_child_exits_and_sets_environment(self):
        self.install()
        ready = self.root / 'ready.json'
        release = self.root / 'release-child'
        output = self.root / 'child-output'
        child = ('import json,os,pathlib,time; '
                 f'pathlib.Path({str(ready)!r}).write_text(json.dumps(dict(home=os.environ["CODEX_HOME"], bytecode=os.environ["PYTHONDONTWRITEBYTECODE"]))); '
                 f'gate=pathlib.Path({str(release)!r}); '
                 'exec("while not gate.exists():\\n time.sleep(0.01)")')
        code = ('import sys; sys.path.insert(0,sys.argv[1]); import portable_install; '
                'raise SystemExit(portable_install.run(sys.argv[2],sys.argv[3:]))')
        with output.open('w') as stream:
            process = subprocess.Popen([sys.executable, '-B', '-c', code, str(REPO / 'scripts'), str(self.target), sys.executable, '-B', '-c', child], stdout=stream, stderr=stream)
            try:
                import time
                deadline = time.monotonic() + 10
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(), output.read_text())
                self.assertEqual(json.loads(ready.read_text()), {'home': str(self.target), 'bytecode': '1'})
                with self.assertRaisesRegex(bundles.KitError, 'lock is held'):
                    installer.verify(self.target)
                release.touch()
                self.assertEqual(process.wait(timeout=10), 0, output.read_text())
            finally:
                release.touch()
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
        installer.verify(self.target)

    def test_complete_stage_failure_cleans_only_known_bytes(self):
        root, _ = self.bundle()
        original = installer._copy_payload

        def fail(source, destination):
            original(source, destination)
            raise OSError('Injected stage failure')

        with mock.patch.object(installer, '_copy_payload', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'Injected'):
                installer.install(root, self.target)
        self.assertEqual(list((self.target / '.portable-kit').glob('.stage-*')), [])
        self.assertEqual(installer.install(root, self.target)['status'], 'installed')

    def test_unknown_stage_bytes_preserved_and_block_retry(self):
        root, _ = self.bundle()
        original = installer._copy_payload

        def fail(source, destination):
            original(source, destination)
            (destination / 'foreign.txt').write_text('Unknown owner')
            raise OSError('Injected stage failure')

        with mock.patch.object(installer, '_copy_payload', side_effect=fail):
            with self.assertRaisesRegex(bundles.KitError, 'preserved'):
                installer.install(root, self.target)
        stage = next((self.target / '.portable-kit').glob('.stage-*'))
        self.assertEqual((stage / 'foreign.txt').read_text(), 'Unknown owner')
        with self.assertRaisesRegex(bundles.KitError, 'Interrupted or unknown'):
            installer.install(root, self.target)

    def test_unknown_empty_stage_directory_is_preserved(self):
        root, _ = self.bundle()
        original = installer._copy_payload

        def fail(source, destination):
            original(source, destination)
            (destination / 'skills' / 'foreign-empty').mkdir()
            raise OSError('Injected stage failure')

        with mock.patch.object(installer, '_copy_payload', side_effect=fail):
            with self.assertRaisesRegex(bundles.KitError, 'preserved'):
                installer.install(root, self.target)
        self.assertTrue(next((self.target / '.portable-kit').glob('.stage-*')).joinpath('skills/foreign-empty').exists())

    def test_interrupted_activation_is_visible_and_blocks_retry(self):
        _, first = self.install()
        root, _ = self.bundle(('beta',), 'b')
        with mock.patch.object(installer, '_atomic_json', side_effect=OSError('Injected crash')):
            with self.assertRaisesRegex(bundles.KitError, 'Interrupted installation'):
                installer.install(root, self.target)
        marker = self.target / '.portable-kit' / 'transaction.json'
        self.assertEqual(json.loads(marker.read_text())['before']['current'], first['id'])
        with self.assertRaisesRegex(bundles.KitError, 'Interrupted or unknown'):
            installer.verify(self.target)

    def test_interrupted_publication_keeps_payload_and_transaction(self):
        self.install()
        root, lock = self.bundle(('beta',), 'b')
        original = installer._write_json

        def fail(path, value, exclusive=False):
            if path.name == lock['id'] + '.json':
                raise OSError('Injected manifest publication failure')
            return original(path, value, exclusive)

        with mock.patch.object(installer, '_write_json', side_effect=fail):
            with self.assertRaisesRegex(bundles.KitError, 'Interrupted installation'):
                installer.install(root, self.target)
        self.assertEqual(installer._scan(self.release(lock)), lock['files'])
        self.assertEqual(json.loads((self.target / '.portable-kit' / 'transaction.json').read_text())['release'], lock['id'])
        with self.assertRaisesRegex(bundles.KitError, 'Interrupted or unknown'):
            installer.verify(self.target)

    def test_process_crash_leaves_stage_and_uncertain_lock(self):
        root, lock = self.bundle()
        code = ('import os,sys; sys.path.insert(0,sys.argv[1]); import portable_install as p; '
                'original=p._copy_payload; '
                'exec("def crash(source,destination):\\n original(source,destination)\\n os._exit(73)"); '
                'p._copy_payload=crash; p.install(sys.argv[2],sys.argv[3])')
        result = subprocess.run([sys.executable, '-B', '-c', code, str(REPO / 'scripts'), str(root), str(self.target)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 73, result.stderr)
        stage = next((self.target / '.portable-kit').glob('.stage-*'))
        self.assertEqual(installer._scan(stage), lock['files'])
        self.assertTrue((self.target / '.portable-kit' / 'operation.lock').exists())
        with self.assertRaisesRegex(bundles.KitError, 'lock is held'):
            installer.install(root, self.target)

    def test_retention_retire_then_fourth_install_and_ownership_union(self):
        first, second, third = self.three()
        fourth, lock = self.bundle(('delta', 'shared'), 'd')
        with self.assertRaisesRegex(bundles.KitError, 'admission limit'):
            installer.install(fourth, self.target)
        foreign = self.target / 'skills' / 'foreign'
        foreign.mkdir()
        (foreign / 'owner').write_text('Unmanaged')
        result = installer.retire(self.target, first['id'])
        self.assertEqual(result['status'], 'retired')
        self.assertFalse(self.release(first).exists())
        self.assertFalse((self.target / '.portable-kit' / 'manifests' / (first['id'] + '.json')).exists())
        self.assertFalse((self.target / 'skills' / 'alpha').is_symlink())
        self.assertTrue((self.target / 'skills' / 'shared').is_symlink())
        self.assertTrue((self.target / 'skills' / 'beta').is_symlink())
        self.assertEqual(installer.install(fourth, self.target)['release_id'], lock['id'])
        self.assertEqual(len(installer.verify(self.target)['releases']), 3)
        self.assertEqual((foreign / 'owner').read_text(), 'Unmanaged')
        self.assertEqual(installer.rollback(self.target)['release_id'], third['id'])
        self.assertEqual(installer.rollback(self.target, second['id'])['release_id'], second['id'])

    def test_retire_rejects_current_previous_unknown_and_drift(self):
        first, second, third = self.three()
        for release in (second['id'], third['id'], 'unknown'):
            with self.subTest(release=release):
                with self.assertRaises(bundles.KitError):
                    installer.retire(self.target, release)
        (self.release(first) / 'AGENTS.md').write_text('Drift')
        with self.assertRaisesRegex(bundles.KitError, 'drift'):
            installer.retire(self.target, first['id'])
        self.assertFalse((self.target / '.portable-kit' / 'transaction.json').exists())
        self.assertTrue(self.release(first).exists())

    def test_retire_interruption_preserves_intent_and_quarantine(self):
        first, _, _ = self.three()
        with mock.patch.object(installer, '_remove_stage', return_value=False):
            with self.assertRaisesRegex(bundles.KitError, 'Interrupted retirement'):
                installer.retire(self.target, first['id'])
        marker = json.loads((self.target / '.portable-kit' / 'transaction.json').read_text())
        self.assertEqual(marker['operation'], 'retire')
        quarantine = self.target / '.portable-kit' / marker['quarantine']
        self.assertEqual(installer._scan(quarantine), first['files'])
        self.assertFalse(self.release(first).exists())
        with self.assertRaisesRegex(bundles.KitError, 'Interrupted or unknown'):
            installer.verify(self.target)

    def test_retire_foreign_bytes_in_quarantine_are_not_deleted(self):
        first, _, _ = self.three()
        original = installer._remove_stage

        def inject(directory, identity, lock, home=None):
            (directory / 'owner.txt').write_text('Foreign owner')
            return original(directory, identity, lock, home)

        with mock.patch.object(installer, '_remove_stage', side_effect=inject):
            with self.assertRaisesRegex(bundles.KitError, 'Interrupted retirement'):
                installer.retire(self.target, first['id'])
        quarantine = next((self.target / '.portable-kit').glob('.retired-*'))
        self.assertEqual((quarantine / 'owner.txt').read_text(), 'Foreign owner')
        self.assertTrue((quarantine / 'AGENTS.md').exists())
        self.assertTrue((self.target / 'skills' / 'alpha').is_symlink())

    def test_retirement_does_not_delete_replaced_orphan_link(self):
        first, _, _ = self.three()
        original = installer._remove_stage
        entry = self.target / 'skills' / 'alpha'

        def replace(directory, identity, lock, home=None):
            entry.unlink()
            entry.mkdir()
            (entry / 'owner').write_text('New owner')
            return original(directory, identity, lock, home)

        with mock.patch.object(installer, '_remove_stage', side_effect=replace):
            with self.assertRaisesRegex(bundles.KitError, 'Interrupted retirement'):
                installer.retire(self.target, first['id'])
        self.assertEqual((entry / 'owner').read_text(), 'New owner')
        self.assertTrue((self.target / '.portable-kit' / 'transaction.json').exists())

    def test_retirement_parent_replacement_preserves_unknown_home(self):
        first, _, _ = self.three()
        original = installer._remove_stage
        moved = self.root / 'moved-home'

        def replace(directory, identity, lock, home=None):
            self.target.rename(moved)
            self.target.mkdir()
            (self.target / 'owner').write_text('Foreign home')
            return original(directory, identity, lock, home)

        with mock.patch.object(installer, '_remove_stage', side_effect=replace):
            with self.assertRaisesRegex(bundles.KitError, 'Interrupted retirement'):
                installer.retire(self.target, first['id'])
        self.assertEqual((self.target / 'owner').read_text(), 'Foreign home')
        quarantine = next((moved / '.portable-kit').glob('.retired-*'))
        self.assertEqual(installer._scan(quarantine), first['files'])
        self.assertTrue((moved / '.portable-kit' / 'transaction.json').exists())

    def test_budget_is_three_generations_one_gibibyte(self):
        self.assertEqual(installer.MAX_RELEASES, 3)
        self.assertEqual(installer.MAX_BYTES, 1024 * 1024 * 1024)
        _, first = self.install()
        second, _ = self.bundle(version='b')
        with mock.patch.object(installer, 'MAX_BYTES', sum(row['bytes'] for row in first['files'].values())):
            with self.assertRaisesRegex(bundles.KitError, 'admission limit'):
                installer.install(second, self.target)
        self.assertEqual(installer.verify(self.target)['release_id'], first['id'])


if __name__ == '__main__':
    unittest.main()
