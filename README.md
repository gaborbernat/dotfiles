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

- Fish shell configuration
- Git configuration (with GPG signing)
- Tig configuration
- Ghostty terminal configuration
- Homebrew packages via Brewfile
- uv Python tools
- Cargo packages

## Structure

| File/Directory                     | Description       |
| ---------------------------------- | ----------------- |
| `dot_config/fish/config.fish.tmpl` | Fish shell config |
| `dot_gitconfig.tmpl`               | Git configuration |
| `dot_Brewfile.tmpl`                | Homebrew packages |
| `dot_uv_tools.txt.tmpl`            | uv Python tools   |
| `dot_cargo_packages.txt`           | Cargo packages    |
| `run_*`                            | Setup scripts     |
