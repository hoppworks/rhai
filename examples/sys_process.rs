//! Demonstrates allowlisted child processes and shared wait results through `sys`.

#[cfg(unix)]
mod unix_example {
    use rhai::packages::sys::{Child, ProgramPolicy, SysConfig, SysPackage};
    use rhai::packages::Package;
    use rhai::{Dynamic, Engine, Map, Scope, INT};
    use std::fs;
    use std::io;
    use std::path::{Path, PathBuf};
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::thread;
    use std::time::{Duration, Instant};

    const MODE: &str = "RHAI_SYS_PROCESS_EXAMPLE_MODE";
    const DIRECTORY: &str = "RHAI_SYS_PROCESS_EXAMPLE_DIRECTORY";
    static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

    struct TemporaryDirectory(PathBuf);

    impl TemporaryDirectory {
        fn create() -> io::Result<Self> {
            loop {
                let id = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
                let path = std::env::temp_dir().join(format!(
                    "rhai-sys-process-example-{}-{id}",
                    std::process::id()
                ));
                match fs::create_dir(&path) {
                    Ok(()) => return Ok(Self(path)),
                    Err(error) if error.kind() == io::ErrorKind::AlreadyExists => continue,
                    Err(error) => return Err(error),
                }
            }
        }

        fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TemporaryDirectory {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }

    fn child_fixture() -> Result<Option<i32>, Box<dyn std::error::Error>> {
        let Ok(mode) = std::env::var(MODE) else {
            return Ok(None);
        };
        let directory = PathBuf::from(std::env::var(DIRECTORY)?);
        let code = match mode.as_str() {
            "run" => {
                fs::write(
                    directory.join("run-effect.txt"),
                    "run child wrote its record\n",
                )?;
                println!("run child output");
                7
            }
            "spawn" => {
                let ready_path = directory.join("spawn-ready.txt");
                let ready_temporary = directory.join("spawn-ready.tmp");
                fs::write(
                    &ready_temporary,
                    format!("pid={} ready\n", std::process::id()),
                )?;
                fs::rename(&ready_temporary, &ready_path)?;
                let deadline = Instant::now() + Duration::from_secs(5);
                while !directory.join("release-child").is_file() {
                    if Instant::now() >= deadline {
                        eprintln!("parent did not release the example child before its deadline");
                        return Ok(Some(70));
                    }
                    thread::sleep(Duration::from_millis(10));
                }
                fs::write(
                    directory.join("spawn-effect.txt"),
                    "spawn child observed release\n",
                )?;
                println!("spawn child output");
                0
            }
            _ => return Err(format!("unknown child fixture mode: {mode}").into()),
        };
        Ok(Some(code))
    }

    fn child_options(mode: &str) -> String {
        format!(
            "#{{ env_clear: true, env: #{{ \"{MODE}\": \"{mode}\", \"{DIRECTORY}\": directory }} }}"
        )
    }

    fn child_call(
        engine: &Engine,
        child: &Child,
        expression: &str,
    ) -> Result<Dynamic, Box<dyn std::error::Error>> {
        let mut scope = Scope::new();
        scope.push_dynamic("child", Dynamic::from(child.clone()));
        Ok(engine.eval_with_scope::<Dynamic>(&mut scope, expression)?)
    }

    fn child_id(engine: &Engine, child: &Child) -> Result<INT, Box<dyn std::error::Error>> {
        let mut scope = Scope::new();
        scope.push_dynamic("child", Dynamic::from(child.clone()));
        Ok(engine.eval_with_scope::<INT>(&mut scope, "child.id")?)
    }

    fn field_bool(map: &Map, name: &str) -> bool {
        map.get(name)
            .unwrap_or_else(|| panic!("process result omitted {name}"))
            .clone()
            .cast::<bool>()
    }

    fn field_int(map: &Map, name: &str) -> INT {
        map.get(name)
            .unwrap_or_else(|| panic!("process result omitted {name}"))
            .clone()
            .cast::<INT>()
    }

    fn field_optional_int(map: &Map, name: &str) -> Option<INT> {
        let value = map
            .get(name)
            .unwrap_or_else(|| panic!("process result omitted {name}"))
            .clone();
        if value.is_unit() {
            None
        } else {
            Some(value.cast::<INT>())
        }
    }

    fn field_string(map: &Map, name: &str) -> String {
        map.get(name)
            .unwrap_or_else(|| panic!("process result omitted {name}"))
            .clone()
            .cast::<String>()
    }

    fn assert_same_process_result(left: &Map, right: &Map) {
        for name in ["success", "timed_out", "stdout_complete", "stderr_complete"] {
            assert_eq!(
                field_bool(left, name),
                field_bool(right, name),
                "cached {name} field differs"
            );
        }
        for name in ["code", "signal"] {
            assert_eq!(
                field_optional_int(left, name),
                field_optional_int(right, name),
                "cached {name} field differs"
            );
        }
        for name in ["stdout", "stderr"] {
            assert_eq!(
                field_string(left, name),
                field_string(right, name),
                "cached {name} field differs"
            );
        }
    }

    fn wait_until_complete(
        engine: &Engine,
        child: &Child,
        deadline: Instant,
    ) -> Result<Map, Box<dyn std::error::Error>> {
        loop {
            let result = child_call(engine, child, "child.wait(0.0)")?;
            if !result.is_unit() {
                return Ok(result.cast::<Map>());
            }
            if Instant::now() >= deadline {
                return Err("child did not finish before the host deadline".into());
            }
            thread::sleep(Duration::from_millis(10));
        }
    }

    struct ChildCleanup<'a> {
        engine: &'a Engine,
        child: Child,
        release: PathBuf,
        finished: bool,
    }

