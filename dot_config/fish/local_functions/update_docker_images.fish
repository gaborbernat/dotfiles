function update_docker_images -d "Pull Docker images from config file"
    set --local config_file "$HOME/.local/share/chezmoi-private/docker_images.txt"
    test -f "$config_file" || return 0

    while read -l image
        test -z "$image" && continue
        string match -q '#*' "$image" && continue
        echo "Pulling $image..."
        docker pull "$image"
    end <"$config_file"
end
