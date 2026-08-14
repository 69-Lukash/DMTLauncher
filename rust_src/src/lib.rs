use pyo3::prelude::*;

mod net;
mod parser;
mod preset;

#[pymodule]
fn dmtl_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(net::query_server_full, m)?)?;
    m.add_function(wrap_pyfunction!(net::ping_server, m)?)?;
    m.add_function(wrap_pyfunction!(parser::parse_local_mods, m)?)?;
    m.add_function(wrap_pyfunction!(parser::clean_orphan_mods, m)?)?;
    m.add_function(wrap_pyfunction!(preset::export_preset, m)?)?;
    m.add_function(wrap_pyfunction!(preset::import_preset, m)?)?;
    Ok(())
}