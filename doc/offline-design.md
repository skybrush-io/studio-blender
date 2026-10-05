# Experimental offline design

This optional, in-process backend is intended for local authoring and review,
including when Blender's online access is disabled. It is not a replacement for
Studio Server's full feature set, an emergency flight-controller RTH system, or
approval to fly a show. Existing service authentication and entitlements are
unchanged. There is no fallback to a remote service when offline work fails.

## Enable and use

Build/install the add-on using the normal repository instructions. In Blender's
Skybrush Studio add-on preferences, choose **Offline design (experimental)**.
No gateway, API key, or server process is needed for this mode.
The default remains **Community server**. Switch back to a server mode for
unsupported operations; that service's normal requirements still apply.

Supported local operations:

- Formation matching and transition-duration estimates. Matching minimizes a
  distance cost; it does not guarantee collision-free arbitrary transitions.
- Takeoff layer assignment. This is not a full takeoff flight-safety proof.
- Synchronized cubic landing and layered return-to-home authoring. Generated
  phases check full-path pair separation, altitude, speed and acceleration
  bounds under the planner's common-progress motion model. Infeasible layouts
  are rejected; the conservative planner is not complete or globally optimal.
- Zipped CSV with trajectories and RGB samples, and unoptimized draft SKYC
  archives with trajectories, compiled LED programs and validation metadata.

There is no local drone-count entitlement limit. Runtime and memory still grow
with the show size; large shows should be benchmarked on the intended hardware.

## Export policy and limitations

**Checked draft** is the default offline SKYC policy. It requires all drones and
the full storyboard, checks continuous piecewise-linear exported positions, and
samples Blender-evaluated motion every half-frame. Known failures or incomplete
audit evidence block saving. Fractional frame rates and clipped phase metadata
are handled consistently. A successful export does not grant flight approval.

**Preview only** explicitly allows unfinished designs and partial clips for
inspection. The archive is marked as preview-only, but downstream software may
ignore that metadata. Never treat a preview as permission to upload or fly.
CSV export does not run the checked SKYC gate.

The sampled Blender audit is not a bound on all unsampled motion. Polyline-corner
acceleration, tracking error, downwash, obstacles/terrain, battery endurance,
firmware, radio, upload compatibility, and flight readiness remain outside its
guarantees. Ground/flight-phase exemptions are not applied: closely spaced
ground layouts can fail separation checks even when motors would be stopped.
The export-deviation tolerance is authoring fidelity, not a flight safety margin.

Landing/RTH must begin at the storyboard end and require metre-scale coordinates,
supported animation, valid separated endpoints and sufficient altitude capacity.
Drone identity and home altitude are preserved. Generated maneuvers do not
validate the preceding show or its handoff velocity. Offline RTH always uses the
checked planner, even if the legacy smart-RTH toggle is off.

PDF and vendor-specific exports, SVG sampling, DSS conversion, and SKYC with
pyro, audio or cameras are unsupported offline. Checked offline SKYC also rejects
yaw until its validation is implemented. Unsupported operations raise an error
instead of contacting a server or silently omitting requested content.

Saving uses a temporary sibling file and atomic replacement. Optional background
SKYC export runs a scene snapshot in an isolated Blender process, supports
cancellation, and refuses to replace a destination changed during the job.
Save/pack changed image assets first; video light effects require foreground
export. Snapshot creation itself remains synchronous.

## Reproduce verification

Run the portable tests and style checks:

```sh
uv sync --locked
uv run --locked pytest -q -rs
uv run --locked ruff check .
uv run --locked ruff format --check .
bash etc/scripts/create_blender_dist.sh
```

Test the exact built ZIP in a separate Blender profile:

```sh
uv run python etc/scripts/run_isolated_blender_test.py \
  --blender /path/to/blender \
  --addon-zip dist/skybrush-studio-for-blender-5.0.4.zip --mode maneuvers
```

Repeat with `--mode checked` and `--mode stress`. These create synthetic scenes;
they do not install into the normal profile, open a user show, or contact drones.
The runner prints a retained evidence directory containing the installer hash,
exit status, Blender log and results. The stress case exports 500 drones over
approximately ten minutes with a dense audit. Use the ZIP matching the current
repository version if its version changes.

On Windows, pass quoted paths to `blender.exe` and the ZIP. The Python runner uses
argument arrays, not shell quoting; run it with Python 3.11+ or Blender's bundled
Python. These are headless tests, not Windows GUI or real-flight acceptance.
The optional LED decoder test is skipped unless `SKYBRUSH_LIGHT_READER` points
to a compiled independent adapter; the test summary must retain that skip.

## Review scope

This contribution preserves upstream branding, module identifiers, copyright,
license, project version and server defaults. It ports an experimental local
backend developed in a downstream fork; it does not contain Studio Server source
or server-license modifications. Acceptance of this design and its scope remains
the maintainers' decision. AI tooling assisted with implementation and tests.
