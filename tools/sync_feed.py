"""Combine the maintained source feeds, validating everything before replacing the feed."""
import argparse
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validate the checked-in feed without fetching')
    args = parser.parse_args()
    sources = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    expected = {name for source in sources for name in source['plugins']}
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
        # All sources must validate before writing anything. Failed updates preserve the last feed.
        (ROOT / 'pluginmaster.json').write_text(json.dumps(feed, indent=2) + '\n', encoding='utf-8')
    print('Validated:', ', '.join(entry['InternalName'] for entry in feed))


if __name__ == '__main__':
    main()
