"""One-time replacement of the known accidentally uploaded private IPA."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

repo = 'zynthec-dev/zynthec-apps-altsource'
tag = 'mipet-0.1.0-beta'
release = json.loads(subprocess.check_output(['gh', 'api', f'repos/{repo}/releases/tags/{tag}']))
for asset in release['assets']:
    if asset.get('digest') == 'sha256:274bded7e43dda2aa2ed891ac3063bf22753ec58050b48b02e9b7c4e8c4a92db':
        blob = json.loads(subprocess.check_output(['gh', 'api', f'repos/{repo}/git/blobs/be2d1192c2c2d34812d601a8780ee7b861c80471']))
        data = base64.b64decode(blob['content'])
        assert hashlib.sha256(data).hexdigest() == 'c51bc6e9d7a89ace196b7dfb5171a2615a618fe9eda636b48fb1350f72cf79bb'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / asset['name']
            path.write_bytes(data)
            subprocess.run(['gh', 'release', 'upload', tag, str(path), '--clobber', '--repo', repo], check=True)
        print('Replaced known private IPA with verified public build 2')
