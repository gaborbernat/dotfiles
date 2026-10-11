function _u_stage -a name -d "Run one upgrade stage for u (one mprocs tab)"
    set -l t0 (date +%s)
    switch $name
        case dnf
            _u_run sudo dnf upgrade --refresh -y
        case flatpak
            _u_run sudo flatpak update --system -y
            set -l system_status $status
            _u_run flatpak update --user -y
            set -l user_status $status
            test $system_status -eq 0 -a $user_status -eq 0
        case brew
            _u_run brew upgrade --greedy --yes
            set -l ok $status
            _u_run brew cleanup
            test $ok -eq 0
        case uv
            _u_run uv self update
            and _u_run update_python
            and _u_run uv tool upgrade --all
            set -l ok $status
            _u_uv_inventory
            test $ok -eq 0
        case rust
            _u_run rustup update
        case cargo
            _u_run cargo install-update (cargo install-update -l 2>/dev/null | string match -rv cargo-nextest | awk "NR>1 && NF {print \$1}")
            and _u_run cargo install --locked cargo-nextest
        case npm
            set -l outdated (npm outdated -g --parseable 2>/dev/null | awk -F: '{print $4}')
            if set -q outdated[1]
                _u_run npm install -g $outdated
            else
                echo "all global packages already up to date"
            end
            set -l ok $status
            _u_npm_inventory
            test $ok -eq 0
        case fisher
            _u_run fisher update
        case docker
            _u_docker
        case firmware extensions bazecor streamdeck
            if test -f /etc/fedora-release
                _u_run update_fedora_extras $name
            else
                echo "$name is a Fedora-only upgrade stage" >&2
                false
            end
        case mise
            if test -f /etc/fedora-release
                if mise upgrade --help | string match -q '*--global*'
                    _u_run mise upgrade --global
                else
                    _u_run mise -C / upgrade
                end
            else
                echo "mise is a Fedora-only upgrade stage" >&2
                false
            end
        case distrobox
            if not test -f /etc/fedora-release
                echo "distrobox is a Fedora-only upgrade stage" >&2
                false
            else if not command -q distrobox
                echo "distrobox is not installed" >&2
                false
            else if distrobox list | string match -rv '^ID\s*\|' | string match -qr '\S'
                _u_run distrobox-upgrade --all
            else
                echo "No Distrobox containers to update"
            end
        case '*'
            echo "unknown upgrade stage: $name" >&2
            return 2
    end

    set -l rc $status
    set -l dur (_u_fmt_dur (math (date +%s) - $t0))
    printf '⏱  %s finished in %s (exit %d)\n' $name $dur $rc
    if test -n "$_U_STATUS_DIR"
        echo $rc >$_U_STATUS_DIR/$name
        echo $dur >$_U_STATUS_DIR/$name.time
    end
    return $rc
end

function _u_docker
    if test (uname) = Darwin
        if not docker info >/dev/null 2>&1
            echo "Docker is not running — starting Docker Desktop…"
            _u_run open -a Docker; or return $status
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
        _u_run update_docker_images
        return $status
    end

    if not systemctl is-active --quiet docker
        _u_run sudo systemctl start docker; or return $status
    end
    if docker info >/dev/null 2>&1
        _u_run update_docker_images
        return $status
    end

    # A new docker-group membership does not reach shells opened before login refresh.
    set -l docker_group (getent group docker)
    if test -n "$docker_group"; and contains (id -un) (string split , (string split -f4 : $docker_group))
        _u_run sg docker -c update_docker_images
        return $status
    end

    docker info >&2
    return 1
end

function _u_run -d "Echo a command (▶ prefix), then run it"
    set_color --bold cyan
    echo "▶ $argv"
    set_color normal
    $argv
end

function _u_fmt_dur -a secs -d "Humanize a duration in seconds"
    if test $secs -ge 60
        echo (math --scale=0 $secs / 60)"m"(math $secs % 60)"s"
    else
        echo "$secs"s
    end
end

function _u_mtime_info -a path -d "Print epoch|YYYY-MM-DD HH:MM for a path's mtime, portable across BSD/GNU stat"
    if test (uname) = Darwin
        /usr/bin/stat -f '%m|%Sm' -t '%Y-%m-%d %H:%M' "$path" 2>/dev/null
    else
        set -l epoch (stat -c '%Y' "$path" 2>/dev/null)
        test -n "$epoch"; and echo "$epoch|"(date -d "@$epoch" '+%Y-%m-%d %H:%M')
    end
end

function _u_npm_inventory -d "List global npm packages, newest-updated first, with version"
    set -l root (npm root -g)
    echo
    echo "Global npm packages (newest first · version · last updated):"
    for spec in (npm ls -g --depth=0 2>/dev/null | string match -r '@?\S+@\S+$')
        set -l pkg (string replace -r '@[^@]+$' '' $spec)
        set -l info (string split '|' (_u_mtime_info "$root/$pkg"))
        printf '%s\t  %-26s %-10s %s\n' $info[1] $pkg (string replace -r '^.*@' '' $spec) $info[2]
    end | sort -rn -k1,1 | cut -f2-
end

function _u_uv_inventory -d "List uv tools, newest-updated first, with version"
    set -l tdir (uv tool dir 2>/dev/null)
    echo
    echo "uv tools (newest first · version · last updated):"
    for line in (uv tool list 2>/dev/null | string match -rv '^([- ]|$)')
        set -l parts (string split ' ' $line)
        set -l info (string split '|' (_u_mtime_info "$tdir/$parts[1]"))
        printf '%s\t  %-26s %-10s %s\n' $info[1] $parts[1] (string replace -r '^v' '' $parts[2]) $info[2]
    end | sort -rn -k1,1 | cut -f2-
end
