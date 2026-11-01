from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import uuid
from pathlib import Path

from portable_bundle import KitError, bundle_id, verify_bundle


MANAGED_NAMES = ('skills', 'agents', 'agent-graph-runtime', 'AGENTS.md', 'config.toml', 'knowledge')
REQUIRED_NAMES = set(MANAGED_NAMES) - {'knowledge'}
MAX_RELEASES = 3
MAX_BYTES = 1024 * 1024 * 1024
RELEASE_ID = re.compile(r'^[0-9a-f]{64}$')


def _json(path: Path) -> dict:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 32 * 1024 * 1024:
                raise KitError(f'Unsafe metadata: {path.name}')
            value = json.load(stream)
    except (OSError, ValueError) as exc:
        raise KitError(f'Missing or invalid metadata: {path.name}') from exc
    if not isinstance(value, dict):
        raise KitError(f'Invalid metadata: {path.name}')
    return value


def _write_json(path: Path, value: dict, exclusive: bool = False) -> None:
    data = (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
    flags |= os.O_EXCL if exclusive else os.O_TRUNC
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _atomic_json(path: Path, value: dict) -> None:
    scratch = path.with_name('.write-' + uuid.uuid4().hex)
    identity = None
    try:
        _write_json(scratch, value, exclusive=True)
        info = scratch.lstat()
        identity = (info.st_dev, info.st_ino)
        os.replace(scratch, path)
    finally:
        if identity is not None and (scratch.exists() or scratch.is_symlink()):
            info = scratch.lstat()
            if (info.st_dev, info.st_ino) == identity and not scratch.is_symlink() and _json(scratch) == value:
                scratch.unlink()


def _scan(root: Path | int, normalize_modes: bool = False) -> dict:
    result = {}

    def visit(directory: int, prefix: str) -> None:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            relative = prefix + entry.name
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                try:
                    opened = os.fstat(child)
                    if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                        raise KitError('Managed directory changed during verification')
                    visit(child, relative + '/')
                    final = os.stat(entry.name, dir_fd=directory, follow_symlinks=False)
                    if (final.st_dev, final.st_ino) != (info.st_dev, info.st_ino):
                        raise KitError('Managed directory changed during verification')
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise KitError(f'Hard link in managed payload: {relative}')
                fd = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                with os.fdopen(fd, 'rb') as stream:
                    opened = os.fstat(stream.fileno())
                    if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                        raise KitError('Managed file changed during verification')
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                    final = os.fstat(stream.fileno())
                    if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (final.st_size, final.st_mtime_ns, final.st_ctime_ns):
                        raise KitError('Managed file changed during verification')
                result[relative] = {
                    'sha256': digest, 'bytes': opened.st_size,
                    'mode': (0o755 if opened.st_mode & 0o111 else 0o644) if normalize_modes else stat.S_IMODE(opened.st_mode),
                }
            else:
                raise KitError(f'Symlink or special file in managed payload: {relative}')

    try:
        fd = os.dup(root) if isinstance(root, int) else os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            visit(fd, '')
        finally:
            os.close(fd)
    except OSError as exc:
        raise KitError('Unsafe or changing managed payload') from exc
    return result


def _copy_payload(source: Path, destination: Path) -> None:
    def copy(directory: int, output: int) -> None:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                try:
                    os.mkdir(entry.name, 0o755, dir_fd=output)
                    created = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=output)
                    try:
                        copy(child, created)
                    finally:
                        os.close(created)
                finally:
                    os.close(child)
            elif stat.S_ISREG(info.st_mode):
                fd = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                with os.fdopen(fd, 'rb') as incoming:
                    if not stat.S_ISREG(os.fstat(incoming.fileno()).st_mode):
                        raise KitError('Source file changed during staging')
                    created = os.open(entry.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=output)
                    with os.fdopen(created, 'wb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                        os.fchmod(outgoing.fileno(), 0o755 if info.st_mode & 0o111 else 0o644)
            else:
                raise KitError('Symlink or special file encountered during staging')

    source_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        output_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            copy(source_fd, output_fd)
        finally:
            os.close(output_fd)
    finally:
        os.close(source_fd)


def _payload(root: Path, lock: dict, normalize_modes: bool = False) -> None:
    names = {path.name for path in root.iterdir()}
    if not REQUIRED_NAMES <= names or not names <= set(MANAGED_NAMES):
        raise KitError('Payload has missing or unexpected managed roots')
    for name in ('skills', 'agents', 'agent-graph-runtime'):
        if (root / name).is_symlink() or not (root / name).is_dir():
            raise KitError(f'Payload root must be a directory: {name}')
    for name in ('AGENTS.md', 'config.toml'):
        if (root / name).is_symlink() or not (root / name).is_file():
            raise KitError(f'Payload root must be a file: {name}')
    if 'knowledge' in names and ((root / 'knowledge').is_symlink() or not (root / 'knowledge').is_dir()):
        raise KitError('Payload knowledge must be a directory')
    if _scan(root, normalize_modes=normalize_modes) != lock.get('files'):
        raise KitError('Managed payload drift or incomplete release')
    _tree(root, lock)
    skills = root / 'skills'
    if {path.name for path in skills.iterdir()} != _skills(lock):
        raise KitError('Unexpected skill roots in managed payload')


def _skills(lock: dict) -> set[str]:
    names = set()
    for name in lock['files']:
        parts = name.split('/')
        if parts[0] == 'skills':
            if len(parts) < 3 or parts[1].startswith('.'):
                raise KitError('Managed skills must be named top-level directories')
            names.add(parts[1])
    return names


def _owned_skills(releases: dict) -> set[str]:
    return set().union(*(_skills(lock) for lock in releases.values())) if releases else set()


def _tree(root: Path, lock: dict) -> dict:
    allowed = set(MANAGED_NAMES) - {'AGENTS.md', 'config.toml'}
    for name in lock['files']:
        allowed.update(parent.as_posix() for parent in Path(name).parents if parent != Path('.'))
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                if relative not in allowed:
                    raise KitError(f'Unowned directory in managed payload: {relative}')
            elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or relative not in lock['files']:
                raise KitError(f'Unowned entry in managed payload: {relative}')
            result[relative] = (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode))
    return result


