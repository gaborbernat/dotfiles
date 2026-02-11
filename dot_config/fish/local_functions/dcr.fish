function dcr -d "Run a docker compose service then tear down"
    argparse h/help b v no-rm -- $argv
    or return 1
    if set -q _flag_help
        echo "Usage: dcr [-b] [-v] [--no-rm] <service> [-- args...]"
        echo
        echo "Run a docker compose service and tear down after exit"
        echo
        echo "Options:"
        echo "  -b, --build  Rebuild image before running"
        echo "  -v           Remove volumes on teardown"
        echo "  --no-rm      Skip teardown (for debugging)"
        echo "  -h, --help   Show this help"
        echo
        echo "Examples:"
        echo "  dcr myservice"
        echo "  dcr -b myservice"
        echo "  dcr --no-rm myservice"
        echo "  dcr myservice -- --verbose"
        return 0
    end
    if not set -q argv[1]
        echo "Usage: dcr [-b] [-v] [--no-rm] <service> [-- args...]" >&2
        return 1
    end
    set -l flags --force-recreate --abort-on-container-exit --exit-code-from $argv[1]
    if set -q _flag_b
        set -a flags --build
    end
    docker compose up $flags $argv
    set -l rc $status
    if not set -q _flag_no_rm
        set -l down_flags --remove-orphans
        if set -q _flag_v
            set -a down_flags --volumes
        end
        docker compose down $down_flags
    end
    exit $rc
end
