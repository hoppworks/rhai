"""Retire only detached ISO files created by this native bootstrap package."""
import hashlib
import json
from pathlib import Path
import subprocess

vm = "rhai-win11-quality"
uuid = "dc5b8fd5-1a0b-4d86-8b8f-aaa1bd492b19"
base = Path("/var/lib/libvirt/images/rhai-win11-quality")
nonce = "a7e54f39104e47c7ad826b2b9938365f"
images = {
    base / f"rhai-msrv-bootstrap-{nonce}.iso":
        "e16c3f6122cb8a28c5ba24cc4ba5b6423fa8f989094e3922d5e6f1841e34c0b6",
    base / f"rhai-msrv-bootstrap-a03-{nonce}.iso":
        "a7a3633608af61114f40978cdd37d38773982ff20ee5bc2747793baaf4914ea1",
    base / f"rhai-msrv-bootstrap-a04-{nonce}.iso":
        "6a5278548109fa6e3dfeee6245c20785f1c0d6b6ec596ed4f966b329a4100582",
}
def output(*args):
    return subprocess.check_output(args, text=True).strip()

assert output("virsh", "domuuid", vm) == uuid
domains = [name for name in output("virsh", "list", "--all", "--name").splitlines() if name]
assert vm in domains
device_readbacks = {}
for domain in domains:
    for mode in ("active", "inactive"):
        command = ["virsh", "domblklist", "--details", domain]
        if mode == "inactive":
            command.insert(2, "--inactive")
        device_readbacks[f"{domain}:{mode}"] = output(*command)
joined = "\n".join(device_readbacks.values())
expected_original = str(base / "acceptance-20261008T125846Z-b7f83433" /
                        "monitor-fixture02.iso")
expected_foreign = str(base / "work-retirement-bounds-20261009-c18e85827e6f4404.iso")
assert expected_original in device_readbacks[f"{vm}:active"]
assert expected_original in device_readbacks[f"{vm}:inactive"]
assert expected_foreign in device_readbacks[f"{vm}:active"]
assert expected_foreign in device_readbacks[f"{vm}:inactive"]
for path, expected_hash in images.items():
    assert path.parent == base and path.is_file() and not path.is_symlink()
    assert str(path) not in joined
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
    user = subprocess.run(["fuser", "-a", str(path)], capture_output=True, text=True)
    assert user.returncode == 1 and not user.stdout.strip(), (path, user)
for path in images:
    path.unlink()
assert all(not path.exists() for path in images)
record = {"vm_uuid": uuid, "domains_checked": domains,
          "original_sdc": expected_original, "foreign_sdb": expected_foreign,
          "removed_owned_images": {str(path): digest for path, digest in images.items()},
          "no_active_or_inactive_domain_reference": True,
          "no_exact_file_user_before_removal": True,
          "all_owned_images_absent_after_removal": True}
print(json.dumps(record, indent=2))
