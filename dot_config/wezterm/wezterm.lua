local wezterm = require 'wezterm';

local module = {
    font = wezterm.font("JetBrainsMono Nerd Font Mono"),
    color_scheme = "Monokai Remastered",
    scrollback_lines = 35000,
    font_size = 8,
    dpi = 111.0,
    enable_scroll_bar = false,
    term = "xterm-256color",
    cursor_blink_rate = 0,
    default_cursor_style = "SteadyBar",
    use_ime = false,
    disable_default_key_bindings = true,
    keys = {
        {
            mods = "CTRL",
            key = "t",
            action = wezterm.action {SpawnTab = "CurrentPaneDomain"}
        }, {
            mods = "CTRL",
            key = "w",
            action = wezterm.action {CloseCurrentTab = {confirm = false}}
        }, {mods = "SUPER", key = "n", action = "SpawnWindow"}, {
            key = "PageUp",
            mods = "CTRL",
            action = wezterm.action {ActivateTabRelative = -1}
        }, {
            key = "PageDown",
            mods = "CTRL",
            action = wezterm.action {ActivateTabRelative = 1}
        },
        {
            key = "v",
            mods = "SUPER",
            action = wezterm.action {PasteFrom = "Clipboard"}
        }, {
            key = "c",
            mods = "SUPER",
            action = wezterm.action {CopyTo = "ClipboardAndPrimarySelection"}
        },
        {key="PageUp", mods="SHIFT", action=wezterm.action{ScrollByPage=-1}},
        {key="PageDown", mods="SHIFT", action=wezterm.action{ScrollByPage=1}},
        {key="UpArrow", mods="SHIFT", action=wezterm.action{ScrollByLine=-1}},
        {key="DownArrow", mods="SHIFT", action=wezterm.action{ScrollByLine=1}},
    }
};

local platform = {};
if wezterm.target_triple == "x86_64-apple-darwin" then
    platform = require('macOS');
end
for k, v in pairs(platform) do module[k] = v end

return module
