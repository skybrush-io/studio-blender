"""Create a portable, offline Windows acceptance bundle beside the installer."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installer", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    manifest = {
        "installer": args.installer.name,
        "sha256": hashlib.sha256(args.installer.read_bytes()).hexdigest(),
        "windows_test_status": "not yet executed; inspect returned evidence",
    }
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(args.installer, args.installer.name)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.write(scripts / "Run-Windows-QA.ps1", "Run-Windows-QA.ps1")
        archive.write(scripts.parent.parent / "doc" / "windows-qa.md", "README.md")
        for script in (
            "run_isolated_blender_test.py",
            "check_safe_maneuvers.py",
            "check_checked_export.py",
            "stress_offline_export.py",
        ):
            archive.write(scripts / script, f"scripts/{script}")
    print(f"Windows acceptance bundle: {args.output}")


if __name__ == "__main__":
    main()
