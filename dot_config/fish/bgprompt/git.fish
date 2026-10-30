# Usage: fish git.fish <universal-var> <dirty-symbol> <ahead-symbol> <behind-symbol>
set --local var $argv[1]
set --local symbol_dirty $argv[2]
set --local symbol_ahead $argv[3]
set --local symbol_behind $argv[4]

set branch (
    command git symbolic-ref --short HEAD 2>/dev/null ||
    command git describe --tags --exact-match HEAD 2>/dev/null ||
    command git rev-parse --short HEAD 2>/dev/null |
        string replace --regex -- '(.+)' '@$1'
)

# A bare-repo worktree named after its branch already shows the branch in the path.
set --local hide_branch false
set --local git_common (command git rev-parse --git-common-dir 2>/dev/null)
if test "$git_common" != ".git" -a "$git_common" != "." -a -d "$git_common"
    if command git -C "$git_common" rev-parse --is-bare-repository 2>/dev/null | string match -q true
        if test (basename $PWD) = "$branch"
            set hide_branch true
        end
    end
end

if test "$hide_branch" = true
    test -z "$$var" && set --universal $var ""
else
    test -z "$$var" && set --universal $var "$branch"
end

command git diff-index --quiet HEAD 2>/dev/null
set --local dirty_status $status
set --local info ""
if test $dirty_status -eq 1
    set info "$symbol_dirty"
else
    count (command git ls-files --others --exclude-standard 2>/dev/null) >/dev/null &&
        set info "$symbol_dirty"
end

command git rev-list --count --left-right @{upstream}...@ 2>/dev/null | read behind ahead

set --local upstream ""
switch "$behind $ahead"
    case " " "0 0"
    case "0 *"
        set upstream " $symbol_ahead$ahead"
    case "* 0"
        set upstream " $symbol_behind$behind"
    case "*"
        set upstream " $symbol_ahead$ahead $symbol_behind$behind"
end

if test "$hide_branch" = true
    set --universal $var "$info$upstream"
else
    set --universal $var "$branch$info$upstream"
end
