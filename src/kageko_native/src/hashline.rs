// Anchor-based source-line edit engine.
//
// Each line is identified by an 8-character hex anchor derived from a SHA-256
// hash of its trimmed content.  Edits reference anchors instead of line numbers
// so they remain valid even when the file changes between edits.

use pyo3::prelude::*;
use sha2::{Digest, Sha256};

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

fn anchor(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.trim().as_bytes());
    let digest = hasher.finalize();
    hex::encode(&digest[..4]) // first 4 bytes → 8 hex chars
}

// ---------------------------------------------------------------------------
// SourceLine (exposed to Python)
// ---------------------------------------------------------------------------

#[pyclass]
#[derive(Clone, Debug)]
pub struct SourceLine {
    #[pyo3(get)]
    pub number: usize,
    #[pyo3(get)]
    pub content: String,
    #[pyo3(get)]
    pub anchor: String,
}

#[pymethods]
impl SourceLine {
    fn __repr__(&self) -> String {
        format!(
            "SourceLine(number={}, anchor='{}', content='{}')",
            self.number,
            self.anchor,
            self.content.chars().take(40).collect::<String>(),
        )
    }
}

// ---------------------------------------------------------------------------
// Edit instruction (internal)
// ---------------------------------------------------------------------------

struct EditInstruction {
    anchor: String,
    new_content: String,
}

fn parse_edit(raw: &str) -> PyResult<EditInstruction> {
    // Format:  #<ignored>|<anchor>|<new content>
    // The new-content part may be empty (means "delete the line").
    let body = raw
        .strip_prefix('#')
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("Edit must start with '#'"))?;

    let parts: Vec<&str> = body.splitn(3, '|').collect();
    if parts.len() < 2 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Edit format: #<line>|<anchor>|<new content>",
        ));
    }

    let anchor = parts[1].trim().to_owned();
    let new_content = parts.get(2).map(|s| s.to_owned()).unwrap_or("").to_owned();

    Ok(EditInstruction { anchor, new_content })
}

// ---------------------------------------------------------------------------
// HashlineEditor (exposed to Python)
// ---------------------------------------------------------------------------

#[pyclass]
pub struct HashlineEditor {
    source: String,
    lines: Vec<SourceLine>,
}

#[pymethods]
impl HashlineEditor {
    #[new]
    fn new(source: &str) -> Self {
        let lines = source
            .lines()
            .enumerate()
            .map(|(i, content)| SourceLine {
                number: i + 1,
                content: content.to_owned(),
                anchor: anchor(content),
            })
            .collect();

        HashlineEditor {
            source: source.to_owned(),
            lines,
        }
    }

    /// Return the current reconstructed source text.
    fn source(&self) -> String {
        self.source.clone()
    }

    /// Return a list of SourceLine objects.
    fn lines(&self, py: Python<'_>) -> Vec<PyObject> {
        self.lines
            .iter()
            .map(|sl| sl.clone().into_pyobject(py).unwrap().into_any().unbind())
            .collect()
    }

    /// Apply a single hashline edit string.
    ///
    /// Format: `#<line>|<anchor>|<new content>`
    ///
    /// Returns the updated full source text.
    fn apply(&mut self, edit: &str) -> PyResult<String> {
        let instr = parse_edit(edit)?;
        let idx = self.find_anchor(&instr.anchor)?;

        if instr.new_content.is_empty() {
            // delete the line
            self.lines.remove(idx);
        } else {
            self.lines[idx].content = instr.new_content.clone();
            self.lines[idx].anchor = anchor(&instr.new_content);
        }

        self.rebuild();
        Ok(self.source.clone())
    }

    /// Apply a batch of edits sequentially.
    fn apply_batch(&mut self, edits: Vec<String>) -> PyResult<String> {
        for edit in &edits {
            self.apply(edit)?;
        }
        Ok(self.source.clone())
    }
}

impl HashlineEditor {
    fn find_anchor(&self, target: &str) -> PyResult<usize> {
        self.lines
            .iter()
            .position(|sl| sl.anchor == target)
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "Anchor not found: {}",
                    target
                ))
            })
    }

    fn rebuild(&mut self) {
        self.source = self.lines.iter().map(|sl| sl.content.as_str()).collect::<Vec<_>>().join("\n");
        // Re-number
        for (i, sl) in self.lines.iter_mut().enumerate() {
            sl.number = i + 1;
        }
    }
}
