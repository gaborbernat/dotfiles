# Lives in functions/, not local_functions/, because the statusline calls it from non-interactive fish.
function _bgp_pwd_plain --argument-names dir
    test -z "$dir" && set dir $PWD
    set --local parts (string split / (string replace -- $HOME "~" $dir))
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
