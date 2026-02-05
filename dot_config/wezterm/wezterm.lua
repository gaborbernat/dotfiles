local wezterm = require 'wezterm'
local act = wezterm.action
local config = wezterm.config_builder()

config.window_decorations = "RESIZE"
config.color_scheme = "Monokai Remastered"
config.font = wezterm.font_with_fallback({
    "JetBrainsMono Nerd Font",
    "Symbols Nerd Font Mono",
})
config.font_size = 13
config.window_padding = { left = 4, right = 4, top = 4, bottom = 4 }

config.scrollback_lines = 200000
config.enable_scroll_bar = false
config.term = "wezterm"
config.cursor_blink_rate = 500
config.default_cursor_style = "BlinkingBar"
config.use_ime = false
config.default_prog = { "/opt/homebrew/bin/fish" }
config.window_close_confirmation = "AlwaysPrompt"

config.hyperlink_rules = wezterm.default_hyperlink_rules()
config.inactive_pane_hsb = { saturation = 0.8, brightness = 0.7 }
config.audible_bell = "Disabled"
config.selection_word_boundary = " \t\n{}[]()\"'`,;:@"
config.mouse_bindings = {
    {
        event = { Up = { streak = 1, button = 'Left' } },
        mods = 'NONE',
        action = act.CompleteSelectionOrOpenLinkAtMouseCursor 'ClipboardAndPrimarySelection',
    },
}
config.harfbuzz_features = { "calt=1", "clig=1", "liga=1" }
config.tab_bar_at_bottom = true

config.disable_default_key_bindings = true
config.keys = {
    { key = "p", mods = "SUPER", action = act.ActivateCommandPalette },
    { key = "t", mods = "SUPER", action = act.SpawnTab("CurrentPaneDomain") },
    { key = "w", mods = "SUPER", action = act.CloseCurrentTab({ confirm = false }) },
    { key = "n", mods = "SUPER", action = act.SpawnWindow },
    { key = "PageUp", mods = "SUPER", action = act.ActivateTabRelative(-1) },
    { key = "PageDown", mods = "SUPER", action = act.ActivateTabRelative(1) },
    { key = "v", mods = "SUPER", action = act.PasteFrom("Clipboard") },
    { key = "c", mods = "SUPER", action = act.CopyTo("ClipboardAndPrimarySelection") },
    { key = "PageUp", mods = "SHIFT", action = act.ScrollByPage(-1) },
    { key = "PageDown", mods = "SHIFT", action = act.ScrollByPage(1) },
    { key = "UpArrow", mods = "SHIFT", action = act.ScrollByLine(-1) },
    { key = "DownArrow", mods = "SHIFT", action = act.ScrollByLine(1) },
    { key = "h", mods = "SUPER", action = act.SplitHorizontal({ domain = "CurrentPaneDomain" }) },
    { key = "j", mods = "SUPER", action = act.SplitVertical({ domain = "CurrentPaneDomain" }) },
    { key = "LeftArrow", mods = "SUPER", action = act.ActivatePaneDirection("Left") },
    { key = "RightArrow", mods = "SUPER", action = act.ActivatePaneDirection("Right") },
    { key = "UpArrow", mods = "SUPER", action = act.ActivatePaneDirection("Up") },
    { key = "DownArrow", mods = "SUPER", action = act.ActivatePaneDirection("Down") },
    { key = "f", mods = "SUPER", action = act.Search({ CaseInSensitiveString = "" }) },
    { key = "f", mods = "SUPER|SHIFT", action = act.TogglePaneZoomState },
    { key = "s", mods = "SUPER|SHIFT", action = act.PaneSelect },
    { key = "Enter", mods = "SHIFT", action = act.SendString("\x1b\r") },
    { key = "1", mods = "SUPER", action = act.ActivateTab(0) },
    { key = "2", mods = "SUPER", action = act.ActivateTab(1) },
    { key = "3", mods = "SUPER", action = act.ActivateTab(2) },
    { key = "4", mods = "SUPER", action = act.ActivateTab(3) },
    { key = "5", mods = "SUPER", action = act.ActivateTab(4) },
    { key = "6", mods = "SUPER", action = act.ActivateTab(5) },
    { key = "7", mods = "SUPER", action = act.ActivateTab(6) },
    { key = "8", mods = "SUPER", action = act.ActivateTab(7) },
    { key = "9", mods = "SUPER", action = act.ActivateTab(8) },
    { key = "0", mods = "SUPER", action = act.ActivateTab(9) },
    { key = "=", mods = "SUPER", action = act.IncreaseFontSize },
    { key = "-", mods = "SUPER", action = act.DecreaseFontSize },
    { key = "0", mods = "SUPER", action = act.ResetFontSize },
    { key = "Space", mods = "SUPER|SHIFT", action = act.QuickSelect },
    { key = "d", mods = "SUPER", action = act.CloseCurrentPane({ confirm = false }) },
    { key = "m", mods = "SUPER", action = act.PaneSelect { mode = 'MoveToNewWindow' } },
    { key = "UpArrow", mods = "CTRL|SHIFT", action = act.ScrollToPrompt(-1) },
    { key = "DownArrow", mods = "CTRL|SHIFT", action = act.ScrollToPrompt(1) },
    { key = "x", mods = "SUPER|SHIFT", action = act.SelectTextAtMouseCursor("SemanticZone") },
}

local function is_dir(path)
    local f = io.open(path .. "/.")
    if f then
        f:close()
        return true
    end
    return false
end

local function get_git_project(cwd)
    if not cwd then
        return nil
    end
    local path = cwd
    while path and path ~= "/" do
        local git_path = path .. "/.git"
        local f = io.open(git_path, "r")
        if f then
            if is_dir(git_path) then
                f:close()
                return path:match("([^/]+)$")
            end
            local content = f:read("*a")
            f:close()
            if content and content:match("^gitdir:") then
                path = path:match("(.+)/[^/]*$")
            else
                return path:match("([^/]+)$")
            end
        else
            local head = io.open(path .. "/HEAD", "r")
            if head then
                local objects = io.open(path .. "/objects/.")
                if objects then
                    objects:close()
                    head:close()
                    return path:match("([^/]+)$")
                end
                head:close()
            end
            path = path:match("(.+)/[^/]*$")
        end
    end
    return nil
end

wezterm.on("format-tab-title", function(tab, tabs, panes, cfg, hover, max_width)
    local pane = tab.active_pane
    local process = pane.foreground_process_name:gsub(".*/", "")
    local title = pane.title
    local index = tab.tab_index + 1

    if process == "ssh" or process == "tsh" then
        local host = title:match("[%w%-]+%-%w+%-%d+") or title:match("@([%w%-%.]+)") or title:match("([%w%-%.]+)$")
        if host then
            return { { Text = " " .. index .. ": " .. host .. " " } }
        end
    end

    local cwd = pane.current_working_dir and pane.current_working_dir.file_path
    local dir_name = cwd and cwd:gsub(".*/", "")
    local project = get_git_project(cwd)
    if project and project ~= dir_name then
        title = project .. "/" .. dir_name
    elseif dir_name then
        title = dir_name
    end
    if process ~= "" and process ~= "fish" then
        title = process .. ": " .. title
    end
    return { { Text = " " .. index .. ": " .. title .. " " } }
end)

wezterm.on("update-right-status", function(window, pane)
    window:set_right_status(wezterm.format({
        { Attribute = { Italic = true } },
        { Text = wezterm.strftime("%Y-%m-%d %H:%M:%S") },
    }))
end)

return config
