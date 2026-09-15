#!/bin/sh
# Garbage-collect superseded Claude Code native builds.
# The native installer drops one ~325 MB binary per version into versions/ and
# only repoints the ~/.local/bin/claude symlink; nothing ever removes the old
# ones. Keep the newest few so `claude install <version>` can still roll back.

keep=2
versions_dir="$HOME/.local/share/claude/versions"
app_binary="$HOME/.local/share/claude/ClaudeCode.app/Contents/MacOS/claude"

[ -d "$versions_dir" ] || exit 0

# A build is pinned if the launcher points at it, a live session is executing
# it, or ClaudeCode.app hardlinks it for the bundle-scoped TCC identity.
pinned=$(
    readlink "$HOME/.local/bin/claude"
    ps -axo comm= | grep "^$versions_dir/"
    if [ -e "$app_binary" ]; then
        app_inode=$(ls -i "$app_binary" | awk '{print $1}')
        ls -i "$versions_dir"/* | awk -v inode="$app_inode" '$1 == inode {print $NF}'
    fi
)
protected=$(printf '%s\n' "$pinned" | sed 's|.*/||'; ls -t "$versions_dir" | head -n "$keep")

pruned=""
for version in $(ls "$versions_dir"); do
    printf '%s\n' "$protected" | grep -qxF "$version" && continue
    rm -f "$versions_dir/$version" && pruned="$pruned $version"
done

if [ -n "$pruned" ] && command -v logger >/dev/null 2>&1; then
    printf 'pruned%s\n' "$pruned" | logger -t claude-prune-versions
fi

exit 0
