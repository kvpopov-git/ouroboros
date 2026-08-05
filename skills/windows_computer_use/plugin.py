"""Windows computer-use extension: screenshot + desktop input via Win32 APIs."""

from __future__ import annotations

import json
import pathlib
import platform
import time
from datetime import datetime, timezone
from typing import Any

_TIMEOUT_SEC = 30
_MAX_SHOT_W, _MAX_SHOT_H = 1280, 800
_TRANSFORM_FILE = "last_transform.json"

_KEY_ALIASES = {
    "pagedown": "page-down", "page_down": "page-down", "pgdn": "page-down",
    "pageup": "page-up", "page_up": "page-up", "pgup": "page-up",
    "down": "arrow-down", "up": "arrow-up", "left": "arrow-left", "right": "arrow-right",
    "arrowdown": "arrow-down", "arrowup": "arrow-up", "arrowleft": "arrow-left", "arrowright": "arrow-right",
    "enter": "return", "escape": "esc", "del": "delete", "backspace": "backspace",
    "space": "space", "tab": "tab", "home": "home", "end": "end",
    "cmd": "win", "command": "win", "ctrl": "ctrl", "control": "ctrl",
    "alt": "alt", "option": "alt", "shift": "shift", "win": "win", "meta": "win",
}

# Virtual-key codes for named keys (Windows).
_VK = {
    "return": 0x0D, "esc": 0x1B, "tab": 0x09, "space": 0x20,
    "backspace": 0x08, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "page-up": 0x21, "page-down": 0x22,
    "arrow-left": 0x25, "arrow-up": 0x26, "arrow-right": 0x27, "arrow-down": 0x28,
    "ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B,
    **{f"f{i}": 0x70 + i - 1 for i in range(1, 13)},
}

_MODS = {"ctrl", "alt", "shift", "win"}


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


