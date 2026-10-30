function dcr -d "Run a docker compose service then tear down"
    argparse h/help b/build v no-rm -- $argv
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
    set -l service $argv[1]
    set -l service_args $argv[2..-1]
    if set -q service_args[1]; and test "$service_args[1]" = --
        set -e service_args[1]
    end
    set -l services (docker compose config --services)
    or return $status
    if not contains -- "$service" $services
        echo "dcr: unknown service: $service" >&2
        return 1
    end
    set -l existing (docker compose ps --all --quiet)
    or return $status
    if set -q existing[1]
        echo "dcr: Compose project already has containers; refusing project-wide teardown" >&2
        return 1
    end
    set -l flags --force-recreate --abort-on-container-exit --exit-code-from $service
    if set -q _flag_b
        set -a flags --build
    else if test -f Dockerfile
        set -l image_name (docker compose config --format json 2>/dev/null |
            jq -r ".services[\"$service\"].image // empty")
        if test -n "$image_name"
            set -l image_created (docker inspect --format='{{.Created}}' "$image_name" 2>/dev/null)
            if test -n "$image_created"
                set -l dockerfile_mtime
                set -l image_ts (string replace -r '[.+].*' '' $image_created)
                set -l image_mtime
                if test (uname) = Darwin
                    set dockerfile_mtime (stat -f %m Dockerfile 2>/dev/null)
                    set image_mtime (date -j -f '%Y-%m-%dT%H:%M:%S' $image_ts +%s 2>/dev/null)
                else
                    set dockerfile_mtime (stat -c %Y Dockerfile 2>/dev/null)
                    set image_mtime (date -u -d "$image_ts" +%s 2>/dev/null)
                end
                if test -n "$dockerfile_mtime" -a -n "$image_mtime" -a $dockerfile_mtime -gt $image_mtime
                    echo "Dockerfile changed, rebuilding..."
                    set -a flags --build
                end
            end
        end
    end
    if set -q service_args[1]
        set -l run_flags
        if contains -- --build $flags
            set run_flags --build
        end
        docker compose run $run_flags $service $service_args
    else
        docker compose up $flags $service
    end
    set -l rc $status
    if not set -q _flag_no_rm
        set -l down_flags --remove-orphans
        if set -q _flag_v
            set -a down_flags --volumes
        end
        docker compose down $down_flags
    end
    return $rc
end
