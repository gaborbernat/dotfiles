function _bgp_pwd_statusline --argument-names max
    set --local dir (string match --regex --groups-only '"current_dir":"([^"]*)"' -- (cat))
    test -z "$dir" && set dir $PWD
    set --local path (_bgp_pwd_plain $dir)

    # ccstatusline's custom-command only clips the end; clip from the left here so the tail (repo + current dir) stays
    # visible.
    if test -n "$max"; and test (string length -- $path) -gt $max
        set path "…"(string sub --start=-(math $max - 1) -- $path)
    end

    echo $path
end
