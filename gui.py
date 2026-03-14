import ctypes
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

import wx
import wx.adv
import wx.lib.scrolledpanel as scrolled

APP_NAME = "KeyTwist"
APP_VERSION = "0.0.1"
BUILD_DATE = "2026-03-14"
SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
BASE_DIR = Path(__file__).resolve().parent
ICON_ICO = BASE_DIR / "icon.ico"
ICON_PNG = BASE_DIR / "icon.png"

WINDOW_W = 460
WINDOW_H = 680
MIN_W = 420
MIN_H = 600

DEFAULT_SETTINGS = {
    "auto_start_engine": True,
    "minimize_to_tray": True,
    "close_to_tray": True,
    "start_minimized": False,
    "font_family": "Microsoft YaHei UI" if IS_WINDOWS else "Arial",
    "font_size": 11,
    "tray_icon_mode": "default",
    "custom_icon_path": "",
    "window_topmost": False,
    "log_level": "普通",
    "check_update_on_start": False,
    "launch_at_startup": False,
    "run_as_admin": False,
    "theme": "light",
    "window_width": WINDOW_W,
    "window_height": WINDOW_H,
}
DEFAULT_RULES = {"rules": []}

TOKEN_ALIAS = {
    "control_l": "lctrl",
    "control_r": "rctrl",
    "control": "ctrl",
    "ctrl": "ctrl",
    "alt_l": "lalt",
    "alt_r": "ralt",
    "alt": "alt",
    "shift_l": "lshift",
    "shift_r": "rshift",
    "shift": "shift",
    "super_l": "lcmd",
    "super_r": "rcmd",
    "super": "cmd",
    "meta_l": "lcmd",
    "meta_r": "rcmd",
    "meta": "cmd",
    "win_l": "lcmd",
    "win_r": "rcmd",
    "return": "enter",
    "escape": "esc",
    "prior": "page_up",
    "next": "page_down",
    "caps_lock": "caps_lock",
    "print": "print_screen",
}
MODIFIER_TOKENS = {"lctrl", "rctrl", "ctrl", "lalt", "ralt", "alt", "lshift", "rshift", "shift", "lcmd", "rcmd", "cmd"}
MODIFIER_ORDER = {
    "lctrl": 1, "ctrl": 2, "rctrl": 3,
    "lshift": 4, "shift": 5, "rshift": 6,
    "lalt": 7, "alt": 8, "ralt": 9,
    "lcmd": 10, "cmd": 11, "rcmd": 12,
}
DISPLAY_TOKEN = {
    "lctrl": "左Ctrl", "rctrl": "右Ctrl", "ctrl": "Ctrl",
    "lalt": "左Alt", "ralt": "右Alt", "alt": "Alt",
    "lshift": "左Shift", "rshift": "右Shift", "shift": "Shift",
    "lcmd": "左Win", "rcmd": "右Win", "cmd": "Win",
    "enter": "Enter", "esc": "Esc", "space": "Space", "tab": "Tab",
    "backspace": "Backspace", "delete": "Delete", "insert": "Insert",
    "page_up": "PgUp", "page_down": "PgDn", "home": "Home", "end": "End",
    "up": "↑", "down": "↓", "left": "←", "right": "→",
    "print_screen": "PrtSc", "caps_lock": "CapsLock",
}


class ThemePalette:
    def __init__(self, dark: bool):
        self.dark = dark
        self.bg = wx.Colour(32, 34, 37) if dark else wx.Colour(249, 250, 252)
        self.panel = wx.Colour(40, 43, 48) if dark else wx.Colour(255, 255, 255)
        self.soft = wx.Colour(48, 52, 58) if dark else wx.Colour(244, 246, 249)
        self.text = wx.Colour(238, 238, 238) if dark else wx.Colour(30, 34, 40)
        self.input = wx.Colour(53, 57, 64) if dark else wx.Colour(255, 255, 255)
        self.border = wx.Colour(74, 80, 88) if dark else wx.Colour(210, 215, 224)


def enable_hidpi() -> None:
    if not IS_WINDOWS:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def safe_read_json(path: Path, default: Dict) -> Dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return json.loads(json.dumps(default))


def safe_write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def open_path(path: Path) -> None:
    path = Path(path)
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def is_admin() -> bool:
    if not IS_WINDOWS:
        return os.getuid() == 0 if hasattr(os, "getuid") else False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def walk_children(win):
    for child in getattr(win, "GetChildren", lambda: [])() or []:
        yield child
        yield from walk_children(child)


def load_wx_icon() -> wx.Icon:
    for path in (ICON_ICO, ICON_PNG):
        if path.exists():
            try:
                icon = wx.Icon(str(path), wx.BITMAP_TYPE_ANY)
                if icon.IsOk():
                    return icon
            except Exception:
                pass
    return wx.ArtProvider.GetIcon(wx.ART_EXECUTABLE_FILE, wx.ART_FRAME_ICON, (32, 32))


def apply_window_icon(win) -> None:
    icon = load_wx_icon()
    if icon.IsOk():
        try:
            win.SetIcon(icon)
        except Exception:
            pass


def normalize_shortcut(text: str) -> str:
    tokens = []
    for raw in str(text).replace(" ", "").split("+"):
        token = TOKEN_ALIAS.get(raw.lower(), raw.lower())
        if token:
            tokens.append(token)
    seen = set()
    ordered = []
    for token in sorted(tokens, key=lambda x: (MODIFIER_ORDER.get(x, 100), x)):
        if token not in seen:
            ordered.append(token)
            seen.add(token)
    return "+".join(ordered)


def display_shortcut(text: str) -> str:
    parts = []
    for token in normalize_shortcut(text).split("+"):
        if not token:
            continue
        parts.append(DISPLAY_TOKEN.get(token, token.upper() if len(token) == 1 else token))
    return " + ".join(parts) if parts else "-"


