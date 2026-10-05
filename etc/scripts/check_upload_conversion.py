"""Offline-only conversion probe; never imports a driver or connects to hardware.

Requires crcmod. Arguments: server-checkout input.skyc native-reader report.json.
Loads the checkout's unmodified show format modules in an isolated namespace,
without initializing the server. Binary artifacts remain in a temporary directory.
This checks core trajectory/light conversion, not upload or flight readiness.
"""

import asyncio
import hashlib
import importlib
import json
import subprocess
import sys
import types
from base64 import b64decode
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile


async def main():
    server, source, reader, output = sys.argv[1:]
    module_path = Path(server) / "src/flockwave/server/show"
    package = types.ModuleType("conversion_reference")
    package.__path__ = [str(module_path)]
    sys.modules[package.__name__] = package
    formats = importlib.import_module("conversion_reference.formats")
    trajectory_module = importlib.import_module("conversion_reference.trajectory")
    hashes = {
        name: hashlib.sha256((module_path / name).read_bytes()).hexdigest()
        for name in ("formats.py", "trajectory.py", "utils.py")
    }
    results = []
    with (
        ZipFile(source) as archive,
        TemporaryDirectory(prefix="dronetara-conversion-") as temporary,
    ):
        show = json.loads(archive.read("show.json"))

        def resolve(reference):
            return json.loads(
                archive.read(reference["$ref"].removeprefix("./").split("#")[0])
            )

        for index, drone in enumerate(show["swarm"]["drones"]):
            settings = drone["settings"]
            result = {"drone": settings["name"]}
            try:
                trajectory = trajectory_module.TrajectorySpecification(
                    resolve(settings["trajectory"])
                )
                lights = resolve(settings["lights"])
                if lights["version"] != 1:
                    raise ValueError("unsupported light format")
                async with formats.SkybrushBinaryShowFile.create_in_memory() as binary:
                    await binary.add_trajectory(trajectory)
                    await binary.add_encoded_light_program(
                        b64decode(lights["data"], validate=True)
                    )
                    await binary.finalize()
                    data = binary.get_contents()
                async with formats.SkybrushBinaryShowFile.from_bytes(data) as binary:
                    blocks = await binary.read_all_blocks(validate=True)
                    assert [int(block.type) for block in blocks] == [1, 2]
                binary_path = Path(temporary) / f"{index}.skyb"
                binary_path.write_bytes(data)
                decoded_ms = int(
                    subprocess.check_output([reader, str(binary_path)], text=True)
                )
                expected_ms = round(trajectory.duration * 1000)
                result.update(
                    converted=True,
                    binary_bytes=len(data),
                    checksum_valid=True,
                    expected_duration_ms=expected_ms,
                    decoded_duration_ms=decoded_ms,
                    duration_difference_ms=decoded_ms - expected_ms,
                )
            except Exception as exc:
                result.update(converted=False, error=f"{type(exc).__name__}: {exc}")
            results.append(result)
    converted = [result for result in results if result["converted"]]
    report = {
        "scope": "local MAVLink core trajectory/light SKYC-to-SKYB conversion; no network or hardware calls",
        "reference_module_sha256": hashes,
        "native_reader_sha256": hashlib.sha256(Path(reader).read_bytes()).hexdigest(),
        "drone_count": len(results),
        "converted_count": len(converted),
        "failed_count": len(results) - len(converted),
        "duration_mismatch_count": sum(
            result["duration_difference_ms"] != 0 for result in converted
        ),
        "maximum_absolute_duration_difference_ms": max(
            (abs(result["duration_difference_ms"]) for result in converted),
            default=None,
        ),
        "not_verified": [
            "position quantization",
            "light/trajectory synchronization",
            "yaw/pyro/RTH",
            "coordinate origin and geofence",
            "device storage limits",
            "actual upload",
            "flight readiness",
        ],
        "drones": results,
    }
    Path(output).write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "drones"}, indent=2
        )
    )
    return 1 if report["failed_count"] or report["duration_mismatch_count"] else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
