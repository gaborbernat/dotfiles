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

    set use_https true
    set gh_host ""
    set repo_path ""
    if string match -q 'git@*:*' $repo_input
        set use_https false
        set gh_host (string replace -r '^git@([^:]+):.*' '$1' $repo_input)
        set repo_path (string replace -r '^git@[^:]+:(.+?)(?:\.git)?$' '$1' $repo_input)
    else if string match -qr '^https?://' $repo_input
        set gh_host (string replace -r '^https?://([^/]+)/.*' '$1' $repo_input)
        set repo_path (string replace -r '^https?://[^/]+/(.+?)(?:\.git)?$' '$1' $repo_input)
    else
        set repo_path $repo_input
    end

    # GH_HOST points gh at an enterprise GitHub instance.
    test -n "$gh_host"; and set -lx GH_HOST $gh_host

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

    set name (string split / $repo)[2]
    set default_branch_dir $name-(string replace -ra '[^A-Za-z0-9._-]' '-' -- $default_branch)
    set branch_dir $name-(string replace -ra '[^A-Za-z0-9._-]' '-' -- $branch)

    echo "Upstream repo : $repo"
    echo "Default branch: $default_branch"

    set me (gh api user --jq .login)
    or begin
        echo "error: failed to get current user (gh auth status?)"
        return 2
    end

    # A user account cannot own both a parent and its fork, so when we own the repo we push straight to upstream. Org
    # repos still fork to our account.
    if test (string split / $repo)[1] = "$me"
        echo "You own $repo; using it directly, no fork"
        set fork $repo
        set fork_url $upstream_url
    else
        echo "Ensuring fork exists..."
        set fork "$me/$name"

        set fork_err (gh repo fork $repo --fork-name $name 2>&1)
        if test $status -ne 0; and not string match -q "*already exists*" $fork_err
            echo "error: failed to fork $repo: $fork_err"
            return 2
        end

        # Fork creation is async, so the fork may not resolve right away.
        set fork_url ""
        for i in 1 2 3 4 5
            if test "$use_https" = true
                set fork_url (gh repo view $fork --json url --jq '.url' 2>/dev/null)
            else
                set fork_url (gh repo view $fork --json sshUrl --jq '.sshUrl' 2>/dev/null)
            end
            test -n "$fork_url"; and break
            echo "Waiting for fork to be available... ($i/5)"
            sleep 2
        end
        if test -z "$fork_url"
            echo "error: could not resolve fork $fork after retries"
            return 2
        end
    end

    if not test -d $name
        echo "Cloning bare repo..."
        git clone --bare $upstream_url $name; or return $status
    else
        if not git -C "$name" rev-parse --is-bare-repository 2>/dev/null | string match -q true
            echo "error: $name exists but is not the expected bare repository"
            return 2
        end
        set existing_remote (git -C "$name" remote get-url upstream 2>/dev/null)
        if test -z "$existing_remote"
            set existing_remote (git -C "$name" remote get-url origin 2>/dev/null)
        end
        if test -z "$existing_remote"; or not string match -q "*$repo*" -- "$existing_remote"
            echo "error: $name does not point to $repo"
            return 2
        end
        echo "Bare repo already exists, skipping clone"
    end

    cd $name

    if not git remote get-url upstream >/dev/null 2>&1
        git remote rename origin upstream 2>/dev/null
    end
    git config remote.upstream.fetch "+refs/heads/*:refs/remotes/upstream/*"

    if not git remote get-url origin >/dev/null 2>&1
        git remote add origin $fork_url
    end
    git config remote.origin.fetch "+refs/heads/*:refs/remotes/origin/*"

    echo "Fetching upstream"
    git fetch upstream
    echo "Fetching origin"
    git fetch origin 2>/dev/null

    if not test -f CLAUDE.md
        touch CLAUDE.md
    end

    if not test -d $default_branch_dir
        git worktree add $default_branch_dir $default_branch
    end

    if not test -e $default_branch_dir/CLAUDE.md
        ln -s ../CLAUDE.md $default_branch_dir/CLAUDE.md
    end

    # gh repo set-default needs a worktree, not the bare repo.
    cd $default_branch_dir
    gh repo set-default $repo >/dev/null 2>&1
    cd ..

    if not test -d $branch_dir
        if git show-ref --verify --quiet refs/remotes/origin/$branch
            echo "Branch exists on origin: $branch"
            if git show-ref --verify --quiet refs/heads/$branch
                git worktree add $branch_dir $branch
            else
                git worktree add --track -b $branch $branch_dir origin/$branch
            end
        else
            echo "Creating new branch from upstream/$default_branch: $branch"
            git worktree add -b $branch $branch_dir upstream/$default_branch
            cd $branch_dir
            git push -u origin $branch
            cd ..
        end
    else
        echo "Branch worktree already exists: $branch"
    end

    if not test -e $branch_dir/CLAUDE.md
        ln -s ../CLAUDE.md $branch_dir/CLAUDE.md
    end

    cd $branch_dir

    echo ""
    echo "✅ Ready:"
    echo "Repo   : $repo"
    echo "Branch : $branch"
    echo "Path   : "(pwd)
end
