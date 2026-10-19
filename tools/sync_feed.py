"""Combine the maintained source feeds, validating everything before replacing the feed."""
import argparse
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse
import tempfile
from release_tools import validate_package

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['InternalName', 'Name', 'Author', 'AssemblyVersion', 'DalamudApiLevel',
            'Description', 'RepoUrl', 'IconUrl', 'DownloadLinkInstall',
            'DownloadLinkUpdate', 'DownloadLinkTesting']


def validate(feed):
    if not isinstance(feed, list) or not feed:
        raise ValueError('Expected a nonempty plugin list')
    names = set()
    for plugin in feed:
        for key in REQUIRED:
            if not plugin.get(key):
                raise ValueError(f'Missing {key} in {plugin.get("InternalName", "entry")}')
        name = plugin['InternalName']
        if name in names:
            raise ValueError(f'Duplicate plugin: {name}')
        names.add(name)
        if not re.fullmatch(r'\d+(?:\.\d+){2,3}', plugin['AssemblyVersion']):
            raise ValueError(f'Invalid version for {name}')
        if not isinstance(plugin['DalamudApiLevel'], int) or plugin['DalamudApiLevel'] < 1:
            raise ValueError(f'Invalid Dalamud API for {name}')
        for key in ['RepoUrl', 'IconUrl', 'DownloadLinkInstall', 'DownloadLinkUpdate', 'DownloadLinkTesting']:
            url = urlparse(plugin[key])
            if url.scheme != 'https' or url.hostname not in ['github.com', 'raw.githubusercontent.com']:
                raise ValueError(f'Unexpected {key} for {name}')
            if not url.path.startswith('/kaldigo/'):
                raise ValueError(f'Unexpected repository owner in {key} for {name}')
    return names


def prevent_downgrades(previous, incoming):
    old = {entry['InternalName']: entry for entry in previous}
    for entry in incoming:
        name = entry['InternalName']
        if name in old:
            before = tuple(map(int, old[name]['AssemblyVersion'].split('.')))
            after = tuple(map(int, entry['AssemblyVersion'].split('.')))
            if after < before:
                raise ValueError(f'Refusing version downgrade for {name}')


def verify_publication(entry, policy):
    url = urlparse(entry['DownloadLinkInstall'])
    parts = url.path.split('/')
    repo = policy['repository']
    if len(parts) != 7 or '/'.join(parts[1:3]) != repo or parts[3:5] != ['releases', 'download']:
        raise ValueError('Automatic release must use an immutable source GitHub release URL')
    tag = parts[5]
    base = f'https://github.com/{repo}/releases/download/{tag}'
    with tempfile.TemporaryDirectory(prefix='plugin-release-verification-') as temporary:
        folder = Path(temporary)
        assert folder.resolve().parent == Path(tempfile.gettempdir()).resolve()
        for name in [entry['InternalName'] + '.zip', 'SHA256SUMS.txt']:
            with urllib.request.urlopen(base + '/' + name, timeout=60) as response:
                (folder / name).write_bytes(response.read())
        (folder / 'pluginmaster.json').write_text(json.dumps([entry]), encoding='utf-8')
        validate_package(folder, dict(repo=repo, tag=tag, version=entry['AssemblyVersion'], internal_name=entry['InternalName']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validate the checked-in feed without fetching')
    args = parser.parse_args()
    sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    expected = {name for source in sources for name in source['plugins']}
    policies = json.loads((ROOT / 'release-policies.json').read_text(encoding='utf-8'))
    if set(policies) != expected or any(item['mode'] not in ['source-managed', 'routine-auto-release'] for item in policies.values()):
        raise ValueError('Every configured plugin must have an explicit release policy')
    if args.check:
        feed = json.loads((ROOT / 'pluginmaster.json').read_text(encoding='utf-8-sig'))
    else:
        feed = []
        for source in sources:
            request = urllib.request.Request(source['url'], headers={'User-Agent': 'kaldigo-DalamudPlugins'})
            with urllib.request.urlopen(request, timeout=45) as response:
                entries = json.load(response)
            validate(entries)
            selected = [entry for entry in entries if entry['InternalName'] in source['plugins']]
            if {entry['InternalName'] for entry in selected} != set(source['plugins']):
                raise ValueError(f'Missing expected plugins from {source["url"]}')
            feed.extend(selected)
    if validate(feed) != expected:
        raise ValueError('Combined feed does not match the configured plugin list')
    feed.sort(key=lambda entry: entry['Name'].casefold())
    if not args.check:
        previous = json.loads((ROOT / 'pluginmaster.json').read_text(encoding='utf-8-sig'))
        prevent_downgrades(previous, feed)
        old = {entry['InternalName']: entry for entry in previous}
        for entry in feed:
            policy = policies[entry['InternalName']]
            if policy['mode'] == 'routine-auto-release' and old.get(entry['InternalName']) != entry:
                verify_publication(entry, policy)
        # All sources must validate before writing anything. Failed updates preserve the last feed.
        (ROOT / 'pluginmaster.json').write_text(json.dumps(feed, indent=2) + '\n', encoding='utf-8')
    print('Validated:', ', '.join(entry['InternalName'] for entry in feed))


if __name__ == '__main__':
    main()
