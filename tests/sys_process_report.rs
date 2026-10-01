#![cfg(feature = "sys")]

use rhai::packages::sys::{ProcessCause, ProcessDiagnostic, ProcessExit, ProcessReport, ProcessScope, SysConfig, SysError, SysPackage};
use rhai::packages::Package;
use rhai::{Engine, EvalAltResult};

fn report() -> ProcessReport {
    ProcessReport::new(
        b"hello\xff".to_vec(),
        b"warning".to_vec(),
        false,
        true,
        Some(ProcessExit::Code(7)),
        true,
        vec![ProcessDiagnostic::new("kill", Some(std::io::ErrorKind::Other), "failed once"), ProcessDiagnostic::new("reap", None, "pending")],
    )
}

#[test]
fn scope_defaults_and_builder() {
    assert_eq!(ProcessScope::default(), ProcessScope::DirectChild);
    assert_eq!(SysConfig::default().process_scope_value(), ProcessScope::DirectChild);
    assert_eq!(SysConfig::default().process_scope(ProcessScope::Managed).process_scope_value(), ProcessScope::Managed);
}

#[cfg(feature = "sync")]
#[test]
fn process_representation_is_send_sync_and_shareable() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<ProcessScope>();
    assert_send_sync::<ProcessCause>();
    assert_send_sync::<ProcessReport>();
    assert_send_sync::<ProcessExit>();
    assert_send_sync::<ProcessDiagnostic>();
    assert_send_sync::<SysError>();
    let report = std::sync::Arc::new(report());
    let reader = std::sync::Arc::clone(&report);
    assert_eq!(std::thread::spawn(move || reader.stdout()).join().unwrap(), "hello�");
}

