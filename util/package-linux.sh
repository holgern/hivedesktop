#!/usr/bin/env bash
#COMM_TAG=$(git describe --tags $(git rev-list --tags --max-count=1))
#COMM_COUNT=$(git rev-list --count HEAD)
#BUILD="steemdesktop-${COMM_TAG}-${COMM_COUNT}_linux.deb"
BUILD="steemdesktop_linux.deb"
echo -e ${BUILD}
mv target/steemdesktop.deb ./${BUILD}
wget -t 1 -qO - --method=PUT --body-file="steemdesktop_linux.deb" --header="Content-Type: $(file -b --mime-type steemdesktop_linux.deb)" https://transfer.sh/steemdesktop_linux.deb;
# curl -T steemdesktop_linux.deb https://transfer.sh/steemdesktop_linux.
# Required for a newline between the outputs
echo -e "\n"
md5sum  ${BUILD}
echo -e "\n"
sha256sum ${BUILD}
