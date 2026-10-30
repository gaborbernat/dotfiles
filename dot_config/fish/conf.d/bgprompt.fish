status is-interactive || exit

# The async jobs report back through universal variables, so key the names by pid to keep shells apart.
set --global _bgp_git _bgp_git_$fish_pid
set --global _bgp_context _bgp_context_$fish_pid

function $_bgp_git --on-variable $_bgp_git
    commandline --function repaint
end

function $_bgp_context --on-variable $_bgp_context
    commandline --function repaint
end

# Pure string work with no git calls, so `cd` never blocks on the filesystem; the async git job below
# decides whether we are in a repo.
function _bgp_pwd --on-variable PWD
    set --local plain_result (_bgp_pwd_plain $PWD)

    # Bold the components kept full (git root, basename); they are the only multi-char segments since parents are
    # truncated to one char.
    set --local colored_parts
    for part in (string split / $plain_result)
        if test (string length -- "$part") -gt 1 -a "$part" != "~"
            set --append colored_parts (set_color --bold)"$part"(set_color normal; set_color $bgp_color_pwd)
        else
            set --append colored_parts $part
        end
    end
    set --local colored_result (string join "/" $colored_parts)
    set --global _bgp_pwd (string replace --regex --all -- '/' \
        (set_color brblack)"/"(set_color normal; set_color $bgp_color_pwd) $colored_result)
end

function _bgp_postexec --on-event fish_postexec
    set --local last_status $pipestatus
    set --global _bgp_status "$_bgp_color_prompt$bgp_symbol_prompt"

    for code in $last_status
        if test $code -ne 0
            set --local codes (string join " " $last_status)
            set --global _bgp_status "$_bgp_color_error| $codes $_bgp_color_prompt$_bgp_color_error$bgp_symbol_prompt"
            break
        end
    end

    if test "$CMD_DURATION" -lt 100
        set --global _bgp_cmd_duration ""
        return
    end

    set --local out ""

    if test "$CMD_DURATION" -lt 1000
        set out "$CMD_DURATION"ms
    else if test "$CMD_DURATION" -lt 60000
        set --local secs (math --scale=2 $CMD_DURATION / 1000)
        set secs (string replace --regex -- '\.?0+$' '' $secs)
        set out "$secs"s
    else if test "$CMD_DURATION" -lt 3600000
        set --local mins (math --scale=0 $CMD_DURATION / 60000)
        set --local secs (math --scale=0 $CMD_DURATION / 1000 % 60)
        set out "$mins"m
        test $secs -gt 0 && set out "$out $secs"s
    else
        set --local hours (math --scale=0 $CMD_DURATION / 3600000)
        set --local mins (math --scale=0 $CMD_DURATION / 60000 % 60)
        set out "$hours"h
        test $mins -gt 0 && set out "$out $mins"m
    end

    set --global _bgp_cmd_duration "$out"
end

function _bgp_prompt --on-event fish_prompt
    set --query _bgp_status || set --global _bgp_status "$_bgp_color_prompt$bgp_symbol_prompt"
    set --query _bgp_pwd || _bgp_pwd

    command kill $_bgp_last_git_pid 2>/dev/null
    command kill $_bgp_last_context_pid 2>/dev/null

    # Clear before re-detecting so the prompt picks up a version switched by nvm use, pyenv and the like.
    set --erase $_bgp_context

    fish --private $__fish_config_dir/bgprompt/git.fish $_bgp_git \
        "$bgp_symbol_git_dirty" "$bgp_symbol_git_ahead" "$bgp_symbol_git_behind" &
    set --global _bgp_last_git_pid $last_pid

    # Pass PATH explicitly to keep the nvm/pyenv changes made in this shell.
    fish $__fish_config_dir/bgprompt/context.fish $_bgp_context $PATH &
    set --global _bgp_last_context_pid $last_pid
end

function _bgp_fish_exit --on-event fish_exit
    set --erase $_bgp_git
    set --erase $_bgp_context
end

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
        printf '%s' "$_bgp_color_prompt$bgp_symbol_prompt$bgp_color_normal "
        return 0
    end
    return 1
end

bind \r _bgp_transient
bind \n _bgp_transient
bind -M insert \r _bgp_transient
bind -M insert \n _bgp_transient

set --global bgp_color_normal (set_color normal)

for color in bgp_color_{pwd,git,error,prompt,duration,context}
    function $color --on-variable $color --inherit-variable color
        set --query $color && set --global _$color (set_color $$color)
    end && $color
end

set --query bgp_color_error || set --global bgp_color_error $fish_color_error
set --query bgp_color_pwd || set --global bgp_color_pwd green
set --query bgp_color_git || set --global bgp_color_git yellow
set --query bgp_color_duration || set --global bgp_color_duration brblack
set --query bgp_color_context || set --global bgp_color_context brblack
set --query bgp_symbol_prompt || set --global bgp_symbol_prompt "❯"
set --query bgp_symbol_git_dirty || set --global bgp_symbol_git_dirty "•"
set --query bgp_symbol_git_ahead || set --global bgp_symbol_git_ahead "↑"
set --query bgp_symbol_git_behind || set --global bgp_symbol_git_behind "↓"
