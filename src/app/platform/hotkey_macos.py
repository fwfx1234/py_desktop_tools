from __future__ import annotations

from PySide6.QtCore import QObject, Signal, QTimer


_NORMALIZED_ALT_NAMES = {"alt", "option"}
_NORMALIZED_CTRL_NAMES = {"ctrl", "control"}
_NORMALIZED_SHIFT_NAMES = {"shift"}
_NORMALIZED_CMD_NAMES = {"cmd", "command", "meta", "win"}


class MacHotkeyManager(QObject):
    hotkeyPressed = Signal()

    def __init__(self, parent: QObject | None = None, *, hotkey: str = "", hotkey_id: int = 0) -> None:
        super().__init__(parent)
        self._hotkey = hotkey
        self._hotkey_id = hotkey_id
        self._registered = False
        self._listener = None
        self._pressed_modifiers: set[str] = set()
        self._target_modifiers: set[str] = set()
        self._target_key = ""

    def register(self, hotkey: str | None = None) -> bool:
        if hotkey is not None:
            self._hotkey = hotkey
        parsed = _parse_hotkey(self._hotkey)
        if parsed is None:
            self._registered = False
            return False
        self.unregister()
        try:
            from pynput import keyboard
        except Exception as exc:
            print(f"[WARN] macOS global hotkey unavailable: {exc}")
            return False

        self._target_modifiers, self._target_key = parsed

        def on_press(key):
            self._handle_press(key)

        def on_release(key):
            self._handle_release(key)

        try:
            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.start()
            self._registered = True
            return True
        except Exception as exc:
            print(f"[WARN] macOS global hotkey register failed: {exc}")
            self._listener = None
            self._registered = False
            return False

    def unregister(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
        self._listener = None
        self._pressed_modifiers.clear()
        self._registered = False

    def is_registered(self) -> bool:
        return self._registered

    def _handle_press(self, key: object) -> None:
        normalized = _normalize_pressed_key(key)
        if not normalized:
            return
        if normalized in {"alt", "ctrl", "shift", "cmd"}:
            self._pressed_modifiers.add(normalized)
            return
        if normalized == self._target_key and self._pressed_modifiers == self._target_modifiers:
            QTimer.singleShot(0, self.hotkeyPressed.emit)

    def _handle_release(self, key: object) -> None:
        normalized = _normalize_pressed_key(key)
        if normalized in {"alt", "ctrl", "shift", "cmd"}:
            self._pressed_modifiers.discard(normalized)


class MacHotkeyFactory:
    def create(self, *, parent: object | None, hotkey: str, hotkey_id: int) -> MacHotkeyManager:
        owner = parent if isinstance(parent, QObject) else None
        return MacHotkeyManager(owner, hotkey=hotkey, hotkey_id=hotkey_id)

    def install_filter(self, app: object, manager: object) -> object | None:
        del app, manager
        return None


def _parse_hotkey(hotkey: str) -> tuple[set[str], str] | None:
    parts = [part.strip().lower() for part in hotkey.replace("＋", "+").split("+") if part.strip()]
    if not parts:
        return None
    modifiers: set[str] = set()
    key_name = ""
    for part in parts:
        if part in _NORMALIZED_ALT_NAMES:
            modifiers.add("alt")
        elif part in _NORMALIZED_CTRL_NAMES:
            modifiers.add("ctrl")
        elif part in _NORMALIZED_SHIFT_NAMES:
            modifiers.add("shift")
        elif part in _NORMALIZED_CMD_NAMES:
            modifiers.add("cmd")
        else:
            key_name = _normalize_key_name(part)
    if not key_name:
        return None
    return modifiers, key_name


def _normalize_pressed_key(key: object) -> str:
    try:
        from pynput import keyboard
    except Exception:
        return ""
    if key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr}:
        return "alt"
    if key in {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}:
        return "ctrl"
    if key in {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}:
        return "shift"
    if key in {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r}:
        return "cmd"
    if key == keyboard.Key.space:
        return "space"
    if key == keyboard.Key.enter:
        return "enter"
    if key == keyboard.Key.tab:
        return "tab"
    if key == keyboard.Key.esc:
        return "escape"
    char = getattr(key, "char", None)
    if isinstance(char, str) and char:
        return _normalize_key_name(char)
    name = getattr(key, "name", None)
    if isinstance(name, str) and name:
        return _normalize_key_name(name)
    return ""


def _normalize_key_name(name: str) -> str:
    token = name.strip().lower()
    aliases = {
        "return": "enter",
        "esc": "escape",
        "option": "alt",
    }
    return aliases.get(token, token)
