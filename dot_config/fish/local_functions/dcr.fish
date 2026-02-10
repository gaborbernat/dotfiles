function dcr -d "Run a docker compose service then tear down"
    argparse b -- $argv
    or return 1
    if not set -q argv[1]
        echo "Usage: dcr [-b] <service>" >&2
        return 1
    end
    set -l flags --force-recreate --abort-on-container-exit --exit-code-from $argv[1]
    if set -q _flag_b
        set -a flags --build
    end
    docker compose up $flags
    set -l rc $status
    docker compose down --remove-orphans
    exit $rc
end
