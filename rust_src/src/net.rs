/*
DayZ A2S_RULES parser.
Names and logic are based around the Arma 3 ServerBrowserProtocol3.
Bohemia Interactive modified the standard A2S_RULES to store a binary payload inside a dictionary.
*/

use pyo3::prelude::*;
use std::collections::HashMap;
use std::net::UdpSocket;
use std::time::{Duration, Instant};

/// Reads packets from the socket. Reassembles them if the server split the payload.
fn receive_packet(socket: &UdpSocket) -> Result<Vec<u8>, std::io::Error> {
    let mut packets: HashMap<u8, Vec<u8>> = HashMap::new();

    loop {
        let mut buf = [0u8; 4096];
        let (amt, _) = socket.recv_from(&mut buf)?;
        let data = &buf[..amt];

        // Check if the packet is split (starts with FE FF FF FF)
        if data.starts_with(b"\xFE\xFF\xFF\xFF") {
            if data.len() < 13 {
                return Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "Packet too short"));
            }
            let total = data[8];
            let number = data[9];
            
            // Skip header, ID, total, number, and max_size
            let payload = &data[12..];
            packets.insert(number, payload.to_vec());

            // Reassemble when all parts are received
            if packets.len() == total as usize {
                let mut reassembled = Vec::new();
                for i in 0..total {
                    if let Some(p) = packets.get(&i) {
                        reassembled.extend_from_slice(p);
                    }
                }
                return Ok(reassembled);
            }
        // Single complete packet (starts with FF FF FF FF)
        } else if data.starts_with(b"\xFF\xFF\xFF\xFF") {
            return Ok(data.to_vec());
        } else {
            return Err(std::io::Error::new(std::io::ErrorKind::InvalidData, "Invalid header"));
        }
    }
}

/// Safely extracts a null-terminated string from the buffer
fn read_str<'a>(data: &'a [u8], cursor: &mut usize) -> &'a [u8] {
    let start = *cursor;
    while *cursor < data.len() {
        if let Some(&b) = data.get(*cursor) {
            if b == 0 {
                break;
            }
        }
        *cursor += 1;
    }
    let res = &data[start..(*cursor).min(data.len())];
    *cursor += 1;
    res
}

/// Parses A2S_INFO to extract players count and in-game time
fn parse_a2s_info(data: &[u8]) -> (String, String) {
    if data.len() < 5 || data.get(4).copied() != Some(b'I') { 
        return (String::new(), String::new()); 
    }
    let mut c = 6;

    read_str(data, &mut c); // Name
    read_str(data, &mut c); // Map
    read_str(data, &mut c); // Folder
    read_str(data, &mut c); // Game
    c += 2; // App ID
    
    let players = data.get(c).copied().unwrap_or(0);
    let max_players = data.get(c + 1).copied().unwrap_or(0);
    let players_str = format!("{}/{}", players, max_players);
    
    c += 2;
    c += 5; // Skip bots, type, env, vis, vac
    read_str(data, &mut c); // Version
    
    let mut day_time = String::new();
    if let Some(&edf) = data.get(c) {
        c += 1;
        if edf & 0x80 != 0 { c += 2; }
        if edf & 0x10 != 0 { c += 8; }
        if edf & 0x40 != 0 { c += 2; read_str(data, &mut c); }
        if edf & 0x20 != 0 {
            // DayZ hides in-game time inside the keywords field
            let kw_bytes = read_str(data, &mut c);
            let kw_str = String::from_utf8_lossy(kw_bytes);
            
            // Search for HH:MM pattern
            for word in kw_str.split(|c| c == ',' || c == ' ') {
                let parts: Vec<&str> = word.split(':').collect();
                if parts.len() == 2 && parts[0].parse::<u8>().is_ok() && parts[1].parse::<u8>().is_ok() {
                    day_time = format!("{}:{}", parts[0], parts[1]);
                    break;
                }
            }
        }
    }
    (players_str, day_time)
}

