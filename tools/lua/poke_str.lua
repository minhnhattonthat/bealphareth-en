-- poke_str.lua: every frame, overwrite a string in RAM once its old text is there. A label's width test without a rebuild.
--   --var POKE_AT=0x80012345 --var "POKE_OLD='Flip Panel 1'" --var "POKE_NEW='Flip Panel 123'"
local mem = PCSX.getMemPtr()
local at = POKE_AT & 0x1FFFFF
L.on_frame(function()
  for i = 1, #POKE_OLD do
    if mem[at + i - 1] ~= POKE_OLD:byte(i) then return end
  end
  for i = 1, #POKE_NEW do mem[at + i - 1] = POKE_NEW:byte(i) end
  mem[at + #POKE_NEW] = 0
  L.log("poked")
end)
