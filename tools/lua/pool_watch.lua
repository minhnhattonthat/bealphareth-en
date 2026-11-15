-- pool_watch.lua: playtest probe for the sub-scene pool (insert.SUB_POOL_RAM, 0x801974C0 + 0x3B40).
-- Logs every change of map id, of the loaded sub-scene's first word, and of the pool area (with its first bytes as
-- text). A pool change with no sub-scene load in the same few frames means something else uses the area.
-- Also logs when a word of MAIN.EXE code in 0x80018000-0x80070000 changes (stray writes, as the v1.4 freeze did).
local ffi = require("ffi")
local m = PCSX.getMemPtr()
local POOL, SIZE = 0x1974C0, 0x3B40
local function u32(a) return ffi.cast("uint32_t*", m + a)[0] end
local function u16(a) return ffi.cast("uint16_t*", m + a)[0] end
local function sum(lo, n)
  local s = 0
  for i = 0, n / 4 - 1 do s = (s * 31 + u32(lo + i * 4)) % 4294967291 end
  return s
end
local last_map, last_sub, last_pool, code
L.on_frame(function(n)
  if n % 10 ~= 0 then return end
  local map, sub, pool = u16(0x177D70), u32(0x136C00 + 0x10), sum(POOL, SIZE)
  if map ~= last_map then L.log(string.format("WATCH f%d map %d", n, map)); last_map = map end
  if sub ~= last_sub then L.log(string.format("WATCH f%d sub word %08x", n, sub)); last_sub = sub end
  if pool ~= last_pool then
    local txt = ffi.string(m + POOL, 40):gsub("[^%g ]", ".")
    L.log(string.format("WATCH f%d pool changed map %d [%s]", n, map, txt)); last_pool = pool
  end
  if n % 60 == 0 then
    local c = sum(0x18000, 0x58000)
    if code and c ~= code then L.log(string.format("WATCH f%d CODE CHANGED map %d", n, map)) end
    code = c
  end
end)
