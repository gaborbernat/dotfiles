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

If the repo is already checked out, initialize chezmoi with that checkout as its source:

```bash
chezmoi --source "$HOME/git/dotfiles" init
chezmoi source-path
chezmoi apply
```

Replace the example path if needed. Init records its absolute path as `sourceDir` in `~/.config/chezmoi/chezmoi.toml`;
the config template retains it when you run `chezmoi update --init`. Keep the checkout on the branch you want to pull.
Chezmoi otherwise uses `~/.local/share/chezmoi`, regardless of the shell's directory.

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

The [ChatGPT desktop app](https://learn.chatgpt.com/docs/linux/linux-app) includes Codex. Its official Fedora RPM adds
OpenAI's signed DNF repository, so Fish `u` updates it with the other RPMs.

Kooha, LocalSend, Gradia, ProtonPlus, and BlueBubbles install as system Flatpaks. StreamController comes from Flathub
and uses its OS, media, clock, and AMD GPU plugins for the Stream Deck. Copyous comes from the GNOME Extensions release
compatible with the running Shell. Bazecor uses a pinned upstream AppImage and checksum; JetBrains Toolbox verifies the
vendor's checksum for the current release. uv uses its
[standalone installer](https://docs.astral.sh/uv/getting-started/installation/) so `uv self update` works.

The Fedora Stream Deck keeps the macOS emoji keys and adds live clocks, CPU, RAM, and GPU tiles. Main links directly to
the Fedora, System, Media, and Emoji pages. These pages provide app launchers, hardware details, playback, and volume
controls; page links and launchers use installed icon assets. Chezmoi creates missing pages and leaves later edits made
in StreamController intact. The [Unicode input patch](scripts/fedora/streamcontroller-unicode.diff) completes the key
sequence used by OSPlugin's text action for emoji and kaomoji.

GNOME uses Dash to Panel for a top taskbar on each monitor. Until Fedora's RPM supports indicator mirroring, chezmoi
installs [the upstream change](https://github.com/home-sweet-gnome/dash-to-panel/pull/2570) as a user extension. Astra
Monitor, Copyous, and DDC brightness then appear on both panels. xremap handles selected Super-key application
shortcuts. Ghostty handles its own Super-key shortcuts. The `agent-awake` user service inhibits suspend while a Codex,
Claude, or ChatGPT client is open; it leaves display blanking available. The first apply also sets Fish as the login
shell, enables SSH, Mosh, and Eternal Terminal, and adds the account to the `docker` and `gamemode` groups. Log out and
back in for the group, shell, and newly installed GNOME extension changes.

The Antec Flux Pro display needs a [separate community driver](scripts/fedora/flux-pro/setup.sh). Review its
[sensor configuration](scripts/fedora/flux-pro/config.conf) for this machine, then install it with:

```bash
bash "$(chezmoi source-path)/scripts/fedora/flux-pro/setup.sh"
```

Sign in to Insync and select the Google Drive folders to sync. Sign in to Steam and enable Steam Play in its
Compatibility settings for Windows games. GameMode, MangoHud, and Gamescope are installed; add their launch options per
game.

For iMessage on Fedora, [BlueBubbles](https://bluebubbles.app/install/) needs its server running on an awake Mac signed
in to Messages. Complete the server's Full Disk Access, notification, and connection setup on the Mac, then connect the
Fedora app. GNOME starts the client at login and hides it in the top bar after the tray appears; closing its window
keeps it running. Leave BlueBubbles' own startup option off to avoid a second instance. The optional Private API
requires a separate macOS setup.

For graphical access to the Mac mini on the local network, enable macOS
[Screen Sharing](https://support.apple.com/guide/mac-help/mh11848/mac) and open `vnc://Bernats-Mac-mini.local:5900` in
[GNOME Connections](https://apps.gnome.org/Connections/). Sign in with the Mac account. GNOME Connections is installed
from Fedora's RPM repository.

### macOS

The [Brewfile](dot_Brewfile.tmpl) installs CLI tools, apps, fonts, and Mac App Store entries. Chezmoi also applies duti
file associations and Stream Deck profiles; it configures the opener socket LaunchAgent where needed. Docker Desktop is
installed separately because its cask asks for sudo on updates.

## Software

The manifests above are the install sources. These links cover the desktop apps and frequently used CLI tools.

### Desktop apps

- **Terminal:** [Ghostty](https://ghostty.org/) on both systems.
- **AI desktop:** [ChatGPT and Codex](https://learn.chatgpt.com/docs/app) on Fedora.
- **Messages:** [BlueBubbles](https://bluebubbles.app/) on Fedora, relayed through a Mac.
- **Remote desktop:** [GNOME Connections](https://apps.gnome.org/Connections/) on Fedora for access to the Mac mini.
- **Editors:** [VS Code](https://code.visualstudio.com/) and [JetBrains Toolbox](https://www.jetbrains.com/toolbox-app/)
  on both systems.
- **Containers:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) on macOS;
  [Moby Engine](https://mobyproject.org/) and [Distrobox](https://distrobox.it/) on Fedora.
- **Drive sync:** [Google Drive](https://www.google.com/drive/) on macOS; [Insync](https://www.insynchq.com/linux) on
  Fedora.
- **Video:** [IINA](https://iina.io/) on macOS; [Celluloid](https://celluloid-player.github.io/) on Fedora.
- **Screen recording:** [Gifox](https://gifox.io/) on macOS; [Kooha](https://github.com/SeaDve/Kooha) and
  [OBS Studio](https://obsproject.com/) on Fedora.
- **Stream Deck:** [Elgato Stream Deck](https://www.elgato.com/us/en/s/stream-deck) on macOS;
  [StreamController](https://github.com/StreamController/StreamController) on Fedora with
  [World Clocks](https://github.com/larkum/StreamController-WorldClocks) and
  [AMD GPU Monitor](https://github.com/julaub/StreamController-AMDGPUTop).
- **Logitech devices:** [Logi Options+](https://www.logitech.com/en-us/software/logi-options-plus.html) on macOS;
  [Solaar](https://pwr-solaar.github.io/Solaar/) on Fedora.
- **External displays:** [BetterDisplay](https://betterdisplay.pro/) on macOS; [ddcutil](https://www.ddcutil.com/) on
  Fedora.

The macOS Brewfile also installs [BetterCmdTab](https://bettercmdtab.app/), [Discord](https://discord.com/),
[Element](https://element.io/), [Insta360 Link Controller](https://www.insta360.com/),
[LaunchControl](https://www.soma-zone.com/LaunchControl/), [Legcord](https://github.com/Legcord/Legcord),
[Path Finder](https://www.cocoatech.io/), [RØDE Central](https://rode.com/en-us/apps/RODE-central),
[Simple Comic](https://github.com/MaddTheSane/Simple-Comic),
[Keystroke Pro](https://appahead.studio/apps/keystroke-pro/), and [Magnet](https://magnet.crowdcafe.com/).

Both systems use [JetBrains Mono](https://www.jetbrains.com/lp/mono/) fonts.

Fedora adds [Astra Monitor](https://github.com/AstraExt/astra-monitor),
[Dash to Panel](https://github.com/home-sweet-gnome/dash-to-panel),
[Copyous](https://extensions.gnome.org/extension/8834/copyous/), [LocalSend](https://localsend.org/),
[Gradia](https://apps.gnome.org/Gradia/), [Bazecor](https://github.com/Dygmalab/Bazecor),
[OpenRGB](https://openrgb.org/), and [xremap](https://github.com/xremap/xremap). Gaming uses
[Steam](https://store.steampowered.com/about/), [GameMode](https://github.com/FeralInteractive/gamemode),
[MangoHud](https://github.com/flightlessmango/MangoHud), [Gamescope](https://github.com/ValveSoftware/gamescope), and
[ProtonPlus](https://github.com/Vysp3r/ProtonPlus).

### Command-line tools

**Shell and prompt** — [Fish](https://fishshell.com/) · [fisher](https://github.com/jorgebucaran/fisher) ·
[Atuin](https://atuin.sh/) · [zoxide](https://github.com/ajeetdsouza/zoxide) · [direnv](https://direnv.net/) ·
[mise](https://mise.jdx.dev/)

**Git** — [Git](https://git-scm.com/) · [GitHub CLI](https://cli.github.com/) · [tig](https://jonas.github.io/tig/) ·
[delta](https://dandavison.github.io/delta/) · [Git LFS](https://git-lfs.com/)

**Files and search** — [ripgrep](https://github.com/BurntSushi/ripgrep) · [fd](https://github.com/sharkdp/fd) ·
[fzf](https://github.com/junegunn/fzf) · [bat](https://github.com/sharkdp/bat) · [lsd](https://github.com/lsd-rs/lsd) ·
[glow](https://github.com/charmbracelet/glow) · [gdu](https://github.com/dundee/gdu)

**Languages and build** — [rustup](https://rust-lang.github.io/rustup/) ·
[GNU Parallel](https://www.gnu.org/software/parallel/) · [uv](https://docs.astral.sh/uv/) ·
[ruff](https://docs.astral.sh/ruff/) · [ty](https://github.com/astral-sh/ty) · [tox](https://tox.wiki/) ·
[prek](https://github.com/j178/prek)

**Packages** — [Homebrew](https://brew.sh/) · [DNF](https://dnf5.readthedocs.io/) · [Flatpak](https://flatpak.org/) ·
[Cargo](https://doc.rust-lang.org/cargo/)

**Editors and multiplexers** — [Neovim](https://neovim.io/) · [tmux](https://github.com/tmux/tmux/wiki) ·
[mprocs](https://github.com/pvolok/mprocs)

**Data** — [jq](https://jqlang.github.io/jq/) · [yq](https://mikefarah.gitbook.io/yq/)

**Remote access** — [OpenSSH](https://www.openssh.com/) · [Mosh](https://mosh.org/) ·
[Eternal Terminal](https://eternalterminal.dev/)

**Cloud** — [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)

**macOS integration** — [duti](https://github.com/moretension/duti) · [mas](https://github.com/mas-cli/mas)

**AI** — [Claude Code](https://docs.claude.com/en/docs/claude-code) ·
[ccstatusline](https://github.com/sirmalloc/ccstatusline) · [Codex](https://github.com/openai/codex) ·
[OpenCode](https://opencode.ai/)

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
