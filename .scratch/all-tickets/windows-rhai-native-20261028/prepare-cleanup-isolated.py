from pathlib import Path
import hashlib
import json
import subprocess

root = Path.cwd()
base = root / '.scratch/all-tickets/windows-rhai-native-20261028'
source = (root / 'src/packages/sys/process/windows/mod.rs').read_text()
commit = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
assert commit == '192b6af955b3b0ba0b04ff02ab01e8ddc9e5e256'
name = 'src/packages/sys/process/windows/mod.rs'
original = subprocess.check_output(['git','show',commit+':'+name], text=True)
def replace_once(text, old, new):
    assert text.count(old) == 1, old[:100]
    return text.replace(old, new)
current_begin = source.index('fn retain_for_cleanup(owner: ProcessOwner)')
current_end = source.index('\nimpl ProcessOwner {', current_begin)
base_begin = original.index('fn retain_for_cleanup(owner: ProcessOwner)')
base_end = original.index('\nimpl ProcessOwner {', base_begin)
candidate = original[:base_begin] + source[current_begin:current_end] + original[base_end:]
candidate = replace_once(candidate, '    retirement_probe: Option<Arc<child::PendingProbe>>,\n', '    retirement_probe: Option<Arc<child::PendingProbe>>,\n    #[cfg(test)]\n    retirement_panic_probe: Option<Arc<std::sync::atomic::AtomicBool>>,\n')
candidate = replace_once(candidate, '            retirement_probe: None,\n', '            retirement_probe: None,\n            #[cfg(test)]\n            retirement_panic_probe: None,\n')
hook_start = source.index('        #[cfg(test)]\n        if self.retirement_panic_probe')
hook_end = source.index('\n        // The job handle', hook_start)
candidate = replace_once(candidate, '    fn finish_in_background(&mut self) {\n', '    fn finish_in_background(&mut self) {\n' + source[hook_start:hook_end] + '\n')
test_start = source.index('    use std::os::windows::io::{FromRawHandle, OwnedHandle, RawHandle};', source.index('#[cfg(test)]\nmod tests'))
test_end = source.index('    #[test]\n    fn windows_ready_overflow_wins_over_expired_deadline()', test_start)
candidate = replace_once(candidate, '    use std::io::Write;\n\n    #[test]\n    fn windows_ready_overflow_wins_over_expired_deadline()', '    use std::io::Write;\n' + source[test_start:test_end] + '    #[test]\n    fn windows_ready_overflow_wins_over_expired_deadline()')
fix_start = candidate.index('            if catch_unwind(AssertUnwindSafe(|| owner.finish_in_background())).is_err() {')
fix_end = candidate.index('            #[cfg(test)]\n            {\n                drop(owner);', fix_start)
fix = candidate[fix_start:fix_end]
baseline = replace_once(candidate, fix, '            owner.finish_in_background();\n')
digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
before, after = digest(baseline), digest(candidate)
previous = json.loads((base/'attempt40/binding.json').read_text())
template = (base/'prepare-cleanup-panic-green.py').read_text()
template = template.replace("new = base / 'attempt45'", "new = base / 'attempt46'")
template = template.replace('import zipfile\n', 'import zipfile\nimport subprocess\n')
old = "files = sorted(json.loads((old / 'media-input/source-manifest.json').read_text())['files'])"
new = """candidates = sorted(json.loads((old / 'media-input/source-manifest.json').read_text())['files'])
def base_file(name):
    result = subprocess.run(['git','show',new_commit+':'+name], capture_output=True)
    return result.stdout if result.returncode == 0 else None
files = [name for name in candidates if base_file(name) is not None]
files.append('ApplyCleanupFix.ps1')
files.sort()
baseline = (base/'isolated-cleanup-baseline.rs').read_bytes()
fixer = (base/'isolated-cleanup-fix.ps1').read_bytes()
"""
assert old in template
template = template.replace(old,new)
template = template.replace("content = (root / name).read_bytes()", "content = baseline if name == 'src/packages/sys/process/windows/mod.rs' else fixer if name == 'ApplyCleanupFix.ps1' else base_file(name)\n        assert content is not None")
template = template.replace("previous['manifest_sha256']:file_digest(media/'source-manifest.json'),", "previous['manifest_sha256']:file_digest(media/'source-manifest.json'), 'file_count -ne 448':f'file_count -ne {len(files)}', '$actual.Count -ne 448':f'$actual.Count -ne {len(files)}', 'source_files=453':f'source_files={len(files)+5}',")
template = template.replace("str(previous['source_bytes']):str(manifest['total_source_bytes'])", "str(previous['source_bytes']):str(manifest['total_source_bytes'])")
needle = 'set RHAI_WINDOWS_CLEANUP_PANIC_WRONG_EXPECTATION=1'
assert template.count(needle) == 1
prefix = r'''"%~dp0cargo.exe" test --locked --features testing-environ,sys,metadata --lib packages::sys::process::windows::tests::windows_cleanup_panic_preserves_exact_owner_and_permit -- --exact --nocapture > baseline-red.log 2>&1
set RC=!ERRORLEVEL!
if not "!RC!"=="101" exit /b 51
findstr /C:"deliberate per-owner cleanup panic" baseline-red.log > NUL || exit /b 52
findstr /C:"cleanup worker must preserve exact owner and permit after panic" baseline-red.log > NUL || exit /b 53
findstr /C:"test result: FAILED. 0 passed; 1 failed;" baseline-red.log > NUL || exit /b 54
echo RHAI_ISOLATED_BASELINE_RED
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0ApplyCleanupFix.ps1" > fix.log 2>&1
if errorlevel 1 exit /b 55
findstr /C:"RHAI_EXACT_FIX_APPLIED" fix.log > NUL || exit /b 56
del "%~dp0ApplyCleanupFix.ps1"
if errorlevel 1 exit /b 57
echo RHAI_ISOLATED_FIX_APPLIED
'''
template = template.replace(needle,prefix+needle)
template = template.replace("@('RHAI_CLEANUP_WRONG_REJECTED'", "@('RHAI_ISOLATED_BASELINE_RED','RHAI_ISOLATED_FIX_APPLIED','RHAI_CLEANUP_WRONG_REJECTED'")
needle = "  $wrong=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\\wrong.log'))"
addition = r'''  $baseline=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\baseline-red.log'))
  $fixed=[IO.File]::ReadAllText((Join-Path $evidence[0].FullName 'runtime\fix.log'))
  foreach($line in @('deliberate per-owner cleanup panic','cleanup worker must preserve exact owner and permit after panic','test result: FAILED. 0 passed; 1 failed;')){if(!$baseline.Contains($line)){throw "Baseline RED missing: $line"}}
  if(!$fixed.Contains('RHAI_EXACT_FIX_APPLIED')){throw 'Exact isolated fix record missing.'}
'''
assert needle in template
template = template.replace(needle,addition+needle)
template = template.replace("'runtime\\wrong.log','runtime\\green.log','runtime\\pending-red.log','runtime\\pending-green.log'", "'runtime\\baseline-red.log','runtime\\fix.log','runtime\\wrong.log','runtime\\green.log','runtime\\pending-red.log','runtime\\pending-green.log'")
template = template.replace('native retained-owner GREEN and wrong control plus pending-cancellation mutant/green regression', 'isolated HEAD baseline RED, exact fix, custody wrong/green and pending mutant/green')
template = template.replace('"attempt45": "\'+nonce+\'"', '"attempt46": "\'+nonce+\'"')
(base/'isolated-cleanup-baseline.rs').write_text(baseline)
(base/'isolated-cleanup-candidate.rs').write_text(candidate)
fix_literal = fix.rstrip('\n')
ps = "$ErrorActionPreference='Stop'\n$path=Join-Path $PSScriptRoot 'src\\packages\\sys\\process\\windows\\mod.rs'\n"
ps += "if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne '"+before+"'){throw 'Baseline hash mismatch'}\n"
ps += "$old='            owner.finish_in_background();' + [char]10\n$new=@'\n"+fix_literal+"\n'@\n$new += [char]10\n"
ps += "$text=[IO.File]::ReadAllText($path); if(([regex]::Matches($text,[regex]::Escape($old))).Count -ne 1){throw 'Baseline replacement mismatch'}\n"
ps += "$updated=$text.Replace($old,$new); [IO.File]::WriteAllText($path,$updated,[Text.UTF8Encoding]::new($false))\n"
ps += "if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne '"+after+"'){throw 'Fixed hash mismatch'}\n"
ps += "Write-Output 'RHAI_EXACT_FIX_APPLIED baseline="+before+" fixed="+after+"'\n"
(base/'isolated-cleanup-fix.ps1').write_text(ps)
(base/'prepare-cleanup-isolated-generated.py').write_text(template)
print(json.dumps({'baseline_sha256':before,'fixed_sha256':after},indent=2))
