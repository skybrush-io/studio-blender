:: Windows Bootstrap script for the repository to set up a dev/ folder
:: inside the repo that can pose as a Blender addon path


ECHO off

set SCRIPT_ROOT=%~dp0
set REPO_ROOT="%SCRIPT_ROOT%\..\.."

cd %REPO_ROOT%

call poetry install -E standalone

del /Q "dev\"
mkdir "dev\vendor\skybrush"
mklink /D "dev\addons" "%REPO_ROOT%\src\addons"
mklink /D "dev\modules" "%REPO_ROOT%\src\modules"

set VENV_PYTHONPATH="%REPO_ROOT%\.venv\Lib\site-packages"

FOR %%A in (natsort pyledctrl skybrush) DO mklink /D "dev\vendor\skybrush\%%A" "%VENV_PYTHONPATH%\%%A"