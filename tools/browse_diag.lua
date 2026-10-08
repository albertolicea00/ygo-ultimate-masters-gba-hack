-- Frame-exact diagnostic: engage browse on CPU turn, force mode 1, inject Right
-- edges, log per-frame state. No screenshots, no human timing.
dg_gen = (dg_gen or 0) + 1
local mygen = dg_gen

local DUEL    = 0x0201C4E0
local TURN    = 0x0201E1C8
local MODE    = 0x0201E22C
local TASKRUN = 0x0201E230
local NEWKEYS = 0x03000188
local FSTATE  = 0x02023130  -- field-screen state struct, byte +0
local CURSOR  = 0x02023340
local LOCAL   = 0x0201E2A4
local RIGHT   = 16
local KEY_A   = 0

dg_state = 0
dg_f = 0
dg_f2 = io.open('/tmp/diag.log','w')
local function log(s) if dg_f2 then dg_f2:write(s..'\n'); dg_f2:flush() end end

local function setMode1()
  emu:write32(MODE, 1)
  emu:write32(DUEL + 0x1D7C, 0)
  emu:write32(DUEL + 0x1D58, 0)
  emu:write32(DUEL + 0x1D54, 0)
  emu:write32(DUEL + 0x1D64, emu:read32(LOCAL))
end

callbacks:add('keysRead', function()
  if mygen ~= dg_gen then return end
  if dg_state == 1 then emu:clearKey(KEY_A) end
end)

callbacks:add('frame', function()
  if mygen ~= dg_gen then return end
  local turn = emu:read32(TURN) & 1
  if dg_state == 0 then
    if turn == 1 then
      setMode1()
      dg_state = 1; dg_f = 0
      log('engaged mode='..emu:read32(MODE))
    end
  elseif dg_state == 1 then
    dg_f = dg_f + 1
    -- inject Right edge: press on frames where f%6==1, else release
    if dg_f % 6 == 1 then emu:setKeys(RIGHT) else emu:setKeys(0) end
    log(string.format('f=%2d turn=%d mode=%d task=%d fstate=%d newkeys=%04x cursor=%04x',
      dg_f, turn,
      emu:read32(MODE), emu:read32(TASKRUN),
      emu:read8(FSTATE), emu:read16(NEWKEYS), emu:read16(CURSOR)))
    if dg_f >= 48 then
      emu:write32(MODE, 0)
      dg_state = 2
      log('exit mode=0')
    end
  end
end)
log('armed gen='..mygen)
