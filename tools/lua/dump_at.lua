-- Dump PS1 RAM and VRAM at the frames in DUMP_FRAMES (a Lua table), to <out>/ram_<frame>.bin and <out>/v<frame>.vram.bin.
--   emu.py ... --script tools/lua/dump_at.lua --var "DUMP_FRAMES={7000,8000}"
local want = {}
for _, f in ipairs(DUMP_FRAMES or {}) do want[f] = true end
L.on_frame(function(f)
  if want[f] then
    L.dump_ram(string.format("ram_%06d.bin", f))
    L.dump_ppu(string.format("v%06d", f))
    L.shot(string.format("d%06d.png", f))
  end
end)
