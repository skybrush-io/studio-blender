#!/bin/bash
#
# Bash script that creates a single ZIP file containing the full code of
# Skybrush Studio for Blender so it can simply be extracted in the
# Blender addons folder.
#
# It also creates standalone executables for Blender if the Skybrush Studio
# bootloader is accessible on your system.
#
# You need to install Python 3 and poetry in order to use this script; both
# of them must be accessible on the system path in order for the script to
# succeed.

OUTPUT_DIR="./dist"
TMP_DIR="./tmp"
MINIFY=1

###############################################################################

set -e

SCRIPT_ROOT=`dirname $0`
REPO_ROOT="${SCRIPT_ROOT}/../.."

cd "${REPO_ROOT}"

# Check whether the bootloader is present on the system
BOOTLOADER_DIR=${BOOTLOADER_DIR:-"${REPO_ROOT}/../sbstudio-bootloader/dist"}
if [ ! -d "${BOOTLOADER_DIR}" -o ! -f "${BOOTLOADER_DIR}/sbstudio-bootloader-linux" ]; then
    BOOTLOADER_DIR=
fi

# Extract the name of the project and the version number from pyproject.toml
PROJECT_NAME=`cat pyproject.toml|grep ^name|head -1|cut -d '"' -f 2`
VERSION=`cat pyproject.toml|grep ^version|head -1|cut -d '"' -f 2`

# Remove all requirements.txt files, we don't use them, only poetry
rm -f requirements*.txt

# Generate requirements.txt from poetry
poetry export -f requirements.txt -o requirements.txt --without-hashes
trap "rm -f requirements.txt" EXIT

# Create virtual environment if it doesn't exist yet
if [ ! -d .venv ]; then
  echo -n "--> Creating virtual environment... "
  python3 -m venv .venv
  echo "done."
fi

# Create build folder
BUILD_DIR="${OUTPUT_DIR}/build"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/vendor/skybrush"

echo -n "--> Installing dependencies... "
.venv/bin/pip install -q -U pip wheel pyclean
.venv/bin/pip install -q -r requirements.txt -t "${BUILD_DIR}/vendor/skybrush"
rm -rf "${BUILD_DIR}/vendor/skybrush/bin"
echo "done."

# Copy our code as well
echo -n "--> Copying addon code... "
cp -r src/modules/sbstudio ${BUILD_DIR}/vendor/skybrush
cp src/addons/ui_skybrush_studio.py ${BUILD_DIR}
echo "done."

# Clean any __pycache__ and *.dist-info files
echo -n "--> Cleaning up and minifying code... "
.venv/bin/pyclean -q ${BUILD_DIR}
rm -rf ${BUILD_DIR}/vendor/skybrush/*.dist-info

# Strip the comments from the source code
if [ "x${MINIFY}" = x1 ]; then
  for file in `find ${BUILD_DIR}/vendor/skybrush/sbstudio -name "*.py"`; do
    if [ -s "$file" ]; then
      .venv/bin/python etc/scripts/_strip_comments.py -o ${BUILD_DIR}/tmp.py $file && mv ${BUILD_DIR}/tmp.py $file
    fi
  done
fi
echo "done."

# Create a single ZIP
echo -n "--> Creating ZIP addon... "
ZIP_STEM="${PROJECT_NAME}-${VERSION}"
rm -rf "${TMP_DIR}/${ZIP_STEM}"
mkdir -p "${TMP_DIR}/${ZIP_STEM}"
cp -r "${BUILD_DIR}"/* "${TMP_DIR}/${ZIP_STEM}"
( cd "${TMP_DIR}/${ZIP_STEM}"; zip -q -r "../${ZIP_STEM}.zip" * )
mv "${TMP_DIR}/${ZIP_STEM}.zip" "${OUTPUT_DIR}"
rm -rf "${TMP_DIR}/${ZIP_STEM}"
echo "done."

if [ "x${BOOTLOADER_DIR}" != x ]; then
    echo -n "--> Creating executables... "

    # pyminifier only needed here, but we need our patched version that works
    # with Python 3
    .venv/bin/pip install -q -U pyminifier>=3.0.0

    # Create a single-file Python entry point
    cat ${BUILD_DIR}/ui_skybrush_studio.py | sed -n '/BLENDER ADD-ON INFO ENDS HERE/,$p' >${BUILD_DIR}/entrypoint.py
    cat >>${BUILD_DIR}/entrypoint.py <<EOF

register()

from sbstudio.plugin.api import set_fallback_api_key, get_api
set_fallback_api_key("NNAs8w.hApopcx8s68YZAuRAGofbboqzFwx7KikdT0Q")
EOF
    PYTHONPATH=vendor .venv/bin/python -m stickytape.main ${BUILD_DIR}/entrypoint.py \
        --add-python-path ${BUILD_DIR}/vendor/skybrush \
        --add-python-module sbstudio.plugin.utils.platform \
        --add-python-module natsort \
        >${OUTPUT_DIR}/${ZIP_STEM}.py.orig
    if [ "x${MINIFY}" = x1 ]; then
      .venv/bin/pyminifier --gzip ${OUTPUT_DIR}/${ZIP_STEM}.py.orig >${OUTPUT_DIR}/${ZIP_STEM}.py
      rm ${OUTPUT_DIR}/${ZIP_STEM}.py.orig
    else
      mv ${OUTPUT_DIR}/${ZIP_STEM}.py.orig ${OUTPUT_DIR}/${ZIP_STEM}.py
    fi

    # Attach the single-file entry point to the bootloader(s)
    .venv/bin/python etc/scripts/_append_to_bootloader.py \
        --bootloader-dir "${BOOTLOADER_DIR}" \
        --output-dir ${OUTPUT_DIR} \
        ${OUTPUT_DIR}/${ZIP_STEM}.py

    # Remove the single-file entry point, not needed any more
    rm ${OUTPUT_DIR}/${ZIP_STEM}.py

    echo "done."

    # Create macOS launcher app in a disk image
    echo -n "--> Creating macOS disk image... "
    etc/scripts/_build_macos_dmg.sh "${BUILD_DIR}" "${OUTPUT_DIR}" >/dev/null 2>/dev/null
    echo "done."
else
    echo "[-] Skipping executables - no bootloader code present."
fi

# Clean up after ourselves
rm -rf "${BUILD_DIR}"

echo ""
echo "------------------------------------------------------------------------"
echo ""
echo "Bundle created successfully in ${OUTPUT_DIR}/${ZIP_STEM}.zip"
if [ "x${BOOTLOADER_DIR}" != x ]; then
    echo "Single-file Windows executable created successfully in ${OUTPUT_DIR}/${ZIP_STEM}-win64.exe"
    echo "macOS launcher created successfully in ${OUTPUT_DIR}"
fi
