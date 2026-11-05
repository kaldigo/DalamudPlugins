"""Compatibility mirror only; native testing channels are composed in the main feed."""
import argparse
import json
from pathlib import Path
from testing_channels import overlay, validate_config, verify_candidate, fetch, version

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        validate_config(json.loads((ROOT / 'testing-sources.json').read_text()))
        print('Legacy alias configuration valid; main is authoritative.')
        return
    data = fetch('https://raw.githubusercontent.com/kaldigo/DalamudPlugins/main/pluginmaster.json')
    if not isinstance(json.loads(data), list):
        raise ValueError('Invalid main feed')
    temporary = ROOT / '.testing-pluginmaster.tmp'
    temporary.write_bytes(data)
    temporary.replace(ROOT / 'testing-pluginmaster.json')
    print('Mirrored the main feed; no separate channel composition.')

if __name__ == '__main__': main()
