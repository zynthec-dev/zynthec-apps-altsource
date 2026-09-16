import argparse,json,urllib.request
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--remote',action='store_true');args=parser.parse_args()
source=json.loads(Path('source.json').read_text())
ids=set()
assert source['name']=='zynthec Apps'
for app in source['apps']:
    assert app['bundleIdentifier'] not in ids
    ids.add(app['bundleIdentifier'])
    assert app['versions']
    assert 'marketplaceID' not in app
    assert app['iconURL'].startswith('https://')
    for version in app['versions']:
        assert version['size']>0 and version['downloadURL'].startswith('https://')
    if args.remote:
        for url in (app['iconURL'],app['versions'][0]['downloadURL']):
            with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=60) as response:
                assert response.status==200
print('Source valid:', ', '.join(app['name'] for app in source['apps']))
