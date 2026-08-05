use pyo3::prelude::*;
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use jwalk::WalkDir;

// Calculates the total size of a directory using fast multi-threaded traversal.
fn get_dir_size(path: &Path) -> u64 {
    WalkDir::new(path)
        .skip_hidden(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.metadata().map(|m| m.len()).unwrap_or(0))
        .sum()
}

// Converts bytes into a human-readable format (B, KB, MB, GB).
fn format_size(size_bytes: u64) -> String {
    if size_bytes < 1024 {
        format!("{} B", size_bytes)
    } else if size_bytes < 1024 * 1024 {
        format!("{:.1} KB", size_bytes as f64 / 1024.0)
    } else {
        let mb = size_bytes as f64 / (1024.0 * 1024.0);
        if mb < 1024.0 {
            format!("{:.1} MB", mb)
        } else {
            format!("{:.1} GB", mb / 1024.0)
        }
    }
}

// Main Python binding: scans the workshop folder and extracts mod metadata.
#[pyfunction]
pub fn parse_local_mods(py: Python<'_>, game_path_str: String) -> PyResult<Vec<HashMap<String, String>>> {
    // Release the GIL to prevent freezing the Python UI during file I/O.
    let res = py.allow_threads(move || {
        let mut mods_list = Vec::new();
        let game_path = Path::new(&game_path_str);
        
        // Resolve the workshop content folder path.
        let steamapps_dir = match game_path.parent().and_then(|p| p.parent()) {
            Some(p) => p,
            None => return mods_list,
        };
        
        let content_dir = steamapps_dir.join("workshop").join("content").join("221100");
        
        if !content_dir.exists() {
            return mods_list;
        }

        if let Ok(entries) = fs::read_dir(content_dir) {
            for entry in entries.filter_map(|e| e.ok()) {
                let path = entry.path();
                if !path.is_dir() {
                    continue;
                }
                
                let dir_name = match path.file_name().and_then(|n| n.to_str()) {
                    Some(n) => n.to_string(),
                    None => continue,
                };
                
                // Ensure the folder name consists only of digits (Workshop ID).
                if !dir_name.chars().all(|c| c.is_ascii_digit()) {
                    continue;
                }

                let published_id = dir_name.clone();
                let mut display_name = dir_name.clone();
                let meta_file = path.join("meta.cpp");
                
                // Read meta.cpp using lossy conversion to handle invalid characters safely.
                if let Ok(bytes) = fs::read(&meta_file) {
                    let content = String::from_utf8_lossy(&bytes);
                    
                    // Extract the mod name between the first pair of quotes after "name".
                    if let Some(idx) = content.find("name") {
                        let after_name = &content[idx..];
                        if let Some(start_quote) = after_name.find('"') {
                            let inside_quotes = &after_name[start_quote + 1..];
                            if let Some(end_quote) = inside_quotes.find('"') {
                                display_name = inside_quotes[..end_quote].to_string();
                            }
                        }
                    }
                }

                // Calculate total mod size using jwalk.
                let size_bytes = get_dir_size(&path);
                let size_str = format_size(size_bytes);

                let mut mod_map = HashMap::new();
                mod_map.insert("display_name".to_string(), display_name);
                mod_map.insert("dir_name".to_string(), dir_name);
                mod_map.insert("author".to_string(), "Steam".to_string());
                mod_map.insert("size".to_string(), size_str);
                mod_map.insert("path".to_string(), path.to_string_lossy().to_string());
                mod_map.insert("published_id".to_string(), published_id);

                mods_list.push(mod_map);
            }
        }
        mods_list
    });
    
    Ok(res)
}

#[pyfunction]
pub fn clean_orphan_mods(py: Python<'_>, game_path_str: String) -> PyResult<usize> {
    py.allow_threads(move || {
        let game_path = std::path::Path::new(&game_path_str);
        
        let steamapps_dir = match game_path.parent().and_then(|p| p.parent()) {
            Some(p) => p,
            None => return Ok(0),
        };
        
        let content_dir = steamapps_dir.join("workshop").join("content").join("221100");
        let acf_path = steamapps_dir.join("workshop").join("appworkshop_221100.acf");
        
        if !content_dir.exists() || !acf_path.exists() {
            return Ok(0);
        }

        let acf_content = std::fs::read_to_string(acf_path).unwrap_or_default();
        let mut valid_ids = std::collections::HashSet::new();
        
        let mut in_details_section = false;
        let mut depth = 0;

        for line in acf_content.lines() {
            let trimmed = line.trim();
            
            if trimmed.contains("\"WorkshopItemDetails\"") {
                in_details_section = true;
                continue;
            }
            
            if in_details_section {
                if trimmed == "{" {
                    depth += 1;
                    continue;
                }
                if trimmed == "}" {
                    depth -= 1;
                    if depth <= 0 {
                        break;
                    }
                    continue;
                }
                
                if depth == 1 && trimmed.starts_with('"') {
                    let parts: Vec<&str> = trimmed.split('"').collect();
                    if parts.len() >= 3 {
                        let id = parts[1];
                        if !id.is_empty() && id.chars().all(|c| c.is_ascii_digit()) {
                            valid_ids.insert(id.to_string());
                        }
                    }
                }
            }
        }

        let mut deleted_count = 0;

        if let Ok(entries) = std::fs::read_dir(content_dir) {
            for entry in entries.filter_map(|e| e.ok()) {
                let path = entry.path();
                if !path.is_dir() { continue; }
                
                if let Some(dir_name) = path.file_name().and_then(|n| n.to_str()) {
                    if dir_name.chars().all(|c| c.is_ascii_digit()) {
                        if !valid_ids.contains(dir_name) {
                            if std::fs::remove_dir_all(&path).is_ok() {
                                deleted_count += 1;
                            }
                        }
                    }
                }
            }
        }
        
        Ok(deleted_count)
    })
}