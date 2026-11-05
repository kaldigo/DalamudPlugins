"""Combine the maintained source feeds, validating everything before replacing the feed."""
import argparse
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse
import tempfile
from release_tools import validate_package
from testing_channels import compose_channels, validate_config

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
            upstream_metadata = name == 'RotationSolver' and (
                key == 'RepoUrl' and plugin[key] == 'https://github.com/FFXIV-CombatReborn/RotationSolverReborn' or
                key == 'IconUrl' and plugin[key] == 'https://raw.githubusercontent.com/FFXIV-CombatReborn/RebornAssets/main/IconAssets/RSR_Icon.png')
            if not url.path.startswith('/kaldigo/') and not upstream_metadata:
                raise ValueError(f'Unexpected repository owner in {key} for {name}')
        if 'TestingAssemblyVersion' in plugin:
            if not re.fullmatch(r'\d+(?:\.\d+){2,3}', plugin['TestingAssemblyVersion']) or not isinstance(plugin.get('TestingDalamudApiLevel'), int):
                raise ValueError(f'Invalid testing channel for {name}')
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


def validate_policies(policies, expected):
    modes = {'source-managed', 'reviewed-source-release', 'routine-auto-release', 'testing-only'}
    if set(policies) != expected or any(item.get('mode') not in modes for item in policies.values()):
        raise ValueError('Every configured plugin must have an explicit release policy')
    for name, policy in policies.items():
        if policy['mode'] == 'testing-only' and (name != 'RotationSolver' or
                policy.get('repository') != 'kaldigo/RotationSolverReborn'):
            raise ValueError('Unreviewed testing-only policy')


def stable_fields(entry):
    return {key: value for key, value in entry.items() if key not in
            ('TestingAssemblyVersion', 'TestingDalamudApiLevel', 'DownloadLinkTesting', 'TestingChangelog')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validate the checked-in feed without fetching')
    args = parser.parse_args()
    sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    expected = {name for source in sources for name in source['plugins']}
    policies = json.loads((ROOT / 'release-policies.json').read_text(encoding='utf-8'))
    testing = json.loads((ROOT / 'testing-sources.json').read_text(encoding='utf-8'))
    validate_config(testing)
    exclusive = {name for name, item in testing['plugins'].items() if item.get('testing_only')}
    validate_policies(policies, expected | exclusive)
    if exclusive & expected or not set(testing['plugins']).issubset(expected | exclusive):
        raise ValueError('Testing identities must match the registered stable/testing-only sources')
    if any(policies[name]['mode'] != 'testing-only' for name in exclusive):
        raise ValueError('Testing-only source requires an explicit policy')
    if args.check:
        feed = json.loads((ROOT / 'pluginmaster.json').read_text(encoding='utf-8-sig'))
    else:
        feed = []
        for source in sources:
            request = urllib.request.Request(source['url'], headers={'User-Agent': 'kaldigo-DalamudPlugins'})
            with urllib.request.urlopen(request, timeout=45) as response:
                entries = json.load(response)
            selected = [entry for entry in entries if entry['InternalName'] in source['plugins']]
            if {entry['InternalName'] for entry in selected} != set(source['plugins']):
                raise ValueError(f'Missing expected plugins from {source["url"]}')
            validate(selected)
            feed.extend(selected)
    found = validate(feed)
    if not expected.issubset(found) or not found.issubset(expected | exclusive):
        raise ValueError('Combined feed does not match the configured plugin list')
    for entry in feed:
        if entry['InternalName'] in exclusive and not entry.get('IsTestingExclusive'):
            raise ValueError('Testing-only plugin must not advertise a stable channel')
    feed.sort(key=lambda entry: entry['Name'].casefold())
    if not args.check:
        previous = json.loads((ROOT / 'pluginmaster.json').read_text(encoding='utf-8-sig'))
        prevent_downgrades(previous, feed)
        old = {entry['InternalName']: entry for entry in previous}
        for entry in feed:
            policy = policies[entry['InternalName']]
            if policy['mode'] in ['reviewed-source-release', 'routine-auto-release'] and stable_fields(old.get(entry['InternalName'], {})) != stable_fields(entry):
                verify_publication(entry, policy)
        feed = compose_channels(feed, testing)
        validate(feed)
        feed.sort(key=lambda entry: entry['Name'].casefold())
        # Validate stable sources and any advertised testing assets before atomic publication.
        temporary = ROOT / '.pluginmaster.tmp'
        temporary.write_text(json.dumps(feed, indent=2) + '\n', encoding='utf-8')
        temporary.replace(ROOT / 'pluginmaster.json')
    print('Validated:', ', '.join(entry['InternalName'] for entry in feed))


if __name__ == '__main__':
    main()
