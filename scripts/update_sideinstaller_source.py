#!/usr/bin/env python3
"""Generate an AltStore/SideStore source from the original SideInstaller IPA."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import plistlib
import struct
import urllib.request
import zipfile

UPSTREAM = 'FrizzleM/SideInstaller'
SOURCE_URL = 'https://raw.githubusercontent.com/zynthec-dev/zynthec-apps-altsource/main/source.json'


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'SideInstaller-Source', 'Accept': 'application/vnd.github+json' if 'api.github.com/' in url else '*/*'})
    with urllib.request.urlopen(request, timeout=120) as response:
        content = response.read(256 * 1024 * 1024 + 1)
    if len(content) > 256 * 1024 * 1024:
        raise ValueError('Download exceeds maximum permitted size')
    return content


def entitlements(binary):
    magic = binary[:4]
    if magic in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
        wide = magic[-1] == 0xbf
        count = struct.unpack_from('>I', binary, 4)[0]
        result = set()
        for index in range(count):
            offset = 8 + index * (32 if wide else 20)
            start, length = struct.unpack_from('>QQ' if wide else '>II', binary, offset + 8)
            result.update(entitlements(binary[start:start + length]))
        return result
    formats = {b'\xcf\xfa\xed\xfe': ('<', 32), b'\xce\xfa\xed\xfe': ('<', 28), b'\xfe\xed\xfa\xcf': ('>', 32), b'\xfe\xed\xfa\xce': ('>', 28)}
    if magic not in formats:
        raise ValueError('Unsupported executable format; inspect before publishing')
    endian, offset = formats[magic]
    count = struct.unpack_from(endian + 'I', binary, 16)[0]
    result = set()
    for _ in range(count):
        command, size = struct.unpack_from(endian + 'II', binary, offset)
        if size < 8:
            raise ValueError('Invalid Mach-O command')
        if command == 0x1d:
            start, length = struct.unpack_from(endian + 'II', binary, offset + 8)
            signature = binary[start:start + length]
            sig_magic, sig_length, slots = struct.unpack_from('>III', signature)
            if sig_magic != 0xfade0cc0 or sig_length > len(signature):
                raise ValueError('Unsupported code signature')
            for slot in range(slots):
                kind, location = struct.unpack_from('>II', signature, 12 + 8 * slot)
                if kind == 5:
                    blob_magic, blob_length = struct.unpack_from('>II', signature, location)
                    if blob_magic != 0xfade7171:
                        raise ValueError('Unsupported entitlements blob')
                    result.update(plistlib.loads(signature[location + 8:location + blob_length]))
        offset += size
    return result


def generate(release, ipa):
    assets = [a for a in release['assets'] if a['name'] == 'SideInstaller.ipa']
    if len(assets) != 1 or release['draft'] or release['prerelease']:
        raise ValueError('Expected one stable original SideInstaller IPA')
    asset = assets[0]
    if len(ipa) != asset['size']:
        raise ValueError('IPA size does not match release metadata')
    digest = asset.get('digest')
    if digest and digest.startswith('sha256:') and hashlib.sha256(ipa).hexdigest() != digest[7:]:
        raise ValueError('IPA checksum mismatch')
    privacy = {}
    permissions = set()
    with zipfile.ZipFile(io.BytesIO(ipa)) as archive:
        infos = [n for n in archive.namelist() if n.startswith('Payload/') and n.endswith('/Info.plist') and n.count('/') == 2]
        if len(infos) != 1:
            raise ValueError('Expected exactly one main app')
        info = plistlib.loads(archive.read(infos[0]))
        if info['CFBundleIdentifier'] != 'com.frizzlem.sideinstaller':
            raise ValueError('Unexpected app identity')
        for name in archive.namelist():
            if name == infos[0] or name.endswith('.appex/Info.plist'):
                metadata = plistlib.loads(archive.read(name))
                privacy.update({k: v for k, v in metadata.items() if k.startswith('NS') and 'UsageDescription' in k})
                executable = name.rsplit('/', 1)[0] + '/' + metadata['CFBundleExecutable']
                permissions.update(entitlements(archive.read(executable)))
    permissions -= {'application-identifier', 'com.apple.developer.team-identifier'}
    icon = f"https://raw.githubusercontent.com/{UPSTREAM}/{release['tag_name']}/app-icon.png"
    version = {'version': info['CFBundleShortVersionString'], 'buildVersion': info['CFBundleVersion'], 'date': release['published_at'], 'downloadURL': asset['browser_download_url'], 'size': len(ipa), 'minOSVersion': info['MinimumOSVersion'], 'localizedDescription': f"Original release {release['tag_name']}. Release notes: {release['html_url']}"}
    app = {'name': 'SideInstaller', 'bundleIdentifier': info['CFBundleIdentifier'], 'developerName': 'FrizzleM', 'localizedDescription': 'SideInstaller installs SideStore and other IPA apps on your device. This community source links directly to the original releases by FrizzleM. Pairing and VPN requirements: https://github.com/FrizzleM/SideInstaller', 'iconURL': icon, 'category': 'utilities', 'versions': [version], 'appPermissions': {'entitlements': sorted(permissions), 'privacy': privacy}}
    return {'name': 'zynthec Apps', 'identifier': 'dev.zynthec.apps', 'subtitle': 'Eigene Apps und Community-Apps', 'description': 'Apps von zynthec und Original-Releases ausgewählter Entwickler.', 'website': 'https://github.com/zynthec-dev/zynthec-apps-altsource', 'sourceURL': SOURCE_URL, 'iconURL': icon, 'apps': [app], 'news': []}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('source.json'))
    parser.add_argument('--release-json', type=Path)
    parser.add_argument('--ipa', type=Path)
    args = parser.parse_args()
    release = json.loads(args.release_json.read_bytes() if args.release_json else fetch(f'https://api.github.com/repos/{UPSTREAM}/releases/latest'))
    asset = next(a for a in release['assets'] if a['name'] == 'SideInstaller.ipa')
    ipa = args.ipa.read_bytes() if args.ipa else fetch(asset['browser_download_url'])
    source = generate(release, ipa)
    if args.output.exists():
        previous = json.loads(args.output.read_text())
        updated_app = source['apps'][0]
        apps = previous.get('apps', [])
        indices = [i for i, app in enumerate(apps) if app['bundleIdentifier'] == updated_app['bundleIdentifier']]
        if len(indices) > 1:
            raise ValueError('Duplicate app identity in existing source')
        if indices:
            apps[indices[0]] = updated_app
        else:
            apps.append(updated_app)
        previous['apps'] = apps
        source = previous
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix('.json.tmp')
    temp.write_text(json.dumps(source, ensure_ascii=False, indent=2) + '\n')
    temp.replace(args.output)
    print('Source generated:', source['apps'][0]['versions'][0]['version'])


if __name__ == '__main__':
    main()
