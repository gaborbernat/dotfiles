return {
    default_prog = {"/usr/local/bin/pwsh", "-NoLogo"},
    launch_menu = {
        {args = {"htop"}}, {label = "Bash", args = {"bash"}},
        {label = "zsh", args = {"zsh"}}, {label = "Fish", args = {"fish"}}
    }
}
