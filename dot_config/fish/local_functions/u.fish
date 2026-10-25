function u -d "Update all development tools (one mprocs tab per tool)"
    set -l stages uv rust cargo npm fisher docker
    if test (uname) = Darwin
        set --prepend stages brew casks
    else if command -q dnf
        if command -q flatpak
            set stages dnf flatpak $stages
        else
            set --prepend stages dnf
        end
        if test -f /etc/fedora-release
            set stages $stages firmware extensions bazecor streamdeck gamescope ghostty tuxtalk mise distrobox
        end
    end
    set -l stagefile $__fish_config_dir/local_functions/_u_stage.fish
    source $stagefile

    set -l runner
    if command -q mprocs
        set runner mprocs
    else if command -q dekit
        set runner dekit mprocs
    else
        echo "u needs mprocs or dekit" >&2
        return 127
    end

    if contains dnf $stages
        sudo -v; or return $status
    end
    set -gx _U_STATUS_DIR (mktemp -d)
    set -l cmds
    for s in $stages
        test "$s" = casks; and continue
        set --append cmds "fish -lc 'source $stagefile; _u_stage $s'"
    end
    set -l parallel_stages (string match -v casks -- $stages)
    $runner --proc-list-title "Upgrade packages" --names (string join , $parallel_stages) $cmds
    if contains casks $stages
        _u_stage casks
    end

    set -l npass 0
    set -l nfail 0
    set_color --bold
    printf '\nUpgrade summary:\n'
    set_color normal
    for s in $stages
        set -l rc (cat $_U_STATUS_DIR/$s 2>/dev/null)
        test -z "$rc"; and set rc ?
        set -l dur (cat $_U_STATUS_DIR/$s.time 2>/dev/null)
        test -z "$dur"; and set dur -
        if test "$rc" = 0
            set npass (math $npass + 1)
            set_color green
            printf '  ✓ %-8s %s\n' $s $dur
        else
            set nfail (math $nfail + 1)
            set_color red
            printf '  ✗ %-8s %s (exit %s)\n' $s $dur $rc
        end
        set_color normal
    end
    printf '%d passed, %d failed\n' $npass $nfail

    rm -rf $_U_STATUS_DIR
    set -e _U_STATUS_DIR
    printf '\033]2;Upgrade ✓%d ✗%d\007' $npass $nfail
    test $nfail -eq 0
end
