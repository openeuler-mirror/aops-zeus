#! /bin/bash

abs_path="$INSPECTION_ASSET_PATH/$1"
bash "$abs_path" "${@:2}"
