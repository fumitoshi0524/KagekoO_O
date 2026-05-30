use grep_regex::RegexMatcher;
use grep_searcher::sinks::UTF8;
use grep_searcher::SearcherBuilder;
use pyo3::prelude::*;
use std::path::Path;

#[pyclass]
#[derive(Clone)]
pub struct GrepMatch {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub line_number: u64,
    #[pyo3(get)]
    pub line: String,
}

/// In-process grep using ripgrep internals. No subprocess spawned.
#[pyfunction]
#[pyo3(signature = (pattern, path, max_results=None))]
pub fn ripgrep(
    pattern: &str,
    path: &str,
    max_results: Option<usize>,
) -> PyResult<Vec<GrepMatch>> {
    let matcher = RegexMatcher::new(pattern).map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Invalid regex: {}", e))
    })?;

    let max = max_results.unwrap_or(100);
    let mut matches = Vec::new();
    let search_path = Path::new(path);

    if search_path.is_file() {
        search_file(&matcher, search_path, &mut matches, max)?;
    } else if search_path.is_dir() {
        for entry in walkdir::WalkDir::new(search_path)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            if entry.file_type().is_file() {
                if matches.len() >= max {
                    break;
                }
                let _ = search_file(&matcher, entry.path(), &mut matches, max);
            }
        }
    }

    Ok(matches)
}

fn search_file(
    matcher: &RegexMatcher,
    path: &Path,
    matches: &mut Vec<GrepMatch>,
    max: usize,
) -> Result<(), std::io::Error> {
    let mut searcher = SearcherBuilder::new().build();
    let path_str = path.to_string_lossy().to_string();

    searcher.search_path(
        matcher,
        path,
        UTF8(|lnum, line| {
            if matches.len() < max {
                matches.push(GrepMatch {
                    path: path_str.clone(),
                    line_number: lnum,
                    line: line.trim_end().to_string(),
                });
            }
            Ok(true)
        }),
    )?;

    Ok(())
}
