#!/usr/bin/env python3
# ~/.local/bin/remote-daemon.py
# eDio USB Multi Remote Controller daemon
# Reads raw 4-byte HID reports from /dev/hidraw-remote
# Handles remote buttons (MPD/dwm) and mouse pad (uinput virtual mouse)

import struct, subprocess, time, logging, sys, os
import evdev
from evdev import UInput, ecodes as e

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
log = logging.getLogger(__name__)

DEVICE  = '/dev/hidraw-remote'
DISPLAY = os.environ.get('DISPLAY', ':0')
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

    # ncmpcpp view cycling
    18: ['/bin/bash', f'{home}/.local/bin/ncmpcpp-view.sh', 'prev'],
    19: ['/bin/bash', f'{home}/.local/bin/ncmpcpp-view.sh', 'next'],

    # play mode
    20: ['mpc', 'single'],    # window symbol
    21: ['mpc', 'update'],    # calendar symbol
    32: ['mpc', 'repeat'],    # loop symbol

    # number keys 1-9 — switch dwm tags
    23: ['xdotool', 'key', '--clearmodifiers', 'alt+1'],
    24: ['xdotool', 'key', '--clearmodifiers', 'alt+2'],
    25: ['xdotool', 'key', '--clearmodifiers', 'alt+3'],
    26: ['xdotool', 'key', '--clearmodifiers', 'alt+4'],
    27: ['xdotool', 'key', '--clearmodifiers', 'alt+5'],
    28: ['xdotool', 'key', '--clearmodifiers', 'alt+6'],
    29: ['xdotool', 'key', '--clearmodifiers', 'alt+7'],
    30: ['xdotool', 'key', '--clearmodifiers', 'alt+8'],
    31: ['xdotool', 'key', '--clearmodifiers', 'alt+9'],

    # 0 key — jump to queue position 10
    33: ['mpc', 'play', '10'],

    # unmapped but available:
    # 1  (VCR),  2  (DVD),   4  (FM)
    # 5-8 (special), 12 (record), 14 (eject)
    # 22 (audio), 35 (teletext), 36 (search), 46 (center pad click)
    # note: button 64 (0x40) is permanently unusable — aliases with protocol framing byte
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

    # virtual mouse for the circular pad
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
                    # mouse event
                    btn_left  = 1 if b0 & 0x01 else 0
                    btn_right = 1 if b0 & 0x02 else 0

                    dx =  struct.unpack('b', bytes([b1]))[0]
                    dy = -struct.unpack('b', bytes([b2]))[0]  # inverted Y axis

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
