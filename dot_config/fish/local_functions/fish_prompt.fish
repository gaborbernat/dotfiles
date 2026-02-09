function fish_prompt
    # OSC 133;A - mark fresh line / start of prompt
    printf "\e]133;A\a"

    # Check for transient mode first
    if _bgp_transient_prompt
        printf "\e]133;B\a"
        return
    end

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

    # OSC 133;B - end of prompt, start of user input
    printf "\e]133;B\a"
end
