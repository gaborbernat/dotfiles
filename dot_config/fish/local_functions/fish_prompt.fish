function fish_prompt
    # OSC 133 shell integration (skip when VS Code injects its own OSC 633)
    if not set --query VSCODE_SHELL_INTEGRATION
        printf "\e]133;A\a"
    end

    if _bgp_transient_prompt
        if not set --query VSCODE_SHELL_INTEGRATION
            printf "\e]133;B\a"
        end
        return
    end

    set --local prompt "$_bgp_color_pwd$_bgp_pwd$bgp_color_normal"

    if test -n "$$_bgp_git"
        set prompt "$prompt:$_bgp_color_git$$_bgp_git$bgp_color_normal"
    end

    if test -n "$_bgp_cmd_duration"
        set prompt "$prompt $_bgp_color_duration$_bgp_cmd_duration$bgp_color_normal"
    end

    set prompt "$prompt$_bgp_status$bgp_color_normal "

    printf '%s' "$prompt"

    if not set --query VSCODE_SHELL_INTEGRATION
        printf "\e]133;B\a"
    end
end
