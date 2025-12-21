#!/bin/bash
#
# Bootstrap script for the repository to set up a dev/ folder inside the repo
# that can pose as a Blender addon path.
#
# You should run the script without any arguments, unless you are an
# in-house Skybrush developer. In the latter case run it with the
# first argument set to "standalone".
#
# After running this script, open Blender and add the /dev folder to
# Preferences -> "File Paths" -> "Script Directories" to reach the
# Skybrush Studio for Blender addon from your local source code.
#
# You will need to close and reopen Blender to see Skybrush Studio
# in the list of add-ons. You will also need to close and open Blender
# after any code modifications on the source code to take effect.
#
# Please consider supporting the open-source initiative of Skybrush by the following ways:
#
# - Join our Discord community at https://skybrush.io/r/discord to share your
#   ideas, thoughts and feedback
#
# - Share your code modifications with the community as a pull-request to the
#   official repo at https://github.com/skybrush-io/studio-blender
#
# - Donate to support Skybrush development at https://skybrush.io/donate
#
###############################################################################

set -e

SCRIPT_ROOT=$(dirname $0)
REPO_ROOT="${SCRIPT_ROOT}/../.."

if [ "$1" == "standalone" ]; then
  uv sync -E standalone
  DEPENDENCIES="natsort pyledctrl skybrush svgpathtools svgwrite webcolors"
else
  uv sync
  DEPENDENCIES=natsort
fi

cd "${REPO_ROOT}"

rm -rf dev/
mkdir -p dev/vendor/skybrush
cd dev/
ln -s ../src/addons
ln -s ../src/modules

cd vendor/skybrush/
VENV_PYTHONPATH=$(ls -d ../../../.venv/lib/python*/site-packages | sed -e 's#/$##')

for dependency in $DEPENDENCIES; do
  if [ -d "${VENV_PYTHONPATH}/${dependency}" ]; then
    ln -s "${VENV_PYTHONPATH}/${dependency}"
  fi
done
