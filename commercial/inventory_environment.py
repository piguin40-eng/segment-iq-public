"""Emit a package inventory from the executing Python environment; never config/data."""
import argparse
import importlib.metadata
import json
import re
from pathlib import Path
from urllib.parse import quote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    components = []
    for distribution in importlib.metadata.distributions():
        meta = distribution.metadata
        name = meta.get('Name', 'unknown')
        license_text = meta.get('License-Expression') or meta.get('License') or 'REVIEW_REQUIRED'
        components.append({'type': 'library', 'name': name, 'version': distribution.version,
            'purl': 'pkg:pypi/' + quote(re.sub(r'[-_.]+', '-', name).lower()) + '@' + quote(distribution.version),
            'properties': [{'name': 'segmentiq:license-metadata-unverified', 'value': license_text[:1000]}]})
    value = {'bomFormat': 'CycloneDX', 'specVersion': '1.6', 'version': 1,
        'metadata': {'properties': [{'name': 'segmentiq:scope', 'value': 'Installed Python packages only; no binaries, models, Blender or licensing approval'}]},
        'components': sorted(components, key=lambda item: item['name'].lower())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(components)} package records written; license review remains required.')


if __name__ == '__main__':
    main()
