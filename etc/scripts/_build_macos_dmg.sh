#!/bin/sh

BUILD_DIR="$1"
OUTPUT_DIR="$2"

###############################################################################

set -e

SCRIPT_ROOT=`dirname $0`
REPO_ROOT="${SCRIPT_ROOT}/../.."
NAME="Skybrush Studio for Blender"

###############################################################################

VERSION=`cat pyproject.toml|grep ^version|head -1|cut -d '"' -f 2`

EXECUTABLE=skybrush-studio-for-blender-${VERSION}-macos

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

rm "${BUILD_DIR}/launch.sh"
rm -rf "${OUTPUT_DIR}/${NAME} ${VERSION}.dmg"
hdiutil create \
    -volname "${NAME} ${VERSION}" \
    -srcfolder "${BUILD_DIR}/${NAME}.app" \
    -ov \
    -format UDZO \
    "${OUTPUT_DIR}/${NAME} ${VERSION}.dmg"

