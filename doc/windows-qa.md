# Dronetara Studio 5.10.0 — Windows acceptance

Windows execution is **not yet verified**. The installer is a platform-neutral
Python add-on; that fact and a Mac pass are not substitutes for Windows tests.
This package tests the exact installer identified in `manifest.json` using an
isolated profile. It does not change your normal Blender installation/preferences,
open your show, contact drones, or require Studio Gateway/a Studio server.

## Run on a Windows test computer

1. Extract the entire QA ZIP into a writable folder. Keep the files together.
2. Use Blender 5.2 for comparison with the Mac acceptance run. Other Blender
   versions need their own acceptance evidence.
3. In PowerShell opened in the extracted folder, run:

   ```powershell
   .\Run-Windows-QA.ps1
   ```

   Choose `blender.exe` when prompted. If your organization restricts PowerShell
   scripts, do not change its policy. Use the manual Python command below or ask
   your IT administrator to run the reviewed script.
4. Allow the three test runs to finish. The 500-drone, ten-minute dense-audit
   stress test uses several GB of RAM and takes several minutes (machine dependent).
   `-SkipStress` omits it for troubleshooting, but is not full acceptance.
5. Retain **each printed evidence directory**. Share its `run.json`, `blender.log`
   and `output` reports. Nonzero exit status, an exception or missing results is
   a failure, not a successful pass.

Manual alternative (replace both Blender installation paths with your actual
paths; no separately installed Python is needed):

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\5.2\python\bin\python.exe' `
  -X utf8 `
  '.\scripts\run_isolated_blender_test.py' `
  --blender 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' `
  --addon-zip '.\dronetara-studio-for-blender-5.10.0.zip' --mode maneuvers
```

Repeat with `--mode checked` and `--mode stress`. `run.json` records the platform,
installer hash and process exit status. The stress test reports memory as unknown
on Windows because Python's Unix `resource` module is unavailable there.

## What this covers

- Landing/RTH feasibility, full generated-curve separation, fixed home identity,
  real home heights, fractional FPS, save/reopen, failure rollback, 100/500-drone
  crossing returns and checked SKYC export.
- Existing checked-export regressions and background-worker success/failure.
- Synthetic 500-drone ten-minute export and dense motion audit.
- Unicode/spaces in paths, isolated directories and real Windows subprocesses.

These are **background Blender tests**, not Windows GUI testing. Before teamwide
Windows rollout, also check installation/enabling, dialogs, ordinary save/export,
background-export Esc cancellation and restart in the intended Windows/Blender
combination. Record the version and results; do not infer GUI success from this
script. No test here grants aircraft compatibility or permission to fly a show.

The 5.10.0 installer can be installed via Blender Preferences → Add-ons → Install
from Disk. Do not install the outer QA ZIP as an add-on; use the installer inside.
