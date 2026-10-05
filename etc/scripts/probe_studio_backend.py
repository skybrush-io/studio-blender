"""Capture synthetic API examples through the user's licensed Studio Gateway.

Run explicitly with Python. Signatures stay in memory; only synthetic inputs,
calculation responses and timings are saved. No Blender preferences are changed.
"""

import argparse
import json
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(endpoint, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    signature_request = Request(
        "http://127.0.0.1:7999/sign",
        data=body or b"",
        headers={"Content-Type": "application/octet-stream"},
    )
    with urlopen(signature_request, timeout=10) as response:
        signature = response.read().decode()
    headers = {"X-Skybrush-Request-Signature": signature}
    if body is not None:
        headers["Content-Type"] = "application/json"
    query = Request(
        f"https://studio.skybrush.io/api/v1/{endpoint}",
        data=body,
        headers=headers,
    )
    with urlopen(query, timeout=45) as response:
        return response.read(), response.headers.get_content_type()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = [[0, 0, 0], [4, 0, 0], [8, 0, 0]]
    target = [[8, 0, 6], [0, 0, 6], [4, 0, 6]]
    motion = {
        "version": 1,
        "source": source,
        "target": target,
        "max_velocity_xy": 4,
        "max_velocity_z": 2,
        "max_acceleration": 2,
    }
    cases = [
        ("version", "queries/version", None),
        ("limits", "queries/limits", None),
        (
            "matching",
            "operations/match-points",
            {
                "version": 1,
                "source": source,
                "target": target,
                "radius": 0.5,
            },
        ),
        (
            "transition",
            "operations/plan-transition",
            {
                **motion,
                "transition_method": "const_jerk",
                "matching_method": "optimal",
            },
        ),
        (
            "takeoff",
            "operations/plan-takeoff",
            {
                "version": 1,
                "points": source,
                "min_distance": 5,
            },
        ),
        (
            "landing",
            "operations/plan-landing",
            {
                "version": 1,
                "points": target,
                "min_distance": 5,
                "velocity": 2,
                "target_altitude": 0,
                "spindown_time": 5,
            },
        ),
        (
            "smart-rth",
            "operations/plan-smart-rth",
            {
                **motion,
                "source": target,
                "target": source,
                "min_distance": 3,
                "rth_model": "straight_line_with_neck",
            },
        ),
        (
            "skyc",
            "operations/render",
            {
                "input": {
                    "format": "json",
                    "data": {
                        "version": 1,
                        "environment": {"type": "outdoor"},
                        "settings": {"validation": {"minDistance": 3}},
                        "swarm": {
                            "drones": [
                                {
                                    "type": "generic",
                                    "settings": {
                                        "name": "Synthetic probe",
                                        "trajectory": {
                                            "version": 1,
                                            "points": [
                                                [0, [0, 0, 0], []],
                                                [6, [0, 0, 6], []],
                                            ],
                                        },
                                        "lights": {
                                            "version": 1,
                                            "data": [
                                                [0, [255, 0, 0], 0],
                                                [6, [0, 0, 255], 1],
                                            ],
                                        },
                                    },
                                }
                            ]
                        },
                        "meta": {"title": "Synthetic compatibility probe"},
                        "media": {},
                    },
                },
                "output": {"format": "skyc"},
            },
        ),
    ]
    records = []
    for name, endpoint, payload in cases:
        start = perf_counter()
        record = {"name": name, "endpoint": endpoint, "input": payload}
        try:
            body, content_type = request(endpoint, payload)
            if "json" in content_type:
                record["response"] = json.loads(body)
            else:
                filename = f"{name}.skyc" if name == "skyc" else f"{name}.bin"
                (args.output / filename).write_bytes(body)
                record["artifact"] = filename
                record["bytes"] = len(body)
            record["status"] = "ok"
        except HTTPError as error:
            record["status"] = f"HTTP {error.code}"
        except Exception as error:
            record["status"] = type(error).__name__
        record["seconds"] = round(perf_counter() - start, 3)
        records.append(record)
        print(name, record["status"], flush=True)
        (args.output / "observations.json").write_text(json.dumps(records, indent=2))


if __name__ == "__main__":
    main()
