from __future__ import annotations

from pathlib import Path

from PIL import Image


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "assets" / "icon-source.png"
    target = root / "assets" / "icon.ico"

    if not source.exists():
        print(f"[icon] Source image not found: {source}")
        return 1

    image = Image.open(source).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    image.save(target, format="ICO", sizes=sizes)
    print(f"[icon] Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
