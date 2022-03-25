Skybrush Studio for Blender
===========================

This repo contains [Skybrush Studio for Blender](https://skybrush.io),
a professional drone show designer framework integrated into
[Blender](https://blender.org).

The output of Skybrush Studio for Blender is a single `.skyc` file, which
contains the trajectories and light programs for all the drones in the show.
Using `.skyc` files together with the [Skybrush suite](https://skybrush.io)
allows you to preview, validate, verify, analyze, plot and execute drone shows
with a few clicks.

Installation
------------

[Skybrush Studio for Blender](https://skybrush.io) is distributed either as a
ZIP file that can be installed in Blender according to the official
[Blender add-on guide](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html),
or as a stand-alone executable that can be placed next to Blender's own
executable. The latter solution allows one to use Skybrush Studio for Blender
in a way that does not alter the Blender environment -- the source code of the
plugin is unpacked and piped into Blender at startup time.

However, this repository does not contain the ZIP version of the plugin or the
standalone executables but the _source code_ of the plugin. Therefore, in order
to create the ZIP version and the executables on your own, you either need to
[download it from us](https://skybrush.io) or [build the ZIP
yourself](#building-the-plugin). Once you obtained the ZIP version of the
plugin, follow the installation guide in our [online
documentation](https://doc.collmot.com/public/skybrush-studio-for-blender/latest/install.html)

To install standalone add-ons, such as the .csv exporter, you can follow the official Blender add-on install guide.

Building the plugin
-------------------

The build process is tested on macOS at the moment. It is very likely to work
on Linux as well. On Windows, you can try building inside Cygwin or Windows
Subsystem for Linux; the build script is written in `bash` so you will
definitely need an environment that provides `bash`.

The build script can be executed as follows:

```sh
$ bash etc/scripts/create_blender_dist.sh
```

When successful, the script creates the ZIP bundle of the addon in the `dist/`
folder.

Development
-----------

If you want to modify the plugin and add your own functionality, the easiest is
to set up a folder that can be used directly as an entry in the Blender addon
path. This way you can modify the source code of the plugin without having to
build a ZIP after every modification.

First, run `poetry install` in the root folder of the repository to install the
dependencies of the plugin.

Next, on Linux or macOS, you can run `etc/scripts/bootstrap.sh` to create a folder
named `dev/` within the repository. This folder sets up symbolic links in a
way that allows you to load the plugin directly if you add the `dev/` folder to
your Blender addon path. On Windows, you can achieve the same thing by running
`etc/scripts/bootstrap_windows.bat`.

Note that you might still need to exit Blender and restart it again if you
make a modification to the plugin code to ensure that your modifications are
picked up by Blender.

Support
-------

For any support questions please contact us on our [Discord server](https://skybrush.io/r/discord).

License
-------

Copyright 2020-2022 CollMot Robotics Ltd.

Skybrush Studio for Blender is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

Skybrush Studio for Blender is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.
