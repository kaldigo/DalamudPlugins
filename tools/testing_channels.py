"""Verify opt-in testing downloads for entries in the ordinary main feed."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+(?:\.\d+){2,3}', value):
        raise ValueError('Invalid version')
    parts = tuple(map(int, value.split('.')))
    if any(part > 65535 for part in parts):
        raise ValueError('Version exceeds assembly limits')
    return parts + (0,) * (4 - len(parts))


def validate_config(config):
    if config['stable_feed'] != 'https://raw.githubusercontent.com/kaldigo/DalamudPlugins/main/pluginmaster.json':
        raise ValueError('Stable feed must follow the live main branch')
    for name, entry in config['plugins'].items():
        if not re.fullmatch(r'kaldigo/[A-Za-z0-9_.-]+', entry['repository']):
            raise ValueError('Unexpected candidate repository')
        if 'testing_only' in entry and not isinstance(entry['testing_only'], bool):
            raise ValueError('testing_only must be a boolean')
        candidate = entry.get('candidate')
        if candidate is not None and not re.fullmatch(
                re.escape('https://github.com/' + entry['repository'] + '/releases/download/testing-v') +
                r'\d+\.\d+\.\d+\.\d+/testing-release\.json', candidate):
            raise ValueError('Candidate must reference an immutable testing release')
        extra = entry.get('stable_feed')
        if extra is not None and (name != 'RotationSolver' or extra !=
                'https://raw.githubusercontent.com/FFXIV-CombatReborn/CombatRebornRepo/main/pluginmaster.json'):
            raise ValueError('Unreviewed additional stable source')


def overlay(stable, candidates):
    if not isinstance(stable, list) or not stable:
        raise ValueError('Expected stable entries')
    names = [entry['InternalName'] for entry in stable]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate stable identities')
    result = copy.deepcopy(stable)
    for name, candidate in candidates.items():
        if name not in names or candidate['InternalName'] != name:
            raise ValueError('Candidate identity missing or changed')
        entry = next(item for item in result if item['InternalName'] == name)
        if entry.get('IsTestingExclusive'):
            raise ValueError('Expected an ordinary stable identity')
        if version(candidate['AssemblyVersion']) <= version(entry['AssemblyVersion']):
            continue
        if not isinstance(candidate['DalamudApiLevel'], int) or candidate['DalamudApiLevel'] < 1:
            raise ValueError('Invalid testing API level')
        entry.update(TestingAssemblyVersion=candidate['AssemblyVersion'],
                     TestingDalamudApiLevel=candidate['DalamudApiLevel'],
                     DownloadLinkTesting=candidate['DownloadLinkTesting'])
    return result


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'kaldigo-DalamudPlugins-testing'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read(128 * 1024 * 1024 + 1)
    if len(data) > 128 * 1024 * 1024:
        raise ValueError('Unexpected artifact size')
    return data


def verify_candidate(name, registration, read=fetch):
    location = registration['candidate']
    candidate = json.loads(read(location))
    base = location.rsplit('/', 1)[0]
    tag_version = base.rsplit('/testing-v', 1)[1]
    expected = base + '/' + name + '.zip'
    if candidate['InternalName'] != name or candidate['AssemblyVersion'] != tag_version or candidate['DownloadLinkTesting'] != expected:
        raise ValueError('Candidate manifest differs from registered identity/version/artifact')
    archive = read(expected)
    if read(base + '/SHA256SUMS.txt').decode().split() != [hashlib.sha256(archive).hexdigest(), name + '.zip']:
        raise ValueError('Candidate checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        if zipped.testzip() or name + '.dll' not in zipped.namelist():
            raise ValueError('Invalid candidate archive')
        packaged = json.loads(zipped.read(name + '.json'))
        if any(packaged.get(key) != candidate.get(key) for key in ['InternalName', 'AssemblyVersion', 'DalamudApiLevel']):
            raise ValueError('Packaged identity/version/API differs')
        if any(packaged.get(key) != expected for key in ['DownloadLinkInstall', 'DownloadLinkUpdate', 'DownloadLinkTesting']):
            raise ValueError('Packaged links differ from immutable artifact')
    return candidate


def compose_channels(stable, config, verify=verify_candidate, warn=print):
    validate_config(config)
    candidates = {}
    exclusive = []
    for name, registration in config['plugins'].items():
        if not registration.get('candidate'):
            continue
        try:
            candidate = verify(name, registration)
            if not isinstance(candidate.get('DalamudApiLevel'), int) or candidate['DalamudApiLevel'] < 1:
                raise ValueError('Invalid testing API level')
            if registration.get('testing_only'):
                if any(entry['InternalName'] == name for entry in stable):
                    raise ValueError('Testing-only identity also has a stable source')
                candidate = dict(candidate, IsTestingExclusive=True,
                                 TestingAssemblyVersion=candidate['AssemblyVersion'],
                                 TestingDalamudApiLevel=candidate['DalamudApiLevel'],
                                 DownloadLinkInstall=candidate['DownloadLinkTesting'],
                                 DownloadLinkUpdate=candidate['DownloadLinkTesting'])
                exclusive.append(candidate)
            else:
                candidates[name] = candidate
        except Exception as error:
            # A failed testing-only release is omitted; existing stable channels still refresh.
            warn(f'Testing candidate unavailable for {name}; not advertising it: {error}')
    return overlay(stable, candidates) + exclusive
