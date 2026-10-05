# Offline production checklist

This is a completion checklist, not a declaration of flight readiness.

## 5.10.0 scope: checked offline landing/RTH and designer handoff

The user stopped the other unfinished engineering work for this release. It has
not been silently completed or removed from the codebase. Version 5.10.0 adds
checked offline landing/Smart RTH and retains the fail-closed **Checked draft**
export policy introduced in 5.0.10, not a flight-approved mode. Known violations
cannot be saved in that mode. Dense
audit coverage, sampled fidelity (default 0.05 m), positive limits and common
timing are enforced. The Blender exporter requires all drones/full storyboard;
unvalidated yaw is rejected. **Preview only** is an explicit exception for
inspection, including partial clips. The new dialog resets to Checked draft.

Both modes embed `flight_approved: false` and the remaining limitations in the
archive. External upload tools may ignore these fields: this is a review warning,
not a hardware lockout. Adopt a controlled designer pilot first. A qualified
flight team must separately approve aircraft-specific limits, the complete show,
deployment conversion/timing/lights, fleet configuration, contingencies and the
event operating plan before any commercial deployment.

Windows compatibility is requested for 5.10.0. The platform-neutral installer,
portable tests and Windows test bundle are provided, but only Mac Blender has
actually executed them here. Do not mark Windows verified without its evidence.
Unused paid-feature parity and the other unfinished work below are not being
pursued in this scoped release. Their absence still limits broader claims of
production/flight readiness, regardless of whether a Studio server is used.

| Workstream | State | Required evidence / dependency |
| --- | --- | --- |
| Offline core planning / SKYC / CSV | Implemented, draft | Existing automated and Blender integration tests |
| Checked offline SKYC handoff | Implemented in 5.0.10 | Known violations block saving; sampled checks are not flight certification |
| 500-drone dense audit | Tested synthetic case | Broader adversarial formations and platform coverage remain |
| Native cancellation without Gateway | Mac Blender 5.2 GUI cancellation, restart/export and error handling tested | Windows/Linux GUI acceptance and additional Blender versions still pending |
| Cross-platform automated tests | Six-job CI matrix prepared; local Mac suite passes | Workflow has not been pushed or executed on Windows/Linux |
| Continuous Blender motion / acceleration bounds | Partial: sampled diagnostics only | Sound treatment of constraints, drivers, interpolation and tracking margins |
| Phase rules / minimum navigation altitude | Partial: labels only | Explicit policy and reliable ground/flight-state definition; no blanket exemptions |
| Collision-safe landing / Smart RTH | Implemented and tested in 5.10.0, within the generated-path model | Feasibility, complete synchronized cubic phases, fixed identity, ceilings, rollback, adversarial and 100/500-drone cases; not obstacle/aircraft safety |
| Offline SVG, PDF, DSS, audio/camera/pyro parity | Incomplete | Implementations and independent format/consumer tests |
| Full-project type diagnostics | Incomplete | Triage against real Blender API rather than suppressing errors |
| Binary upload conversion | Core conversion tested | Quantization, synchronization, optional blocks and target firmware acceptance remain |
| Fleet identification / backups | Waiting for user hardware evidence | PCB/connector photos, SD listing, firmware/parameters |
| Hardware upload / flight acceptance | Blocked on identification | Explicit controlled test plan and qualified operator; no automatic drone commands |

The user's existing show is outside the 5.10.0 acceptance scope and was not
opened or modified. Reinstalling the add-on does not repair old show animation.

## Scoped 5.10.0 acceptance — 2026-10-05

Installer: `dist/dronetara-studio-for-blender-5.10.0.zip`, 410,068 bytes,
SHA-256 `ae39feb49959cdfeafaaa344d084864068d4568cf2acaf7f5edbfbfdaccf22bb`.
The release evidence is retained under `dist/offline-qa-5.10.0/`.

- **323 tests passed, 1 optional external LED-decoder test skipped**. Lint,
  repository formatting, diff whitespace and targeted type checks for the new
  planner/Blender installer passed. Full-source type checking still reports the
  existing **85 diagnostics**; that excluded work is not claimed complete.