/// Parses the modified DayZ A2S_RULES response
fn parse_dayz_rules(data: &[u8]) -> Vec<(String, String)> {
    if data.len() < 7 || data.get(4).copied() != Some(b'E') { 
        return vec![]; 
    }
    let mut c = 5;
    let b0 = data.get(c).copied().unwrap_or(0);
    let b1 = data.get(c + 1).copied().unwrap_or(0);
    let num_rules = u16::from_le_bytes([b0, b1]) as usize;
    c += 2;

    let mut rules_map: Vec<(u16, &[u8])> = Vec::new();

    // DayZ stores the actual binary payload inside rule values where the key is 2 bytes long
    for _ in 0..num_rules {
        if c >= data.len() { break; }
        let key = read_str(data, &mut c);
        let val = read_str(data, &mut c);
        
        match key.len() {
            1 => rules_map.push((key[0] as u16, val)),
            2 => rules_map.push((u16::from_le_bytes([key[0], key[1]]), val)),
            _ => {} 
        }
    }

    // Sort by key and concatenate all values
    rules_map.sort_by_key(|k| k.0);
    let mut bin_content = Vec::new();
    for (_, val) in rules_map {
        bin_content.extend_from_slice(val);
    }

    // Resolve Bohemia's custom escape sequences
    let mut unescaped = Vec::new();
    let mut i = 0;
    while i < bin_content.len() {
        if bin_content.get(i).copied() == Some(0x01) {
            if let Some(&next_byte) = bin_content.get(i + 1) {
                match next_byte {
                    0x02 => { unescaped.push(0x00); i += 2; continue; } // 01 02 -> 00
                    0x03 => { unescaped.push(0xFF); i += 2; continue; } // 01 03 -> FF
                    0x01 => { unescaped.push(0x01); i += 2; continue; } // 01 01 -> 01
                    _ => {}
                }
            }
        }
        if let Some(&b) = bin_content.get(i) {
            unescaped.push(b);
        }
        i += 1;
    }

    let mut uc = 0;
    
    // Helper closures for reading types from the unescaped buffer
    let read_u8 = |u: &[u8], idx: &mut usize| -> u8 { 
        let v = u.get(*idx).copied().unwrap_or(0); 
        *idx += 1; 
        v 
    };
    let read_u16 = |u: &[u8], idx: &mut usize| -> u16 { 
        let b0 = u.get(*idx).copied().unwrap_or(0);
        let b1 = u.get(*idx + 1).copied().unwrap_or(0);
        *idx += 2; 
        u16::from_le_bytes([b0, b1]) 
    };
    let read_u32 = |u: &[u8], idx: &mut usize| -> u32 { 
        let b0 = u.get(*idx).copied().unwrap_or(0);
        let b1 = u.get(*idx + 1).copied().unwrap_or(0);
        let b2 = u.get(*idx + 2).copied().unwrap_or(0);
        let b3 = u.get(*idx + 3).copied().unwrap_or(0);
        *idx += 4; 
        u32::from_le_bytes([b0, b1, b2, b3]) 
    };

    let _proto = read_u8(&unescaped, &mut uc);
    let _overflow = read_u8(&unescaped, &mut uc);
    let dlc_flags = read_u16(&unescaped, &mut uc);
    
    // Skip DLC hashes based on set bits
    for _ in 0..dlc_flags.count_ones() {
        read_u32(&unescaped, &mut uc);
    }

    let mods_count = read_u8(&unescaped, &mut uc);
    let mut mods = Vec::new();
    
    // Extract Workshop IDs and mod names
    for _ in 0..mods_count {
        if uc >= unescaped.len() { break; }
        let _hash = read_u32(&unescaped, &mut uc);
        let id_len = read_u8(&unescaped, &mut uc);
        
        let actual_len = (id_len & 0x0F) as usize;
        let mut workshop_id: u64 = 0;
        for j in 0..actual_len {
            if uc < unescaped.len() {
                workshop_id |= (unescaped[uc] as u64) << (j * 8);
                uc += 1;
            }
        }
        
        let name_len = read_u8(&unescaped, &mut uc) as usize;
        let end = (uc + name_len).min(unescaped.len());
        let name_str = String::from_utf8_lossy(&unescaped[uc..end]).to_string();
        
        mods.push((workshop_id.to_string(), name_str));
        uc += name_len;
    }

    mods
}

