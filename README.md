# Skybrush Studio for Blender

This repo contains [Skybrush Studio for Blender](https://skybrush.io), a professional drone show designer framework integrated into Blender.

Tehcnically speaking, Skybrush Studio for Blender is set of add-ons and operators for Blender with complex functionality related to drone show design.

The output of Skybrush Studio for Blender is a single .skyc file. Using .skyc files together with the Skybrush Suite allows you to preview, validate, verify, analyze, plot and execute drone shows with a few clicks.

# Install

To install Skybrush Studio for Blender, **DO NOT** follow the official
[Blender add-on guide](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html),
as it does not give a solution to easily install external Python dependencies.

Instead, a complete installation guide is available in the [online documentation](https://doc.collmot.com/public/skybrush-plugin-blender/latest/install.html)

To install standalone add-ons, such as the .csv exporter, you can follow the official Blender add-on install guide.

# List of available add-ons

## Skybrush Studio for Blender (ui_skybrush_studio.py)

This is the single add-on that creates the Skybrush Studio designer framework in Blender.

## Skybrush .SKY Importer (io_import_skybrush.py)

This add-on lets you import drone shows created in the Skybrush Studio Script Language (.sky).

This add-on needs skybrush-studio as a dependency and is only available for developers for the time being.

## Skybrush .CSV Exporter (io_export_skybrush_csv.py)

This add-on lets you export your drone show into a skybrush-compatible CSV Format (.csv).

This is a standalone add-on for those who work in their own design framework but need to use Skybrush Viewer or Live, or want to post-process or use shows designed in Skybrush Studio for Blender in other softwares.

We offer an online tool for converting .csv shows into .skyc at https://account.skybrush.io/tools.
To use the online converter, you need to register an account at https://account.skybrush.io.

## Skybrush Compiled Format Legacy Exporter (io_export_skybrush_legacy.py)

This is our deprecated, separate add-on for exporting into Skybrush Compiled Format (.skyc) - by now the .skyc export is integrated into Skybrush Studio for Blender.

# Support

For any support questions please contact us at hello@skybrush.io.