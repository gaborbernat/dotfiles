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

    # Build the list from porcelain: paths with spaces stay intact and the branch (empty for a
    # detached worktree) comes straight from git. Emit each entry when the next 'worktree' header
    # — or the trailing sentinel — arrives, skipping the bare entry.
    set --local entries
    set --local wt_path ""
    set --local branch ""
    set --local is_bare 0
    for line in (git -C "$bare_root" worktree list --porcelain) "worktree "
        switch $line
            case 'worktree *'
                if test -n "$wt_path"; and test "$is_bare" = 0
                    set --local wt_name (basename "$wt_path")
                    set --local last_commit (git -C "$wt_path" log -1 --format="%cr" 2>/dev/null)
                    set --local last_ts (git -C "$wt_path" log -1 --format="%ct" 2>/dev/null)
                    test -z "$last_ts"; and set last_ts 0

                    set --local upstream_info local
                    if test -n "$branch"; and git -C "$bare_root" rev-parse "origin/$branch" &>/dev/null
                        set --local counts (git -C "$wt_path" rev-list --count --left-right "origin/$branch"...HEAD 2>/dev/null)
                        set --local behind (echo $counts | awk '{print $1}')
                        set --local ahead (echo $counts | awk '{print $2}')
                        test -z "$behind"; and set behind 0
                        test -z "$ahead"; and set ahead 0
                        if test "$behind" -gt 0 -a "$ahead" -gt 0
                            set upstream_info "↓$behind ↑$ahead"
                        else if test "$behind" -gt 0
                            set upstream_info "↓$behind"
                        else if test "$ahead" -gt 0
                            set upstream_info "↑$ahead"
                        else
                            set upstream_info "✓"
                        end
                    end

                    set --append entries (printf "%s\t%-24s %-15s %s\t%s\t%s" "$last_ts" "$wt_name" "$last_commit" "$upstream_info" "$wt_path" "$branch")
                end
                set wt_path (string replace 'worktree ' '' -- $line)
                set branch ""
                set is_bare 0
            case 'branch refs/heads/*'
                set branch (string replace 'branch refs/heads/' '' -- $line)
            case bare
                set is_bare 1
        end
    end

    # Sort by last commit (most recent first), then drop the sort-key column
    if test (count $entries) -gt 0
        set entries (printf '%s\n' $entries | sort -t (printf '\t') -k1,1 -rn | cut -f2-)
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
        # fish only runs external processes in parallel, not backgrounded functions, so fan out
        # one subshell per worktree that sources this file and calls the remover. Args go through
        # $argv (never interpolated) so paths with spaces survive.
        set --local self (status filename)
        set --local default_branch (git -C "$bare_root" symbolic-ref --short refs/remotes/upstream/HEAD 2>/dev/null)
        set default_branch (string replace 'upstream/' '' -- "$default_branch")
        if test -z "$default_branch"
            set default_branch (git -C "$bare_root" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)
            set default_branch (string replace 'origin/' '' -- "$default_branch")
        end
        test -z "$default_branch"; and set default_branch main
        for selection in $selections
            set --local path (string split \t $selection)[2]
            set --local name (string split ' ' $selection)[1]
            set --local sel_branch (string split \t $selection)[3]
            fish -c 'source $argv[1]; _wl_remove_worktree $argv[2] $argv[3] $argv[4] $argv[5] $argv[6]' \
                "$self" "$bare_root" "$path" "$name" "$sel_branch" "$default_branch" &
        end
        wait
        wl
    else
        cd "$wt_path"
    end
end

