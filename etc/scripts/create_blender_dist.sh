#!/bin/bash
#
# Bash script that creates a single ZIP file containing the full code of
# Skybrush Studio for Blender so it can simply be extracted in the
# Blender addons folder.
#
# It also creates standalone executables for Blender if the Skybrush Studio
# bootloader is accessible on your system.
#
# You need to install Python 3 and uv in order to use this script; both
# of them must be accessible on the system path in order for the script to
# succeed.

OUTPUT_DIR="./dist"
TMP_DIR="./tmp"
MINIFY=1

###############################################################################

set -e

SCRIPT_ROOT=$(dirname $0)
REPO_ROOT="${SCRIPT_ROOT}/../.."

cd "${REPO_ROOT}"

# Extract the name of the project and the version number from pyproject.toml
PROJECT_NAME=$(cat pyproject.toml | grep ^name | head -1 | cut -d '"' -f 2)
VERSION=$(cat pyproject.toml | grep ^version | head -1 | cut -d '"' -f 2)

# Remove all requirements.txt files, we don't use them, only uv
rm -f requirements*.txt

# Generate requirements.txt from uv
uv export --no-hashes --no-emit-project --format requirements-txt >requirements.txt
trap "rm -f requirements.txt" EXIT

# Log requirements for debugging purposes
echo "[>] List of requirements"
cat requirements.txt
echo ""

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

echo "[>] Installing dependencies"
.venv/bin/pip install -q -U pip wheel pyclean
.venv/bin/pip install -r requirements.txt -t "${BUILD_DIR}/vendor/skybrush"
rm -rf "${BUILD_DIR}/vendor/skybrush/bin"
echo ""

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
  for file in $(find ${BUILD_DIR}/vendor/skybrush/sbstudio -name "*.py"); do
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
(
  cd "${TMP_DIR}/${ZIP_STEM}"
  zip -q -r "../${ZIP_STEM}.zip" *
)
mv "${TMP_DIR}/${ZIP_STEM}.zip" "${OUTPUT_DIR}"
rm -rf "${TMP_DIR}/${ZIP_STEM}"
echo "done."

# Clean up after ourselves
rm -rf "${BUILD_DIR}"

echo ""
echo "------------------------------------------------------------------------"
echo ""
echo "Bundle created successfully in ${OUTPUT_DIR}/${ZIP_STEM}.zip"
