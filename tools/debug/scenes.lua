-- scenes.lua: scene list for warp.lua. name -> { map, sub, entr, base, keys, frames, flags, unflags, debug, hp }.
-- map = MAIN.RES scene overlay id (0xA0000 slot); sub = sub-scene overlay id (0x40000 slot), loaded on top of its parent map.
-- base "field" = play to first control first (75 s, needed for menus); default "opening" (15 s, hero not controllable).
-- keys = route after arrival ("6 start;40 -"). chain = true: the map ends by jumping on, so `map` is proven by the visit.
local S = {}

-- Maps. Mission cards + dungeon, events, endings: all are reached the same way.
local MAPS = {
  1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 32, 34, 35, 36, 38,
  40, 41, 42, 43, 44, 45, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
  90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 140, 160, 168,
  171, 175, 178, 181, 183, 188, 193, 196, 204, 208, 214, 215, 216, 217, 219, 222, 223, 227, 228, 230, 231, 233, 235, 236,
  237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 1023,
}
for _, id in ipairs(MAPS) do S["m" .. id] = { map = id } end
-- 66-112 play a short event and jump on by themselves
for _, id in ipairs({ 66, 74, 75, 78, 79, 82, 88, 89, 90, 96, 98, 102, 103, 228 }) do S["m" .. id].chain = true end
-- #223 is a code-only overlay (2 parts: code + one data blob, no room art): it loads (map id logged) but draws a black
-- screen in every cold entry tried. Keep it in the list with that shot, not as a failure.
S.m223.blank = true

-- Sub-scenes -> parent map. Parent from the map's own code or tables (tools/debug/ov_parents.py); ids of 0x9C bytes are
-- empty stubs and left out (303 307 316 320 325 326 329 330 333 334 337 338 341 342 345 346 349 350 355 356 359 360 570 1732).
local SUBS = {
[300]=5,[301]=6,[302]=42,[304]=219,[305]=178,[306]=183,[308]=42,[309]=42,[310]=42,[311]=42,[312]=140,[313]=183,
[314]=42,[315]=160,[317]=42,[318]=160,[319]=178,[321]=42,[322]=140,[323]=183,[324]=42,[327]=42,[328]=42,[331]=42,
[332]=42,[335]=42,[336]=171,[339]=42,[340]=42,[343]=183,[344]=219,[347]=219,[348]=183,[351]=183,[352]=183,[353]=183,
[354]=219,[357]=178,[358]=183,[361]=171,[362]=4,[363]=183,[364]=140,[555]=183,[556]=183,[557]=183,[558]=183,
[559]=183,[560]=183,[561]=183,[562]=183,[563]=183,[564]=196,[565]=196,[566]=196,[567]=196,[568]=196,[569]=196,
[571]=66,[598]=140,[625]=222,[626]=183,[705]=183,[706]=140,[707]=171,[708]=4,[735]=4,[736]=183,[763]=222,[764]=222,
[791]=183,[792]=183,[871]=222,[872]=4,[873]=140,[874]=140,[875]=140,[928]=183,[955]=140,[1042]=140,[1048]=4,
[1169]=171,[1170]=171,[1171]=171,[1172]=171,[1173]=171,[1174]=171,[1175]=171,[1181]=196,[1188]=183,[1192]=188,
[1193]=140,[1194]=178,[1195]=178,[1196]=178,[1197]=178,[1198]=178,[1199]=181,[1200]=188,[1201]=188,[1202]=188,
[1203]=188,[1256]=140,[1291]=171,[1292]=222,[1332]=183,[1333]=140,[1334]=160,[1370]=178,[1405]=140,[1474]=4,
[1475]=183,[1504]=183,[1573]=183,[1596]=160,[1621]=171,[1648]=105,[1683]=140,[1684]=178,[1733]=222,[1734]=168,
[1838]=4,[1839]=183,[1874]=140,[1944]=43,[1945]=105,[1946]=105,[1947]=105,[1948]=105,[1949]=105,[1950]=105,
[1951]=105,[1952]=105,[1953]=105,[1954]=105,[1955]=105,[1956]=105,[1957]=105,[1958]=105,[1959]=105,[1960]=105,
[1961]=171,[1962]=160,[2034]=188,[4100]=160,[4101]=160,[4102]=160,[4103]=160,[4104]=160,[4105]=160,[4106]=171,
[4107]=171,[4112]=196,[4113]=160,[4114]=160,[4115]=183,[4116]=196,[4117]=171,[4125]=183,[4126]=183,
}
for id, parent in pairs(SUBS) do S["s" .. id] = { map = parent, sub = id } end
-- Forced-load proof is a log line, not a visible room, for these nine: they load (callback non-zero, load id back to
-- 0xFFFF) but draw nothing on their guessed parent, so their final shot is flat. They are event/script overlays whose
-- content only appears inside their event (phase 5 sees them in the marker tour). Tried: parent 42/44/219 renders the
-- parent's own mission card unchanged, so the black is not a wrong parent.
for _, id in ipairs({ 305, 319, 357, 1197, 1198, 1370, 1683, 1684, 2034 }) do S["s" .. id].blank = true end

-- Screens. All from the tavern with the hero in hand; keys open the game's own menus.
local function field(keys, extra)
  local t = extra or {}
  t.map, t.base, t.keys = t.map or 171, "field", keys
  return t
end
S.field_tavern = field("30 -")
-- 120 frames first: the flag warp.lua waits for is up before the field takes input, and an early Start is lost
S.menu_main = field("120 -;6 start;60 -")
S.menu_tabs = field("120 -;6 start;30 -;6 circle;60 -")
S.menu_item = field("120 -;6 start;30 -;6 circle;30 -;6 circle;60 -")
S.menu_status = field("120 -;6 start;30 -;6 circle;30 -;6 right;30 -;6 circle;60 -")
S.menu_help = field("120 -;6 start;30 -;6 circle;30 -;6 right;30 -;6 right;30 -;6 circle;60 -")
S.menu_party = field("120 -;6 start;30 -;6 down;30 -;6 circle;60 -")
S.menu_system = field("120 -;6 start;30 -;6 down;30 -;6 down;30 -;6 down;30 -;6 circle;60 -")
S.menu_controls = field("120 -;6 start;30 -;6 down;30 -;6 down;30 -;6 circle;240 -")
-- Leftover debug menu (Aug 24 2000), R2+Cross with debug on: its screens are English and never shipped text.
local D = "20 r2+cross;40 -;"
S.debug_menu = field(D, { debug = true })
S.debug_save = field(D .. "6 down;25 -;6 down;25 -;6 down;25 -;6 circle;40 -;6 down;25 -;6 down;25 -;6 down;25 -;6 circle;120 -",
  { debug = true })
S.debug_load = field(D .. "6 down;25 -;6 down;25 -;6 down;25 -;6 circle;40 -;6 down;25 -;6 down;25 -;6 down;25 -;6 down;25 -;6 circle;120 -",
  { debug = true })
-- Game over and the credits need a battle wipe / ending run; the field HP write does not trigger the death check
-- (tested: HP 0 on the leader for 40k frames, game stays on the opening map), so they are phase-8 work, not a warp.
-- Pre-game screens, reached by the boot route only.
S.title = { route = "tools/routes/boot.txt", frames = 3800 }

return S
