function fish_prompt
    # OSC 133 shell integration (skip when VS Code injects its own OSC 633)
    if not set --query VSCODE_SHELL_INTEGRATION
        printf "\e]133;A\a"
    end

    # Check for transient mode first
    if _bgp_transient_prompt
        if not set --query VSCODE_SHELL_INTEGRATION
            printf "\e]133;B\a"
        end
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

    printf '%s' "$prompt"

    if not set --query VSCODE_SHELL_INTEGRATION
        printf "\e]133;B\a"
    end
end
