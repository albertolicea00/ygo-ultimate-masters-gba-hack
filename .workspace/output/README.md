# How to play the patched ROM on your phone

This folder has **`trm-yum6-oppnav.gba`**: Yu-Gi-Oh! Ultimate Masters with the
patch already baked in. That file IS the ready-to-play game. You don't need to
patch anything else.

(There's a copy with an easy name on your Desktop:
`YuGiOh-UltimateMasters-PARCHEADO.gba`. Same file.)

- CRC32 of this file: `0xE0C3D7F0` (use it to confirm you have the right one).

---

## Step 1 — get the .gba file onto your phone

Pick whatever is easiest:

- **Google Drive**: upload it from the computer → open Drive on the phone →
  download it.
- **Telegram / WhatsApp / email**: send it to yourself as a file attachment →
  download it on the phone.
- **USB cable**: plug in the phone and copy the `.gba` over.
- **iPhone**: **AirDrop** from the Mac also works.

Remember which folder it lands in (usually **Downloads**, or the **Files** app on
iPhone).

---

## Step 2A — Android

1. In the **Play Store**, install a GBA emulator. Recommended:
   **Pizza Boy GBA (Free)**. Alternatives: My Boy!, mGBA.
2. Open the emulator.
3. Tap **Open ROM / Load game** (the wording varies).
4. Find `trm-yum6-oppnav.gba` in the folder where you saved it.
5. Tap it. The game starts.

---

## Step 2B — iPhone / iPad (iOS)

1. In the **App Store**, install **Delta** (free).
2. Make sure the `.gba` is in the **Files** app. If you got it via Drive or
   AirDrop, save it there (**Downloads** or **On My iPhone**).
3. Open **Delta**.
4. Tap the **+** button (top) → **Import**.
5. Choose the `.gba` from Files.
6. The game's cover appears. Tap it to play.

---

## How to use the patch in-game

The whole point of the patch: **move around during the opponent's turn**.

1. When it's the opponent's (CPU's) turn, press **Select**.
2. The cursor appears and the opponent's turn **pauses**.
3. Move the cursor with the **D-pad** (you can see the whole field, both sides).
4. **Start** → view a card's detail.
5. **B** → leave; the opponent's turn resumes.
6. **A is blocked on purpose** (you can't play cards out of turn).

Note: after pressing Select there's a ~half-second wait before the cursor shows,
while the animation the CPU was in the middle of finishes. That's normal.

---

## Common problems

- **Emulator says the ROM is invalid / corrupt**: you downloaded an incomplete
  file. Transfer it again in full. It should be 32 MB.
- **Nothing happens on Select**: confirm it's really the opponent's turn, and
  that you're pressing **Select** (not Start). Wait the ~half-second.
- **Can't leave view mode**: press **B** (**A** is blocked on purpose).
- **Where do I set the buttons?**: Pizza Boy / Delta have on-screen control
  settings; that's where you see/change Select, Start, A and B.
