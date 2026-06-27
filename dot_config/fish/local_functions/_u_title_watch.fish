function _u_title_watch -d "Update the terminal title with live u stage counts (running/ok/failed)"
    set -l total (count $argv)
    while true
        set -l ok 0
        set -l fail 0
        set -l done 0
        for s in $argv
            set -l rc (cat $_U_STATUS_DIR/$s 2>/dev/null)
            test -z "$rc"; and continue
            set done (math $done + 1)
            if test "$rc" = 0
                set ok (math $ok + 1)
            else
                set fail (math $fail + 1)
            end
        end
        printf '\033]2;Upgrade ⟳%d ✓%d ✗%d\007' (math $total - $done) $ok $fail >/dev/tty 2>/dev/null
        test $done -ge $total; and break
        sleep 1
    end
end