    impl Drop for ChildCleanup<'_> {
        fn drop(&mut self) {
            if self.finished {
                return;
            }
            let _ = fs::write(&self.release, "release during host cleanup\n");
            let _ = child_call(self.engine, &self.child, "child.kill()");
            let deadline = Instant::now() + Duration::from_secs(2);
            while Instant::now() < deadline {
                match child_call(self.engine, &self.child, "child.wait(0.0)") {
                    Ok(value) if !value.is_unit() => return,
                    Err(_) => return,
                    _ => thread::sleep(Duration::from_millis(10)),
                }
            }
            eprintln!("bounded cleanup did not observe a terminal child result");
        }
    }

    fn run_example() -> Result<(), Box<dyn std::error::Error>> {
        let directory = TemporaryDirectory::create()?;
        let executable = std::env::current_exe()?;
        let executable = executable
            .to_str()
            .ok_or_else(|| {
                io::Error::new(io::ErrorKind::InvalidData, "executable path is not UTF-8")
            })?
            .to_owned();
        let program = executable.clone();
        let mut scope = Scope::new();
        scope.push("program", executable);
        scope.push(
            "directory",
            directory
                .path()
                .to_str()
                .ok_or_else(|| {
                    io::Error::new(io::ErrorKind::InvalidData, "temporary path is not UTF-8")
                })?
                .to_owned(),
        );

        let package = SysPackage::new(
            SysConfig::default()
                .programs(ProgramPolicy::AllowList(vec![program]))
                .default_timeout(Some(4.0))
                .max_output(1024),
        )?;
        let mut engine = Engine::new();
        package.register_into_engine(&mut engine);

        let run_options = child_options("run");
        let run_result =
            engine.eval_with_scope::<Map>(&mut scope, &format!("run(program, {run_options})"))?;
        let run_effect = fs::read_to_string(directory.path().join("run-effect.txt"))?;
        let run_code = field_int(&run_result, "code");
        let expected_run_code = std::env::var("RHAI_SYS_PROCESS_EXAMPLE_EXPECTED_EXIT")
            .ok()
            .and_then(|value| value.parse::<INT>().ok())
            .unwrap_or(7);

        let spawn_options = child_options("spawn");
        let child = engine
            .eval_with_scope::<Child>(&mut scope, &format!("spawn(program, {spawn_options})"))?;
        let sibling = child.clone();
        let release = directory.path().join("release-child");
        let mut cleanup = ChildCleanup {
            engine: &engine,
            child: child.clone(),
            release: release.clone(),
            finished: false,
        };
        let child_id = child_id(&engine, &child)?;

        let ready_path = directory.path().join("spawn-ready.txt");
        let ready_deadline = Instant::now() + Duration::from_secs(3);
        while !ready_path.is_file() {
            if Instant::now() >= ready_deadline {
                return Err("spawn fixture did not publish readiness".into());
            }
            thread::sleep(Duration::from_millis(10));
        }
        let ready = fs::read_to_string(&ready_path)?;
        let ready_pid = ready
            .split_whitespace()
            .find_map(|part| part.strip_prefix("pid="))
            .ok_or("spawn fixture readiness record has no PID")?
            .parse::<INT>()?;
        assert_eq!(ready_pid, child_id, "host observed the exact spawned child");
        let early = child_call(&engine, &sibling, "child.wait(0.0)")?;
        assert!(
            early.is_unit(),
            "the child is pending while it awaits release"
        );

        fs::write(&release, "release\n")?;
        let spawn_result =
            wait_until_complete(&engine, &child, Instant::now() + Duration::from_secs(3))?;
        let repeated_result =
            wait_until_complete(&engine, &sibling, Instant::now() + Duration::from_secs(1))?;
        cleanup.finished = true;

        let spawn_effect = fs::read_to_string(directory.path().join("spawn-effect.txt"))?;
        assert_same_process_result(&spawn_result, &repeated_result);
        assert!(field_bool(&spawn_result, "success"));
        assert_eq!(field_int(&spawn_result, "code"), 0);
        assert!(field_bool(&spawn_result, "stdout_complete"));
        assert!(field_bool(&spawn_result, "stderr_complete"));
        assert_eq!(
            field_string(&spawn_result, "stdout"),
            "spawn child output\n"
        );
        assert_eq!(field_string(&spawn_result, "stderr"), "");
        assert!(!field_bool(&spawn_result, "timed_out"));

        println!("Host read back run child record: {run_effect:?}");
        println!("Host read back spawned child record: {spawn_effect:?} (pid {ready_pid})");
        println!("Spawn wait was pending, then both cloned handles returned the same result.");

        assert_eq!(field_bool(&run_result, "success"), false);
        assert_eq!(run_code, 7, "nonzero run exit is returned as data");
        assert_eq!(field_bool(&run_result, "timed_out"), false);
        assert!(field_bool(&run_result, "stdout_complete"));
        assert!(field_bool(&run_result, "stderr_complete"));
        assert_eq!(field_string(&run_result, "stdout"), "run child output\n");
        assert_eq!(field_string(&run_result, "stderr"), "");
        assert_eq!(run_effect, "run child wrote its record\n");
        assert_eq!(spawn_effect, "spawn child observed release\n");
        assert_eq!(
            run_code, expected_run_code,
            "RED control changes only the expected exit"
        );
        Ok(())
    }

    pub(super) fn main() -> Result<(), Box<dyn std::error::Error>> {
        if let Some(status) = child_fixture()? {
            std::process::exit(status);
        }
        run_example()
    }
}

#[cfg(unix)]
fn main() -> Result<(), Box<dyn std::error::Error>> {
    unix_example::main()
}

#[cfg(not(unix))]
fn main() {
    eprintln!("The sys process example requires a Unix target and the `sys` feature.");
}
