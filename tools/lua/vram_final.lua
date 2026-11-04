-- vram_final.lua: VRAM near a run's end, to vram.bin in its out dir. tools/debug/vram_compare.py compares two tours' dumps:
-- a texture that differs from the Japanese disc's is a part read after something overwrote it.
L.on_frame(function(n)
  if n == FRAMES - 30 then L.dump_ppu("vram") end
end)