def _target(target: Path) -> Path:
    path = Path(os.path.abspath(target))
    known = [Path.home() / '.codex']
    if os.environ.get('CODEX_HOME'):
        known.append(Path(os.path.abspath(os.environ['CODEX_HOME'])))
    if os.environ.get('USERPROFILE'):
        known.append(Path(os.path.abspath(os.environ['USERPROFILE'])) / '.codex')
    if path in known:
        raise KitError('Refusing an active or default global CODEX_HOME')
    return path


class _Home:
    def __init__(self, target: Path, create: bool = False):
        self.target = _target(target)
        self.descriptors = []
        self.identities = []
        self.created = False
        if os.name != 'posix' or not Path('/proc/self/fd').is_dir():
            raise KitError('Portable installation requires Linux/WSL directory descriptors and symlinks')
        try:
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
            self.descriptors.append(fd)
            parts = self.target.parts[1:]
            for index, part in enumerate(parts):
                parent = fd
                try:
                    fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                except FileNotFoundError:
                    if not create or index != len(parts) - 1:
                        raise KitError('Target parent must exist; target may be absent')
                    os.mkdir(part, 0o700, dir_fd=parent)
                    self.created = True
                    fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                self.descriptors.append(fd)
                info = os.fstat(fd)
                self.identities.append((parent, part, info.st_dev, info.st_ino))
            self.path = Path(f'/proc/self/fd/{fd}')
            if not parts:
                raise KitError('Filesystem root cannot be an installation target')
            self.check()
        except (OSError, KitError) as exc:
            self.close()
            if isinstance(exc, KitError):
                raise
            raise KitError(f'Unsafe target or parent: {self.target}') from exc

    def anchor(self, name: str, parent: Path | None = None) -> Path:
        parent = self.path if parent is None else parent
        descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        self.descriptors.append(descriptor)
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
        self.descriptors.append(fd)
        info = os.fstat(fd)
        self.identities.append((descriptor, name, info.st_dev, info.st_ino))
        return Path(f'/proc/self/fd/{fd}')

    def check(self) -> None:
        for parent, name, device, inode in self.identities:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != (device, inode):
                raise KitError('Target parent changed during operation')

    def close(self) -> None:
        for fd in reversed(self.descriptors):
            os.close(fd)
        self.descriptors.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _owner(home: _Home) -> dict:
    return {'schema_version': 1, 'kind': 'codex-portable-kit', 'target': str(home.target)}


