function _wt_link_claude_md -d "Link a worktree's CLAUDE.md to the bare repo's" -a bare_root worktree
    # One untracked CLAUDE.md in the bare root serves every worktree under it.
    test -f "$bare_root/CLAUDE.md"; or touch "$bare_root/CLAUDE.md"
    test -e "$worktree/CLAUDE.md"; or ln -s ../CLAUDE.md "$worktree/CLAUDE.md"
end
