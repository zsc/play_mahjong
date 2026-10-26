"""Create a small SOFY bundle with explicit native library and checkpoint provenance."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, required=True, help="Linux x86-64 FFI from the same source")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    header = args.library.read_bytes()[:20]
    if header[:4] != b"\x7fELF" or header[4:6] != b"\x02\x01" or header[18:20] != b"\x3e\x00":
        parser.error("library must be a 64-bit little-endian x86-64 ELF, not the macOS library")
    if not args.checkpoint.is_file() or args.output.exists():
        parser.error("checkpoint must exist and output directory must be new")
    args.output.mkdir(parents=True)
    names = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
    for name in names:
        if name.startswith(("training/", "ocaml/mahjong_core/", "ocaml/mahjong_ffi/")):
            target = args.output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, target)
    (args.output / "scripts").mkdir()
    for path in (root / "scripts").glob("sofy_*.py"):
        shutil.copy2(path, args.output / "scripts" / path.name)
    for name in ["AGENTS.md", "pyproject.toml", "uv.lock"]:
        shutil.copy2(root / name, args.output / name)
    shutil.copy2(root / "docs/sofy-ppo-plan.md", args.output / "sofy-ppo-plan.md")
    (args.output / "native").mkdir()
    shutil.copy2(args.library, args.output / "native/mahjong_ffi.so")
    # SOFY intentionally skips *.pt; this explicitly selected file is the warm start.
    shutil.copy2(args.checkpoint, args.output / "initial.bin")
    manifest = {str(p.relative_to(args.output)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(args.output.rglob("*")) if p.is_file()}
    (args.output / "bundle-sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Bundle ready: {args.output}; {len(manifest)} files")


if __name__ == "__main__":
    main()
