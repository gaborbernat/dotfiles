# Environment variables that must be set before other conf.d files load
# (conf.d files load alphabetically, before config.fish)

# SDKMAN (homebrew install location) - must be set before sdk.fish plugin
set -gx SDKMAN_DIR /opt/homebrew/opt/sdkman-cli/libexec
