//! Environment functions of the `sys` package.

use super::error::SysError;
use super::{reg, SysState};
use crate::{Dynamic, EvalAltResult, Map, Module, Shared};

pub(super) fn register(module: &mut Module, state: &Shared<SysState>) {
    let st = state.clone();
    reg(
        "env_var",
        &[
            "/// Return the value of an environment variable, or `()` when it is unset or not",
            "/// visible under the host policy.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// let home = env_var(\"HOME\");",
            "///",
            "/// if home == () { print(\"HOME is not set or not allowed\"); }",
            "/// ```",
        ],
    )
    .set_into_module(module, move |name: &str| -> Dynamic {
        if !st.config.env.allows(name) {
            return Dynamic::UNIT;
        }
        match std::env::var(name) {
            Ok(value) => value.into(),
            Err(..) => Dynamic::UNIT,
        }
    });

    let st = state.clone();
    reg(
        "env_vars",
        &[
            "/// Return every environment variable visible under the host policy as an object map.",
            "///",
            "/// # Example",
            "///",
            "/// ```rhai",
            "/// for name in env_vars().keys() { print(name); }",
            "/// ```",
        ],
    )
    .set_into_module(module, move || -> Map {
        let mut map = Map::new();
        for (name, value) in std::env::vars_os() {
            let Ok(name) = name.into_string() else {
                continue;
            };
            if !st.config.env.allows(&name) {
                continue;
            }
            let Ok(value) = value.into_string() else {
                continue;
            };
            map.insert(name.into(), value.into());
        }
        map
    });

    reg(
        "cwd",
        &["/// Return the current working directory of the host process."],
    )
    .set_into_module(module, move || -> Result<String, Box<EvalAltResult>> {
        let dir =
            std::env::current_dir().map_err(|e| SysError::io("get current directory", ".", &e))?;
        dir.into_os_string()
            .into_string()
            .map_err(|s| SysError::NotUtf8(format!("current directory {s:?}")).into())
    });
}
