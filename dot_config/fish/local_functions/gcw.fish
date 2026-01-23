function gcw -d "Create or update a worktree from upstream/main" -a branch
    test -z "$branch" && echo "Usage: gcw <branch-name>" && return 1

    set --local git_dir (git rev-parse --git-dir 2>/dev/null)
    test -z "$git_dir" && echo "Not in a git repository" && return 1

    # For bare repos, git-dir is the repo itself; for worktrees, find the common dir
    set --local bare_root (git rev-parse --git-common-dir 2>/dev/null)
    if not git rev-parse --is-bare-repository 2>/dev/null | string match -q true
        # Not bare - check if we're in a worktree of a bare repo
        if test "$bare_root" != ".git" -a -d "$bare_root"
            # git-common-dir already points to the bare repo
            set bare_root $bare_root
        else
            echo "Not a bare repository setup" && return 1
        end
    end

    set --local worktree_path "$bare_root/$branch"

    # Clean up stale worktree references
    git -C "$bare_root" worktree prune

    echo "Fetching upstream..."
    git -C "$bare_root" fetch upstream --quiet

    if git -C "$bare_root" show-ref --verify --quiet "refs/heads/$branch"
        # Branch exists - rebase against upstream/main
        if not test -d "$worktree_path"
            echo "Branch '$branch' exists, recreating worktree..."
            git -C "$bare_root" worktree add "$worktree_path" "$branch"
        else
            echo "Rebasing '$branch' against upstream/main..."
            git -C "$worktree_path" rebase upstream/main
        end
        # Ensure tracking is set to origin
        git -C "$worktree_path" branch --set-upstream-to=origin/"$branch" 2>/dev/null
        or git -C "$worktree_path" push -u origin "$branch"
    else
        # New branch - create worktree from upstream/main, track origin
        echo "Creating new worktree '$branch' from upstream/main..."
        git -C "$bare_root" worktree add --no-track -b "$branch" "$worktree_path" upstream/main
        echo "Pushing to origin and setting upstream..."
        git -C "$worktree_path" push -u origin "$branch"
    end

    if test -f "$bare_root/CLAUDE.md" -a ! -e "$worktree_path/CLAUDE.md"
        ln -s "$bare_root/CLAUDE.md" "$worktree_path/CLAUDE.md"
    end

    cd "$worktree_path"
    echo "Now in: $worktree_path"
end
