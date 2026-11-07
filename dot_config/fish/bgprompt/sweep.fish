# Erases the prompt variables of shells that died without firing fish_exit (a closed terminal, SIGKILL, OOM).
set --local live (ps -A -o pid= | string trim)
for name in (set --universal --names | string match --regex '^_bgp_(?:git|context)_\d+$')
    contains -- (string replace --regex '.*_' '' -- $name) $live
    or set --universal --erase $name
end
