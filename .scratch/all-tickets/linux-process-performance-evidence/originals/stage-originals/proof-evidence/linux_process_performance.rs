#![cfg(all(target_os = "linux", feature = "sys"))]

use rhai::packages::sys::{ProcessScope, ProgramPolicy, SysConfig, SysPackage};
use rhai::packages::Package;
use rhai::{Blob, Dynamic, Engine, Map, Scope, INT};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const START_SAMPLES: usize = 5;
const CAPTURE_SAMPLES: usize = 3;
const CAPTURE_BYTES: usize = 1_048_576;
const FIXTURE_TIMEOUT: Duration = Duration::from_secs(5);

fn engine(scope: ProcessScope) -> Engine {
    let mut engine = Engine::new();
    SysPackage::new(
        SysConfig::default()
            .programs(ProgramPolicy::AllowList(vec![
                "/bin/sh".into(),
                "/usr/bin/head".into(),
            ]))
            .default_timeout(Some(10.0))
            .max_output(CAPTURE_BYTES)
            .process_scope(scope),
    )
    .expect("construct sys package")
    .register_into_engine(&mut engine);
    engine
}

struct TempRoot {
    path: PathBuf,
    retain: bool,
}
impl TempRoot {
    fn new(label: &str) -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let retain = std::env::var_os("RHAI_PROCESS_MEASUREMENT_RECORD_DIR").is_some();
        let parent = std::env::var_os("RHAI_PROCESS_MEASUREMENT_RECORD_DIR")
            .map(PathBuf::from)
            .unwrap_or_else(std::env::temp_dir);
        fs::create_dir_all(&parent).expect("create measurement record parent");
        let path = parent.join(format!(
            "rhai-proc-measure-{}-{label}-{nonce}",
            std::process::id()
        ));
        fs::create_dir(&path).expect("create unique fixture root");
        Self { path, retain }
    }
    fn path(&self) -> &Path {
        &self.path
    }
}
impl Drop for TempRoot {
    fn drop(&mut self) {
        if !self.retain {
            let _ = fs::remove_dir_all(&self.path);
        }
    }
}

fn script_string(value: &str) -> String {
    format!(
        "\"{}\"",
        value
            .replace('\\', "\\\\")
            .replace('"', "\\\"")
            .replace('\n', "\\n")
    )
}

fn mode_order(index: usize) -> [ProcessScope; 2] {
    if index % 2 == 0 {
        [ProcessScope::DirectChild, ProcessScope::Managed]
    } else {
        [ProcessScope::Managed, ProcessScope::DirectChild]
    }
}
fn mode_name(mode: ProcessScope) -> &'static str {
    match mode {
        ProcessScope::DirectChild => "direct",
        ProcessScope::Managed => "managed",
    }
}

fn readiness(pid: u32, started: Instant, record: &Path) -> (u128, u64, i32) {
    let deadline = Instant::now() + FIXTURE_TIMEOUT;
    loop {
        let ack_path = record.with_extension("ack");
        if let (Ok(ack), Ok(text)) = (fs::read_to_string(ack_path), fs::read_to_string(record)) {
            if let (Ok(ack_pid), Ok(recorded)) =
                (ack.trim().parse::<u32>(), text.trim().parse::<u32>())
            {
                assert_eq!(
                    (recorded, ack_pid),
                    (pid, pid),
                    "OS readiness/settled ACK agrees with public Child.id"
                );
                if let Some((ticks, group)) =
                    proc_identity(pid).expect("read live fixture identity")
                {
                    return (started.elapsed().as_nanos(), ticks, group);
                }
            }
        }
        assert!(
            Instant::now() < deadline,
            "fixture readiness timed out: {}",
            record.display()
        );
        std::thread::yield_now();
    }
}

fn proc_identity(pid: u32) -> std::io::Result<Option<(u64, i32)>> {
    let raw = match fs::read_to_string(format!("/proc/{pid}/stat")) {
        Ok(raw) => raw,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error),
    };
    let close = raw.rfind(')').ok_or_else(|| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "malformed proc stat framing",
        )
    })?;
    if !raw.starts_with(&format!("{pid} ("))
        || raw.get(close + 1..close + 2).ok_or_else(|| {
            std::io::Error::new(
                std::io::ErrorKind::InvalidData,
                "truncated proc stat framing",
            )
        })? != " "
    {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "malformed proc stat identity",
        ));
    }
    let fields: Vec<_> = raw[close + 2..].split_whitespace().collect();
    if fields.len() < 20 {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "truncated proc stat fields",
        ));
    }
    let ticks = fields[19].parse().map_err(|_| {
        std::io::Error::new(std::io::ErrorKind::InvalidData, "invalid proc start ticks")
    })?;
    let group = fields[2].parse().map_err(|_| {
        std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "invalid proc process group",
        )
    })?;
    Ok(Some((ticks, group)))
}

