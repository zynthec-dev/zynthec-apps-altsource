#!/usr/bin/env python3
"""Reconcile every published IPA asset; filenames/tags are not app identities."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import plistlib
import urllib.request
import zipfile
from update_sideinstaller_source import entitlements, fetch

REPO = 'zynthec-dev/zynthec-apps-altsource'
EXTERNAL = {'com.frizzlem.sideinstaller'}


def inspect_ipa(asset, data):
    if len(data) != asset['size']:
        raise ValueError('IPA size mismatch')
    digest = asset.get('digest')
    if digest and digest != 'sha256:' + hashlib.sha256(data).hexdigest():
        raise ValueError('IPA checksum mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if sum(i.file_size for i in archive.infolist()) > 1024 * 1024 * 1024:
            raise ValueError('Uncompressed IPA exceeds 1 GB')
        roots = [n for n in names if n.startswith('Payload/') and n.endswith('/Info.plist') and n.count('/') == 2]
        if len(roots) != 1:
            raise ValueError('Expected one main app')
        if any(n.endswith('embedded.mobileprovision') for n in names):
            raise ValueError('Remove private provisioning profiles before publishing')
        info = plistlib.loads(archive.read(roots[0]))
        privacy, permissions = {}, set()
        for name in names:
            if name.endswith('/Info.plist'):
                metadata = plistlib.loads(archive.read(name))
                if metadata.get('MIPET_GEMINI_API_KEY'):
                    raise ValueError('Refusing embedded API key')
                if name != roots[0] and not name.endswith('.appex/Info.plist'):
                    continue
                prefix = name.rsplit('/', 1)[0]
                privacy.update({k: v for k, v in metadata.items() if k.startswith('NS') and 'UsageDescription' in k})
                permissions.update(entitlements(archive.read(prefix + '/' + metadata['CFBundleExecutable'])))
                sidecar = prefix + '/Entitlements.plist'
                if sidecar in names:
                    permissions.update(plistlib.loads(archive.read(sidecar)))
        permissions -= {'application-identifier', 'com.apple.developer.team-identifier'}
    return {'bundleIdentifier': info['CFBundleIdentifier'], 'name': info.get('CFBundleDisplayName') or info.get('CFBundleName') or info['CFBundleIdentifier'], 'version': str(info['CFBundleShortVersionString']), 'buildVersion': str(info['CFBundleVersion']), 'minOSVersion': info['MinimumOSVersion'], 'appPermissions': {'entitlements': sorted(permissions), 'privacy': privacy}}


def reconcile(source, releases, download=fetch, overrides=None):
    result = copy.deepcopy(source)
    old = {a['bundleIdentifier']: a for a in source['apps']}
    owned = {}
    # Newest publication wins for duplicate version/build pairs, deterministically.
    for release in sorted(releases, key=lambda r: (r.get('published_at') or '', r['id']), reverse=True):
        if release.get('draft') or not release.get('published_at'):
            continue
        for asset in sorted(release['assets'], key=lambda a: a['id'], reverse=True):
            if not asset['name'].lower().endswith('.ipa'):
                continue
            metadata = inspect_ipa(asset, download(asset['browser_download_url']))
            bundle = metadata['bundleIdentifier']
            if bundle in EXTERNAL:
                raise ValueError('Own release conflicts with managed upstream app')
            if bundle not in owned:
                app = copy.deepcopy(old.get(bundle, {}))
                app.update({'bundleIdentifier': bundle, 'versions': [], 'appPermissions': {'entitlements': [], 'privacy': {}}})
                app.setdefault('name', metadata['name'])
                app.setdefault('developerName', 'zynthec')
                app.setdefault('localizedDescription', release.get('body') or metadata['name'])
                app.setdefault('iconURL', source['iconURL'])
                app.setdefault('category', 'utilities')
                for key, value in (overrides or {}).get(bundle, {}).items():
                    if key not in {'name', 'developerName', 'localizedDescription', 'iconURL', 'category'}:
                        raise ValueError('Unsupported app metadata override: ' + key)
                    app[key] = value
                owned[bundle] = app
            app = owned[bundle]
            if any((v['version'], v['buildVersion']) == (metadata['version'], metadata['buildVersion']) for v in app['versions']):
                continue
            app['versions'].append({**{k: metadata[k] for k in ('version', 'buildVersion', 'minOSVersion')}, 'date': release['published_at'], 'downloadURL': asset['browser_download_url'], 'size': asset['size'], 'localizedDescription': release.get('body') or 'Neue Version.'})
            app['appPermissions']['entitlements'] = sorted(set(app['appPermissions']['entitlements']) | set(metadata['appPermissions']['entitlements']))
            app['appPermissions']['privacy'].update(metadata['appPermissions']['privacy'])
    result['apps'] = [a for a in result['apps'] if a['bundleIdentifier'] in EXTERNAL] + sorted(owned.values(), key=lambda a: a['bundleIdentifier'])
    return result


def releases_from_github():
    releases = []
    for page in range(1, 101):
        url = f'https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}'
        headers = {'User-Agent': 'zynthec-apps-source', 'Accept': 'application/vnd.github+json'}
        if os.environ.get('GH_TOKEN'):
            headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
            batch = json.load(response)
        releases.extend(batch)
        if len(batch) < 100:
            return releases
    raise ValueError('Release pagination limit exceeded; refusing partial catalog')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('source.json'))
    args = parser.parse_args()
    overrides = json.loads(Path('apps.json').read_text()) if Path('apps.json').exists() else {}
    result = reconcile(json.loads(args.source.read_text()), releases_from_github(), overrides=overrides)
    temporary = args.source.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(args.source)
    print('Indexed apps:', ', '.join(a['name'] for a in result['apps']))


if __name__ == '__main__':
    main()
