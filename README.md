# Dotfiles

Personal dotfiles managed with [chezmoi](https://chezmoi.io/).

## Prerequisites

- macOS with [Homebrew](https://brew.sh/) installed, or Fedora Workstation
- GPG key configured for commit signing where used

## Installation

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply gaborbernat/dotfiles
```

On Fedora Workstation, use its packaged Chezmoi:

```bash
sudo dnf install chezmoi git
chezmoi init gaborbernat/dotfiles
chezmoi apply
```

The [RPM manifest](dot_dnf_packages.txt) covers tools available through DNF. Fedora uses uv's
[standalone installer](https://docs.astral.sh/uv/getting-started/installation/) so Fish `u` can update uv's bundled
Python release catalog. Chezmoi enables the Ghostty, xremap, and mise COPRs; the VS Code and Insync HTTPS repositories;
and Fedora Workstation's Steam repository before installing it. Boatswain and Kooha use Flatpak. Bazecor and JetBrains
Toolbox use checksum-checked upstream releases because their selected Linux builds lack suitable RPMs. Run
`chezmoi update` for dotfiles and Fish `u` for package updates.

The first apply changes the login shell, configures GNOME extensions, and adds the account to the `docker` and
`gamemode` groups. Log out and back in to activate those changes. The `docker` group grants
[root-level access](https://docs.docker.com/engine/install/linux-postinstall/). Fish `u` authenticates sudo once before
starting parallel updates; its 30-minute sudo ticket is shared across this account's terminals.

The Antec Flux Pro display uses a [separate community driver](scripts/fedora/flux-pro/setup.sh). Review its
[machine-specific sensor settings](scripts/fedora/flux-pro/config.conf), then install it with:

```bash
bash "$(chezmoi source-path)/scripts/fedora/flux-pro/setup.sh"
```

Sign in to Insync and select the Google Drive folders to sync. Sign in to Steam and enable Steam Play in its
Compatibility settings if you want Windows games. Steam launch options can use `gamemoderun %command%` for GameMode,
`mangohud %command%` for frame times, or `gamescope -w 1920 -h 1080 -W 3840 -H 2160 -f -- %command%` to scale a game
from 1080p to a 4K fullscreen window. Set these per game.

## Post-Installation

Run `gh auth login` for Git operations. Fish sources `~/.secrets` for optional machine-specific variables; Chezmoi does
not commit that file. `maintainer` requires `GITHUB_TOKEN`, while `git-tidy` skips PR checks when it is unset.

## Updating

```bash
chezmoi update
```

## What's Included

- **Shell** — [Fish](https://fishshell.com/docs/current/) with a custom async prompt, functions, completions, and
  [fisher](https://github.com/jorgebucaran/fisher) plugins; [atuin](https://docs.atuin.sh/) history,
  [zoxide](https://github.com/ajeetdsouza/zoxide), [direnv](https://direnv.net/), and [mise](https://mise.jdx.dev/) for
  language runtimes
- **Git** — GPG-signed config with [delta](https://dandavison.github.io/delta/) as the diff pager,
  [tig](https://jonas.github.io/tig/), [git-lfs](https://git-lfs.com/), and a global gitignore
- **Terminal** — [Ghostty](https://ghostty.org/docs) configuration
- **Package managers:** [Homebrew](https://brew.sh/) Brewfile on macOS, DNF RPM manifest on Fedora,
  [uv](https://docs.astral.sh/uv/) Python tools, Cargo packages, and [mise](https://mise.jdx.dev/) runtimes
- **Utilities** — Atuin shell history, duti file associations, [gdu](https://github.com/dundee/gdu) disk usage config
- **Scripts** — custom CLI tools in `~/.local/bin/` backed by uv-managed Python scripts
- **Stream Deck** — Elgato Stream Deck profiles (v2 and v3)
- **AI tooling** — [Claude Code](https://docs.claude.com/en/docs/claude-code) settings, hooks, sounds, and skills with a
  custom [ccstatusline](https://github.com/sirmalloc/ccstatusline) status line; [Codex](https://github.com/openai/codex)
  config; and shared agent skill definitions (e.g. `simp`) linked into Codex and Claude Code

## Tools

Documentation for the notable tools in the macOS Brewfile and Fedora RPM manifest.

**Shell & prompt** — [fish](https://fishshell.com/docs/current/) · [fisher](https://github.com/jorgebucaran/fisher) ·
[atuin](https://docs.atuin.sh/) · [zoxide](https://github.com/ajeetdsouza/zoxide) · [direnv](https://direnv.net/) ·
[mise](https://mise.jdx.dev/)

**Terminal** — [Ghostty](https://ghostty.org/docs)

**Git** — [git](https://git-scm.com/doc) · [gh](https://cli.github.com/manual/) · [tig](https://jonas.github.io/tig/) ·
[git-delta](https://dandavison.github.io/delta/) · [git-lfs](https://git-lfs.com/)

**Files & search** — [ripgrep](https://github.com/BurntSushi/ripgrep) · [fd](https://github.com/sharkdp/fd) ·
[fzf](https://github.com/junegunn/fzf) · [bat](https://github.com/sharkdp/bat) · [lsd](https://github.com/lsd-rs/lsd) ·
[glow](https://github.com/charmbracelet/glow) · [gdu](https://github.com/dundee/gdu)

**Languages & build** — [mise](https://mise.jdx.dev/) · [rustup](https://rust-lang.github.io/rustup/) ·
[GNU parallel](https://www.gnu.org/software/parallel/)

**Python** — [uv](https://docs.astral.sh/uv/) · [ruff](https://docs.astral.sh/ruff/) ·
[ty](https://github.com/astral-sh/ty) · [tox](https://tox.wiki/) · [prek](https://github.com/j178/prek)

**Editors & multiplexers** — [neovim](https://neovim.io/doc/) · [tmux](https://github.com/tmux/tmux/wiki) ·
[mprocs](https://github.com/pvolok/mprocs)

**Data** — [jq](https://jqlang.github.io/jq/manual/) · [yq](https://mikefarah.gitbook.io/yq/)

**AI** — [Claude Code](https://docs.claude.com/en/docs/claude-code) ·
[ccstatusline](https://github.com/sirmalloc/ccstatusline) · [Codex](https://github.com/openai/codex) ·
[opencode](https://opencode.ai/)

## Private overlay

A downstream private chezmoi source can be layered on top of this public one:

```bash
chezmoi apply --source ~/.local/share/chezmoi-private
```

When present it augments the public config without forking it:

| Private file                                    | Effect                                              |
| ----------------------------------------------- | --------------------------------------------------- |
| `~/.local/share/chezmoi-private/Brewfile`       | Adds private-only Homebrew installs                 |
| `~/.local/share/chezmoi-private/Brewfile.skip`  | Drops named public Brewfile entries on that machine |
| `~/.local/share/chezmoi-private/fish_work.fish` | Sourced by fish for work-specific shell config      |
| `~/.local/share/chezmoi-private/gitconfig_work` | Included by git for work identity/settings          |

The brew-bundle runner merges the public Brewfile with the private additions and applies the skip-list.

## Structure

| Path                          | Description                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------ |
| `.chezmoitemplates/`          | Shared template fragments (AI instructions)                                          |
| `dot_agents/`                 | Shared agent skill definitions (linked into Claude Code and Codex)                   |
| `dot_codex/`                  | Codex CLI config, AGENTS.md, and rules                                               |
| `dot_config/atuin/`           | Atuin shell history config                                                           |
| `dot_config/ccstatusline/`    | ccstatusline (Claude Code status line) config                                        |
| `dot_config/fish/`            | Fish shell config, prompt, functions, and completions                                |
| `dot_config/ghostty/`         | Ghostty terminal config                                                              |
| `dot_config/ruff/`            | Global ruff (Python lint/format) config                                              |
| `dot_config/tig/`             | Tig git interface config                                                             |
| `dot_local/bin/`              | Executable wrapper scripts for CLI tools                                             |
| `dot_local/scripts/`          | Python source for CLI tools (uv-managed)                                             |
| `dot_Brewfile.tmpl`           | Homebrew packages (public baseline)                                                  |
| `dot_cargo_packages.txt.tmpl` | Cargo packages, including Fedora fallbacks                                           |
| `dot_dnf_packages.txt`        | Fedora RPM manifest                                                                  |
| `dot_duti`                    | Default application associations                                                     |
| `dot_gdu.yaml`                | gdu disk usage config                                                                |
| `dot_gitconfig.tmpl`          | Git configuration                                                                    |
| `dot_gitignore_global`        | Global gitignore                                                                     |
| `dot_uv_tools.txt.tmpl`       | uv Python tools                                                                      |
| `private_dot_claude/`         | Claude Code settings, hooks, sounds, and skills                                      |
| `private_Library/`            | Stream Deck profiles                                                                 |
| `create_private_dot_secrets`  | Template creating `~/.secrets` (never committed)                                     |
| `run_once_*`                  | One-time setup (uv, rustup, Ghostty symlink)                                         |
| `run_onchange_*`              | On-change scripts (brew, cargo, fisher, uv tools, duti, wrappers, skill/cache links) |
