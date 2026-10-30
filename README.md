# Dotfiles

Personal dotfiles for macOS and Fedora Workstation, managed with [chezmoi](https://www.chezmoi.io/). Other Linux systems
get a smaller [apt](https://wiki.debian.org/Apt)-based CLI setup.

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

Replace the example path if needed. `chezmoi init` records the checkout's absolute path as `sourceDir` in
`~/.config/chezmoi/chezmoi.toml`, and the config template retains it when you run `chezmoi update --init`. Keep the
checkout on the branch you want to pull. Without `--source`, chezmoi uses `~/.local/share/chezmoi`, whatever the shell's
working directory.

## Software

The [Brewfile](dot_Brewfile), [RPM manifest](dot_dnf_packages.txt), and [apt manifest](dot_apt_packages.txt) are the
install sources. These links cover the desktop apps and frequently used CLI tools.

### Desktop apps

- **Terminal:** [Ghostty](https://ghostty.org/) on both systems.
- **AI desktop:** [Claude](https://claude.com/download) on both systems;
  [ChatGPT and Codex](https://learn.chatgpt.com/docs/app) on Fedora.
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

**Packages** — `Homebrew` · [DNF](https://dnf5.readthedocs.io/) · [Flatpak](https://flatpak.org/) ·
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
[Copilot CLI](https://docs.github.com/en/copilot/get-started/cli-quickstart) · [OpenCode](https://opencode.ai/)

### Forks

Forks made for this setup:

- [gaborbernat/ghostty](https://github.com/gaborbernat/ghostty): the `feat/gtk-undo-upstream` branch is the source of
  [PR #14653](https://github.com/ghostty-org/ghostty/pull/14653) and of `scripts/fedora/ghostty-undo.diff`.
- [gaborbernat/TuxTalk](https://github.com/gaborbernat/TuxTalk): its GNOME Shell extension draws the recording indicator
  at the monitor's own scale, next to the focused window. It runs from a local checkout; the dotfiles still install the
  upstream RPM.

## Platforms

| Area     | macOS                    | Fedora Workstation             | Other apt-based Linux |
| -------- | ------------------------ | ------------------------------ | --------------------- |
| Packages | `Homebrew` and App Store | `DNF`, `Flatpak`, vendor tools | `apt` CLI tools       |
| Desktop  | `duti` and LaunchAgent   | GNOME and keyboard setup       | Shared shell config   |
| Hardware | Stream Deck profiles     | Peripheral tools               | None                  |

Shared configuration includes `Fish`, `Ghostty`, `Git`, `Atuin`, `mise`, `uv` tools, `Cargo` tools, and the
`~/.agents/skills` store linked into `Codex` and `Claude Code`. The `u` Fish function updates the installed toolchains
and package managers; its stages depend on the host OS.

## Fedora

### Packages and repositories

`chezmoi` enables the `xremap` and `mise` [COPRs](https://copr.fedorainfracloud.org/), the `VS Code` and `Insync` RPM
repositories, and Fedora Workstation's `Steam` repository before installing the [RPM manifest](dot_dnf_packages.txt).
Fedora's `Moby` packages provide `Docker`, and `Distrobox` uses that daemon. Membership in the `docker` group grants
[root-level access](https://docs.docker.com/engine/install/linux-postinstall/).

[ChatGPT's Linux app](https://learn.chatgpt.com/docs/linux/linux-app) includes `Codex`. Its official Fedora RPM adds
OpenAI's signed DNF repository, so `u` updates it with the other RPMs.
[Claude Desktop](https://support.claude.com/en/articles/10065433-install-claude-desktop) runs in a Debian `Distrobox`
because Anthropic publishes an apt package but no Fedora RPM. The app appears in GNOME; `u` updates its apt package
through `distrobox-upgrade`. `Copilot CLI` installs through [npm](https://www.npmjs.com/) and updates with the `npm`
stage.

`Kooha`, `LocalSend`, `Gradia`, `ProtonPlus`, and `BlueBubbles` install as system Flatpaks. `StreamController` comes
from [Flathub](https://flathub.org/) and uses its OS, media, clock, and AMD GPU plugins for the Stream Deck. `Copyous`
comes from the GNOME Extensions release compatible with the running Shell. `Bazecor` uses a pinned upstream
[AppImage](https://appimage.org/) and checksum; `JetBrains Toolbox` verifies the vendor's checksum for the current
release. `uv` uses its [standalone installer](https://docs.astral.sh/uv/getting-started/installation/) so
`uv self update` works.

### Updates

On Fedora, `u` also updates [LVFS firmware](https://fwupd.org/), the installed `Astra Monitor`, `Copyous`, and
[DDC brightness](https://github.com/daitj/gnome-display-brightness-ddcutil) extensions, the latest stable `Bazecor`
`AppImage`, `StreamController` plugins, global `mise` tools, and existing `Distrobox` containers. Project `mise` files
are outside that upgrade. `Docker` image updates keep local images, stopped containers, and volumes intact.

`u` builds `Ghostty` from the latest upstream `main` source with the closed-tab restore patch from
[PR #14653](https://github.com/ghostty-org/ghostty/pull/14653). When that PR merges, the update uses upstream without
the patch. `Dash to Panel` stays pinned to the patched `chezmoi` install.

### GNOME desktop

GNOME uses `Dash to Panel` for a top taskbar on each monitor. Until Fedora's RPM supports indicator mirroring, `chezmoi`
installs [the upstream change](https://github.com/home-sweet-gnome/dash-to-panel/pull/2570) as a user extension.
`Astra Monitor`, `Copyous`, and `DDC brightness` then appear on both panels. The patched build also adds "Move to"
entries to a taskbar app's right-click menu, naming each monitor by model and the BenQ pair by position; switching back
to the RPM drops them.

[AppIndicator](https://github.com/ubuntu/gnome-shell-extension-appindicator) also runs as a patched user copy of the RPM
build. Its v66 breaks tray registration for the rest of the session when [vicinae](https://github.com/vicinaehq/vicinae)
publishes its icon before its bus name
([#675](https://github.com/ubuntu/gnome-shell-extension-appindicator/issues/675)), and the copy retires itself once the
patch stops applying.

`xremap` handles selected Super-key application shortcuts; `Ghostty` handles its own. The focused-monitor extension
opens new windows on the focused screen and moves the MX Master pointer to the LG TV once when that mouse becomes
active.

### Stream Deck

The Fedora Stream Deck keeps the macOS emoji keys and adds live clocks, CPU, RAM, and GPU tiles. The Main page links
directly to the Fedora, System, Media, and Emoji pages, which hold app launchers, hardware details, playback, and volume
controls; page links and launchers use installed icon assets. `chezmoi` creates missing pages and leaves later edits
made in `StreamController` intact. The [Unicode input patch](scripts/fedora/streamcontroller-unicode.diff) completes the
key sequence used by OSPlugin's text action for emoji and kaomoji.

`chezmoi` turns off `StreamController`'s store auto-update because it replaces the patched OSPlugin; `u` stages plugin
updates, reapplies the patch, and keeps the installed version if the patch fails. Avoid the app's manual **Update All**
action, which bypasses this check. With auto-update off, the store also stops updating icons and wallpapers.

### Desktop services

The `agent-awake` user service inhibits suspend while a `Codex`, `Claude`, or `ChatGPT` client is open; it leaves
display blanking available.

The `rustdesk-pin-primary` user service keeps [RustDesk](https://rustdesk.com/)'s
[Wayland](https://wayland.freedesktop.org/) screen share on the HDMI dummy plug, or the primary monitor without it, so a
connection while the displays are off or unplugged no longer brings back the screen picker. GNOME refuses screen sharing
while the session is locked.

`chezmoi` installs the [TuxTalk](https://github.com/ronb1964/TuxTalk) release RPM once, after checking its SHA-256
digest, and binds Super+D to toggle dictation; `TuxTalk`'s own updater installs later releases.

### After the first apply

The first apply also sets `Fish` as the login shell, enables SSH, `Mosh`, and `Eternal Terminal`, and adds the account
to the `docker` and `gamemode` groups. Log out and back in for the group, shell, and newly installed GNOME extension
changes. Then sign in to `Insync` and select the Google Drive folders to sync.

### Antec Flux Pro display

The Antec Flux Pro display needs a [separate community driver](scripts/fedora/flux-pro/setup.sh). Review its
[sensor configuration](scripts/fedora/flux-pro/config.conf) for this machine, then install it with:

```bash
bash "$(chezmoi source-path)/scripts/fedora/flux-pro/setup.sh"
```

### Windows VM

A Windows 11 VM for testing Python projects runs in `Docker` through
[dockur/windows](https://github.com/dockur/windows). The first start downloads Windows and installs it unattended. The
[first-logon script](dot_config/windows-vm/oem/setup.ps1) enables long paths and `OpenSSH` with your
`~/.ssh/id_ed25519.pub`, and installs `uv`, Python 3.11 to 3.15, `tox` with [tox-uv](https://github.com/tox-dev/tox-uv),
and `Git`. The VM stays off until something starts it:

```bash
docker compose -f ~/.config/windows-vm/compose.yml up -d    # first install; watch at http://localhost:8006
winvm ssh                                                   # PowerShell over SSH as $USER
```

[`winvm`](dot_local/bin/executable_winvm) lets several agents share the VM: each `winvm up` holds a shared `flock` for
as long as the calling process lives, and `winvm down` stops the VM only when no other lease remains. A stop in progress
holds the lock exclusively, so a concurrent `up` waits for it and then boots the VM again.

Ports listen on localhost only. The Windows password defaults to `admin`; set `WINDOWS_VM_PASSWORD` before the first
start to change it. The first-logon script runs only on that first install, so changes to it need
`docker compose -f ~/.config/windows-vm/compose.yml down -v` to reinstall.

### Gaming

Sign in to `Steam` and enable Steam Play in its Compatibility settings for Windows games. `chezmoi` installs `GameMode`,
`MangoHud`, and `Gamescope`; add their launch options per game.

To play on the LG TV, switch to the `gaming` user: its SteamOS-style
[session](scripts/fedora/gamescope-session/install.sh) from [ChimeraOS](https://github.com/ChimeraOS/gamescope-session)
drives the TV directly while your desktop session keeps running (Ctrl+Alt+F2 returns to it). The first apply creates the
user, the shared `/home/games/steam` library, and the login-screen avatars and monitor layout; set its password with
`sudo passwd gaming`.

`Steam` keeps a library list per account, so start and quit it once as each user, then rerun the installer to register
the shared library for both. The installer also makes each user's built-in Steam library read-only, so an install aimed
there fails with a disk write error; pick `/home/games/steam` instead.

Quit desktop `Steam` before switching, since it keeps the controller open. In the gaming session, turn on Bluetooth
under Steam's settings, or `Steam` powers the adapter off for both users. `u` shows new upstream session commits and
installs them after you confirm.

Connecting an Xbox controller runs a [udev trigger](scripts/fedora/steam-tv/steam-tv-trigger) that wakes the TV over
Wake-on-LAN, switches it to HDMI 1 through webOS, and opens Big Picture: in the session on screen if someone is logged
in, otherwise by logging in `gaming` once through GDM's runtime config. The trigger ignores a controller reconnecting
mid-game. Enable Turn on via Wi-Fi on the TV, and accept the pairing prompt it shows on the first connect.

On the desktop, `order-monitors` makes the left BenQ primary while it is connected and the TV otherwise, so Big Picture
and games open on the TV when the desk screens are off. An unknown display keeps its place, but the primary rule still
applies. GNOME ignores gamepad input, so the desktop wakes the screens and holds off blanking until the last Xbox
controller disconnects.

### iMessage

For iMessage on Fedora, `BlueBubbles` needs its [server](https://bluebubbles.app/install/) running on an awake Mac
signed in to Messages. Complete the server's Full Disk Access, notification, and connection setup on the Mac, then
connect the Fedora app. GNOME starts the client at login and hides it in the top bar after the tray appears; closing its
window keeps it running. Leave the app's own startup option off to avoid a second instance. The optional Private API
requires a separate macOS setup.

### Mac mini screen sharing

For graphical access to the Mac mini on the local network, enable macOS
[Screen Sharing](https://support.apple.com/guide/mac-help/mh11848/mac) and open `vnc://Bernats-Mac-mini.local:5900` in
`GNOME Connections`, which comes from Fedora's RPM repository. Sign in with the Mac account.

## macOS

The [Brewfile](dot_Brewfile) installs CLI tools, apps, fonts, and Mac App Store entries. `chezmoi` also applies `duti`
file associations and Stream Deck profiles, and on the Mac mini it loads the opener socket LaunchAgent. Install
`Docker Desktop` from its DMG instead, because its cask asks for sudo on updates.

## Updating

```bash
chezmoi status
chezmoi update
```

`chezmoi update` pulls the configured source checkout and applies it. A separate `chezmoi apply` is only needed after
local edits or a partial apply. `--init` reloads the chezmoi config template; it does not create a missing source
checkout. Run `u` for package and tool updates.

## Local configuration

Run `gh auth login` for GitHub operations. `Fish` reads `~/.secrets` when it exists; chezmoi creates that file once and
keeps its contents out of the repo. `maintainer` needs `GITHUB_TOKEN`, while `git-tidy` skips PR checks without it.

Optional machine-local files live in `~/.local/share/chezmoi-private`. Public scripts read them directly:

| File                           | Use                                           |
| ------------------------------ | --------------------------------------------- |
| `Brewfile` and `Brewfile.skip` | Add or omit `Homebrew` entries on one machine |
| `fish_work.fish`               | Work-specific `Fish` settings                 |
| `gitconfig_work`               | Work `Git` identity and settings              |
| `uv_tools_work.txt`            | Private `uv` tools                            |
| `codex_work.toml`              | Private `Codex` config                        |
| `ai_instructions_work.md`      | Private agent instructions                    |

## Source layout

| Path                                               | Use                                |
| -------------------------------------------------- | ---------------------------------- |
| `dot_Brewfile`                                     | macOS packages                     |
| `dot_dnf_packages.txt`                             | Fedora RPMs                        |
| `dot_apt_packages.txt`                             | apt CLI tools                      |
| `dot_config/`                                      | Shell, terminal, and user services |
| `dot_agents/`, `dot_codex/`, `private_dot_claude/` | Agent configuration                |
| `dot_local/`                                       | CLI wrappers and their source      |
| `scripts/fedora/`                                  | Fedora system and hardware setup   |
| `run_once_*`, `run_onchange_*`, `run_after_*`      | Setup scripts                      |
