function _bgp_pwd_statusline --description 'Abbreviated cwd for ccstatusline; reads the status JSON on stdin'
    set --local dir (string match --regex --groups-only '"current_dir":"([^"]*)"' -- (cat))
    test -z "$dir" && set dir $PWD
    _bgp_pwd_plain $dir
end
