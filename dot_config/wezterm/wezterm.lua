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

config.unix_domains = { { name = "unix" } }
config.default_gui_startup_args = { "connect", "unix" }

config.hyperlink_rules = wezterm.default_hyperlink_rules()
config.inactive_pane_hsb = { saturation = 0.8, brightness = 0.7 }
config.audible_bell = "Disabled"
config.selection_word_boundary = " \t\n{}[]()\"'`,;:@"
config.mouse_bindings = {
    {
        event = { Up = { streak = 1, button = 'Left' } },
        mods = 'NONE',
        action = act.CompleteSelection 'ClipboardAndPrimarySelection',
    },
    {
        event = { Up = { streak = 1, button = 'Left' } },
        mods = 'SUPER',
        action = act.OpenLinkAtMouseCursor,
    },
}
config.harfbuzz_features = { "calt=1", "clig=1", "liga=1" }
config.tab_bar_at_bottom = false
config.show_close_tab_button_in_tabs = false

local function spawn_tab_next_to_current(window, pane)
    local mux_win = window:mux_window()
    local current_tab = mux_win:active_tab()
    local tabs = mux_win:tabs()
    local current_idx = 0
    for i, tab in ipairs(tabs) do
        if tab:tab_id() == current_tab:tab_id() then
            current_idx = i - 1
            break
        end
    end
    local new_tab = mux_win:spawn_tab({})
    if new_tab then
        window:perform_action(act.MoveTab(current_idx + 1), pane)
    end
end

config.disable_default_key_bindings = true
config.keys = {
    { key = "p", mods = "SUPER", action = act.ActivateCommandPalette },
    { key = "t", mods = "SUPER", action = wezterm.action_callback(spawn_tab_next_to_current) },
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
    { key = "LeftArrow", mods = "CTRL|SUPER", action = act.MoveTabRelative(-1) },
    { key = "RightArrow", mods = "CTRL|SUPER", action = act.MoveTabRelative(1) },
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

local function get_claude_status_priority(status)
    if not status or #status == 0 then
        return 0
    end
    if status:find("❓") then
        return 4
    end
    if status:find("❗") then
        return 3
    end
    if status:find("🏃") then
        return 2
    end
    return 1
end

local function get_pane_cwd(p)
    local cwd_var = p.user_vars and p.user_vars.cwd
    if cwd_var and #cwd_var > 0 then
        return cwd_var
    end
    local cwd = p.current_working_dir and p.current_working_dir.file_path
    local dir_name = cwd and cwd:gsub(".*/", "")
    local project = get_git_project(cwd)
    if project and project ~= dir_name then
        return project .. "/" .. dir_name
    end
    return dir_name or ""
end

local function get_pane_title(p)
    local cwd = get_pane_cwd(p)
    local claude_status = p.user_vars and p.user_vars.claude_status
    if claude_status and #claude_status > 0 then
        return claude_status .. " " .. cwd, get_claude_status_priority(claude_status)
    end
    local proc = p.foreground_process_name:gsub(".*/", "")
    if p.user_vars and p.user_vars.prog then
        proc = p.user_vars.prog
    end
    if proc == "ssh" or proc == "tsh" then
        local host = p.title:match("[%w%-]+%-%w+%-%d+") or p.title:match("@([%w%-%.]+)") or p.title:match("([%w%-%.]+)$")
        if host then
            return proc .. ": " .. host, 0
        end
    end
    if proc ~= "" and proc ~= "fish" then
        return proc .. ": " .. cwd, 0
    end
    return cwd, 0
end

wezterm.on("format-tab-title", function(tab, tabs, panes, cfg, hover, max_width)
    local index = tab.tab_index + 1

    if tab.tab_title and #tab.tab_title > 0 then
        return { { Text = " " .. index .. ": " .. tab.tab_title .. " " } }
    end

    local pane_infos = {}
    for _, p in ipairs(tab.panes or {}) do
        local title, priority = get_pane_title(p)
        table.insert(pane_infos, { title = title, priority = priority, is_active = p.pane_id == tab.active_pane.pane_id })
    end

    table.sort(pane_infos, function(a, b)
        if a.priority ~= b.priority then
            return a.priority > b.priority
        end
        if a.is_active ~= b.is_active then
            return a.is_active
        end
        return false
    end)

    local parts = {}
    for _, info in ipairs(pane_infos) do
        table.insert(parts, info.title)
    end
    local title = table.concat(parts, " | ")
    return { { Text = " " .. index .. ": " .. title .. " " } }
end)

wezterm.on("open-uri", function(window, pane, uri)
    if uri:sub(1, 7) == "file://" then
        local path = uri:sub(8):gsub("%%(%x%x)", function(hex)
            return string.char(tonumber(hex, 16))
        end)
        local f = io.open(path, "r")
        if f then
            f:close()
        else
            window:toast_notification("wezterm", "File not found: " .. path, nil, 4000)
            return false
        end
    end
end)

wezterm.on("bell", function(window, pane)
    local tab = pane:tab()
    if tab and tab:active_pane():pane_id() ~= pane:pane_id() then
        window:toast_notification("wezterm", "Command finished in background pane", nil, 3000)
    elseif not window:is_focused() then
        local title = pane:get_title()
        window:toast_notification("wezterm", "Command finished: " .. title, nil, 3000)
    end
end)

wezterm.on("update-right-status", function(window, pane)
    window:set_right_status(wezterm.format({
        { Attribute = { Italic = true } },
        { Text = wezterm.strftime("%Y-%m-%d %H:%M:%S") },
    }))
end)

return config
