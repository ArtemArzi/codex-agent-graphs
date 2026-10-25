import importlib.util
import contextlib
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

API = load('storage_install_api', 'scripts/install.py')
STORAGE = load('tested_storage_install', 'scripts/storage_install.py')


def same_target(path, target):
    path = Path(path)
    return path.name == target.name and path.parent.samefile(target.parent)


class Fixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.source = self.root / 'source'; (self.source / 'policies/storage-overlays').mkdir(parents=True)
        (self.source / 'skills/example').mkdir(parents=True)
        (self.source / 'skills/example/helper.py').write_text('new helper\n')
        (self.source / 'policies/orchestration.md').write_text('new policy\n')
        self.old_block = API.ORCHESTRATION_POLICY_BLOCK_START + '\nold policy\n' + API.ORCHESTRATION_POLICY_BLOCK_END + '\n'
        self.spec = {'schema_version': 1, 'files': [
            {'source':'skills/example/helper.py', 'target':'skills/example/helper.py',
             'before_sha256':[STORAGE.digest(b'old helper\n')], 'after_sha256':STORAGE.digest(b'new helper\n')},
            {'source':'skills/example/helper.py', 'target':'skills/example/new.py',
             'before_sha256':[None], 'after_sha256':STORAGE.digest(b'new helper\n')}],
            'policy_before_sha256':[STORAGE.digest(self.old_block.encode())],
            'policy_after_sha256':STORAGE.digest(b'new policy\n')}
        (self.source / 'policies/storage-files.json').write_text(json.dumps(self.spec))
        (self.source / 'policies/storage-overlays/manifest.json').write_text(json.dumps({'overlays':[]}))
        self.homes = []
        for label in ('wsl','desktop'):
            home = self.root / label; (home / 'skills/example').mkdir(parents=True)
            (home / 'skills/example/helper.py').write_text('old helper\n')
            (home / 'skills/example/helper.py').chmod(0o755)
            (home / 'skills/example/foreign.py').write_text('foreign')
            (home / 'AGENTS.md').write_text('user prefix\n' + self.old_block + 'user suffix\n')
            (home / 'config.toml').write_text('private profile, disabled skills unchanged\n')
            self.homes.append((label,home))
        self.before = {p:p.read_bytes() for _,h in self.homes for p in h.rglob('*') if p.is_file()}

    def tearDown(self):
        self.temp.cleanup()

    def install(self):
        return STORAGE.run('install',self.homes,root=self.source,api=API)