def palette_from_theme(theme: str) -> ThemePalette:
    return ThemePalette(str(theme).lower() == "dark")


def apply_theme_to_window(win, theme: str = "light") -> None:
    palette = palette_from_theme(theme)
    all_windows = [win, *list(walk_children(win))]
    for child in all_windows:
        try:
            if isinstance(child, (wx.Frame, wx.Dialog)):
                child.SetBackgroundColour(palette.bg)
                child.SetForegroundColour(palette.text)
            elif isinstance(child, (wx.Panel, scrolled.ScrolledPanel, wx.Notebook)):
                child.SetBackgroundColour(palette.panel)
                child.SetForegroundColour(palette.text)
            elif isinstance(child, wx.ListCtrl):
                child.SetBackgroundColour(palette.input)
                child.SetForegroundColour(palette.text)
            elif isinstance(child, (wx.TextCtrl, wx.Choice, wx.SpinCtrl)):
                child.SetBackgroundColour(palette.input)
                child.SetForegroundColour(palette.text)
            elif isinstance(child, (wx.Button, wx.CheckBox, wx.RadioButton, wx.StaticBox)):
                child.SetBackgroundColour(palette.panel)
                child.SetForegroundColour(palette.text)
            elif isinstance(child, wx.StaticText):
                child.SetForegroundColour(palette.text)
        except Exception:
            pass
    try:
        if isinstance(win, wx.Frame):
            win.SetOwnBackgroundColour(palette.bg)
        win.Refresh()
        win.Update()
    except Exception:
        pass


def apply_fonts_to_window(win, family: str, base_size: int, header: Optional[wx.Window] = None) -> None:
    for child in [win, *list(walk_children(win))]:
        try:
            font = child.GetFont()
            if not font.IsOk():
                font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetFaceName(family)
            delta = 0
            if isinstance(child, wx.StaticText):
                delta = 1
            if isinstance(child, wx.ListCtrl):
                delta = 2
            if isinstance(child, (wx.Button, wx.Choice, wx.SpinCtrl, wx.TextCtrl)):
                delta = 1
            font.SetPointSize(max(9, base_size + delta))
            child.SetFont(font)
        except Exception:
            pass
    if header is not None:
        try:
            font = header.GetFont()
            font.SetFaceName(family)
            font.SetPointSize(base_size + 5)
            font.MakeBold()
            header.SetFont(font)
        except Exception:
            pass


@dataclass
class RuleRecord:
    id: str
    description: str
    trigger: str
    output: str
    count: int = 1
    max_interval: Optional[float] = 0.45
    block_source: bool = False
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict) -> "RuleRecord":
        trigger = data.get("trigger", "")
        output = data.get("output", "")
        if isinstance(trigger, list):
            trigger = "+".join(trigger)
        if isinstance(output, list):
            output = "+".join(output)
        try:
            count = max(1, int(data.get("count", 1)))
        except Exception:
            count = 1
        return cls(
            id=str(data.get("id", "")).strip(),
            description=str(data.get("description", "")).strip(),
            trigger=normalize_shortcut(str(trigger).strip()),
            output=normalize_shortcut(str(output).strip()),
            count=count,
            max_interval=data.get("max_interval", 0.45),
            block_source=bool(data.get("block_source", False)),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "trigger": self.trigger,
            "output": self.output,
            "count": int(self.count),
            "max_interval": self.max_interval,
            "block_source": bool(self.block_source),
            "enabled": bool(self.enabled),
        }


