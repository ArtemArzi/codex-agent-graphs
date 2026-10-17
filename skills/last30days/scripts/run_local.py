"""Local last30days launcher: no cookies/setup; bounded project outputs."""
import os
from pathlib import Path
import subprocess
import sys

def prepare(argv):
    args=list(argv)
    # Match the engine's normalized command dispatch, including split topics.
    normalized=[' '.join(a.strip().lower().split()) for a in args]
    if any(a in {'setup','library','queue','library feed','library search','queue list','queue cover'}
           or a.startswith(('library search ','queue cover ','--publish','--browser',
                            '--allow-browser','--store','--record-fixtures')) for a in args):
        raise ValueError('Setup, publishing, library/queue/store modes, recording and browser extraction are outside this research launcher.')
    if any(a in {'setup','library','queue','library feed','library search','queue list','queue cover'}
           or a.startswith(('library search ','queue cover ')) for a in normalized):
        raise ValueError('Stateful command mode is outside this research launcher.')
    # Pinned upstream build_parser uses allow_abbrev=False and validates extras.
    project=Path.cwd().resolve()
    def take(flag):
        for i,a in enumerate(args):
            if a==flag:
                if i+1>=len(args): raise ValueError(flag+' requires a value')
                value=args[i+1];del args[i:i+2];return value
            if a.startswith(flag+'='):
                value=a.split('=',1)[1];del args[i];return value
        return None
    p=take('--project-root')
    if p is not None: project=Path(p).resolve()
    if not project.is_dir(): raise ValueError('Project root must exist.')
    no_save='--no-save' in args
    if no_save: args.remove('--no-save')
    save=take('--save-dir')
    preflight='--preflight' in args or '--help' in args or '-h' in args
    if no_save or preflight:
        save=''
    elif save is None or save=='':
        raise ValueError('Supply project-local --save-dir or explicit --no-save.')
    elif not Path(save).resolve().is_relative_to(project):
        raise ValueError('Research output must stay within the project root.')
    if save: save=str(Path(save).resolve())
    for flag in ('--output','--export-dir','--preflight-report-on-save-dir'):
        value=take(flag)
        if value is not None:
            if not value or not Path(value).resolve().is_relative_to(project):
                raise ValueError(flag+' must stay within the project root.')
            args.extend([flag,str(Path(value).resolve())])
    args.extend(['--no-browser-cookies','--save-dir',save])
    return args

def main():
    if sys.version_info<(3,12):
        print('Use an existing Python 3.12+ runtime.',file=sys.stderr);return 2
    try: args=prepare(sys.argv[1:])
    except ValueError as e: print(str(e),file=sys.stderr);return 2
    env=os.environ.copy()
    # Supported clean mode prevents unconditional shared report/doctor caches.
    # Existing process-environment provider credentials remain available.
    env['LAST30DAYS_CONFIG_DIR']=''
    env['LAST30DAYS_MEMORY_DIR']=''
    env['LAST30DAYS_STORE']='0'
    env['LAST30DAYS_DISCOVERY_QUEUE']='off'
    env['PYTHONDONTWRITEBYTECODE']='1'
    engine=Path(__file__).resolve().with_name('last30days.py')
    return subprocess.run([sys.executable,str(engine),*args],env=env).returncode

if __name__=='__main__': raise SystemExit(main())