class StorageInstallerTests(Fixture, unittest.TestCase):
    def test_plan_install_readback_noop_and_protected_files(self):
        plan=STORAGE.run('plan',self.homes,root=self.source,api=API)
        self.assertEqual('ok',plan['status'])
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.before})
        result=self.install(); self.assertEqual(4,len(result['backups']))
        for _,home in self.homes:
            self.assertEqual(b'new helper\n',(home/'skills/example/helper.py').read_bytes())
            self.assertEqual(0o755,(home/'skills/example/helper.py').stat().st_mode & 0o777)
            self.assertEqual(1,(home/'skills/example/helper.py').stat().st_nlink)
            self.assertEqual('foreign',(home/'skills/example/foreign.py').read_text())
            self.assertEqual(self.before[home/'config.toml'],(home/'config.toml').read_bytes())
            text=(home/'AGENTS.md').read_text()
            self.assertTrue(text.startswith('user prefix\n')); self.assertTrue(text.endswith('user suffix\n'))
        backups={p for _,h in self.homes for p in (h/'backups').rglob('*')}
        self.assertEqual([],self.install()['backups'])
        self.assertEqual(backups,{p for _,h in self.homes for p in (h/'backups').rglob('*')})
        self.assertEqual('ok',STORAGE.run('verify',self.homes,root=self.source,api=API)['status'])

    def test_second_home_conflict_prevents_first_home_write(self):
        (self.homes[1][1]/'skills/example/helper.py').write_text('foreign edit')
        with self.assertRaisesRegex(STORAGE.StorageInstallError,'drift'):self.install()
        self.assertEqual(b'old helper\n',(self.homes[0][1]/'skills/example/helper.py').read_bytes())
        self.assertFalse((self.homes[0][1]/'backups').exists())

    def test_failure_in_second_home_rolls_back_both(self):
        original=STORAGE.capture_publish; failed=[]
        def write(path, content, *args):
            if path == self.homes[1][1]/'skills/example/helper.py' and not failed:
                failed.append(True); raise OSError('second-home failure')
            return original(path,content,*args)
        with mock.patch.object(STORAGE,'capture_publish',side_effect=write), self.assertRaises(OSError):self.install()
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.before})
        for _,home in self.homes:
            self.assertFalse((home/'skills/example/new.py').exists())
            self.assertEqual(1,(home/'skills/example/helper.py').stat().st_nlink)
        self.assertEqual(0o755,(self.homes[0][1]/'skills/example/helper.py').stat().st_mode & 0o777)

    def test_concurrent_edit_survives_rollback(self):
        original=STORAGE.capture_publish; target=self.homes[0][1]/'skills/example/helper.py'
        def write(path, content, *args):
            if path == self.homes[1][1]/'skills/example/helper.py':
                target.write_text('concurrent bytes'); raise OSError('second-home failure')
            return original(path,content,*args)
        with mock.patch.object(STORAGE,'capture_publish',side_effect=write), self.assertRaises(OSError) as error:self.install()
        self.assertEqual('concurrent bytes',target.read_text())
        self.assertTrue(any('concurrent' in n for n in error.exception.__notes__))

    def test_target_source_preimages_and_path_aliases(self):
        inputs,plans=STORAGE.build_plans(self.homes,self.source,API)
        (self.homes[0][1]/'skills/example/helper.py').write_text('new external')
        with self.assertRaisesRegex(STORAGE.StorageInstallError,'Concurrent'):
            STORAGE.apply_plans(plans,inputs,self.source,API)
        self.assertEqual(b'old helper\n',(self.homes[1][1]/'skills/example/helper.py').read_bytes())
        (self.source/'skills/example/helper.py').write_text('changed source')
        with self.assertRaisesRegex(STORAGE.StorageInstallError,'Unreviewed'):
            STORAGE.build_plans(self.homes,self.source,API)
        (self.source/'skills/example/helper.py').write_text('new helper\n')
        alias=self.root/'alias'; alias.symlink_to(self.homes[0][1],target_is_directory=True)
        with self.assertRaises(STORAGE.StorageInstallError):STORAGE.build_plans([('alias',alias)],self.source,API)

    def test_overlay_exact_preimage_noop_and_unknown_drift(self):
        entry={'target':'skills/example/SKILL.md','before_sha256':STORAGE.digest(b'before'),
               'after_sha256':STORAGE.digest(b'after'),'edits':[['before','after']]}
        self.assertEqual(b'after',STORAGE.rendered_overlay(b'before',entry))
        self.assertEqual(b'after',STORAGE.rendered_overlay(b'after',entry))
        with self.assertRaises(STORAGE.StorageInstallError):STORAGE.rendered_overlay(b'foreign',entry)

    def test_capability_failure_on_second_home_precedes_every_target_write(self):
        link=STORAGE.os.link
        def refuse(source,dest):
            if Path(source).resolve().is_relative_to(self.homes[1][1]):raise OSError('unsupported filesystem')
            return link(source,dest)
        with mock.patch.object(STORAGE.os,'link',side_effect=refuse), self.assertRaises(OSError):self.install()
        self.assertEqual(self.before,{p:p.read_bytes() for p in self.before})


