:: Windows Bootstrap script for the repository to set up a dev/ folder
:: inside the repo that can pose as a Blender addon path


ECHO off

set SCRIPT_ROOT=%~dp0
set REPO_ROOT=%SCRIPT_ROOT%\..\..
set SKYBRUSH_ROOT=%REPO_ROOT%\..\skybrush
cd %REPO_ROOT%

call poetry install -E standalone

rmdir /Q /S dev\
mkdir dev\vendor\skybrush
mklink /D dev\addons %REPO_ROOT%\src\addons
mklink /D dev\modules %REPO_ROOT%\src\modules

set VENV_PYTHONPATH=%REPO_ROOT%\.venv\Lib\site-packages
::FOR %%A in (natsort pyledctrl skybrush svgpathtools svgwrite webcolors) DO mklink /D dev\vendor\skybrush\%%A %VENV_PYTHONPATH%\%%A
FOR %%A in (natsort pyledctrl svgpathtools svgwrite webcolors) DO mklink /D dev\vendor\skybrush\%%A %VENV_PYTHONPATH%\%%A

:: skybrush is included as a development version for the time being
set VENV_PYTHONPATH=%SKYBRUSH_ROOT%\.venv\Lib\site-packages
mklink /D dev\vendor\skybrush\skybrush %SKYBRUSH_ROOT%\src\skybrush
FOR %%A in (svgpathtools svgwrite webcolors) DO mklink /D dev\vendor\skybrush\%%A %VENV_PYTHONPATH%\%%A
FOR %%A in (jsonref.py proxytypes.py) DO mklink dev\vendor\skybrush\%%A %VENV_PYTHONPATH%\%%A



cd etc/scripts
