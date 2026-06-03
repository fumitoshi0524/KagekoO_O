// In-process shell session with persistent environment.
//
// Uses std::process::Command to execute commands. Environment variables
// persist across exec calls. Working directory is tracked by parsing
// cd / chdir / Set-Location commands (since each exec spawns a fresh process).
//
// On Windows, prefers PowerShell (pwsh/powershell) for native UTF-8 output.
// Falls back to cmd /C if no PowerShell is found.
// On Unix, uses /bin/sh -c.

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::collections::HashMap;
use std::path::Path;
use std::process::Command;

/// Detect the best available shell. Returns (shell_name, flags).
///
/// Windows: use PowerShell (pwsh.exe or powershell.exe). It has:
///   - Native UTF-8 output (no GBK/CP936 encoding problems)
///   - Full Windows PATH (uv, python, cargo, git all available)
///   - Same environment as the user's terminal
/// Fall back to cmd /C if no PowerShell is found.
///
/// Unix: always use /bin/sh -c
fn detect_shell() -> (&'static str, Vec<&'static str>) {
    #[cfg(windows)]
    {
        for exe in &["pwsh", "powershell"] {
            if Command::new(exe)
                .arg("-NoProfile").arg("-Command").arg("exit 0")
                .output()
                .map(|o| o.status.success())
                .unwrap_or(false)
            {
                return (exe, vec!["-NoProfile", "-Command"]);
            }
        }
        ("cmd", vec!["/C"])
    }
    #[cfg(not(windows))]
    {
        ("/bin/sh", vec!["-c"])
    }
}

