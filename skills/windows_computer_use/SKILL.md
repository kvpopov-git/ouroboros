---
name: windows_computer_use
description: Local Windows desktop observation and input (screenshot, mouse, keyboard) with coordinate remapping.
version: 0.1.0
type: extension
entry: plugin.py
runtime: python3
permissions: [tool, subprocess]
env_from_settings: []
when_to_use: The user asks Ouroboros to inspect a Windows desktop, take a screenshot, click/type/press keys, drag, or scroll under human supervision.
---

# Windows Computer Use

Supervised Windows desktop substrate for this fork. Uses Pillow `ImageGrab` for
screenshots and Win32 `SendInput` / cursor APIs for pointer and keyboard input
(no extra pip dependency beyond the core runtime).

Tools:

- `capabilities` — platform and backend health.
- `screenshot` — capture primary display, downscale to WXGA (1280x800), persist
  the image→input transform, and auto-attach the image.
- `click` / `double_click` / `triple_click` / `move` / `left_click_drag` /
  `mouse_down` / `mouse_up` / `cursor_position` / `type_text` / `key` /
  `scroll` / `wait` / `window_list`.

Coordinate contract matches `unix_computer_use`: coordinates are in the last
screenshot's image space unless `raw=true`.

Safety: all actions are for supervised low-risk workflows. The skill does not
elevate UAC or bypass application permissions.
