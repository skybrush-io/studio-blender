# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## main

### Added

- Added light effect import/export feature.

- Added export option for combined/parallel .skyc and .pdf exports to save time on final
  drone show renderings.

- Added mandatory backend version check before dispatching the first request to
  the current server instance.

### Changed

- The minimum backend version required for this version of the add-on is now
  2.29.0.

- Trajectories sent to the backend use a new, compact binary format to speed up
  render requests and save some bandwidth towards remote backends.

### Fixed

- Fixed CUSTOM y output mode of light effects that previously used x output functions
  accidentally.

## [3.13.2] - 2025-06-29

- Fixed the discovery of principled BSDF shader nodes when Blender is localized
  and the node has a different name than what we expect.

## [3.13.1] - 2025-06-25

### Fixed

- Fixed a bug in the smart RTH calculation.

## [3.13.0] - 2025-06-18

### Added

- Added a new panel to allow the designer to add pyro trigger events to drones.

- Pyro effects can be visualized in the 3D view with markers (faster) or with
  Blender particle systems (slower but more spectacular).

- There is a new option for the smart RTH operator to return to an aerial grid
  above home only instead of landing to the takeoff grid at the end. The new
  method also uses a new algorithm in the backend that ensures that minimum
  distance requirements are not violated during the return to the aerial grid.
  This is achieved by returning to an enlarged grid first and shrinking that
  at the end horizontally to reach the final required aerial grid.

### Fixed

- Default formation entry purpose upon opening old non-annotated Blender files
  became `UNSPECIFIED`. In these cases user needs to mark purpose of all
  entries manually to have a valid segment annotation on export.

## 3.12.1 - 2025-06-04

### Fixed

- Removed a few debug statements that were accidentally left in the code and
  broke things for Blender 4.2 and earlier versions.

## [3.12.0] - 2025-06-02

## Added

- The "Generate markers" feature has a new option that imports zipped DSS
  PATH/PATH3 colored animations to better support modular show design
  even using external sources.

- Professional / paid features are now highlighted with a "(PRO)" tag.

### Fixed

- Fixed the generation of animated formation markers from CSV data in Blender
  4.4 due to the introduction of slotted actions in the Python API of Blender.

- Fixed a bug that prevented a newly added storyboard entry from being selected
  if the current formation was auto-assigned to it.

## [3.11.2] - 2025-05-21

### Fixed

- Images and videos that are being used as source material for light effects
  are now properly converted from sRGB to linear color space, thanks to
  @flopbuster

## [3.11.1] - 2025-05-06

### Fixed

- Fixed the icons showing the status of a light effect in the current frame;
  this broke in Blender 4.4 because the names of the icons changed.

- When exporting a partial frame range, it is now ensured that the time axis of
  the exported show file always starts at 0:00.

## [3.11.0] - 2025-04-03

### Added

- Added progress reporting for the time consuming export operations.
  To see progress or predicted remaining time, run Blender from a terminal
  window or press "Toggle System Console" in the "Windows" menu.

- Added custom spacing parameter for the takeoff, return to home and land
  operators. Users now can override the default spacing that is taken from the
  proximity warning threshold.

- Added support for proposing show origin and orientation for placing the show
  in the real world. Show origin and orientation from now on gets exported to
  .skyc show files and aid positioning of shows in Skybrush Live.

- Added an option to exporters that decides whether to keep on redrawing the
  current frame in the Blender window during export. Redrawing may slow down
  the export process significantly; on the other hand it provides visual
  feedback about the progress of the export and it is actually _necessary_ for
  video-based light effects to work properly.

- Added support for exporting drone shows into the Depence .ddsf format
  for integration with fireworks/events. Fireworks launched from drones are
  not yet supported, but trajectories, light animation and yaw setpoints
  are all saved.

### Fixed

- Video-based light effects now trigger a redraw for frames during export
  unless disabled explicitly. This is needed for the frames to propagate
  correctly to the exported .skyc file.

### Changed

- The layout of the add-on has been refactored. There is a new tab called
  "Skybrush" that contains configuration options for the show design workflow.
  This also shortens the Formation tab that now focuses on formations and
  nothing else.

## [3.10.0] - 2025-03-05

### Added

- Added support for exporting drone shows into the Finale 3D VVIZ format
  for integration with fireworks. Fireworks launched from drones are
  not yet supported, but trajectories, light animation and yaw setpoints
  are all saved.

### Changed

- The semantics of the "End frame" and "Duration" fields in the Storyboard and
  Light Effects panels was changed such that the end frame is _included_ in the
  affected frame range. This is to make things consistent with how Blender
  treats frame ranges in other parts of the application.

