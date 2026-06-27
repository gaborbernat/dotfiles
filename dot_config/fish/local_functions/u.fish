function u -d "Update all development tools (one mprocs tab per tool)"
    set -l stages brew uv rust cargo npm fisher docker
    set -l stagefile $__fish_config_dir/local_functions/_u_stage.fish

    set -gx _U_STATUS_DIR (mktemp -d)
    set -l cmds
    for s in $stages
        set --append cmds "fish -lc 'source $stagefile; _u_stage $s'"
    end

    _u_title_watch $stages &
    set -l watcher $last_pid

    mprocs --proc-list-title "Upgrade packages" --names (string join , $stages) $cmds

    kill $watcher 2>/dev/null

    set -l passed
    set -l failed
    for s in $stages
        set -l rc (cat $_U_STATUS_DIR/$s 2>/dev/null)
        test -z "$rc"; and set rc ?
        if test "$rc" = 0
            set --append passed $s
        else
            set --append failed "$s (exit $rc)"
        end
    end
    rm -rf $_U_STATUS_DIR
    set -e _U_STATUS_DIR

    printf '\033]2;Upgrade ✓%d ✗%d\007' (count $passed) (count $failed)
    set_color --bold
    printf '\nUpgrade: %d passed, %d failed\n' (count $passed) (count $failed)
    set_color normal
    if set -q failed[1]
        set_color red
        printf '  ✗ %s\n' $failed
        set_color normal
        return 1
    end
end
