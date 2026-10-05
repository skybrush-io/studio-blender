# Licensed backend investigation

Follow-up implementation and verification: [offline readiness](offline-readiness.md).
Observations below describe the baseline before that work.

Observed on 2026-09-16 using eight synthetic requests sent through the running
Studio Gateway. This is an implementation roadmap, not a claim of feature parity.

## Architecture confirmed

- Gateway responds on `127.0.0.1:7999`. Its client API signs request bodies and
  manages progress tasks. A running Gateway does not supply the calculation API.
- No service responded on the standard Studio Server port, `127.0.0.1:8000`.
- Gateway-signed requests to `https://studio.skybrush.io/api/v1` succeeded.
- Backend version: **2.45.0**.
- The limits response returned `num_drones: null` (unbounded in the client's
  parser), a 600-second timeout, and these feature flags:
  `export:plot`, `feat:pyro`, `feat:yaw`, `import:svg`, `op:smart_rth`.
- Manufacturer-specific exporters were not advertised by this license. Baseline
  SKYC and CSV support is implicit in the client API.

The probe uses the existing Gateway signing API normally. It does not save
signatures or hardware identifiers, change Blender preferences, or upload user
show files. An independent offline backend must compute its own results; a
Gateway or saved signatures will not replace cloud computation after a license
ends. External outputs reveal behavior, not the server's internal algorithms.

## Capability map

| Capability | Current offline implementation | Work needed for parity |
| --- | --- | --- |
| Formation matching | Hungarian assignment on squared distances; analytical straight-line clearance | Broader reference cases, unequal sizes, radius and degenerate input tests |
| Transition planning | Trapezoidal speed-profile duration estimate | Match Blender interpolation and the API's `const_jerk` semantics; verify velocity and acceleration over the entire curve |
| Takeoff | Proximity graph grouping | Downwash/layer ordering and dense-grid comparisons |
| Landing | Grouped vertical descent | Pairwise scheduling, spindown semantics, mixed-height comparisons |
| Smart RTH | Unsupported | Path construction, departure scheduling, intermediate waypoint timing and whole-trajectory separation checks |
| SVG import | Unsupported | Parse transforms/paths/colors and sample by arc length with corner handling |
| CSV | Local writer | Broader reference comparisons of sample times and RGB values |
| SKYC | ZIP, JSON trajectories and raw light keyframes | Compile light bytecode; validate with a real consumer; support metadata, media and optional controls |
| Yaw | Raw setpoint serialization | Consumer compatibility and continuous angular-rate validation |
| Pyro | Rejected by local exporter | Payload/event serialization and verification of timing/channel semantics |
| PDF reports | Unsupported | Local trajectory statistics and plots, proximity/velocity/acceleration checks |
| Audio/cameras | Rejected by local exporter | Packaging, references, camera transforms, and consumer tests |
| Combined exports | Unsupported | Share sampling across local renderers and propagate errors |
| Manufacturer formats | Unsupported, not advertised by this license | Obtain format specifications and test consumers individually |

## Concrete reference observations

For source points `(0,0,0), (4,0,0), (8,0,0)` and shuffled targets
`(8,0,6), (0,0,6), (4,0,6)`:

- Matching with radius 0.5 returns `[2,0,1]`, clearance 3.0.
- `const_jerk` transition with XY velocity 4, Z velocity 2 and acceleration 2
  returns three 4.5-second durations. The current offline trapezoidal estimator
  gives 4.0 seconds. One matching example does not prove algorithm equivalence.
- Takeoff at minimum distance 5 returns groups `[0,1,0]`.
- Landing from the shuffled targets at velocity 2 and spindown 5 returns
  start times `[0,0,7.5]`, durations `[3,3,3]`. Our grouping implementation
  does not reproduce this schedule.
- Smart RTH returns start times `[7,0,0]`, durations `[10,9,9]` and timed
  intermediate paths. It performs more than a source-to-target assignment.

The synthetic cloud SKYC archive contains trajectory version 1 and **a base64
string** in `lights.json.data`. Our draft writer stores **a keyframe array** in
that field. ZIP integrity and drone-count checks performed previously did not
prove light-program compatibility with Viewer or Live. This remains unverified;
the draft writer must not be described as fully interchangeable with cloud SKYC.

## Reproduce

With the licensed Gateway running:

```sh
python3 etc/scripts/probe_studio_backend.py --output dist/backend-probe
```

The output directory contains `observations.json` with synthetic inputs,
responses and wall-clock timings, and `skyc.skyc` from the cloud renderer.
Timings include network/signing overhead; they cannot identify server CPU time.
Use a new output directory to retain an earlier capture.

## Implementation order and acceptance

1. SKYC light compilation and actual Viewer loading, including LED colors over
   time. Retain licensed synthetic archives as reference examples.
2. Transition timing and continuous curve checks, with analytical derivative
   tests, ascent/descent limits, and varied distances. Do not infer a timing
   formula from one server response.
3. Local validation and PDF reports using the same computed trajectories.
4. SVG sampling, then media/yaw/pyro serialization and consumer verification.
5. Smart RTH and landing scheduling, with complete-path separation checks at
   100 and 500 drones, including infeasible layouts and explicit failures.
6. Additional format exporters once their specifications and test readers are
   available.

Regression acceptance should compare meaning (paths, colors, bounds, timing and
archive references), not require byte-identical output or identical optimal
assignments. Full paid-feature parity is not implemented by this investigation.