class ShortcutRecorderDialog(wx.Dialog):
    def __init__(self, parent, title: str, settings: Optional[Dict] = None):
        super().__init__(parent, title=title, size=(380, 240), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        apply_window_icon(self)
        self.settings = settings or {}
        self.tokens_in_order: List[str] = []
        self.current_down = set()
        self.result_value = ""
        self.finish_timer: Optional[wx.CallLater] = None
        self.last_input_ms = 0
        self.finished = False

        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        tip = wx.StaticText(panel, label="按下组合键，全部松开后会自动完成。\n如果系统没有正确上报松键，也会在短暂静止后自动保存。\n纯修饰键也可录制；双击次数请在规则里用“连击次数”设置。")
        tip.Wrap(340)
        root.Add(tip, 0, wx.ALL | wx.EXPAND, 12)

        self.preview = wx.StaticText(panel, label="等待输入…")
        root.Add(self.preview, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.clear_btn = wx.Button(panel, label="清空重录")
        self.ok_btn = wx.Button(panel, wx.ID_OK, "完成")
        self.cancel_btn = wx.Button(panel, wx.ID_CANCEL, "取消")
        btn_row.Add(self.clear_btn, 0, wx.RIGHT, 8)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self.ok_btn, 0, wx.RIGHT, 8)
        btn_row.Add(self.cancel_btn, 0)
        root.Add(btn_row, 0, wx.ALL | wx.EXPAND, 12)
        panel.SetSizer(root)

        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.on_manual_finish)
        panel.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)
        panel.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_KEY_UP, self.on_key_up)
        self.Bind(wx.EVT_SHOW, self.on_show)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self._apply_style()
        self.SetMinSize((360, 220))
        self.CenterOnParent()

    def _apply_style(self):
        apply_theme_to_window(self, self.settings.get("theme", "light"))
        base_size = int(self.settings.get("font_size", 11))
        apply_fonts_to_window(self, self.settings.get("font_family", DEFAULT_SETTINGS["font_family"]), base_size)
        try:
            f = self.preview.GetFont()
            f.SetPointSize(base_size + 4)
            f.MakeBold()
            self.preview.SetFont(f)
        except Exception:
            pass

    def _now_ms(self) -> int:
        return int(time.monotonic() * 1000)

    def on_show(self, event):
        if event.IsShown():
            wx.CallAfter(self.SetFocus)
            wx.CallAfter(self.Raise)
        event.Skip()

    def on_close(self, event):
        self._stop_finish_timer()
        event.Skip()

    def _stop_finish_timer(self):
        if self.finish_timer and self.finish_timer.IsRunning():
            self.finish_timer.Stop()
        self.finish_timer = None

    def schedule_finish(self, delay_ms: int = 260):
        self._stop_finish_timer()
        self.finish_timer = wx.CallLater(delay_ms, self.finish_if_ready)

    def finish_if_ready(self):
        if self.finished or not self.tokens_in_order:
            return
        idle_ms = self._now_ms() - self.last_input_ms
        modifiers_still_down = wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_SHIFT) or wx.GetKeyState(wx.WXK_ALT)
        if self.current_down and idle_ms < 350:
            self.schedule_finish(220)
            return
        if modifiers_still_down and idle_ms < 500:
            self.schedule_finish(220)
            return
        self._accept_result()

    def _accept_result(self):
        if self.finished:
            return
        value = normalize_shortcut("+".join(self.tokens_in_order))
        if not value:
            return
        self.finished = True
        self.result_value = value
        self._stop_finish_timer()
        if self.IsModal():
            wx.CallAfter(self.EndModal, wx.ID_OK)
        else:
            wx.CallAfter(self.Destroy)

    def _key_to_token(self, event: wx.KeyEvent) -> Optional[str]:
        code = event.GetKeyCode()
        uni = event.GetUnicodeKey()
        special = {
            wx.WXK_CONTROL: "ctrl",
            wx.WXK_SHIFT: "shift",
            wx.WXK_ALT: "alt",
            wx.WXK_WINDOWS_LEFT: "lcmd",
            wx.WXK_WINDOWS_RIGHT: "rcmd",
            wx.WXK_WINDOWS_MENU: "cmd",
            wx.WXK_RETURN: "enter",
            wx.WXK_NUMPAD_ENTER: "enter",
            wx.WXK_ESCAPE: "esc",
            wx.WXK_SPACE: "space",
            wx.WXK_TAB: "tab",
            wx.WXK_BACK: "backspace",
            wx.WXK_DELETE: "delete",
            wx.WXK_INSERT: "insert",
            wx.WXK_HOME: "home",
            wx.WXK_END: "end",
            wx.WXK_LEFT: "left",
            wx.WXK_RIGHT: "right",
            wx.WXK_UP: "up",
            wx.WXK_DOWN: "down",
            wx.WXK_PAGEUP: "page_up",
            wx.WXK_PAGEDOWN: "page_down",
            wx.WXK_NUMPAD0: "num0", wx.WXK_NUMPAD1: "num1", wx.WXK_NUMPAD2: "num2", wx.WXK_NUMPAD3: "num3",
            wx.WXK_NUMPAD4: "num4", wx.WXK_NUMPAD5: "num5", wx.WXK_NUMPAD6: "num6", wx.WXK_NUMPAD7: "num7",
            wx.WXK_NUMPAD8: "num8", wx.WXK_NUMPAD9: "num9",
            wx.WXK_NUMPAD_ADD: "num+", wx.WXK_NUMPAD_SUBTRACT: "num-", wx.WXK_NUMPAD_MULTIPLY: "num*", wx.WXK_NUMPAD_DIVIDE: "num/",
        }
        if wx.WXK_F1 <= code <= wx.WXK_F24:
            return f"f{code - wx.WXK_F1 + 1}"
        if code in special:
            return special[code]
        if 32 <= uni < 127:
            return chr(uni).lower()
        if ord("A") <= code <= ord("Z"):
            return chr(code).lower()
        if ord("0") <= code <= ord("9"):
            return chr(code)
        return None

    def _refresh_preview(self):
        text = normalize_shortcut("+".join(self.tokens_in_order))
        self.preview.SetLabel(display_shortcut(text) if text else "等待输入…")
        self.preview.Wrap(max(260, self.GetClientSize().Width - 36))
        self.Layout()

    def on_key_down(self, event: wx.KeyEvent):
        code = event.GetKeyCode()
        if code == wx.WXK_ESCAPE and not self.tokens_in_order:
            self._stop_finish_timer()
            self.EndModal(wx.ID_CANCEL)
            return
        if code == wx.WXK_BACK:
            self.on_clear(None)
            return
        token = self._key_to_token(event)
        if not token:
            event.Skip()
            return
        self.last_input_ms = self._now_ms()
        self._stop_finish_timer()
        self.current_down.add(token)
        if token not in self.tokens_in_order:
            self.tokens_in_order.append(token)
        self._refresh_preview()
        self.schedule_finish(520)

    def on_key_up(self, event: wx.KeyEvent):
        token = self._key_to_token(event)
        self.last_input_ms = self._now_ms()
        if token and token in self.current_down:
            self.current_down.discard(token)
        if not self.current_down and self.tokens_in_order:
            self.schedule_finish(220)
        else:
            self.schedule_finish(420)
        event.Skip()

    def on_manual_finish(self, _event):
        if not self.tokens_in_order:
            wx.MessageBox("请先录制一个快捷键。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        self._accept_result()

    def on_clear(self, _event):
        self.tokens_in_order.clear()
        self.current_down.clear()
        self.result_value = ""
        self.finished = False
        self.last_input_ms = 0
        self._stop_finish_timer()
        self._refresh_preview()


class RuleDialog(wx.Dialog):
    def __init__(self, parent, existing_ids: List[str], rule: Optional[RuleRecord] = None):
        super().__init__(parent, title="编辑规则" if rule else "新增规则", size=(470, 560), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        apply_window_icon(self)
        self.settings = getattr(parent, "settings", {})
        self.existing_ids = {x for x in existing_ids if not rule or x != rule.id}
        self.result: Optional[RuleRecord] = None

        panel = scrolled.ScrolledPanel(self)
        panel.SetupScrolling(scroll_x=False, rate_y=20)
        outer = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(0, 2, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.id_text = wx.TextCtrl(panel, value=rule.id if rule else "")
        self.desc_text = wx.TextCtrl(panel, value=rule.description if rule else "")
        self.trigger_text = wx.TextCtrl(panel, value=rule.trigger if rule else "")
        self.output_text = wx.TextCtrl(panel, value=rule.output if rule else "")
        self.count_spin = wx.SpinCtrl(panel, min=1, max=9, initial=(rule.count if rule else 2))
        self.use_interval = wx.CheckBox(panel, label="限制最大间隔")
        self.use_interval.SetValue(rule.max_interval is not None if rule else True)
        self.interval_text = wx.TextCtrl(panel, value=str(rule.max_interval if rule and rule.max_interval is not None else 0.45))
        self.block_check = wx.CheckBox(panel, label="尽量阻止原始按键")
        self.block_check.SetValue(rule.block_source if rule else False)
        self.enable_check = wx.CheckBox(panel, label="启用此规则")
        self.enable_check.SetValue(True if rule is None else rule.enabled)

        trigger_row = wx.BoxSizer(wx.HORIZONTAL)
        trigger_row.Add(self.trigger_text, 1, wx.RIGHT, 8)
        trigger_btn = wx.Button(panel, label="录制")
        trigger_row.Add(trigger_btn, 0)

        output_row = wx.BoxSizer(wx.HORIZONTAL)
        output_row.Add(self.output_text, 1, wx.RIGHT, 8)
        output_btn = wx.Button(panel, label="录制")
        output_row.Add(output_btn, 0)

        interval_row = wx.BoxSizer(wx.HORIZONTAL)
        interval_row.Add(self.use_interval, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 8)
        interval_row.Add(self.interval_text, 1)

        rows = [
            ("规则ID", self.id_text),
            ("规则说明", self.desc_text),
            ("触发键", trigger_row),
            ("输出键", output_row),
            ("连击次数", self.count_spin),
            ("最大间隔", interval_row),
        ]
        for label, ctrl in rows:
            grid.Add(wx.StaticText(panel, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        outer.Add(grid, 0, wx.ALL | wx.EXPAND, 14)
        outer.Add(self.block_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        outer.Add(self.enable_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        tip = wx.StaticText(panel, label="示例：ctrl / ctrl+alt+x / q。\n双击某个键请把“连击次数”设置为 2，而不是在录制窗口里按两次。")
        tip.Wrap(400)
        outer.Add(tip, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 14)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer(1)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "取消")
        ok_btn = wx.Button(panel, wx.ID_OK, "保存")
        btn_row.Add(cancel_btn, 0, wx.RIGHT, 8)
        btn_row.Add(ok_btn, 0)
        outer.Add(btn_row, 0, wx.ALL | wx.EXPAND, 14)

        panel.SetSizer(outer)
        trigger_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_recorder(self.trigger_text, "录制触发键"))
        output_btn.Bind(wx.EVT_BUTTON, lambda _e: self.open_recorder(self.output_text, "录制输出键"))
        self.use_interval.Bind(wx.EVT_CHECKBOX, self.on_toggle_interval)
        self.Bind(wx.EVT_BUTTON, self.on_submit, ok_btn)

        self.on_toggle_interval(None)
        self.SetMinSize((440, 500))
        apply_theme_to_window(self, self.settings.get("theme", "light"))
        apply_fonts_to_window(self, self.settings.get("font_family", DEFAULT_SETTINGS["font_family"]), int(self.settings.get("font_size", 11)))
        self.CenterOnParent()

    def open_recorder(self, target: wx.TextCtrl, title: str):
        dlg = ShortcutRecorderDialog(self, title, settings=self.settings)
        if dlg.ShowModal() == wx.ID_OK and dlg.result_value:
            target.SetValue(dlg.result_value)
        dlg.Destroy()

    def on_toggle_interval(self, _event):
        self.interval_text.Enable(self.use_interval.GetValue())

    def on_submit(self, _event):
        rule_id = self.id_text.GetValue().strip()
        trigger = normalize_shortcut(self.trigger_text.GetValue().strip())
        output = normalize_shortcut(self.output_text.GetValue().strip())
        if not rule_id:
            wx.MessageBox("请填写规则ID。", "提示", wx.OK | wx.ICON_WARNING, self)
            return
        if rule_id in self.existing_ids:
            wx.MessageBox(f"规则ID“{rule_id}”已存在。", "提示", wx.OK | wx.ICON_WARNING, self)
            return
        if not trigger or not output:
            wx.MessageBox("触发键和输出键不能为空。", "提示", wx.OK | wx.ICON_WARNING, self)
            return
        max_interval = None
        if self.use_interval.GetValue():
            try:
                max_interval = float(self.interval_text.GetValue())
                if max_interval <= 0:
                    raise ValueError
            except Exception:
                wx.MessageBox("最大间隔必须是大于0的数字。", "提示", wx.OK | wx.ICON_WARNING, self)
                return
        self.result = RuleRecord(
            id=rule_id,
            description=self.desc_text.GetValue().strip(),
            trigger=trigger,
            output=output,
            count=max(1, int(self.count_spin.GetValue())),
            max_interval=max_interval,
            block_source=self.block_check.GetValue(),
            enabled=self.enable_check.GetValue(),
        )
        self.EndModal(wx.ID_OK)


class SettingsFrame(wx.Frame):
    def __init__(
        self,
        config_path: str = "hotkeys.json",
        settings_path: str = "app_settings.json",
        on_rules_changed: Optional[Callable[[], None]] = None,
        on_settings_changed: Optional[Callable[[Dict], None]] = None,
        on_open_logs: Optional[Callable[[], None]] = None,
        on_open_config_dir: Optional[Callable[[], None]] = None,
        on_toggle_engine: Optional[Callable[[], None]] = None,
        on_reload_engine: Optional[Callable[[], None]] = None,
        on_set_startup: Optional[Callable[[bool], bool]] = None,
        on_restart_as_admin: Optional[Callable[[], None]] = None,
        get_runtime_status: Optional[Callable[[], Dict]] = None,
    ):
        super().__init__(None, title=f"{APP_NAME} 设置", size=(WINDOW_W, WINDOW_H), style=wx.DEFAULT_FRAME_STYLE | wx.RESIZE_BORDER)
        apply_window_icon(self)
        self.SetMinSize((MIN_W, MIN_H))
        self.config_path = Path(config_path)
        self.settings_path = Path(settings_path)
        self.on_rules_changed = on_rules_changed
        self.on_settings_changed = on_settings_changed
        self.on_open_logs = on_open_logs
        self.on_open_config_dir = on_open_config_dir
        self.on_toggle_engine = on_toggle_engine
        self.on_reload_engine = on_reload_engine
        self.on_set_startup = on_set_startup
        self.on_restart_as_admin = on_restart_as_admin
        self.get_runtime_status = get_runtime_status or (lambda: {"running": False, "status_text": "未运行"})
        self.settings = {**DEFAULT_SETTINGS, **safe_read_json(self.settings_path, DEFAULT_SETTINGS)}
        self.rules: List[RuleRecord] = self.load_rules()

        self._apply_window_geometry()
        self._build_ui()
        self.apply_visuals()
        self.refresh_runtime_status()

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def _apply_window_geometry(self):
        w = max(MIN_W, int(self.settings.get("window_width", WINDOW_W)))
        h = max(MIN_H, int(self.settings.get("window_height", WINDOW_H)))
        self.SetSize((w, h))
        style = self.GetWindowStyleFlag()
        if self.settings.get("window_topmost"):
            style |= wx.STAY_ON_TOP
        else:
            style &= ~wx.STAY_ON_TOP
        self.SetWindowStyleFlag(style)

    def apply_visuals(self):
        apply_theme_to_window(self, self.settings.get("theme", "light"))
        apply_fonts_to_window(
            self,
            self.settings.get("font_family", DEFAULT_SETTINGS["font_family"]),
            max(10, int(self.settings.get("font_size", 11))),
            header=getattr(self, "title_label", None),
        )
        self._refresh_wraps()
        self.Layout()
        self.SendSizeEvent()
        self.Refresh()
        self.Update()

    def _refresh_wraps(self):
        wrap_width = max(300, self.GetClientSize().Width - 70)
        for name in ("admin_label", "rule_detail", "about_hint"):
            ctrl = getattr(self, name, None)
            if ctrl is not None:
                try:
                    ctrl.Wrap(wrap_width)
                except Exception:
                    pass

    def _font(self, delta=0, bold=False):
        size = max(9, int(self.settings.get("font_size", 11)) + delta)
        return wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL, False, self.settings.get("font_family", DEFAULT_SETTINGS["font_family"]))

    def _make_scrolled_page(self, notebook: wx.Notebook) -> scrolled.ScrolledPanel:
        page = scrolled.ScrolledPanel(notebook)
        page.SetupScrolling(scroll_x=False, rate_y=20)
        page.SetSizer(wx.BoxSizer(wx.VERTICAL))
        return page

    def _section(self, parent, title: str, hint: str = ""):
        box = wx.StaticBox(parent, label=title)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        if hint:
            hint_text = wx.StaticText(parent, label=hint)
            hint_text.Wrap(360)
            sizer.Add(hint_text, 0, wx.ALL | wx.EXPAND, 10)
        parent.GetSizer().Add(sizer, 0, wx.ALL | wx.EXPAND, 8)
        return sizer

    def _build_ui(self):
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.BoxSizer(wx.HORIZONTAL)
        self.title_label = wx.StaticText(panel, label=APP_NAME)
        self.runtime_label = wx.StaticText(panel, label="未运行")
        header.Add(self.title_label, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        header.Add(self.runtime_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)
        root.Add(header, 0, wx.EXPAND)

        self.notebook = wx.Notebook(panel)
        self.general_page = self._build_general_page(self.notebook)
        self.appearance_page = self._build_appearance_page(self.notebook)
        self.rules_page = self._build_rules_page(self.notebook)
        self.about_page = self._build_about_page(self.notebook)
        self.notebook.AddPage(self.general_page, "常规")
        self.notebook.AddPage(self.appearance_page, "外观")
        self.notebook.AddPage(self.rules_page, "规则")
        self.notebook.AddPage(self.about_page, "关于")
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_changed)
        root.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 8)
        panel.SetSizer(root)

    def _build_general_page(self, notebook):
        page = self._make_scrolled_page(notebook)
        sec = self._section(page, "启动与行为", "保持功能完整，同时尽量降低配置难度。")
        self.cb_auto_start = wx.CheckBox(page, label="启动程序后自动运行映射引擎")
        self.cb_minimize_to_tray = wx.CheckBox(page, label="启动时隐藏到托盘")
        self.cb_close_to_tray = wx.CheckBox(page, label="关闭窗口时隐藏到托盘")
        self.cb_topmost = wx.CheckBox(page, label="设置窗口置顶")
        self.cb_launch_at_startup = wx.CheckBox(page, label="开机自启动")
        self.cb_run_as_admin = wx.CheckBox(page, label="优先以管理员权限运行")
        self.cb_start_minimized = wx.CheckBox(page, label="启动时不弹出设置页")
        for cb, key in [
            (self.cb_auto_start, "auto_start_engine"),
            (self.cb_minimize_to_tray, "minimize_to_tray"),
            (self.cb_close_to_tray, "close_to_tray"),
            (self.cb_topmost, "window_topmost"),
            (self.cb_launch_at_startup, "launch_at_startup"),
            (self.cb_run_as_admin, "run_as_admin"),
            (self.cb_start_minimized, "start_minimized"),
        ]:
            cb.SetValue(bool(self.settings.get(key, DEFAULT_SETTINGS[key])))
            sec.Add(cb, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
            cb.Bind(wx.EVT_CHECKBOX, self.on_general_changed)

        row = wx.BoxSizer(wx.HORIZONTAL)
        btn_toggle = wx.Button(page, label="启动/暂停")
        btn_reload = wx.Button(page, label="重载规则")
        row.Add(btn_toggle, 0, wx.RIGHT, 8)
        row.Add(btn_reload, 0)
        sec.Add(row, 0, wx.ALL, 8)
        btn_toggle.Bind(wx.EVT_BUTTON, lambda _e: self._call(self.on_toggle_engine))
        btn_reload.Bind(wx.EVT_BUTTON, lambda _e: self._call(self.on_reload_engine))

        sec2 = self._section(page, "文件与日志")
        self.choice_log_level = wx.Choice(page, choices=["关闭", "追踪", "调试", "普通"])
        self.choice_log_level.SetStringSelection(str(self.settings.get("log_level", "普通")))
        sec2.Add(wx.StaticText(page, label="日志级别"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        sec2.Add(self.choice_log_level, 0, wx.ALL | wx.EXPAND, 8)
        self.choice_log_level.Bind(wx.EVT_CHOICE, lambda _e: self.save_settings())
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        btn_logs = wx.Button(page, label="打开日志目录")
        btn_dir = wx.Button(page, label="打开程序目录")
        row2.Add(btn_logs, 0, wx.RIGHT, 8)
        row2.Add(btn_dir, 0)
        sec2.Add(row2, 0, wx.ALL, 8)
        btn_logs.Bind(wx.EVT_BUTTON, lambda _e: self.handle_open_logs())
        btn_dir.Bind(wx.EVT_BUTTON, lambda _e: self.handle_open_config_dir())

        sec3 = self._section(page, "状态提示")
        self.admin_label = wx.StaticText(page, label=self._admin_text())
        sec3.Add(self.admin_label, 0, wx.ALL | wx.EXPAND, 8)
        return page

    def _build_appearance_page(self, notebook):
        page = self._make_scrolled_page(notebook)
        sec = self._section(page, "主题与字体", "主题和字号会立即作用到主页面与弹窗。")
        sec.Add(wx.StaticText(page, label="主题"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.choice_theme = wx.Choice(page, choices=["light", "dark"])
        self.choice_theme.SetStringSelection(str(self.settings.get("theme", "light")))
        sec.Add(self.choice_theme, 0, wx.ALL | wx.EXPAND, 8)
        self.choice_theme.Bind(wx.EVT_CHOICE, lambda _e: self.save_settings(rebuild=True))

        sec.Add(wx.StaticText(page, label="字体"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        choices = ["Microsoft YaHei UI", "Segoe UI", "Arial", "PingFang SC", "Noto Sans CJK SC"]
        self.choice_font_family = wx.Choice(page, choices=sorted(choices))
        family = str(self.settings.get("font_family", DEFAULT_SETTINGS["font_family"]))
        if family not in choices:
            family = DEFAULT_SETTINGS["font_family"]
        self.choice_font_family.SetStringSelection(family)
        sec.Add(self.choice_font_family, 0, wx.ALL | wx.EXPAND, 8)
        self.choice_font_family.Bind(wx.EVT_CHOICE, lambda _e: self.save_settings(rebuild=True))

        sec.Add(wx.StaticText(page, label="字号"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.spin_font_size = wx.SpinCtrl(page, min=9, max=20, initial=int(self.settings.get("font_size", 11)))
        sec.Add(self.spin_font_size, 0, wx.ALL | wx.EXPAND, 8)
        self.spin_font_size.Bind(wx.EVT_SPINCTRL, lambda _e: self.save_settings(rebuild=True))

        sec2 = self._section(page, "图标", "窗口、关于页与托盘统一优先使用当前目录下的 icon.ico / icon.png。")
        self.rb_default_icon = wx.RadioButton(page, label="使用程序目录图标", style=wx.RB_GROUP)
        self.rb_custom_icon = wx.RadioButton(page, label="自定义图标")
        self.rb_default_icon.SetValue(self.settings.get("tray_icon_mode", "default") != "custom")
        self.rb_custom_icon.SetValue(self.settings.get("tray_icon_mode", "default") == "custom")
        self.icon_path = wx.TextCtrl(page, value=str(self.settings.get("custom_icon_path", "")))
        btn_pick = wx.Button(page, label="选择")
        sec2.Add(self.rb_default_icon, 0, wx.ALL, 8)
        sec2.Add(self.rb_custom_icon, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.icon_path, 1, wx.RIGHT, 8)
        row.Add(btn_pick, 0)
        sec2.Add(row, 0, wx.ALL | wx.EXPAND, 8)
        self.rb_default_icon.Bind(wx.EVT_RADIOBUTTON, lambda _e: self.save_settings())
        self.rb_custom_icon.Bind(wx.EVT_RADIOBUTTON, lambda _e: self.save_settings())
        self.icon_path.Bind(wx.EVT_TEXT, lambda _e: self.save_settings())
        btn_pick.Bind(wx.EVT_BUTTON, self.pick_icon)
        return page

    def _build_rules_page(self, notebook):
        page = self._make_scrolled_page(notebook)
        sec = self._section(page, "规则列表", "进入本页会直接读取 hotkeys.json，双击可编辑。")
        wrap = wx.WrapSizer(wx.HORIZONTAL, wx.WRAPSIZER_DEFAULT_FLAGS)
        for label, handler in [("新增", self.add_rule), ("编辑", self.edit_selected_rule), ("删除", self.delete_selected_rule), ("启停", self.toggle_selected_rule), ("刷新", self.reload_rules_from_file)]:
            btn = wx.Button(page, label=label)
            btn.Bind(wx.EVT_BUTTON, lambda _e, fn=handler: fn())
            wrap.Add(btn, 0, wx.RIGHT | wx.BOTTOM, 8)
        sec.Add(wrap, 0, wx.ALL | wx.EXPAND, 8)

        self.rule_list = wx.ListCtrl(page, style=wx.LC_REPORT | wx.BORDER_THEME | wx.LC_SINGLE_SEL)
        self.rule_list.InsertColumn(0, "状态", width=60)
        self.rule_list.InsertColumn(1, "ID", width=120)
        self.rule_list.InsertColumn(2, "触发", width=170)
        self.rule_list.InsertColumn(3, "连击", width=55)
        self.rule_list.SetMinSize((-1, 260))
        sec.Add(self.rule_list, 1, wx.ALL | wx.EXPAND, 8)
        self.rule_list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda _e: self.update_rule_detail())
        self.rule_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self.edit_selected_rule())

        btn_save_reload = wx.Button(page, label="保存并重载")
        btn_save_reload.Bind(wx.EVT_BUTTON, lambda _e: self.save_and_reload_engine())
        sec.Add(btn_save_reload, 0, wx.ALL | wx.ALIGN_RIGHT, 8)

        sec2 = self._section(page, "所选规则详情")
        self.rule_detail = wx.StaticText(page, label="选择一条规则后显示详情。")
        sec2.Add(self.rule_detail, 0, wx.ALL | wx.EXPAND, 8)
        self.populate_rules()
        return page

    def _build_about_page(self, notebook):
        page = self._make_scrolled_page(notebook)
        sec = self._section(page, APP_NAME, "一款快捷键替换软件，解决部分软件无法更换快捷键的问题")
        sec.Add(wx.StaticText(page, label=f"版本 {APP_VERSION}\n构建日期 {BUILD_DATE}"), 0, wx.ALL, 8)
        btn_copy = wx.Button(page, label="复制邮箱")
        btn_copy.Bind(wx.EVT_BUTTON, lambda _e: self.copy_text("pengxiaoyou435@gmail.com"))
        sec.Add(btn_copy, 0, wx.ALL, 8)
        sec2 = self._section(page, "说明")
        self.about_hint = wx.StaticText(page, label="本软件可能存在bug，可以尽情反馈")
        sec2.Add(self.about_hint, 0, wx.ALL | wx.EXPAND, 8)
        return page

    def _call(self, fn):
        if callable(fn):
            fn()

    def _admin_text(self):
        return "当前已是管理员权限。" if is_admin() else "当前不是管理员权限。某些键盘拦截场景建议启用管理员权限运行。"

    def on_general_changed(self, event):
        source = event.GetEventObject()
        if source is self.cb_launch_at_startup:
            enabled = self.cb_launch_at_startup.GetValue()
            ok = self._call_startup(enabled)
            if not ok and enabled:
                self.cb_launch_at_startup.SetValue(False)
                wx.MessageBox("开机自启动设置失败，请检查权限。", "设置失败", wx.OK | wx.ICON_WARNING, self)
                return
        if source is self.cb_run_as_admin and self.cb_run_as_admin.GetValue() and not is_admin() and callable(self.on_restart_as_admin):
            if wx.MessageBox("下次重启将以管理员权限运行。是否现在立即重启程序？", "管理员权限", wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
                self.on_restart_as_admin()
                return
        self.save_settings(rebuild=(source is self.cb_topmost))
        self.admin_label.SetLabel(self._admin_text())
        self._refresh_wraps()

    def _call_startup(self, enabled: bool) -> bool:
        if callable(self.on_set_startup):
            try:
                return bool(self.on_set_startup(enabled))
            except Exception:
                return False
        return not enabled

    def on_page_changed(self, event):
        if self.notebook.GetSelection() == 2:
            self.reload_rules_from_file()
        event.Skip()

    def on_size(self, event):
        size = self.GetSize()
        self.settings["window_width"] = max(MIN_W, size.Width)
        self.settings["window_height"] = max(MIN_H, size.Height)
        self._refresh_wraps()
        event.Skip()

    def save_settings(self, rebuild: bool = False):
        self.settings.update({
            "auto_start_engine": self.cb_auto_start.GetValue(),
            "minimize_to_tray": self.cb_minimize_to_tray.GetValue(),
            "close_to_tray": self.cb_close_to_tray.GetValue(),
            "start_minimized": self.cb_start_minimized.GetValue(),
            "window_topmost": self.cb_topmost.GetValue(),
            "launch_at_startup": self.cb_launch_at_startup.GetValue(),
            "run_as_admin": self.cb_run_as_admin.GetValue(),
            "log_level": self.choice_log_level.GetStringSelection() or self.settings.get("log_level"),
            "theme": self.choice_theme.GetStringSelection() or self.settings.get("theme"),
            "font_family": self.choice_font_family.GetStringSelection() or self.settings.get("font_family"),
            "font_size": self.spin_font_size.GetValue(),
            "tray_icon_mode": "custom" if self.rb_custom_icon.GetValue() else "default",
            "custom_icon_path": self.icon_path.GetValue().strip(),
        })
        safe_write_json(self.settings_path, self.settings)
        self._apply_window_geometry()
        if callable(self.on_settings_changed):
            self.on_settings_changed(dict(self.settings))
        if rebuild:
            self.apply_visuals()

    def load_rules(self) -> List[RuleRecord]:
        data = safe_read_json(self.config_path, DEFAULT_RULES)
        return [RuleRecord.from_dict(item) for item in data.get("rules", []) if isinstance(item, dict)]

    def reload_rules_from_file(self):
        self.rules = self.load_rules()
        self.populate_rules()

    def save_rules(self):
        safe_write_json(self.config_path, {"rules": [r.to_dict() for r in self.rules]})
        if callable(self.on_rules_changed):
            self.on_rules_changed()

    def populate_rules(self):
        if not hasattr(self, "rule_list"):
            return
        self.rule_list.DeleteAllItems()
        for idx, rule in enumerate(self.rules):
            self.rule_list.InsertItem(idx, "开" if rule.enabled else "关")
            self.rule_list.SetItem(idx, 1, rule.id)
            self.rule_list.SetItem(idx, 2, display_shortcut(rule.trigger))
            self.rule_list.SetItem(idx, 3, str(rule.count))
        self.update_rule_detail()

    def get_selected_index(self) -> int:
        return self.rule_list.GetFirstSelected() if hasattr(self, "rule_list") else -1

    def get_selected_rule(self) -> Optional[RuleRecord]:
        idx = self.get_selected_index()
        return self.rules[idx] if 0 <= idx < len(self.rules) else None

    def update_rule_detail(self):
        rule = self.get_selected_rule()
        if not rule:
            self.rule_detail.SetLabel("选择一条规则后显示详情。")
            self._refresh_wraps()
            return
        interval = "不限" if rule.max_interval is None else f"{rule.max_interval:.2f}s"
        self.rule_detail.SetLabel(
            f"说明：{rule.description or '无'}\n"
            f"触发：{display_shortcut(rule.trigger)}\n"
            f"输出：{display_shortcut(rule.output)}\n"
            f"连击：{rule.count}\n"
            f"间隔：{interval}\n"
            f"block_source：{'是' if rule.block_source else '否'}"
        )
        self._refresh_wraps()

    def add_rule(self):
        dlg = RuleDialog(self, [r.id for r in self.rules])
        if dlg.ShowModal() == wx.ID_OK and dlg.result:
            self.rules.append(dlg.result)
            self.save_rules()
            self.populate_rules()
        dlg.Destroy()

    def edit_selected_rule(self):
        rule = self.get_selected_rule()
        if not rule:
            wx.MessageBox("请先选择一条规则。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        dlg = RuleDialog(self, [r.id for r in self.rules], rule=rule)
        if dlg.ShowModal() == wx.ID_OK and dlg.result:
            self.rules[self.get_selected_index()] = dlg.result
            self.save_rules()
            self.populate_rules()
        dlg.Destroy()

    def delete_selected_rule(self):
        rule = self.get_selected_rule()
        idx = self.get_selected_index()
        if not rule:
            wx.MessageBox("请先选择一条规则。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        if wx.MessageBox(f"确定删除“{rule.id}”吗？", "删除规则", wx.YES_NO | wx.ICON_QUESTION, self) == wx.YES:
            self.rules.pop(idx)
            self.save_rules()
            self.populate_rules()

    def toggle_selected_rule(self):
        rule = self.get_selected_rule()
        if not rule:
            wx.MessageBox("请先选择一条规则。", "提示", wx.OK | wx.ICON_INFORMATION, self)
            return
        rule.enabled = not rule.enabled
        self.save_rules()
        self.populate_rules()

    def save_and_reload_engine(self):
        self.save_rules()
        if callable(self.on_reload_engine):
            self.on_reload_engine()
            wx.MessageBox("规则已保存并重载。", "已完成", wx.OK | wx.ICON_INFORMATION, self)
        else:
            wx.MessageBox("规则已保存。", "已保存", wx.OK | wx.ICON_INFORMATION, self)

    def handle_open_logs(self):
        if callable(self.on_open_logs):
            self.on_open_logs()
        else:
            open_path(BASE_DIR / "logs")

    def handle_open_config_dir(self):
        if callable(self.on_open_config_dir):
            self.on_open_config_dir()
        else:
            open_path(BASE_DIR)

    def pick_icon(self, _event):
        with wx.FileDialog(self, "选择图标", wildcard="图标文件 (*.ico;*.png)|*.ico;*.png|所有文件 (*.*)|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.icon_path.SetValue(dlg.GetPath())
                self.rb_custom_icon.SetValue(True)
                self.save_settings()

    def refresh_runtime_status(self):
        status = self.get_runtime_status() or {}
        self.runtime_label.SetLabel(status.get("status_text", "未运行"))
        self.Layout()

    def copy_text(self, text: str):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        wx.MessageBox(text, "已复制", wx.OK | wx.ICON_INFORMATION, self)

    def on_close(self, event):
        self.save_settings()
        if self.settings.get("close_to_tray", True):
            self.Hide()
            event.Veto()
        else:
            event.Skip()


class SettingsApp:
    def __init__(self, root=None, **kwargs):
        enable_hidpi()
        self.wx_app = wx.App(False)
        self.frame = SettingsFrame(**kwargs)

    def show(self):
        self.frame.Show()
        self.frame.Raise()
        self.frame.refresh_runtime_status()

    def run(self):
        if not self.frame.settings.get("start_minimized", False):
            self.show()
        self.wx_app.MainLoop()


if __name__ == "__main__":
    SettingsApp().run()