fn checked_count<I, T>(entries: I) -> std::io::Result<usize>
where
    I: IntoIterator<Item = std::io::Result<T>>,
{
    let mut count = 0;
    for entry in entries {
        entry?;
        count += 1;
    }
    Ok(count)
}
fn count_entries(path: &str) -> std::io::Result<usize> {
    checked_count(fs::read_dir(path)?)
}
fn resource_sample(pid: u32) -> std::io::Result<(usize, usize, usize, usize)> {
    Ok((
        count_entries(&format!("/proc/{pid}/task"))?,
        count_entries(&format!("/proc/{pid}/fd"))?,
        count_entries("/proc/self/task")?,
        count_entries("/proc/self/fd")?,
    ))
}
fn group_members_from<I, S, F>(pgid: i32, entries: I, mut read_stat: F) -> std::io::Result<usize>
where
    I: IntoIterator<Item = S>,
    S: AsRef<str>,
    F: FnMut(u32) -> std::io::Result<Option<String>>,
{
    let mut count = 0;
    for name in entries {
        let name = name.as_ref();
        let Ok(pid) = name.parse::<u32>() else {
            continue;
        };
        match read_stat(pid)? {
            None => continue,
            Some(raw) => {
                let close = raw.rfind(')').ok_or_else(|| {
                    std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        "malformed proc stat framing",
                    )
                })?;
                if !raw.starts_with(&format!("{pid} ("))
                    || raw.get(close + 1..close + 2) != Some(" ")
                {
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        "proc stat PID/framing mismatch",
                    ));
                }
                let fields: Vec<_> = raw[close + 2..].split_whitespace().collect();
                if fields.len() < 3 {
                    return Err(std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        "truncated proc stat fields",
                    ));
                }
                let observed_group = fields[2].parse::<i32>().map_err(|_| {
                    std::io::Error::new(
                        std::io::ErrorKind::InvalidData,
                        "invalid proc process group",
                    )
                })?;
                if observed_group == pgid {
                    count += 1;
                }
            }
        }
    }
    Ok(count)
}
fn group_members(pgid: i32) -> std::io::Result<usize> {
    let mut names = Vec::new();
    for entry in fs::read_dir("/proc")? {
        names.push(entry?.file_name().to_string_lossy().into_owned());
    }
    group_members_from(pgid, names, |pid| {
        match fs::read_to_string(format!("/proc/{pid}/stat")) {
            Ok(raw) => Ok(Some(raw)),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
            Err(error) => Err(error),
        }
    })
}

fn wait_ready_child(
    scope: ProcessScope,
    root: &TempRoot,
    label: &str,
) -> (Engine, Scope<'static>, u32, u64, i32, u128) {
    let record = root.path().join(format!("{label}.pid"));
    let release = root.path().join(format!("{label}.release"));
    let body = format!(
        "printf '%s\\n' \"$$\" > {}.pending && mv {}.pending {} && printf '%s\\n' \"$$\" > {}; while [ ! -e {} ]; do :; done",
        script_string(&record.to_string_lossy()),
        script_string(&record.to_string_lossy()),
        script_string(&record.to_string_lossy()),
        script_string(&root.path().join(format!("{label}.ack")).to_string_lossy()),
        script_string(&release.to_string_lossy())
    );
    let program = format!("spawn(\"/bin/sh\", [\"-c\", {}])", script_string(&body));
    let engine = engine(scope);
    let started = Instant::now();
    let value = engine
        .eval::<Dynamic>(&program)
        .expect("public Engine spawn");
    let child = value
        .try_cast::<rhai::packages::sys::Child>()
        .expect("public spawn returns Child");
    let mut variables = Scope::new();
    variables.push("child", child);
    let pid = engine
        .eval_with_scope::<INT>(&mut variables, "child.id")
        .expect("public Child.id") as u32;
    let (latency, ticks, pgid) = readiness(pid, started, &record);
    (engine, variables, pid, ticks, pgid, latency)
}

fn release_and_reap(
    engine: &Engine,
    variables: &mut Scope<'_>,
    pid: u32,
    ticks: u64,
    release: &Path,
) {
    fs::write(release, b"release\n").expect("release fixture");
    let result = engine
        .eval_with_scope::<Map>(variables, "child.wait()")
        .expect("public Child.wait");
    assert!(result["success"].as_bool().expect("success field"));
    assert_eq!(result["code"].as_int().expect("code field"), 0);
    match proc_identity(pid).expect("fresh post-wait proc identity read") {
        None => {}
        Some((observed, _)) if observed == ticks => panic!("owned PID/start identity remains after public wait: pid={pid}, start={ticks}"),
        Some((observed, _)) => panic!("PID was reused before absence readback: pid={pid}, expected_start={ticks}, observed_start={observed}"),
    }
}