- **16 packaged Blender maneuver acceptance cases passed** on macOS 26.6.2
  arm64 / Blender 5.2.0 LTS. They include actual 100/500-drone landings and crossing
  returns, stationary drones, fractional FPS, real home Z, fixed identity,
  aerial-grid stopping, save/reopen, locked-route recalculation, rejection without
  animation changes, unsupported drivers, partial-install rollback and a complete
  100-drone checked SKYC export. No parent-process network connections occurred.
- Pure-math adversarial regressions additionally cover crossing paths between
  endpoints, unsafe climb/descent columns, initial/final spacing, tight ceilings,
  malformed/non-finite inputs, timing overflow, float32 handles, 20 seeded route
  permutations checked by independent polynomial roots and an over-capacity
  500-way crossing. These are bounded tests, not exhaustive route completeness.
- **15 existing packaged checked-export cases passed** against this exact ZIP,
  including background-worker success/rejection and preserving existing output
  on failure. These are headless tests; prior Mac GUI evidence below remains
  historical rather than a new 5.10.0 GUI acceptance run.
- The final ZIP also passed a **500-drone, 600.600-second checked export** with
  14,400,500 dense samples in **145.46 seconds**. Peak process RSS was
  2,513,682,432 bytes; maximum sampled export deviation was 0.0008212 m; the
  resulting archive was 12,602,363 bytes. This synthetic run is not a worst-case
  performance or aircraft test. See `500-drone-benchmark.json` in the evidence.
- [Windows QA procedure](windows-qa.md): the bundle runs the same packaged
  maneuver, checked-export and 500-drone stress scripts using Blender's bundled
  Python. Windows lacks the Unix `resource` module, so memory measurement is
  optional there. The six-job pure-Python CI matrix is still prepared, not run.

The planner uses a conservative layered route family. It can reject layouts
that another planner could solve, cannot exempt crowded ground slots, and does
not optimize battery use. Its analytic bounds cover only the generated,
unmodified synchronized curves. Prior-show motion/handoff velocity, obstacles,
terrain, downwash, tracking uncertainty, endurance and flight-controller emergency
RTH remain outside that check. Complete-show checked export is still required.

Use **5.10.0** as the version label for this scoped offline design release, not
as a declaration that the excluded work or Windows/aircraft acceptance is done.

## Generic offline acceptance — 2026-10-04

Tested installer: `dist/dronetara-studio-for-blender-5.0.10.zip`, 401,505 bytes,
SHA-256 `f4b62a452dd44625f1aa331fd80a2ba93408b650780e6792093503425255dd98`.
All tests below used synthetic scenes; the user's original show was not opened.

- Unit/subprocess/modal regressions: **267 passed, 1 skipped**. The skipped test
  needs the external compiled libskybrush LED-reader executable. Ruff lint,
  whole-repository formatting and diff whitespace checks passed. Targeted type
  checks for the new gate/export path passed; full-source type checking still has
  the previous **85 diagnostics**, so this is not a clean full-project typecheck.
- Fifteen packaged-Blender acceptance cases passed. They include a 100-drone
  checked export at fractional FPS with Unicode filename; actual property reset
  from preview to checked; selected/partial-range and yaw rejection; successful
  and collision-rejected background workers; explicit preview marking; crossing
  trajectories between samples; vertical overspeed; sampled export deviation;
  missing audit/range and invalid tolerance. Rejected exports preserved existing
  destination bytes and did not publish a stale success report. Python socket
  connection attempts were blocked in the parent test process; none occurred.
- Full 500-drone, 600.600-second synthetic export with 14,400,500 dense samples
  passed the checked gate and archive-integrity tests: 155.89 seconds, peak RSS
  2,324,955,136 bytes on macOS 26.6.2 arm64 / Blender 5.2.0 LTS. Maximum sampled
  export deviation was 0.0008212 m; archive size 12,602,363 bytes. This is one
  measured scene, not a worst-case or real-flight guarantee.
- Live Mac GUI: Checked defaults/full-storyboard lock and Preview warning were
  inspected; changing Preview with selected-only enabled back to Checked reset
  selection to all drones. A checked background export completed with 100 drones,
  intact ZIP, passing gate and `flight_approved: false`. Frame 120 was preserved,
  the active job cleared, and the completion message retained the independent
  flight-review requirement. The test scene was saved and closed cleanly; its
  source fixture's checksum was unchanged. Some secondary field labels still
  clip at the narrow default sidebar width; the main policy/warning is readable.
