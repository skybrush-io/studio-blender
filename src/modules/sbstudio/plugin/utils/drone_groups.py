"""Drone group utilities for Starlight Animator integration (v4.8.0+).

Each drone has a custom property ``sb_group`` with one of the values:
- ``""`` (unset): drone is untagged, treated as ALL group
- ``"BOX"``: box-array drone (typically no payload, take off in interleaved layers)
- ``"TRAD"``: traditional single-drone array (typically pyrotechnics-equipped)

A storyboard entry can have ``limit_to_group`` set to ``"ALL"``, ``"BOX"`` or
``"TRAD"``. When the planner processes a transition, only the drones matching
the entry's group participate in the matching/movement. Non-participating
drones keep their previous position (no new constraint created for them).
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

GROUP_BOX = "BOX"
GROUP_TRAD = "TRAD"
GROUP_ALL = "ALL"


def get_drone_group(drone) -> str:
    """Return the group tag of a drone object. Empty string if untagged."""
    try:
        return str(drone.get("sb_group", "") or "")
    except Exception:
        return ""


def set_drone_group(drone, group: str) -> None:
    """Set the drone's group tag. Use one of GROUP_BOX / GROUP_TRAD / ""."""
    if group:
        drone["sb_group"] = group
    elif "sb_group" in drone.keys():
        del drone["sb_group"]


def get_participating_indices(drones: Sequence, limit: str) -> List[int]:
    """Return indices of drones that participate in a transition with the given limit.

    - ``limit == "ALL"`` or empty: all drones participate.
    - ``limit == "BOX"`` / ``"TRAD"``: only drones tagged with that group participate.
      If NO drone is tagged at all (legacy project), ALL drones participate
      (graceful fallback so old projects still work).
    """
    if not limit or limit == GROUP_ALL:
        return list(range(len(drones)))
    
    # Check if any drone has a tag at all
    has_any_tag = any(get_drone_group(d) for d in drones)
    if not has_any_tag:
        # Legacy project - no tags exist, treat as ALL
        return list(range(len(drones)))
    
    return [i for i, d in enumerate(drones) if get_drone_group(d) == limit]


def auto_tag_drones_by_count(drones: Sequence, box_count: int, trad_count: int) -> int:
    """Tag drones by index: first ``box_count`` as BOX, next ``trad_count`` as TRAD.
    
    Returns the number of drones tagged.
    """
    tagged = 0
    n = len(drones)
    for i, d in enumerate(drones):
        if i < box_count:
            set_drone_group(d, GROUP_BOX)
            tagged += 1
        elif i < box_count + trad_count:
            set_drone_group(d, GROUP_TRAD)
            tagged += 1
    return tagged


def count_groups(drones: Sequence) -> dict:
    """Return a dict with counts of drones per group."""
    counts = {GROUP_BOX: 0, GROUP_TRAD: 0, "": 0}
    for d in drones:
        g = get_drone_group(d)
        counts[g] = counts.get(g, 0) + 1
    return counts


def infer_limit_from_formation_size(num_markers: int, drones: Sequence) -> str:
    """Try to auto-infer limit_to_group based on formation marker count.

    Returns ``"BOX"``, ``"TRAD"``, or ``"ALL"`` (default).
    """
    counts = count_groups(drones)
    if num_markers == counts.get(GROUP_BOX, 0) and counts.get(GROUP_BOX, 0) > 0:
        return GROUP_BOX
    if num_markers == counts.get(GROUP_TRAD, 0) and counts.get(GROUP_TRAD, 0) > 0:
        return GROUP_TRAD
    return GROUP_ALL
