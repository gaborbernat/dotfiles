function wl -d "List worktrees for bare repo (interactive: enter=cd, ctrl-d=delete)"
    set --local git_dir (git rev-parse --git-dir 2>/dev/null)
    test -z "$git_dir" && echo "Not in a git repository" && return 1

    set --local bare_root (git rev-parse --git-common-dir 2>/dev/null)
    if not git rev-parse --is-bare-repository 2>/dev/null | string match -q true
        if test "$bare_root" != ".git" -a -d "$bare_root"
            set bare_root $bare_root
        else
            echo "Not a bare repository setup" && return 1
        end
    end

    # Ensure fetch refspecs are set (one-time fix, no fetch)
    git -C "$bare_root" config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*" 2>/dev/null
    git -C "$bare_root" config remote.upstream.fetch "+refs/heads/*:refs/remotes/upstream/*" 2>/dev/null

    # Build worktree list
    set --local entries
    for wt in (git -C "$bare_root" worktree list | string match -v "*bare*")
        set --local wt_path (echo $wt | awk '{print $1}')
        set --local wt_name (basename "$wt_path")
        set --local branch (git -C "$wt_path" symbolic-ref --short HEAD 2>/dev/null)
        set --local last_commit (git -C "$wt_path" log -1 --format="%cr" 2>/dev/null)
        set --local upstream_info ""

        set --local remote_ref ""
        if git -C "$bare_root" rev-parse "origin/$branch" &>/dev/null
            set remote_ref "origin/$branch"
        end

        if test -n "$remote_ref"
            set --local counts (git -C "$wt_path" rev-list --count --left-right "$remote_ref"...HEAD 2>/dev/null)
            set --local behind (echo $counts | awk '{print $1}')
            set --local ahead (echo $counts | awk '{print $2}')
            if test "$behind" -gt 0 -a "$ahead" -gt 0
                set upstream_info "↓$behind ↑$ahead"
            else if test "$behind" -gt 0
                set upstream_info "↓$behind"
            else if test "$ahead" -gt 0
                set upstream_info "↑$ahead"
            else
                set upstream_info "✓"
            end
        else
            set upstream_info local
        end

        set --append entries (printf "%-24s %-15s %s\t%s" "$wt_name" "$last_commit" "$upstream_info" "$wt_path")
    end

    set --local legend (printf "%-24s %-15s %s" "WORKTREE" "LAST COMMIT" "ORIGIN")
    set --local header (basename "$bare_root")" (bare) | enter=cd, c=create, o=open PR, d=delete (multi), r=refresh, q=quit
$legend"
    set --local result (printf '%s\n' $entries | fzf --height=~50% --header="$header" --expect=c,o,d,r --bind=q:abort --delimiter='\t' --with-nth=1 --multi)

    test (count $result) -eq 0 && return 0

    set --local key $result[1]
    set --local selections $result[2..-1]
    set --local wt_path (string split \t $selections[1])[2]
    set --local wt_name (string split ' ' $selections[1])[1]

    if test "$key" = c
        read -P "Branch name: " branch_name
        test -z "$branch_name" && return 0
        gcw $branch_name
    else if test "$key" = o
        read -P "PR number: " pr_number
        test -z "$pr_number" && return 0
        _wl_open_pr "$bare_root" "$pr_number"
    else if test "$key" = r
        echo "Fetching origin and upstream..."
        git -C "$bare_root" fetch origin --quiet 2>/dev/null
        git -C "$bare_root" fetch upstream --quiet 2>/dev/null
        wl
    else if test "$key" = d
        cd "$bare_root"
        for selection in $selections
            set --local path (string split \t $selection)[2]
            set --local name (string split ' ' $selection)[1]
            _wl_remove_worktree "$bare_root" "$path" "$name" &
        end
        wl
    else
        cd "$wt_path"
    end
end

function _wl_remove_worktree -a bare_root wt_path wt_name
    set --local start_time (date +%s.%N)
    echo "Removing worktree '$wt_name'..."
    if git -C "$bare_root" worktree remove "$wt_path" 2>&1
        or git -C "$bare_root" worktree remove --force "$wt_path" 2>&1
        git -C "$bare_root" branch -d "$wt_name" 2>/dev/null
        set --local end_time (date +%s.%N)
        set --local elapsed (math "$end_time - $start_time")
        printf "Deleted branch %s (%.2fs)\n" "$wt_name" "$elapsed"
    else
        set --local end_time (date +%s.%N)
        set --local elapsed (math "$end_time - $start_time")
        printf "Failed to remove %s (%.2fs)\n" "$wt_name" "$elapsed"
    end
end

function _wl_open_pr -a bare_root pr_number
    cd "$bare_root"

    set pr_info (gh pr view $pr_number --json headRefName,headRepository,headRepositoryOwner --jq '[.headRefName, .headRepository.name, .headRepositoryOwner.login] | @tsv')
    or begin
        echo "error: could not fetch PR #$pr_number"
        return 2
    end

    set branch (echo $pr_info | cut -f1)
    set repo_name (echo $pr_info | cut -f2)
    set owner (echo $pr_info | cut -f3)

    if test -z "$branch"
        echo "error: could not determine branch for PR #$pr_number"
        return 2
    end

    set worktree_name "pr-$pr_number"

    if test -d $worktree_name
        echo "Worktree already exists: $worktree_name"
        cd $worktree_name
        return 0
    end

    # First check if any existing remote already has the branch (after fetching)
    echo "Fetching remotes..."
    git fetch --all --quiet

    set remote_name ""
    for remote in (git remote)
        if git show-ref --verify --quiet refs/remotes/$remote/$branch
            set remote_name $remote
            echo "Found branch on remote: $remote_name"
            break
        end
    end

    # If branch not found, check if PR author's repo is available and add if needed
    if test -z "$remote_name"
        set target_repo (string lower "$owner/$repo_name")
        for remote in (git remote)
            set remote_url (git remote get-url $remote 2>/dev/null)
            set remote_repo (string replace -r '^.*[:/]([^/]+/[^/]+?)(?:\.git)?$' '$1' "$remote_url" | string lower)
            if test "$remote_repo" = "$target_repo"
                set remote_name $remote
                break
            end
        end

        if test -z "$remote_name"
            set remote_name $owner
            echo "Adding remote: $remote_name"
            set existing_url (git remote get-url upstream 2>/dev/null; or git remote get-url origin 2>/dev/null)
            if string match -q 'git@*' "$existing_url"
                set remote_url (gh repo view "$owner/$repo_name" --json sshUrl --jq '.sshUrl' 2>/dev/null)
            else
                set remote_url (gh repo view "$owner/$repo_name" --json url --jq '.url' 2>/dev/null)
            end
            if test -z "$remote_url"
                echo "error: could not resolve remote URL for $owner/$repo_name"
                return 2
            end
            git remote add $remote_name $remote_url
            git config remote.$remote_name.fetch "+refs/heads/*:refs/remotes/$remote_name/*"
        end

        echo "Fetching $remote_name"
        git fetch $remote_name

        if not git show-ref --verify --quiet refs/remotes/$remote_name/$branch
            echo "error: branch $branch not found on remote $remote_name"
            return 2
        end
    end

    echo "Creating worktree: $worktree_name"
    git worktree add -b $branch $worktree_name $remote_name/$branch

    cd $worktree_name
    git branch --set-upstream-to=$remote_name/$branch

    if not test -f ../CLAUDE.md
        touch ../CLAUDE.md
    end
    if not test -e CLAUDE.md
        ln -s ../CLAUDE.md CLAUDE.md
    end

    echo "✅ Ready: PR #$pr_number ($branch)"
end
