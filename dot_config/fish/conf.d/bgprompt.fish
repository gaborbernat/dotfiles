status is-interactive || exit

# Unique variable names per fish process
set --global _bgp_git _bgp_git_$fish_pid
set --global _bgp_context _bgp_context_$fish_pid

# Repaint on async git update
function $_bgp_git --on-variable $_bgp_git
    commandline --function repaint
end

# Repaint on async context update
function $_bgp_context --on-variable $_bgp_context
    commandline --function repaint
end

# PWD formatting - full git root, single letter for all other dirs, bold basename
function _bgp_pwd --on-variable PWD
    set --local git_root (command git --no-optional-locks rev-parse --show-toplevel 2>/dev/null)

    if set --query git_root[1]
        set --erase _bgp_skip_git_prompt
    else if command git --no-optional-locks rev-parse --is-bare-repository 2>/dev/null | string match -q true
        set --erase _bgp_skip_git_prompt
    else
        set --global _bgp_skip_git_prompt
    end

    # Replace $HOME with ~ for display
    set --local pwd_display (string replace -- $HOME "~" $PWD)

    if test -n "$git_root"
        # For worktrees, use git-common-dir to find the actual repo location
        set --local git_common (command git --no-optional-locks rev-parse --git-common-dir 2>/dev/null)
        # If git_common is a .git file/folder inside git_root, use git_root; otherwise use git_common's parent
        if test "$git_common" != ".git" -a -d "$git_common"
            # Worktree case: git_common points to bare repo
            set git_root $git_common
        end

        # Handle symlinks: git returns real paths but PWD may use symlinks
        if not string match -q "$git_root*" $PWD
            set --local pwd_real (realpath $PWD 2>/dev/null)
            if test -n "$pwd_real" && string match -q "$git_root*" $pwd_real
                set --local rel_path (string replace "$git_root/" "" $pwd_real)
                test -n "$rel_path" && set git_root (string replace "/$rel_path" "" $PWD) || set git_root $PWD
            end
        end

        # Inside a git repo
        set --local git_root_display (string replace -- $HOME "~" $git_root)
        set --local git_base (basename $git_root)

        # Split paths into components
        set --local root_parts (string split / $git_root_display)
        set --local pwd_parts (string split / $pwd_display)

        # Find how many parts are in the git root
        set --local root_count (count $root_parts)
        set --local pwd_count (count $pwd_parts)

        # Build result
        set --local result_parts

        for i in (seq 1 $pwd_count)
            set --local part $pwd_parts[$i]

            if test $i -lt $root_count
                # Before git root - truncate (but keep ~ as is)
                if test "$part" = "~" -o "$part" = ""
                    set --append result_parts $part
                else
                    set --append result_parts (string sub -l 1 $part)
                end
            else if test $i -eq $root_count
                # Git root itself - keep full, make bold
                set --append result_parts (set_color --bold)"$part"(set_color normal; set_color $bgp_color_pwd)
            else if test $i -eq $pwd_count
                # Last component (basename) - keep full, make bold
                set --append result_parts (set_color --bold)"$part"(set_color normal; set_color $bgp_color_pwd)
            else
                # Inside repo but not basename - truncate
                set --append result_parts (string sub -l 1 $part)
            end
        end

        set --local result (string join "/" $result_parts)
        # Dim the slashes, reset to pwd color after
        set --global _bgp_pwd (string replace --regex --all -- '/' (set_color brblack)"/"(set_color normal; set_color $bgp_color_pwd) $result)
    else
        # Not in a git repo - truncate all but basename
        set --local parts (string split / $pwd_display)
        set --local num_parts (count $parts)
        set --local result_parts

        for i in (seq 1 $num_parts)
            set --local part $parts[$i]
            if test $i -eq $num_parts
                # Basename - keep full, bold
                set --append result_parts (set_color --bold)"$part"(set_color normal; set_color $bgp_color_pwd)
            else if test "$part" = "~" -o "$part" = ""
                set --append result_parts $part
            else
                set --append result_parts (string sub -l 1 $part)
            end
        end

        set --local result (string join "/" $result_parts)
        # Dim the slashes, reset to pwd color after
        set --global _bgp_pwd (string replace --regex --all -- '/' (set_color brblack)"/"(set_color normal; set_color $bgp_color_pwd) $result)
    end
end