class _WindowsComputerUse:
    def __init__(self, api: Any) -> None:
        self.api = api
        self.state_dir = pathlib.Path(api.get_state_dir())
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.shot_dir = self.state_dir / "screenshots"
        self.shot_dir.mkdir(parents=True, exist_ok=True)

    def capabilities(self) -> str:
        ok = _is_windows()
        try:
            from PIL import ImageGrab  # noqa: F401
            pillow_ok = True
        except Exception:
            pillow_ok = False
        return _json({
            "ok": ok and pillow_ok,
            "platform": "windows" if ok else platform.system().lower(),
            "backend": "win32+pillow",
            "screenshot": {"pillow_imagegrab": pillow_ok},
            "input": {"sendinput": ok},
            "notes": [
                "Supervised low-risk Windows desktop control only.",
                "Coordinates default to the LAST screenshot image space; pass raw=true for native pixels.",
                "Does not bypass UAC or application sandboxes.",
            ],
        })

    def _save_transform(self, data: dict[str, Any]) -> None:
        (self.state_dir / _TRANSFORM_FILE).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def _load_transform(self) -> dict[str, Any]:
        try:
            return json.loads((self.state_dir / _TRANSFORM_FILE).read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _map_xy(self, x: int, y: int, *, raw: bool) -> tuple[int, int]:
        if raw:
            return int(x), int(y)
        tr = self._load_transform()
        scale_x = float(tr.get("scale_x") or 1.0)
        scale_y = float(tr.get("scale_y") or 1.0)
        off_x = float(tr.get("offset_x") or 0.0)
        off_y = float(tr.get("offset_y") or 0.0)
        return int(round(x * scale_x + off_x)), int(round(y * scale_y + off_y))

    def screenshot(self, max_width: int = _MAX_SHOT_W, max_height: int = _MAX_SHOT_H) -> str:
        if not _is_windows():
            return _json({"ok": False, "error": "windows_computer_use only runs on Windows"})
        try:
            from PIL import ImageGrab
        except Exception as exc:
            return _json({"ok": False, "error": f"Pillow ImageGrab unavailable: {exc}"})

        img = ImageGrab.grab(all_screens=False)
        native_w, native_h = img.size
        mw = max(64, int(max_width or _MAX_SHOT_W))
        mh = max(64, int(max_height or _MAX_SHOT_H))
        scale = min(1.0, mw / native_w, mh / native_h)
        out_w = max(1, int(round(native_w * scale)))
        out_h = max(1, int(round(native_h * scale)))
        if scale < 1.0:
            img = img.resize((out_w, out_h))

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.shot_dir / f"screen_{ts}.png"
        img.save(path, format="PNG")
        transform = {
            "scale_x": native_w / out_w,
            "scale_y": native_h / out_h,
            "offset_x": 0.0,
            "offset_y": 0.0,
            "image_w": out_w,
            "image_h": out_h,
            "native_w": native_w,
            "native_h": native_h,
            "path": str(path),
        }
        self._save_transform(transform)
        return _json({
            "ok": True,
            "path": str(path),
            "image_w": out_w,
            "image_h": out_h,
            "native_w": native_w,
            "native_h": native_h,
            "auto_attach_image": str(path),
            "transform": transform,
        })

    def _require_win32(self):
        if not _is_windows():
            raise RuntimeError("windows_computer_use only runs on Windows")
        import ctypes
        return ctypes

    def _set_cursor(self, x: int, y: int) -> None:
        ctypes = self._require_win32()
        ctypes.windll.user32.SetCursorPos(int(x), int(y))

    def _mouse_event(self, flags: int, data: int = 0) -> None:
        ctypes = self._require_win32()
        ctypes.windll.user32.mouse_event(flags, 0, 0, data, 0)

    def cursor_position(self) -> str:
        ctypes = self._require_win32()
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return _json({"ok": True, "x": int(pt.x), "y": int(pt.y)})

    def move(self, x: int, y: int, raw: bool = False) -> str:
        nx, ny = self._map_xy(int(x), int(y), raw=bool(raw))
        self._set_cursor(nx, ny)
        return _json({"ok": True, "x": nx, "y": ny})

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1,
        raw: bool = False,
    ) -> str:
        nx, ny = self._map_xy(int(x), int(y), raw=bool(raw))
        self._set_cursor(nx, ny)
        button = str(button or "left").lower()
        down_up = {
            "left": (0x0002, 0x0004),
            "right": (0x0008, 0x0010),
            "middle": (0x0020, 0x0040),
        }.get(button)
        if not down_up:
            return _json({"ok": False, "error": f"unsupported button: {button}"})
        down, up = down_up
        for _ in range(max(1, int(clicks))):
            self._mouse_event(down)
            self._mouse_event(up)
            time.sleep(0.05)
        return _json({"ok": True, "x": nx, "y": ny, "button": button, "clicks": int(clicks)})

    def double_click(self, x: int, y: int, button: str = "left", raw: bool = False) -> str:
        return self.click(x, y, button=button, clicks=2, raw=raw)

    def triple_click(self, x: int, y: int, button: str = "left", raw: bool = False) -> str:
        return self.click(x, y, button=button, clicks=3, raw=raw)

    def mouse_down(self, x: int | None = None, y: int | None = None, button: str = "left", raw: bool = False) -> str:
        if x is not None and y is not None:
            nx, ny = self._map_xy(int(x), int(y), raw=bool(raw))
            self._set_cursor(nx, ny)
        else:
            nx = ny = None
        button = str(button or "left").lower()
        flag = {"left": 0x0002, "right": 0x0008, "middle": 0x0020}.get(button)
        if flag is None:
            return _json({"ok": False, "error": f"unsupported button: {button}"})
        self._mouse_event(flag)
        return _json({"ok": True, "x": nx, "y": ny, "button": button, "state": "down"})

    def mouse_up(self, x: int | None = None, y: int | None = None, button: str = "left", raw: bool = False) -> str:
        if x is not None and y is not None:
            nx, ny = self._map_xy(int(x), int(y), raw=bool(raw))
            self._set_cursor(nx, ny)
        else:
            nx = ny = None
        button = str(button or "left").lower()
        flag = {"left": 0x0004, "right": 0x0010, "middle": 0x0040}.get(button)
        if flag is None:
            return _json({"ok": False, "error": f"unsupported button: {button}"})
        self._mouse_event(flag)
        return _json({"ok": True, "x": nx, "y": ny, "button": button, "state": "up"})

    def left_click_drag(self, x1: int, y1: int, x2: int, y2: int, raw: bool = False) -> str:
        a = self._map_xy(int(x1), int(y1), raw=bool(raw))
        b = self._map_xy(int(x2), int(y2), raw=bool(raw))
        self._set_cursor(*a)
        self._mouse_event(0x0002)
        time.sleep(0.05)
        self._set_cursor(*b)
        time.sleep(0.05)
        self._mouse_event(0x0004)
        return _json({"ok": True, "from": {"x": a[0], "y": a[1]}, "to": {"x": b[0], "y": b[1]}})

    def scroll(self, x: int, y: int, direction: str = "down", amount: int = 3, raw: bool = False) -> str:
        nx, ny = self._map_xy(int(x), int(y), raw=bool(raw))
        self._set_cursor(nx, ny)
        direction = str(direction or "down").lower()
        clicks = max(1, int(amount))
        delta = 120 * clicks if direction in {"up", "left"} else -120 * clicks
        # MOUSEEVENTF_WHEEL / HWHEEL
        flag = 0x01000 if direction in {"up", "down"} else 0x01000
        if direction in {"left", "right"}:
            flag = 0x01000  # vertical fallback; horizontal wheel is less portable
        self._mouse_event(flag, data=delta & 0xFFFFFFFF)
        return _json({"ok": True, "x": nx, "y": ny, "direction": direction, "amount": clicks})

    def _key_event(self, vk: int, *, up: bool = False) -> None:
        ctypes = self._require_win32()
        flags = 0x0002 if up else 0x0000  # KEYEVENTF_KEYUP
        ctypes.windll.user32.keybd_event(vk, 0, flags, 0)

    def _resolve_token(self, token: str) -> str:
        t = str(token or "").strip().lower()
        return _KEY_ALIASES.get(t, t)

    def key(self, keys: str) -> str:
        parts = [self._resolve_token(p) for p in str(keys or "").replace("+", " ").split() if p.strip()]
        if not parts:
            return _json({"ok": False, "error": "keys required"})
        mods = [p for p in parts if p in _MODS]
        bases = [p for p in parts if p not in _MODS]
        if len(bases) != 1:
            return _json({"ok": False, "error": "provide exactly one non-modifier key (e.g. ctrl+s)"})
        base = bases[0]
        if base in _VK:
            vk = _VK[base]
        elif len(base) == 1:
            ctypes = self._require_win32()
            vk = ctypes.windll.user32.VkKeyScanW(ord(base)) & 0xFF
        else:
            return _json({"ok": False, "error": f"unsupported key: {base}"})
        for m in mods:
            self._key_event(_VK[m], up=False)
        self._key_event(vk, up=False)
        self._key_event(vk, up=True)
        for m in reversed(mods):
            self._key_event(_VK[m], up=True)
        return _json({"ok": True, "keys": parts})

    def type_text(self, text: str, interval: float = 0.02) -> str:
        ctypes = self._require_win32()
        payload = str(text or "")
        for ch in payload:
            if ch == "\n":
                self.key("return")
                continue
            vk = ctypes.windll.user32.VkKeyScanW(ord(ch))
            if vk == -1:
                continue
            lo = vk & 0xFF
            shift = bool(vk & 0x100)
            if shift:
                self._key_event(_VK["shift"], up=False)
            self._key_event(lo, up=False)
            self._key_event(lo, up=True)
            if shift:
                self._key_event(_VK["shift"], up=True)
            time.sleep(max(0.0, float(interval)))
        return _json({"ok": True, "length": len(payload)})

    def wait(self, seconds: float = 1.0) -> str:
        time.sleep(max(0.0, min(float(seconds), 30.0)))
        return _json({"ok": True, "waited": float(seconds)})

    def window_list(self) -> str:
        ctypes = self._require_win32()
        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        titles: list[str] = []

        def _cb(hwnd, _lparam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        titles.append(title)
            return True

        EnumWindows(EnumWindowsProc(_cb), 0)
        return _json({"ok": True, "windows": titles[:80]})


def register(api: Any) -> None:
    impl = _WindowsComputerUse(api)
    api.register_tool(
        "capabilities",
        lambda: impl.capabilities(),
        description="Report Windows computer-use backend health and coordinate contract.",
        schema={"type": "object", "properties": {}},
        timeout_sec=5,
    )
    api.register_tool(
        "screenshot",
        impl.screenshot,
        description="Capture the primary Windows display, downscale, and auto-attach the image.",
        schema={
            "type": "object",
            "properties": {
                "max_width": {"type": "integer", "default": _MAX_SHOT_W},
                "max_height": {"type": "integer", "default": _MAX_SHOT_H},
            },
        },
        timeout_sec=_TIMEOUT_SEC,
    )
    api.register_tool(
        "click",
        impl.click,
        description="Click at screenshot-space coordinates (or raw=true for native pixels).",
        schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "button": {"type": "string", "default": "left"},
                "clicks": {"type": "integer", "default": 1},
                "raw": {"type": "boolean", "default": False},
            },
            "required": ["x", "y"],
        },
        timeout_sec=10,
    )
    api.register_tool("double_click", impl.double_click, description="Double-click.", schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "raw": {"type": "boolean", "default": False}}, "required": ["x", "y"]}, timeout_sec=10)
    api.register_tool("triple_click", impl.triple_click, description="Triple-click.", schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "raw": {"type": "boolean", "default": False}}, "required": ["x", "y"]}, timeout_sec=10)
    api.register_tool("move", impl.move, description="Move the cursor.", schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "raw": {"type": "boolean", "default": False}}, "required": ["x", "y"]}, timeout_sec=5)
    api.register_tool("left_click_drag", impl.left_click_drag, description="Drag with left button held.", schema={"type": "object", "properties": {"x1": {"type": "integer"}, "y1": {"type": "integer"}, "x2": {"type": "integer"}, "y2": {"type": "integer"}, "raw": {"type": "boolean", "default": False}}, "required": ["x1", "y1", "x2", "y2"]}, timeout_sec=15)
    api.register_tool("mouse_down", impl.mouse_down, description="Press a mouse button.", schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "raw": {"type": "boolean", "default": False}}}, timeout_sec=5)
    api.register_tool("mouse_up", impl.mouse_up, description="Release a mouse button.", schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "default": "left"}, "raw": {"type": "boolean", "default": False}}}, timeout_sec=5)
    api.register_tool("cursor_position", lambda: impl.cursor_position(), description="Return current cursor position in native pixels.", schema={"type": "object", "properties": {}}, timeout_sec=5)
    api.register_tool("type_text", impl.type_text, description="Type Unicode text via Win32 key events.", schema={"type": "object", "properties": {"text": {"type": "string"}, "interval": {"type": "number", "default": 0.02}}, "required": ["text"]}, timeout_sec=60)
    api.register_tool("key", impl.key, description="Press a key or combo (e.g. ctrl+s, alt+tab, enter).", schema={"type": "object", "properties": {"keys": {"type": "string"}}, "required": ["keys"]}, timeout_sec=10)
    api.register_tool("scroll", impl.scroll, description="Scroll at a point.", schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "direction": {"type": "string", "default": "down"}, "amount": {"type": "integer", "default": 3}, "raw": {"type": "boolean", "default": False}}, "required": ["x", "y"]}, timeout_sec=10)
    api.register_tool("wait", impl.wait, description="Sleep briefly (max 30s).", schema={"type": "object", "properties": {"seconds": {"type": "number", "default": 1.0}}}, timeout_sec=35)
    api.register_tool("window_list", lambda: impl.window_list(), description="List visible top-level window titles.", schema={"type": "object", "properties": {}}, timeout_sec=10)
