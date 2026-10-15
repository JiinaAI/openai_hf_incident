#!/bin/sh
set -e
# --reload: /app is bind-mounted from the host (see run.sh), so a fix written by security_remediate
# takes effect within a second or two, with no container rebuild or restart needed.
uvicorn app:app --host 0.0.0.0 --port 8300 --reload --reload-dir /app &
uvicorn internal_repo:app --host 0.0.0.0 --port 8301 --reload --reload-dir /app &
wait