# Post-exec: capture status and duration
function _bgp_postexec --on-event fish_postexec
    set --local last_status $pipestatus
    set --global _bgp_status "$_bgp_color_prompt$bgp_symbol_prompt"

    for code in $last_status
        if test $code -ne 0
            set --global _bgp_status "$_bgp_color_error| "(string join " " $last_status)" $_bgp_color_prompt$_bgp_color_error$bgp_symbol_prompt"
            break
        end
    end

    # Command duration formatting
    # < 100ms: don't show
    # 100-999ms: show as XXXms
    # >= 1s: show as X.XXs (strip trailing zeros)
    # >= 60s: Xm Xs
    # >= 1h: Xh Xm

    if test "$CMD_DURATION" -lt 100
        set --global _bgp_cmd_duration ""
        return
    end

    set --local out ""

    if test "$CMD_DURATION" -lt 1000
        # Show as milliseconds
        set out "$CMD_DURATION"ms
    else if test "$CMD_DURATION" -lt 60000
        # Show as seconds with 2 decimal precision, strip trailing zeros
        set --local secs (math --scale=2 $CMD_DURATION / 1000)
        # Strip trailing zeros after decimal
        set secs (string replace --regex -- '\.?0+$' '' $secs)
        set out "$secs"s
    else if test "$CMD_DURATION" -lt 3600000
        # Show as Xm Xs
        set --local mins (math --scale=0 $CMD_DURATION / 60000)
        set --local secs (math --scale=0 $CMD_DURATION / 1000 % 60)
        set out "$mins"m
        test $secs -gt 0 && set out "$out $secs"s
    else
        # Show as Xh Xm
        set --local hours (math --scale=0 $CMD_DURATION / 3600000)
        set --local mins (math --scale=0 $CMD_DURATION / 60000 % 60)
        set out "$hours"h
        test $mins -gt 0 && set out "$out $mins"m
    end

    set --global _bgp_cmd_duration "$out"
end

