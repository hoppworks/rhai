//! Bounded companion for the frozen zero-input Managed I/O stress fixture.
//! This file is copied into the private source tree only for the setup control.
use std::env;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;

use rhai::packages::sys::{ProcessScope, ProgramPolicy, SysConfig, SysPackage};
use rhai::packages::Package;
use rhai::{Engine, Map};

fn quote(value: &str) -> String {
    format!("{value:?}")
}

fn write_once(path: &Path, contents: &str) -> Result<(), Box<dyn std::error::Error>> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(contents.as_bytes())?;
    file.sync_all()?;
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 6 {
        return Err("expected fixture, readiness, fixture record, completion, and capture receipt paths".into());
    }
    let fixture = &args[1];
    let ready = Path::new(&args[2]);
    let fixture_record = &args[3];
    let complete = Path::new(&args[4]);
    let _capture_progress = Path::new(&args[5]);
    let host_pid = std::process::id();

    let config = SysConfig::default()
        .programs(ProgramPolicy::AllowList(vec![fixture.clone()]))
        .max_output(8 * 1024 * 1024)
        .default_timeout(Some(6.0))
        .process_scope(ProcessScope::Managed);
    let mut engine = Engine::new();
    SysPackage::new(config)?.register_into_engine(&mut engine);
    let script = format!(
        "run_raw({}, [\"--exact\", \"process_fixture\", \"--nocapture\", \"--quiet\"], #{{ env_clear: true, env: #{{ RHAI_SYS_PROCESS_FIXTURE: \"0\", RHAI_SYS_PROCESS_FIXTURE_RECORD: {}, RHAI_SYS_PROCESS_IO_STRESS: \"1\", RHAI_SYS_PROCESS_IO_BYTES: \"0\", RHAI_SYS_PROCESS_STDOUT_BYTES: \"8388592\", RHAI_SYS_PROCESS_STDERR_BYTES: \"8388608\" }}, stdin: \"\", max_output: 8388608, timeout: 6.0 }})",
        quote(fixture), quote(fixture_record));

    // This marker only brackets entry into eval. The public API exposes stream
    // bytes after completion, so it cannot provide the live per-stream progress
    // receipt required by the adapter. No capture-progress receipt is fabricated.
    write_once(ready, &format!(
        "{{\"schema\":1,\"host_pid\":{host_pid},\"stage\":\"managed-run-entering\"}}\n"))?;
    let result: Map = engine.eval(&script)?;
    let stdout_complete = result.get("stdout_complete").and_then(|v| v.as_bool().ok()) == Some(true);
    let stderr_complete = result.get("stderr_complete").and_then(|v| v.as_bool().ok()) == Some(true);
    let exit_code = result.get("exit_code").and_then(|v| v.as_int().ok()) == Some(0);
    if !(stdout_complete && stderr_complete && exit_code) {
        return Err("Managed fixture did not complete with both captured streams".into());
    }
    write_once(complete, "managed-capture-complete\n")?;
    Ok(())
}