function _wl_remove_worktree -a bare_root wt_path wt_name branch default_branch
    set --local start_time (gdate +%s.%N 2>/dev/null; or date +%s)
    echo "Removing worktree '$wt_name'..."

    # Only reap a lock we can prove is stale: a live-pid agent lock means the tree is in use, and a
    # lock without a pid that isn't a claude agent is a deliberate hold. Warn and skip both.
    set --local lock_reason (_wl_lock_reason "$bare_root" "$wt_path")
    if test -n "$lock_reason"
        set --local lock_pid (string replace -rf '.*pid ([0-9]+).*' '$1' -- "$lock_reason")
        if test -n "$lock_pid"; and kill -0 $lock_pid 2>/dev/null
            printf "⚠ Skipping %s: locked by live agent (pid %s)\n" "$wt_name" "$lock_pid"
            return 1
        end
        if test -z "$lock_pid"; and not string match -q '*claude agent*' -- "$lock_reason"
            printf "⚠ Skipping %s: locked (%s)\n" "$wt_name" "$lock_reason"
            return 1
        end
        git -C "$bare_root" worktree unlock "$wt_path" 2>/dev/null
    end

    set --local worktree_status (git -C "$wt_path" status --porcelain --untracked-files=all 2>/dev/null)
    if test -d "$wt_path"; and test (count $worktree_status) -gt 0
        printf "⚠ Kept %s: worktree has uncommitted or untracked files\n" "$wt_name"
        return 1
    end

    if not begin
            git -C "$bare_root" worktree remove "$wt_path" 2>/dev/null
            or _wl_prune_worktree "$bare_root" "$wt_path"
        end
        printf "Failed to remove %s (%.2fs)\n" "$wt_name" (math (gdate +%s.%N 2>/dev/null; or date +%s) - "$start_time")
        return 1
    end

    if test -n "$branch"
        if git -C "$bare_root" merge-base --is-ancestor "$branch" "$default_branch" 2>/dev/null
            and git -C "$bare_root" branch -d "$branch" 2>/dev/null
            echo "Deleted local branch $branch"
            if git -C "$bare_root" rev-parse --verify "origin/$branch" &>/dev/null
                if git -C "$bare_root" push origin --delete "$branch" 2>/dev/null
                    echo "Deleted remote branch origin/$branch"
                else
                    echo "⚠ Could not delete remote origin/$branch"
                end
            end
        else
            echo "⚠ Kept branch $branch (not merged into $default_branch)"
        end
    end
    printf "Removed %s (%.2fs)\n" "$wt_name" (math (gdate +%s.%N 2>/dev/null; or date +%s) - "$start_time")
end

function _wl_lock_reason -a bare_root wt_path
    git -C "$bare_root" worktree list --porcelain 2>/dev/null | awk -v p="$wt_path" '
        /^worktree /{ cur = substr($0, 10) }
        /^locked/{ if (cur == p) { line = $0; sub(/^locked ?/, "", line); print line } }
    '
end

function _wl_prune_worktree -a bare_root wt_path
    git -C "$bare_root" worktree prune 2>/dev/null
    not git -C "$bare_root" worktree list --porcelain 2>/dev/null | string match -q -- "worktree $wt_path"
end

function _wl_open_pr -a bare_root pr_number
    cd "$bare_root"

    set pr_info (gh pr view $pr_number --json headRefName,headRepository --jq '[.headRefName, .headRepository.url, .headRepository.sshUrl, .headRepository.owner.login] | @tsv')
    or begin
        echo "error: could not fetch PR #$pr_number"
        return 2
    end

    set branch (echo $pr_info | cut -f1)
    set repo_url (echo $pr_info | cut -f2)
    set repo_ssh (echo $pr_info | cut -f3)
    set owner (echo $pr_info | cut -f4)

    if test -z "$branch"
        echo "error: could not determine branch for PR #$pr_number"
        return 2
    end

    set worktree_name (path basename (path resolve "$bare_root"))"-pr-$pr_number"

    if test -d $worktree_name
        echo "Worktree already exists: $worktree_name"
        cd $worktree_name
        return 0
    end

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

    if test -z "$remote_name"
        set existing_url (git remote get-url upstream 2>/dev/null; or git remote get-url origin 2>/dev/null)
        if string match -q 'git@*' "$existing_url"
            set remote_url $repo_ssh
        else
            set remote_url $repo_url
        end

        for remote in (git remote)
            set url (git remote get-url $remote 2>/dev/null)
            if test "$url" = "$remote_url" -o "$url" = "$repo_ssh" -o "$url" = "$repo_url"
                set remote_name $remote
                break
            end
        end

        if test -z "$remote_name"
            set remote_name $owner
            echo "Adding remote: $remote_name ($remote_url)"
            git remote add $remote_name $remote_url
            git config remote.$remote_name.fetch "+refs/heads/*:refs/remotes/$remote_name/*"
        end

        echo "Fetching $remote_name..."
        git fetch $remote_name

        if not git show-ref --verify --quiet refs/remotes/$remote_name/$branch
            echo "error: branch $branch not found on remote $remote_name"
            return 2
        end
    end

    echo "Creating worktree: $worktree_name"
    if git -C "$bare_root" show-ref --verify --quiet "refs/heads/$branch"
        git worktree add $worktree_name $branch
    else
        git worktree add -b $branch $worktree_name $remote_name/$branch
    end

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
