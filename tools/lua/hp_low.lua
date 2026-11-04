-- hp_low.lua: keep the leader's HP (docs/re/warp.md) at 1 so the next hit ends the run: the only way to the Game Over screen.
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
local DIRS = { "up", "right", "down", "left" }
L.on_frame(function(n)
  -- past the warp (f5400): dismiss the mission card, then wander until something hits the leader
  if n > 5400 and n % 120 == 0 and n < (WANDER_UNTIL or 1e9) then
    L.press(n % 240 == 0 and "circle" or DIRS[(n / 120) % 4 + 1], 100)
  end
  local p = ffi.cast("uint32_t*", mem + 0xA1814)[0] & 0x1FFFFF
  if p ~= 0 then
    local hp = ffi.cast("uint16_t*", mem + p + 0x6A)
    if hp[0] > 1 and hp[0] < 10000 then hp[0] = 1 end
  end
end)
