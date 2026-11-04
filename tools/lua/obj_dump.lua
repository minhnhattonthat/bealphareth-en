-- obj_dump.lua: at frame AT (default 5) log party count, the leader object's first 0x90 bytes, mode flags, and dump RAM.
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
local function r8(a) return mem[a & 0x1FFFFF] end
local function r32(a) return ffi.cast("uint32_t*", mem + (a & 0x1FFFFF))[0] end
L.on_frame(function(n)
  if n == (AT or 5) then
    local p = r32(0x800A1814)
    L.log(string.format("party=%d leader=%08x flags=%08x", r32(0x800A1810) & 0xFFFF, p, r32(0x80177CA8)))
    if p ~= 0 then
      local t = {}
      for i = 0, 0x8F do
        t[#t + 1] = string.format("%02x", r8(p + i))
        if i % 16 == 15 then L.log(table.concat(t, " ")); t = {} end
      end
    end
    L.dump_ram("ram.bin")
  end
end)
