use pyo3::prelude::*;

mod grep;
mod hashline;

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<hashline::HashlineEditor>()?;
    m.add_class::<hashline::SourceLine>()?;
    m.add_function(wrap_pyfunction!(grep::ripgrep, m)?)?;
    m.add_class::<grep::GrepMatch>()?;
    Ok(())
}
