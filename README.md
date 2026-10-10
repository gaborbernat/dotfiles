# Dotfiles

Personal dotfiles for macOS and Fedora Workstation, managed with [chezmoi](https://www.chezmoi.io/). Other Linux systems
get a smaller apt-based CLI setup.

## Install

On macOS, install [Homebrew](https://brew.sh/) first:

```bash
brew install chezmoi git
chezmoi init --apply gaborbernat/dotfiles
```

On Fedora Workstation:

```bash
sudo dnf install chezmoi git
chezmoi init --apply gaborbernat/dotfiles
```

On an apt-based Linux system, install `chezmoi` and `git` with that distribution's package manager, then run
`chezmoi init --apply gaborbernat/dotfiles`. The [apt manifest](dot_apt_packages.txt) covers CLI tools; the Fedora
GNOME, hardware, and gaming setup only runs on Fedora.

If the repo is already checked out, point chezmoi at that checkout. Put `sourceDir` before any `[data]` section in
`~/.config/chezmoi/chezmoi.toml`:

```toml
sourceDir = "/home/you/git/dotfiles"
```

Use the checkout's absolute path, then run `chezmoi source-path` to check it and `chezmoi apply` to install the files.
Keep that checkout on the branch you want `chezmoi update` to pull. The default source directory is
`~/.local/share/chezmoi`; running `chezmoi` from a different checkout does not select it automatically.

## Platform setup

| Area     | macOS                  | Fedora Workstation         | Other apt-based Linux |
| -------- | ---------------------- | -------------------------- | --------------------- |
| Packages | Homebrew and App Store | DNF, Flatpak, vendor tools | apt CLI tools         |
| Desktop  | duti and LaunchAgent   | GNOME and keyboard setup   | Shared shell config   |
| Hardware | Stream Deck profiles   | Peripheral tools           | None                  |

Shared configuration includes Fish, Ghostty, Git, Atuin, mise, uv tools, Cargo tools, and the `~/.agents/skills` store
linked into Codex and Claude Code. The Fish `u` command updates the installed toolchains and package managers; the
stages depend on the host OS.

### Fedora

Chezmoi enables the configured Ghostty, xremap, and mise COPRs; the VS Code and Insync RPM repositories; and Fedora
Workstation's Steam repository before installing the [RPM manifest](dot_dnf_packages.txt). Fedora's Moby packages
provide Docker, and Distrobox uses that daemon. Membership in the `docker` group grants
[root-level access](https://docs.docker.com/engine/install/linux-postinstall/).

Boatswain, Kooha, LocalSend, Gradia, and ProtonPlus install as system Flatpaks. Copyous comes from the GNOME Extensions
release compatible with the running Shell. Bazecor uses a pinned upstream AppImage and checksum; JetBrains Toolbox
verifies the vendor's checksum for the current release. uv uses its
[standalone installer](https://docs.astral.sh/uv/getting-started/installation/) so `uv self update` works.

GNOME setup covers Dash to Panel on every monitor, Astra Monitor, Copyous, DDC brightness, and xremap for selected
Super-key application shortcuts. Ghostty handles its own Super-key shortcuts. The `agent-awake` user service inhibits
suspend while a Codex, Claude, or ChatGPT client is open; it leaves display blanking available. The first apply also
sets Fish as the login shell, enables SSH, Mosh, and Eternal Terminal, and adds the account to the `docker` and
`gamemode` groups. Log out and back in for the group, shell, and newly installed GNOME extension changes.

The Antec Flux Pro display needs a [separate community driver](scripts/fedora/flux-pro/setup.sh). Review its
[sensor configuration](scripts/fedora/flux-pro/config.conf) for this machine, then install it with:

```bash
bash "$(chezmoi source-path)/scripts/fedora/flux-pro/setup.sh"
```

Sign in to Insync and select the Google Drive folders to sync. Sign in to Steam and enable Steam Play in its
Compatibility settings for Windows games. GameMode, MangoHud, and Gamescope are installed; add their launch options per
game.

### macOS

The [Brewfile](dot_Brewfile.tmpl) installs CLI tools, apps, fonts, and Mac App Store entries. Chezmoi also applies duti
file associations and Stream Deck profiles; it configures the opener socket LaunchAgent where needed. Docker Desktop is
installed separately because its cask asks for sudo on updates.

## Updating

```bash
chezmoi status
chezmoi update
```

`chezmoi update` pulls the configured source checkout and applies it. A separate `chezmoi apply` is only needed after
local edits or a partial apply. `--init` reloads the chezmoi config template; it does not create a missing source
checkout. Run Fish `u` for package and tool updates.

## Local configuration

Run `gh auth login` for GitHub operations. Fish reads `~/.secrets` when it exists; that file is never committed.
`maintainer` needs `GITHUB_TOKEN`, while `git-tidy` skips PR checks without it.

Optional machine-local files live in `~/.local/share/chezmoi-private`. Public scripts read them directly:

| File                           | Use                                         |
| ------------------------------ | ------------------------------------------- |
| `Brewfile` and `Brewfile.skip` | Add or omit Homebrew entries on one machine |
| `fish_work.fish`               | Work-specific Fish settings                 |
| `gitconfig_work`               | Work Git identity and settings              |
| `uv_tools_work.txt`            | Private uv tools                            |
| `codex_work.toml`              | Private Codex config                        |
| `ai_instructions_work.md`      | Private agent instructions                  |

## Source layout

| Path                                               | Use                                |
| -------------------------------------------------- | ---------------------------------- |
| `dot_Brewfile.tmpl`                                | macOS packages                     |
| `dot_dnf_packages.txt`                             | Fedora RPMs                        |
| `dot_apt_packages.txt`                             | apt CLI tools                      |
| `dot_config/`                                      | Shell, terminal, and user services |
| `dot_agents/`, `dot_codex/`, `private_dot_claude/` | Agent configuration                |
| `dot_local/`                                       | CLI wrappers and their source      |
| `scripts/fedora/`                                  | Fedora system and hardware setup   |
| `run_once_*`, `run_onchange_*`, `run_after_*`      | Setup scripts                      |
