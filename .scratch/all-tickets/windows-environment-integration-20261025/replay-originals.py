"""Replay only the four archived Windows environment exports; never contacts a guest."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

packet = Path(__file__).resolve().parent
originals = packet / 'originals'
runtime = Path(os.environ['AGENT_RUNTIME_DIR'])
repo = packet.parents[2]
collector_path = repo / '.scratch/rhai-wayfinder-replan-20261008/results/windows-custody-20261008T125846Z-b7f83433/collect_serial.py'
collector = collector_path.read_text()
marker = "print(json.dumps(record['end']))"
assert collector.count(marker) == 1
# Keep the original bounded frame/file validation byte-for-byte. Only its final
# optional root-level stdout/stderr display is omitted for nested export layouts.
decoder = collector[:collector.index(marker)]
cases = [
    originals / 'workhorse-environment-fixture01/environment-fixture01-export-readback.json',
    originals / 'workhorse-environment-red01/environment-red01-export-readback.json',
    originals / 'workhorse-environment-tools01/compile-output/environment-tools01-export-readback.json',
    originals / 'workhorse-environment-green01/environment-green01-export-readback.json',
]
report = {'collector_sha256': hashlib.sha256(collector.encode()).hexdigest(),
          'decoder_change': 'omit final optional console display only; validation prefix unchanged',
          'native_execution': False, 'cases': []}
for index, readback in enumerate(cases):
    expected = json.loads(readback.read_text())
    tag = readback.name.removesuffix('-export-readback.json')
    nonce = expected['begin']['id']
    raw = readback.parent / (tag + '-serial-original.txt')
    stage = runtime / ('decode-' + str(index))
    stage.mkdir()
    (stage / 'collect_serial.py').write_text(decoder)
    shutil.copyfile(raw, stage / raw.name)
    subprocess.run([sys.executable, str(stage / 'collect_serial.py'), tag, nonce], check=True)
    actual = json.loads((stage / readback.name).read_text())
    assert actual == expected, (tag, 'reconstructed metadata differs from original readback')
    export = stage / (tag + '-export')
    saved = readback.parent / (tag + '-export')
    saved_count = 0
    for name, entry in actual['files'].items():
        data = (export / name).read_bytes()
        assert len(data) == entry['length'] and hashlib.sha256(data).hexdigest() == entry['sha256']
        if (saved / name).is_file():
            assert data == (saved / name).read_bytes()
            saved_count += 1
    item = {'tag': tag, 'nonce': nonce, 'frames': actual['frames'],
            'files': len(actual['files']), 'saved_original_files_equal': saved_count,
            'decoded_bytes': sum(x['length'] for x in actual['files'].values()),
            'accepted': actual['end']['accepted'], 'exit': actual['end']['exit'],
            'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest()}
    # Retain the small independently reconstructed native result and witnesses,
    # not a second copy of the complete archived source/exports.
    extracts = packet / 'readback' / tag
    extracts.mkdir(parents=True, exist_ok=False)
    for f in export.rglob('*'):
        if f.is_file() and (f.name in ['observer.json', 'result.json', 'bootstrap.stdout', 'bootstrap.stderr', 'payload-environment.txt', 'build-manifest.txt'] or f.suffix == '.journal'):
            relative = f.relative_to(export)
            destination = extracts / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, destination)
    report['cases'].append(item)
    print(json.dumps(item))
frozen = originals / 'workhorse-environment-tools01/environment-tools-input'
manifest = json.loads((frozen / 'input-manifest.json').read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((frozen / 'input' / name).read_bytes()).hexdigest() == digest, name
report['frozen_inputs_verified'] = len(manifest)
report['input_manifest_sha256'] = hashlib.sha256((frozen / 'input-manifest.json').read_bytes()).hexdigest()
(packet / 'replay-result.json').write_text(json.dumps(report, indent=2) + '\n')
