"""Publish only immutable testing assets. Never checkout or update a source feed."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from compose_testing_feed import verify_candidate, version as parse_version
from release_tools import gh, find_release


def validate(folder, repo, name, commit):
    if not re.fullmatch(r'kaldigo/[A-Za-z0-9_.-]+', repo) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Invalid repository/source')
    registrations = json.loads((Path(__file__).resolve().parents[1] / 'testing-sources.json').read_text())['plugins']
    if name not in registrations or registrations[name]['repository'] != repo:
        raise ValueError('Unregistered testing identity/repository')
    manifest = json.loads((folder / 'testing-release.json').read_text(encoding='utf-8-sig'))
    version = manifest['AssemblyVersion']
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
        raise ValueError('Testing version must have four parts')
    parse_version(version)
    tag = 'testing-v' + version
    base = f'https://github.com/{repo}/releases/download/{tag}/'
    files = [name + '.zip', 'SHA256SUMS.txt', 'testing-release.json', 'SOURCE_COMMIT.txt']
    if (folder / 'SOURCE_COMMIT.txt').read_text(encoding='utf-8-sig').strip() != commit:
        raise ValueError('Candidate was built from another source')
    def read_candidate(url):
        if not url.startswith(base) or url.removeprefix(base) not in files:
            raise ValueError('Foreign artifact URL')
        return (folder / url.removeprefix(base)).read_bytes()
    verify_candidate(name, {'candidate': base + 'testing-release.json'}, read_candidate)
    return tag, {file: 'sha256:' + hashlib.sha256((folder / file).read_bytes()).hexdigest() for file in files}


def verify_assets(release, digests):
    actual = {asset['name']: asset.get('digest') for asset in release.get('assets', [])}
    if actual != digests:
        raise ValueError('Uploaded testing assets differ from the validated candidate')


def publish(folder, repo, name, commit):
    tag, digests = validate(folder, repo, name, commit)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if head != commit:
        raise ValueError('Publish the exact checked-out source')
    subprocess.run(['git', 'fetch', 'origin', 'testing'], check=True)
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'origin/testing'], check=True)
    remote = subprocess.check_output(['git', 'ls-remote', '--tags', 'origin', 'refs/tags/' + tag], text=True).strip()
    if not remote:
        # Lightweight tag creation is explicit; an existing local tag is never moved.
        local = subprocess.run(['git', 'rev-parse', '--verify', tag + '^{commit}'], capture_output=True, text=True)
        if local.returncode:
            subprocess.run(['git', 'tag', tag, commit], check=True)
        elif local.stdout.strip() != commit:
            raise ValueError('Local tag belongs to different source')
        subprocess.run(['git', 'push', 'origin', 'refs/tags/' + tag], check=True)
    subprocess.run(['git', 'fetch', 'origin', 'tag', tag], check=True)
    if subprocess.check_output(['git', 'rev-parse', tag + '^{commit}'], text=True).strip() != commit:
        raise ValueError('Published tag belongs to different source')
    marker = f'<!-- accord-testing-source:{commit} -->'
    release = find_release(repo, tag)
    if release:
        if marker not in (release.get('body') or ''):
            raise ValueError('Existing release belongs to another publication')
        if not release['draft']:
            verify_assets(release, digests)
            print('Existing immutable testing release verified; no files changed.')
            return
    else:
        notes = folder / 'testing-notes.md'
        notes.write_text(f'Opt-in testing build; native acceptance remains pending.\n\nSource: https://github.com/{repo}/commit/{commit}\n\n{marker}\n', encoding='utf-8')
        gh('release', 'create', tag, '--repo', repo, '--target', commit, '--draft', '--prerelease',
           '--title', name + ' ' + tag, '--notes-file', str(notes))
    # Recovery may replace draft assets only. A published release never reaches this call.
    gh('release', 'upload', tag, '--repo', repo, '--clobber', *(str(folder / file) for file in digests))
    release = find_release(repo, tag)
    verify_assets(release, digests)
    gh('release', 'edit', tag, '--repo', repo, '--draft=false', '--prerelease', '--latest=false')
    print(f'Published https://github.com/{repo}/releases/download/{tag}/testing-release.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    publish(args.folder, args.repo, args.name, args.commit)
