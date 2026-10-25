from __future__ import annotations

import contextlib
import hashlib
import json
import os
import stat
import uuid
from pathlib import Path


class StorageInstallError(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(home, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise StorageInstallError(f'Unsafe relative target: {relative}')
    path = home / relative
    for parent in [home, *path.relative_to(home).parents]:
        current = parent if parent == home else home / parent
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise StorageInstallError(f'Linked/non-directory target parent: {current}')
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise StorageInstallError(f'Linked/non-file target: {path}')
    if path.exists() and path.stat().st_nlink != 1:
        raise StorageInstallError(f'Hard-linked target: {path}')
    return path


def snapshot(path):
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    except FileNotFoundError:
        return None
    except OSError as error:
        raise StorageInstallError(f'Unsafe or unreadable file: {path}: {error}') from error
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise StorageInstallError(f'Unsafe file: {path}')
        return handle.read()


def rendered_overlay(raw, entry):
    if digest(raw) == entry['after_sha256']:
        return raw
    if digest(raw) != entry['before_sha256']:
        raise StorageInstallError(f'Unknown overlay drift: {entry["target"]}')
    text = raw.decode('utf-8')
    for old, new in entry['edits']:
        if text.count(old) != 1:
            raise StorageInstallError(f'Ambiguous overlay edit: {entry["target"]}')
        text = text.replace(old, new)
    result = text.encode('utf-8')
    if digest(result) != entry['after_sha256']:
        raise StorageInstallError(f'Invalid overlay postimage: {entry["target"]}')
    return result


def source_inputs(root):
    paths = ['policies/storage-files.json', 'policies/storage-overlays/manifest.json',
             'policies/orchestration.md']
    spec = json.loads((root / paths[0]).read_bytes())
    paths += [entry['source'] for entry in spec['files']]
    inputs = {name: snapshot(root / name) for name in paths}
    for entry in spec['files']:
        raw = inputs[entry['source']]
        if raw is None or digest(raw) != entry['after_sha256']:
            raise StorageInstallError(f'Unreviewed source bytes: {entry["source"]}')
    if digest(inputs['policies/orchestration.md']) != spec['policy_after_sha256']:
        raise StorageInstallError('Unreviewed orchestration source')
    return inputs


def build_plans(homes, root, api):
    inputs = source_inputs(root)
    specs = json.loads(inputs['policies/storage-files.json'])['files']
    overlays = json.loads(inputs['policies/storage-overlays/manifest.json'])['overlays']
    plans = []
    seen = set()
    for label, original in homes:
        home = Path(os.path.abspath(original))
        if home.resolve() != home or not home.is_dir():
            raise StorageInstallError(f'Home must be an existing unaliased directory: {home}')
        info = home.stat()
        identity = (info.st_dev, info.st_ino)
        if identity in seen:
            raise StorageInstallError(f'Aliased homes are not independent: {home}')
        seen.add(identity)
        for directory in ('skills', 'backups', 'backups/agent-graphs'):
            path = home / directory
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                raise StorageInstallError(f'Unsafe installer directory: {path}')
        items = []
        for entry in specs:
            target = safe_path(home, entry['target'])
            skill = home / 'skills' / Path(entry['target']).parts[1]
            if not skill.is_dir():
                continue
            before = snapshot(target)
            after = inputs[entry['source']]
            if after is None:
                raise StorageInstallError(f'Missing source: {entry["source"]}')
            current = digest(before) if before is not None else None
            if before != after and current not in entry['before_sha256']:
                raise StorageInstallError(f'Unknown file drift: {target}')
            items.append({'path': target, 'before': before, 'after': after,
                          'before_mode': target.stat().st_mode & 0o777 if before is not None else None})
        for entry in overlays:
            target = safe_path(home, entry['target'])
            if not target.exists():
                continue
            before = snapshot(target)
            items.append({'path': target, 'before': before, 'after': rendered_overlay(before, entry),
                          'before_mode': target.stat().st_mode & 0o777})
        agents = safe_path(home, 'AGENTS.md')
        before = snapshot(agents)
        if before is None:
            raise StorageInstallError(f'Missing global policy owner: {agents}')
        text = before.decode('utf-8')
        pattern = api.ORCHESTRATION_POLICY_MANAGED_RE
        matches = list(pattern.finditer(text))
        if len(matches) != 1 or text.count(api.ORCHESTRATION_POLICY_BLOCK_START) != 1 or text.count(api.ORCHESTRATION_POLICY_BLOCK_END) != 1:
            raise StorageInstallError(f'Expected one existing orchestration block: {agents}')
        match = matches[0]
        old_block = match.group()
        new_block = api.policy_block(root / 'policies/orchestration.md',
                                     api.ORCHESTRATION_POLICY_BLOCK_START,
                                     api.ORCHESTRATION_POLICY_BLOCK_END)
        allowed = json.loads(inputs['policies/storage-files.json'])['policy_before_sha256']
        if old_block != new_block and digest(old_block.encode()) not in allowed:
            raise StorageInstallError(f'Unknown orchestration policy drift: {agents}')
        after = (text[:match.start()] + new_block + text[match.end():]).encode()
        items.append({'path': agents, 'before': before, 'after': after,
                      'before_mode': agents.stat().st_mode & 0o777})
        if len({item['path'] for item in items}) != len(items):
            raise StorageInstallError('Duplicate storage targets')
        plans.append((label, home, items))
    return inputs, plans


class BoundDirectory:
    def __init__(self, path, base=None, create=False):
        if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW') or not Path('/proc/self/fd').is_dir():
            raise StorageInstallError('Storage publication requires verified POSIX directory descriptors')
        self.path = path
        self.owned = []
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        if base is None:
            first = os.open('/', flags)
            self.owned.append(first)
            self.labels = [Path('/')]
            self.fds = [first]
            parts = path.parts[1:]
        else:
            base.verify()
            self.labels = list(base.labels)
            self.fds = list(base.fds)
            parts = path.relative_to(base.path).parts
        try:
            for part in parts:
                if create:
                    try:
                        os.mkdir(part, 0o700, dir_fd=self.fds[-1])
                    except FileExistsError:
                        pass
                fd = os.open(part, flags, dir_fd=self.fds[-1])
                self.owned.append(fd)
                self.fds.append(fd)
                self.labels.append(self.labels[-1] / part)
            self.verify()
        except BaseException:
            self.close()
            raise

    @property
    def anchor(self):
        return Path('/proc/self/fd') / str(self.fds[-1])

    def file(self, name):
        if Path(name).name != name or name in {'.', '..'}:
            raise StorageInstallError('Unsafe anchored filename')
        return self.anchor / name

    def verify(self):
        for index in range(1, len(self.fds)):
            actual = os.stat(self.labels[index].name, dir_fd=self.fds[index - 1], follow_symlinks=False)
            opened = os.fstat(self.fds[index])
            if not stat.S_ISDIR(actual.st_mode) or (actual.st_dev, actual.st_ino) != (opened.st_dev, opened.st_ino):
                raise StorageInstallError(f'Directory identity changed: {self.labels[index]}')

    def sync_to(self, home):
        for label, fd in reversed(list(zip(self.labels, self.fds))):
            fsync_directory(label, fd=fd)
            if label == home:
                return
        raise StorageInstallError('Recovery capsule escapes its established home')

    def close(self):
        for fd in reversed(self.owned):
            os.close(fd)
        self.owned.clear()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


class BoundIO:
    def __init__(self, homes, stack):
        self.stack = stack
        self.homes = {}
        self.directories = {}
        for _, home, _ in homes:
            bound = stack.enter_context(BoundDirectory(home))
            self.homes[home] = bound
            self.directories[home] = bound

    def directory(self, path, create=False, verify=True):
        if path not in self.directories:
            if not verify:
                raise StorageInstallError('Unregistered directory cannot be used for rollback')
            home = next((h for h in self.homes if path.is_relative_to(h)), None)
            if home is None:
                raise StorageInstallError(f'Directory outside selected homes: {path}')
            base_path = max((p for p in self.directories if path.is_relative_to(p)), key=lambda p: len(p.parts))
            self.directories[path] = self.stack.enter_context(BoundDirectory(path, self.directories[base_path], create))
        bound = self.directories[path]
        if verify:
            bound.verify()
        return bound

    def target(self, path, verify=True):
        return self.directory(path.parent, verify=verify).file(path.name)

    def capsule(self, backup):
        parent = self.directory(backup, create=True)
        name = 'publication-' + uuid.uuid4().hex
        os.mkdir(name, 0o700, dir_fd=parent.fds[-1])
        return self.directory(backup / name)

    def verify(self):
        for bound in self.directories.values():
            bound.verify()


def fsync_directory(path, fd=None):
    if fd is not None:
        os.fsync(fd)
        return
    opened = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(opened)
    finally:
        os.close(opened)


def write_new(path, raw, mode=0o600):
    with path.open('xb') as handle:
        os.fchmod(handle.fileno(), mode)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def journal(capsule, phase, data, home):
    write_new(capsule.file(phase + '.json'), (json.dumps(data, sort_keys=True) + '\n').encode())
    capsule.sync_to(home)


def capability_check(home, items, io):
    pending = [item for item in items if item['before'] != item['after']]
    if not pending:
        return
    parent = io.directory(home / 'backups/agent-graphs', create=True)
    name = '.storage-capability-' + uuid.uuid4().hex
    os.mkdir(name, 0o700, dir_fd=parent.fds[-1])
    with BoundDirectory(parent.path / name, io.homes[home]) as probe:
        first = probe.file('first'); linked = probe.file('linked'); moved = probe.file('moved')
        try:
            write_new(first, b'capability probe')
            os.link(first, linked)
            try:
                os.link(first, linked)
            except FileExistsError:
                pass
            else:
                raise StorageInstallError('Filesystem did not refuse existing publication target')
            os.rename(linked, moved)
            first.unlink()
            if snapshot(moved) != b'capability probe':
                raise StorageInstallError('Filesystem publication readback failed')
            probe.sync_to(home)
            for item in pending:
                target_parent = io.directory(item['path'].parent)
                if os.fstat(target_parent.fds[-1]).st_dev != os.fstat(probe.fds[-1]).st_dev:
                    raise StorageInstallError('Target and recovery capsule must share a filesystem')
        finally:
            for file in (first, linked, moved):
                try:
                    file.unlink()
                except FileNotFoundError:
                    pass
    os.rmdir(name, dir_fd=parent.fds[-1])


def restore_captured(path, captured, capsule, failure, home, parent):
    try:
        raw = snapshot(captured)
        if raw is None:
            return
        mode = captured.stat().st_mode & 0o777
        stage = capsule.file('restoration')
        write_new(stage, raw, mode)
        os.link(stage, path)
        stage.unlink()
        parent.sync_to(home)
        if snapshot(path) != raw or snapshot(captured) != raw:
            raise StorageInstallError('Restored copy or retained inode changed during restoration')
        journal(capsule, 'restored', {'target': str(parent.path / path.name), 'captured': str(capsule.path / 'displaced'), 'sha256': digest(raw)}, home)
    except BaseException as error:
        failure.add_note(f'Recovery conflict; preserve target and complete capsule {capsule.path}: {error}')


def capture_publish(path, payload, expected, backup, mode, expected_mode, home, io, allow_moved_parent=False):
    logical = path
    parent = io.directory(path.parent, verify=not allow_moved_parent)
    path = parent.file(path.name)
    capsule = io.capsule(backup)
    stage = capsule.file('prepared'); captured = capsule.file('displaced')
    record = {'target': str(logical), 'stage': str(capsule.path / 'prepared'),
              'captured': str(capsule.path / 'displaced'),
              'parent_identity': list((os.fstat(parent.fds[-1]).st_dev, os.fstat(parent.fds[-1]).st_ino)),
              'expected_sha256': digest(expected) if expected is not None else None,
              'desired_sha256': digest(payload), 'expected_mode': expected_mode}
    moved = False
    published = False
    try:
        write_new(stage, payload, mode)
        journal(capsule, 'intent', record, home)
        if expected is not None:
            os.rename(path, captured)
            moved = True
            parent.sync_to(home)
            capsule.sync_to(home)
            if snapshot(captured) != expected or captured.stat().st_mode & 0o777 != expected_mode:
                raise StorageInstallError(f'Concurrent edit captured and retained: {captured}')
            if not allow_moved_parent:
                parent.verify()
            journal(capsule, 'captured', record, home)
        os.link(stage, path)
        published = True
        stage.unlink()
        parent.sync_to(home)
        if snapshot(path) != payload:
            raise StorageInstallError(f'Publication readback changed: {path}')
        if moved and snapshot(captured) != expected:
            raise StorageInstallError(f'Retained captured inode changed: {captured}')
        if not allow_moved_parent:
            parent.verify()
        record['published_mode'] = path.stat().st_mode & 0o777
        journal(capsule, 'published', record, home)
        record['_capsule'] = capsule
        return record if moved else None
    except BaseException as failure:
        failure.add_note(f'Publication recovery capsule: {capsule.path}; current directory: {os.readlink(capsule.anchor)}')
        if moved and not published:
            restore_captured(path, captured, capsule, failure, home, parent)
        raise


def withdraw_file(path, expected, backup, expected_mode, home, io):
    logical = path
    parent = io.directory(path.parent, verify=False)
    path = parent.file(path.name)
    capsule = io.capsule(backup)
    captured = capsule.file('displaced')
    journal(capsule, 'intent', {'target': str(logical), 'captured': str(capsule.path / 'displaced'),
                              'expected_sha256': digest(expected), 'expected_mode': expected_mode}, home)
    moved = False
    try:
        os.rename(path, captured)
        moved = True
        parent.sync_to(home)
        capsule.sync_to(home)
        if snapshot(captured) != expected or captured.stat().st_mode & 0o777 != expected_mode:
            raise StorageInstallError(f'Concurrent rollback edit retained: {captured}')
        journal(capsule, 'withdrawn', {'target': str(logical), 'captured': str(capsule.path / 'displaced')}, home)
    except BaseException as failure:
        failure.add_note(f'Withdrawal recovery capsule: {capsule.path}; current directory: {os.readlink(capsule.anchor)}')
        if moved:
            restore_captured(path, captured, capsule, failure, home, parent)
        raise


def apply_plans(plans, inputs, root, api):
    changed = []
    backups = []
    captured_records = []
    def recheck_sources():
        if source_inputs(root) != inputs:
            raise StorageInstallError('Source changed during storage installation')
    def recheck(item):
        anchored = io.target(item['path'])
        if snapshot(anchored) != item['before']:
            raise StorageInstallError(f'Concurrent edit before publication: {item["path"]}')
        if item['before'] is not None and anchored.stat().st_mode & 0o777 != item['before_mode']:
            raise StorageInstallError(f'Concurrent mode edit: {item["path"]}')
    with contextlib.ExitStack() as stack:
        io = BoundIO(plans, stack)
        for _, home, _ in sorted(plans, key=lambda p: str(p[1])):
            stack.enter_context(api.skills_install_lock(io.directory(home).anchor))
        try:
            recheck_sources()
            for _, home, items in plans:
                for item in items:
                    item['home'] = home
                    recheck(item)
                capability_check(home, items, io)
            for _, home, items in plans:
                pending = [item for item in items if item['before'] != item['after']]
                if not pending:
                    continue
                backup = api.backup_root(home) / 'storage-only'
                for item in pending:
                    recheck_sources()
                    recheck(item)
                    item['backup'] = backup
                    item['mode'] = item['before_mode'] if item['before_mode'] is not None else 0o644
                    changed.append(item)
                    record = capture_publish(item['path'], item['after'], item['before'], backup,
                                             item['mode'], item['before_mode'], home, io)
                    item['after_mode'] = io.target(item['path']).stat().st_mode & 0o777
                    if record is not None:
                        captured_records.append(record)
                        backups.append(record['captured'])
            recheck_sources()
            io.verify()
            for record in captured_records:
                retained = snapshot(record['_capsule'].file('displaced'))
                if retained is None or digest(retained) != record['expected_sha256']:
                    raise StorageInstallError(f'Retained captured inode changed: {record["captured"]}')
            for _, _, items in plans:
                for item in items:
                    if snapshot(io.target(item['path'])) != item['after']:
                        raise StorageInstallError(f'Concurrent edit after publication: {item["path"]}')
        except BaseException as failure:
            for item in reversed(changed):
                try:
                    parent = io.directory(item['path'].parent, verify=False)
                    try:
                        parent.verify()
                    except StorageInstallError as identity_error:
                        failure.add_note(f'Rollback retains original directory {os.readlink(parent.anchor)}: {identity_error}')
                    anchored = parent.file(item['path'].name)
                    current = snapshot(anchored)
                    if current == item['before']:
                        continue
                    if current != item['after']:
                        failure.add_note(f'Rollback preserved concurrent edit: {item["path"]}')
                        continue
                    actual_mode = item.get('after_mode', anchored.stat().st_mode & 0o777)
                    if item['before'] is None:
                        withdraw_file(item['path'], item['after'], item['backup'], actual_mode, item['home'], io)
                    else:
                        capture_publish(item['path'], item['before'], item['after'], item['backup'],
                                        item['mode'], actual_mode, item['home'], io, True)
                    if snapshot(io.target(item['path'], verify=False)) != item['before']:
                        failure.add_note(f'Rollback readback differs: {item["path"]}')
                except BaseException as rollback_error:
                    failure.add_note(f'Rollback retained {item["path"]}: {rollback_error}')
                    for note in getattr(rollback_error, '__notes__', []):
                        failure.add_note(note)
            raise
    return backups

def run(action, homes, *, root, api):
    inputs, plans = build_plans(homes, root, api)
    backups = apply_plans(plans, inputs, root, api) if action == 'install' else []
    items = []
    for label, _, files in plans:
        for item in files:
            synced = item['before'] == item['after']
            items.append({'environment': label, 'path': str(item['path']),
                          'status': 'in-sync' if synced else ('installed' if action == 'install' else 'update'),
                          'before_sha256': digest(item['before']) if item['before'] is not None else None,
                          'after_sha256': digest(item['after'])})
    failed = action == 'verify' and any(item['status'] != 'in-sync' for item in items)
    return {'status': 'failed' if failed else 'ok', 'scope': 'storage-only',
            'items': items, 'backups': backups}
