use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use std::fs;
use crc32fast::Hasher;

// Header: DMTL (4 bytes) + Format Version (1 byte)
const MAGIC_BYTES: &[u8; 4] = b"DMTL";
const FORMAT_VERSION: u8 = 1;

#[pyfunction]
pub fn export_preset(path: String, name: String, mods: Vec<u64>) -> PyResult<()> {
    let mut data = Vec::new();
    
    // Header
    data.extend_from_slice(MAGIC_BYTES);
    data.push(FORMAT_VERSION);

    // Metadata (Name)
    let name_bytes = name.as_bytes();
    if name_bytes.len() > 255 {
        return Err(PyValueError::new_err("Preset name is too long (max 255 bytes)"));
    }
    data.push(name_bytes.len() as u8);
    data.extend_from_slice(name_bytes);

    // Payload (Mods count + IDs)
    data.extend_from_slice(&(mods.len() as u16).to_le_bytes());
    for m in mods {
        data.extend_from_slice(&m.to_le_bytes());
    }

    // CRC32 Validation
    let mut hasher = Hasher::new();
    hasher.update(&data);
    data.extend_from_slice(&hasher.finalize().to_le_bytes());

    fs::write(path, data)?;
    Ok(())
}

#[pyfunction]
pub fn import_preset(path: String) -> PyResult<(String, Vec<u64>)> {
    let data = fs::read(path)?;
    
    if data.len() < 10 {
        return Err(PyValueError::new_err("File is too small to be a valid DMTL preset"));
    }

    // Validate Header
    if &data[0..4] != MAGIC_BYTES || data[4] != FORMAT_VERSION {
        return Err(PyValueError::new_err("Invalid format or unsupported version"));
    }

    // Validate CRC32 (last 4 bytes)
    let payload_len = data.len() - 4;
    let mut hasher = Hasher::new();
    hasher.update(&data[..payload_len]);
    
    let expected_crc = u32::from_le_bytes(data[payload_len..].try_into().unwrap());
    if hasher.finalize() != expected_crc {
        return Err(PyValueError::new_err("CRC32 validation failed. File is corrupted."));
    }

    // Parse Name
    let name_len = data[5] as usize;
    let name = String::from_utf8_lossy(&data[6..6 + name_len]).to_string();

    // Parse Payload
    let mut cursor = 6 + name_len;
    let mods_count = u16::from_le_bytes(data[cursor..cursor+2].try_into().unwrap()) as usize;
    cursor += 2;

    let mut mods = Vec::with_capacity(mods_count);
    for _ in 0..mods_count {
        mods.push(u64::from_le_bytes(data[cursor..cursor+8].try_into().unwrap()));
        cursor += 8;
    }

    Ok((name, mods))
}