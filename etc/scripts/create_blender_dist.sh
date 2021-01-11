#!/bin/bash
#
# Bash script that creates a single ZIP file containing the full code of the
# Blender plugin so it can simply be extracted in the Blender plugins folder.

OUTPUT_DIR="./dist"
TMP_DIR="./tmp"
MINIFY=1

###############################################################################

set -e

SCRIPT_ROOT=`dirname $0`
REPO_ROOT="${SCRIPT_ROOT}/../.."

cd "${REPO_ROOT}"

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
  python3 -m venv .venv
fi

# Create build folder
BUILD_DIR="${OUTPUT_DIR}/build"
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/vendor/skybrush"

# Install dependencies
.venv/bin/pip install -U pip wheel pyclean pyminifier
.venv/bin/pip install -r requirements.txt -t "${BUILD_DIR}/vendor/skybrush"
rm -rf "${BUILD_DIR}/vendor/skybrush/bin"

# Copy our code as well
cp -r src/modules/sbstudio ${BUILD_DIR}/vendor/skybrush
cp src/addons/ui_skybrush_studio.py ${BUILD_DIR}

# Clean any __pycache__ and *.dist-info files
.venv/bin/pyclean ${BUILD_DIR}
rm -rf ${BUILD_DIR}/vendor/skybrush/*.dist-info

# Minify the source code with pyminifier
if [ "x${MINIFY}" = x1 ]; then
  for file in `find ${BUILD_DIR}/vendor/skybrush/sbstudio -name "*.py"`; do
    if [ -s "$file" ]; then
      .venv/bin/pyminifier -o ${BUILD_DIR}/tmp.py $file && mv ${BUILD_DIR}/tmp.py $file
    fi
  done
fi

# Create a single ZIP
ZIP_STEM="${PROJECT_NAME}-${VERSION}"
rm -rf "${TMP_DIR}/${ZIP_STEM}"
mkdir -p "${TMP_DIR}/${ZIP_STEM}"
cp -r "${BUILD_DIR}"/* "${TMP_DIR}/${ZIP_STEM}"
( cd "${TMP_DIR}/${ZIP_STEM}"; zip -r "../${ZIP_STEM}.zip" * )
mv "${TMP_DIR}/${ZIP_STEM}.zip" "${OUTPUT_DIR}"
rm -rf "${TMP_DIR}/${ZIP_STEM}"

# Create a single-file Python entry point
cat ${BUILD_DIR}/ui_skybrush_studio.py >${BUILD_DIR}/entrypoint.py
echo -e "\n\nregister()\n" >>${BUILD_DIR}/entrypoint.py
PYTHONPATH=vendor .venv/bin/python -m stickytape.main ${BUILD_DIR}/entrypoint.py --add-python-path ${BUILD_DIR}/vendor/skybrush --add-python-module sbstudio.plugin.utils.platform --add-python-module natsort >${OUTPUT_DIR}/${ZIP_STEM}.py.orig
.venv/bin/pyminifier --gzip ${OUTPUT_DIR}/${ZIP_STEM}.py.orig >${OUTPUT_DIR}/${ZIP_STEM}.py
rm ${OUTPUT_DIR}/${ZIP_STEM}.py.orig

# Clean up after ourselves
rm -rf "${BUILD_DIR}"

echo ""
echo "------------------------------------------------------------------------"
echo ""
echo "Bundle created successfully in ${OUTPUT_DIR}/${ZIP_STEM}.zip"
echo "Single-file script created successfully in ${OUTPUT_DIR}/${ZIP_STEM}.py"

