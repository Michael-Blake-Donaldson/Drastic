# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for DRASTIC Planner
# Run via:  build.bat  (or directly: pyinstaller drastic.spec --noconfirm)

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ---------------------------------------------------------------------------
# PySide6 WebEngine requires explicit collection — standard hooks miss
# several Qt resource files that the in-process renderer needs at runtime.
# ---------------------------------------------------------------------------
datas    = [("reference_data/geography_profiles.csv", "reference_data")]
binaries = []
hiddenimports = [
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebChannel",
    "sqlite3",
]

for _pkg in ("PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore"):
    _d, _b, _h = collect_all(_pkg)
    datas         += _d
    binaries      += _b
    hiddenimports += _h

# ---------------------------------------------------------------------------

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "scipy"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DRASTIC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX can corrupt Qt WebEngine binaries — keep off
    console=False,      # No console window for the end user
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="installer\\windows_version_info.txt",
    icon="assets\\icon.ico" if __import__("os").path.exists("assets\\icon.ico") else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DRASTIC",
)
