:: Windows bootstrap script for the repository to set up a dev/ folder 
:: inside the repo that can pose as a Blender addon path.
::
:: You should run the script without any arguments, unless you are an
:: in-house skybrush developer. In the latter case run it with the
:: first argument set to "standalone".
::
:: After running this script, open Blender and add the /dev folder to
:: Preferences -> "File Paths" -> "Script Directories" to reach the
:: Skybrush Studio for Blender addon from your local source code.
::
:: You will need to close and reopen Blender to see Skybrush Studio
:: in the list of add-ons. You will also need to close and open Blender
:: after any code modifications on the source code to take effect.
::
:: Please consider supporting the open-source initiative of Skybrush by the following ways:
::
:: - Join our Discord community at https://skybrush.io/r/discord to share your
::   ideas, thoughts and feedback
::
:: - Share your code modifications with the community as a pull-request to the
::   official repo at https://github.com/skybrush-io/studio-blender
::
:: - Donate to support Skybrush development at https://skybrush.io/donate
::
::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

ECHO off

set ORIGINAL_DIR=%cd%
set SCRIPT_ROOT=%~dp0
set REPO_ROOT=%SCRIPT_ROOT%\..\..
cd %REPO_ROOT%

if "%1"=="standalone" (
    set SKYBRUSH_ROOT=%REPO_ROOT%\..\skybrush
    call poetry install -E standalone
) else (
    call poetry install
)



rmdir /Q /S dev\
mkdir dev\vendor\skybrush
mklink /D dev\addons %REPO_ROOT%\src\addons
mklink /D dev\modules %REPO_ROOT%\src\modules

set VENV_PYTHONPATH=%REPO_ROOT%\.venv\Lib\site-packages
FOR %%A in (natsort) DO mklink /D dev\vendor\skybrush\%%A %VENV_PYTHONPATH%\%%A

:: skybrush is included as a development version for the time being
if defined SKYBRUSH_ROOT (
    set VENV_PYTHONPATH=%SKYBRUSH_ROOT%\.venv\Lib\site-packages
    mklink /D dev\vendor\skybrush\skybrush %SKYBRUSH_ROOT%\src\skybrush
    FOR %%A in (pyledctrl svgpathtools svgwrite webcolors) DO mklink /D dev\vendor\skybrush\%%A %VENV_PYTHONPATH%\%%A
    FOR %%A in (jsonref.py proxytypes.py) DO mklink dev\vendor\skybrush\%%A %VENV_PYTHONPATH%\%%A
)

cd /d "%ORIGINAL_DIR%"
