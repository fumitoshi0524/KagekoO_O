// In-process shell session with persistent environment.
//
// Uses std::process::Command to execute commands. Environment variables
// persist across exec calls. Working directory is tracked by parsing
// cd / chdir commands (since each exec spawns a fresh process).
//
// On Windows, prefers Git Bash / MSYS2 bash if available, falls back to cmd.

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

/// Detect the best available shell. Returns (shell_name, flag).
///
/// Strategy on Windows:
///   1. Try `bash` (Git Bash / MSYS2) — validate with a quick echo test
///   2. Fall back to `cmd /C`
/// Strategy on Unix:
///   1. Always use /bin/sh
fn detect_shell() -> (&'static str, &'static str) {
    #[cfg(windows)]
    {
        // Try bash, but filter out WSL bash (which produces garbled output)
        if let Ok(output) = Command::new("bash").arg("-c").arg("echo ok").output() {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            if output.status.success()
                && stdout.trim() == "ok"
                && !stdout.contains('\0')
                && !stderr.contains('\0')
                && stderr.trim().is_empty()
            {
                return ("bash", "-c");
            }
        }
        ("cmd", "/C")
    }
    #[cfg(not(windows))]
    {
        ("/bin/sh", "-c")
    }
}

/// Parse a potential `cd` (or `chdir`) command.
///
/// Returns `(command_to_execute, new_cwd_if_cd_detected)`.
/// For non-cd commands, new_cwd is None.
fn parse_cd(command: &str, current_cwd: &str, shell_is_cmd: bool) -> (String, Option<String>) {
    let trimmed = command.trim();

    // cd on both bash and cmd; chdir is cmd-specific
    let cd_prefixes: &[&str] = if shell_is_cmd {
        &["cd ", "cd\t", "CD ", "CD\t", "chdir ", "chdir\t", "CHDIR ", "CHDIR\t"]
    } else {
        &["cd ", "cd\t"]
    };

    // Handle bare "cd" / "CD" / "chdir"
    for bare in ["cd", "CD", "chdir", "CHDIR"] {
        if trimmed == bare {
            let home = dirs_fallback();
            let noop = if shell_is_cmd { String::from("rem cd ok") } else { String::from(": cd ok") };
            return (noop, Some(home));
        }
    }

    for prefix in cd_prefixes {
        if trimmed.starts_with(*prefix) {
            let mut arg = trimmed[prefix.len()..].trim();

            // Handle cmd's "cd /d <path>" flag (change drive + directory)
            if shell_is_cmd {
                if let Some(rest) = arg.strip_prefix("/d ").or_else(|| arg.strip_prefix("/D ")) {
                    arg = rest.trim();
                }
            }

            // "cd ~" → home directory
            if arg == "~" {
                let home = dirs_fallback();
                let noop = if shell_is_cmd { String::from("rem cd ok") } else { String::from(": cd ok") };
                return (noop, Some(home));
            }

            // Resolve the new path: join with cwd, then canonicalize
            let candidate = if arg.starts_with('/') || (arg.len() >= 2 && arg.as_bytes().get(1) == Some(&b':')) {
                // Absolute path
                Path::new(arg).to_path_buf()
            } else {
                // Relative path
                Path::new(current_cwd).join(arg)
            };

            // Try to canonicalize (resolves .. and .); fall back to the joined path
            let resolved = match candidate.canonicalize() {
                Ok(p) => p,
                Err(_) => candidate, // doesn't exist yet — let the shell report the error
            };

            // Strip Windows extended-path prefix (\\?\) if present
            let new_cwd = resolved.to_string_lossy().to_string();
            let new_cwd = new_cwd.strip_prefix("\\\\?\\").unwrap_or(&new_cwd).to_string();

            if resolved.is_dir() {
                let noop = if shell_is_cmd { String::from("rem cd ok") } else { String::from(": cd ok") };
                return (noop, Some(new_cwd));
            } else {
                // Directory doesn't exist — let the shell execute the original command
                // and report the error, but DON'T change cwd
                return (command.to_string(), None);
            }
        }
    }

    (command.to_string(), None)
}

/// Fallback home directory detection.
fn dirs_fallback() -> String {
    #[cfg(windows)]
    {
        std::env::var("USERPROFILE")
            .or_else(|_| std::env::var("HOMEDRIVE").map(|hd| {
                let hp = std::env::var("HOMEPATH").unwrap_or_default();
                format!("{}{}", hd, hp)
            }))
            .unwrap_or_else(|_| String::from("C:\\"))
    }
    #[cfg(not(windows))]
    {
        std::env::var("HOME").unwrap_or_else(|_| String::from("/"))
    }
}

#[pyclass]
pub struct NativeShell {
    cwd: String,
    env_vars: HashMap<String, String>,
    shell: String,
    flag: String,
    shell_is_cmd: bool,
    last_exit_code: i32,
}

#[pymethods]
impl NativeShell {
    #[new]
    fn new() -> Self {
        let cwd = std::env::current_dir()
            .map(|p| p.to_string_lossy().to_string())
            .unwrap_or_else(|_| String::from("."));

        // Validate that cwd exists; if not, fall back to home
        let cwd = if Path::new(&cwd).is_dir() {
            cwd
        } else {
            dirs_fallback()
        };

        let (shell, flag) = detect_shell();
        let shell_is_cmd = shell == "cmd";

        NativeShell {
            cwd,
            env_vars: HashMap::new(),
            shell: shell.to_string(),
            flag: flag.to_string(),
            shell_is_cmd,
            last_exit_code: 0,
        }
    }

    fn exec(&mut self, command: &str, py: Python<'_>) -> PyResult<String> {
        if command.trim().is_empty() {
            return Ok(String::new());
        }

        // Parse cd commands to track working directory
        let (actual_command, new_cwd) = parse_cd(command, &self.cwd, self.shell_is_cmd);

        // Validate cwd exists before executing
        if !Path::new(&self.cwd).is_dir() {
            // Reset cwd to a safe fallback
            self.cwd = dirs_fallback();
            if !Path::new(&self.cwd).is_dir() {
                return Err(PyRuntimeError::new_err(format!(
                    "Working directory does not exist and no fallback found: {}",
                    self.cwd
                )));
            }
        }

        let shell = self.shell.clone();
        let flag = self.flag.clone();

        let mut cmd = Command::new(&shell);
        cmd.arg(&flag).arg(&actual_command);
        cmd.current_dir(&self.cwd);

        // Apply persistent environment variables
        for (key, value) in &self.env_vars {
            cmd.env(key, value);
        }

        let output = py
            .allow_threads(|| cmd.output())
            .map_err(|e| PyRuntimeError::new_err(format!(
                "Failed to execute: {} (cwd: {})",
                e, self.cwd
            )))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        self.last_exit_code = output.status.code().unwrap_or(-1);

        // Update cwd if a cd command was detected and parsed
        if let Some(cwd) = new_cwd {
            self.cwd = cwd;
        }

        let combined = if stderr.is_empty() {
            stdout.trim().to_string()
        } else if stdout.is_empty() {
            stderr.trim().to_string()
        } else {
            format!("{}\n{}", stdout.trim(), stderr.trim())
        };

        if combined.is_empty() {
            Ok(String::from("(no output)"))
        } else {
            Ok(combined)
        }
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
        let p = if path.starts_with('~') {
            path.replacen('~', &dirs_fallback(), 1)
        } else {
            path
        };
        if Path::new(&p).is_dir() {
            self.cwd = p;
        }
    }

    fn get_last_exit_code(&self) -> i32 {
        self.last_exit_code
    }
}
