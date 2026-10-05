# Offline implementation status

## 5.10.0: checked offline landing and authored Smart RTH

This release stops work on the other unfinished items at the user's request.
It implements a conservative local planner with source/home feasibility,
analytical separation over every generated synchronized cubic phase, speed and
acceleration bounds, configured ceilings, actual home heights and fixed drone
identity. It includes climb, transfer, final descent, waiting/landed drones and
endpoint holds. There is no motor-off spacing exemption and no online fallback.

Generated curves use validated float32 handles and rounded-up phase times at the
effective Blender FPS. Their entries are locked against ordinary recalculation.
Partial installation rolls back its own objects, actions, constraints and entry.
The planner may reject a route family without asserting that every alternative
is impossible. It is authored animation, not an aircraft emergency RTH function.

323 unit tests passed (one optional decoder skipped), lint/format checks passed,
and 16 packaged Blender maneuver cases plus 15 existing checked-export cases
passed on Mac Blender 5.2. These include 100/500-drone landing/crossing RTH and a
complete checked show export. The [production checklist](production-checklist.md)
records the exact installer and scope. Windows has a portable acceptance bundle
but **has not been executed/verified** here. Other unimplemented work is excluded,
not certified away; flight readiness remains a separate requirement.

## 5.0.10: checked offline drafts, not flight approval

Checked draft is now the default SKYC policy. It requires all drones/full
storyboard in the Blender exporter, a dense audit, positive configured limits,
common zero-based timing, complete audit coverage and sampled export fidelity
within the chosen tolerance (default 0.05 m). Known validation/acceleration
diagnostic failures prevent saving. Checked yaw export is rejected until yaw
validation is implemented. Preview-only export must be selected explicitly and
can retain warnings for design inspection. Both policies record that independent
flight review is still required; external consumers may ignore this metadata.

This hardens the design handoff; it does not solve the continuous-motion,
landing/RTH, tracking-margin or aircraft-acceptance gaps listed below. The
100/500-drone checks use synthetic scenes, separately from the user's show.

Verified on 2026-10-04: 267 unit tests passed (one external LED-reader test
skipped), lint/format checks passed, fifteen packaged-Blender acceptance cases
passed, and the full 500-drone/ten-minute dense-audit run passed in 155.89 seconds.
The checked and preview controls plus a 100-drone background export were also
tested through the Mac GUI using the final installer. Full-source type checking
still reports 85 existing diagnostics. See `production-checklist.md` for the
exact installer checksum, measurements and remaining release requirements.

## Verified in this iteration

- GUI/platform test pass on 2026-10-03: unchanged 5.0.9 installer passed live
  Mac Blender 5.2 Esc cancellation, subsequent background export with Unicode
  filename, and empty-selection error reporting. Original show checksum and
  parent frame were preserved. Expanded unit suite: 224 passed, one native
  decoder test skipped; lint passed. Windows/Linux CI matrix is prepared but
  has not run, and their Blender GUI acceptance is still pending. See
  `production-checklist.md` for repeatable runner instructions and remaining cases.

- Version 5.0.9 adds opt-in **Cancellable background export (offline)**.
  It saves a temporary scene copy, exports through a separate Blender process,
  and atomically commits the result only after success. Cancellation, worker
  failures, empty output and destination changes prevent commit. Temporary
  snapshots are removed when the job closes. The scene-copy step is synchronous.
- The isolated Blender 5.2 worker exported the supplied 100-drone show to a
  2,684,673-byte SKYC while preserving the parent file path and current frame.
  Separation, ascent and descent warnings remained visible; this does not fix
  the show. Unit suite: 211 passed, one external native LED-decoder test skipped;
  Ruff lint passed. At that time GUI Esc interaction was unverified; the later
  Mac GUI pass is recorded above. Other platforms remain unverified.
  Full-project type checking still reports 85 diagnostics.
- Background export requires Offline mode, uses additional process memory and
  rejects modified unpacked images and video light effects. Script-dependent
  scenes are not granted automatic script execution. Use foreground export for
  unsupported scenes after reviewing their content. The option defaults off.

- Added an offline-only MAVLink core conversion probe using the local Server
  checkout's unmodified `SkybrushBinaryShowFile` converter and an independently
  compiled libskybrush trajectory reader. No driver is imported, server started,
  network connection opened, or vehicle command issued. The report records
  reference-module and decoder hashes; per-drone SKYB files are temporary.
- All 100 drones in the supplied show and all 500 in the synthetic dense-audit
  show converted, passed CRC validation, and loaded through libskybrush.
  Nine supplied-show trajectories decode 1 ms shorter than their rounded JSON
  duration; all synthetic trajectories preserve total duration. The converter
  floors each segment duration to milliseconds. These are strict diagnostic
  mismatches, not a measured hardware failure or a flight-safety verdict.
- Still unverified in this probe: decoded positional error, intermediate-time
  alignment, light/trajectory synchronization, yaw/pyro/RTH, origin/geofence,
  onboard storage limits, actual transfer, firmware behavior and flight readiness.
  The server converter has not been changed. That diagnostic-only iteration
  used 5.0.8; the subsequent background-export installer is 5.0.9.

