function gcw -d "Create or update a worktree from upstream default branch" -a branch
    test -z "$branch" && echo "Usage: gcw <branch-name>" && return 1

    not git rev-parse --git-dir &>/dev/null && echo "Not in a git repository" && return 1

    # git-common-dir is the bare repo both from its root and from any of its worktrees.
    set --local bare_root (git rev-parse --git-common-dir 2>/dev/null)
    if not git rev-parse --is-bare-repository 2>/dev/null | string match -q true
        and test "$bare_root" = .git -o ! -d "$bare_root"
        echo "Not a bare repository setup" && return 1
    end

    set --local worktree_path "$bare_root/"(path basename (path resolve "$bare_root"))"-$branch"

    git -C "$bare_root" worktree prune

    set --local base_remote upstream
    if not git -C "$bare_root" remote | string match -q upstream
        set base_remote origin
    end
    echo "Fetching $base_remote..."
    git -C "$bare_root" fetch $base_remote --quiet

    # The remote HEAD ref stays unset until set-head asks the remote for it.
    git -C "$bare_root" symbolic-ref "refs/remotes/$base_remote/HEAD" &>/dev/null
    or git -C "$bare_root" remote set-head $base_remote --auto 2>/dev/null
    set --local default_branch (git -C "$bare_root" symbolic-ref "refs/remotes/$base_remote/HEAD" 2>/dev/null |
        sed "s|refs/remotes/$base_remote/||")
    test -z "$default_branch" && echo "Cannot determine default branch for $base_remote" && return 1
    set --local base_ref "$base_remote/$default_branch"

    if git -C "$bare_root" show-ref --verify --quiet "refs/heads/$branch"
        if not test -d "$worktree_path"
            echo "Branch '$branch' exists, recreating worktree..."
            git -C "$bare_root" worktree add "$worktree_path" "$branch"
        else
            echo "Rebasing '$branch' against $base_ref..."
            if not git -C "$worktree_path" rebase $base_ref
                echo "Rebase has conflicts — resolve them in $worktree_path"
                cd "$worktree_path"
                return 1
            end
        end
        git -C "$worktree_path" branch --set-upstream-to=origin/"$branch" 2>/dev/null
        or git -C "$worktree_path" push -u origin "$branch"
    else
        echo "Creating new worktree '$branch' from $base_ref..."
        git -C "$bare_root" worktree add --no-track -b "$branch" "$worktree_path" $base_ref
        echo "Pushing to origin and setting upstream..."
        git -C "$worktree_path" push -u origin "$branch"
    end

    if not test -f "$bare_root/CLAUDE.md"
        touch "$bare_root/CLAUDE.md"
    end
    if not test -e "$worktree_path/CLAUDE.md"
        ln -s ../CLAUDE.md "$worktree_path/CLAUDE.md"
    end

    cd "$worktree_path"
    echo "Now in: $worktree_path"
end
