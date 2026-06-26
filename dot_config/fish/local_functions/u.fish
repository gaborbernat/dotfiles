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

    for step in $steps
        set_color --bold yellow
        echo "▶ $step"
        set_color normal
        eval $step
    end
end

function npm_update
    npm outdated -g --parseable 2>/dev/null | awk -F: '{print $4}' | xargs npm install -g
end

function cargo_update
    cargo install-update (cargo install-update -l 2>/dev/null | string match -rv cargo-nextest | awk "NR>1 && NF {print \$1}")
end
