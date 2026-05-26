// In-process shell session with persistent environment.
//
// Uses std::process::Command to execute commands. Environment variables
// and working directory persist across exec calls.

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use std::collections::HashMap;
use std::process::Command;

/// Detect the best available shell. Returns (shell_name, flag).
/// Prefers a native bash (e.g. Git Bash) over WSL bash on Windows.
/// Falls back to cmd on Windows if no suitable bash is found.
fn detect_shell() -> (&'static str, &'static str) {
    // Try bash -c "echo ok" and check the output is clean UTF-8 (not WSL)
    if let Ok(output) = Command::new("bash").arg("-c").arg("echo ok").output() {
        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        // WSL bash outputs UTF-16 with null bytes in stderr; filter it out
        if output.status.success()
            && stdout.trim() == "ok"
            && !stdout.contains('\0')
            && !stderr.contains('\0')
        {
            return ("bash", "-c");
        }
    }
    ("cmd", "/C")
}

#[pyclass]
pub struct NativeShell {
    cwd: String,
    env_vars: HashMap<String, String>,
    shell: String,
    flag: String,
}

#[pymethods]
impl NativeShell {
    #[new]
    fn new() -> Self {
        let cwd = std::env::current_dir()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|_| String::from("."));

        let (shell, flag) = detect_shell();

        NativeShell {
            cwd,
            env_vars: HashMap::new(),
            shell: shell.to_string(),
            flag: flag.to_string(),
        }
    }

    fn exec(&mut self, command: &str) -> PyResult<String> {
        let shell = self.shell.clone();
        let flag = self.flag.clone();

        let mut cmd = Command::new(&shell);
        cmd.arg(&flag).arg(command);
        cmd.current_dir(&self.cwd);

        // Apply persistent environment variables
        for (key, value) in &self.env_vars {
            cmd.env(key, value);
        }

        let output = cmd
            .output()
            .map_err(|e| PyRuntimeError::new_err(format!("Failed to execute: {}", e)))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();

        // Update cwd by querying the shell after command execution
        self._update_cwd(&shell, &flag);

        let combined = if stderr.is_empty() {
            stdout.trim().to_string()
        } else {
            format!("{}\n{}", stdout, stderr).trim().to_string()
        };

        Ok(combined)
    }

    fn set_env(&mut self, key: String, value: String) {
        self.env_vars.insert(key, value);
    }

    fn get_env(&self, key: &str) -> Option<String> {
        self.env_vars.get(key).cloned()
    }

    fn get_cwd(&self) -> String {
        self.cwd.clone()
    }

    fn set_cwd(&mut self, path: String) {
        self.cwd = path;
    }
}

impl NativeShell {
    fn _update_cwd(&mut self, shell: &str, flag: &str) {
        let pwd_cmd = if shell == "cmd" { "cd" } else { "pwd" };
        if let Ok(output) = Command::new(shell)
            .arg(flag)
            .arg(pwd_cmd)
            .current_dir(&self.cwd)
            .output()
        {
            let pwd = String::from_utf8_lossy(&output.stdout).trim().to_string();
            if !pwd.is_empty() {
                self.cwd = pwd;
            }
        }
    }
}
