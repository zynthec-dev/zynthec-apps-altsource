#!/usr/bin/env python3
"""Index configured apps from this repository's published IPA releases."""
import argparse
import io
import json
from pathlib import Path
import plistlib
import zipfile
from update_sideinstaller_source import entitlements, fetch


def update(source, release, ipa):
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('Only stable published releases are indexed')
    assets = [asset for asset in release['assets'] if asset['name'].lower().endswith('.ipa')]
    if len(assets) != 1 or len(ipa) != assets[0]['size']:
        raise ValueError('Expected one complete IPA asset')
    with zipfile.ZipFile(io.BytesIO(ipa)) as archive:
        roots = [name for name in archive.namelist() if name.startswith('Payload/') and name.endswith('/Info.plist') and name.count('/') == 2]
        if len(roots) != 1:
            raise ValueError('Expected one main app')
        info = plistlib.loads(archive.read(roots[0]))
        if info.get('MIPET_GEMINI_API_KEY'):
            raise ValueError('Refusing to publish an embedded miPet API key')
        if any(name.endswith('embedded.mobileprovision') for name in archive.namelist()):
            raise ValueError('Remove private provisioning profiles before publishing')
        app = next((app for app in source['apps'] if app['bundleIdentifier'] == info['CFBundleIdentifier']), None)
        if not app or app['developerName'] != 'zynthec':
            raise ValueError('Add the owned app metadata to source.json before releasing')
        privacy = {}
        permissions = set()
        for name in archive.namelist():
            if name == roots[0] or name.endswith('.appex/Info.plist'):
                metadata = plistlib.loads(archive.read(name))
                prefix = name.rsplit('/', 1)[0]
                privacy.update({key: value for key, value in metadata.items() if key.startswith('NS') and 'UsageDescription' in key})
                permissions.update(entitlements(archive.read(prefix + '/' + metadata['CFBundleExecutable'])))
                sidecar = prefix + '/Entitlements.plist'
                if sidecar in archive.namelist():
                    permissions.update(plistlib.loads(archive.read(sidecar)))
        permissions -= {'application-identifier', 'com.apple.developer.team-identifier'}
    version = {'version': info['CFBundleShortVersionString'], 'buildVersion': info['CFBundleVersion'], 'date': release['published_at'], 'downloadURL': assets[0]['browser_download_url'], 'size': len(ipa), 'minOSVersion': info['MinimumOSVersion'], 'localizedDescription': release.get('body') or 'Neue Version.'}
    old = [item for item in app.get('versions', []) if (item['version'], item.get('buildVersion')) != (version['version'], version['buildVersion'])]
    app['versions'] = [version] + old
    app['appPermissions'] = {'entitlements': sorted(permissions | set(app.get('appPermissions', {}).get('entitlements', []))), 'privacy': {**app.get('appPermissions', {}).get('privacy', {}), **privacy}}
    return source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--event', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path('source.json'))
    args = parser.parse_args()
    release = json.loads(args.event.read_text())['release']
    assets = [asset for asset in release['assets'] if asset['name'].lower().endswith('.ipa')]
    if len(assets) != 1:
        raise ValueError('Expected one IPA asset')
    result = update(json.loads(args.source.read_text()), release, fetch(assets[0]['browser_download_url']))
    temporary = args.source.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(args.source)


if __name__ == '__main__':
    main()
