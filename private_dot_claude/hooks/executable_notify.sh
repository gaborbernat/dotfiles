#!/bin/sh
# Title-setting helper for Claude Code hooks.
# Claude spawns hooks in a detached session with no controlling terminal, so
# writing to /dev/tty fails with ENXIO. We instead walk up the process tree to
# find an ancestor still attached to the user's terminal and write the OSC
# title-set escape there directly.

event=$1
emoji=$2
sound=$3

printf '%s %s\n' "$(date '+%H:%M:%S.%N')" "$event" >> /tmp/claude-hooks.log

tty_path=""
pid=$PPID
while [ -n "$pid" ] && [ "$pid" != "1" ]; do
    t=$(ps -o tty= -p "$pid" 2>/dev/null | tr -d ' ')
    if [ -n "$t" ] && [ "$t" != "??" ]; then
        tty_path="/dev/$t"
        break
    fi
    pid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
done

if [ -n "$tty_path" ] && [ -w "$tty_path" ]; then
    printf '\033]2;%s %s Claude\007' "$emoji" "$(basename "$PWD")" > "$tty_path"
fi

if [ -n "$sound" ] && [ -f "$HOME/.claude/sounds/$sound" ]; then
    afplay "$HOME/.claude/sounds/$sound" >/dev/null 2>&1 &
fi

exit 0
