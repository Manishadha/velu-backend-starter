#!/bin/sh
set -eu

mkdir -p /data /git /workspace
chown -R 10001:10001 /data /git /workspace
chmod -R u+rwX /data /git /workspace
