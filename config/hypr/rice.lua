-- Sourceable theme and bindings for the Hyprland 0.55+ Lua API.
-- The returned function accepts { config_root = "/path", autostart = true }.
return function(options)
    options = options or {}
    local root = options.config_root or os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")
    local function quote(value)
        return "'" .. value:gsub("'", "'\\''") .. "'"
    end
    local function shell_command(action)
        -- Pass arguments to the selected executable rather than interpolate them into a shell command.
        local command = "if command -v qs >/dev/null 2>&1; then exec qs \"$@\"; else exec quickshell \"$@\"; fi"
        return "env XDG_CONFIG_HOME=" .. quote(root) .. " sh -c " .. quote(command) .. " spidey -c spidey " .. (action or "--no-duplicate")
    end
    local function desktop_action(name)
        return "env XDG_CONFIG_HOME=" .. quote(root) .. " python3 "
            .. quote(root .. "/quickshell/spidey/scripts/system.py") .. " action " .. quote(name)
    end

    hl.config({
        general = {
            gaps_in = 5,
            gaps_out = 12,
            border_size = 3,
            col = { active_border = "rgba(49c7f4ff)", inactive_border = "rgba(122743ff)" },
            resize_on_border = true,
            allow_tearing = false,
            layout = "dwindle",
        },
        decoration = {
            rounding = 0,
            active_opacity = 1.0,
            inactive_opacity = 1.0,
            shadow = { enabled = false, range = 12, render_power = 3, color = "rgba(00000066)" },
            blur = { enabled = false },
        },
        animations = { enabled = true },
        dwindle = { preserve_split = true },
        misc = { disable_hyprland_logo = true, force_default_wallpaper = 0 },
    })
    hl.curve("spidey", { type = "bezier", points = { {0.2, 0.8}, {0.2, 1.0} } })
    hl.animation({ leaf = "windows", enabled = true, speed = 3, bezier = "spidey", style = "slide" })
    hl.animation({ leaf = "workspaces", enabled = true, speed = 3, bezier = "spidey", style = "slide" })
    hl.animation({ leaf = "fade", enabled = true, speed = 2, bezier = "default" })

    if options.autostart ~= false then
        hl.on("hyprland.start", function()
            hl.exec_cmd(shell_command())
        end)
    end

    hl.bind("SUPER + RETURN", hl.dsp.exec_cmd(desktop_action("terminal")))
    hl.bind("SUPER + D", hl.dsp.exec_cmd(shell_command("ipc call dashboard toggle")))
    hl.bind("SUPER + SPACE", hl.dsp.exec_cmd(desktop_action("launcher")))
    hl.bind("SUPER + E", hl.dsp.exec_cmd(desktop_action("files")))
    hl.bind("SUPER + Q", hl.dsp.window.close())
    hl.bind("SUPER + F", hl.dsp.window.fullscreen())
    hl.bind("SUPER + V", hl.dsp.window.float({ action = "toggle" }))
    hl.bind("SUPER + L", hl.dsp.exec_cmd(desktop_action("lock")))
    hl.bind("SUPER + SHIFT + R", hl.dsp.exec_cmd("hyprctl reload"))
    hl.bind("PRINT", hl.dsp.exec_cmd("region=$(slurp) && grim -g \"$region\" - | wl-copy"))
    for _, direction in ipairs({"left", "right", "up", "down"}) do
        hl.bind("SUPER + " .. direction, hl.dsp.focus({ direction = direction }))
        hl.bind("SUPER + SHIFT + " .. direction, hl.dsp.window.move({ direction = direction }))
    end
    for workspace = 1, 10 do
        local key = workspace % 10
        hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = workspace }))
        hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = workspace }))
    end
    hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })
    hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true })
    hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
    hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true })
    hl.bind("XF86AudioMute", hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true })
    hl.bind("XF86MonBrightnessUp", hl.dsp.exec_cmd("brightnessctl set +5%"), { locked = true, repeating = true })
    hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl set 5%-"), { locked = true, repeating = true })
    hl.bind("XF86AudioPlay", hl.dsp.exec_cmd(desktop_action("media-play-pause")), { locked = true })
    hl.bind("XF86AudioNext", hl.dsp.exec_cmd(desktop_action("media-next")), { locked = true })
    hl.bind("XF86AudioPrev", hl.dsp.exec_cmd(desktop_action("media-previous")), { locked = true })
end
