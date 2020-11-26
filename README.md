# Blender Add-ons for Skybrush

This repo contains add-ons for Blender that aid drone show design and compatibility with the [Skybrush Suite](https://skybrush.io).


## Install

To install Skybrush-specific Blender add-ons, follow the official
[Blender add-on guide](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html). Steps specific to this repo:

 1. Set the main repo folder as the _Scripts_ path in the _File Paths_ section of the _Preferences_.
 2. Enable the preferred add-ons in the _Add-ons_ section of _Preferences_


# List of available add-ons


## Skybrush Importer (io_import_skybrush.py)

This add-on lets you import drone shows created in Skybrush Studio (.sky).


## Skybrush Exporter (io_export_skybrush.py)

This add-on lets you export your drone show into Skybrush Compiled Format (.skyc).

Using .skyc files together with the Skybrush Suite allows you to preview, validate, verify, analyze, plot and execute drone shows with a few clicks.

There are two methods for compiling to .skyc:

 1.  If you are authorized to have the `pyledctrl` and `skybrush` python modules, create a symlink to these in the `modules` folder.

 2.  We offer an online tool for converting drone shows into .skyc, which is called automatically by this add-on. To use the online converter, you need to register an acoount at https://account.skybrush.io.

The exporter plugin will decide automatically which route is available for you.