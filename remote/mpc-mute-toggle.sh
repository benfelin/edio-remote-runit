#!/bin/bash
# toggles mute by saving and restoring volume

STATE_FILE="/tmp/mpc-volume"

CURRENT=$(mpc volume | grep -oP '\d+')

if [ "$CURRENT" = "0" ]; then
    # currently muted — restore saved volume
    if [ -f "$STATE_FILE" ]; then
        saved=$(cat "$STATE_FILE")
        mpc volume "$saved"
    else
        mpc volume 50   # fallback if no saved volume
    fi
else
    # currently playing — save volume and mute
    echo "$CURRENT" > "$STATE_FILE"
    mpc volume 0
fi