class _Store:
    def __init__(self, home: _Home):
        self.root = home.anchor('.portable-kit')
        self.releases = home.anchor('releases', self.root)
        self.manifests = home.anchor('manifests', self.root)

    def __truediv__(self, name: str) -> Path:
        if name == 'releases':
            return self.releases
        if name == 'manifests':
            return self.manifests
        return self.root / name

    def iterdir(self):
        return self.root.iterdir()


def _kit(home: _Home) -> _Store:
    try:
        kit = _Store(home)
    except OSError as exc:
        raise KitError('Target is not an owned portable home or has unsafe directories') from exc
    if _json(kit / 'owner.json') != _owner(home):
        raise KitError('Portable home ownership mismatch')
    return kit


def _initialize(home: _Home) -> None:
    if list(home.path.iterdir()):
        raise KitError('Refusing existing unowned target contents')
    kit = home.path / '.portable-kit'
    kit.mkdir(mode=0o700)
    (kit / 'releases').mkdir(mode=0o700)
    (kit / 'manifests').mkdir(mode=0o700)
    _write_json(kit / 'owner.json', _owner(home), exclusive=True)
    _write_json(kit / 'state.json', {'schema_version': 1, 'current': None, 'previous': None}, exclusive=True)
    (home.path / 'skills').mkdir(mode=0o755)


