function fish_prompt
    # Check for transient mode first
    _bgp_transient_prompt && return

    # Build prompt parts
    set --local prompt "$_bgp_color_pwd$_bgp_pwd$bgp_color_normal"

    # Add git info with : separator
    if test -n "$$_bgp_git"
        set prompt "$prompt:$_bgp_color_git$$_bgp_git$bgp_color_normal"
    end

    # Add duration with space if present
    if test -n "$_bgp_cmd_duration"
        set prompt "$prompt $_bgp_color_duration$_bgp_cmd_duration$bgp_color_normal"
    end

    # Add prompt symbol (no leading space)
    set prompt "$prompt$_bgp_status$bgp_color_normal "

    echo -e -n "$prompt"
end
