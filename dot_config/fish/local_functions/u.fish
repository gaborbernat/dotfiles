function u -d "Update all development tools"
    set -l steps \
        "brew upgrade --yes" \
        "brew cleanup" \
        "uv self update" \
        update_python \
        "uv tool upgrade --all" \
        npm_update \
        "rustup update" \
        cargo_update \
        "cargo install --locked cargo-nextest" \
        "fisher update" \
        update_docker_images \
        "docker system prune -f --volumes"

    set -l failed
    for step in $steps
        set_color --bold yellow
        echo "▶ $step"
        set_color normal

        set -l start (date +%s)
        eval $step
        set -l rc $status
        set -l elapsed (math (date +%s) - $start)

        if test $rc -eq 130
            set_color --bold red
            echo "■ interrupted after "$elapsed"s — aborting u"
            set_color normal
            return 130
        else if test $rc -ne 0
            set --append failed "$step (exit $rc)"
            set_color red
            echo "✗ $step failed (exit $rc, "$elapsed"s)"
            set_color normal
        end
    end

    if set -q failed[1]
        set_color --bold red
        printf '\n%d step(s) failed:\n' (count $failed)
        printf '  ✗ %s\n' $failed
        set_color normal
        return 1
    end

    set_color --bold green
    echo "✓ all updates complete"
    set_color normal
end

function npm_update
    npm outdated -g --parseable 2>/dev/null | awk -F: '{print $4}' | xargs npm install -g
end

function cargo_update
    cargo install-update (cargo install-update -l 2>/dev/null | string match -rv cargo-nextest | awk "NR>1 && NF {print \$1}")
end
