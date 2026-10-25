import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


class StorageError(Exception):
    pass


def git(repo, *args):
    try:
        result = subprocess.run(['git', '--no-optional-locks', *args], cwd=repo, capture_output=True,
                                text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StorageError(f'Git operation did not complete: {exc}') from exc
    if result.returncode:
        raise StorageError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def canonical(raw):
    path = Path(os.path.abspath(raw))
    if path != path.resolve() or any(part.is_symlink() for part in (path, *path.parents)):
        raise StorageError(f'Symlink/alias path retained: {path}')
    return path


def identity(path):
    path = canonical(path)
    stat = path.stat()
    return dict(path=str(path), device=stat.st_dev, inode=stat.st_ino)


def atomic(path, value):
    canonical(path.parent)
    if path.is_symlink():
        raise StorageError('Refusing to overwrite a symlink destination')
    payload = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    fd, raw = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    temp = Path(raw)
    initial = os.fstat(fd)
    published = False
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        published = True
    finally:
        if not published:
            try:
                if not temp.is_symlink():
                    current = temp.stat()
                    if (current.st_dev, current.st_ino) == (initial.st_dev, initial.st_ino):
                        temp.unlink()
            except OSError:
                pass


def initialize(manifest, workspace, authority, lifecycle):
    if lifecycle == 'ephemeral' and not authority:
        raise StorageError('Ephemeral lifecycle requires --authority TASK')
    repo = canonical(manifest['repo'])
    common = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    manifest['storage'] = dict(marker='factory-storage-v1', workspace=identity(workspace),
                               repo=identity(repo), common=identity(common),
                               source_admin=identity(Path(git(repo, 'rev-parse', '--absolute-git-dir'))),
                               authority=authority,
                               lifecycle=lifecycle, integration_cap=2, resources={})


def validate(manifest, workspace):
    storage = manifest.get('storage')
    if not storage or storage.get('marker') != 'factory-storage-v1':
        raise StorageError('Legacy/unmanaged workspace retained; no automatic disposal authority')
    if storage['workspace'] != identity(workspace) or storage['repo'] != identity(manifest['repo']):
        raise StorageError('Workspace/source identity changed; retained')
    common = Path(git(manifest['repo'], 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    if storage['common'] != identity(common):
        raise StorageError('Git common-dir identity changed; retained')
    if (storage['source_admin'] != identity(Path(git(manifest['repo'], 'rev-parse', '--absolute-git-dir'))) or
            canonical(git(manifest['repo'], 'rev-parse', '--show-toplevel')) != canonical(manifest['repo'])):
        raise StorageError('Source Git-admin/root identity changed; retained')
    return storage


def signature(base, jobs):
    return hashlib.sha256(json.dumps(dict(base=base, jobs=jobs), sort_keys=True).encode()).hexdigest()


def reserve(manifest, workspace, key, path, branch, owner, **extra):
    storage = validate(manifest, workspace)
    canonical(path)
    if key in storage['resources']:
        raise StorageError('Resource already reserved')
    resource = dict(key=key, path=str(path), branch=branch, owner=owner, owner_state='active',
                    state='reserved', base_sha=manifest['base_sha'], **extra)
    storage['resources'][key] = resource
    atomic(workspace / 'workspace.json', manifest)
    return resource


def allocate(manifest, workspace, resource):
    validate(manifest, workspace)
    path = canonical(resource['path'])
    if path.exists() or path.is_symlink():
        raise StorageError(f'Partial/foreign allocation retained: {path}')
    refs = git(manifest['repo'], 'for-each-ref', '--format=%(refname)', 'refs/heads/' + resource['branch'])
    registrations = git(manifest['repo'], 'worktree', 'list', '--porcelain', '-z').split('\0')
    if refs or 'worktree ' + str(path) in registrations:
        raise StorageError(f'Partial branch/registration retained: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    git(manifest['repo'], 'worktree', 'add', '-b', resource['branch'], str(path), resource['base_sha'])
    resource['identity'] = identity(path)
    resource['admin'] = identity(Path(git(path, 'rev-parse', '--absolute-git-dir')))
    resource['state'] = 'ready'
    atomic(workspace / 'workspace.json', manifest)


def registered(manifest, resource):
    chunks = git(manifest['repo'], 'worktree', 'list', '--porcelain', '-z').split('\0\0')
    matches = [part.split('\0') for part in chunks if part.startswith('worktree ' + resource['path'] + '\0')]
    if len(matches) != 1 or any(item.startswith(('locked', 'prunable')) for item in matches[0]):
        raise StorageError('Missing/locked/changed worktree registration')
    if 'branch refs/heads/' + resource['branch'] not in matches[0]:
        raise StorageError('Worktree branch registration changed')


def resource_identity(manifest, workspace, resource):
    validate(manifest, workspace)
    path = canonical(resource['path'])
    expected_parent = workspace / ('jobs' if resource['key'].startswith('job:') else 'integration')
    if path.parent != expected_parent or path == Path(manifest['repo']):
        raise StorageError('Resource path escaped its declared directory')
    if resource.get('identity') != identity(path):
        raise StorageError('Worktree identity changed')
    admin = Path(git(path, 'rev-parse', '--absolute-git-dir'))
    if resource.get('admin') != identity(admin):
        raise StorageError('Git admin identity changed')
    if identity(Path(git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir'))) != manifest['storage']['common']:
        raise StorageError('Worktree common-dir changed')
    registered(manifest, resource)
    if git(path, 'symbolic-ref', 'HEAD') != 'refs/heads/' + resource['branch']:
        raise StorageError('Worktree branch changed')
    if not (path / '.git').is_file() or (path / '.git').is_symlink():
        raise StorageError('Worktree Git pointer changed')
    if (path / '.git').read_text().strip() != 'gitdir: ' + str(admin):
        raise StorageError('Worktree Git pointer changed')
    if Path((admin / 'gitdir').read_text().strip()) != path / '.git':
        raise StorageError('Git admin backlink changed')
    return path, admin


def inspect(manifest, workspace, resource):
    reasons = []
    try:
        path, admin = resource_identity(manifest, workspace, resource)
        if resource['state'] != 'terminal' or resource['owner_state'] != 'joined':
            reasons.append('active/unfinished owner; root must join writers and finish')
        if manifest['storage']['lifecycle'] != 'ephemeral' or not manifest['storage']['authority']:
            reasons.append('retained lifecycle; disposal authority unavailable')
        if git(path, 'status', '--porcelain', '--untracked-files=all', '--ignored'):
            reasons.append('tracked/staged/untracked/ignored files retained')
        if any(line and (line[0].islower() or line[0] == 'S') for line in git(path, 'ls-files', '-v').splitlines()):
            reasons.append('special index flags retained')
        allowed = {'HEAD', 'index', 'commondir', 'gitdir', 'logs', 'logs/HEAD', 'ORIG_HEAD', 'COMMIT_EDITMSG'}
        for item in admin.rglob('*'):
            relative = item.relative_to(admin).as_posix()
            if item.is_symlink() or relative not in allowed:
                reasons.append('unknown/unfinished Git-admin data: ' + relative)
        if (admin / 'COMMIT_EDITMSG').exists() and (admin / 'COMMIT_EDITMSG').read_text().strip() != git(path, 'log', '-1', '--format=%B'):
            reasons.append('uncommitted Git commit message retained')
        reachable = set(git(path, 'rev-list', '--branches', '--tags', '--remotes').splitlines())
        hashes = {git(path, 'rev-parse', 'HEAD')}
        for file in (admin / 'logs' / 'HEAD', admin / 'ORIG_HEAD'):
            if file.exists():
                for line in file.read_text().splitlines():
                    hashes.update(part for part in line.split()[:2] if len(part) in (40, 64) and all(c in '0123456789abcdef' for c in part))
        if any(value != '0' * len(value) and value not in reachable for value in hashes):
            reasons.append('reflog-only/unanchored commits retained')
        expected = resource.get('candidate_sha')
        if not expected or git(path, 'rev-parse', 'HEAD') != expected or git(path, 'rev-parse', 'refs/heads/' + resource['branch']) != expected:
            reasons.append('recovery branch/terminal commit changed or missing')
        if resource['key'].startswith('integration:'):
            receipt = resource.get('receipt')
            if not receipt or canonical(receipt).parent != workspace / 'evidence':
                reasons.append('complete evidence outside checkout unavailable')
            else:
                payload = Path(receipt).read_bytes()
                evidence = json.loads(payload)
                if (hashlib.sha256(payload).hexdigest() != resource.get('receipt_sha256') or
                        not evidence.get('log') or
                        hashlib.sha256(Path(evidence['log']).read_bytes()).hexdigest() != resource.get('log_sha256')):
                    reasons.append('verification evidence changed or incomplete')
                if (evidence.get('check') not in ('pass', 'fail') or not evidence.get('finished') or
                        evidence.get('candidate_sha') != expected or evidence.get('candidate_path') != str(path) or
                        evidence.get('base_sha') != manifest['base_sha'] or evidence.get('jobs') != resource.get('jobs') or
                        evidence.get('candidate_branch') != resource['branch'] or
                        not evidence.get('log') or not Path(evidence['log']).is_file() or
                        canonical(evidence['log']).parent != workspace / 'evidence'):
                    reasons.append('complete verification receipt/log unavailable')
            if (git(manifest['repo'], 'rev-parse', manifest['base_ref']) != manifest['base_sha'] or
                    git(manifest['repo'], 'rev-parse', 'HEAD') != manifest['base_sha'] or
                    git(manifest['repo'], 'symbolic-ref', 'HEAD') != manifest['base_ref'] or
                    git(manifest['repo'], 'status', '--porcelain', '--untracked-files=all')):
                reasons.append('source target/base moved or source dirty')
    except (OSError, ValueError, KeyError, StorageError) as exc:
        reasons.append(str(exc))
    return dict(resource=resource['key'], path=resource['path'], state=resource['state'],
                owner=resource['owner'], eligible=not reasons, reasons=reasons)


def close_resource(manifest, workspace, resource, authority, apply=False):
    report = inspect(manifest, workspace, resource)
    if authority != manifest.get('storage', {}).get('authority') or not authority:
        report['eligible'] = False
        report['reasons'].append('task authority mismatch')
    report['removed'] = False
    if not apply or not report['eligible']:
        return report
    if json.loads((workspace / 'workspace.json').read_text()) != manifest:
        raise StorageError('Workspace changed during close; retained')
    path, admin = resource_identity(manifest, workspace, resource)
    archive = dict(git_pointer=base64.b64encode((path / '.git').read_bytes()).decode(),
                   files={item.relative_to(admin).as_posix(): base64.b64encode(item.read_bytes()).decode()
                          for item in admin.rglob('*') if item.is_file()})
    encoded = (json.dumps(archive, sort_keys=True) + '\n').encode()
    archive_dir = workspace / 'evidence'
    archive_dir.mkdir(exist_ok=True)
    canonical(archive_dir)
    archive_path = archive_dir / (resource['key'].replace(':', '-') + '-git-admin.json')
    resource['admin_archive'] = str(archive_path)
    atomic(workspace / 'workspace.json', manifest)
    if archive_path.exists():
        if archive_path.is_symlink() or archive_path.read_bytes() != encoded:
            raise StorageError('Existing Git-admin archive differs; retained without overwrite')
    else:
        with archive_path.open('xb') as stream:
            stream.write(encoded)
    if archive_path.read_bytes() != encoded:
        raise StorageError('Git-admin archive readback failed; retained')
    before = json.dumps(manifest, sort_keys=True)
    latest = json.loads((workspace / 'workspace.json').read_text())
    if json.dumps(latest, sort_keys=True) != before:
        raise StorageError('Workspace changed during close; retained')
    second = inspect(manifest, workspace, resource)
    if not second['eligible']:
        return dict(second, removed=False)
    current_archive = dict(git_pointer=base64.b64encode((path / '.git').read_bytes()).decode(),
                           files={item.relative_to(admin).as_posix(): base64.b64encode(item.read_bytes()).decode()
                                  for item in admin.rglob('*') if item.is_file()})
    if current_archive != archive or archive_path.read_bytes() != encoded:
        raise StorageError('Git-admin/evidence changed before removal; retained')
    git(manifest['repo'], 'worktree', 'remove', resource['path'])
    resource['state'] = 'closed'
    atomic(workspace / 'workspace.json', manifest)
    report['removed'] = True
    return report
