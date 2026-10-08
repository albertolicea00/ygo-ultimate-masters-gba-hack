-- Auto test of pause-and-browse. Generation guard: older loaded instances
-- self-disable, so re-loading via dofile is safe.
bt_gen = (bt_gen or 0) + 1
local mygen = bt_gen

local DUEL   = 0x0201C4E0
local TURN   = 0x0201E1C8
local MODE   = 0x0201E22C
local PHASE  = 0x0201E1F8
local STEP   = 0x0201E1FC
local CURSOR = 0x02023340
local LOCAL  = 0x0201E2A4
local KEY_A  = 0
local RIGHT  = 16

bt_state = 0
bt_frame = 0
bt_cur0  = nil
bt_phaselog = {}
bt_f = io.open('/tmp/browse_test.log','w')
local function log(s) if bt_f then bt_f:write(s..'\n'); bt_f:flush() end end

local function setMode1()
  emu:write32(MODE, 1)
  emu:write32(DUEL + 0x1D7C, 0)
  emu:write32(DUEL + 0x1D58, 0)
  emu:write32(DUEL + 0x1D54, 0)
  emu:write32(DUEL + 0x1D64, emu:read32(LOCAL))
end

log(string.format('start gen=%d turn=%d mode=%d phase=%d step=%d',
  mygen, emu:read32(TURN)&1, emu:read32(MODE), emu:read32(PHASE), emu:read32(STEP)))

callbacks:add('keysRead', function()
  if mygen ~= bt_gen then return end
  if bt_state >= 1 and bt_state <= 3 then emu:clearKey(KEY_A) end
end)

callbacks:add('frame', function()
  if mygen ~= bt_gen then return end
  local turn = emu:read32(TURN) & 1
  local mode = emu:read32(MODE)
  local phase = emu:read32(PHASE)

  if bt_state == 0 then
    if turn == 1 then
      table.insert(bt_phaselog, phase)
      if #bt_phaselog >= 4 then
        setMode1()
        bt_state = 1; bt_frame = 0
        log('engaged: baseline phases='..table.concat(bt_phaselog,',')..
            ' mode->'..emu:read32(MODE))
      end
    end
  elseif bt_state == 1 then
    emu:setKeys(0)
    bt_frame = bt_frame + 1
    if bt_frame >= 8 then
      bt_cur0 = emu:read16(CURSOR)
      log(string.format('settled: turn=%d mode=%d phase=%d cursor=%04x',
        turn, mode, phase, bt_cur0))
      bt_state = 2; bt_frame = 0
    end
  elseif bt_state == 2 then
    emu:setKeys(RIGHT)
    bt_frame = bt_frame + 1
    if bt_frame >= 4 then bt_state = 3; bt_frame = 0 end
  elseif bt_state == 3 then
    emu:setKeys(0)
    bt_frame = bt_frame + 1
    if bt_frame >= 6 then
      local cur1 = emu:read16(CURSOR)
      log(string.format('after Right: turn=%d mode=%d phase=%d cursor=%04x (was %04x) moved=%s',
        turn, mode, phase, cur1, bt_cur0, tostring(cur1 ~= bt_cur0)))
      emu:write32(MODE, 0)
      bt_state = 4; bt_frame = 0
    end
  elseif bt_state == 4 then
    bt_frame = bt_frame + 1
    if bt_frame == 45 then
      log(string.format('post-exit(+45f): turn=%d mode=%d phase=%d',
        turn, emu:read32(MODE), phase))
      bt_state = 5
    end
  end
end)
