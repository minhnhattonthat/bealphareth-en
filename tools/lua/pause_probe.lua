-- pause_probe.lua: log why the emulator stops producing vsyncs (pause events, last PC and registers each 60 frames).
PAUSE_L = PCSX.Events.createEventListener("ExecutionFlow::Pause", function(e)
  local r = PCSX.getRegisters()
  L.log(string.format("PAUSE f%d exception=%s pc=%08x ra=%08x", L.frame, tostring(e and e.exception), r.pc, r.GPR.n.ra))
end)
L.on_frame(function(n)
  if n % 30 == 0 then
    local r = PCSX.getRegisters()
    L.log(string.format("f%d pc=%08x ra=%08x sp=%08x", n, r.pc, r.GPR.n.ra, r.GPR.n.sp))
  end
end)
