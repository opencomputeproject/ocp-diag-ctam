# Copyright (c) NVIDIA CORPORATION
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
#

# pyinstaller command to make binary
pyinstaller_cmd="pyinstaller --add-data=/app/ctam:. --name ctam.build --paths=/app/ctam  --onefile ctam/ctam.py --workpath /tmp --distpath dist --exclude-module sqlite3"

# static to make one executable
staticx_cmd="staticx ./dist/ctam.build ./dist/ctam"

# clear stale files
clean_cmd="rm /app/dist/ctam.build"

# create sample workspace
create_workspace_cmd="cp -r /app/json_spec/input /app/dist/workspace"

# execute commands

$pyinstaller_cmd

$staticx_cmd

$create_workspace_cmd

$clean_cmd