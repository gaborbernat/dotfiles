function _wt_default_branch -d "Print the branch a remote's HEAD points at" -a bare_root remote
    git -C "$bare_root" symbolic-ref "refs/remotes/$remote/HEAD" 2>/dev/null | string replace "refs/remotes/$remote/" ''
end
