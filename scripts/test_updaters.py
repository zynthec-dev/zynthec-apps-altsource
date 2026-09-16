import copy
import hashlib
import io
import plistlib
import unittest
import zipfile
from update_owned_app import reconcile, inspect_ipa


def ipa(bundle='dev.test.one', key=False, profile=False, version='1.0'):
    output = io.BytesIO()
    info = dict(CFBundleIdentifier=bundle, CFBundleName='Test App', CFBundleExecutable='Test', CFBundleShortVersionString=version, CFBundleVersion='7', MinimumOSVersion='17.0', NSCameraUsageDescription='Camera')
    if key: info['MIPET_GEMINI_API_KEY'] = 'dummy'
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr('Payload/Test.app/Info.plist', plistlib.dumps(info))
        z.writestr('Payload/Test.app/Test', b'\xcf\xfa\xed\xfe' + bytes(28))
        if profile: z.writestr('Payload/Test.app/embedded.mobileprovision', b'dummy')
    return output.getvalue()


def release(data, rid=1, aid=1, url='https://example.com/test.ipa'):
    return dict(id=rid, draft=False, prerelease=False, published_at=f'2026-09-{rid:02d}T12:00:00Z', body='Notes', assets=[dict(id=aid, name='test.ipa', size=len(data), digest='sha256:' + hashlib.sha256(data).hexdigest(), browser_download_url=url)])


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = ipa()
        self.external = dict(bundleIdentifier='com.frizzlem.sideinstaller', name='SideInstaller', versions=[])
        self.source = dict(name='zynthec Apps', iconURL='https://example.com/icon.png', apps=[self.external])
        self.release = release(self.data)

    def sync(self, releases, source=None):
        return reconcile(source or self.source, releases, lambda _: self.data)

    def test_new_app_and_real_metadata(self):
        result = self.sync([self.release])
        self.assertEqual(result['apps'][0], self.external)
        app = result['apps'][1]
        self.assertEqual(app['name'], 'Test App')
        self.assertEqual(app['versions'][0]['buildVersion'], '7')
        self.assertEqual(app['appPermissions']['privacy']['NSCameraUsageDescription'], 'Camera')
        self.assertEqual(len(self.source['apps']), 1)

    def test_rename_replaces_url_and_deduplicates(self):
        old = self.sync([self.release])
        self.release['assets'][0]['browser_download_url'] = 'https://example.com/renamed.ipa'
        new = self.sync([self.release], old)
        self.assertEqual(len(new['apps'][1]['versions']), 1)
        self.assertIn('renamed', new['apps'][1]['versions'][0]['downloadURL'])
        self.assertEqual(self.sync([self.release], new), new)

    def test_deletion_removes_owned_app(self):
        self.assertEqual(self.sync([], self.sync([self.release]))['apps'], [self.external])

    def test_drafts_ignored_and_published_prereleases_included(self):
        self.release['draft'] = True
        self.assertEqual(len(self.sync([self.release])['apps']), 1)
        self.release.update(draft=False, prerelease=True)
        self.assertEqual(len(self.sync([self.release])['apps']), 2)

    def test_multiple_apps_in_one_release(self):
        other = ipa('dev.test.two')
        self.release['assets'] += release(other, aid=2, url='https://example.com/two.ipa')['assets']
        result = reconcile(self.source, [self.release], lambda u: other if 'two' in u else self.data)
        self.assertEqual(len(result['apps']), 3)

    def test_duplicate_build_uses_newest_release(self):
        new = release(self.data, rid=2, url='https://example.com/new.ipa')
        app = self.sync([self.release, new])['apps'][1]
        self.assertEqual(len(app['versions']), 1)
        self.assertIn('new', app['versions'][0]['downloadURL'])

    def test_rejects_size(self):
        with self.assertRaisesRegex(ValueError, 'size'): inspect_ipa(self.release['assets'][0], self.data[:-1])

    def test_rejects_digest(self):
        self.release['assets'][0]['digest'] = 'sha256:bad'
        with self.assertRaisesRegex(ValueError, 'checksum'): self.sync([self.release])

    def test_rejects_key(self):
        data = ipa(key=True)
        with self.assertRaisesRegex(ValueError, 'API key'): inspect_ipa(release(data)['assets'][0], data)

    def test_rejects_profile(self):
        data = ipa(profile=True)
        with self.assertRaisesRegex(ValueError, 'profiles'): inspect_ipa(release(data)['assets'][0], data)

    def test_external_collision_rejected(self):
        data = ipa('com.frizzlem.sideinstaller')
        with self.assertRaisesRegex(ValueError, 'upstream'): reconcile(self.source, [release(data)], lambda _: data)

    def test_metadata_override(self):
        result = reconcile(self.source, [self.release], lambda _: self.data, {'dev.test.one': {'name': 'Custom'}})
        self.assertEqual(result['apps'][1]['name'], 'Custom')


if __name__ == '__main__': unittest.main()
