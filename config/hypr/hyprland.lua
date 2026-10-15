-- Starter configuration for Hyprland 0.55+ (Lua).
-- Start explicitly with: Hyprland --config ~/.config/hypr-spidey/hyprland.lua
-- Existing users should load rice.lua from their own config instead; see README.
local config_root = os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.config({
    input = {
        kb_layout = "us", -- Change to "br" for a Brazilian keyboard.
        follow_mouse = 1,
        touchpad = { natural_scroll = true },
    },
})

dofile(config_root .. "/hypr-spidey/rice.lua")({ config_root = config_root })
