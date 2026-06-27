function _u_stage -a name -d "Run one upgrade stage for u (one mprocs tab)"
    switch $name
        case brew
            brew upgrade --yes
            and brew cleanup
        case uv
            uv self update
            and update_python
            and uv tool upgrade --all
        case rust
            rustup update
        case cargo
            cargo install-update (cargo install-update -l 2>/dev/null | string match -rv cargo-nextest | awk "NR>1 && NF {print \$1}")
            and cargo install --locked cargo-nextest
        case npm
            npm outdated -g --parseable 2>/dev/null | awk -F: '{print $4}' | xargs npm install -g
        case fisher
            fisher update
        case docker
            update_docker_images
            and docker system prune -f --volumes
        case '*'
            echo "unknown upgrade stage: $name" >&2
            return 2
    end
end
