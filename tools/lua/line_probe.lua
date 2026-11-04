-- line_probe.lua: --debugger. When 0x80019A24 runs, the first writes over the sub-scene line at 0x80156C00, and the first reads of each
-- pc in --var LO..HI: who reads a sub-scene's data past that line, and whether the load comes first.
L.on_exec(0x80019A24, function() L.log(string.format("f%d 0x80019A24 ra=%08x", L.frame, PCSX.getRegisters().GPR.n.ra)) end)
L.on_exec(0x80019860, function()
  local r = PCSX.getRegisters()
  L.log(string.format("f%d load file=%d to=%08x ra=%08x", L.frame, r.GPR.n.a0, r.GPR.n.a1, r.GPR.n.ra))
end)
local writes = 0
L.on_write(0x80156C00, 0x80156C03, function()
  if writes < 8 then writes = writes + 1; L.log(string.format("f%d write line pc=%08x", L.frame, PCSX.getRegisters().pc)) end
end)
local seen, count = {}, 0
L.on_read(LO, HI, function(addr)
  local r = PCSX.getRegisters()
  if not seen[r.pc] and count < 40 then
    seen[r.pc] = true
    count = count + 1
    L.log(string.format("f%d read %08x pc=%08x ra=%08x a0=%08x a1=%08x", L.frame, addr, r.pc, r.GPR.n.ra, r.GPR.n.a0, r.GPR.n.a1))
  end
end)