- No normal-profile installation, vehicle communication/upload, firmware changes
  or flight tests were performed. Prior 5.0.9 live Esc tests are historical
  evidence, not a new full 5.0.10 cancellation/500-drone GUI acceptance run.

Evidence: `dist/offline-qa-5.0.10/` contains run metadata, acceptance results,
benchmark, logs and dialog screenshots; `dist/offline-5.0.10-tests.xml` contains
the unit results. The retained temporary QA roots are recorded in the run files.

Repeat the generic tests without a user scene:

```text
python etc/scripts/run_isolated_blender_test.py --blender "/path/to/blender" --addon-zip "dist/dronetara-studio-for-blender-5.0.10.zip" --mode checked
python etc/scripts/run_isolated_blender_test.py --blender "/path/to/blender" --addon-zip "dist/dronetara-studio-for-blender-5.0.10.zip" --mode stress
```

## GUI and platform test pass — 2026-10-03

Tested the unchanged 5.0.9 installer (SHA-256
`6106567ee0442cba92b93297891f9cc32ff26b36a1d556cb345dc38327ca7e08`)
in an isolated Blender 5.2.0 LTS GUI session on macOS. Temporary preferences,
add-on installation and scene copies did not change the normal installation.
The original 100-drone scene's SHA-256 remained unchanged.

- Live Esc during a background dense-audit export: cancellation message shown,
  no output created, worker PID exited and its export directory removed.
- A subsequent background export without restarting Blender: successful SKYC
  with a space/Unicode filename, 100 drones, ZIP integrity verified. The file
  was 2,684,677 bytes; parent frame remained 13,535 and the QA filepath remained
  unchanged. Existing separation/ascent/descent warnings were reported.
- Background export with no selected drones: visible error, no new output,
  active-job state cleared. This was an intentional negative test.
- File-dialog Esc cancellation: returned to the scene without overwriting the
  completed export. The separate portable worker runner also exited successfully.
- Portable unit/subprocess and mocked modal-lifecycle suite: 224 passed,
  one native LED-decoder test skipped because its external executable is absent.
  Mocked lifecycle tests are not a substitute for live GUI tests. Ruff passed.
- Minor usability observations: long checkbox labels are clipped in the default
  narrow export sidebar; a packaged operator tooltip reads "undocumented
  operator". No production code was changed in this testing pass.

Evidence is retained locally in `dist/gui-qa-2026-10-03/` (summary, screenshots,
GUI/worker logs, run metadata and the generated SKYC), with JUnit results in
`dist/gui-platform-test-results.xml`. The disposable QA scene was saved and its
Blender session closed cleanly; both test runners confirmed the source unchanged.

### Repeating the tests

Use `etc/scripts/run_isolated_blender_test.py` with Python 3.11+ on each platform:

```text
python etc/scripts/run_isolated_blender_test.py --blender "/path/to/blender" --addon-zip "dist/dronetara-studio-for-blender-5.0.9.zip" --scene "/path/to/100-drone-show.blend" --mode gui
```

On Windows, pass the full path to `blender.exe`; on macOS, pass the executable
inside `Blender.app/Contents/MacOS/Blender`. Close unrelated Blender windows
yourself after saving work. The runner prints a unique retained evidence folder
containing `run.json`, `blender.log`, a QA scene copy and `output/`. Its timer
only records state; the tester must perform the actual GUI interactions.

Repeat cancellation, successful export, empty-selection error and file-dialog
cancellation. Also test existing-file overwrite/cancellation, locked destination
and denied-write access using disposable files; never production exports.
Use `--mode worker` for an automated 100-drone snapshot/export integrity check.
Neither mode uploads to a drone or saves user preferences.

The new `.github/workflows/offline-tests.yml` covers macOS, Windows and Linux
with Python 3.11/3.13 and retains JUnit reports, including skips. It tests the
portable Python code only, not Blender installation, GPU/UI or flight behavior.
Windows/Linux runs, platform-specific locks/permissions, other Blender versions,
GUI installation/removal, CSV GUI export and full GUI 500-drone tests remain open.