- Version 5.0.8 reuses pairwise working arrays across intervals rather than
  allocating new relative-position and relative-motion arrays every time.
  It still evaluates every pair over every interval, with the same projection,
  clipping, closest-time and tie-order logic. Seeded regressions compare exact
  results with the prior formula for moving, stationary and endpoint-only
  cases at fleet sizes 1, 2, 10, 100 and 500. Complexity remains O(N²T).
- Full 500-drone dense-audit rerun: 161.37 seconds versus 215.18 seconds for
  5.0.7 (25.01% lower elapsed time in these single runs). Peak RSS was
  2,173,157,376 bytes, essentially unchanged. The complete parsed validation
  reports are exactly equal, including all dense-audit diagnostics. This is an
  observed benchmark result, not a guaranteed speedup on other shows/hardware.

- Version 5.0.7 moves landing scheduling into a directly tested math helper.
  Takeoff/landing grouping rejects non-finite or negative minimum separation.
  Landing rejects non-finite coordinates (including Z before ground projection),
  nonpositive/non-finite speed, invalid spindown/altitude, overflowing schedules,
  and targets above starting altitude. Empty valid inputs return empty plans.
  Existing lower-first sequential grouping is retained; it is not a proof of
  collision-free landing or a replacement for checking complete trajectories.
- The 500-drone benchmark supports `--audit` to additionally evaluate 28,801
  half-frame positions per drone over the full ten-minute timeline. See its
  generated `.benchmark.json` for results; a successful synthetic run alone
  does not cover arbitrary formations, flight upload or hardware operation.
- The full 5.0.7 dense benchmark passed: 500 drones, 600.600 seconds,
  14,400,500 evaluated samples, normal trajectory/light export, and ZIP integrity
  checks. No implemented validation checks or diagnostic warnings failed.
  Total runtime was 215.18 seconds with 2,169,290,752 bytes peak process RSS on
  the development Mac; the archive was 12,601,802 bytes. These measurements are
  for one synthetic scene, not worst-case resource limits. Pairwise validation
  performance remains an optimization target.

- Version 5.0.6 adds progress/cancellation checkpoints to exported-path and
  dense-motion pairwise validation and immediately before committing an export.
  Progress delivery is throttled to 0.25 seconds, with forced stage-boundary
  updates. Callback exceptions propagate; successful validation state is only
  published after a successful file commit (or successful in-memory export).
  These use the existing progress-handler cancellation mechanism, not a new
  native Blender Cancel button. Preprocessing and ZIP compression still have
  uninterruptible sections; no fixed cancellation-latency guarantee is made.
- Version 5.0.5 adds an opt-in **Dense motion audit (offline)** checkbox to
  SKYC export. It samples evaluated world positions every half-frame, compares
  them with the rounded exported paths, and embeds `evaluated_motion_audit`
  inside `validation.json`. Dense-sample limit failures propagate to Blender's
  export warning. This does not certify continuous Blender motion and does not
  modify trajectories or repair the show.
- The audit refuses workloads above 20 million drone samples before allocation.
  Its sampling stage uses existing progress/cancellation callbacks and restores
  the prior frame/subframe on completion, cancellation, or evaluation failure.
  Isolated Blender regressions cover these cases and negative-frame sampling.
  Pairwise validation remains synchronous but now has callback checkpoints.
  GUI-only cancellation without Gateway remains open.
- Unit regressions demonstrate detection of an excursion missing from sparse
  export samples and converging landing paths. They are counterexamples, not
  proof that all dense/infeasible landing cases are handled by the planner.

- Export hardening (5.0.4): effective frame rate includes `fps_base` for
  sampling, export origin, cues, phase metadata and audio timing. Phases are
  clipped to export bounds; zero-duration phases are omitted without discarding
  otherwise valid phases. Malformed/overlapping metadata remains fail-closed.
- Offline CSV/SKYC saving uses a same-directory temporary file, flush/fsync,
  and atomic replacement. Tests inject fsync and replacement failures and
  verify that the old file survives and temporary files are cleaned up.
  Abrupt process/power loss can still leave an orphan temporary file; this is
  not a filesystem power-loss durability guarantee.
- The evaluated-motion audit sampled 33,897 half-frame positions per drone
  from the supplied 100-drone file. Maximum sampled export deviation was
  0.011044 m (Drone 79 at 507.125 s). Dense-sample acceleration peaks were
  approximately 1.5072 m/s² horizontal and 1.3705 m/s² vertical. Separation,
  ascent and descent still fail. The original standalone audit does not bound
  motion between samples; version 5.0.5 adds a separate opt-in export UI path.
- A 500-object animated Blender scene with a 600.6-second timeline, fractional
  frame rate, 2,401 samples per drone and compiled lights completed local SKYC
  export in about 23 seconds (~1 GB peak process RSS, 12.6 MB archive). All
  implemented checks passed. This synthetic backend/sampler integration test
  does not exercise the complete UI workflow, flight upload or cancellation.