#[test]
fn process_causes_retain_primary_classification_and_snapshot() {
    let r = report();
    let cases = [
        (
            ProcessCause::Io {
                op: "spawn",
                target: "tool".into(),
                kind: std::io::ErrorKind::NotFound,
                message: "gone".into(),
            },
            "Io",
            "NotFound",
            "spawn",
            "tool",
            "Io (NotFound): cannot spawn `tool`: gone",
        ),
        (ProcessCause::Timeout("expired".into()), "Timeout", "", "", "", "Timeout: expired"),
        (ProcessCause::OutputLimit("too much".into()), "OutputLimit", "", "", "", "OutputLimit: too much"),
    ];
    for (cause, kind, io_kind, op, target, expected) in cases {
        let error = SysError::Process { cause, report: r.clone() };
        assert_eq!(error.kind(), kind);
        assert_eq!(error.to_string(), expected);
        assert_eq!(error.clone(), error);
        let mut e = Engine::new();
        e.register_global_module(SysPackage::new(SysConfig::default()).unwrap().as_shared_module());
        e.register_fn("raise_process", move || -> Result<(), Box<EvalAltResult>> { Err(error.clone().into()) });
        let io_kind = if io_kind.is_empty() { "()".to_owned() } else { format!(r#""{io_kind}""#) };
        let op = if op.is_empty() { "()".to_owned() } else { format!(r#""{op}""#) };
        let target = if target.is_empty() { "()".to_owned() } else { format!(r#""{target}""#) };
        let diagnostics = if cfg!(feature = "no_index") {
            "err.process.cleanup_diagnostic(0).operation == \"kill\" && err.process.cleanup_diagnostic(1).operation == \"reap\""
        } else {
            "err.process.cleanup_diagnostics.len() == 2 && err.process.cleanup_diagnostics[0].operation == \"kill\" && err.process.cleanup_diagnostics[1].operation == \"reap\""
        };
        let script = format!(
            r#"let caught = false; try {{ raise_process(); }} catch (err) {{ caught = err.kind == "{kind}" && err.io_kind == {io_kind} && err.op == {op} && err.target == {target} && err.message == "{expected}" && err.process.stdout == "hello�" && err.process.stderr == "warning" && err.process.stdout_complete == false && err.process.stderr_complete && err.process.exit_code == 7 && err.process.exit_signal == () && err.process.timed_out && {diagnostics} }}; caught"#
        );
        assert!(e.eval::<bool>(&script).unwrap(), "{kind}");
    }
}

#[test]
fn process_report_rust_accessors_cover_absent_code_signal_and_diagnostics() {
    let r = report();
    assert_eq!(r.stdout(), "hello�");
    assert_eq!(r.stderr(), "warning");
    assert_eq!(r.exit_code(), Some(7));
    assert_eq!(r.exit_signal(), None);
    assert_eq!(r.cleanup_diagnostics().len(), 2);
    let absent = ProcessReport::new(vec![], vec![], true, true, None, false, vec![]);
    assert_eq!(absent.exit_code(), None);
    #[cfg(unix)]
    {
        let signaled = ProcessReport::new(vec![], vec![], true, true, Some(ProcessExit::Signal(9)), false, vec![]);
        assert_eq!(signaled.exit_signal(), Some(9));
        assert_eq!(signaled.exit_code(), None);
    }
}

#[test]
fn absent_and_signal_exit_are_readable_through_engine() {
    let mut engine = Engine::new();
    engine.register_global_module(SysPackage::new(SysConfig::default()).unwrap().as_shared_module());
    engine.register_fn("absent_report", || ProcessReport::new(vec![], vec![], true, true, None, false, vec![]));
    assert!(engine
        .eval::<bool>("absent_report().exit_code == () && absent_report().exit_signal == () && !absent_report().timed_out")
        .unwrap());
    #[cfg(unix)]
    {
        engine.register_fn("signal_report", || ProcessReport::new(vec![], vec![], true, false, Some(ProcessExit::Signal(9)), false, vec![]));
        assert!(engine
            .eval::<bool>("signal_report().exit_code == () && signal_report().exit_signal == 9 && signal_report().stdout_complete && !signal_report().stderr_complete")
            .unwrap());
    }
}

#[test]
fn prior_sys_error_variants_keep_display_and_classification() {
    let variants = [
        (SysError::Denied("no".into()), "Denied", "Denied: no"),
        (
            SysError::Io {
                op: "read",
                target: "f".into(),
                kind: std::io::ErrorKind::NotFound,
                message: "gone".into(),
            },
            "Io",
            "Io (NotFound): cannot read `f`: gone",
        ),
        (SysError::Timeout("old".into()), "Timeout", "Timeout: old"),
        (SysError::OutputLimit("old".into()), "OutputLimit", "OutputLimit: old"),
        (SysError::NotUtf8("old".into()), "NotUtf8", "NotUtf8: old"),
    ];
    for (error, kind, display) in variants {
        assert_eq!(error.kind(), kind);
        assert_eq!(error.to_string(), display);
    }
}

#[test]
fn old_error_variants_keep_rhai_classification_and_have_no_process_report() {
    let errors = vec![
        (SysError::Denied("no".into()), "Denied"),
        (
            SysError::Io {
                op: "read",
                target: "f".into(),
                kind: std::io::ErrorKind::NotFound,
                message: "gone".into(),
            },
            "Io",
        ),
        (SysError::Timeout("old".into()), "Timeout"),
        (SysError::OutputLimit("old".into()), "OutputLimit"),
        (SysError::NotUtf8("old".into()), "NotUtf8"),
    ];
    for (error, kind) in errors {
        let mut engine = Engine::new();
        engine.register_global_module(SysPackage::new(SysConfig::default()).unwrap().as_shared_module());
        engine.register_fn("raise_old", move || -> Result<(), Box<EvalAltResult>> { Err(error.clone().into()) });
        assert!(engine
            .eval::<bool>(&format!(r#"let caught = false; try {{ raise_old(); }} catch (e) {{ caught = e.kind == "{kind}" && e.process == (); }}; caught"#))
            .unwrap());
    }
}

#[cfg(not(feature = "no_index"))]
#[test]
fn script_mutating_copied_report_blobs_and_collections_does_not_change_snapshot() {
    let mut engine = Engine::new();
    engine.register_global_module(SysPackage::new(SysConfig::default()).unwrap().as_shared_module());
    engine.register_fn("report", report);
    assert!(engine.eval::<bool>(r#"let r = report(); let a = r.stdout_bytes; a[0] = 0; let d = r.cleanup_diagnostics; d[0] = (); r.stdout == "hello�" && r.stderr == "warning" && r.stdout_bytes[0] == 104 && r.cleanup_diagnostics.len() == 2 && r.cleanup_diagnostics[0].operation == "kill" && r.cleanup_diagnostics[1].operation == "reap""#).unwrap());
}

#[cfg(feature = "no_index")]
#[test]
fn no_index_keeps_scalar_and_indexed_diagnostic_access() {
    let mut engine = Engine::new();
    engine.register_global_module(SysPackage::new(SysConfig::default()).unwrap().as_shared_module());
    engine.register_fn("report", report);
    assert_eq!(engine.eval::<String>("report().stdout").unwrap(), "hello�");
    assert_eq!(engine.eval::<String>("report().cleanup_diagnostic(0).operation").unwrap(), "kill");
    assert!(engine.eval::<bool>("report().cleanup_diagnostic(99) == ()").unwrap());
}
