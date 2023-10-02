# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The plugin now supports takeoff grids where multiple drones occupy the same
  takeoff slot within safety distance (e.g., four drones in a pod at the same
  takeoff location). The takeoff, RTH and landing operators were redesigned to
  cater for dense takeoff grids.

- You can now import dynamic formations from a ZIP file containing CSV files,
  one per drone. See the documentation for more details about the format of the
  CSV file.

- Added support for creating a static formation from a QR code where each drone
  becomes a single dot in the QR code.

- The Formations panel now shows a warning if the selected formation does not
  have the same amount of markers as the number of drones in the show. This is
  because in this case we are not able to plan transitions into the formation
  as we would not know what to do with the missing/excess drones.

- Transitions can now be marked as locked. Keyframes corresponding to the
  locked transitions are never modified by transition recalculations.

- You can now tweak the departure and arrival times of individual drones within
  a transition with schedule overrides. This can be used to resolve collisions
  during a staggered transition manually, or to manually create more complex
  transition patterns.

- The Export panel now has a button that can be used to query the server about
  any additional supported file formats besides .skyc and CSV. Additional
  export operators will appear for third-party file formats if the server
  supports them. Note that the community server still supports .skyc and CSV only.
  Contact us for local deployments of the server with support for third-party
  file formats if you are interested.

### Fixed

- View scaling setting from the Blender preferences is now taken into account
  properly when drawing overlays on the 3D view.

## [2.8.0] - 2023-02-16

### Added

- An "Export validation report" button is now available on the Export tab on
  the Safety & Export panel to be able to create a detailed safety report of the
  show in PDF format. _This feature is available for Pro users only._

- Timeline markers are now exported to the .skyc files and to the .pdf
  validation report also.

- The LED panel now contains a slider to adjust the emission strength of the
  materials of all the drones. This can be used to make the drones brighter for
  pre-visualisation purposes.

- Light effects can now be blended using several commonly used blend modes
  (normal, multiply, overlay, screen, soft light, hard light and so on).

### Changed

- CSV export was moved to the server side to allow us to fix issues with the
  CSV exporter more easily.

### Fixed

- CSV export now supports shows with dynamic light effects; earlier versions
  exported only the base color of each drone with the keyframed animations,
  but not the dynamic light effects.

## [2.7.0] - 2022-11-02

### Added

- Gradient and distance-based light effects can now operate in "ordered" and
  "proportional" mode. In the legacy "ordered" mode, drones are sorted first
  based on their coordinates or distances, and then they are distributed evenly
  along the color ramp. In the new "proportional" mode, the drones are
  distributed along the color ramp in a way that their distances on the color
  ramp are proportional to their distances or coordinates in the scene itself.

### Fixed

- Fixed resizing handle of the main list in the Light Effects panel.

## [2.6.1] - 2022-10-18

### Fixed

- Fixed a bug in the `.skyc` export process that resulted in incorrect altitude
  and proximity thresholds saved into the generated `.skyc` file. (The
  "Validate Trajectories" button was unaffected).

## [2.6.0] - 2022-10-04

### Added

- Randomness property of light effects is now animatable.

### Fixed

- "Update Time Markers" operator will not remove markers created manually by the
  user any more. (You need to execute the operator at least once first to
  trigger this new behaviour).

## [2.5.0] - 2022-09-04

### Added

- Added a randomness slider to the Light effects panel, which can be used to
  spread out the drones on the color ramp of a light effect in a uniform manner.
  This is useful for creating sparks and other effects that depend on randomness.

- Added an option to limit a light effect in the Light effects panel to one
  side of an infinite plane. This is computationally less expensive than a full
  containment test.

### Fixed

- Running instances of Skybrush Viewer are now detected correctly on macOS even
  if the user is not connected to any network at all. (The issue may have
  affected Windows and/or Linux as well, but we encountered it on macOS).

## [2.4.0] - 2022-08-21

### Added

- Added "Current formation or transition" as a possible option for the frame
  range when exporting.

### Fixed

- Vertex group based formations now work correctly even if the underlying mesh
  has modifiers. Before this patch, the modifiers were not taken into account
  when the positions of the vertices in the vertex group were sampled for a
  transition calculation.

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
