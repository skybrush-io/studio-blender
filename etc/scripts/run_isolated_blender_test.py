"""Portable ZIP acceptance runner. Never installs into the user's Blender profile.

Example: python etc/scripts/run_isolated_blender_test.py --blender /path/to/blender
--addon-zip dist/addon.zip --scene /path/to/show.blend --mode gui
The run directory is new, retained for evidence, and printed before launch.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from tempfile import mkdtemp
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", required=True, type=Path)
    parser.add_argument("--addon-zip", required=True, type=Path)
    parser.add_argument("--scene", type=Path)
    parser.add_argument(
        "--mode",
        choices=("gui", "worker", "checked", "stress", "maneuvers"),
        default="worker",
    )
    args = parser.parse_args()
    if args.mode in ("gui", "worker") and args.scene is None:
        parser.error("--scene is required for gui/worker mode")
    executable = args.blender.resolve(strict=True)
    addon = args.addon_zip.resolve(strict=True)
    source = args.scene.resolve(strict=True) if args.scene is not None else None
    original_digest = (
        hashlib.sha256(source.read_bytes()).hexdigest() if source else None
    )
    root = Path(mkdtemp(prefix="Skybrush QA space-")).resolve()
    scripts = root / "scripts"
    addons = scripts / "addons"
    addons.mkdir(parents=True)
    for name in ("config", "temp", "output"):
        (root / name).mkdir()
    with ZipFile(addon) as archive:
        for name in archive.namelist():
            if not (addons / name).resolve().is_relative_to(addons):
                raise ValueError(f"Unsafe archive member: {name}")
        archive.extractall(addons)
    fixture = root / "Skybrush GUI QA.blend"
    if source is not None:
        shutil.copy2(source, fixture)
    env = dict(os.environ)
    env.update(
        BLENDER_USER_SCRIPTS=str(scripts),
        BLENDER_USER_CONFIG=str(root / "config"),
        TMPDIR=str(root / "temp"),
        TMP=str(root / "temp"),
        TEMP=str(root / "temp"),
    )
    # Preserve assets referenced relative to the original scene. The GUI fixture
    # itself lives in the new run directory; no original file is opened for write.
    config = {"source": str(source), "fixture": str(fixture), "root": str(root)}
    (root / "session.json").write_text(json.dumps(config))
    helper = Path(__file__).with_name("check_background_export.py")
    tail = [str(source), str(root / "output" / "export space.skyc")]
    if args.mode == "gui":
        helper = Path(__file__).with_name("prepare_gui_session.py")
        tail = [str(root / "session.json")]
    elif args.mode == "checked":
        helper = Path(__file__).with_name("check_checked_export.py")
        tail = [str(root / "output")]
    elif args.mode == "stress":
        helper = Path(__file__).with_name("stress_offline_export.py")
        tail = [str(root / "output" / "500-checked-draft.skyc"), "--audit"]
    elif args.mode == "maneuvers":
        helper = Path(__file__).with_name("check_safe_maneuvers.py")
        tail = [str(root / "output")]
    command = [str(executable)]
    if args.mode != "gui":
        command.append("--background")
    command += [
        "--factory-startup",
        "--disable-autoexec",
        "--python-exit-code",
        "1",
        "--python",
        str(helper.resolve()),
        "--",
        *tail,
    ]
    metadata = {
        "mode": args.mode,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "addon_sha256": hashlib.sha256(addon.read_bytes()).hexdigest(),
        "source_sha256": original_digest,
        "command": command,
        "status": "running",
    }
    record = root / "run.json"
    record.write_text(json.dumps(metadata, indent=2))
    print(f"Isolated QA evidence: {root}", flush=True)
    with (root / "blender.log").open("w") as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    unchanged = (
        hashlib.sha256(source.read_bytes()).hexdigest() == original_digest
        if source
        else None
    )
    metadata.update(
        exit_code=result.returncode, source_unchanged=unchanged, status="exited"
    )
    record.write_text(json.dumps(metadata, indent=2))
    if unchanged is False:
        raise RuntimeError("Source checksum changed during test")
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
