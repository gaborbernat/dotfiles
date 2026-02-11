complete -c dcr -f
complete -c dcr -s h -l help -d "Show help"
complete -c dcr -s b -l build -d "Rebuild image before running"
complete -c dcr -s v -d "Remove volumes on teardown"
complete -c dcr -l no-rm -d "Skip teardown (for debugging)"
complete -c dcr -n "not string match -q -- '-*' (commandline -ct)" -a "(docker compose config --services 2>/dev/null)"