class PublicationRaceTests(Fixture, unittest.TestCase):
    def test_edit_arriving_at_capture_is_retained_and_rejected(self):
        target=self.homes[0][1]/'skills/example/helper.py'; rename=STORAGE.os.rename; injected=[]
        def race(source,dest):
            if same_target(source,target) and Path(dest).name=='displaced' and not injected:
                target.write_text('CONCURRENT USER EDIT\n'); injected.append(True)
            return rename(source,dest)
        with mock.patch.object(STORAGE.os,'rename',side_effect=race), self.assertRaises(STORAGE.StorageInstallError):self.install()
        self.assertTrue(injected); self.assertEqual('CONCURRENT USER EDIT\n',target.read_text())
        self.assertEqual(1,target.stat().st_nlink)

    def test_recreated_target_at_publication_is_never_overwritten(self):
        target=self.homes[0][1]/'skills/example/helper.py'; link=STORAGE.os.link; injected=[]
        def race(source,dest):
            if same_target(dest,target) and Path(source).name=='prepared' and not injected:
                target.write_text('RECREATED USER FILE\n'); injected.append(True)
            return link(source,dest)
        with mock.patch.object(STORAGE.os,'link',side_effect=race), self.assertRaises(FileExistsError):self.install()
        self.assertEqual('RECREATED USER FILE\n',target.read_text())
        self.assertIn(b'old helper\n',[p.read_bytes() for p in (self.homes[0][1]/'backups').rglob('displaced')])

    def test_open_writer_to_displaced_inode_is_preserved_and_detected(self):
        target=self.homes[0][1]/'skills/example/helper.py'; link=STORAGE.os.link; injected=[]
        with target.open('r+') as held:
            def race(source,dest):
                result=link(source,dest)
                if same_target(dest,target) and Path(source).name=='prepared' and not injected:
                    held.seek(0); held.truncate(); held.write('LATE OPEN FD EDIT\n'); held.flush(); injected.append(True)
                return result
            with mock.patch.object(STORAGE.os,'link',side_effect=race), self.assertRaisesRegex(STORAGE.StorageInstallError,'inode changed'):self.install()
        self.assertIn(b'LATE OPEN FD EDIT\n',[p.read_bytes() for p in (self.homes[0][1]/'backups').rglob('displaced')])

    def rollback_race(self, phase, filename='helper.py'):
        target=self.homes[0][1]/('skills/example/'+filename)
        publish=STORAGE.capture_publish; rename=STORAGE.os.rename; link=STORAGE.os.link
        rolling=[False]; injected=[]
        def fail_second(path,payload,*args):
            if path==self.homes[1][1]/'skills/example/helper.py':
                rolling[0]=True; raise OSError('second home failure')
            return publish(path,payload,*args)
        def capture(source,dest):
            if rolling[0] and phase=='capture' and same_target(source,target) and not injected:
                target.write_text('ROLLBACK USER EDIT\n'); injected.append(True)
            return rename(source,dest)
        def publication(source,dest):
            if rolling[0] and phase=='publication' and same_target(dest,target) and Path(source).name=='prepared' and not injected:
                target.write_text('ROLLBACK USER EDIT\n'); injected.append(True)
            return link(source,dest)
        with mock.patch.object(STORAGE,'capture_publish',side_effect=fail_second), mock.patch.object(STORAGE.os,'rename',side_effect=capture), mock.patch.object(STORAGE.os,'link',side_effect=publication), self.assertRaises(OSError):self.install()
        self.assertTrue(injected); self.assertEqual('ROLLBACK USER EDIT\n',target.read_text())
        self.assertEqual(1,target.stat().st_nlink)

    def test_rollback_capture_keeps_new_concurrent_edit(self):self.rollback_race('capture')
    def test_rollback_publication_keeps_recreated_file(self):self.rollback_race('publication')
    def test_new_file_rollback_does_not_unlink_foreign_bytes(self):self.rollback_race('capture','new.py')

    def test_durable_journal_precedes_capture_and_symlink_is_retained(self):
        target=self.homes[0][1]/'skills/example/helper.py'; foreign=self.root/'foreign'; foreign.write_text('untouched')
        rename=STORAGE.os.rename; observed=[]
        def race(source,dest):
            if same_target(source,target) and not observed:
                record=json.loads((Path(dest).parent/'intent.json').read_text())
                self.assertEqual(str(target),record['target']); observed.append(True)
                target.unlink(); target.symlink_to(foreign)
            return rename(source,dest)
        with mock.patch.object(STORAGE.os,'rename',side_effect=race), self.assertRaises(STORAGE.StorageInstallError):self.install()
        self.assertEqual('untouched',foreign.read_text())
        self.assertTrue(any(p.is_symlink() and p.readlink()==foreign for p in (self.homes[0][1]/'backups').rglob('displaced')))


