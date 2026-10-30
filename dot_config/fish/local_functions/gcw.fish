function gcw -d "Create or update a worktree from upstream default branch" -a branch
    test -z "$branch" && echo "Usage: gcw <branch-name>" && return 1

    set --local bare_root (_wt_bare_root); or return 1

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
    set --local default_branch (_wt_default_branch "$bare_root" $base_remote)
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

    _wt_link_claude_md "$bare_root" "$worktree_path"

    cd "$worktree_path"
    echo "Now in: $worktree_path"
end
