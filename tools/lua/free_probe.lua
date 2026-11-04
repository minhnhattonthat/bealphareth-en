-- free_probe.lua: trap for RAM the build treats as free (insert.SUB_POOL_RAM): logs the first frame anything writes it.
local ffi = require("ffi")
local words = ffi.cast("uint32_t*", PCSX.getMemPtr() + 0x17EA00)
local hit = false
L.on_frame(function(n)
  if hit or n % 30 ~= 0 then return end
  for i = 0, 0x9600 / 4 - 1 do
    if words[i] ~= 0 then
      hit = true
      L.log(string.format("free RAM written f%d at %08x", n, 0x8017EA00 + i * 4))
      return
    end
  end
end)
