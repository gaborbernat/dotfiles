# Usage: fish context.fish <universal-var> <PATH entries...>
set -gx PATH $argv[2..]
set --local contexts
set --local search_dir $PWD
set --local found_node false
set --local found_python false
set --local found_go false
set --local found_rust false
set --local found_java false

while test "$search_dir" != /
    if test "$found_node" = false -a -f "$search_dir/package.json"
        set --local node_bin (command -v node 2>/dev/null)
        if test -n "$node_bin"
            set --local ver ($node_bin --version 2>/dev/null | string replace 'v' '')
            test -n "$ver" && set --append contexts "node:$ver"
        end
        set found_node true
    end
    if test "$found_python" = false -a \( -f "$search_dir/pyproject.toml" \
            -o -f "$search_dir/setup.py" -o -f "$search_dir/requirements.txt" \)
        set --local python_bin (command -v python3 2>/dev/null)
        if test -n "$python_bin"
            set --local ver ($python_bin --version 2>/dev/null | string replace 'Python ' '')
            test -n "$ver" && set --append contexts "python:$ver"
        end
        set found_python true
    end
    if test "$found_go" = false -a -f "$search_dir/go.mod"
        set --local go_bin (command -v go 2>/dev/null)
        if test -n "$go_bin"
            set --local ver ($go_bin version 2>/dev/null | string match --regex 'go([0-9.]+)' | tail -1)
            test -n "$ver" && set --append contexts "go:$ver"
        end
        set found_go true
    end
    if test "$found_rust" = false -a -f "$search_dir/Cargo.toml"
        set --local rustc_bin (command -v rustc 2>/dev/null)
        if test -n "$rustc_bin"
            set --local ver ($rustc_bin --version 2>/dev/null | string match --regex 'rustc ([0-9.]+)' | tail -1)
            test -n "$ver" && set --append contexts "rust:$ver"
        end
        set found_rust true
    end
    if test "$found_java" = false -a \( -f "$search_dir/build.gradle" \
            -o -f "$search_dir/build.gradle.kts" -o -f "$search_dir/pom.xml" \)
        set --local java_bin (command -v java 2>/dev/null)
        if test -n "$java_bin"
            set --local ver ($java_bin --version 2>/dev/null | head -1 | string match --regex '([0-9.]+)' | tail -1)
            test -n "$ver" && set --append contexts "java:$ver"
        end
        set found_java true
    end
    set search_dir (dirname "$search_dir")
end

if test -f "$PWD/docker-compose.yml" -o -f "$PWD/docker-compose.yaml" \
        -o -f "$PWD/compose.yml" -o -f "$PWD/compose.yaml"
    set --local running (docker compose ps --status running --format '{{.Service}}' 2>/dev/null | string join ',')
    test -n "$running" && set --append contexts "docker:$running"
end

set --universal $argv[1] (string join ' ' $contexts)
