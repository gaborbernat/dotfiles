# Abbreviated path for a given dir: $HOME -> ~, each parent truncated to one
# char and the basename kept full. Plain text only; shared by the prompt and statusline.
function _bgp_pwd_plain --argument-names dir
    test -z "$dir" && set dir $PWD
    set --local pwd_display (string replace -- $HOME "~" $dir)
    set --local parts (string split / $pwd_display)
    set --local part_count (count $parts)
    set --local plain_parts

    for i in (seq 1 $part_count)
        set --local part $parts[$i]
        if test $i -eq $part_count -o "$part" = "~" -o "$part" = ""
            set --append plain_parts $part
        else
            set --append plain_parts (string sub -l 1 -- $part)
        end
    end

    string join / $plain_parts
end
