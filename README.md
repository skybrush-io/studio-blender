# Dronetara Studio

Dronetara Studio is an open-source drone show designer integrated into
[Blender](https://blender.org). It supports local design workflows for
100–500+ drones without a configured server or an add-on-enforced drone-count
limit.

Dronetara Studio can export a local zipped CSV representation for downstream
tools. Compiled `.skyc` output and certain advanced operations still require a
compatible Skybrush Studio backend and its applicable license.

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
`dist/dronetara-studio-for-blender-5.0.3.zip`.

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
landing planning, and zipped CSV export. See
[`doc/offline-design.md`](doc/offline-design.md) for installation, usage, and
important safety and export limitations.

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
