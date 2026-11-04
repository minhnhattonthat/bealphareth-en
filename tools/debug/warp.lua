-- warp.lua: cold-boot warp using the game's own debug map jump (MAIN.EXE 0x80029838). Notes: docs/re/warp.md.
-- Run with --route tools/routes/newgame.txt and either --var "SCENE='name'" (tools/debug/scenes.lua) or
-- --var MAP=171 [--var SUB=1621] [--var ENTR=0] [--var "FLAGS={0x293}"] [--var "UNFLAGS={0x294}"].
local ffi = require("ffi")
local mem = PCSX.getMemPtr()
local function w16(a, v) ffi.cast("uint16_t*", mem + (a & 0x1FFFFF))[0] = v end
local function w32(a, v) ffi.cast("uint32_t*", mem + (a & 0x1FFFFF))[0] = v end
local function r16(a) return ffi.cast("uint16_t*", mem + (a & 0x1FFFFF))[0] end
local function r32(a) return ffi.cast("uint32_t*", mem + (a & 0x1FFFFF))[0] end
local function j(a) return 0x08000000 + ((a & 0x0FFFFFFF) >> 2) end
local function jal(a) return 0x0C000000 + ((a & 0x0FFFFFFF) >> 2) end

local GP = 0x800A0E24
local CUR_MAP = 0x80177D70 -- 0x8004355C returns this
local REQ = 0x80097B28     -- jump request; +0xC map, +0xE entrance, +0x10 fade
local STORY = 0x80177864   -- story flag bits, 0x8002C4F0 sets
local STUB = 0x800D6B00    -- 0x100 bytes between MAIN.EXE's BSS end (0x800D6AF8) and the overlay base (0x800D6C00)
local LOAD_SUB = 0x800279A0
local WAIT_SUB = 0x80027A10
local WAIT_SITES = { 0x80029EC8, 0x8002A098 } -- `jal WAIT_SUB` in the two map-init paths

local scene = {}
if SCENE then
  -- SCENES_LUA: absolute path, passed by tools/debug/regen.py (the emulator's working folder is not the repo)
  scene = dofile(SCENES_LUA)[SCENE] or error("unknown scene: " .. SCENE)
  MAP, SUB, ENTR, FLAGS, UNFLAGS, BASE = scene.map, scene.sub, scene.entr, scene.flags, scene.unflags, scene.base
end
local function route(spec)
  for frames, btn in spec:gmatch("(%d+) ([^;]+)") do L.press(btn, tonumber(frames)) end
end

local function story(id, on)
  local a, bit = STORY + (id >> 5) * 4, 1 << (id & 31)
  w32(a, on and (r32(a) | bit) or (r32(a) & ~bit))
end

function warp(map, entr, fade)
  w16(REQ + 0xC, map); w16(REQ + 0xE, entr or 0); w16(REQ + 0x10, fade or 7)
  w32(GP + 0x7B8, 0); w32(GP + 0x7C8, REQ); w16(GP + 0x7AE, 1)
  L.log(string.format("warp f%d map=%d entr=%d (cur %d)", L.frame, map, entr or 0, r16(CUR_MAP)))
end

-- Load sub-scene `id` during the map's init, so it gets its init call (mode 0) like a real one. Two patches:
-- 0x800279A0 (load request): any id the map asks for becomes `id`.
-- the map init's `jal WAIT_SUB`: if the map asked for none and none is loading, ask now.
local function force_sub(id)
  local a = STUB + 0x60
  local c = {
    0x34040000 + id, -- ori   a0,zero,id
    0x27BDFFE8,      -- addiu sp,sp,-0x18  (original first instruction)
    0xAFB00010,      -- sw    s0,0x10(sp)  (original second)
    j(LOAD_SUB + 8),
    0,
    -- second stub, a + 0x14
    0x3C08800A,      -- lui   t0,0x800A
    0x85090EC2,      -- lh    t1,0xEC2(t0)  id being loaded, -1 if none (0x9E(gp))
    0x240AFFFF,      -- addiu t2,zero,-1
    0x152A000A,      -- bne   t1,t2,done
    0x8D0915A0,      -- lw    t1,0x15A0(t0) sub-scene callback, 0 if none
    0,               -- load delay
    0x15200007,      -- bnez  t1,done
    0,
    0x27BDFFF8,      -- addiu sp,sp,-8
    0xAFBF0000,      -- sw    ra,0(sp)
    jal(LOAD_SUB),   -- a0 is set by the first stub
    0,
    0x8FBF0000,      -- lw    ra,0(sp)
    0x27BD0008,      -- addiu sp,sp,8
    j(WAIT_SUB),     -- done:
    0,
  }
  for i, w in ipairs(c) do w32(a + (i - 1) * 4, w) end
  w32(LOAD_SUB, j(a)); w32(LOAD_SUB + 4, 0)
  for _, site in ipairs(WAIT_SITES) do w32(site, jal(a + 0x14)) end
  PCSX.invalidateCache()
end

-- BASE "opening" (default): fire on the opening scene, after its room shows (+340) and before its first text box (+900):
-- a box left open blocks the next scene's event. Fast (f5260), but the hero has no valid spot: no control, no menus.
-- BASE "field": mash through the opening to the first hand-control on map 140 (about f26200), then fire. For menus, dungeons.
-- The field ignores a request while it loads, so repeat until the map changes.
local FIELD = 0x01900000 -- mode flags (0x80177CA8) while the player has control
local forced, subbed, settled, last, ready, arrived, mash = false, false, false, -1, nil, nil, 0
L.on_frame(function(n)
  local m = r16(CUR_MAP)
  if m ~= last then L.log(string.format("f%d map %d", n, m)); last = m end
  if BASE == "field" then
    if not ready and m == 140 and r32(0x80177CA8) == FIELD then ready = n; L.log("field ready f" .. n) end
    if not ready and m ~= 0 and n - mash >= 60 then mash = n; L.press("circle", 6) end
  elseif not ready and m == 1023 then ready = n + 400 end
  if MAP and not arrived then
    if m == MAP then
      -- already the current scene (the boot route loads it, e.g. the opening map): don't warp to itself, that
      -- restarts the map mid-scene and leaves the screen blank.
      arrived = n; L.log(string.format("f%d already map %d", n, m))
    elseif ready and n >= ready + (DELAY or 0) and (n - ready) % 120 == 0 then
      if not forced then
        forced = true
        if SUB then force_sub(SUB) end
        for _, id in ipairs(FLAGS or {}) do story(id, true) end
        for _, id in ipairs(UNFLAGS or {}) do story(id, false) end
      end
      warp(MAP, ENTR, FADE)
    end
  end
  if SUB and arrived and not subbed and r32(GP + 0x77C) ~= 0 and r16(GP + 0x9E) == 0xFFFF then
    subbed = true; L.log(string.format("f%d sub %d loaded", n, SUB))
  end
  if scene.debug then w16(GP + 0x1C2, 1) end
  -- wait for hand control on the new map before pressing anything
  if arrived and not settled and r32(0x80177CA8) == FIELD then
    settled = true; L.log("control f" .. n)
    if scene.hp then ffi.cast("uint16_t*", mem + (r32(0x800A1814) & 0x1FFFFF) + 0x6A)[0] = scene.hp end
    if scene.keys then route(scene.keys) end
  end
end)