/// Parse a potential `cd` (or `chdir`) command.
///
/// Returns `(command_to_execute, new_cwd_if_cd_detected)`.
/// For non-cd commands, new_cwd is None.
fn parse_cd(command: &str, current_cwd: &str, shell: &str, shell_is_cmd: bool) -> (String, Option<String>) {
    let trimmed = command.trim();
    let is_pwsh = shell == "pwsh" || shell == "powershell";

    let cd_prefixes: &[&str] = if shell_is_cmd {
        &["cd ", "cd\t", "CD ", "CD\t", "chdir ", "chdir\t", "CHDIR ", "CHDIR\t"]
    } else if is_pwsh {
        &["cd ", "cd\t", "CD ", "CD\t", "Set-Location ", "sl "]
    } else {
        &["cd ", "cd\t"]
    };

    let noop_cmd: String = if shell_is_cmd {
        "rem cd ok".into()
    } else if is_pwsh {
        "Write-Host 'cd ok'".into()
    } else {
        ": cd ok".into()
    };

    // Bare "cd" → home
    for bare in &["cd", "CD", "chdir", "CHDIR", "Set-Location", "sl"] {
        if trimmed == *bare {
            return (noop_cmd.clone(), Some(dirs_fallback()));
        }
    }

    for prefix in cd_prefixes {
        if trimmed.starts_with(*prefix) {
            let mut arg = trimmed[prefix.len()..].trim();

            // cmd: handle "cd /d <path>"
            if shell_is_cmd {
                if let Some(rest) = arg.strip_prefix("/d ").or_else(|| arg.strip_prefix("/D ")) {
                    arg = rest.trim();
                }
            }

            if arg == "~" {
                return (noop_cmd.clone(), Some(dirs_fallback()));
            }

            let candidate = if arg.starts_with('/') || (arg.len() >= 2 && arg.as_bytes().get(1) == Some(&b':')) {
                Path::new(arg).to_path_buf()
            } else {
                Path::new(current_cwd).join(arg)
            };

            let resolved = match candidate.canonicalize() {
                Ok(p) => p,
                Err(_) => candidate,
            };

            let new_cwd = resolved.to_string_lossy().to_string();
            let new_cwd = new_cwd.strip_prefix("\\\\?\\").unwrap_or(&new_cwd).to_string();

            if resolved.is_dir() {
                return (noop_cmd, Some(new_cwd));
            } else {
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

/// Decode raw output bytes to a string.
///
/// With PowerShell, the command is prefixed with `$OutputEncoding = [Console]::OutputEncoding = UTF8`,
/// so output is always valid UTF-8 — just use `from_utf8_lossy`.
/// With cmd, use the system ANSI codepage (matching what cmd.exe emits).
fn decode_output(bytes: &[u8], is_powershell: bool) -> String {
    if is_powershell {
        return String::from_utf8_lossy(bytes).to_string();
    }
    #[cfg(windows)]
    {
        let codepage = unsafe { windows_sys::Win32::Globalization::GetACP() } as u32;
        let s = codepage_to_string(bytes, codepage);
        if !s.is_empty() {
            return s;
        }
    }
    String::from_utf8_lossy(bytes).to_string()
}

#[cfg(windows)]
fn codepage_to_string(bytes: &[u8], codepage: u32) -> String {
    use std::ffi::OsString;
    use std::os::windows::ffi::OsStringExt;
    use windows_sys::Win32::Globalization::MultiByteToWideChar;
    use windows_sys::Win32::Globalization::MB_PRECOMPOSED;

    if bytes.is_empty() {
        return String::new();
    }

    let required = unsafe {
        MultiByteToWideChar(
            codepage,
            MB_PRECOMPOSED,
            bytes.as_ptr(),
            bytes.len() as i32,
            std::ptr::null_mut(),
            0,
        )
    };
    if required <= 0 {
        return String::new();
    }

    let mut wide: Vec<u16> = vec![0; required as usize];
    let written = unsafe {
        MultiByteToWideChar(
            codepage,
            MB_PRECOMPOSED,
            bytes.as_ptr(),
            bytes.len() as i32,
            wide.as_mut_ptr(),
            required,
        )
    };
    if written <= 0 {
        return String::new();
    }
    wide.truncate(written as usize);

    let os_str = OsString::from_wide(&wide);
    os_str.to_string_lossy().to_string()
}

#[pyclass]
pub struct NativeShell {
    cwd: String,
    env_vars: HashMap<String, String>,
    shell: String,
    flags: Vec<String>,    // split args to pass before the command
    shell_is_powershell: bool,
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

        let cwd = if Path::new(&cwd).is_dir() {
            cwd
        } else {
            dirs_fallback()
        };

        let (shell, flags) = detect_shell();
        let shell_is_powershell = shell == "pwsh" || shell == "powershell";
        let shell_is_cmd = shell == "cmd";
        let flags: Vec<String> = flags.iter().map(|s| s.to_string()).collect();

        let mut env_vars = HashMap::new();
        // Force child processes to output UTF-8.
        env_vars.insert("PYTHONIOENCODING".into(), "utf-8".into());
        env_vars.insert("PYTHONUTF8".into(), "1".into());
        env_vars.insert("LANG".into(), "en_US.UTF-8".into());
        env_vars.insert("LC_ALL".into(), "en_US.UTF-8".into());

        NativeShell {
            cwd,
            env_vars,
            shell: shell.to_string(),
            flags,
            shell_is_powershell,
            shell_is_cmd,
            last_exit_code: 0,
        }
    }

    fn exec(&mut self, command: &str, py: Python<'_>) -> PyResult<String> {
        if command.trim().is_empty() {
            return Ok(String::new());
        }

        // Parse cd commands to track working directory
        let (mut actual_command, new_cwd) = parse_cd(command, &self.cwd, &self.shell, self.shell_is_cmd);

        // Bash treats \ as escape — normalize to forward slashes.
        // PowerShell and cmd handle backslashes natively.
        if !self.shell_is_cmd && !self.shell_is_powershell {
            actual_command = actual_command.replace('\\', "/");
        }

        // PowerShell: set UTF-8 encoding so output doesn't need GBK fallback.
        if self.shell_is_powershell {
            actual_command = format!(
                "$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new(); {}",
                actual_command,
            );
        }

        // Validate cwd exists before executing
        if !Path::new(&self.cwd).is_dir() {
            self.cwd = dirs_fallback();
            if !Path::new(&self.cwd).is_dir() {
                return Err(PyRuntimeError::new_err(format!(
                    "Working directory does not exist and no fallback found: {}",
                    self.cwd
                )));
            }
        }

        let shell = self.shell.clone();
        let flags = self.flags.clone();

        let mut cmd = Command::new(&shell);
        for f in &flags {
            cmd.arg(f);
        }
        cmd.arg(&actual_command);
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

        let stdout = decode_output(&output.stdout, self.shell_is_powershell);
        let stderr = decode_output(&output.stderr, self.shell_is_powershell);
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
