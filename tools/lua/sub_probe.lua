-- sub_probe.lua: frame log around a forced sub-scene load (globals FROM, TO): B callback, load id, map, top of B slot.
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
local function r32(a) return ffi.cast("uint32_t*", mem + (a & 0x1FFFFF))[0] end
local function r16(a) return ffi.cast("int16_t*", mem + (a & 0x1FFFFF))[0] end
L.on_frame(function(n)
  if n >= (FROM or 0) and n <= (TO or 1e9) and n % (EVERY or 2) == 0 then
    local r = PCSX.getRegisters()
    L.log(string.format("f%d pc=%08x ra=%08x cbA=%08x cbB=%08x id9e=%d map=%d B0=%08x B10=%08x flags=%08x",
      n, r.pc, r.GPR.n.ra, r32(0x800A15A8), r32(0x800A15A0), r16(0x800A0EC2), r16(0x80177D70), r32(0x80136C00),
      r32(0x80136C10), r32(0x800A0E24 + 0x978)))
  end
end)
