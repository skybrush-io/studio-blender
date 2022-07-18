# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.1] - 2022-07-18

### Fixed

- Fixed a bug in the .skyc trajectory export that sometimes resulted in
  overshoots during long segments when a drone was supposed to hover in place.

## [2.3.0] - 2022-07-14

### Added

- Light effects can now be duplicated in the Light effects panel of the LEDs
  tab with a dedicated button.

- Velocity limits can now be different for descents and ascents.

### Fixed

- When a storyboard entry is removed, the plugin now removes all constraints
  related to the storyboard entry from the constraint stack of all drones.

- When a formation is removed completely, constraints between drones and
  storyboard entries referring to the removed formation are also removed.

## [2.2.0] - 2022-06-26

### Added

- You can now configure the add-on to use a local instance of the Skybrush
  Studio server to run transition calculations and `.skyc` exports locally.

- When exporting to `.skyc`, you can now choose to export lights and trajectories
  at different FPS. Typically, 4 or 5 fps for trajectories is enough, while
  lights can go all the way up to 24, 25 or 30 fps, depending on what you use
  in your project.

### Fixed

- CSV export button now automatically sets the extension of the output file
  to `.zip` when the operator is invoked (unless the output filename is already
  specified).

- Dynamic light effects are now exported correctly in Blender 3.0 and above.

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
