-- free_probe.lua: trap for RAM the build treats as free (insert.SUB_POOL_RAM): logs the first frame anything writes it.
-- The warp tour loads no NPC sprites, so a clean tour is not proof alone (the old pool at 0x8017EA00 passed it).
local ffi = require("ffi")
local LO, SIZE = 0x801974C0, 0x3B40
local words = ffi.cast("uint32_t*", PCSX.getMemPtr() + (LO & 0x1FFFFF))
local hit = false
L.on_frame(function(n)
  if hit or n % 30 ~= 0 then return end
  for i = 0, SIZE / 4 - 1 do
    if words[i] ~= 0 then
      hit = true
      L.log(string.format("free RAM written f%d at %08x", n, LO + i * 4))
      return
    end
  end
end)
