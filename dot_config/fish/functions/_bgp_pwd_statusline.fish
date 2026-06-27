function _bgp_pwd_statusline --description 'Abbreviated cwd for ccstatusline; reads status JSON on stdin. Optional arg: max width (left-clips, keeping the git-root + basename tail)' --argument-names max
    set --local dir (string match --regex --groups-only '"current_dir":"([^"]*)"' -- (cat))
    test -z "$dir" && set dir $PWD
    set --local path (_bgp_pwd_plain $dir)

    # ccstatusline's custom-command only clips the end; clip from the left here
    # so the meaningful tail (repo + current dir) stays visible.
    if test -n "$max"; and test (string length -- $path) -gt $max
        set path "…"(string sub --start=-(math $max - 1) -- $path)
    end

    echo $path
end
