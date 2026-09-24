import os
import shutil
import subprocess
import tempfile
import zipfile
 
STANDALONE = os.path.join('.next', 'standalone')
 
def norm(p):
    return p.replace(chr(92), '/')
 
def write_tree(zf, source, destination=''):
    for root, dirs, files in os.walk(source):
        for f in files:
            fp = os.path.join(root, f)
            relative = os.path.relpath(fp, source)
            zf.write(fp, norm(os.path.join(destination, relative)))
 
if not os.path.exists(STANDALONE):
    raise SystemExit('ERROR: .next/standalone not found. Ensure output:"standalone" is in next.config.mjs and run the build first.')
 
pnpm = shutil.which('pnpm')
if not pnpm:
    raise SystemExit('ERROR: pnpm is required to create the deployment package.')
 
with tempfile.TemporaryDirectory() as dependency_root:
    shutil.copy2('package.json', dependency_root)
    shutil.copy2('pnpm-lock.yaml', dependency_root)
    subprocess.run(
        [
            pnpm,
            'install',
            '--prod',
            '--no-frozen-lockfile',
            '--ignore-scripts',
            '--node-linker=hoisted',
            '--package-import-method=copy',
        ],
        cwd=dependency_root,
        check=True,
    )
 
    with zipfile.ZipFile('frontend-deploy.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1) Standalone server and traced output, excluding pnpm's non-portable links.
        for root, dirs, files in os.walk(STANDALONE):
            if os.path.abspath(root) == os.path.abspath(STANDALONE):
                dirs[:] = [directory for directory in dirs if directory != 'node_modules']
            for f in files:
                fp = os.path.join(root, f)
                zf.write(fp, norm(os.path.relpath(fp, STANDALONE)))
 
        # 2) Materialized production dependencies that remain valid on Linux.
        write_tree(zf, os.path.join(dependency_root, 'node_modules'), 'node_modules')
 
        # 3) Static assets — standalone does NOT include these; must sit at .next/static/.
        write_tree(zf, os.path.join('.next', 'static'), os.path.join('.next', 'static'))
 
        # 4) public/ assets if present.
        if os.path.exists('public'):
            write_tree(zf, 'public', 'public')
 
print('Done:', os.path.getsize('frontend-deploy.zip'), 'bytes')