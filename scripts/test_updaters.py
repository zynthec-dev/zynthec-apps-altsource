import copy
import io
import json
from pathlib import Path
import plistlib
import unittest
import zipfile
from update_owned_app import update

ROOT = Path(__file__).resolve().parents[1]


class OwnAppTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT / 'source.json').read_text())
        self.ipa = (ROOT / 'bootstrap/miPet-0.1.0-2.ipa').read_bytes()
        self.release = {'draft': False, 'prerelease': False, 'published_at': '2026-09-16T12:00:00Z', 'body': 'Test', 'assets': [{'name': 'miPet.ipa', 'size': len(self.ipa), 'browser_download_url': 'https://example.com/miPet.ipa'}]}

    def test_preserves_other_apps_and_uses_real_ipa_metadata(self):
        sideinstaller = copy.deepcopy(self.source['apps'][0])
        result = update(self.source, self.release, self.ipa)
        self.assertEqual(result['apps'][0], sideinstaller)
        version = result['apps'][1]['versions'][0]
        self.assertEqual((version['version'], version['buildVersion']), ('0.1.0', '2'))
        self.assertEqual(version['minOSVersion'], '17.0')
        self.assertEqual(version['size'], len(self.ipa))

    def test_repeated_release_does_not_duplicate_version(self):
        update(self.source, self.release, self.ipa)
        update(self.source, self.release, self.ipa)
        self.assertEqual(len(self.source['apps'][1]['versions']), 1)

    def test_rejects_size_mismatch(self):
        with self.assertRaises(ValueError): update(self.source, self.release, self.ipa[:-1])

    def test_rejects_embedded_key(self):
        data = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.ipa)) as original, zipfile.ZipFile(data, 'w') as archive:
            for name in original.namelist():
                value = original.read(name)
                if name == 'Payload/miPet.app/Info.plist':
                    info = plistlib.loads(value)
                    info['MIPET_GEMINI_API_KEY'] = 'dummy-test-key'
                    value = plistlib.dumps(info)
                archive.writestr(name, value)
        keyed = data.getvalue()
        self.release['assets'][0]['size'] = len(keyed)
        with self.assertRaisesRegex(ValueError, 'API key'):
            update(self.source, self.release, keyed)


if __name__ == '__main__':
    unittest.main()