@contextlib.contextmanager
def _locked(target: Path, initialize: bool = False):
    with _Home(target, create=initialize) as home:
        if not (home.path / '.portable-kit').exists():
            if not initialize:
                raise KitError('Target is not an owned portable home')
            _initialize(home)
        kit = _kit(home)
        lock_path = kit / 'operation.lock'
        try:
            fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError as exc:
            raise KitError('Portable home operation lock is held; never steal an uncertain lock') from exc
        try:
            info = os.fstat(fd)
            with os.fdopen(fd, 'w') as stream:
                stream.write(json.dumps({'pid': os.getpid(), 'nonce': uuid.uuid4().hex}) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            yield home, kit
        finally:
            if lock_path.exists() and not lock_path.is_symlink():
                current = lock_path.lstat()
                if (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino):
                    lock_path.unlink()


def _manifest(kit: _Store, release: str) -> dict:
    if not isinstance(release, str) or not RELEASE_ID.fullmatch(release):
        raise KitError('Invalid release ID')
    lock = _json(kit / 'manifests' / (release + '.json'))
    if lock.get('schema_version') != 1 or lock.get('id') != release or bundle_id(lock) != release:
        raise KitError('Installed release manifest identity mismatch')
    _payload(kit / 'releases' / release, lock)
    return lock


def _validate(home: _Home, kit: _Store, stage: str | None = None, pending: str | None = None, transaction: dict | None = None) -> tuple[dict, dict]:
    home.check()
    if _json(kit / 'owner.json') != _owner(home):
        raise KitError('Portable home ownership mismatch')
    allowed = {'owner.json', 'state.json', 'releases', 'manifests', 'current', 'operation.lock'}
    if stage is not None:
        allowed.add(stage)
    if transaction is not None:
        allowed.add('transaction.json')
        if _json(kit / 'transaction.json') != transaction:
            raise KitError('Transaction intent changed during operation')
    unknown = {p.name for p in kit.iterdir()} - allowed
    if unknown:
        raise KitError('Interrupted or unknown portable state: ' + ', '.join(sorted(unknown)))
    state = _json(kit / 'state.json')
    if set(state) != {'schema_version', 'current', 'previous'} or state['schema_version'] != 1:
        raise KitError('Invalid activation state')
    current, previous = state['current'], state['previous']
    for value in (current, previous):
        if value is not None and (not isinstance(value, str) or not RELEASE_ID.fullmatch(value)):
            raise KitError('Invalid activation release ID')
    releases = {}
    for path in (kit / 'releases').iterdir():
        releases[path.name] = _manifest(kit, path.name)
    if {p.name for p in (kit / 'manifests').iterdir()} != {release + '.json' for release in releases}:
        raise KitError('Unowned or partial release metadata')
    if len(releases) > MAX_RELEASES or sum(sum(f['bytes'] for f in m['files'].values()) for m in releases.values()) > MAX_BYTES:
        raise KitError('Portable retention limit exceeded')
    pointer = kit / 'current'
    try:
        skills = home.anchor('skills')
    except OSError as exc:
        raise KitError('Stable skills root must be a real directory') from exc
    owned = _owned_skills(releases)
    missing = _skills(releases[pending]) - _owned_skills({key: value for key, value in releases.items() if key != pending}) if pending in releases else set()
    for name in owned:
        link = skills / name
        if name in missing and not link.exists() and not link.is_symlink():
            continue
        if not link.is_symlink() or os.readlink(link) != f'../.portable-kit/current/skills/{name}':
            raise KitError(f'Managed skill link drift: {name}')
    if current is None:
        if pointer.exists() or pointer.is_symlink() or set(releases) - ({pending} if pending else set()) or previous is not None:
            raise KitError('Incomplete initial activation')
        if any((home.path / name).exists() or (home.path / name).is_symlink() for name in MANAGED_NAMES if name != 'skills'):
            raise KitError('Unowned managed target entries')
    else:
        if current not in releases or (previous is not None and previous not in releases):
            raise KitError('Activation references missing release')
        if not pointer.is_symlink() or os.readlink(pointer) != f'releases/{current}':
            raise KitError('Current release pointer drift')
        for name in MANAGED_NAMES:
            if name == 'skills':
                continue
            link = home.path / name
            if not link.is_symlink() or os.readlink(link) != f'.portable-kit/current/{name}':
                raise KitError(f'Managed target link drift: {name}')
    home.check()
    return state, releases


def _bundle(bundle: Path, target: Path) -> tuple[Path, dict]:
    bundle = Path(bundle).absolute()
    target = _target(target)
    source = bundle.resolve()
    destination = target.resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise KitError('Bundle and target paths overlap')
    lock = verify_bundle(bundle)
    _payload(bundle / 'payload', lock, normalize_modes=True)
    return bundle, lock


def _result(home: _Home, state: dict, status: str = 'ok') -> dict:
    return {'status': status, 'target': str(home.target), 'release_id': state['current'], 'previous_release_id': state['previous'], 'CODEX_HOME': str(home.target)}


def plan(bundle: Path, target: Path) -> dict:
    bundle, lock = _bundle(bundle, target)
    path = Path(os.path.abspath(target))
    if not path.exists() and not path.is_symlink():
        with _Home(path.parent) as parent:
            parent.check()
        return {'status': 'ready', 'target': str(path), 'release_id': lock['id'], 'action': 'install'}
    with _Home(path) as home:
        if not list(home.path.iterdir()):
            return {'status': 'ready', 'target': str(path), 'release_id': lock['id'], 'action': 'install'}
    with _locked(path) as (home, kit):
        state, releases = _validate(home, kit)
        _admit(lock, releases)
        _incoming_skills(home, releases, lock)
        return {'status': 'ready', 'target': str(path), 'release_id': lock['id'], 'action': 'unchanged' if state['current'] == lock['id'] else 'update'}


def _incoming_skills(home: _Home, releases: dict, lock: dict) -> set[str]:
    names = _skills(lock) - _owned_skills(releases)
    skills = home.anchor('skills')
    for name in names:
        entry = skills / name
        if entry.exists() or entry.is_symlink():
            raise KitError(f'Foreign skill name collision: {name}')
    return names


def _admit(lock: dict, releases: dict) -> None:
    if lock['id'] in releases:
        if releases[lock['id']] != lock:
            raise KitError('Existing release metadata differs from bundle')
        return
    total = sum(sum(f['bytes'] for f in m['files'].values()) for m in releases.values())
    incoming = sum(f['bytes'] for f in lock['files'].values())
    if len(releases) >= MAX_RELEASES or total + incoming > MAX_BYTES:
        raise KitError('Portable retention admission limit reached; reconcile retained releases explicitly')


def _switch(kit: _Store, release: str) -> None:
    pointer = kit / ('.pointer-' + uuid.uuid4().hex)
    identity = None
    try:
        pointer.symlink_to(f'releases/{release}', target_is_directory=True)
        info = pointer.lstat()
        identity = (info.st_dev, info.st_ino)
        os.replace(pointer, kit / 'current')
    except (OSError, NotImplementedError) as exc:
        raise KitError('Atomic symlink activation failed; Linux/WSL symlink support is required') from exc
    finally:
        if pointer.is_symlink():
            info = pointer.lstat()
            if (info.st_dev, info.st_ino) == identity and os.readlink(pointer) == f'releases/{release}':
                pointer.unlink()


def _sync(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _activate(home: _Home, kit: _Store, before: dict, releases: dict, release: str, new_skills: set[str] | None = None, transaction: dict | None = None) -> dict:
    state, found = _validate(home, kit, pending=release, transaction=transaction)
    if state != before or found != releases:
        raise KitError('Managed preimage changed before activation')
    new_skills = new_skills or set()
    skills = home.anchor('skills')
    for name in new_skills:
        entry = skills / name
        if entry.exists() or entry.is_symlink():
            raise KitError(f'Foreign skill name collision: {name}')
    after = {'schema_version': 1, 'current': release, 'previous': before['current']}
    marker = kit / 'transaction.json'
    if transaction is None:
        transaction = {'operation': 'activate', 'before': before, 'after': after, 'new_skills': sorted(new_skills)}
        _write_json(marker, transaction, exclusive=True)
        _sync(kit.root)
    try:
        if before['current'] is None:
            for name in MANAGED_NAMES:
                if name != 'skills':
                    (home.path / name).symlink_to(f'.portable-kit/current/{name}', target_is_directory=name not in ('AGENTS.md', 'config.toml'))
        for name in sorted(new_skills):
            (skills / name).symlink_to(f'../.portable-kit/current/skills/{name}', target_is_directory=True)
        _sync(skills)
        _sync(home.path)
        home.check()
        if _json(kit / 'state.json') != before or _json(marker) != transaction:
            raise KitError('Activation metadata changed before pointer replacement')
        if before['current'] is not None:
            if not (kit / 'current').is_symlink() or os.readlink(kit / 'current') != f"releases/{before['current']}":
                raise KitError('Current preimage changed before pointer replacement')
            _manifest(kit, before['current'])
        _switch(kit, release)
        _sync(kit.root)
        _atomic_json(kit / 'state.json', after)
        _sync(kit.root)
        _validate(home, kit, transaction=transaction)
        marker.unlink()
        _sync(kit.root)
        return after
    except BaseException as failure:
        raise KitError(f'Interrupted activation preserved for reconciliation: {home.target}/.portable-kit/transaction.json') from failure


def _remove_stage(stage: Path, identity: tuple | None, lock: dict, home: _Home | None = None) -> bool:
    if not stage.exists() and not stage.is_symlink():
        return True
    descriptor = None
    try:
        descriptor = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        root = os.fstat(descriptor)
        if (root.st_dev, root.st_ino) != identity:
            return False
        anchored = Path(f'/proc/self/fd/{descriptor}')
        actual = _scan(descriptor)
        if any(lock['files'].get(name) != entry for name, entry in actual.items()):
            return False
        entries = _tree(anchored, lock)

        def remove(directory: int, prefix: str) -> None:
            for entry in sorted(os.scandir(directory), key=lambda item: item.name):
                relative = prefix + entry.name
                expected = entries.get(relative)
                info = entry.stat(follow_symlinks=False)
                if expected != (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode)):
                    raise KitError('Managed cleanup identity changed')
                if home is not None:
                    home.check()
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        opened = os.fstat(child)
                        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                            raise KitError('Managed cleanup directory changed')
                        remove(child, relative + '/')
                    finally:
                        os.close(child)
                    current = os.stat(entry.name, dir_fd=directory, follow_symlinks=False)
                    if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                        raise KitError('Managed cleanup directory replaced')
                    os.rmdir(entry.name, dir_fd=directory)
                else:
                    child = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                    with os.fdopen(child, 'rb') as stream:
                        opened = os.fstat(stream.fileno())
                        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                        current = os.stat(entry.name, dir_fd=directory, follow_symlinks=False)
                        if (opened.st_dev, opened.st_ino, opened.st_nlink) != (info.st_dev, info.st_ino, 1) or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                            raise KitError('Managed cleanup file changed')
                        expected_file = lock['files'][relative]
                        if digest != expected_file['sha256'] or opened.st_size != expected_file['bytes'] or stat.S_IMODE(opened.st_mode) != expected_file['mode']:
                            raise KitError('Managed cleanup file drift')
                    os.unlink(entry.name, dir_fd=directory)

        remove(descriptor, '')
        if home is not None:
            home.check()
        current = stage.lstat()
        if (current.st_dev, current.st_ino) != identity:
            return False
        stage.rmdir()
        return True
    except (OSError, KitError):
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)


