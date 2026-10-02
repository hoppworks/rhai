"""Read original metadata evidence without launching Cargo or build code."""
import hashlib
import json
from pathlib import Path
import tomllib

BASE = Path(__file__).resolve().parent
EVIDENCE = BASE / 'macos-selected-graph-evidence-03'
contract = json.loads((EVIDENCE / 'contract.json').read_text())
lock_bytes = (EVIDENCE / 'Cargo.lock').read_bytes()
assert hashlib.sha256(lock_bytes).hexdigest() == contract['lock_sha256']
lock = tomllib.loads(lock_bytes.decode())
locked = {(p['name'], p['version'], p.get('source')) for p in lock['package']}
metadata = json.loads((EVIDENCE / 'metadata.stdout').read_text())
packages = {p['id']: p for p in metadata['packages']}
nodes = {n['id']: n for n in metadata['resolve']['nodes']}
root = metadata['resolve']['root']
assert packages[root]['name'] == 'rhai'
assert packages[root]['version'] == '1.26.1'
assert len(packages) == len(nodes) == 62
assert len(metadata['workspace_members']) == 3
reachable, pending = set(), [root]
while pending:
    current = pending.pop()
    if current in reachable:
        continue
    reachable.add(current)
    pending.extend(d['pkg'] for d in nodes[current]['deps'])
assert len(reachable) == 61
for p in packages.values():
    assert (p['name'], p['version'], p['source']) in locked
statuses = {name: int((EVIDENCE / (name + '.status')).read_text())
            for name in ('rustc-version', 'cargo-version', 'metadata')}
assert all(status == 0 for status in statuses.values())
assert 'rustc 1.93.0 ' in (EVIDENCE / 'rustc-version.stdout').read_text()
assert 'cargo 1.93.0 ' in (EVIDENCE / 'cargo-version.stdout').read_text()
scopes = {}
for suffix in ('', '-02', '-03'):
    scope = Path((BASE / ('macos-selected-graph-evidence' + suffix + '.scope.txt')).read_text().strip())
    assert scope.is_absolute() and scope.parent == Path.home() / '.local/share/agent-builds/rhai'
    assert not scope.exists() and not scope.is_symlink()
    scopes[str(scope)] = 'absent'
candidates = []
for package_id in sorted(reachable):
    p = packages[package_id]
    targets = [t for t in p['targets'] if any(kind in ('custom-build', 'proc-macro') for kind in t['kind'])]
    if targets:
        candidates.append({'name': p['name'], 'version': p['version'],
                           'source': p['source'], 'features': nodes[package_id]['features'],
                           'targets': [{'name': t['name'], 'kind': t['kind'],
                                        'src_path': t['src_path']} for t in targets]})
maxima = json.loads((EVIDENCE / 'sampled-maxima.json').read_text())
assert maxima['storage_kib'] < contract['sampled_storage_stop_kib']
assert maxima['rss_kib'] < contract['sampled_rss_stop_kib']
assert maxima['descendants'] <= contract['descendants']
receipt = {
    'contract': contract, 'statuses': statuses, 'lock_unchanged': True,
    'package_count': len(packages), 'resolve_nodes': len(nodes),
    'workspace_members': len(metadata['workspace_members']),
    'rhai_reachable_packages': len(reachable), 'root_features': nodes[root]['features'],
    'scope_readback': scopes, 'sampled_maxima': maxima,
    'source_audit_candidates': candidates,
    'acceptance': 'Locked metadata source discovery only; conservative workspace feature union.',
    'unverified': ['Exact executed Cargo unit graph', 'Build-script/toolchain confinement',
                   'Native Darwin ABI', 'Interruption custody', 'Process measurement'],
    'attempt_history': ['01: Python 3.9 data-filter API boundary before Cargo',
                       '02: offline toml_write index boundary; tool probes passed',
                       '03: public index completion; all metadata commands passed'],
    'elapsed_seconds': {'01': 0.729404, '02': 'approximately 4 by file timestamps; not monotonic',
                        '03': 5.527903584064916},
    'resource_method': 'Periodic du/ps samples; not continuous peaks or native custody proof.',
}
(BASE / 'macos-selected-graph-root-readback.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('locked_metadata_readback=passed; packages=62; reachable=61; scope_absence=3')
