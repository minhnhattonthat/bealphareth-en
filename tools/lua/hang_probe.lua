-- hang_probe.lua: a run that stops making frames: pc, ra and a shot, every N frames from --var HANG_FROM=F (--var HANG_EVERY=N).
L.on_frame(function(n)
  if n >= (HANG_FROM or 0) and n % (HANG_EVERY or 10) == 0 then
    local r = PCSX.getRegisters()
    L.log(string.format("f%d pc=%08x ra=%08x sp=%08x v0=%08x", n, r.pc, r.GPR.n.ra, r.GPR.n.sp, r.GPR.n.v0))
    L.shot(string.format("h%06d.png", n))
  end
end)
