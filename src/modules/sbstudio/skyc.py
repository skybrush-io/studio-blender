"""Minimal, dependency-free writer for unoptimized SKYC archives."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sbstudio.light_bytecode import compile_light_keyframes
from sbstudio.math.motion_diagnostics import normalize_phases

_SAFE_FILENAME_PART = re.compile(r"[^A-Za-z0-9_.-]+")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode(
        "utf-8"
    )


def _safe_directory_names(names: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for index, name in enumerate(names, start=1):
        stem = _SAFE_FILENAME_PART.sub("_", name).strip("._") or f"Drone_{index}"
        candidate = stem
        suffix = 2
        while candidate.casefold() in used:
            candidate = f"{stem}_{suffix}"
            suffix += 1
        used.add(candidate.casefold())
        result[name] = candidate
    return result


def render_skyc_archive(
    trajectories: Mapping[str, Any],
    lights: Mapping[str, Any] | None,
    *,
    validation: Any,
    show_title: str | None,
    show_type: str,
    show_location: Any | None,
    show_segments: Mapping[str, tuple[float, float]] | None,
    time_markers: Any,
    yaw_setpoints: Mapping[str, Any] | None,
    validation_report: dict | None = None,
) -> bytes:
    """Create an interoperable, unoptimized SKYC ZIP archive.

    Inputs use the existing model objects' ``as_dict()`` interfaces. Keeping
    this module free of Blender imports also makes the archive writer directly
    testable with lightweight stand-ins.
    """
    directory_names = _safe_directory_names(list(trajectories))
    drones: list[dict[str, Any]] = []
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("cues.json", _json_bytes(time_markers.as_dict()))

        for name, trajectory in trajectories.items():
            directory = f"drones/{directory_names[name]}"
            trajectory_path = f"{directory}/trajectory.json"
            lights_path = f"{directory}/lights.json"
            light_program = lights.get(name) if lights is not None else None

            archive.writestr(
                trajectory_path, _json_bytes(trajectory.as_dict(version=1))
            )
            archive.writestr(
                lights_path,
                _json_bytes(
                    {
                        "version": 1,
                        "data": compile_light_keyframes(
                            light_program.as_dict()["data"]
                            if light_program is not None
                            else []
                        ),
                    }
                ),
            )

            first, last = trajectory.points[0], trajectory.points[-1]
            settings: dict[str, Any] = {
                "name": name,
                "trajectory": {"$ref": f"./{trajectory_path}#"},
                "lights": {"$ref": f"./{lights_path}#"},
                "home": [round(first.x, 3), round(first.y, 3), round(first.z, 3)],
                "landAt": [round(last.x, 3), round(last.y, 3), round(last.z, 3)],
            }
            if yaw_setpoints is not None and name in yaw_setpoints:
                settings["yawControl"] = yaw_setpoints[name].as_dict()
            drones.append({"type": "generic", "settings": settings})

        environment: dict[str, Any] = {"type": show_type}
        if show_location is not None:
            environment["location"] = show_location.json

        meta: dict[str, Any] = {"generator": "Dronetara Studio offline exporter"}
        if validation_report is not None:
            meta["dronetaraExport"] = validation_report.get(
                "export_gate",
                {
                    "status": "preview_only",
                    "flight_approved": False,
                },
            )
        if show_title:
            meta["title"] = show_title
        phases, _ = normalize_phases(show_segments)
        if phases:
            meta["segments"] = {name: [start, end] for start, end, name in phases}

        show = {
            "version": 1,
            "settings": {
                "cues": {"$ref": "./cues.json"},
                "validation": validation.as_dict(),
            },
            "swarm": {"drones": drones},
            "environment": environment,
            "meta": meta,
            "media": {},
        }
        archive.writestr("show.json", _json_bytes(show))
        if validation_report is not None:
            archive.writestr("validation.json", _json_bytes(validation_report))

    return buffer.getvalue()
