"""Shared version planning and validated, retryable publication for plugin repositories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import zipfile


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True).strip()


def version(value):
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', value):
        raise ValueError('Release versions must have four numeric components')
    parts = tuple(map(int, value.split('.')))
    if any(part > 65534 for part in parts):
        raise ValueError('Assembly version component exhausted; review the version manually')
    return parts


def plan(releases, repo, commit, minimum, internal_name, tag=None):
    if not re.fullmatch(r'kaldigo/[A-Za-z0-9_.-]+', repo) or not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid repository or source commit')
    marker = f'<!-- plugin-source:{internal_name}:{commit} -->'
    for release in releases:
        if marker in (release.get('body') or ''):
            v = release['tag_name'].removeprefix('v')
            version(v)
            return dict(repo=repo, commit=commit, internal_name=internal_name, version=v,
                        tag='v' + v, marker=marker, skip=not release['draft'], timestamp=int(time.time()))
    versions = [version(minimum)]
    for release in releases:
        if re.fullmatch(r'v\d+\.\d+\.\d+\.\d+', release['tag_name']):
            versions.append(version(release['tag_name'][1:]))
    latest = max(versions)
    selected = version(tag[1:]) if tag else (*latest[:3], latest[3] + 1)
    version('.'.join(map(str, selected)))
    reserved = [version(item['tag_name'][1:]) for item in releases if re.fullmatch(r'v\d+\.\d+\.\d+\.\d+', item['tag_name'])]
    if tag and (not tag.startswith('v') or (reserved and selected <= max(reserved)) or selected < version(minimum)):
        raise ValueError('A manual release tag must be newer than the published/reserved versions')
    return dict(repo=repo, commit=commit, internal_name=internal_name,
                version='.'.join(map(str, selected)), tag='v' + '.'.join(map(str, selected)),
                marker=marker, skip=False, timestamp=int(time.time()))


def validate_package(folder, release):
    name = release['internal_name']
    package = folder / (name + '.zip')
    expected = (folder / 'SHA256SUMS.txt').read_text().split()
    if expected != [hashlib.sha256(package.read_bytes()).hexdigest(), package.name]:
        raise ValueError('Release checksum does not match the package')
    feed = json.loads((folder / 'pluginmaster.json').read_text(encoding='utf-8'))
    if len(feed) != 1:
        raise ValueError('A plugin release must export exactly one feed entry')
    manifest = feed[0]
    url = f'https://github.com/{release["repo"]}/releases/download/{release["tag"]}/{name}.zip'
    if manifest['InternalName'] != name or manifest['AssemblyVersion'] != release['version']:
        raise ValueError('Release identity/version mismatch')
    if any(manifest[key] != url for key in ['DownloadLinkInstall', 'DownloadLinkUpdate', 'DownloadLinkTesting']):
        raise ValueError('Release feed does not point at the planned immutable asset')
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() or name + '.dll' not in archive.namelist():
            raise ValueError('Invalid plugin archive')
        packaged = json.loads(archive.read(name + '.json'))
        if packaged['AssemblyVersion'] != release['version'] or packaged['InternalName'] != name:
            raise ValueError('Packaged manifest differs from release plan')
    return manifest


def publish(folder, release, branch, preview=True):
    if release['skip']:
        folder.mkdir(parents=True, exist_ok=True)
        url = f'https://github.com/{release["repo"]}/releases/download/{release["tag"]}/pluginmaster.json'
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read()
        recovered = json.loads(data)
        if len(recovered) != 1 or recovered[0]['AssemblyVersion'] != release['version'] or recovered[0]['InternalName'] != release['internal_name']:
            raise ValueError('Published recovery manifest does not match the release plan')
        recovered_file = folder / 'recovered-pluginmaster.json'
        recovered_file.write_bytes(data)
        update_feed(recovered_file, branch, release['version'])
        print('Existing release verified; source feed recovered if necessary.')
        return
    manifest = validate_package(folder, release)
    repo, tag = release['repo'], release['tag']
    notes = folder / 'release-notes.md'
    notes.write_text(manifest.get('Changelog', 'Validated plugin update.') + '\n\n' + release['marker'] +
                     f'\nSource commit: https://github.com/{repo}/commit/{release["commit"]}\n', encoding='utf-8')
    remote_tag = subprocess.check_output(['git', 'ls-remote', '--tags', 'origin', f'refs/tags/{tag}'], text=True).strip()
    if not remote_tag:
        local = subprocess.run(['git', 'rev-parse', '--verify', tag + '^{commit}'], capture_output=True, text=True)
        if local.returncode:
            subprocess.run(['git', 'tag', tag, release['commit']], check=True)
        elif local.stdout.strip() != release['commit']:
            raise ValueError('Local release tag points to different source')
        subprocess.run(['git', 'push', 'origin', f'refs/tags/{tag}'], check=True)
    subprocess.run(['git', 'fetch', 'origin', 'tag', tag], check=True)
    tagged = subprocess.check_output(['git', 'rev-parse', tag + '^{commit}'], text=True).strip()
    if tagged != release['commit']:
        raise ValueError('Release tag does not point at the validated source commit')
    existing = subprocess.run(['gh', 'api', f'repos/{repo}/releases/tags/{tag}'], capture_output=True, text=True)
    if existing.returncode:
        gh('release', 'create', tag, '--repo', repo, '--target', release['commit'], '--draft',
           '--title', f'{release["internal_name"]} {tag}', '--notes-file', str(notes),
           *( ['--prerelease'] if preview else [] ))
    else:
        current = json.loads(existing.stdout)
        if release['marker'] not in (current.get('body') or ''):
            raise ValueError('Existing release belongs to another source commit; refusing to overwrite')
        if not current['draft']:
            raise ValueError('Published releases are immutable; retry planning instead')
    # Only draft assets may be replaced on retry. Published assets are never clobbered.
    gh('release', 'upload', tag, '--repo', repo, '--clobber', str(folder / (release['internal_name'] + '.zip')),
       str(folder / 'pluginmaster.json'), str(folder / 'SHA256SUMS.txt'))
    remote = json.loads(gh('api', f'repos/{repo}/releases/tags/{tag}'))
    assets = {asset['name']: asset for asset in remote['assets']}
    for name in [release['internal_name'] + '.zip', 'pluginmaster.json', 'SHA256SUMS.txt']:
        data = (folder / name).read_bytes()
        if name not in assets or assets[name]['state'] != 'uploaded' or assets[name]['size'] != len(data):
            raise ValueError('Uploaded release assets are incomplete')
        if assets[name].get('digest') != 'sha256:' + hashlib.sha256(data).hexdigest():
            raise ValueError('GitHub asset checksum mismatch')
    gh('release', 'edit', tag, '--repo', repo, '--draft=false')
    # Publish the feed only after the archive is public. Retry concurrent source updates.
    update_feed(folder / 'pluginmaster.json', branch, release['version'])
    print(f'Published https://github.com/{repo}/releases/tag/{tag}')


def update_feed(feed_file, branch, released_version):
    data = feed_file.read_bytes()
    # Packaging writes a candidate source feed. Its reviewed artifact is saved
    # above; restore this generated tracked file before changing branches.
    subprocess.run(['git', 'restore', '--source=HEAD', '--staged', '--worktree', '--', 'pluginmaster.json'], check=True)
    subprocess.run(['git', 'config', 'user.name', 'github-actions[bot]'], check=True)
    subprocess.run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'], check=True)
    for _ in range(3):
        subprocess.run(['git', 'fetch', 'origin', branch], check=True)
        subprocess.run(['git', 'switch', '-C', 'release-feed-update', f'origin/{branch}'], check=True)
        current = json.loads(Path('pluginmaster.json').read_text(encoding='utf-8-sig'))
        if version(current[0]['AssemblyVersion']) > version(released_version):
            print('A newer feed is already published; leaving it in place.')
            return
        Path('pluginmaster.json').write_bytes(data)
        subprocess.run(['git', 'add', 'pluginmaster.json'], check=True)
        if subprocess.run(['git', 'diff', '--cached', '--quiet']).returncode == 0:
            return
        subprocess.run(['git', 'commit', '-m', f'Publish validated plugin feed {released_version}'], check=True)
        if subprocess.run(['git', 'push', 'origin', f'HEAD:refs/heads/{branch}']).returncode == 0:
            return
    raise RuntimeError('Feed publication raced with other changes; rerun the release to recover')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['plan', 'publish'])
    parser.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY'))
    parser.add_argument('--commit')
    parser.add_argument('--minimum')
    parser.add_argument('--name')
    parser.add_argument('--tag')
    parser.add_argument('--plan', required=True)
    parser.add_argument('--branch', default='master')
    parser.add_argument('--assets', default='artifacts')
    args = parser.parse_args()
    if args.operation == 'plan':
        pages = json.loads(gh('api', f'repos/{args.repo}/releases?per_page=100', '--paginate', '--slurp'))
        releases = [item for page in pages for item in page]
        result = plan(releases, args.repo, args.commit, args.minimum, args.name, args.tag)
        # A delayed retry must never publish older source over a newer release.
        for item in releases:
            match = re.search(r'<!-- plugin-source:' + re.escape(args.name) + r':([a-f0-9]{40}) -->', item.get('body') or '')
            if match and not item['draft']:
                ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', args.commit, match[1]])
                if ancestor.returncode == 0:
                    result = plan([item], args.repo, match[1], args.minimum, args.name)
                    break
        Path(args.plan).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
                for key in ['tag', 'version', 'skip']:
                    output.write(f'{key}={str(result[key]).lower()}\n')
        print(json.dumps(result))
    else:
        publish(Path(args.assets).resolve(), json.loads(Path(args.plan).read_text()), args.branch)
