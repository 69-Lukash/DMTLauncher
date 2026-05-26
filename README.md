# DMTL - DayZ MefTeam Launcher

A lightweight and fast custom launcher for DayZ, built with Python.
It features direct integration with the Steamworks API for seamless background mod downloading and management without freezing the UI.

## ✨ Features

* 🚀 **Speed:** Asynchronous A2S UDP pinger for instant server querying.
* 🔄 **Steamworks Integration:** Native background synchronization for Steam Workshop mods.
* 🐧 **Linux/Proton Ready:** Full support for running on Linux without weird workarounds.
* 🎨 **UI:** Clean, minimalist dark theme with zero clutter.

![DMTL Screenshot](https://github.com/user-attachments/assets/16536bfa-0c32-429f-9266-2b426cdf26e5)

## ⚙️ How It Works (Under the Hood)

DMTL is designed to be fast, reliable, and completely non-blocking:

* **Asynchronous Server Queries:** Uses native UDP sockets to ping servers via the A2S protocol, updating the server list instantly without stuttering.
* **Isolated Steamworks Worker:** Steam Workshop interactions (syncing, deleting mods) are handled by a dedicated, isolated background process. This prevents heavy Steam API calls from freezing the PyQt6 UI and ensures stable execution across both Windows and Linux.
* **Smart Mod Parsing:** Reads `meta.cpp` files to identify mods and sizes, automatically creating safe symlinks in your `!Workshop` directory to run seamlessly with Proton/Wine or native Windows.

## 📥 How to Run (Pre-compiled Binaries)



You don't need to install Python or mess with dependencies to play. Just grab the latest release!

**From AUR (Arch Linux):**

If you are running Arch Linux or any Arch-based distribution (Manjaro, EndeavourOS, etc.), you can easily install the launcher directly from the AUR:

```bash
yay -S dmtl-bin
```

This will automatically install the launcher, set up the desktop application shortcut with an icon, and handle system-wide execution.
    
**For Windows:**

1. Go to the [Releases](../../releases) tab and download `DMTL-Windows.zip`.
2. Extract the archive to any folder.
3. Make sure the Steam client is running in the background.
4. Run `DMTL-Windows.exe`.

**For Linux:**

1. Go to the [Releases](../../releases) tab and download `DMTL-Linux.tar.gz`.
2. Extract the archive using your file manager or terminal:

    ```bash
    tar -xzf DMTL-Linux.tar.gz
    ```

3. Make the binary executable and run it:

    ```bash
    chmod +x DMTL-Linux/DMTL-Linux
    ./DMTL-Linux/DMTL-Linux
    ```

*Note for Linux users: Make sure to force a Steam Play compatibility tool (e.g., Proton Experimental) in your DayZ properties in Steam.*

## 🛠️ Running from Source

If you want to modify the launcher or run it directly from the Python scripts:

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

*(Make sure `steam_appid.txt` and the required Steamworks `.so`/`.dll` libraries are present in the project root).*

## 📦 Building the Executable

If you want to compile your own standalone executable using PyInstaller, just run:

```bash
make build
```

The compiled launcher will be available in the `dist/DMTL/` directory.

## 🐛 Bug Reports & Feedback

DMTLauncher is currently in **active development**. If you encounter any crashes, weird behavior, or just have a suggestion to improve the app, please report it in the [Issues](https://github.com/69-Lukash/DMTLauncher/issues) section!

Every bug report helps make the launcher faster and more stable for everyone.

## ⚠️ Important Notes

* The Steam client **must** be running in the background for the launcher to successfully fetch server mods and synchronize your Workshop subscriptions.
* Pre-compiled releases already include the necessary Steamworks API binaries. You only need to manually manage `steam_api64.dll` / `libsteam_api.so` if you are running or building from source.

## 🗺️ Roadmap (Future Plans)

Here are some features planned for future updates:

* [ ] **Mods Management:** Add a search bar to quickly find specific local mods by name in the Mods tab.
* [ ] **Server History:** Add an "Is Played" (or "Last Played") column/indicator to easily find previously visited servers.
* [ ] **Server Filters:** Add simple toggles for server list (e.g., Password-protected, Favorites only, Modded/Vanilla).
* [ ] **Quality of Life (QoL):**
  * Export/Import Favorites list to easily share your top servers with friends.
  * Custom game launch parameters in settings (e.g., `-nosplash`, `-nopause`, CPU core limits).
