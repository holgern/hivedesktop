#!/usr/bin/env bash
COMM_TAG=$(git describe --tags $(git rev-list --tags --max-count=1))
COMM_COUNT=$(git rev-list --count HEAD)
BUILD="steemdesktop-${COMM_TAG}-${COMM_COUNT}_linux.deb"
echo -e ${BUILD}
mv target/steemdesktop.deb ./${BUILD}
curl --upload-file ./${BUILD} https://transfer.sh/
# Required for a newline between the outputs
echo -e "\n"
md5sum  ${BUILD}
echo -e "\n"
sha256sum ${BUILD}
