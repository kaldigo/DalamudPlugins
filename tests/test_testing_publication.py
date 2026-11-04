import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import publish_testing as publisher


class TestingPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.commit = 'a' * 40
        self.repo = 'kaldigo/FFXIVAccord'
        self.tag = 'testing-v2.0.0.0'
        url = f'https://github.com/{self.repo}/releases/download/{self.tag}/Accord.zip'
        self.manifest = dict(InternalName='Accord', AssemblyVersion='2.0.0.0', DalamudApiLevel=15,
                             DownloadLinkTesting=url, DownloadLinkInstall=url, DownloadLinkUpdate=url)
        with zipfile.ZipFile(self.folder / 'Accord.zip', 'w') as archive:
            archive.writestr('Accord.dll', b'fixture')
            archive.writestr('Accord.json', json.dumps(self.manifest))
        (self.folder / 'testing-release.json').write_text(json.dumps(self.manifest))
        (self.folder / 'SOURCE_COMMIT.txt').write_text(self.commit + '\n')
        digest = hashlib.sha256((self.folder / 'Accord.zip').read_bytes()).hexdigest()
        (self.folder / 'SHA256SUMS.txt').write_text(digest + '  Accord.zip\n')

    def test_validated_assets_exclude_frozen_stable_feed(self):
        tag, assets = publisher.validate(self.folder, self.repo, 'Accord', self.commit)
        self.assertEqual(tag, self.tag)
        self.assertEqual(set(assets), {'Accord.zip', 'testing-release.json', 'SHA256SUMS.txt', 'SOURCE_COMMIT.txt'})

    def test_wrong_source_identity_and_corruption_rejected(self):
        with self.assertRaises(ValueError): publisher.validate(self.folder, self.repo, 'Accord', 'b' * 40)
        with self.assertRaises(ValueError): publisher.validate(self.folder, 'kaldigo/Other', 'Accord', self.commit)
        with (self.folder / 'Accord.zip').open('ab') as archive: archive.write(b'tampered')
        with self.assertRaises(ValueError): publisher.validate(self.folder, self.repo, 'Accord', self.commit)

    def test_published_retry_never_uploads_or_writes_a_feed(self):
        _, digests = publisher.validate(self.folder, self.repo, 'Accord', self.commit)
        release = dict(draft=False, body=f'<!-- accord-testing-source:{self.commit} -->',
                       assets=[dict(name=name, digest=digest) for name, digest in digests.items()])
        before = {path.name: path.read_bytes() for path in self.folder.iterdir()}
        with patch.object(publisher.subprocess, 'check_output', side_effect=[self.commit, self.commit + '\trefs/tags/' + self.tag, self.commit]), \
             patch.object(publisher.subprocess, 'run'), patch.object(publisher, 'find_release', return_value=release), \
             patch.object(publisher, 'gh') as gh:
            publisher.publish(self.folder, self.repo, 'Accord', self.commit)
            gh.assert_not_called()
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.folder.iterdir()})

    def test_published_digest_mismatch_is_not_repaired(self):
        with self.assertRaises(ValueError): publisher.verify_assets(dict(assets=[dict(name='Accord.zip', digest='bad')]), {'Accord.zip': 'expected'})
