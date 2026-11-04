-- dma_probe.lua: --debugger. Every image DMA to VRAM (libgpu, MADR write at 0x8008B858): source, bytes, a hash of them.
-- Also each write onto the first word of the sub-scene slot: a map's own load passes it, then a sub-scene's.
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
L.on_exec(0x8008B858, function()
  local r = PCSX.getRegisters()
  local src, bytes = r.GPR.n.s5, r.GPR.n.s4
  local p = ffi.cast("uint32_t*", mem + (src & 0x1FFFFC))
  local sum = 0
  for i = 0, bytes / 4 - 1 do sum = (sum * 33 + p[i]) % 4294967291 end
  L.log(string.format("dma f%d src=%08x bytes=%x sum=%010.0f", L.frame, src, bytes, sum))
end)
L.on_write(0x80136C00, 0x80136C03, function()
  L.log(string.format("sub load f%d", L.frame))
end)
