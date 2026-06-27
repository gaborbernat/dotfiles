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
            set -l outdated (npm outdated -g --parseable 2>/dev/null | awk -F: '{print $4}')
            if set -q outdated[1]
                npm install -g $outdated
            else
                echo "all global packages already up to date"
            end
        case fisher
            fisher update
        case docker
            if not docker info >/dev/null 2>&1
                echo "Docker is not running — starting Docker Desktop…"
                open -a Docker
                set -l waited 0
                while not docker info >/dev/null 2>&1
                    sleep 2
                    set waited (math $waited + 2)
                    if test $waited -ge 120
                        echo "Docker did not become ready within 120s" >&2
                        return 1
                    end
                end
                echo "Docker is ready (after "$waited"s)"
            end
            update_docker_images
            and docker system prune -f --volumes
        case '*'
            echo "unknown upgrade stage: $name" >&2
            return 2
    end

    set -l rc $status
    test -n "$_U_STATUS_DIR"; and echo $rc >$_U_STATUS_DIR/$name
    return $rc
end
