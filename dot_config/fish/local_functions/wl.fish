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
    set --local header (basename "$bare_root")" (bare) | enter=cd, c=create, d=delete, r=refresh, q=quit
$legend"
    set --local result (printf '%s\n' $entries | fzf --height=~50% --header="$header" --expect=c,d,r --bind=q:abort --delimiter='\t' --with-nth=1)

    test (count $result) -eq 0 && return 0

    set --local key $result[1]
    set --local selection $result[2]
    set --local wt_path (string split \t $selection)[2]
    set --local wt_name (string split ' ' $selection)[1]

    if test "$key" = c
        read -P "Branch name: " branch_name
        test -z "$branch_name" && return 0
        gcw $branch_name
    else if test "$key" = r
        echo "Fetching origin and upstream..."
        git -C "$bare_root" fetch origin --quiet 2>/dev/null
        git -C "$bare_root" fetch upstream --quiet 2>/dev/null
        wl
    else if test "$key" = d
        echo "Removing worktree '$wt_name'..."
        git -C "$bare_root" worktree remove "$wt_path"
        git -C "$bare_root" branch -d "$wt_name" 2>/dev/null
        cd "$bare_root"
        wl
    else
        cd "$wt_path"
    end
end
