# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2022-06-17

### Added

- Staggered transitions (i.e. transitions where drones depart and arrive with a
  pre-defined delay between consecutive drones).

- Formation reordering operators (needed to define the order of drones in
  staggered transitions).

### Changed

- The plugin is now primarily released as a standard Blender add-on ZIP instead
  of a pre-compiled executable as the executable did not work reliably on
  Windows for some users.

### Fixed

- Fixed a bug that prevented the plugin from finding the shader node
  responsible for the color of the LED of the drone when Blender was used in
  a non-English locale.

- Fixed the placement of the safety check overlay in the upper left corner of
  the 3D view if the statistics overlay is also turned on.

- The safety check overlay is now hidden when the "Show Overlays" setting is
  turned off in the 3D view.

## [2.0.0] - 2022-03-25

This is the release that serves as a basis for changelog entries above. Refer
to the commit logs for changes affecting this version and earlier versions.
