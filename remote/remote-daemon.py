#!/usr/bin/env python3
# ~/.local/bin/remote-daemon.py
# eDio USB Multi Remote Controller daemon
# Reads raw 4-byte HID reports from /dev/hidraw-remote
# Handles remote buttons (MPD/dwm) and mouse pad (uinput virtual mouse)
#
# Protocol (verified across 3 scan runs):
#   byte 0: 0x40 = remote button event  |  0x88+ = mouse event
#   byte 1: 0x00 = press, 0x80 = release  |  signed delta X
#   byte 2: button code                    |  signed delta Y (inverted)
#   byte 3: 0x0F always (footer)
#
# Mouse clicks encoded in byte 0: 0x89 = left, 0x8A = right

import struct, subprocess, time, logging, sys, os
import evdev
from evdev import UInput, ecodes as e

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
log = logging.getLogger(__name__)

DEVICE   = '/dev/hidraw-remote'
DISPLAY  = os.environ.get('DISPLAY', ':0')
DEBOUNCE = 0.15

home = os.path.expanduser('~')

BUTTON_MAP = {
    # transport
    9:  ['mpc', 'prev'],
    10: ['mpc', 'toggle'],
    11: ['mpc', 'next'],
    13: ['mpc', 'stop'],

    # volume
    15: ['mpc', 'volume', '+5'],
    16: ['mpc', 'volume', '-5'],
    17: ['/bin/bash', f'{home}/.local/bin/mpc-mute-toggle.sh'],

    # ncmpcpp view cycling (CH▲/CH▼)
    18: ['/bin/bash', f'{home}/.local/bin/ncmpcpp-view.sh', 'next'],
    19: ['/bin/bash', f'{home}/.local/bin/ncmpcpp-view.sh', 'prev'],

    # play mode (bottom row left — circular double arrow icon)
    32: ['mpc', 'repeat'],

    # dwm tags 1-9 (numpad)
    23: ['xdotool', 'key', '--clearmodifiers', 'alt+1'],
    24: ['xdotool', 'key', '--clearmodifiers', 'alt+2'],
    25: ['xdotool', 'key', '--clearmodifiers', 'alt+3'],
    26: ['xdotool', 'key', '--clearmodifiers', 'alt+4'],
    27: ['xdotool', 'key', '--clearmodifiers', 'alt+5'],
    28: ['xdotool', 'key', '--clearmodifiers', 'alt+6'],
    29: ['xdotool', 'key', '--clearmodifiers', 'alt+7'],
    30: ['xdotool', 'key', '--clearmodifiers', 'alt+8'],
    31: ['xdotool', 'key', '--clearmodifiers', 'alt+9'],

    # dwm view all tags (bottom row centre — 0 key)
    33: ['xdotool', 'key', '--clearmodifiers', 'alt+0'],

    # middle click (double-click button between L/R mouse buttons)
    46: ['xdotool', 'click', '2'],

    # unmapped buttons:
    # row 1 mode selectors : 1(VCR), 2(DVD), 35(Teletext), 4(FM)
    # row 2 context buttons: 5, 6, 7, 8  (mode-dependent dual labels)
    # transport            : 12(rec), 14(source)
    # function row         : 20(window), 21(calendar/Bookmark), 22(audio/NumLock)
    # mouse                : 46(middle click via xdotool)
    # bottom row           : 36(magnifier/search)
}


def run_command(cmd):
    env = os.environ.copy()
    env['DISPLAY'] = DISPLAY
    try:
        result = subprocess.run(
            cmd,
            timeout=3,
            capture_output=True,
            text=True,
            env=env
        )
        if result.returncode != 0:
            log.warning("Command %s failed (rc=%d): %s", cmd, result.returncode, result.stderr.strip())
        else:
            log.info("Command %s OK", cmd)
    except subprocess.TimeoutExpired:
        log.error("Command %s timed out", cmd)
    except Exception as ex:
        log.error("Command %s error: %s", cmd, ex)


def wait_for_device(path, timeout=30):
    deadline = time.monotonic() + timeout
    while not os.path.exists(path):
        if time.monotonic() > deadline:
            raise FileNotFoundError(f"Device not found after {timeout}s: {path}")
        log.info("Waiting for device %s ...", path)
        time.sleep(2)


def main():
    wait_for_device(DEVICE)

    # virtual mouse for the circular trackball pad
    cap = {
        e.EV_REL: [e.REL_X, e.REL_Y],
        e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT],
    }
    mouse = UInput(cap, name='edio-remote-mouse')
    log.info("Virtual mouse created")

    last_fired = {}
    log.info("Listening on %s", DEVICE)

    try:
        with open(DEVICE, 'rb') as f:
            while True:
                data = f.read(4)
                if len(data) < 4:
                    continue

                b0, b1, b2, b3 = struct.unpack('4B', data)

                # validate footer
                if b3 != 0x0F:
                    log.debug("Unexpected report: %s", list(data))
                    continue

                if b0 == 0x40:
                    # remote button event
                    if b1 != 0x00:
                        continue  # release, skip
                    if b2 not in BUTTON_MAP:
                        log.debug("Unmapped button: %d", b2)
                        continue
                    now = time.monotonic()
                    if now - last_fired.get(b2, 0) > DEBOUNCE:
                        last_fired[b2] = now
                        run_command(BUTTON_MAP[b2])

                elif b0 & 0x88 == 0x88:
                    # mouse event — byte 0 low bits are button state
                    btn_left  = 1 if b0 & 0x01 else 0
                    btn_right = 1 if b0 & 0x02 else 0

                    dx =  struct.unpack('b', bytes([b1]))[0]
                    dy = -struct.unpack('b', bytes([b2]))[0]  # Y axis inverted

                    if dx:
                        mouse.write(e.EV_REL, e.REL_X, dx)
                    if dy:
                        mouse.write(e.EV_REL, e.REL_Y, dy)
                    if b0 != 0x88:
                        mouse.write(e.EV_KEY, e.BTN_LEFT,  btn_left)
                        mouse.write(e.EV_KEY, e.BTN_RIGHT, btn_right)
                    mouse.syn()

    except KeyboardInterrupt:
        log.info("Interrupted")
    finally:
        mouse.close()
        log.info("Virtual mouse closed")


if __name__ == '__main__':
    main()
