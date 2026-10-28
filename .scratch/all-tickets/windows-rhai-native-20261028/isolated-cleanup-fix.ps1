$ErrorActionPreference='Stop'
$path=Join-Path $PSScriptRoot 'src\packages\sys\process\windows\mod.rs'
if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne '29ff1d25532dfd3744cdfeeb7d01c94d63c6c385dad465a225fdf5b35b8f17ff'){throw 'Baseline hash mismatch'}
$old='            owner.finish_in_background();' + [char]10
$new=@'
            if catch_unwind(AssertUnwindSafe(|| owner.finish_in_background())).is_err() {
                // Preserve the exact owner, including pending I/O, Job and permit, when
                // cleanup cannot complete. Do not drop it or claim retirement after a panic.
                let mut slot = worker_cell.lock().unwrap_or_else(|poisoned| poisoned.into_inner());
                if slot.is_none() {
                    *slot = Some(owner);
                } else {
                    // An unexpected competing owner must not cause either owner to be dropped.
                    std::mem::forget(owner);
                }
                return;
            }
'@
$new += [char]10
$text=[IO.File]::ReadAllText($path); if(([regex]::Matches($text,[regex]::Escape($old))).Count -ne 1){throw 'Baseline replacement mismatch'}
$updated=$text.Replace($old,$new); [IO.File]::WriteAllText($path,$updated,[Text.UTF8Encoding]::new($false))
if((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -cne 'fa6cc93c8b5a29195823956364472b362c8edd15c17494a028dc940322024d52'){throw 'Fixed hash mismatch'}
Write-Output 'RHAI_EXACT_FIX_APPLIED baseline=29ff1d25532dfd3744cdfeeb7d01c94d63c6c385dad465a225fdf5b35b8f17ff fixed=fa6cc93c8b5a29195823956364472b362c8edd15c17494a028dc940322024d52'
