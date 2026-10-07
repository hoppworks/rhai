# Metadata contract assertion diagnosis

## Verdict

One bounded source/test repair is sufficient before the affected readiness review. Frozen `07862c3a8ed3707956aba16f1d4bd9f66cd57cbb` is **not ready for native acceptance**. No Cargo/native/SSH action was taken here. Existing additive API compatibility and unchanged example proof remain applicable; generated metadata RED/GREEN and independent read-back remain open.

The cause is an incomplete whole-contract alignment pass, not a metadata-schema problem now. The test correctly reads `docComments`, checks every discovered overload, and uses the public Engine seam. Two literal mismatches remain:

| Requirement | Frozen source | Minimal correction |
|---|---|---|
| `io_kind`: underlying error kind, optional unit | Test requires `underlying io error kind`; getter documents `Underlying I/O error kind` | Require `underlying i/o error kind`, preserving the correct public comment and `unit` assertion. |
| Both `write_blob` overloads: socket-accepted bytes may be short | Timed `write_blob_with_timeout` comment lacks `short` | Add an accurate sentence or clause that the result may be short. Retain the assertion for both forms. |

The revised timeout helper also checks only one matching timed function. It therefore permits loss of the promised untimed form. The source currently contains every promised pair; the assertion must prove that surface rather than merely discover any remaining form.

A read-only deterministic scan of all frozen exported stream/listener/error comments plus explicit connect/listen comments found only the two mismatches above among the current concept requirements. Static signature inspection confirmed eight pairs and timed-only accept. An initial exploratory parameter regex counted `::` type paths as parameters; it was corrected to split parameter declarations at commas and read their leading identifier. The corrected signature check passed. These are source checks, not generated metadata proof or product correction attempts.

## One permissible follow-up for the existing Standard

Complete this single batch in the existing owned worktree:

1. Change the `io_kind` expected phrase to the documented `underlying i/o error kind`. Add the missing short-result statement to the timed blob-write comment. Retain every existing semantic requirement, especially zero-length immediate return versus positive-request EOF, effective requested/host/Engine caps, socket acceptance, partial progress and timeout units. No operational body change is needed.
2. Replace the existential timeout helper with expected signature assertions. For each of `read_string`, `read_blob`, `read_to_end_string`, `read_to_end_blob`, `write_string`, `write_blob`, `write_all_string`, `write_all_blob`, require exactly the two current forms below. Assert `numParams` and `params` length, ordered parameter names, and absence/presence of `timeout_ms`; then apply timed-unit comments to every timed form. Blob checks retain `no_index` gating. For `accept`, require its single two-parameter timed signature separately; do not invent an untimed accept overload. Keep common comments checked on every overload, including both handle types for `close`/`closed`.
3. Run the lightweight source preflight below on the new frozen revision and preserve its output. Have the existing combined reviewer recheck the affected test/comment delta and root helper batch before native allocation. Stop this bounded repair if the preflight still contradicts a stated contract; report the exact discrepancy rather than dropping a keyword or changing runtime behavior.

| Names | Untimed public parameters | Timed public parameters |
|---|---|---|
| `read_string`, `read_blob` | `stream`, `len` | `stream`, `len`, `timeout_ms` |
| `read_to_end_string`, `read_to_end_blob` | `stream`, `max_bytes` | `stream`, `max_bytes`, `timeout_ms` |
| `write_string`, `write_blob`, `write_all_string`, `write_all_blob` | `stream`, `value` | `stream`, `value`, `timeout_ms` |
| `accept` | No untimed form | `listener`, `timeout_ms` |

`NativeCallContext` is not a public script parameter. Actual generated metadata must still verify these expected shapes. Match only the registered TCP surface; if a same-name non-TCP entry is present, use its documented receiver/type signature to distinguish it instead of weakening the count.

## Deterministic lightweight preflight

Run this finite Python check from the owned worktree with `REV` replaced by the frozen corrected commit. It reads immutable Git objects, emits each source overload's checked concepts and public parameter names, and fails on missing concepts or pairs. Its contract values come from the existing reviewed test plus the explicit signature table above. It does not reproduce socket behavior, synthesize generated JSON, or replace the real Engine test. It is intentionally scoped to this fixed source syntax; an unrecognized format must fail rather than silently skip a registration. No permanent parser/framework is required: save this recipe/output with the existing proof preparation.

