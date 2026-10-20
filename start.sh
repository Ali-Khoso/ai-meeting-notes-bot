#!/usr/bin/env bash
set -euo pipefail
pulseaudio --start --exit-idle-time=-1
pactl load-module module-null-sink sink_name=meet sink_properties=device.description=MeetingAudio >/dev/null
pactl set-default-sink meet
exec xvfb-run -a -s '-screen 0 1280x800x24' python -m app.server
