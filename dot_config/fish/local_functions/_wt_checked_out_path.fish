function _wt_checked_out_path -d "Print the worktree path that has a branch checked out, if any" -a branch
    git worktree list | string replace -rf -- '^(.+?)\s+\S+ \['(string escape --style=regex -- $branch)'\]$' '$1'
end
