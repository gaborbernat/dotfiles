# Abbreviated path for a given dir: $HOME -> ~, each parent truncated to one
# char, the git-root component and the basename kept full. Plain text only;
# shared by the prompt (_bgp_pwd) and the statusline (_bgp_pwd_statusline).
function _bgp_pwd_plain --argument-names dir
    test -z "$dir" && set dir $PWD
    set --local pwd_display (string replace -- $HOME "~" $dir)
    set --local git_root (command git --no-optional-locks -C $dir rev-parse --show-toplevel 2>/dev/null)

    if test -n "$git_root"
        # For worktrees, use git-common-dir to find the actual repo location
        set --local git_common (command git --no-optional-locks -C $dir rev-parse --git-common-dir 2>/dev/null)
        if test "$git_common" != ".git" -a -d "$git_common"
            set git_root $git_common
        end

        # Handle symlinks: git returns real paths but dir may use symlinks
        if not string match -q "$git_root*" $dir
            set --local pwd_real (realpath $dir 2>/dev/null)
            if test -n "$pwd_real" && string match -q "$git_root*" $pwd_real
                set --local rel_path (string replace "$git_root/" "" $pwd_real)
                test -n "$rel_path" && set git_root (string replace "/$rel_path" "" $dir) || set git_root $dir
            end
        end

        set --local root_parts (string split / (string replace -- $HOME "~" $git_root))
        set --local pwd_parts (string split / $pwd_display)
        set --local root_count (count $root_parts)
        set --local pwd_count (count $pwd_parts)
        set --local plain_parts

        for i in (seq 1 $pwd_count)
            set --local part $pwd_parts[$i]
            if test $i -eq $root_count -o $i -eq $pwd_count
                # Git root or basename - keep full
                set --append plain_parts $part
            else if test "$part" = "~" -o "$part" = ""
                set --append plain_parts $part
            else
                set --append plain_parts (string sub -l 1 -- $part)
            end
        end

        string join "/" $plain_parts
    else
        # Not in a git repo - truncate all but basename
        set --local parts (string split / $pwd_display)
        set --local num_parts (count $parts)
        set --local plain_parts

        for i in (seq 1 $num_parts)
            set --local part $parts[$i]
            if test $i -eq $num_parts -o "$part" = "~" -o "$part" = ""
                set --append plain_parts $part
            else
                set --append plain_parts (string sub -l 1 -- $part)
            end
        end

        string join "/" $plain_parts
    end
end