class CapsuleDurabilityTests(Fixture, unittest.TestCase):
    def test_every_ancestor_synced_before_target_capture(self):
        sync=STORAGE.fsync_directory; rename=STORAGE.os.rename; seen=[]; captures=[]
        target=self.homes[0][1]/'skills/example/helper.py'; home=self.homes[0][1]
        def traced_sync(path, *args, **kwargs):
            seen.append(Path(path));return sync(path, *args, **kwargs)
        def checked_rename(source,dest):
            if same_target(source,target):
                capsule=Path(dest).parent.resolve()
                chain=[]; current=capsule
                while True:
                    chain.append(current)
                    if current==home:break
                    current=current.parent
                positions=[max(i for i,observed in enumerate(seen) if observed==p) for p in chain]
                self.assertEqual(sorted(positions),positions);captures.append(True)
                self.assertTrue((capsule/'intent.json').is_file())
            return rename(source,dest)
        with mock.patch.object(STORAGE,'fsync_directory',side_effect=traced_sync),mock.patch.object(STORAGE.os,'rename',side_effect=checked_rename):self.install()
        self.assertTrue(captures)

    def test_ancestor_sync_failure_prevents_publication_and_withdrawal_capture(self):
        sync=STORAGE.fsync_directory; rename=STORAGE.os.rename; captures=[]
        first=self.homes[0][1]/'skills/example/helper.py'
        def refuse(path, *args, **kwargs):
            if Path(path).name=='agent-graphs':raise OSError('ancestor sync failed')
            return sync(path, *args, **kwargs)
        def record(source,dest):
            if same_target(source,first):captures.append(True)
            return rename(source,dest)
        with mock.patch.object(STORAGE,'fsync_directory',side_effect=refuse),mock.patch.object(STORAGE.os,'rename',side_effect=record),self.assertRaises(OSError):self.install()
        self.assertFalse(captures);self.assertEqual(self.before,{p:p.read_bytes() for p in self.before})
        home=self.homes[0][1];backup=home/'backups/agent-graphs/new-withdrawal/storage-only'
        with contextlib.ExitStack() as stack:
            io=STORAGE.BoundIO([(label,h,[]) for label,h in self.homes],stack)
            io.directory(first.parent)
            with mock.patch.object(STORAGE,'fsync_directory',side_effect=refuse),self.assertRaises(OSError):
                STORAGE.withdraw_file(first,b'old helper\n',backup,0o755,home,io)
        self.assertEqual(b'old helper\n',first.read_bytes())


class ParentIdentityTests(Fixture, unittest.TestCase):
    def run_parent_race(self, when):
        target=self.homes[0][1]/'skills/example/helper.py'; original_parent=target.parent
        preserved=original_parent.with_name('example-preserved')
        foreign=self.root/'foreign-package';foreign.mkdir()
        (foreign/'helper.py').write_bytes(b'old helper\n');(foreign/'helper.py').chmod(0o755)
        (foreign/'foreign.txt').write_text('foreign sentinel')
        foreign_before={p.name:p.read_bytes() for p in foreign.iterdir()}
        rename=STORAGE.os.rename;link=STORAGE.os.link;publish=STORAGE.capture_publish
        switched=[];rolling=[False]
        def substitute():
            rename(original_parent,preserved)
            original_parent.symlink_to(foreign,target_is_directory=True)
            switched.append(True)
        def capture(source,dest):
            if not switched and same_target(source,target) and when in {'capture','rollback'} and (when!='rollback' or rolling[0]):substitute()
            return rename(source,dest)
        def publication(source,dest):
            if not switched and same_target(dest,target) and Path(source).name=='prepared' and when=='publication':substitute()
            return link(source,dest)
        def fail_second(path,payload,*args):
            if when=='rollback' and path==self.homes[1][1]/'skills/example/helper.py':
                rolling[0]=True;raise OSError('second home failed')
            return publish(path,payload,*args)
        with mock.patch.object(STORAGE.os,'rename',side_effect=capture),mock.patch.object(STORAGE.os,'link',side_effect=publication),mock.patch.object(STORAGE,'capture_publish',side_effect=fail_second),self.assertRaises((OSError,STORAGE.StorageInstallError)):
            self.install()
        self.assertTrue(switched)
        self.assertEqual(foreign_before,{p.name:p.read_bytes() for p in foreign.iterdir()})
        self.assertEqual(b'old helper\n',(preserved/'helper.py').read_bytes())
        self.assertTrue(original_parent.is_symlink())
    def test_capture_does_not_follow_substituted_parent(self):self.run_parent_race('capture')
    def test_publication_does_not_follow_substituted_parent(self):self.run_parent_race('publication')
    def test_rollback_does_not_follow_substituted_parent(self):self.run_parent_race('rollback')
