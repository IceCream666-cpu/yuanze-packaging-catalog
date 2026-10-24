"""Connect individually finished source models to the local viewer; never publish."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/client-motion-demo'
SOURCE = BASE / 'model-source/collection'

def integrate(ids):
    config_path = BASE / 'src/structure/collection-products.json'
    manifest_path = BASE / 'packaging-manifest.json'
    config = json.loads(config_path.read_text())
    manifest = json.loads(manifest_path.read_text())
    destinations = {
        identifier: BASE / 'public/assets/packaging' / f'{identifier}.glb'
        for identifier in ids
    }
    for destination in destinations.values():
        assert not destination.is_symlink()
    payloads = {}
    for identifier in ids:
        assert identifier in config, identifier
        review = json.loads((SOURCE / identifier / 'review-config.json').read_text())
        info = json.loads((SOURCE / identifier / 'model-info.json').read_text())
        parts = review.pop('parts')
        assert set(p['node'] for p in parts) == set(info['components'])
        assert info['containsFormula'] is False
        assert all(len(p['short'][0]) <= 4 for p in parts)
        assert review['explosion']['offsets']['print'][2] > review['explosion']['offsets']['label'][2]
        raw = (BASE / 'packaging-assets' / f'{identifier}.glb').read_bytes()
        payloads[identifier] = raw
        config[identifier].update(parts=parts, review=review)
        entry = next(f for f in manifest['files'] if f['name'] == f'{identifier}.glb')
        entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        product = next(p for p in manifest['additionalProducts'] if p['posterId'] == identifier)
        product['components'] = [p['node'] for p in parts]
        print(identifier, len(raw), entry['sha256'])
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    # Other models can still be exporting; the final showroom build checks the entire manifest.
    for identifier in ids:
        destinations[identifier].write_bytes(payloads[identifier])

if __name__ == '__main__':
    integrate(sys.argv[1:])
