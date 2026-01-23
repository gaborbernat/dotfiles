function clw --description "Clone upstream as bare + worktrees, ensure fork, checkout or create branch"
    if test (count $argv) -ne 2
        echo "usage: clw <repo-url-or-owner/name> <branch>"
        return 2
    end

    set repo_input $argv[1]
    set branch $argv[2]

    if not type -q gh
        echo "error: gh CLI is required"
        return 2
    end

    # Detect protocol: use SSH only if explicitly passed SSH URL, otherwise default to HTTPS
    set use_https true
    if string match -q 'git@*:*' $repo_input
        set use_https false
    end

    # Extract hostname from URL if present
    # Supports SSH (git@host:path) and HTTPS (https://host/path) formats
    set gh_host ""
    if string match -q 'git@*:*' $repo_input
        # SSH format: git@hostname:owner/repo.git
        set gh_host (string replace -r '^git@([^:]+):.*' '$1' $repo_input)
    else if string match -q 'https://*' $repo_input
        # HTTPS format: https://hostname/owner/repo.git
        set gh_host (string replace -r '^https://([^/]+)/.*' '$1' $repo_input)
    else if string match -q 'http://*' $repo_input
        # HTTP format: http://hostname/owner/repo.git
        set gh_host (string replace -r '^http://([^/]+)/.*' '$1' $repo_input)
    end

    # Set GH_HOST for enterprise GitHub instances
    if test -n "$gh_host"
        set -x GH_HOST $gh_host
    end

    # Extract owner/repo from URL
    set repo_path ""
    if string match -q 'git@*:*' $repo_input
        # SSH format: git@hostname:owner/repo.git -> owner/repo
        set repo_path (string replace -r '^git@[^:]+:(.+?)(?:\.git)?$' '$1' $repo_input)
    else if string match -q 'https://*' $repo_input; or string match -q 'http://*' $repo_input
        # HTTPS format: https://hostname/owner/repo.git -> owner/repo
        set repo_path (string replace -r '^https?://[^/]+/(.+?)(?:\.git)?$' '$1' $repo_input)
    else
        # Assume owner/repo format
        set repo_path $repo_input
    end

    # Resolve repo info
    set repo (gh repo view $repo_path --json nameWithOwner --jq '.nameWithOwner')
    or begin
        echo "error: unable to resolve repo: $repo_input"
        return 2
    end

    if test "$use_https" = true
        set upstream_url (gh repo view $repo --json url --jq '.url')
    else
        set upstream_url (gh repo view $repo --json sshUrl --jq '.sshUrl')
    end
    set default_branch (gh repo view $repo --json defaultBranchRef --jq '.defaultBranchRef.name')

    set owner (string split / $repo)[1]
    set name (string split / $repo)[2]

    set target_dir $name

    if test -e $target_dir
        echo "error: directory already exists: $target_dir"
        return 2
    end

    echo "Upstream repo : $repo"
    echo "Default branch: $default_branch"

    # Ensure fork exists (idempotent)
    echo "Ensuring fork exists..."
    gh repo fork $repo --fork-name $name --remote=false >/dev/null 2>&1

    # Determine fork URL (SSH or HTTPS based on input format):
    # If you already have a local clone elsewhere, gh can still resolve your fork via 'gh repo fork' + API,
    # but easiest is to ask gh for YOUR fork explicitly:
    set me (gh api user --jq .login)
    set fork "$me/$name"
    if test "$use_https" = true
        set fork_url (gh repo view $fork --json url --jq '.url' 2>/dev/null)
    else
        set fork_url (gh repo view $fork --json sshUrl --jq '.sshUrl' 2>/dev/null)
    end
    if test -z "$fork_url"
        # Fallback: if fork naming differs, ask gh for the parent/fork network; last resort keep origin unset.
        echo "warning: could not resolve fork repo $fork; origin remote may need manual setup"
    end

    # Clone upstream as bare
    echo "Cloning bare repo..."
    git clone --bare $upstream_url $target_dir; or return $status

    cd $target_dir

    # Wire remotes correctly: upstream is source; origin is your fork
    git remote rename origin upstream
    if test -n "$fork_url"
        git remote add origin $fork_url
    end

    # Fetch everything
    git fetch --all --prune --prune-tags

    # Create worktree for default branch
    git worktree add $default_branch $default_branch

    # Set gh default to upstream (run inside a worktree)
    cd $default_branch
    gh repo set-default $repo >/dev/null 2>&1
    cd ..

    # If origin exists and branch exists on origin, use it; else create from upstream/default and push to origin
    if git remote get-url origin >/dev/null 2>&1
        if git show-ref --verify --quiet refs/remotes/origin/$branch
            echo "Branch exists on origin: $branch"
            git worktree add $branch $branch
        else
            echo "Creating new branch from upstream/$default_branch: $branch"
            git worktree add -b $branch $branch upstream/$default_branch
            cd $branch
            git push -u origin $branch
            cd ..
        end
    else
        echo "note: no origin remote configured; creating branch locally from upstream/$default_branch"
        git worktree add -b $branch $branch upstream/$default_branch
    end

    cd $branch

    echo ""
    echo "✅ Ready:"
    echo "Repo   : $repo"
    echo "Branch : $branch"
    echo "Path   : "(pwd)
end