# Prompt event: trigger async git and context detection
function _bgp_prompt --on-event fish_prompt
    set --query _bgp_status || set --global _bgp_status "$_bgp_color_prompt$bgp_symbol_prompt"
    set --query _bgp_pwd || _bgp_pwd

    # Kill previous async processes
    command kill $_bgp_last_git_pid 2>/dev/null
    command kill $_bgp_last_context_pid 2>/dev/null

    # Always clear context before re-detecting (handles nvm use, pyenv, etc.)
    set --erase $_bgp_context

    # Async git info
    if not set --query _bgp_skip_git_prompt
        fish --private --command "
            set branch (
                command git symbolic-ref --short HEAD 2>/dev/null ||
                command git describe --tags --exact-match HEAD 2>/dev/null ||
                command git rev-parse --short HEAD 2>/dev/null |
                    string replace --regex -- '(.+)' '@\$1'
            )

            # Check if in a bare repo worktree where dirname matches branch
            set --local hide_branch false
            set --local git_common (command git rev-parse --git-common-dir 2>/dev/null)
            if test \"\$git_common\" != \".git\" -a \"\$git_common\" != \".\" -a -d \"\$git_common\"
                # In a worktree - check if git_common is the bare repo
                if command git -C \"\$git_common\" rev-parse --is-bare-repository 2>/dev/null | string match -q true
                    if test (basename \$PWD) = \"\$branch\"
                        set hide_branch true
                    end
                end
            end

            if test \"\$hide_branch\" = true
                test -z \"\$$_bgp_git\" && set --universal $_bgp_git \"\"
            else
                test -z \"\$$_bgp_git\" && set --universal $_bgp_git \"\$branch\"
            end

            command git diff-index --quiet HEAD 2>/dev/null
            set --local dirty_status \$status
            set --local info \"\"
            if test \$dirty_status -eq 1
                set info \"$bgp_symbol_git_dirty\"
            else
                # Check for untracked files
                count (command git ls-files --others --exclude-standard 2>/dev/null) >/dev/null && set info \"$bgp_symbol_git_dirty\"
            end

            command git rev-list --count --left-right @{upstream}...@ 2>/dev/null | read behind ahead

            set --local upstream \"\"
            switch \"\$behind \$ahead\"
                case \" \" \"0 0\"
                case \"0 *\"
                    set upstream \" $bgp_symbol_git_ahead\$ahead\"
                case \"* 0\"
                    set upstream \" $bgp_symbol_git_behind\$behind\"
                case \"*\"
                    set upstream \" $bgp_symbol_git_ahead\$ahead $bgp_symbol_git_behind\$behind\"
            end

            if test \"\$hide_branch\" = true
                set --universal $_bgp_git \"\$info\$upstream\"
            else
                set --universal $_bgp_git \"\$branch\$info\$upstream\"
            end
        " &
        set --global _bgp_last_git_pid $last_pid
    else
        set $_bgp_git ""
    end

    # Async context detection (node/python/go/rust versions - supports multiple)
    # Fully async - uses fish -c (not --private) to inherit current PATH from nvm/pyenv
    fish -c "
        set --local contexts
        set --local search_dir \$PWD
        set --local found_node false
        set --local found_python false
        set --local found_go false
        set --local found_rust false
        set --local found_java false

        # Search up for project markers (find all ecosystems)
        while test \"\$search_dir\" != \"/\"
            if test \"\$found_node\" = false -a -f \"\$search_dir/package.json\"
                set --local node_bin (command -v node 2>/dev/null)
                if test -n \"\$node_bin\"
                    set --local ver (\$node_bin --version 2>/dev/null | string replace 'v' '')
                    test -n \"\$ver\" && set --append contexts \"node:\$ver\"
                end
                set found_node true
            end
            if test \"\$found_python\" = false -a \\( -f \"\$search_dir/pyproject.toml\" -o -f \"\$search_dir/setup.py\" -o -f \"\$search_dir/requirements.txt\" \\)
                set --local python_bin (command -v python3 2>/dev/null)
                if test -n \"\$python_bin\"
                    set --local ver (\$python_bin --version 2>/dev/null | string replace 'Python ' '')
                    test -n \"\$ver\" && set --append contexts \"python:\$ver\"
                end
                set found_python true
            end
            if test \"\$found_go\" = false -a -f \"\$search_dir/go.mod\"
                set --local go_bin (command -v go 2>/dev/null)
                if test -n \"\$go_bin\"
                    set --local ver (\$go_bin version 2>/dev/null | string match --regex 'go([0-9.]+)' | tail -1)
                    test -n \"\$ver\" && set --append contexts \"go:\$ver\"
                end
                set found_go true
            end
            if test \"\$found_rust\" = false -a -f \"\$search_dir/Cargo.toml\"
                set --local rustc_bin (command -v rustc 2>/dev/null)
                if test -n \"\$rustc_bin\"
                    set --local ver (\$rustc_bin --version 2>/dev/null | string match --regex 'rustc ([0-9.]+)' | tail -1)
                    test -n \"\$ver\" && set --append contexts \"rust:\$ver\"
                end
                set found_rust true
            end
            if test \"\$found_java\" = false -a \\( -f \"\$search_dir/build.gradle\" -o -f \"\$search_dir/build.gradle.kts\" -o -f \"\$search_dir/pom.xml\" \\)
                set --local java_bin (command -v java 2>/dev/null)
                if test -n \"\$java_bin\"
                    set --local ver (\$java_bin --version 2>/dev/null | head -1 | string match --regex '([0-9.]+)' | tail -1)
                    test -n \"\$ver\" && set --append contexts \"java:\$ver\"
                end
                set found_java true
            end
            set search_dir (dirname \"\$search_dir\")
        end

        # Docker compose - check for running containers in current project
        if test -f \"\$PWD/docker-compose.yml\" -o -f \"\$PWD/docker-compose.yaml\" -o -f \"\$PWD/compose.yml\" -o -f \"\$PWD/compose.yaml\"
            set --local running (docker compose ps --status running --format '{{.Service}}' 2>/dev/null | string join ',')
            test -n \"\$running\" && set --append contexts \"docker:\$running\"
        end

        set --universal $_bgp_context (string join ' ' \$contexts)
    " &
    set --global _bgp_last_context_pid $last_pid
end

# Cleanup on exit
function _bgp_fish_exit --on-event fish_exit
    set --erase $_bgp_git
    set --erase $_bgp_context
end

# Transient prompt
function _bgp_transient
    if test -n "$_bgp_transient_pending"
        set --erase _bgp_transient_pending
        commandline --function execute
    else if not string length -q -- (commandline --current-buffer | string trim)
        set --global _bgp_transient_pending 1
        commandline --function repaint
    else
        commandline --function execute
    end
end

function _bgp_transient_prompt
    if set --query _bgp_transient_pending
        echo -e -n "$_bgp_color_prompt$bgp_symbol_prompt$bgp_color_normal "
        return 0
    end
    return 1
end

# Bind Enter for transient prompt
bind \r _bgp_transient
bind \n _bgp_transient
bind -M insert \r _bgp_transient
bind -M insert \n _bgp_transient

# Initialize colors
set --global bgp_color_normal (set_color normal)

for color in bgp_color_{pwd,git,error,prompt,duration,context}
    function $color --on-variable $color --inherit-variable color
        set --query $color && set --global _$color (set_color $$color)
    end && $color
end

# Default values
set --query bgp_color_error || set --global bgp_color_error $fish_color_error
set --query bgp_color_pwd || set --global bgp_color_pwd green
set --query bgp_color_git || set --global bgp_color_git yellow
set --query bgp_color_duration || set --global bgp_color_duration brblack
set --query bgp_color_context || set --global bgp_color_context brblack
set --query bgp_symbol_prompt || set --global bgp_symbol_prompt "❯"
set --query bgp_symbol_git_dirty || set --global bgp_symbol_git_dirty "•"
set --query bgp_symbol_git_ahead || set --global bgp_symbol_git_ahead "↑"
set --query bgp_symbol_git_behind || set --global bgp_symbol_git_behind "↓"