```python
import re
import subprocess

REV = "REPLACE_WITH_FROZEN_CORRECTED_REVISION"

def source(path):
    return subprocess.check_output(["git", "show", f"{REV}:{path}"], text=True)

test = source("tests/net_metadata.rs")
requirements = {}
for name, array in re.findall(
    r'require_comments\("([^"\n]+)",\s*&\[([^]]*)\]\)', test
):
    assert name not in requirements, f"duplicate explicit requirement: {name}"
    requirements[name] = re.findall(r'"([^"\n]+)"', array)

# These are the two current grouped calls; reject changed grouped syntax.
for names, concepts in [
    (["connect", "listen"], ["numeric ip address and port", "host-granted"]),
    (["shutdown_read", "shutdown_write"], ["receiving", "sending", "unit", "neterror"]),
]:
    group = ", ".join(f'"{name}"' for name in names)
    literals = ", ".join(f'"{concept}"' for concept in concepts)
    assert f'for name in [{group}]' in test
    assert f'require_comments(name, &[{literals}])' in test
    for name in names:
        requirements[name] = concepts + requirements.get(name, [])
assert test.count("require_comments(name,") == 2

records = []
pattern = (
    r'((?:(?:\s*///[^\n]*\n)|(?:\s*#\[[^\n]*\]\n))+)'
    r'(\s*pub fn (\w+)\s*\((.*?)\)\s*(?:->[^\{]*)?\{)'
)
for leaf in ["stream", "listener", "error"]:
    text = source(f"src/packages/net/{leaf}.rs")
    text = text[text.index("#[export_module]"):]
    matches = list(re.finditer(pattern, text, re.S))
    assert len(matches) == text.count("pub fn "), f"unparsed export in {leaf}"
    for match in matches:
        prefix, _, rust_name, declaration = match.groups()
        export = re.search(r'rhai_fn\(name = "([^"]+)"', prefix)
        assert export, f"unrecognized export {leaf}/{rust_name}"
        params = []
        for part in declaration.split(","):
            if part.strip():
                identifier = re.match(r'\s*(\w+)\s*:', part)
                assert identifier, f"unparsed parameter {part!r}"
                if identifier[1] != "ctx":
                    params.append(identifier[1])
        comments = " ".join(re.findall(r'///\s*(.*)', prefix)).lower()
        records.append((export[1], rust_name, params, comments))

module = source("src/packages/net/mod.rs")
for name in ["connect", "listen"]:
    comments = [line for line in re.findall(r'"/// ([^"\n]+)"', module)
                if line.startswith(name.title())]
    assert len(comments) == 1, f"unrecognized explicit metadata: {name}"
    records.append((name, name, None, comments[0].lower()))

failures = []
for name, concepts in sorted(requirements.items()):
    overloads = [record for record in records if record[0] == name]
    assert overloads, f"missing source export: {name}"
    for _, rust_name, params, comments in overloads:
        missing = [concept for concept in concepts if concept.lower() not in comments]
        print(name, rust_name, params, "missing=", missing)
        if not comments.strip() or missing:
            failures.append((name, rust_name, missing))

pairs = {
    "read_string": "len", "read_blob": "len",
    "read_to_end_string": "max_bytes", "read_to_end_blob": "max_bytes",
    "write_string": "value", "write_blob": "value",
    "write_all_string": "value", "write_all_blob": "value",
}
assert set(re.findall(r'require_timeout_overloads\(&functions, "([^"]+)"\)', test)) == set(pairs) | {"accept"}
for name, argument in pairs.items():
    actual = sorted(tuple(row[2]) for row in records if row[0] == name)
    expected = sorted([("stream", argument), ("stream", argument, "timeout_ms")])
    assert actual == expected, (name, actual, expected)
assert [row[2] for row in records if row[0] == "accept"] == [["listener", "timeout_ms"]]
for name, rust_name, params, comments in records:
    if name in set(pairs) | {"accept"} and "timeout_ms" in params:
        assert "positive timeout in milliseconds" in comments, (name, rust_name)
assert not failures, failures
print("PASS source contract alignment; generated metadata proof remains required")
```

If the helper is renamed as part of the signature correction, update only the preflight's call-inventory pattern to that concrete name. Do not change the independently expected eight pairs plus accept. Before interpreting PASS, the reviewer must confirm that the new Rust helper asserts the ordered names/counts above; this source recipe checks available source registrations, not the Rust helper's execution.

## Required native proof and root-owned work

The shared native sequence remains: fixed test bytes over accepted baseline production source give named TCP missing-comment RED; the frozen corrected production comments give named TCP GREEN and real `TCP_METADATA_JSON`; frozen assertion bytes give SYS RED specifically at the first required missing Child getter; a reviewed Child-only correction then gives SYS GREEN plus integrated TCP GREEN. Compare exported public JSON independently, including every overload/signature and its comments. Retain exact attempted revisions/archive/test/source hashes before each case, raw output, named test success/failure records and nonzero expected counts. The final Child handshake must preserve the reviewed TCP/Sys tests and prove the permitted Child-only delta. A hash of arbitrary replacement archive bytes is insufficient.

Those helper fixes belong to root and the existing consolidated reviewer; this answer does not edit or independently close them. No keyword normalization framework, broad native platform rerun, runtime redesign or new ticket hierarchy is warranted. Preserve cause `api-metadata-contract-assertions`, the two failed corrections, schema/admission/gate infrastructure history, original raw evidence and cumulative consumption. Expert diagnosis stayed within the 15-minute active planning checkpoint; exact total cost and previous cumulative active use remain unknown. One finite follow-up is recommended, with readiness and native acceptance still separate.