- Reproduction scripts: `etc/scripts/check_evaluated_motion.py` and
  `etc/scripts/stress_offline_export.py`; run in isolated background Blender
  with the built addon, as described in their module docstrings.

- Validation schema version 3 adds authored storyboard phase intervals and
  separation minima for takeoff, show, landing, and unclassified intervals.
  Missing or overlapping phase metadata never grants spacing exemptions.
  Labels describe authored purposes, not measured flight state.
- Acceleration diagnostics compare adjacent segment velocities over their
  midpoint time separation, including irregular sample intervals. They report
  horizontal/vertical estimates, peak locations, and insufficient samples.
  These are estimates on rounded, potentially simplified export samples, not
  bounds on actual Blender motion or continuous acceleration. Estimated limit
  exceedances produce draft export warnings separately from proven checks.
- Before 5.0.4, the supplied 100-drone show's zero-duration takeoff interval
  caused all phase labels to remain unclassified. The fix now omits that empty
  interval and preserves the authored show phase (without asserting that its
  purpose labels match physical flight phases). Peak export-sample acceleration
  estimates are 1.409908 m/s² horizontal
  and 1.232 m/s² vertical against 4 m/s²; existing separation and ascent/descent
  failures remain. The original Blender file was not changed.
- Validation schema version 2 reports the worst speed interval per drone/check,
  global speed peak locations, initial-layout spacing, and spacing grouped by
  relative height. Times are seconds from the exported show's start.
- Height groups use each drone's first exported Z coordinate plus 0.1 m. At
  least one drone exceeding that height puts a pair in `airborne_or_mixed`.
  Threshold crossings split linear intervals before distance minimization.
  This is a heuristic, not a flight-state or ground-plane measurement, and
  does not waive any existing spacing checks. Avoid interpreting it as actual
  flight state for clips that begin airborne or land on different levels.
- The supplied show reports Drone 1 ascending at 2.352 m/s over 42–42.25 s,
  Drone 99 descending at 2.088 m/s over 539.75–540 s, and Drones 1/93 at
  0.509902 m separation in the airborne-or-mixed category at 702.277778 s.
  The standalone report lists 101 worst drone/check speed violations; these
  are not a count of all violating frames or distinct events.

- Offline SKYC now contains `validation.json`. Separation is minimized
  analytically within every interval of the union of all drone timestamps;
  altitude and directional speed bounds are also checked. This covers the
  exported linear paths, including events between samples.
- Blender reports draft export warnings when a checked limit is exceeded, with
  the destination path. It does not replace the warning with a success message.
- A 500-drone, 60-second synthetic translation with 241 samples per drone was
  validated in 1.55 seconds on the development machine. This is a bounded
  benchmark, not a worst-case performance guarantee.
- The supplied 100-drone show has minimum distance 0.5 m at time zero (3 m
  configured), ascent 2.352 m/s and descent 2.088 m/s (2 m/s configured).
  Ground spacing is included; flight-phase exemptions are not implemented.

- LED compilation uses the public Skybrush bytecode format (20 ms ticks,
  unsigned LEB128 durations, set/fade/wait/end instructions). Absolute timestamp
  quantization prevents accumulated timing drift. Invalid times/colors fail.
- A six-second red-to-blue fade is byte-identical to the licensed backend
  reference. The public libskybrush decoder independently verifies fades,
  steps, holds, and backward seeking.
- The supplied 100-drone Blender file exports with compiled LEDs and opens in
  installed Skybrush Viewer 2.10.0, displaying colored drones.
- Transition duration uses analytical cubic smoothstep peak speed and
  acceleration bounds. The licensed 6 m vertical example returns 4.5 seconds
  and now matches locally. This does not prove agreement for every Blender
  handle arrangement or transition profile.

## Still prevents a production-ready designation

- Acceleration validation and unsampled Blender motion. Exported polylines have
  velocity jumps at corners; finite acceleration cannot be inferred from them.
- Flight-phase exemptions and minimum navigation altitude checks.
- Full paid-planner parity/route completeness. Version 5.10.0 supplies checked
  conservative landing/RTH, not all dense-layout solutions or phase exemptions.
- SVG import, PDF validation reports, and optional audio/camera/pyro export.
- Broader consumer testing, particularly real-flight upload format conversion.
- Stress and failure testing for complete 500-drone shows.

The generated artifact is still labeled draft. Existing show keyframes are not
recalculated by changing the duration estimator, and no flight readiness is
implied by successful Viewer loading.

## Reproduce independent LED verification

Build the public GPL reference implementation from
https://github.com/skybrush-io/libskybrush, then compile the test adapter:

```sh
clang++ -std=c++11 -I /path/to/libskybrush/include \
  etc/scripts/check_light_player.cpp \
  /path/to/libskybrush/build/src/libskybrush.a -o /tmp/check-light-player
DRONETARA_LIGHT_READER=/tmp/check-light-player .venv/bin/pytest -q
```

Without that environment variable the native integration test is skipped; the
ordinary Python tests still run. The production add-on does not depend on this
external C library; it is used only as an independent test reader.
