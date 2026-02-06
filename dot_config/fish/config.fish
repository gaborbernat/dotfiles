# Core
set -gx EDITOR code
set -gx VISUAL code
set -gx TERM screen-256color
set -gx SHELL /opt/homebrew/bin/fish
set -gx DEBUG_PRINT_LIMIT 1000000

# Path
set -gx PATH \
    $HOME/.local/sbin \
    $HOME/.local/bin \
    $HOME/.cargo/bin \
    /opt/homebrew/opt/gnu-sed/libexec/gnubin \
    /opt/homebrew/opt/gawk/libexec/gnubin \
    /opt/homebrew/opt/gnu-indent/libexec/gnubin \
    /opt/homebrew/opt/coreutils/libexec/gnubin \
    /opt/homebrew/sbin \
    /opt/homebrew/bin/ \
    /usr/local/bin \
    /opt/homebrew/opt/ed/bin \
    /opt/homebrew/opt/findutils/libexec/gnubin \
    /opt/homebrew/opt/flex/bin \
    /opt/homebrew/opt/make/libexec/gnubin \
    /opt/homebrew/opt/zip/bin \
    /Applications/Docker.app/Contents/Resources/bin \
    $HOME/go/bin \
    $PATH

# bb-homebrew
set -gx PKG_CONFIG_PATH \
    /opt/homebrew/opt/openssl@1.1/lib/pkgconfig \
    /opt/homebrew/opt/python@3.14/lib/pkgconfig

set -gx MACOSX_DEPLOYMENT_TARGET (sw_vers -productVersion)
set -gx LDFLAGS "-L/opt/homebrew/opt/ncurses/lib -L/opt/homebrew/opt/sqlite/lib -L/opt/homebrew/opt/librdkafka/lib/"
set -e CFLAGS
set -gx CPPFLAGS "-I/opt/homebrew/opt/ncurses/include -I/opt/homebrew/opt/sqlite/include -I/opt/homebrew/opt/librdkafka/include"

# GO
set -gx GOPATH $HOME/go

# SDKMAN (brew install location)
set -gx SDKMAN_DIR (brew --prefix sdkman-cli 2>/dev/null)/libexec

set -gx DIFF_AGAINST upstream/main
set -gx PY_PYTHON 3.14

if status --is-interactive
    # Add local functions directory
    set --global fish_function_path $__fish_config_dir/local_functions $fish_function_path

    # abbreviations
    abbr --add g git
    abbr --add grv "gh repo view -w"
    abbr --add gpv "gh pr view -w"
    abbr --add prs "gh pr create -f; gh pr view -w"
    abbr --add prsd "gh pr create -f -d; gh pr view -w"
    abbr --add l lsd
    abbr --add v nvim
    abbr --add t tig
    abbr --add b bat
    abbr --add d docker compose
    abbr --add du 'docker compose up -d --wait'
    abbr --add do 'docker compose down'
    abbr --add de 'docker compose exec app'

    abbr --add pcu 'prek autoupdate -j 12'
    abbr --add pcr 'prek run --all-files'
    abbr --add u 'brew upgrade; brew cleanup; uv self update; update_python; uv tool upgrade --all; begin; set tmp (mktemp -d); npm update -g --cache $tmp; rm -rf $tmp; end; rustup update; cargo install-update (cargo install-update -l 2>/dev/null | string match -rv cargo-nextest | awk "NR>1 && NF {print \$1}"); cargo install --locked cargo-nextest; sdk selfupdate; fisher update; update_docker_images; docker system prune -f --volumes | grep "Total reclaimed space"'

    # load tools
    zoxide init fish | source
    atuin init fish | source

    # fish interactive changes
    set fish_greeting
    function fish_title
        echo (basename (pwd)): $argv
    end

    # WezTerm shell integration (OSC7 for tab titles)
    function __wezterm_osc7 --on-variable PWD
        printf "\033]7;file://%s%s\033\\" (hostname) (pwd)
    end
    __wezterm_osc7

    function dbu -a val
        docker compose down $val
        docker compose --progress plain build $val && docker compose up $val
    end

    function dbr -a val
        docker compose build $val && docker compose run --rm $val
    end
    eval (direnv hook fish)

    # Source work-specific config if exists
    if test -f "$HOME/.local/share/chezmoi-private/fish_work.fish"
        source "$HOME/.local/share/chezmoi-private/fish_work.fish"
    end

    # Source secrets if exists
    if test -f "$HOME/.secrets"
        source "$HOME/.secrets"
    end

end

# bun
set --export BUN_INSTALL "$HOME/.bun"
set --export PATH $BUN_INSTALL/bin $PATH
