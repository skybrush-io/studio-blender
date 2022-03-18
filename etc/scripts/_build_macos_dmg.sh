#!/bin/sh
#
# Creates a macOS .dmg file hosting the executable version of Skybrush
# Studio for Blender. Requires platypus.
#
# This script is not meant to be called directly; it will be called from
# create_blender_dist.sh

BUILD_DIR="$1"
OUTPUT_DIR="$2"

###############################################################################

set -e

SCRIPT_ROOT=`dirname $0`
REPO_ROOT="${SCRIPT_ROOT}/../.."
NAME="Skybrush Studio for Blender"

###############################################################################

# Parse version number
VERSION=`cat pyproject.toml|grep ^version|head -1|cut -d '"' -f 2`

EXECUTABLE=skybrush-studio-for-blender-${VERSION}-macos

# Create a launcher shell script
mkdir -p "${BUILD_DIR}"
cat >${BUILD_DIR}/launch.sh <<EOF
echo "Starting Skybrush Studio for Blender..."
./${EXECUTABLE}
echo " "
echo "Blender started successfully."
echo "This window will close automatically when you close Blender."
echo " "
echo "You may also close this window with Command-Q."
EOF

# Invoke Platypus to bundle everything into a standalone app
platypus \
    -a "${NAME}" \
    -o "Text Window" \
    -V "${VERSION}" \
    -u "CollMot Robotics Ltd" \
    -I com.collmot.skybrush.studio.blender \
    -R \
    -y \
    -f dist/${EXECUTABLE} \
    -i assets/icons/mac/skybrush.icns \
    "${BUILD_DIR}/launch.sh"

# Remove launcher script and any previous .dmg files
rm "${BUILD_DIR}/launch.sh"
rm -rf "${OUTPUT_DIR}/${NAME} ${VERSION}.dmg"

# Create the final .dmg
hdiutil create \
    -volname "${NAME} ${VERSION}" \
    -srcfolder "${BUILD_DIR}/${NAME}.app" \
    -ov \
    -format UDZO \
    "${OUTPUT_DIR}/${NAME} ${VERSION}.dmg"

