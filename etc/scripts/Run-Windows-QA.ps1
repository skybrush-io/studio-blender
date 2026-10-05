# Tests only. Does not install into the normal Blender profile or contact drones.
param([string]$Blender, [switch]$SkipStress)
$ErrorActionPreference = 'Stop'
if (-not $Blender) {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.OpenFileDialog
    $picker.Title = 'Select the Blender executable to test (blender.exe)'
    $picker.Filter = 'Blender executable (blender.exe)|blender.exe'
    if ($picker.ShowDialog() -ne 'OK') { throw 'No Blender executable selected.' }
    $Blender = $picker.FileName
}
$Blender = (Resolve-Path -LiteralPath $Blender).Path
if ((Split-Path -Leaf $Blender) -ne 'blender.exe') { throw 'Select blender.exe.' }
$installation = Split-Path -Parent $Blender
$python = Get-ChildItem -LiteralPath $installation -Directory |
    Where-Object { $_.Name -match '^\d+\.\d+$' } |
    ForEach-Object { Join-Path $_.FullName 'python\bin\python.exe' } |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1
if (-not $python) { throw 'Cannot find Blender bundled Python; use the manual instructions.' }
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw | ConvertFrom-Json
$installer = Join-Path $PSScriptRoot $manifest.installer
$actualHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $manifest.sha256) { throw 'Installer checksum mismatch; do not test or distribute this copy.' }
$runner = Join-Path $PSScriptRoot 'scripts\run_isolated_blender_test.py'
$modes = @('maneuvers', 'checked')
if (-not $SkipStress) { $modes += 'stress' }
foreach ($mode in $modes) {
    Write-Host "Running $mode acceptance. Keep the evidence directory printed below."
    & $python -X utf8 $runner --blender $Blender --addon-zip $installer --mode $mode
    if ($LASTEXITCODE -ne 0) { throw "$mode acceptance failed; send its blender.log and run.json for review." }
}
Write-Host 'Requested background tests passed. This is not GUI acceptance or flight approval.'
Write-Host 'Send the printed evidence directories for review before marking Windows verified.'
