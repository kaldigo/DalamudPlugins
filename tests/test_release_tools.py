import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release_tools as releases
from sync_feed import prevent_downgrades


class ReleaseTests(unittest.TestCase):
    def test_draft_lookup_uses_release_listing_instead_of_public_tag_endpoint(self):
        draft = {'tag_name': 'v1.0.1.2', 'id': 123, 'draft': True}
        with patch.object(releases, 'gh', return_value=json.dumps([[draft]])) as request:
            self.assertEqual(releases.find_release('kaldigo/Example', 'v1.0.1.2'), draft)
            self.assertNotIn('/releases/tags/', request.call_args.args[1])

    def test_revision_is_newer_than_published_and_draft_versions(self):
        data = [{'tag_name': 'v1.0.1.3', 'draft': False}, {'tag_name': 'v1.0.1.4', 'draft': True}]
        result = releases.plan(data, 'kaldigo/Example', 'a' * 40, '1.0.1.1', 'Example')
        self.assertEqual(result['version'], '1.0.1.5')

    def test_same_source_is_idempotent_and_draft_can_resume(self):
        data = [{'tag_name': 'v1.0.1.2', 'draft': True, 'body': '<!-- plugin-source:Example:' + 'a' * 40 + ' -->'}]
        draft = releases.plan(data, 'kaldigo/Example', 'a' * 40, '1.0.1.1', 'Example')
        self.assertEqual(draft['tag'], 'v1.0.1.2')
        self.assertFalse(draft['skip'])
        data[0]['draft'] = False
        self.assertTrue(releases.plan(data, 'kaldigo/Example', 'a' * 40, '1.0.1.1', 'Example')['skip'])

    def test_reusing_existing_manual_version_is_rejected(self):
        with self.assertRaises(ValueError):
            releases.plan([{'tag_name': 'v1.0.1.2'}], 'kaldigo/Example', 'a' * 40, '1.0.1.1', 'Example', 'v1.0.1.2')

    def test_exhausted_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            releases.plan([{'tag_name': 'v1.0.1.65534'}], 'kaldigo/Example', 'a' * 40, '1.0.1.1', 'Example')

    def test_source_feed_downgrade_is_rejected(self):
        with self.assertRaises(ValueError):
            prevent_downgrades([{'InternalName': 'Example', 'AssemblyVersion': '1.0.1.3'}],
                               [{'InternalName': 'Example', 'AssemblyVersion': '1.0.1.2'}])

    def test_package_must_match_version_checksum_identity_and_urls(self):
        with tempfile.TemporaryDirectory(prefix='plugin-package-test-') as temporary:
            folder = Path(temporary)
            assert folder.resolve().parent == Path(tempfile.gettempdir()).resolve()
            release = dict(repo='kaldigo/Example', tag='v1.0.1.2', version='1.0.1.2', internal_name='Example')
            url = 'https://github.com/kaldigo/Example/releases/download/v1.0.1.2/Example.zip'
            manifest = dict(InternalName='Example', AssemblyVersion='1.0.1.2', DownloadLinkInstall=url, DownloadLinkUpdate=url, DownloadLinkTesting=url)
            (folder / 'pluginmaster.json').write_text(json.dumps([manifest]))
            with zipfile.ZipFile(folder / 'Example.zip', 'w') as archive:
                archive.writestr('Example.dll', b'test-binary')
                archive.writestr('Example.json', json.dumps(manifest))
            checksum = hashlib.sha256((folder / 'Example.zip').read_bytes()).hexdigest()
            (folder / 'SHA256SUMS.txt').write_text(checksum + '  Example.zip\n')
            releases.validate_package(folder, release)
            bad = dict(release, version='1.0.1.9')
            with self.assertRaises(ValueError):
                releases.validate_package(folder, bad)
            (folder / 'Example.zip').write_bytes(b'corrupted-download')
            with self.assertRaises(ValueError):
                releases.validate_package(folder, release)

    def test_existing_release_recovers_feed_without_replacing_assets(self):
        release = dict(skip=True, repo='kaldigo/Example', tag='v1.0.1.2', version='1.0.1.2', internal_name='Example')
        data = json.dumps([{'InternalName': 'Example', 'AssemblyVersion': '1.0.1.2'}]).encode()
        with tempfile.TemporaryDirectory(prefix='plugin-recovery-test-') as temporary:
            folder = Path(temporary)
            assert folder.resolve().parent == Path(tempfile.gettempdir()).resolve()
            with patch.object(releases.urllib.request, 'urlopen') as request, patch.object(releases, 'update_feed') as update, patch.object(releases, 'gh', side_effect=AssertionError('Must not change public release assets')):
                request.return_value.__enter__.return_value.read.return_value = data
                releases.publish(folder, release, 'master')
                update.assert_called_once()


if __name__ == '__main__':
    unittest.main()
