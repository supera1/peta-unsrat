#!/bin/sh
set -eu
export SERVE_ROOT=/usr/share/nginx/html
export SERVE_BIND=127.0.0.1
export SERVE_PORT=8091
export SERVE_MODE=gate
export LOGIN_FILE=/opt/peta/login.html
python3 /opt/peta/serve.py &
exec nginx -g "daemon off;"
