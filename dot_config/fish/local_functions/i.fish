function i -d "Open IntelliJ IDEA with worktree-aware project name" -a path
    set --local dir (pwd)
    if test -n "$path"
        set dir (realpath "$path" 2>/dev/null)
        if test -z "$dir"; or not test -e "$dir"
            echo "i: no such path: $path" >&2
            return 1
        end
    end
    if not command -q idea
        echo "i: IntelliJ IDEA launcher 'idea' not found" >&2
        return 127
    end

    _idea_project "$dir" JAVA_MODULE "" build target
    idea "$dir" &
end
