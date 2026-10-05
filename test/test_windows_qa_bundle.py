import hashlib
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def test_acceptance_bundle_is_self_contained_and_hashes_exact_installer(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    installer = tmp_path / "installer space café.zip"
    with ZipFile(installer, "w") as archive:
        archive.writestr("ui_dronetara_studio.py", "# dummy fixture, never installed")
    bundle = tmp_path / "Windows QA.zip"
    subprocess.run(
        [
            sys.executable,
            str(repo / "etc/scripts/build_windows_qa_bundle.py"),
            str(installer),
            str(bundle),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    with ZipFile(bundle) as archive:
        assert archive.testzip() is None
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["installer"] == installer.name
        assert manifest["sha256"] == hashlib.sha256(installer.read_bytes()).hexdigest()
        assert archive.read(installer.name) == installer.read_bytes()
        assert "not yet executed" in manifest["windows_test_status"]
        assert set(archive.namelist()) == {
            installer.name,
            "manifest.json",
            "README.md",
            "Run-Windows-QA.ps1",
            "scripts/run_isolated_blender_test.py",
            "scripts/check_safe_maneuvers.py",
            "scripts/check_checked_export.py",
            "scripts/stress_offline_export.py",
        }
