function dcr -d "Run a docker compose service then tear down"
    argparse b v -- $argv
    or return 1
    if not set -q argv[1]
        echo "Usage: dcr [-b] [-v] <service> [-- args...]" >&2
        return 1
    end
    set -l flags --force-recreate --abort-on-container-exit --exit-code-from $argv[1]
    if set -q _flag_b
        set -a flags --build
    end
    docker compose up $flags $argv
    set -l rc $status
    set -l down_flags --remove-orphans
    if set -q _flag_v
        set -a down_flags --volumes
    end
    docker compose down $down_flags
    exit $rc
end
