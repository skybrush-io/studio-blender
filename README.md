# Dronetara Studio

Dronetara Studio is an open-source drone show designer integrated into
[Blender](https://blender.org). It supports local design workflows for
100–500+ drones without a configured server or an add-on-enforced drone-count
limit.

Dronetara Studio can export local zipped CSV and unoptimized draft `.skyc`
archives for downstream tools. Version 5.10.0 defaults to checked offline drafts:
known violations block saving, a full-storyboard dense motion audit is required,
and preview exports are explicitly marked. Passing these checks is not flight
approval. Certain optional operations still require a compatible backend and its
applicable license; commercial-flight acceptance is a separate process.

## Installation

Dronetara Studio is distributed as a ZIP file that can be installed in Blender
according to the official
[Blender add-on guide](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html).
This repository contains the source code; build the installable ZIP locally as
described below.

## Building the plugin

The build process is tested on macOS at the moment. It is very likely to work
on Linux as well. On Windows, you can try building inside Cygwin or Windows
Subsystem for Linux; the build script is written in `bash` so you will
definitely need an environment that provides `bash`.

The build script can be executed as follows:

```sh
bash etc/scripts/create_blender_dist.sh
```

When successful, the script creates
`dist/dronetara-studio-for-blender-5.10.0.zip`.

In Blender, disable or uninstall any older **Skybrush Studio** entry, then use
**Preferences → Add-ons → Install from Disk** to install that ZIP. Enable
**Dronetara Studio** and select **Offline design (experimental)** in its
preferences for the local 100–500+ drone workflow.

Fully quit and restart Blender after replacing Skybrush Studio. The legacy and
Dronetara entry points use the same internal Python package, so Blender cannot
safely switch between them by hot-reloading add-ons in an existing session.

## Development

If you want to modify the plugin and add your own functionality, the easiest is
to set up a folder that can be used directly as an entry in the Blender addon
path. This way you can modify the source code of the plugin without having to
build a ZIP after every modification.

First, run `uv sync` in the root folder of the repository to install the
dependencies of the plugin.

Next, on Linux or macOS, you can run `etc/scripts/bootstrap.sh` to create a folder
named `dev/` within the repository. This folder sets up symbolic links in a
way that allows you to load the plugin directly if you add the `dev/` folder to
your Blender addon path. On Windows, you can achieve the same thing by running
`etc/scripts/bootstrap_windows.bat`.

Note that you might still need to exit Blender and restart it again if you
make a modification to the plugin code to ensure that your modifications are
picked up by Blender.

### Experimental offline design mode

This edition includes an experimental **Offline design** operation mode for large
local designs that do not need the proprietary Skybrush Studio Server. It adds
local formation matching, transition-duration estimates, layered takeoff and
checked landing/Smart RTH, and zipped CSV export. See
[`doc/offline-design.md`](doc/offline-design.md) for installation, usage, and
important safety and export limitations.

### Designer rollout and offline export

Use this build for a controlled internal authoring/review rollout, not as a
blanket approval to fly shows at paid events. In Offline mode, SKYC export
defaults to **Checked draft**, all drones and the full **Storyboard** range.
The exporter always performs a half-frame motion audit in this mode and refuses
known separation, altitude, speed, acceleration-estimate, audit-coverage or
export-fidelity failures before replacing the destination. Checked export also
rejects yaw control until its validation is implemented.

The default **Export tolerance (m)** is 0.05 m. It limits sampled authoring/export
differences, not GPS uncertainty, tracking error or a flight safety buffer. Do
not raise this tolerance or aircraft limits merely to silence a failure.

**Preview only** explicitly permits unfinished drafts and partial clips for
inspection. Its warning/status is saved inside the SKYC; third-party consumers
may ignore this metadata, so the file is not technically prevented from upload.
Never use preview output as flight approval. A newly opened export dialog resets
to Checked draft. Background export remains optional and supports Esc cancellation.

General Blender motion bounds, ground/flight-state policy, controller/upload
compatibility and operational acceptance remain outside this release's completed
scope. See [the production checklist](doc/production-checklist.md) for the evidence
and release boundaries. Successful export or Viewer playback is not a substitute.

### Checked offline landing and Smart RTH — 5.10.0

In Offline mode, **Land Drones** and **Return Drones to Home Positions** always
use the checked local planner. No Studio server, Gateway or server license is
needed for these operations. Start at the final storyboard frame; the dialog
chooses it automatically. Speeds are maxima, capped by the scene's configured
safety thresholds. The complete generated curves include climb, crossing return
routes, descent, stationary drones and endpoint holds.

Smart RTH uses separate altitude layers for conflicting horizontal routes and
returns each drone to its own first-storyboard position, including its actual Z
height. **Return to aerial grid** stops at the requested altitude instead.
The altitude ceiling is enforced. Close home/landing slots, unsafe vertical
columns and routes needing too many layers are rejected before animation is
changed. This conservative planner may reject a layout for which a different
route exists; it does not silently reduce spacing or change drone assignments.
No motor-spindown or landed-drone spacing exemption is assumed.

Generated entries are locked against ordinary transition recalculation. Editing
or unlocking their curves invalidates the construction checks. Always re-export
the full show with **Checked draft**, since the preceding show and exported path
are checked separately. This authored RTH is **not emergency controller RTH** and
does not assess obstacles, terrain, downwash, tracking uncertainty or endurance.

The same installer is intended for macOS and Windows; it contains no Mac-only
runtime binary. **Windows execution/GUI acceptance remains unverified** until
the included [Windows acceptance procedure](doc/windows-qa.md) is run and reviewed.
Installing the ZIP does not require building it or running Bash on Windows.

## Support

Use the [Dronetara Studio issue tracker](https://github.com/DRONETARA/studio-blender/issues)
for bugs and support requests.

## License

Copyright 2020-2025 CollMot Robotics Ltd.

Dronetara Studio is based on the open-source Skybrush Studio for Blender codebase.
Skybrush and its associated product names remain the property of their respective
owners. The original copyright and GPL terms are retained.

Dronetara Studio is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

Dronetara Studio is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.

## Utility script: light effect preset GIF previews

The repository also contains `etc/scripts/render_light_effect_preset_gifs.py`,
a helper script that renders animated GIF previews for all built-in light
effect presets.

The script evaluates each preset on a sunflower-seed drone layout and saves one
GIF per preset. It also supports options for the output folder, drone count,
and whether a connector line should be drawn between consecutive drones.

Example usage:

```sh
uv run --with pillow python etc/scripts/render_light_effect_preset_gifs.py
```

For instance, to render previews for 100 drones into `tmp/light-effect-gifs/`
and draw the connector line:

```sh
uv run --with pillow python etc/scripts/render_light_effect_preset_gifs.py \
  --output-dir tmp/light-effect-gifs \
  --drone-count 100 \
  --draw-connector-line
```
