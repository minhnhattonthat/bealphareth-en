-- flag_probe.lua: log game mode flags (0x80177CA8, 0x80062E60 reads it) on change and the map id; RAM dump on demand.
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
local function r32(a) return ffi.cast("uint32_t*", mem + (a & 0x1FFFFF))[0] end
local function r16(a) return ffi.cast("uint16_t*", mem + (a & 0x1FFFFF))[0] end
local last_f, last_m = -1, -1
local last_p, last_l = -1, -1
L.on_frame(function(n)
  local c, l = r16(0x800A1810), r32(0x800A1814)
  if c ~= last_p or l ~= last_l then
    L.log(string.format("f%d party count=%d leader=%08x", n, c, l))
    last_p, last_l = c, l
  end
  local f, m = r32(0x80177CA8), r16(0x80177D70)
  if f ~= last_f or m ~= last_m then
    local p = r32(0x800A15EC)
    L.log(string.format("f%d map=%d flags=%08x pad=%04x cur=%04x,%04x,%04x req=%08x %04x %04x %04x %04x %04x", n, m, f,
      r16(0x800A1550), r16(0x80177D68), r16(0x80177D6A), r16(0x80177D6C), p,
      r16(p), r16(p + 2), r16(p + 0xC), r16(p + 0xE), r16(p + 0x10)))
    last_f, last_m = f, m
  end
end)
