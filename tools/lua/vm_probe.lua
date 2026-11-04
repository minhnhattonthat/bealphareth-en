-- vm_probe.lua: --debugger, --var VM=0x80137718 (the `lbu v1,(v0)` of a scene's event VM): each op it reads, bytes and offset.
-- Scene VMs live in the overlay, so the address differs per sub. Logs up to --var MAX_OPS (default 400) ops.
local mem = PCSX.getMemPtr()
local count = 0
L.on_exec(VM, function()
  if count >= (MAX_OPS or 400) then return end
  count = count + 1
  local r = PCSX.getRegisters().GPR.n
  local p = r.v0 & 0x1FFFFF
  local t = {}
  for i = 0, 7 do t[#t + 1] = string.format("%02x", mem[p + i]) end
  L.log(string.format("f%d op s2=%08x ptr=%08x %s", L.frame, r.s2, r.v0, table.concat(t, " ")))
end)
