#!/bin/bash
set -euo pipefail

if ! command -v tuxtalk >/dev/null 2>&1 || ! command -v gsettings >/dev/null 2>&1 || \
    [[ ! -S "${XDG_RUNTIME_DIR:-}/bus" ]]; then
    exit 0
fi

schema=org.gnome.settings-daemon.plugins.media-keys
bindings=$(gsettings get "$schema" custom-keybindings)
tuxtalk_path=
while IFS= read -r path; do
    binding="$schema.custom-keybinding:$path"
    case $(gsettings get "$binding" name) in
        "'TuxTalk Dictation'") tuxtalk_path=$path ;;
    esac
done < <(grep -oE '/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/[^/]+/' <<< "$bindings")

if [[ -z "$tuxtalk_path" ]]; then
    tuxtalk_path=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/tuxtalk/
    updated=$(python3 -c 'import ast, sys; paths = ast.literal_eval(sys.argv[1].removeprefix("@as ")); paths.append(sys.argv[2]); print(repr(paths))' \
        "$bindings" "$tuxtalk_path")
    gsettings set "$schema" custom-keybindings "$updated"
fi

binding="$schema.custom-keybinding:$tuxtalk_path"
gsettings set "$binding" name 'TuxTalk Dictation'
gsettings set "$binding" command 'tuxtalk --toggle'
gsettings set "$binding" binding '<Super>d'