- The time fraction used in individual light effect calculations (in the
  temporal mode and in custom expressions) now scales such that it starts from
  zero at the start frame and reaches 1 at the end frame. In previous versions
  1 was never reached as the end frame was not part of the light effect.

### Fixed

- Disabled the caching of pixel data of image-based light effects between
  frames when the underlying image is a video file or an image sequence.

## [3.9.1] - 2025-02-24

### Fixed

- Temporarily removed option to use license files as API key. It will be
  only available for pro users at a later stage.

- Fixed an issue with creating new formations from selected vertices, due to
  changes in Blender's Python API in Blender 4.x.

- Added caching to the pixel data of image-based light effects because direct
  access to `bpy.types.Image.pixels` is slow in Blender. This should fix
  problems with low frame rates for scenes that use many image-based light
  effects.

## [3.9.0] - 2025-01-21

### Added

- Accelerations are now validated using a configurable acceleration threshold.

- Pro feature: new validation plot type added for predicting drift thoughout
  the entire show. This is a very important validation check to avoid situations
  when too high acceleration is expected from the drones and they will surely lag
  behind their expected trajectory and thus possibly crash with others.

### Removed

- Renderer parameter `min_nav_altitude` got removed as the new release of
  Skybrush Studio Server does not use it any more. Static starting and ending
  parts are still removed from show trajectories automatically, but now without
  the need of this parameter.

## [3.8.0] - 2024-12-23

### Added

- Blender cameras can be optionally exported into .skyc show files to be used by
  Skybrush Viewer.

- Added option to use the Skybrush license file as the API key for the cloud
  server.

- Storyboard entries can now be marked as being part of the takeoff, the show
  itself or the landing. These annotations will be used by Skybrush Live to
  re-design the takeoff and the landing dynamically when the takeoff grid
  changes on site, without having to re-design the entire show in Blender.

### Fixed

- Yaw angle conversion from Blender (CCW) to Skybrush (CW) representation fixed

## [3.7.1] - 2024-12-05

### Fixed

- Fixed wrap-around of yaw angles near +-180 degrees when exporting to .skyc

- Fixed compatibility issues with Blender 4.3 LTS where the bloom effect was
  removed from the EEVEE renderer.

## [3.7.0] - 2024-10-14

### Added

- The radius of the drone template object can be setup with the new "Drone radius"
  parameter before creating the first takeoff grid.

- Takeoff grid column spacing can be setup separately from row spacing, if needed.
  Takeoff grid parameters also got reorganized into basic and advanced groups.

### Fixed

- Fixed the "Stats" button in the formation panel so it does not throw an
  error any more.

- Improved the error message that appeared when trying to create a takeoff
  transition while online access is disabled in Blender.

## [3.6.0] - 2024-09-25

### Added

- Added "End Frame" fields in the Storyboard and Light effects panels; these are
  editable and implicitly adjust the duration of the storyboard entry or light
  effect.

- Added basic support for translating the plugin into other languages.

- Added Chinese translation. Huge thanks to PeiYi on our Discord server for
  providing the translation!

### Changed

- The add-on now respects the "Allow Online Access" setting from Blender when
  running on Blender 4.2 and later. You need to enable online access explicitly
  when using this add-on on Blender 4.2 and later.

### Fixed

- When selecting a start frame for the takeoff operation, the operator chooses
  in a way that it always falls between the first and the second formation.

## [3.5.0] - 2024-09-17

### Added

- Proximity warnings are now restricted to above the minimum navigation threshold
  only by default. You can switch back to the old behaviour in the safety
  settings panel if needed.

- Proximity warnings can now be executed manually on all pairs of drones in the
  current frame by pressing a button in the Safety panel.

### Fixed

- The name of the custom function file and the name of the selected function are
  now copied correctly when duplicating a light effect with a custom function.

## [3.4.2] - 2024-09-06

### Fixed

- Fixed a bug that was accidentally introduced in the transition calculation in
  version 3.4.1.

- Duplicating a light effect now uses numeric suffixes added to the original
  name, similarly to how Blender does it in its own code.

## [3.4.1] - 2024-08-26

### Changed

- Distances in the safety overlay are now shown with two decimal digits to
  cater for the needs of indoor shows.

### Fixed

- The add-on is now compatible with Blender 4.2 LTS.

- The constraints on the first storyboard entry now start at an influence of
  1.0 when the start of the scene coincides with the first storyboard entry
  (which is the typical case). This makes it slightly harder to mess up the
  takeoff procedure by moving drones around manually before the first storyboard
  entry.