#[pyfunction]
#[pyo3(signature = (ip, port))]
pub fn query_server_full(py: Python<'_>, ip: String, port: u16) -> PyResult<(String, String, String, Vec<(String, String)>)> {
    // Release the GIL so Python UI doesn't freeze during network IO
    let res = py.allow_threads(move || -> Result<(String, String, String, Vec<(String, String)>), std::io::Error> {
        let address = format!("{}:{}", ip, port);
        
        let socket = UdpSocket::bind("0.0.0.0:0")?;
        socket.set_read_timeout(Some(Duration::from_millis(2000)))?;
        socket.set_write_timeout(Some(Duration::from_millis(2000)))?;

        let start = Instant::now();
        let mut mods = vec![];
        let mut day_time = String::new();
        let mut players_str = String::new();

        // 1. Send A2S_INFO query
        socket.send_to(b"\xFF\xFF\xFF\xFFTSource Engine Query\x00", &address)?;
        if let Ok(info_data) = receive_packet(&socket) {
            let (p, d) = parse_a2s_info(&info_data);
            players_str = p;
            day_time = d;
        }
        
        let ping_ms = start.elapsed().as_millis().to_string();

        // 2. Send A2S_RULES query (Challenge phase)
        socket.send_to(b"\xFF\xFF\xFF\xFFV\xFF\xFF\xFF\xFF", &address)?;
        
        let mut rules_req = None;
        for _ in 0..3 {
            if let Ok(chall_data) = receive_packet(&socket) {
                // If server responded with challenge token
                if chall_data.len() >= 9 && chall_data.get(4).copied() == Some(b'A') {
                    let mut req = b"\xFF\xFF\xFF\xFFV\x00\x00\x00\x00".to_vec();
                    if chall_data.len() >= 9 {
                        req[5..9].copy_from_slice(&chall_data[5..9]);
                    }
                    rules_req = Some(req);
                    break;
                }
            }
        }

        // 3. Send actual rules request with token
        if let Some(req) = rules_req {
            socket.send_to(&req, &address)?;
            if let Ok(rules_data) = receive_packet(&socket) {
                mods = parse_dayz_rules(&rules_data);
            }
        }

        Ok((ping_ms, players_str, day_time, mods))
    })?;

    Ok(res)
}

#[pyfunction]
#[pyo3(signature = (ip, port))]
pub fn ping_server(py: Python<'_>, ip: String, port: u16) -> PyResult<(String, String, String)> {
    let res = py.allow_threads(move || -> Result<(String, String, String), std::io::Error> {
        let address = format!("{}:{}", ip, port);
        
        let socket = UdpSocket::bind("0.0.0.0:0")?;
        socket.set_read_timeout(Some(Duration::from_millis(1000)))?;
        socket.set_write_timeout(Some(Duration::from_millis(1000)))?;

        let start = Instant::now();
        let mut day_time = String::new();
        let mut players_str = String::new();

        // 1. Send A2S_INFO request (with challenge handling)
        let mut info_req = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00".to_vec();
        for _ in 0..3 {
            socket.send_to(&info_req, &address)?;
            if let Ok(info_data) = receive_packet(&socket) {
                // If server asks for a challenge (starts with 'A')
                if info_data.len() >= 9 && info_data.get(4).copied() == Some(b'A') {
                    info_req = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00".to_vec();
                    info_req.extend_from_slice(&info_data[5..9]);
                    continue;
                } else if info_data.get(4).copied() == Some(b'I') {
                    let (p, d) = parse_a2s_info(&info_data);
                    players_str = p;
                    day_time = d;
                    break;
                }
            }
        }
        
        let ping_ms = start.elapsed().as_millis().to_string();

        Ok((ping_ms, players_str, day_time))
    })?;

    Ok(res)
}