def install(bundle: Path, target: Path) -> dict:
    bundle, lock = _bundle(bundle, target)
    with _locked(target, initialize=True) as (home, kit):
        before, releases = _validate(home, kit)
        _admit(lock, releases)
        new_skills = _incoming_skills(home, releases, lock)
        release = lock['id']
        if before['current'] == release:
            return _result(home, before, 'unchanged')
        stage = None
        stage_identity = None
        transaction = None
        try:
            if release not in releases:
                stage = kit / ('.stage-' + uuid.uuid4().hex)
                stage.mkdir(mode=0o700)
                info = stage.stat()
                stage_identity = (info.st_dev, info.st_ino)
                _copy_payload(bundle / 'payload', stage)
                _payload(stage, lock)
                if verify_bundle(bundle) != lock:
                    raise KitError('Bundle changed during staging')
                home.check()
                state, latest = _validate(home, kit, stage=stage.name)
                if state != before or latest != releases:
                    raise KitError('Managed preimage changed during staging')
                destination = kit / 'releases' / release
                if destination.exists() or destination.is_symlink() or (kit / 'manifests' / (release + '.json')).exists():
                    raise KitError('Existing partial or unowned release')
                transaction = {'operation': 'install', 'before': before, 'release': release, 'stage': stage.name,
                               'new_skills': sorted(new_skills)}
                _write_json(kit / 'transaction.json', transaction, exclusive=True)
                _sync(kit.root)
                os.rename(stage, destination)
                stage = None
                _write_json(kit / 'manifests' / (release + '.json'), lock, exclusive=True)
                _sync(kit.releases)
                _sync(kit.manifests)
                releases = dict(releases, **{release: lock})
            after = _activate(home, kit, before, releases, release, new_skills, transaction)
            return _result(home, after, 'installed')
        except BaseException as failure:
            if (kit / 'transaction.json').exists() or (kit / 'transaction.json').is_symlink():
                raise KitError(f'Interrupted installation preserved for reconciliation: {home.target}/.portable-kit/transaction.json') from failure
            if stage is not None and not _remove_stage(stage, stage_identity, lock, home):
                raise KitError(f'Interrupted staging preserved for reconciliation: {home.target}/.portable-kit/{stage.name}') from failure
            raise


