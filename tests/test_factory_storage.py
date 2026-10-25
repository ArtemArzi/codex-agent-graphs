import argparse
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

import test_software_factory as fixtures


SCRIPT = fixtures.HELPER
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('factory_storage_subject', SCRIPT)
factory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(factory)
storage = factory.storage


class FactoryStorageTests(unittest.TestCase):
    setUp = fixtures.FactoryTests.setUp
    git = fixtures.FactoryTests.git
    cli = fixtures.FactoryTests.cli
    prepare = fixtures.FactoryTests.prepare
    commit = fixtures.FactoryTests.commit
    verify = fixtures.FactoryTests.verify

    def manifest(self):
        return json.loads((self.workspace / 'workspace.json').read_text())

    def managed(self):
        return self.cli('prepare', '--repo', self.repo, '--workspace', self.workspace,
                        '--job', 'alpha', '--owns', 'a.txt', '--objective', 'Test',
                        '--lifecycle', 'ephemeral', '--authority', 'TASK', '--owner', 'writer-alpha')

    def checked(self, *, joined=True, code='print("original evidence")', expected=0):
        job = self.managed()
        self.commit(job, {'a.txt': '41\n'})
        flags = ['--writers-joined'] if joined else []
        result = self.cli('verify', '--workspace', self.workspace, *flags, '--', sys.executable,
                          '-c', code, expected=expected)
        return job, result

    def close(self, result, apply=False, authority='TASK'):
        return self.cli('close', '--workspace', self.workspace, '--resource', result['resource'],
                        '--authority', authority, *(['--apply'] if apply else []))

    def finish(self, key='job:alpha', owner='writer-alpha', authority='TASK', joined=True, expected=0):
        return self.cli('finish', '--workspace', self.workspace, '--resource', key,
                        '--owner', owner, '--authority', authority, '--outcome', 'terminal',
                        *(['--writers-joined'] if joined else []), expected=expected)

    def test_repeat_check_reuses_one_checkout_but_runs_again_and_keeps_logs(self):
        _, first = self.checked()
        candidate = Path(first['candidate_path'])
        inode = candidate.stat().st_ino
        second = self.cli('verify', '--workspace', self.workspace, '--writers-joined', '--',
                          sys.executable, '-c', 'print("fresh failure"); raise SystemExit(7)', expected=1)
        self.assertEqual(second['candidate_path'], str(candidate))
        self.assertEqual(candidate.stat().st_ino, inode)
        self.assertTrue(second['reused'])
        self.assertEqual(second['check'], 'fail')
        self.assertEqual(second['returncode'], 7)
        self.assertNotEqual(first['log'], second['log'])
        self.assertEqual(Path(first['log']).read_text(), 'original evidence\n')
        self.assertEqual(Path(second['log']).read_text(), 'fresh failure\n')
        self.assertEqual(len(list((self.workspace / 'integration').iterdir())), 1)
        self.assertEqual(len(list((self.workspace / 'evidence').glob('*.json'))), 2)

    def test_reservation_precedes_allocation_and_absent_retry_completes(self):
        original = storage.git
        def fail(repo, *args):
            if args[:2] == ('worktree', 'add'):
                manifest = self.manifest()
                self.assertEqual(manifest['jobs']['alpha']['allocation'], 'reserved')
                self.assertEqual(manifest['storage']['resources']['job:alpha']['state'], 'reserved')
                raise storage.StorageError('injected allocation failure')
            return original(repo, *args)
        args = argparse.Namespace(repo=str(self.repo), workspace=str(self.workspace), job='alpha',
                                  owns=['a.txt'], objective='Test', base='main', context=None,
                                  authority='TASK', lifecycle='ephemeral', owner='writer-alpha')
        with mock.patch.object(storage, 'git', side_effect=fail):
            with self.assertRaisesRegex(storage.StorageError, 'injected'):
                factory.prepare(args)
        self.assertFalse((self.workspace / 'jobs' / 'alpha').exists())
        report = self.cli('storage', '--workspace', self.workspace)
        self.assertEqual(report['resources'][0]['state'], 'reserved')
        self.assertFalse(report['resources'][0]['eligible'])
        result = factory.prepare(args)
        self.assertTrue(Path(result['path']).exists())
        self.assertEqual(self.manifest()['jobs']['alpha']['allocation'], 'ready')

    def test_partial_allocation_not_overwritten_after_post_add_failure(self):
        original = storage.atomic
        def fail(path, value):
            resource = value.get('storage', {}).get('resources', {}).get('job:alpha', {})
            if resource.get('state') == 'ready':
                raise OSError('injected manifest publication failure')
            return original(path, value)
        args = argparse.Namespace(repo=str(self.repo), workspace=str(self.workspace), job='alpha',
                                  owns=['a.txt'], objective='Test', base='main', context=None,
                                  authority='TASK', lifecycle='ephemeral', owner='writer-alpha')
        with mock.patch.object(storage, 'atomic', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'publication'):
                factory.prepare(args)
        path = self.workspace / 'jobs' / 'alpha'
        (path / 'sentinel').write_text('foreign recovery')
        self.assertIn('Partial/foreign', self.managed_error())
        self.assertEqual((path / 'sentinel').read_text(), 'foreign recovery')
        self.assertEqual(self.manifest()['jobs']['alpha']['allocation'], 'reserved')

    def managed_error(self):
        return self.cli('prepare', '--repo', self.repo, '--workspace', self.workspace,
                        '--job', 'alpha', '--owns', 'a.txt', '--objective', 'Test',
                        '--lifecycle', 'ephemeral', '--authority', 'TASK', '--owner', 'writer-alpha', expected=2)

    def test_integration_reservation_failure_retry_does_not_allocate_second_copy(self):
        job = self.managed()
        self.commit(job, {'a.txt': '41\n'})
        original = storage.git
        def fail(repo, *args):
            if args[:2] == ('worktree', 'add'):
                self.assertEqual(len([r for r in self.manifest()['storage']['resources'].values()
                                      if r['key'].startswith('integration:')]), 1)
                raise storage.StorageError('injected')
            return original(repo, *args)
        args = argparse.Namespace(workspace=str(self.workspace), command=[sys.executable, '-c', 'assert True'],
                                  timeout=10, writers_joined=True)
        with mock.patch.object(storage, 'git', side_effect=fail):
            with self.assertRaisesRegex(storage.StorageError, 'injected'):
                factory.verify(args)
        result = factory.verify(args)
        self.assertEqual(result['check'], 'pass')
        self.assertEqual(len(list((self.workspace / 'integration').iterdir())), 1)

    def test_close_dry_run_apply_preserves_refs_all_evidence_and_source(self):
        job, result = self.checked()
        before_refs = self.git(self.repo, 'show-ref')
        evidence = {p: p.read_bytes() for p in (self.workspace / 'evidence').iterdir()}
        self.assertTrue(self.close(result)['eligible'])
        self.assertTrue(Path(result['candidate_path']).exists())
        self.assertTrue(self.close(result, apply=True)['removed'])
        self.assertFalse(Path(result['candidate_path']).exists())
        self.assertEqual(self.git(self.repo, 'show-ref'), before_refs)
        self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.base)
        for path, payload in evidence.items():
            self.assertEqual(path.read_bytes(), payload)
        self.finish()
        report = self.cli('close', '--workspace', self.workspace, '--resource', 'job:alpha',
                          '--authority', 'TASK', '--apply')
        self.assertTrue(report['removed'])
        self.assertFalse(Path(job['path']).exists())
        self.assertEqual(self.git(self.repo, 'show-ref'), before_refs)

    def test_failed_check_can_close_with_anchored_branch_and_receipt(self):
        _, result = self.checked(code='raise SystemExit(1)', expected=1)
        self.assertTrue(self.close(result, apply=True)['removed'])
        self.assertEqual(self.git(self.repo, 'rev-parse', result['candidate_branch']), result['candidate_sha'])
        self.assertEqual(json.loads(Path(self.manifest()['storage']['resources'][result['resource']]['receipt']).read_text())['check'], 'fail')

    def test_default_retain_legacy_wrong_authority_and_unjoined_owner_refuse(self):
        job = self.prepare()
        self.commit(job, {'a.txt': '41\n'})
        result = self.verify()
        report = self.close(result, apply=True)
        self.assertFalse(report['removed'])
        self.assertIn('lifecycle', ' '.join(report['reasons']))
        state = self.manifest()
        del state['storage']
        (self.workspace / 'workspace.json').write_text(json.dumps(state))
        self.assertIn('Legacy', self.cli('storage', '--workspace', self.workspace, expected=2))

    def test_active_and_wrong_owner_guards_even_when_clean(self):
        job, result = self.checked(joined=False)
        report = self.close(result, apply=True)
        self.assertFalse(report['removed'])
        self.assertIn('active/unfinished', ' '.join(report['reasons']))
        self.assertIn('mismatch', self.finish(owner='other', expected=2))
        self.assertIn('join all writers', self.finish(joined=False, expected=2))
        self.finish(key=result['resource'], owner=result['owner'])
        self.assertFalse(self.close(result, apply=True, authority='OTHER')['removed'])
        self.assertTrue(self.close(result, apply=True)['removed'])
        self.assertTrue(Path(job['path']).exists())

    def test_dirty_ignored_staged_untracked_and_admin_data_retain(self):
        _, result = self.checked()
        path = Path(result['candidate_path'])
        admin = Path(self.git(path, 'rev-parse', '--absolute-git-dir'))
        cases = [(path / 'a.txt', 'changed'), (path / 'unknown', 'unknown'),
                 (path / '__pycache__' / 'valuable', 'ignored'),
                 (admin / 'MERGE_HEAD', self.base), (admin / 'index.lock', 'active'),
                 (admin / 'config.worktree', '[core]\n'),
                 (admin / 'refs' / 'worktree' / 'keep', self.base + '\n')]
        for file, content in cases:
            with self.subTest(file=file):
                original = file.read_bytes() if file.exists() else None
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content)
                report = self.close(result, apply=True)
                self.assertFalse(report['removed'], report)
                self.assertEqual(file.read_text(), content)
                if original is not None:
                    file.write_bytes(original)
                else:
                    file.unlink()
                    if file.parent.name in ('__pycache__', 'worktree'):
                        file.parent.rmdir()
                    if (admin / 'refs').exists():
                        (admin / 'refs').rmdir()
        (path / 'a.txt').write_text('staged')
        self.git(path, 'add', 'a.txt')
        self.assertFalse(self.close(result, apply=True)['removed'])

    def test_reflog_only_commit_is_not_deleted(self):
        _, result = self.checked()
        path = Path(result['candidate_path'])
        (path / 'a.txt').write_text('valuable commit\n')
        self.git(path, 'add', 'a.txt')
        self.git(path, 'commit', '-m', 'Reflog only')
        orphan = self.git(path, 'rev-parse', 'HEAD')
        self.git(path, 'reset', '--hard', result['candidate_sha'])
        report = self.close(result, apply=True)
        self.assertFalse(report['removed'])
        self.assertIn('reflog-only', ' '.join(report['reasons']))
        self.assertIn('valuable commit', self.git(path, 'show', orphan + ':a.txt'))

    def test_cap_counts_retained_candidates_and_dirty_exact_candidate_never_duplicates(self):
        job = self.prepare()
        self.commit(job, {'a.txt': '41\n'})
        first = self.verify()
        (Path(first['candidate_path']) / 'valuable').write_text('retain')
        self.assertIn('retained without replacement', self.verify(expected=2))
        self.assertEqual(len(list((self.workspace / 'integration').iterdir())), 1)
        self.commit(job, {'a.txt': '42\n'})
        second = self.verify()
        self.assertNotEqual(first['candidate_path'], second['candidate_path'])
        self.commit(job, {'a.txt': '43\n'})
        self.assertIn('cap reached', self.verify(expected=2))
        self.assertEqual(len(list((self.workspace / 'integration').iterdir())), 2)
        self.assertEqual((Path(first['candidate_path']) / 'valuable').read_text(), 'retain')

    def test_new_inputs_automatically_close_only_eligible_previous_candidate(self):
        job, first = self.checked()
        self.commit(job, {'a.txt': '42\n'})
        second = self.cli('verify', '--workspace', self.workspace, '--writers-joined', '--',
                          sys.executable, '-c', 'assert True')
        self.assertFalse(Path(first['candidate_path']).exists())
        self.assertTrue(Path(second['candidate_path']).exists())
        self.assertEqual(len(list((self.workspace / 'integration').iterdir())), 1)
        self.assertTrue(Path(first['log']).exists())
        self.assertEqual(self.git(self.repo, 'rev-parse', first['candidate_branch']), first['candidate_sha'])

    def test_timeout_unfinished_and_stale_checks_retain_and_cannot_finish(self):
        job = self.managed()
        self.commit(job, {'a.txt': '41\n'})
        result = self.cli('verify', '--workspace', self.workspace, '--writers-joined', '--timeout', '1',
                          '--', sys.executable, '-c', 'import time; time.sleep(3)', expected=1)
        self.assertFalse(self.close(result, apply=True)['removed'])
        self.assertIn('Unfinished', self.finish(key=result['resource'], owner=result['owner'], expected=2))
        self.assertIn('retained without replacement', self.verify(expected=2))

    def test_identity_alias_replacement_and_source_race_retain(self):
        _, result = self.checked()
        alias = self.root / 'alias'
        alias.symlink_to(self.workspace, target_is_directory=True)
        self.assertIn('alias', self.cli('close', '--workspace', alias, '--resource', result['resource'],
                                       '--authority', 'TASK', '--apply', expected=2))
        path = Path(result['candidate_path'])
        moved = path.with_name(path.name + '-preserved')
        path.rename(moved)
        path.mkdir()
        (path / 'sentinel').write_text('foreign')
        report = self.close(result, apply=True)
        self.assertFalse(report['removed'])
        self.assertIn('identity changed', ' '.join(report['reasons']))
        self.assertEqual((path / 'sentinel').read_text(), 'foreign')
        path.rename(path.with_name(path.name + '-foreign'))
        moved.rename(path)
        (self.repo / 'b.txt').write_text('101\n')
        self.git(self.repo, 'add', 'b.txt')
        self.git(self.repo, 'commit', '-m', 'Source movement')
        self.assertFalse(self.close(result, apply=True)['removed'])

    def test_final_recheck_prevents_removal_on_mutation_and_native_remove_has_no_force(self):
        _, result = self.checked()
        manifest = self.manifest()
        resource = manifest['storage']['resources'][result['resource']]
        path = Path(result['candidate_path'])
        original = storage.inspect
        calls = []
        def raced(*args):
            calls.append(1)
            if len(calls) == 2:
                (path / 'raced').write_text('external writer')
            return original(*args)
        with mock.patch.object(storage, 'inspect', side_effect=raced):
            report = storage.close_resource(manifest, self.workspace, resource, 'TASK', True)
        self.assertFalse(report['removed'])
        self.assertEqual((path / 'raced').read_text(), 'external writer')
        (path / 'raced').unlink()
        original_git = storage.git
        argv = []
        def recorded(repo, *args):
            argv.append(args)
            return original_git(repo, *args)
        with mock.patch.object(storage, 'git', side_effect=recorded):
            report = storage.close_resource(manifest, self.workspace, resource, 'TASK', True)
        self.assertTrue(report['removed'])
        self.assertIn(('worktree', 'remove', str(path)), argv)
        self.assertFalse(any('--force' in args or 'prune' in args for args in argv))

    def test_storage_is_read_only_and_report_preserves_index_bytes(self):
        _, result = self.checked()
        path = Path(result['candidate_path'])
        admin = Path(self.git(path, 'rev-parse', '--absolute-git-dir'))
        watched = [self.workspace / 'workspace.json', admin / 'index']
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in watched}
        names = sorted(str(p.relative_to(self.workspace)) for p in self.workspace.rglob('*'))
        self.cli('storage', '--workspace', self.workspace)
        self.assertEqual(names, sorted(str(p.relative_to(self.workspace)) for p in self.workspace.rglob('*')))
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in watched})

    def test_unknown_admin_draft_changed_evidence_and_common_identity_refuse(self):
        _, result = self.checked()
        path = Path(result['candidate_path'])
        admin = Path(self.git(path, 'rev-parse', '--absolute-git-dir'))
        draft = admin / 'COMMIT_EDITMSG'
        prior = draft.read_bytes() if draft.exists() else None
        draft.write_text('unsaved draft')
        self.assertIn('commit message', ' '.join(self.close(result, True)['reasons']))
        if prior is None:
            draft.unlink()
        else:
            draft.write_bytes(prior)
        log = Path(result['log'])
        before = log.read_bytes()
        log.write_text('foreign log')
        self.assertIn('evidence changed', ' '.join(self.close(result, True)['reasons']))
        log.write_bytes(before)
        manifest = self.manifest()
        manifest['storage']['common']['inode'] += 1
        (self.workspace / 'workspace.json').write_text(json.dumps(manifest))
        self.assertIn('common-dir', self.cli('close', '--workspace', self.workspace,
                                           '--resource', result['resource'], '--authority', 'TASK',
                                           '--apply', expected=2))
        self.assertTrue(path.exists())

    def test_recheck_manifest_race_and_native_locked_worktree_refuse(self):
        _, result = self.checked()
        path = Path(result['candidate_path'])
        self.git(self.repo, 'worktree', 'lock', str(path), '--reason', 'active external owner')
        self.assertFalse(self.close(result, True)['removed'])
        self.git(self.repo, 'worktree', 'unlock', str(path))
        manifest = self.manifest()
        resource = manifest['storage']['resources'][result['resource']]
        original = storage.inspect
        def changed(*args):
            report = original(*args)
            latest = self.manifest()
            latest['external_writer'] = 'active'
            (self.workspace / 'workspace.json').write_text(json.dumps(latest))
            return report
        with mock.patch.object(storage, 'inspect', side_effect=changed):
            with self.assertRaisesRegex(storage.StorageError, 'Workspace changed'):
                storage.close_resource(manifest, self.workspace, resource, 'TASK', True)
        self.assertTrue(path.exists())

    def test_interrupted_recheck_never_reuses_old_pass_receipt(self):
        _, result = self.checked()
        original = factory.save
        def fail(path, value):
            if path.parent.name == 'evidence' and value.get('check') == 'incomplete':
                raise OSError('crashed before check')
            return original(path, value)
        args = argparse.Namespace(workspace=str(self.workspace), command=[sys.executable, '-c', 'assert True'],
                                  timeout=10, writers_joined=True)
        with mock.patch.object(factory, 'save', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'crashed'):
                factory.verify(args)
        manifest = self.manifest()
        resource = manifest['storage']['resources'][result['resource']]
        self.assertEqual(resource['state'], 'active')
        self.assertEqual(len(resource['attempts']), 2)
        self.assertFalse(Path(resource['receipt']).exists())
        self.assertFalse(self.close(result, True)['removed'])
        self.finish(key=result['resource'], owner=result['owner'], expected=2)
        self.assertTrue(Path(result['candidate_path']).exists())

    def test_atomic_publication_failure_preserves_destination_and_foreign_temp(self):
        dest = self.root / 'state.json'
        dest.write_text('original')
        sentinel = self.root / 'foreign.tmp'
        sentinel.write_text('foreign')
        with mock.patch.object(storage.os, 'replace', side_effect=OSError('publication failed')):
            with self.assertRaisesRegex(OSError, 'publication failed'):
                storage.atomic(dest, {'value': 'new'})
        self.assertEqual(dest.read_text(), 'original')
        self.assertEqual(sentinel.read_text(), 'foreign')
        self.assertEqual(list(self.root.glob('state.json.*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
