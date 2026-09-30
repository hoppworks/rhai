//! Demonstrates a confined streaming file handle through the `sys` package.

use rhai::packages::sys::{FsAccess, SysConfig, SysPackage};
use rhai::packages::Package;
use rhai::{Engine, Scope};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

static NEXT_DIRECTORY: AtomicU64 = AtomicU64::new(0);

struct TemporaryDirectory(PathBuf);

impl TemporaryDirectory {
    fn create() -> io::Result<Self> {
        loop {
            let id = NEXT_DIRECTORY.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir().join(format!(
                "rhai-sys-example-{}-{id}",
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

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let directory = TemporaryDirectory::create()?;
    let file_path = directory.path().join("notes.txt");
    fs::write(&file_path, "existing data")?;

    let config = SysConfig::default().fs_root(directory.path(), FsAccess::ReadWrite);
    let package = SysPackage::new(config)?;
    let mut engine = Engine::new();
    package.register_into_engine(&mut engine);

    let mut scope = Scope::new();
    scope.push(
        "path",
        file_path
            .to_str()
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidData, "temporary path is not UTF-8"))?
            .to_owned(),
    );
    let output = engine.eval_with_scope::<String>(
        &mut scope,
        r#"
            let file = open_file(path, "r+");
            file.seek(0);
            let written = file.write("Rhai");
            file.seek(0);
            let output = file.read_string(4);
            if written != 4 { throw "short write"; }
            output
        "#,
    )?;

    assert_eq!(output, "Rhai");
    let host_contents = fs::read_to_string(&file_path)?;
    assert_eq!(host_contents, "Rhaiting data");
    println!("Script read {output}; host file now contains {host_contents:?}.");

    Ok(())
}
