"""Validate generated metadata and, optionally, every public download."""
import argparse
import json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--remote', action='store_true')
args = parser.parse_args()
source = json.loads(Path('source.json').read_text())
ids, urls = set(), set()
assert source['name'] == 'zynthec Apps'
for app in source['apps']:
    assert app['bundleIdentifier'] not in ids
    ids.add(app['bundleIdentifier'])
    assert app['versions'] and app['name'] and app['developerName']
    assert 'marketplaceID' not in app
    assert app['iconURL'].startswith('https://')
    urls.add(app['iconURL'])
    versions = set()
    for version in app['versions']:
        identity = (version['version'], version.get('buildVersion'))
        assert identity not in versions
        versions.add(identity)
        assert version['size'] > 0 and version['downloadURL'].startswith('https://')
        urls.add(version['downloadURL'])
if args.remote:
    for url in sorted(urls):
        request = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'zynthec-apps-source'})
        with urllib.request.urlopen(request, timeout=60) as response:
            assert response.status == 200
print('Source valid:', ', '.join(app['name'] for app in source['apps']))
