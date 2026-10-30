function _wt_bare_root -d "Print the bare repository behind the current worktree setup"
    not git rev-parse --git-dir &>/dev/null && echo "Not in a git repository" >&2 && return 1

    # git-common-dir is the bare repo both from its root and from any of its worktrees.
    set --local bare_root (git rev-parse --git-common-dir 2>/dev/null)
    if not git rev-parse --is-bare-repository 2>/dev/null | string match -q true
        and test "$bare_root" = .git -o ! -d "$bare_root"
        echo "Not a bare repository setup" >&2 && return 1
    end
    echo $bare_root
end
