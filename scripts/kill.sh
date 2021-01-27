#!/bin/sh

set -e

CURRENT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE_DIR="$(dirname "$CURRENT_DIR")"

cd $BASE_DIR

docker rm $(docker stop $(docker ps -a -q --filter ancestor=ctms_api --format="{{.ID}}"))
