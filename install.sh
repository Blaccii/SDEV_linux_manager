#!/usr/bin/env bash
set -euo pipefail

install -m 755 sdev.py /usr/local/bin/sdev

echo "Installed SDEV to /usr/local/bin/sdev"
echo "Use inside your server folder:"
echo "  cd /home/container"
echo "  sdev adoptserver"
