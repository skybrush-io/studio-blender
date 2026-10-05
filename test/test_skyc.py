from io import BytesIO
from json import loads
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from sbstudio.skyc import render_skyc_archive


class Serializable:
    def __init__(self, value):
        self.value = value

    def as_dict(self, **kwargs):
        return self.value


class FakeTrajectory(Serializable):
    def __init__(self):
        super().__init__(
            {
                "version": 1,
                "points": [[0, [1, 2, 0], []], [5, [4, 5, 6], []]],
            }
        )
        self.points = [
            SimpleNamespace(x=1, y=2, z=0),
            SimpleNamespace(x=4, y=5, z=6),
        ]


def test_local_skyc_writer_creates_complete_archive(tmp_path):
    data = render_skyc_archive(
        {"Drone 1": FakeTrajectory()},
        {"Drone 1": Serializable({"version": 1, "data": [[0, [255, 0, 0], 1]]})},
        validation=Serializable({"minDistance": 4}),
        show_title="Offline test",
        show_type="outdoor",
        show_location=None,
        show_segments={"show": (0, 5)},
        time_markers=Serializable(
            {"version": 1, "items": [{"name": "start", "time": 0}]}
        ),
        yaw_setpoints=None,
        validation_report={"version": 1, "failed_checks": ["separation"]},
    )
    output = tmp_path / "draft.skyc"
    output.write_bytes(data)

    assert output.stat().st_size > 0
    with ZipFile(output) as archive:
        assert set(archive.namelist()) == {
            "cues.json",
            "show.json",
            "validation.json",
            "drones/Drone_1/trajectory.json",
            "drones/Drone_1/lights.json",
        }
        show = loads(archive.read("show.json"))
        cues = loads(archive.read("cues.json"))
        trajectory = loads(archive.read("drones/Drone_1/trajectory.json"))
        lights = loads(archive.read("drones/Drone_1/lights.json"))
        assert loads(archive.read("validation.json"))["failed_checks"] == ["separation"]

    assert data.startswith(b"PK")
    assert show["version"] == 1
    assert show["meta"]["title"] == "Offline test"
    assert show["meta"]["skybrushExport"]["flight_approved"] is False
    assert show["settings"]["validation"]["minDistance"] == 4
    assert show["swarm"]["drones"][0]["settings"]["home"] == [1, 2, 0]
    assert show["swarm"]["drones"][0]["settings"]["landAt"] == [4, 5, 6]
    assert cues["items"] == [{"name": "start", "time": 0}]
    assert trajectory["version"] == 1
    assert lights["version"] == 1


def test_local_skyc_writer_disambiguates_safe_directory_names():
    data = render_skyc_archive(
        {"Drone / 1": FakeTrajectory(), "Drone ? 1": FakeTrajectory()},
        None,
        validation=Serializable({}),
        show_title=None,
        show_type="indoor",
        show_location=None,
        show_segments=None,
        time_markers=Serializable({"version": 1, "items": []}),
        yaw_setpoints=None,
    )

    output_names = set()
    with ZipFile(BytesIO(data)) as archive:
        output_names.update(archive.namelist())

    assert "drones/Drone_1/trajectory.json" in output_names
    assert "drones/Drone_1_2/trajectory.json" in output_names


def test_nonfinite_json_metadata_is_rejected():
    with pytest.raises(ValueError, match="JSON"):
        render_skyc_archive(
            {"A": FakeTrajectory()},
            None,
            validation=Serializable({}),
            show_title=None,
            show_type="outdoor",
            show_location=None,
            show_segments=None,
            time_markers=Serializable({"time": float("nan")}),
            yaw_setpoints=None,
        )
