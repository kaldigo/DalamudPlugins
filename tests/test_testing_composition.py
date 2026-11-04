import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from compose_testing_feed import overlay, validate_config, verify_candidate


class TestingCompositionTests(unittest.TestCase):
    def setUp(self):
        self.stable = [dict(InternalName='Accord', AssemblyVersion='1.0.0.0',
                            DownloadLinkInstall='stable-install', DownloadLinkUpdate='stable-update',
                            DownloadLinkTesting='stable-test', Name='Original name')]
        self.candidate = dict(InternalName='Accord', AssemblyVersion='2.0.0.0', DalamudApiLevel=15,
                              DownloadLinkTesting='https://github.com/kaldigo/FFXIVAccord/releases/download/testing-v2.0.0.0/Accord.zip')

    def test_only_testing_fields_change(self):
        before = copy.deepcopy(self.stable)
        result = overlay(self.stable, {'Accord': self.candidate})
        self.assertEqual(self.stable, before)
        changed = {key for key in result[0] if result[0][key] != before[0].get(key)}
        self.assertEqual(changed, {'TestingAssemblyVersion', 'TestingDalamudApiLevel', 'DownloadLinkTesting'})

    def test_newer_stable_supersedes_old_test(self):
        self.stable[0]['AssemblyVersion'] = '3.0.0.0'
        self.assertEqual(overlay(self.stable, {'Accord': self.candidate}), self.stable)

    def test_identity_and_duplicates_rejected(self):
        with self.assertRaises(ValueError): overlay(self.stable * 2, {})
        with self.assertRaises(ValueError): overlay(self.stable, {'Other': self.candidate})

    def test_registration_rejects_mutable_or_foreign_candidate(self):
        config = json.loads((Path(__file__).resolve().parents[1] / 'testing-sources.json').read_text())
        validate_config(config)
        for bad in ['https://github.com/kaldigo/FFXIVAccord/releases/latest/download/testing-release.json',
                    'https://github.com/other/repo/releases/download/testing-v2.0.0.0/testing-release.json']:
            config['plugins']['Accord']['candidate'] = bad
            with self.assertRaises(ValueError): validate_config(config)

    def test_archive_is_verified_before_overlay(self):
        base = self.candidate['DownloadLinkTesting'].rsplit('/', 1)[0]
        manifest = dict(self.candidate, DownloadLinkInstall=self.candidate['DownloadLinkTesting'],
                        DownloadLinkUpdate=self.candidate['DownloadLinkTesting'])
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zipped:
            zipped.writestr('Accord.dll', b'test fixture')
            zipped.writestr('Accord.json', json.dumps(manifest))
        archive = buf.getvalue()
        data = {base + '/testing-release.json': json.dumps(self.candidate).encode(),
                base + '/Accord.zip': archive,
                base + '/SHA256SUMS.txt': (hashlib.sha256(archive).hexdigest() + '  Accord.zip\n').encode()}
        registration = dict(candidate=base + '/testing-release.json')
        self.assertEqual(verify_candidate('Accord', registration, data.__getitem__), self.candidate)
        data[base + '/Accord.zip'] += b'tampered'
        with self.assertRaises(ValueError): verify_candidate('Accord', registration, data.__getitem__)


if __name__ == '__main__': unittest.main()
