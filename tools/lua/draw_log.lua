-- draw_log.lua: with --debugger, log every 0x8004EB94(text) call: caller and the string's first bytes.
-- Finds which code draws a label, so its fixed x can be read off the caller.
local mem = PCSX.getMemPtr()
local seen = {}
L.on_exec(0x8004EB94, function()
  local r = PCSX.getRegisters().GPR.n
  local p = r.a0 & 0x1FFFFF
  local t = {}
  for i = 0, 15 do
    local c = mem[p + i]
    if c == 0 then break end
    t[#t + 1] = (c >= 0x20 and c < 0x7F) and string.char(c) or string.format("{%02x}", c)
  end
  local key = string.format("%08x %s", r.ra, table.concat(t))
  if not seen[key] then
    seen[key] = true
    L.log(string.format("f%d ra=%08x text=%08x %s", L.frame, r.ra, r.a0, table.concat(t)))
  end
end)
