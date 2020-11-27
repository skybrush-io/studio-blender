# Blender Add-ons for Skybrush

This repo contains add-ons for Blender that aid drone show design and compatibility with the [Skybrush Suite](https://skybrush.io).


# Install

To install Skybrush-specific Blender add-ons, **DO NOT** follow the official
[Blender add-on guide](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html),
as it does not give a solution to easily install external python dependencies.

Instead, do the followings:

  1. Run the installer that is...<br>
  **TODO**: not yet provided :).<br>
  This should copy all add-ons and dependencies inside the default Blender scripts folder.

  2. Activate the preferred add-ons in the _Add-ons_ section of _Preferences_ by clicking on the checkbox on the left side of the given add-ons.<br>
  **Hint**: filter for _User_ to increase visibility by listing only user-specific add-ons such as the ones for Skybrush.


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

# Support

For any support questions please contact us at support@collmot.com.