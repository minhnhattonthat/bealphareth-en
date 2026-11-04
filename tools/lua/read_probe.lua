-- read_probe.lua: --debugger, --var LO=0x.. --var HI=0x..: the first distinct pcs that read a RAM range, with the address read.
local seen, count = {}, 0
L.on_read(LO, HI, function(addr)
  local r = PCSX.getRegisters()
  local key = r.pc
  if not seen[key] and count < 60 then
    seen[key] = true
    count = count + 1
    L.log(string.format("f%d read %08x pc=%08x ra=%08x a0=%08x a1=%08x", L.frame, addr, r.pc, r.GPR.n.ra, r.GPR.n.a0, r.GPR.n.a1))
  end
end)
