-- OPTIONAL PALETTE FRAGMENT for Ly versions that use /etc/ly/config.lua.
-- Add AFTER your existing `ly = { ... }` block. Do not replace the full file.
-- Verified against fairyglade/ly master; current Arch Ly 1.4.x uses spidey.ini.
-- Session, authentication, and autologin configuration stay in your file.
ly.full_color = true
ly.bg = 0x00081B35
ly.fg = 0x00D8F6EA
ly.border_fg = 0x0046C8F1
ly.error_bg = 0x00081B35
ly.error_fg = 0x01FF887B
ly.box_title = "SPIDEY // ACCESS TERMINAL"
ly.initial_info_text = "IDENTIFY TO ENTER THE NETWORK"
ly.blank_box = true
ly.hide_borders = false
ly.animation = "none"
ly.clock = "%H:%M"
ly.bigclock = "en"
ly.bigclock_seconds = false
ly.margin_box_h = 3
ly.margin_box_v = 1
