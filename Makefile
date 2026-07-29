.PHONY: install run build clean

install:
	pip install -r requirements.txt
	pip install pyinstaller
	maturin develop --release -m rust_src/Cargo.toml

run:
	python launcher.py

build: clean install
	pyinstaller --noconfirm \
		--onedir \
		--windowed \
		--icon "assets/icon.png" \
		--add-data "assets:assets" \
		--add-data "locales:locales" \
		--add-data "steam_appid.txt:." \
		--add-data "libsteam_api.so:." \
		--add-data "SteamworksPy.so:." \
		--name "DMTL" \
		launcher.py
	rm -f dist/DMTL/_internal/libxkbcommon.so.0
	@echo "Build complete! Check the dist/DMTL/ folder for the launcher."

clean:
	rm -rf build/ dist/ *.spec
	find . -type d -name "__pycache__" -exec rm -rf {} +
