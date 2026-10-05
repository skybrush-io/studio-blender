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
- local grouping for layered takeoffs;
- checked synchronized landing and identity-preserving layered Smart RTH;
- the existing Blender safety overlays and current-frame proximity checks;
- zipped Skybrush CSV export with trajectories and RGB values.
- unoptimized draft `.skyc` export with trajectories, lights, cues, validation
  settings, show location, segments, and optional yaw control.
- an embedded `validation.json` report with continuous separation, altitude and
  directional speed checks on exported linear trajectories. Failed checks are
  shown as export warnings; ground layout is included in separation checks.

The offline matcher scales comfortably to 500 points, but it does **not** prove
that the resulting trajectories are collision-free. Review the complete
timeline, use the safety overlays, add transition time where required, and use
a production-grade validator before any real flight.

Draft `.skyc` files are intended for preview and interoperability testing. They
are not a substitute for server-grade validation or production flight checks.

## Capabilities that still require a Studio backend

Offline design mode deliberately does not implement:

- optimized/production `.skyc` compilation, including embedded audio, cameras,
  or pyro control;
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

Install the resulting `dist/dronetara-studio-for-blender-5.10.0.zip` using
Blender Preferences → Add-ons → Install from Disk. Enable the add-on and choose
**Offline design (experimental)** in the Dronetara Studio add-on settings.

## Dense motion audit

The default **Checked draft** SKYC export requires a dense audit of evaluated
Blender positions every half-frame in addition to the normal export. This can
take substantially longer and use more memory. Preview-only exports can omit
it; ranges exceeding 20 million drone samples are rejected before allocation.

Inside the exported archive, `validation.json` contains an
`evaluated_motion_audit` section with sampled limit checks and maximum sampled
deviation from the exported path. It does not change the show, increase output
trajectory FPS, or prove safety between samples. Audit sampling restores the
previous frame/subframe even on cancellation or evaluation error. Version 5.0.6
also checks the existing progress-handler cancellation callback during pairwise
analysis and before saving. A native Blender Cancel button without Gateway is
available through optional process-isolated background export; preprocessing and
ZIP compression still have synchronous sections.

## Checked landing and authored Smart RTH

Version 5.10.0 checks the full synchronized cubic phases it generates, including
descent to each drone's actual home height. The offline operator cannot select
the old unchecked RTH path. It preserves drone identity, enforces configured
spacing/speed/acceleration/altitude bounds and rejects unsafe start/home layouts
or a layered route that does not fit. Grounded drones receive no spacing waiver.
The planner is conservative rather than complete or time-optimal.

Start at the final storyboard frame, using metre-scale scene coordinates and
local single-user drone actions without NLA blending or drivers. The generated
formation is locked against ordinary recalculation. Installation failure rolls
back the new data. Re-export/check the complete show after changes; the preceding
motion, obstacles, terrain, tracking error, endurance and emergency controller
behavior are not approved by this generated-path check.

Windows execution still needs the [Windows acceptance procedure](windows-qa.md).

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
