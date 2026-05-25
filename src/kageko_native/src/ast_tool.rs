use pyo3::prelude::*;
use tree_sitter::{Parser, Language};

#[pyclass]
#[derive(Clone)]
pub struct ASTNode {
    #[pyo3(get)]
    pub kind: String,
    #[pyo3(get)]
    pub start_line: usize,
    #[pyo3(get)]
    pub end_line: usize,
    #[pyo3(get)]
    pub text: String,
}

/// Parse source code and return a summary of top-level declarations.
#[pyfunction]
pub fn summarize(source: &str, language: &str) -> PyResult<Vec<ASTNode>> {
    let lang = get_language(language)?;
    let mut parser = Parser::new();
    parser.set_language(&lang).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Parser error: {}", e))
    })?;

    let tree = parser.parse(source, None).ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("Failed to parse source")
    })?;

    let root = tree.root_node();
    let mut nodes = Vec::new();
    collect_top_level(source, root, &mut nodes);

    Ok(nodes)
}

fn get_language(name: &str) -> PyResult<Language> {
    match name {
        "python" => Ok(tree_sitter_python::LANGUAGE.into()),
        "javascript" | "js" => Ok(tree_sitter_javascript::LANGUAGE.into()),
        "rust" | "rs" => Ok(tree_sitter_rust::LANGUAGE.into()),
        _ => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Unsupported language: {}",
            name
        ))),
    }
}

fn collect_top_level(source: &str, node: tree_sitter::Node, results: &mut Vec<ASTNode>) {
    let kind_names = [
        "function_definition",
        "class_definition",
        "import_statement",
        "import_from_statement",
        "decorated_definition",
        "expression_statement",
    ];

    for child in node.children(&mut node.walk()) {
        let kind = child.kind().to_string();
        if kind_names.contains(&kind.as_str()) {
            let text = child
                .utf8_text(source.as_bytes())
                .unwrap_or("")
                .lines()
                .next()
                .unwrap_or("")
                .to_string();

            results.push(ASTNode {
                kind,
                start_line: child.start_position().row + 1,
                end_line: child.end_position().row + 1,
                text,
            });
        }

        // Recurse into blocks
        if child.child_count() > 0 && !kind_names.contains(&child.kind()) {
            collect_top_level(source, child, results);
        }
    }
}
