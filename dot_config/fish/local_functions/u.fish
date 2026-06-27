function u -d "Update all development tools (one mprocs tab per tool)"
    set -l stages brew uv rust cargo npm fisher docker
    set -l stagefile $__fish_config_dir/local_functions/_u_stage.fish

    set -gx _U_STATUS_DIR (mktemp -d)
    set -l cmds
    for s in $stages
        set --append cmds "fish -lc 'source $stagefile; _u_stage $s'"
    end

    mprocs --proc-list-title "Upgrade packages" --names (string join , $stages) $cmds

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
