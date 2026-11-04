-- write_probe.lua: --debugger, --var LO=0x.. --var HI=0x..: every write to a RAM range: pc, ra, a0-a2, first 80.
local count = 0
L.on_write(LO, HI, function(addr)
  if count < 80 then
    count = count + 1
    local r = PCSX.getRegisters()
    L.log(string.format("f%d write %08x pc=%08x ra=%08x a0=%08x a1=%08x a2=%08x v0=%08x v1=%08x", L.frame, addr, r.pc, r.GPR.n.ra, r.GPR.n.a0, r.GPR.n.a1, r.GPR.n.a2, r.GPR.n.v0, r.GPR.n.v1))
  end
end)