## [3.4.0] - 2024-08-01

### Added

- Spatial constraints on light effects can now be inverted.

- "Inside the mesh" light effects now take mesh deformations into account. This
  may have a minor performance impact; if you experience slower-than-usual
  performance with scenes that have lots of "Inside the mesh" light effects,
  let us know.

- Light effects panel now shows which effects are active in the current frame.

- Safety warning overlays now use different colors for different types of
  safety warnings: red for proximity alerts (drones being too close),
  yellow for velocity alerts (drones moving too fast) and blue for altitude
  alerts (drones being too high or too low).

## [3.3.3] - 2024-03-19

### Fixed

- Fixed a bug that prevented exported CSV formations from being re-imported
  into another project.

## [3.3.2] - 2024-03-12

### Fixed

- Fixed a bug that sometimes resulted in a crash or out-of-memory errors when
  duplicating light effects.

## [3.3.1] - 2024-03-08

### Fixed

- Copying light effects resulted in an error due to the newly added properties
  for selecting functions to use for coloring. A temporary fix has been
  introduced to restore the old functionality _without_ copying the associated
  function.

## [3.3.0] - 2024-03-07

### Added

- Smart RTH is not an experimental feature any more. Feel free to test it and
  report any issues that you run into while using smart RTH transitions, but
  note that the calculation is done on our servers and we reserve the right to
  make smart RTH transitions a feature for pro users only in the future.

### Fixed

- Fixed a problem with light effects when trying to index into a color image
  whose width or height was zero.

- Fixed a problem with repeated smart return-to-home transitions when the
  animation data of the previous smart RTH attempt was accidentally kept in the
  keyframes.

## [3.2.0] - 2024-03-03

### Added

- Custom Python functions can now be used to create light effects that have not
  been possible so far. Thanks to [@thomas-advantitge](https://github.com/thomas-advantitge)
  for the contribution! Talk to us on Discord in the #studio channel if you are
  interested in what the possibilities are.

- Yaw angles can now be exported into the `.skyc` show format.

- Added multiple options for selecting a drone template before creating the
  swarm and the takeoff grid: sphere, cone (suitable for yaw control) or any
  custom selected object;

- Added support for exporting into Litebee format if the server supports it.
  Note that this is a proof-of-concept only; Litebee files generated by
  linearizing arbitrary Blender curves are usually too large to be handled by
  the Litebee drones.

### Fixed

- Minimum navigation altitude during export fixed for shows with staged landing

## [3.0.2] - 2023-11-20

### Fixed

- The add-on is now compatible with Blender 4.0.0.

## [3.0.1] - 2023-10-27

### Fixed

- Fixed the static CSV import option of the "Generate Markers" operator.

## [3.0.0] - 2023-10-22

### Breaking change

- Dropped support for Python <3.10.

- The add-on now declares that it needs at least Blender 3.3 LTS as this was
  the first version of Blender where the bundled Python was from the 3.10
  series.

### Added

- The SVG formation generation got a new angle keyword that determines
  the maximum allowed change of angle at each path node to still treat the path
  around the node to be continuous.

### Fixed

- Smart RTH operation starting frame and duration is fixed.

- All operations of the "Generate Markers" dropdown list are treating
  the cursor position now as the origin of the generated marker positions.

- Fixed an issue with the ordering of drones in multi-stage landings.

## [2.9.0] - 2023-10-13

This release introduces the concept of experimental features in the Blender
plugin. Experimental features are hidden by default and you need to opt in
explicitly in the add-on preferences dialog to use them. We reserve the right
to change, disable or remove experimental features any time in future releases.
Experimental features that prove to be successful will be finalized in later
releases, at which point we will commit ourselves to keeping them for the
foreseeable future.

Some experimental features _may_ be converted to premium features when they are
finalized and you will need to purchase a Pro license for the add-on to keep on
using them.

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

- Return-to-home can now be performed in a way that every single drone lands in
  the same spot where it took off from, at the expense of a more complicated
  trajectory and a slightly increased time needed to land the entire swarm
  safely. This is an experimental feature.

- Besides the one dimensional color ramp, a two dimensional color image can
  also be used as the base color space of light effects to be mapped onto the
  drones with the desired output mapping. In case of color images, both
  dimensions / axes can accept any output mapping type. Along with that feature,
  a new light effect output type called `INDEXED_BY_FORMATION` is also
  available, which orders the drones according to the order of markers in the
  formation of the storyboard entry of a given frame.

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