fn exact_capture(bytes: &[u8]) -> Result<(), &'static str> {
    if bytes.len() != CAPTURE_BYTES {
        return Err("capture length mismatch");
    }
    if bytes.iter().any(|byte| *byte != 0) {
        return Err("capture byte mismatch");
    }
    Ok(())
}
fn exact_live_identity(
    expected_pid: u32,
    expected_ticks: u64,
    observed: Option<(u64, i32)>,
) -> Result<(), &'static str> {
    if expected_pid == 0 || observed.map(|identity| identity.0) != Some(expected_ticks) {
        return Err("live PID/start identity mismatch");
    }
    Ok(())
}

fn exact_resource_snapshot(
    pid: u32,
    ticks: u64,
    observed_identity: Option<(u64, i32)>,
    child_resources: (usize, usize, usize, usize),
) -> Result<(), &'static str> {
    exact_live_identity(pid, ticks, observed_identity)?;
    if child_resources.0 == 0 || child_resources.1 == 0 {
        return Err("live child resource counts are empty");
    }
    Ok(())
}

#[test]
fn measurement_controls_reject_corruption() {
    let capture_engine = engine(ProcessScope::DirectChild);
    let capture = capture_engine
        .eval::<Map>("run_raw(\"/usr/bin/head\", [\"-c\", \"1048576\", \"/dev/zero\"])")
        .expect("public Engine byte-control capture");
    assert!(capture["success"].as_bool().expect("success field"));
    let good = capture["stdout"]
        .clone()
        .try_cast::<Blob>()
        .expect("raw capture bytes");
    exact_capture(&good).expect("real expected byte contract");
    let mut corrupt = good.clone();
    corrupt[CAPTURE_BYTES - 1] = 1;
    assert_eq!(
        exact_capture(&corrupt),
        Err("capture byte mismatch"),
        "byte-corruption control"
    );
    let root = TempRoot::new("resource-control");
    let label = "held";
    let (child_engine, mut variables, pid, ticks, _pgid, _latency) =
        wait_ready_child(ProcessScope::DirectChild, &root, label);
    let observed = proc_identity(pid).expect("independent resource-control proc read");
    let resources = resource_sample(pid).expect("read resource-control proc directories");
    exact_resource_snapshot(pid, ticks, observed, resources).expect("actual live resource receipt");
    let bad_counts = (resources.0, 0, resources.2, resources.3);
    assert_eq!(
        exact_resource_snapshot(pid, ticks, observed, bad_counts),
        Err("live child resource counts are empty"),
        "wrong-resource-count control"
    );
    let valid_stat = "700 (fixture) S 1 55".to_string();
    assert_eq!(
        group_members_from(55, ["not-a-pid", "700"], |_| Ok(Some(valid_stat.clone()))).unwrap(),
        1
    );
    assert_eq!(
        group_members_from(55, ["700"], |_| Ok(None)).unwrap(),
        0,
        "vanished proc entry is skipped"
    );
    assert!(
        group_members_from(55, ["700"], |_| Ok(Some("malformed".to_string()))).is_err(),
        "malformed census control"
    );
    assert_eq!(
        group_members_from(55, ["700"], |_| Err(std::io::Error::new(
            std::io::ErrorKind::PermissionDenied,
            "denied"
        )))
        .unwrap_err()
        .kind(),
        std::io::ErrorKind::PermissionDenied,
        "unreadable census control"
    );
    assert!(
        checked_count(vec![
            Ok::<_, std::io::Error>(()),
            Err(std::io::Error::new(
                std::io::ErrorKind::Other,
                "entry failed"
            ))
        ])
        .is_err(),
        "resource directory iteration error control"
    );
    eprintln!("PERF_CONTROL,kind=proc-census,malformed_rejected=true,unreadable_rejected=true,vanished_skipped=true,entry_error_rejected=true");
    eprintln!("PERF_CONTROL,kind=byte-integrity,captures=1,corrupted_copy_rejected=true");
    eprintln!("PERF_CONTROL,kind=resource-count,live_fixtures=1,zero_descriptor_control_rejected=true,pid={pid},start_ticks={ticks}");
    release_and_reap(
        &child_engine,
        &mut variables,
        pid,
        ticks,
        &root.path().join("held.release"),
    );
}

