-- debug_on.lua: turn on the game's leftover debug mode (0x1C2(gp) = 0x800A0FE6). R2+Cross on the field opens its menu.
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
L.on_frame(function(n) ffi.cast("uint16_t*", mem + 0xA0FE6)[0] = 1 end)
