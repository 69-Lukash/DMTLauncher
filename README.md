# DMTL - DayZ MefTeam Launcher

A lightweight and fast custom launcher for DayZ, built with Python.
It features direct integration with the Steamworks API for seamless background mod downloading and management without freezing the UI.

## Features

* 🚀 **Speed:** Asynchronous A2S UDP pinger for instant server querying.
* 🔄 **Steamworks Integration:** Native background synchronization for Steam Workshop mods.
* 🐧 **Linux/Proton Ready:** Full support for running on Linux without weird workarounds.
* 🎨 **UI:** Clean, minimalist dark theme with zero clutter.

## Running from Source

1. Clone the repository:

   ```bash
    git clone https://github.com/69-Lukash/DMTLauncher.git
    cd DMTLauncher
   ```

2. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install dependencies and run:

   ```bash
   make install
   make run
   ```

## Building the Executable

If you don't want to mess with Python environments, you can compile a standalone executable using PyInstaller.

Just run:

```bash
make build
```

The compiled launcher will be available in the `dist/DMTL/` directory.

## Important Note

For the Steam API to work properly, ensure the Steam client is running in the background, and the following files are present in the project root:

* `steam_appid.txt` (must contain `221100`)
* `libsteam_api.so` (for Linux) or `steam_api64.dll` (for Windows)
* `SteamworksPy.so` (for Linux) or `SteamworksPy64.dll` (for Windows)