def describe(target: Path) -> dict:
    with _locked(target) as (home, kit):
        state, releases = _validate(home, kit)
        if state['current'] is None:
            raise KitError('Portable home has no activated release')
        result = _result(home, state)
        result['releases'] = sorted(releases)
        result['managed_bytes'] = sum(sum(f['bytes'] for f in m['files'].values()) for m in releases.values())
        result['manifest'] = releases[state['current']]
        return result


def verify(target: Path) -> dict:
    result = describe(target)
    del result['manifest']
    return result


def retire(target: Path, release_id: str) -> dict:
    with _locked(target) as (home, kit):
        state, releases = _validate(home, kit)
        if release_id not in releases:
            raise KitError('Requested retirement release is unavailable')
        if release_id in (state['current'], state['previous']):
            raise KitError('Cannot retire current or previous release')
        lock = releases[release_id]
        retained = {key: value for key, value in releases.items() if key != release_id}
        skills = home.anchor('skills')
        orphan_links = {}
        for name in _skills(lock) - _owned_skills(retained):
            entry = skills / name
            info = entry.lstat()
            orphan_links[name] = (info.st_dev, info.st_ino)
        directory = kit / 'releases' / release_id
        info = directory.lstat()
        identity = (info.st_dev, info.st_ino)
        metadata = kit / 'manifests' / (release_id + '.json')
        info = metadata.lstat()
        metadata_identity = (info.st_dev, info.st_ino)
        quarantine = kit / ('.retired-' + release_id + '-' + uuid.uuid4().hex)
        marker = kit / 'transaction.json'
        transaction = {'operation': 'retire', 'release': release_id, 'quarantine': quarantine.name,
                       'identity': list(identity), 'orphan_skills': sorted(orphan_links), 'state': state}
        _write_json(marker, transaction, exclusive=True)
        _sync(kit.root)
        try:
            home.check()
            if _manifest(kit, release_id) != lock or _json(kit / 'state.json') != state:
                raise KitError('Retirement preimage changed')
            current = directory.lstat()
            if (current.st_dev, current.st_ino) != identity:
                raise KitError('Retirement directory changed')
            os.rename(directory, quarantine)
            _sync(kit.releases)
            _sync(kit.root)
            _payload(quarantine, lock)
            for release, expected in retained.items():
                if _manifest(kit, release) != expected:
                    raise KitError('Retained release changed during retirement')
            for name, expected in orphan_links.items():
                entry = skills / name
                info = entry.lstat()
                if not stat.S_ISLNK(info.st_mode) or (info.st_dev, info.st_ino) != expected or os.readlink(entry) != f'../.portable-kit/current/skills/{name}':
                    raise KitError('Orphan skill link changed during retirement')
            if not _remove_stage(quarantine, identity, lock, home):
                raise KitError('Retirement cleanup encountered unknown or changed bytes')
            home.check()
            current = metadata.lstat()
            if (current.st_dev, current.st_ino) != metadata_identity or _json(metadata) != lock:
                raise KitError('Retirement manifest changed')
            metadata.unlink()
            _sync(kit.manifests)
            for name, expected in orphan_links.items():
                entry = skills / name
                info = entry.lstat()
                if not stat.S_ISLNK(info.st_mode) or (info.st_dev, info.st_ino) != expected or os.readlink(entry) != f'../.portable-kit/current/skills/{name}':
                    raise KitError('Orphan skill link changed during retirement')
                home.check()
                entry.unlink()
            _sync(skills)
            if _json(kit / 'state.json') != state:
                raise KitError('Activation changed during retirement')
            home.check()
            _validate(home, kit, transaction=transaction)
            marker.unlink()
            _sync(kit.root)
            result = _result(home, state, 'retired')
            result['retired_release_id'] = release_id
            result['releases'] = sorted(retained)
            return result
        except BaseException as failure:
            raise KitError(f'Interrupted retirement preserved for reconciliation: {home.target}/.portable-kit/transaction.json') from failure


def rollback(target: Path, release_id: str | None = None) -> dict:
    with _locked(target) as (home, kit):
        before, releases = _validate(home, kit)
        release = release_id if release_id is not None else before['previous']
        if release not in releases:
            raise KitError('Requested rollback release is unavailable')
        if release == before['current']:
            return _result(home, before, 'unchanged')
        after = _activate(home, kit, before, releases, release)
        return _result(home, after, 'rolled-back')


def run(target: Path, argv: list[str]) -> int:
    if not argv:
        raise KitError('run requires a command')
    with _locked(target) as (home, kit):
        state, _ = _validate(home, kit)
        if state['current'] is None:
            raise KitError('Portable home has no activated release')
        environment = os.environ.copy()
        environment['CODEX_HOME'] = str(home.target)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        home.check()
        return subprocess.run(argv, env=environment, check=False).returncode
