use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use std::fs;
use crc32fast::Hasher;

// Header: DMTL (4 bytes) + Format Version (1 byte)
const MAGIC_BYTES: &[u8; 4] = b"DMTL";
const FORMAT_VERSION: u8 = 1;

fn encode_preset(name: &str, mods: &[u64]) -> Result<Vec<u8>, String> {
    let mut data = Vec::new();

    // Header
    data.extend_from_slice(MAGIC_BYTES);
    data.push(FORMAT_VERSION);

    // Metadata (Name)
    let name_bytes = name.as_bytes();
    if name_bytes.len() > 255 {
        return Err("Preset name is too long (max 255 bytes)".to_string());
    }
    data.push(name_bytes.len() as u8);
    data.extend_from_slice(name_bytes);

    // Payload (Mods count + IDs)
    if mods.len() > u16::MAX as usize {
        return Err("Too many mods in preset (max 65535)".to_string());
    }
    data.extend_from_slice(&(mods.len() as u16).to_le_bytes());
    for m in mods {
        data.extend_from_slice(&m.to_le_bytes());
    }

    // CRC32 Validation
    let mut hasher = Hasher::new();
    hasher.update(&data);
    data.extend_from_slice(&hasher.finalize().to_le_bytes());

    Ok(data)
}

fn decode_preset(data: &[u8]) -> Result<(String, Vec<u64>), String> {
    // Minimum valid file: 4 (magic) + 1 (version) + 1 (name_len) + 2 (mods_count) + 4 (crc32) = 12 bytes
    if data.len() < 12 {
        return Err("File is too small to be a valid DMTL preset".to_string());
    }

    // Validate Header
    if &data[0..4] != MAGIC_BYTES || data[4] != FORMAT_VERSION {
        return Err("Invalid format or unsupported version".to_string());
    }

    // Validate CRC32 (last 4 bytes)
    let payload_len = data.len() - 4;
    let payload = &data[..payload_len];
    let mut hasher = Hasher::new();
    hasher.update(payload);

    let crc_bytes: [u8; 4] = data[payload_len..]
        .try_into()
        .map_err(|_| "Corrupted CRC32 trailer".to_string())?;
    let expected_crc = u32::from_le_bytes(crc_bytes);
    if hasher.finalize() != expected_crc {
        return Err("CRC32 validation failed. File is corrupted.".to_string());
    }

    // Parse Name
    let name_len = payload[5] as usize;
    let name_end = 6 + name_len;
    if name_end + 2 > payload.len() {
        return Err("Preset header is truncated or malformed".to_string());
    }
    let name = String::from_utf8_lossy(&payload[6..name_end]).to_string();

    // Parse Payload
    let mut cursor = name_end;
    let count_bytes: [u8; 2] = payload[cursor..cursor + 2]
        .try_into()
        .map_err(|_| "Preset mods count is truncated".to_string())?;
    let mods_count = u16::from_le_bytes(count_bytes) as usize;
    cursor += 2;

    let expected_mods_bytes = mods_count
        .checked_mul(8)
        .ok_or_else(|| "Preset mods count overflow".to_string())?;
    if payload.len() - cursor != expected_mods_bytes {
        return Err("Preset mod list is truncated or malformed".to_string());
    }

    let mut mods = Vec::with_capacity(mods_count);
    for chunk in payload[cursor..].chunks_exact(8) {
        let id_bytes: [u8; 8] = chunk
            .try_into()
            .map_err(|_| "Preset mod entry is truncated".to_string())?;
        mods.push(u64::from_le_bytes(id_bytes));
    }

    Ok((name, mods))
}

#[pyfunction]
pub fn export_preset(path: String, name: String, mods: Vec<u64>) -> PyResult<()> {
    let data = encode_preset(&name, &mods).map_err(PyValueError::new_err)?;
    fs::write(path, data)?;
    Ok(())
}

#[pyfunction]
pub fn import_preset(path: String) -> PyResult<(String, Vec<u64>)> {
    let data = fs::read(path)?;
    decode_preset(&data).map_err(PyValueError::new_err)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn append_crc(mut buf: Vec<u8>) -> Vec<u8> {
        let mut hasher = Hasher::new();
        hasher.update(&buf);
        buf.extend_from_slice(&hasher.finalize().to_le_bytes());
        buf
    }

    #[test]
    fn test_preset_roundtrip() {
        let mods = vec![1559212036_u64, 2545327648_u64];
        let encoded = encode_preset("DayZ Editor", &mods).expect("encode should succeed");
        let (name, decoded_mods) = decode_preset(&encoded).expect("decode should succeed");
        assert_eq!(name, "DayZ Editor");
        assert_eq!(decoded_mods, mods);
    }

    #[test]
    fn test_preset_corrupted_crc() {
        let mut encoded = encode_preset("Test", &[12345]).unwrap();
        encoded[6] ^= 0xFF;
        assert!(decode_preset(&encoded).is_err());
    }

    #[test]
    fn test_preset_truncated_name_with_valid_crc() {
        // Claims name_len = 50, but only 2 bytes follow before CRC
        let mut raw = Vec::new();
        raw.extend_from_slice(MAGIC_BYTES);
        raw.push(FORMAT_VERSION);
        raw.push(50);
        raw.extend_from_slice(b"hi");
        let crafted = append_crc(raw);
        assert!(decode_preset(&crafted).is_err());
    }

    #[test]
    fn test_preset_truncated_mods_with_valid_crc() {
        // Claims mods_count = 3, but only 1 mod ID follows before CRC
        let mut raw = Vec::new();
        raw.extend_from_slice(MAGIC_BYTES);
        raw.push(FORMAT_VERSION);
        raw.push(1);
        raw.push(b'a');
        raw.extend_from_slice(&3u16.to_le_bytes());
        raw.extend_from_slice(&1559212036u64.to_le_bytes());
        let crafted = append_crc(raw);
        assert!(decode_preset(&crafted).is_err());
    }
}