#!/bin/sh
# Garbage-collects superseded Claude Code native builds.
# The native installer drops one ~325 MB binary per version into versions/ and only repoints the ~/.local/bin/claude
# symlink, so nothing removes the old ones. The newest two stay so `claude install <version>` can still roll back.

versions_dir="$HOME/.local/share/claude/versions"

[ -d "$versions_dir" ] || exit 0

# A build is pinned if the launcher points at it, a live session is executing it, or ClaudeCode.app hardlinks it for the
# bundle-scoped TCC identity.
pinned=$(
    readlink "$HOME/.local/bin/claude"
    if [ "$(uname)" = Linux ]; then
        for exe in /proc/[0-9]*/exe; do
            path=$(readlink "$exe" 2>/dev/null) || continue
            case "$path" in
                "$versions_dir"/*) printf '%s\n' "$path" ;;
            esac
        done
    else
        ps -axo comm= | grep "^$versions_dir/"
    fi
    app_binary="$HOME/.local/share/claude/ClaudeCode.app/Contents/MacOS/claude"
    if [ -e "$app_binary" ]; then
        app_inode=$(ls -i "$app_binary" | awk '{print $1}')
        ls -i "$versions_dir"/* | awk -v inode="$app_inode" '$1 == inode {print $NF}'
    fi
)
protected=$(printf '%s\n' "$pinned" | sed 's|.*/||'; ls -t "$versions_dir" | head -n 2)

pruned=""
for path in "$versions_dir"/*; do
    [ -f "$path" ] || continue
    version=${path##*/}
    printf '%s\n' "$protected" | grep -qxF "$version" && continue
    rm -f "$path" && pruned="$pruned $version"
done

if [ -n "$pruned" ] && command -v logger >/dev/null 2>&1; then
    printf 'pruned%s\n' "$pruned" | logger -t claude-prune-versions
fi

exit 0
