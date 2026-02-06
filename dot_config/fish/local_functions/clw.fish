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

    echo "Upstream repo : $repo"
    echo "Default branch: $default_branch"

    # Ensure fork exists (idempotent)
    echo "Ensuring fork exists..."
    gh repo fork $repo --fork-name $name --remote=false >/dev/null 2>&1

    # Determine fork URL
    set me (gh api user --jq .login)
    set fork "$me/$name"
    if test "$use_https" = true
        set fork_url (gh repo view $fork --json url --jq '.url' 2>/dev/null)
    else
        set fork_url (gh repo view $fork --json sshUrl --jq '.sshUrl' 2>/dev/null)
    end
    if test -z "$fork_url"
        echo "warning: could not resolve fork repo $fork; origin remote may need manual setup"
    end

    # Clone upstream as bare (skip if exists)
    if not test -d $target_dir
        echo "Cloning bare repo..."
        git clone --bare $upstream_url $target_dir; or return $status
    else
        echo "Bare repo already exists, skipping clone"
    end

    cd $target_dir

    # Wire remotes correctly: upstream is source; origin is your fork (idempotent)
    if not git remote get-url upstream >/dev/null 2>&1
        git remote rename origin upstream 2>/dev/null
    end
    git config remote.upstream.fetch "+refs/heads/*:refs/remotes/upstream/*"

    if test -n "$fork_url"; and not git remote get-url origin >/dev/null 2>&1
        git remote add origin $fork_url
    end
    test -n "$fork_url"; and git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"

    echo "Fetching upstream"
    git fetch upstream
    echo "Fetching origin"
    git fetch origin 2>/dev/null

    # Create shared CLAUDE.md in bare repo root if it doesn't exist
    if not test -f CLAUDE.md
        touch CLAUDE.md
    end

    # Create worktree for default branch (skip if exists)
    if not test -d $default_branch
        git worktree add $default_branch $default_branch
    end

    # Symlink CLAUDE.md to default branch worktree
    if not test -e $default_branch/CLAUDE.md
        ln -s ../CLAUDE.md $default_branch/CLAUDE.md
    end

    # Set gh default to upstream (run inside a worktree)
    cd $default_branch
    gh repo set-default $repo >/dev/null 2>&1
    cd ..

    # Create branch worktree (skip if exists)
    if not test -d $branch
        if git remote get-url origin >/dev/null 2>&1
            if git show-ref --verify --quiet refs/remotes/origin/$branch
                echo "Branch exists on origin: $branch"
                git worktree add $branch origin/$branch
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
    else
        echo "Branch worktree already exists: $branch"
    end

    # Symlink CLAUDE.md to branch worktree
    if not test -e $branch/CLAUDE.md
        ln -s ../CLAUDE.md $branch/CLAUDE.md
    end

    cd $branch

    echo ""
    echo "✅ Ready:"
    echo "Repo   : $repo"
    echo "Branch : $branch"
    echo "Path   : "(pwd)
end
