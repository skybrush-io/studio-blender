# Offline design for 100–500+ drones

The Dronetara Studio add-on is GPL-licensed, but the upstream code delegates several
operations to a separate Skybrush Studio Server. The free community server can
limit drone count, execution time, and features. The professional local
**Skybrush Studio Server** is a licensed product and is not the same component
as the open-source **Skybrush Server** repository used by Skybrush Live to
communicate with fleets.

This fork adds an **Offline design (experimental)** mode. It runs the following
operations inside Blender and has no configured drone-count limit:

- takeoff-grid creation and normal formation editing;
- minimum-total-squared-distance automatic matching between formations;
- transition-duration estimates based on XY/Z velocity and acceleration limits;
- local grouping for layered takeoffs and landings;
- the existing Blender safety overlays and current-frame proximity checks;
- zipped Skybrush CSV export with trajectories and RGB values.

The offline matcher scales comfortably to 500 points, but it does **not** prove
that the resulting trajectories are collision-free. Review the complete
timeline, use the safety overlays, add transition time where required, and use
a production-grade validator before any real flight.

## Capabilities that still require a Studio backend

Offline design mode deliberately does not implement:

- `.skyc` compilation;
- smart return-to-home planning;
- SVG path sampling;
- DSS conversion;
- PDF validation reports or manufacturer-specific production exports;
- server-grade continuous trajectory validation.

For these features, select **Community server** or use a purchased Skybrush
Studio Cloud/local license. A licensed local setup needs the vendor-provided
Skybrush Studio Server running at `http://localhost:8000`. Running the
open-source `skybrush-server` repository alone does not provide the Studio HTTP
API because its Studio extension and calculation package are professional
dependencies.

## Run this source checkout directly (macOS/Linux)

From the repository root:

```sh
uv sync
bash etc/scripts/bootstrap.sh
```

On macOS, launch Blender against the generated development script directory.
`--python-use-system-env` is needed so Blender honors `PYTHONPATH`:

```sh
PYTHONPATH="$PWD/dev/modules" \
  BLENDER_USER_SCRIPTS="$PWD/dev" \
  /Applications/Blender.app/Contents/MacOS/Blender --python-use-system-env
```

On Linux, use the same environment variables and option with the path to your
Blender executable. Alternatively, add the generated `dev/` directory under
Blender Preferences → File Paths → Script Directories, then restart Blender.
Enable **Dronetara Studio** under Blender Preferences → Add-ons and choose
**Offline design (experimental)** in its add-on settings.

This development setup reads the Python source from the checkout. Restart
Blender after source edits.

## Build and install a ZIP

From the repository root:

```sh
uv sync
bash etc/scripts/create_blender_dist.sh
```

Install the resulting `dist/dronetara-studio-for-blender-5.0.3.zip` using
Blender Preferences → Add-ons → Install from Disk. Enable the add-on and choose
**Offline design (experimental)** in the Dronetara Studio add-on settings.

## Create a 500-drone project

1. Open the Dronetara sidebar and run **Create Takeoff Grid**.
2. Set rows to `20`, columns to `25`, and drone count to `500` (or choose any
   grid whose capacity is at least the requested count).
3. Create/import formations with 500 markers and append them to the storyboard.
4. Use **Recalculate Transitions** for local automatic matching.
5. Scrub the entire timeline while monitoring proximity, velocity, and
   acceleration warnings. Increase transition durations or manually adjust
   mappings wherever needed.
6. Use **Export Dronetara CSV (.zip)** for a completely local zipped CSV export.

The CSV output is intended for inspection or a downstream toolchain. It is not
a substitute for a validated, vendor-specific flight file.