#[test]
#[ignore = "bounded native Linux Direct/Managed measurements; run only after independent source review and fresh admission"]
fn direct_managed_measurements() {
    assert_eq!(
        mode_order(0),
        [ProcessScope::DirectChild, ProcessScope::Managed]
    );
    assert_eq!(
        mode_order(1),
        [ProcessScope::Managed, ProcessScope::DirectChild]
    );
    let root = TempRoot::new("measurements");

    for index in 0..START_SAMPLES {
        for mode in mode_order(index) {
            let label = format!("start-{index}-{}", mode_name(mode));
            let (engine, mut variables, pid, ticks, pgid, latency_ns) =
                wait_ready_child(mode, &root, &label);
            eprintln!("PERF_START,index={index},mode={},order={}>{},pid={pid},start_ticks={ticks},pgid={pgid},ready_latency_ns={latency_ns}", mode_name(mode), mode_name(mode_order(index)[0]), mode_name(mode_order(index)[1]));
            release_and_reap(
                &engine,
                &mut variables,
                pid,
                ticks,
                &root.path().join(format!("{label}.release")),
            );
        }
    }

    for index in 0..CAPTURE_SAMPLES {
        for mode in mode_order(index) {
            let engine = engine(mode);
            let started = Instant::now();
            let result = engine
                .eval::<Map>("run_raw(\"/usr/bin/head\", [\"-c\", \"1048576\", \"/dev/zero\"])")
                .expect("public Engine captured run");
            let elapsed_ns = started.elapsed().as_nanos();
            assert!(result["success"].as_bool().expect("success field"));
            assert_eq!(result["code"].as_int().expect("status field"), 0);
            assert!(result["stdout_complete"].as_bool().expect("complete field"));
            assert!(result["stderr_complete"]
                .as_bool()
                .expect("stderr complete field"));
            let output = result["stdout"]
                .clone()
                .try_cast::<Blob>()
                .expect("raw output bytes");
            exact_capture(&output).expect("capture contract");
            let stderr = result["stderr"]
                .clone()
                .try_cast::<Blob>()
                .expect("raw stderr bytes");
            assert!(stderr.is_empty(), "capture fixture must not emit stderr");
            let bytes_per_second = (CAPTURE_BYTES as f64) * 1_000_000_000.0 / elapsed_ns as f64;
            eprintln!("PERF_CAPTURE,index={index},mode={},order={}>{},bytes={},captured_run_elapsed_ns={elapsed_ns},captured_run_bytes_per_second={bytes_per_second:.3}", mode_name(mode), mode_name(mode_order(index)[0]), mode_name(mode_order(index)[1]), output.len());
        }
    }

    for mode in [ProcessScope::DirectChild, ProcessScope::Managed] {
        let label = format!("held-{}", mode_name(mode));
        let baseline = resource_sample(std::process::id()).expect("read baseline proc directories");
        let (engine, mut variables, pid, ticks, pgid, latency_ns) =
            wait_ready_child(mode, &root, &label);
        let live_identity = proc_identity(pid)
            .expect("fresh held fixture proc read")
            .expect("held fixture remains live at observation");
        let child_resources = resource_sample(pid).expect("read held child proc directories");
        exact_resource_snapshot(pid, ticks, Some(live_identity), child_resources)
            .expect("actual held resource snapshot");
        let held_host_resources =
            resource_sample(std::process::id()).expect("read live host proc directories");
        let group_count = group_members(pgid).expect("complete process-group census");
        if mode == ProcessScope::Managed {
            assert_eq!(
                pgid, pid as i32,
                "managed scope owns a dedicated process group"
            );
            assert_eq!(
                group_count, 1,
                "managed fixture is the sole live member of its process group"
            );
        }
        eprintln!("PERF_RESOURCE,sample_index=0,order=direct>managed,mode={},pid={pid},start_ticks={ticks},pgid={pgid},live_ready_latency_ns={latency_ns},child_threads={},child_fds={},host_threads_before={},host_fds_before={},host_threads_live={},host_fds_live={},group_members={},group_members_owned={}", mode_name(mode), child_resources.0, child_resources.1, baseline.2, baseline.3, held_host_resources.2, held_host_resources.3, group_count, mode == ProcessScope::Managed);
        release_and_reap(
            &engine,
            &mut variables,
            pid,
            ticks,
            &root.path().join(format!("{label}.release")),
        );
        drop(variables);
        drop(engine);
        let after = resource_sample(std::process::id()).expect("read post-close proc directories");
        eprintln!(
            "PERF_RESOURCE_CLOSED,mode={},host_threads_after={},host_fds_after={},host_threads_delta={},host_fds_delta={}",
            mode_name(mode),
            after.2,
            after.3,
            after.2 as isize - baseline.2 as isize,
            after.3 as isize - baseline.3 as isize
        );
    }
}
