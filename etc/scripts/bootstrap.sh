#!/bin/bash
#
# Bootstrap script for the repository to set up a dev/ folder inside the repo
# that can pose as a Blender addon path

###############################################################################

set -e

SCRIPT_ROOT=`dirname $0`
REPO_ROOT="${SCRIPT_ROOT}/../.."

cd "${REPO_ROOT}"

if [ ! -d .venv ]; then
    poetry install -E standalone
fi

rm -rf dev/
mkdir -p dev/vendor/skybrush
cd dev/
ln -s ../src/addons
ln -s ../src/modules

cd vendor/skybrush/
VENV_PYTHONPATH=`ls -d ../../../.venv/lib/python*/site-packages | sed -e 's#/$##'`

for dependency in natsort pyledctrl skybrush; do
    if [ -d "${VENV_PYTHONPATH}/${dependency}" ]; then
        ln -s "${VENV_PYTHONPATH}/${dependency}"
    fi
done

