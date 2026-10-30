#!/bin/sh
# Sets the terminal title for a Claude Code hook event: notify.sh EVENT EMOJI [SOUND].
# Claude spawns hooks in a detached session with no controlling terminal, so writing to /dev/tty fails with ENXIO. We
# walk up the process tree to an ancestor still attached to the user's terminal and write the OSC title escape there.

if command -v logger >/dev/null 2>&1; then
    now=$(date '+%H:%M:%S.%N')
    printf '%s %s\n' "${now}" "$1" | logger -t claude-hooks
fi

safe_emoji=$(printf '%s' "$2" | sed 's/[[:cntrl:]]//g')
safe_dir=$(basename "${PWD}" | sed 's/[[:cntrl:]]//g')
title=$(printf '\033]2;%s %s Claude\007' "${safe_emoji}" "${safe_dir}")

if ! { printf '%s' "${title}" >/dev/tty; } 2>/dev/null; then
    pid=${PPID}
    while [ -n "${pid}" ] && [ "${pid}" != "1" ]; do
        tty=$(ps -o tty= -p "${pid}" 2>/dev/null | tr -d ' ')
        if [ -n "${tty}" ] && [ "${tty}" != "??" ]; then
            { printf '%s' "${title}" >"/dev/${tty}"; } 2>/dev/null
            break
        fi
        pid=$(ps -o ppid= -p "${pid}" 2>/dev/null | tr -d ' ')
    done
fi

sound="${HOME}/.claude/sounds/$3"
if [ -f "${sound}" ]; then
    if command -v afplay >/dev/null 2>&1; then
        afplay "${sound}" >/dev/null 2>&1 &
    elif command -v pw-play >/dev/null 2>&1; then
        pw-play "${sound}" >/dev/null 2>&1 &
    fi
fi
