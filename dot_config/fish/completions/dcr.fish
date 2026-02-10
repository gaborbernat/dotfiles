complete -c dcr -f
complete -c dcr -s b -d "Rebuild image before running"
complete -c dcr -s v -d "Remove volumes on teardown"
complete -c dcr -n "not string match -q -- '-*' (commandline -ct)" -a "(docker compose config --services 2>/dev/null)"
