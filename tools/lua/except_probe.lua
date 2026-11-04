-- except_probe.lua: full registers at a CPU exception, and optional call logs. --var "EXEC={0x8002B458}" logs a0-a3,ra at
-- each address. Needs emu.py --debugger.
local names = { "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "s0", "s1", "s2",
  "s3", "s4", "s5", "s6", "s7", "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra" }
PAUSE_E = PCSX.Events.createEventListener("ExecutionFlow::Pause", function(e)
  if not (e and e.exception) then return end
  local r = PCSX.getRegisters()
  local s = {}
  for _, n in ipairs(names) do s[#s + 1] = string.format("%s=%08x", n, r.GPR.n[n]) end
  L.log(string.format("EXC f%d pc=%08x %s", L.frame, r.pc, table.concat(s, " ")))
end)
for _, a in ipairs(EXEC or {}) do
  L.on_exec(a, function()
    local r = PCSX.getRegisters()
    L.log(string.format("f%d @%08x a0=%08x a1=%08x a2=%08x a3=%08x ra=%08x", L.frame, a, r.GPR.n.a0, r.GPR.n.a1, r.GPR.n.a2,
      r.GPR.n.a3, r.GPR.n.ra))
  end)
end
