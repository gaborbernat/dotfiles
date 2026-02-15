# Dotfiles

Personal dotfiles managed with [chezmoi](https://chezmoi.io/).

## Prerequisites

- macOS with [Homebrew](https://brew.sh/) installed
- GPG key configured for commit signing

## Installation

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply gaborbernat/dotfiles
```

## Post-Installation

Create `~/.secrets` with your tokens (this file is sourced by fish but never committed):

```fish
set -gx GITHUB_TOKEN ghp_xxx
# Add other secrets as needed
```

## Updating

```bash
chezmoi update
```

## What's Included

- **Shell** - Fish shell with custom prompt, functions, completions, and
  [fisher](https://github.com/jorgebucaran/fisher) plugins
- **Git** - Global config with GPG signing, tig, and global gitignore
- **Terminals** - Ghostty and WezTerm configurations
- **Package managers** - Homebrew Brewfile, uv Python tools, Cargo packages
- **Utilities** - Atuin shell history, duti file associations, gdu disk usage config
- **Scripts** - Custom CLI tools in `~/.local/bin/` backed by Python scripts
- **Stream Deck** - Elgato Stream Deck profiles (v2 and v3)

## Structure

| Path                     | Description                                                       |
| ------------------------ | ----------------------------------------------------------------- |
| `dot_config/atuin/`      | Atuin shell history config                                        |
| `dot_config/fish/`       | Fish shell config, prompt, functions, and completions             |
| `dot_config/ghostty/`    | Ghostty terminal config                                           |
| `dot_config/tig/`        | Tig git interface config                                          |
| `dot_config/wezterm/`    | WezTerm terminal config                                           |
| `dot_local/bin/`         | Executable wrapper scripts for CLI tools                          |
| `dot_local/scripts/`     | Python source for CLI tools (uv-managed)                          |
| `dot_Brewfile.tmpl`      | Homebrew packages                                                 |
| `dot_cargo_packages.txt` | Cargo packages                                                    |
| `dot_duti`               | Default application associations                                  |
| `dot_gdu.yaml`           | gdu disk usage config                                             |
| `dot_gitconfig.tmpl`     | Git configuration                                                 |
| `dot_gitignore_global`   | Global gitignore                                                  |
| `dot_uv_tools.txt.tmpl`  | uv Python tools                                                   |
| `private_Library/`       | Stream Deck profiles                                              |
| `run_once_*`             | One-time setup (uv, rustup, Ghostty symlink)                      |
| `run_onchange_*`         | On-change scripts (brew, cargo, fisher, uv tools, duti, wrappers) |
