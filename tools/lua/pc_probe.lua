-- pc_probe.lua: what a frozen scene is doing: pc and ra every 200 frames from --var PC_FROM=N, 40 samples.
L.on_frame(function(n)
  if n >= (PC_FROM or 7000) and n < (PC_FROM or 7000) + 8000 and n % 200 == 0 then
    local r = PCSX.getRegisters()
    L.log(string.format("f%d pc=%08x ra=%08x sp=%08x v0=%08x a0=%08x", n, r.pc, r.GPR.n.ra, r.GPR.n.sp, r.GPR.n.v0, r.GPR.n.a0))
  end
end)
