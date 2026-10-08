-- Prototype: browse the field during the CPU's turn (pause-and-browse).
--
-- Load in mGBA's Scripting window (File > Load script...) or via the harness:
--   run_lua.sh "dofile('/abs/path/to/tools/opp_turn_browse.lua')"
--
-- During the CPU's turn, press Select: the game's own field-browse mode
-- (mode 1, the one the human gets) is switched on. While it is on, the duel
-- tick skips duel logic, so the CPU's turn pauses. D-pad moves the cursor,
-- Start opens card detail, B leaves (the game's own exit path) and the CPU
-- carries on. A is stripped so the command menu (summon/set/activate) can't
-- open out of turn.
--
-- Addresses from static analysis, then validated live (see
-- docs/OPPONENT_TURN_NAVIGATION.md "Live validation"). The mechanism is proven:
-- forcing field mode 1 during the CPU's turn pauses the duel logic and lets the
-- field cursor move. NOTE: the cursor only becomes movable once the field task
-- actually starts, which waits for any CPU animation already in progress to
-- finish (~0.5s). Until then the screen is paused but the cursor is still. This
-- is expected, not a bug.
--
-- Do NOT re-assert mode=1 every frame: pressing B makes the game's own exit set
-- mode=0, and that is how we detect the player wants out. Re-asserting would
-- trap them in browse mode.

local DUEL        = 0x0201C4E0 -- big duel struct (per-player blocks at +0xC, stride 0x868)
local TURN_PLAYER = 0x0201E1C8 -- u32, & 1 = player whose turn it is
local FIELD_DONE  = 0x0201E234 -- u32, set when a field interaction finishes
local LOCAL_SIDE  = 0x0201E2A4 -- u32, this GBA's player index
local CONTROLLER  = 0x0201E2A8 -- u32[2], 0 = local human, 1 = CPU, 2 = link
local FIELD_MODE  = 0x0201E22C -- u32, 0 = off, 1 = free browse, others = prompts
local NEW_KEYS    = 0x03000188 -- u16, gMain newKeys (ReadKeys output)

local CPU = 1
local KEY_A_INDEX = 0          -- C.GBA_KEY.A
local SELECT_MASK = 0x0004

oppBrowse_active = false
oppBrowse_log = io.open('/tmp/opp_turn_browse.log', 'w')

local function log(msg)
  if oppBrowse_log then oppBrowse_log:write(msg .. '\n'); oppBrowse_log:flush() end
end

local function cpuTurn()
  local tp = emu:read32(TURN_PLAYER) & 1
  return emu:read32(CONTROLLER + 4 * tp) == CPU
end

callbacks:add('keysRead', function()
  if oppBrowse_active then emu:clearKey(KEY_A_INDEX) end
end)

callbacks:add('frame', function()
  local mode = emu:read32(FIELD_MODE)
  if oppBrowse_active then
    if mode == 0 then
      oppBrowse_active = false
      log('browse off (frame ' .. emu:currentFrame() .. ')')
    end
    return
  end
  if cpuTurn() and mode == 0 and (emu:read16(NEW_KEYS) & SELECT_MASK) ~= 0 then
    -- Same writes as the game's SetFieldMode (0x08096988) with r0 = 1.
    log(string.format('before: 1d54=%d 1d58=%d 1d7c=%d', emu:read32(FIELD_DONE),
        emu:read32(DUEL + 0x1D58), emu:read32(DUEL + 0x1D7C)))
    emu:write32(FIELD_MODE, 1)
    emu:write32(DUEL + 0x1D7C, 0)
    emu:write32(DUEL + 0x1D58, 0)
    emu:write32(FIELD_DONE, 0)
    emu:write32(DUEL + 0x1D64, emu:read32(LOCAL_SIDE))
    oppBrowse_active = true
    log('browse on (frame ' .. emu:currentFrame() .. ')')
  end
end)

log('loaded; turnPlayer=' .. emu:read32(TURN_PLAYER) ..
    ' ctl0=' .. emu:read32(CONTROLLER) .. ' ctl1=' .. emu:read32(CONTROLLER + 4))
