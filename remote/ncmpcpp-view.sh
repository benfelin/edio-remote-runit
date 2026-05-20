#!/bin/bash
# cycles through ncmpcpp views using xdotool
# views in order: 1=playlist, 2=browse, 3=search, 4=library,
#                 5=playlist editor, 6=tag, 7=outputs, 8=visualizer

STATE_FILE="/tmp/ncmpcpp-view"
VIEWS=(1 2 3 4 5 6 7 8)
MAX=${#VIEWS[@]}

# read current index
if [ -f "$STATE_FILE" ]; then
    idx=$(cat "$STATE_FILE")
else
    idx=0
fi

# increment or decrement
if [ "$1" = "next" ]; then
    idx=$(( (idx + 1) % MAX ))
else
    idx=$(( (idx - 1 + MAX) % MAX ))
fi

# save and send keypress
echo $idx > "$STATE_FILE"
key=${VIEWS[$idx]}
DISPLAY="${DISPLAY:-:0}" xdotool key --clearmodifiers "$key"
