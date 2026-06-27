function u -d "Update all development tools (one mprocs tab per tool)"
    set -l stages brew uv rust cargo npm fisher docker
    set -l stagefile $__fish_config_dir/local_functions/_u_stage.fish

    set -l cmds
    for s in $stages
        set --append cmds "fish -lc 'source $stagefile; _u_stage $s'"
    end

    mprocs --names (string join , $stages) $cmds
end
