#!/bin/bash

set -exo pipefail
# This script outputs a version string (along the lines of git-describe)
# to identify the driver version currently in use, starting from tags
# in falcosecurity/libs (or its fork draios/agent-libs).

# to be called from that directory

git version >/dev/null || (echo "Please install git" && exit 1)

[[ -e .git && -e driver/ ]] || (echo "Please run this script from the root folder of the agent-libs git workspace" && exit 1)

LAST_COMMIT=$(git log -1 --pretty=format:"%h")
# TODO find a better name for tag prefix
LAST_TAG=$(git describe --tags --abbrev=0 --match  "driver-*" || echo "")
if [[ -n "$LAST_TAG" ]]; then
    LAST_VERSION=$(echo $LAST_TAG | cut -c 8-) # TODO beware of driver- prefix
    # Check the number of commits which *actually* changed _something_ in driver/
    N_COMMITS=$(git log --oneline ...${LAST_TAG} -- driver/ | wc -l)
    if [[ ${N_COMMITS} -gt 0 ]]; then
        echo "${LAST_VERSION}+${N_COMMITS}-${LAST_COMMIT}"
    else
        echo "${LAST_VERSION}"
    fi
else
    # We couldn't find a tag, let's make something up
    echo "0.0.0-0-${LAST_COMMIT}"
fi