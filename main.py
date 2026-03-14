import json
import os
import platform
import signal
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from pynput import keyboard

DEBUG = True
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_FILE = str((BASE_DIR / "hotkeys.json").resolve())
SYSTEM = platform.system().lower()
kb_controller = keyboard.Controller()

MODIFIER_GENERIC_MAP = {
    "lctrl": "ctrl",
    "rctrl": "ctrl",
    "lalt": "alt",
    "ralt": "alt",
    "lshift": "shift",
    "rshift": "shift",
    "lcmd": "cmd",
    "rcmd": "cmd",
}


def debug(*args):
    if DEBUG:
        print("[DEBUG]", *args)


def normalize_token_name(token: str) -> str:
    t = token.strip().lower()
    alias_map = {
        "control": "ctrl",
        "ctl": "ctrl",
        "option": "alt",
        "shft": "shift",
        "win": "cmd",
        "super": "cmd",
        "command": "cmd",
        "meta": "cmd",
        "lwin": "lcmd",
        "rwin": "rcmd",
        "lsuper": "lcmd",
        "rsuper": "rcmd",
        "lmeta": "lcmd",
        "rmeta": "rcmd",
    }
    return alias_map.get(t, t)


def normalize_pynput_key(key) -> Optional[str]:
    if hasattr(key, "char") and key.char is not None:
        return key.char.lower()

    if key == keyboard.Key.ctrl_l:
        return "lctrl"
    if key == keyboard.Key.ctrl_r:
        return "rctrl"
    if key == keyboard.Key.alt_l:
        return "lalt"
    if key == keyboard.Key.alt_r:
        return "ralt"
    if key == keyboard.Key.shift_l:
        return "lshift"
    if key == keyboard.Key.shift_r:
        return "rshift"
    if key == keyboard.Key.cmd_l:
        return "lcmd"
    if key == keyboard.Key.cmd_r:
        return "rcmd"

    if key == keyboard.Key.ctrl:
        return "ctrl"
    if key == keyboard.Key.alt or key == keyboard.Key.alt_gr:
        return "alt"
    if key == keyboard.Key.shift:
        return "shift"
    if key == keyboard.Key.cmd:
        return "cmd"

    special_map = {
        keyboard.Key.enter: "enter",
        keyboard.Key.space: "space",
        keyboard.Key.tab: "tab",
        keyboard.Key.esc: "esc",
        keyboard.Key.backspace: "backspace",
        keyboard.Key.delete: "delete",
        keyboard.Key.up: "up",
        keyboard.Key.down: "down",
        keyboard.Key.left: "left",
        keyboard.Key.right: "right",
        keyboard.Key.home: "home",
        keyboard.Key.end: "end",
        keyboard.Key.page_up: "page_up",
        keyboard.Key.page_down: "page_down",
        keyboard.Key.insert: "insert",
        keyboard.Key.caps_lock: "caps_lock",
        keyboard.Key.menu: "menu",
        keyboard.Key.print_screen: "print_screen",
        keyboard.Key.pause: "pause",
        keyboard.Key.num_lock: "num_lock",
        keyboard.Key.f1: "f1",
        keyboard.Key.f2: "f2",
        keyboard.Key.f3: "f3",
        keyboard.Key.f4: "f4",
        keyboard.Key.f5: "f5",
        keyboard.Key.f6: "f6",
        keyboard.Key.f7: "f7",
        keyboard.Key.f8: "f8",
        keyboard.Key.f9: "f9",
        keyboard.Key.f10: "f10",
        keyboard.Key.f11: "f11",
        keyboard.Key.f12: "f12",
    }
    return special_map.get(key, None)


def canonicalize_combo_tokens(tokens: List[str]) -> Tuple[str, ...]:
    normalized = [normalize_token_name(x) for x in tokens if x.strip()]
    return tuple(sorted(normalized))


def combo_str_to_tuple(combo_str: str) -> Tuple[str, ...]:
    return canonicalize_combo_tokens(combo_str.split("+"))


def combo_variants(combo: Tuple[str, ...]) -> List[Tuple[str, ...]]:
    variants = {tuple(sorted(combo))}
    current = {tuple(sorted(combo))}
    for _ in range(len(combo)):
        next_round = set()
        for item in current:
            for i, token in enumerate(item):
                generic = MODIFIER_GENERIC_MAP.get(token)
                if generic and generic != token:
                    replaced = list(item)
                    replaced[i] = generic
                    next_round.add(tuple(sorted(replaced)))
        next_round -= variants
        if not next_round:
            break
        variants |= next_round
        current = next_round
    return sorted(variants, key=lambda x: (sum(1 for t in x if t in MODIFIER_GENERIC_MAP), len(x)))


def output_name_to_key(name: str):
    name = normalize_token_name(name)
    key_map = {
        "ctrl": keyboard.Key.ctrl,
        "lctrl": keyboard.Key.ctrl_l,
        "rctrl": keyboard.Key.ctrl_r,
        "alt": keyboard.Key.alt,
        "lalt": keyboard.Key.alt_l,
        "ralt": keyboard.Key.alt_r,
        "shift": keyboard.Key.shift,
        "lshift": keyboard.Key.shift_l,
        "rshift": keyboard.Key.shift_r,
        "cmd": keyboard.Key.cmd,
        "lcmd": keyboard.Key.cmd_l,
        "rcmd": keyboard.Key.cmd_r,
        "enter": keyboard.Key.enter,
        "space": keyboard.Key.space,
        "tab": keyboard.Key.tab,
        "esc": keyboard.Key.esc,
        "backspace": keyboard.Key.backspace,
        "delete": keyboard.Key.delete,
        "up": keyboard.Key.up,
        "down": keyboard.Key.down,
        "left": keyboard.Key.left,
        "right": keyboard.Key.right,
        "home": keyboard.Key.home,
        "end": keyboard.Key.end,
        "page_up": keyboard.Key.page_up,
        "page_down": keyboard.Key.page_down,
        "insert": keyboard.Key.insert,
        "caps_lock": keyboard.Key.caps_lock,
        "menu": keyboard.Key.menu,
        "print_screen": keyboard.Key.print_screen,
        "pause": keyboard.Key.pause,
        "num_lock": keyboard.Key.num_lock,
        "f1": keyboard.Key.f1,
        "f2": keyboard.Key.f2,
        "f3": keyboard.Key.f3,
        "f4": keyboard.Key.f4,
        "f5": keyboard.Key.f5,
        "f6": keyboard.Key.f6,
        "f7": keyboard.Key.f7,
        "f8": keyboard.Key.f8,
        "f9": keyboard.Key.f9,
        "f10": keyboard.Key.f10,
        "f11": keyboard.Key.f11,
        "f12": keyboard.Key.f12,
    }
    if name in key_map:
        return key_map[name]
    if len(name) == 1:
        return name
    raise ValueError(f"不支持的输出键名: {name}")


def simulate_shortcut(output_combo: Tuple[str, ...]):
    modifier_names = {
        "ctrl", "lctrl", "rctrl", "alt", "lalt", "ralt", "shift", "lshift", "rshift", "cmd", "lcmd", "rcmd"
    }
    modifiers = []
    normals = []
    for name in output_combo:
        key_obj = output_name_to_key(name)
        if name in modifier_names:
            modifiers.append(key_obj)
        else:
            normals.append(key_obj)

    debug("simulate:", "+".join(output_combo))
    try:
        for m in modifiers:
            kb_controller.press(m)
        if normals:
            for n in normals:
                kb_controller.press(n)
            for n in reversed(normals):
                kb_controller.release(n)
    finally:
        for m in reversed(modifiers):
            try:
                kb_controller.release(m)
            except Exception:
                pass


@dataclass
class Rule:
    id: str
    trigger: Tuple[str, ...]
    output: Tuple[str, ...]
    count: int = 1
    max_interval: Optional[float] = 0.45
    block_source: bool = False
    enabled: bool = True
    description: str = ""


@dataclass
class Stroke:
    combo: Tuple[str, ...]
    timestamp: float


class StrokeHistory:
    def __init__(self):
        self.data: Dict[Tuple[str, ...], deque] = {}

    def add(self, combo: Tuple[str, ...], ts: float):
        if combo not in self.data:
            self.data[combo] = deque()
        self.data[combo].append(ts)

    def clear_combo(self, combo: Tuple[str, ...]):
        if combo in self.data:
            self.data[combo].clear()

    def clear(self):
        self.data.clear()

    def prune(self, combo: Tuple[str, ...], max_interval: Optional[float], now: Optional[float] = None):
        if combo not in self.data or max_interval is None:
            return
        now = time.time() if now is None else now
        dq = self.data[combo]
        while dq and now - dq[0] > max_interval:
            dq.popleft()

    def matched(self, combo: Tuple[str, ...], count: int, max_interval: Optional[float]) -> bool:
        if combo not in self.data:
            return False
        dq = self.data[combo]
        if len(dq) < count:
            return False
        recent = list(dq)[-count:]
        if max_interval is None:
            return True
        return (recent[-1] - recent[0]) <= max_interval


def load_rules(config_path: str) -> List[Rule]:
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rules = []
    for idx, item in enumerate(data.get("rules", []), 1):
        trigger = item["trigger"]
        output = item["output"]
        trigger_tuple = combo_str_to_tuple(trigger) if isinstance(trigger, str) else canonicalize_combo_tokens(trigger)
        output_tuple = combo_str_to_tuple(output) if isinstance(output, str) else canonicalize_combo_tokens(output)
        rules.append(
            Rule(
                id=str(item.get("id", f"rule_{idx}")),
                trigger=trigger_tuple,
                output=output_tuple,
                count=max(1, int(item.get("count", 1))),
                max_interval=item.get("max_interval", 0.45),
                block_source=bool(item.get("block_source", False)),
                enabled=bool(item.get("enabled", True)),
                description=item.get("description", ""),
            )
        )
    return rules


DEFAULT_CONFIG = {
    "rules": [
        {
            "id": "double_qw_to_ctrl_win_u",
            "description": "双击 q+w 输出 ctrl+cmd+u（Windows/Linux 上 cmd 可理解为 Win）",
            "trigger": "q+w",
            "output": "ctrl+cmd+u",
            "count": 2,
            "max_interval": 0.45,
            "block_source": False,
            "enabled": True,
        },
        {
            "id": "double_lctrl_to_lctrl_alt_x",
            "description": "双击左Ctrl输出左Ctrl+Alt+X",
            "trigger": "lctrl",
            "output": "lctrl+alt+x",
            "count": 2,
            "max_interval": 0.35,
            "block_source": True,
            "enabled": True,
        },
    ]
}


def ensure_default_config(path: str):
    try:
        with open(path, "r", encoding="utf-8"):
            return
    except FileNotFoundError:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"已生成默认配置文件: {path}")


class HotkeyMapper:
    def __init__(self, rules: List[Rule]):
        self.lock = threading.RLock()
        self.pressed_keys: Set[str] = set()
        self.current_combo: Set[str] = set()
        self.history = StrokeHistory()
        self.ignore_until = 0.0
        self.rules: List[Rule] = []
        self.has_blocking_rules = False
        self.index_by_trigger: Dict[Tuple[str, ...], List[Rule]] = {}
        self.reload_rules(rules, announce=False)
        self.report_capability()

    def reload_rules(self, rules: List[Rule], announce: bool = True):
        enabled_rules = [r for r in rules if r.enabled]
        index: Dict[Tuple[str, ...], List[Rule]] = {}
        for r in enabled_rules:
            index.setdefault(r.trigger, []).append(r)
        for trigger in index:
            index[trigger].sort(key=lambda x: x.count, reverse=True)
        with self.lock:
            self.rules = enabled_rules
            self.index_by_trigger = index
            self.has_blocking_rules = any(r.block_source for r in enabled_rules)
            self.history.clear()
        if announce:
            print(f"[RELOAD] 已重载规则，启用 {len(enabled_rules)} 条。")

    def report_capability(self):
        print("=" * 60)
        print("Hotkey Mapper 启动")
        print(f"系统: {SYSTEM}")
        print(f"规则数: {len(self.rules)}")
        print("说明:")
        print("  - 匹配/连击/左右键区分/输出模拟：已启用")
        print("  - 原始输入拦截(block_source)：受平台限制")
        print("      Windows: 需更底层钩子库才可靠")
        print("      Linux  : X11 下一般可用，Wayland 下可能受限")
        print("      macOS  : 需辅助功能权限")
        print("  - 当前代码默认统一走 pynput，block_source 为“逻辑支持 + 接口预留”")
        print("=" * 60)

    def should_ignore_event(self) -> bool:
        return time.time() < self.ignore_until

    def on_press(self, key):
        if self.should_ignore_event():
            return
        name = normalize_pynput_key(key)
        if not name or name in self.pressed_keys:
            return
        self.pressed_keys.add(name)
        self.current_combo.add(name)
        debug("press   ", name, "pressed:", self.pressed_keys, "combo:", self.current_combo)

    def on_release(self, key):
        if self.should_ignore_event():
            return
        name = normalize_pynput_key(key)
        if not name:
            return
        if name in self.pressed_keys:
            self.pressed_keys.remove(name)
        debug("release ", name, "pressed:", self.pressed_keys)
        if not self.pressed_keys and self.current_combo:
            combo = tuple(sorted(self.current_combo))
            self.current_combo.clear()
            debug("stroke complete:", combo)
            self.handle_stroke(combo)

    def handle_stroke(self, combo: Tuple[str, ...]):
        ts = time.time()
        candidates = combo_variants(combo)
        debug("stroke variants:", candidates)
        with self.lock:
            for candidate in candidates:
                self.history.add(candidate, ts)
            matched_rule = None
            for candidate in candidates:
                rules = self.index_by_trigger.get(candidate, [])
                if not rules:
                    continue
                for rule in rules:
                    self.history.prune(candidate, rule.max_interval, now=ts)
                for rule in rules:
                    if self.history.matched(candidate, rule.count, rule.max_interval):
                        matched_rule = rule
                        break
                if matched_rule:
                    break
            if matched_rule:
                print(f"[MATCH] {matched_rule.id}: {matched_rule.trigger} x{matched_rule.count} -> {matched_rule.output}")
                for candidate in candidates:
                    self.history.clear_combo(candidate)
        if matched_rule:
            self.fire_rule(matched_rule)

    def fire_rule(self, rule: Rule):
        self.ignore_until = time.time() + 0.08
        if rule.block_source:
            print(f"[INFO] 规则 {rule.id} 要求 block_source=True")
            print("[INFO] 当前统一 pynput 后端下，只能尽量不重复触发，无法保证系统完全收不到原键。")
        simulate_shortcut(rule.output)

    def run(self, stop_event: threading.Event):
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            while not stop_event.is_set():
                listener.join(0.5)
            listener.stop()


class ConfigWatcher(threading.Thread):
    def __init__(self, config_path: str, mapper: HotkeyMapper, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.config_path = Path(config_path)
        self.mapper = mapper
        self.stop_event = stop_event
        self.last_signature = self._signature()

    def _signature(self):
        try:
            stat = self.config_path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except FileNotFoundError:
            return None

    def run(self):
        while not self.stop_event.wait(0.8):
            sig = self._signature()
            if sig == self.last_signature:
                continue
            self.last_signature = sig
            try:
                ensure_default_config(str(self.config_path))
                rules = load_rules(str(self.config_path))
                self.mapper.reload_rules(rules)
                print(f"[RELOAD] 检测到配置文件变化: {self.config_path}")
            except Exception as e:
                print(f"[WARN] 重新加载配置失败: {e}")


def resolve_config_path(argv: Optional[List[str]] = None) -> str:
    argv = list(sys.argv[1:] if argv is None else argv)
    config_path = DEFAULT_CONFIG_FILE
    positional = [x for x in argv if x and not x.startswith("-")]
    if positional:
        config_path = positional[0]
    config_path = os.environ.get("KEYTWIST_CONFIG", config_path)
    return str(Path(config_path).resolve())


def main_entry(argv: Optional[List[str]] = None) -> int:
    config_path = resolve_config_path(argv)
    ensure_default_config(config_path)
    rules = load_rules(config_path)
    print(f"当前配置文件: {config_path}")
    print("加载到的规则:")
    for r in rules:
        print(
            f"  - {r.id}: trigger={'+'.join(r.trigger)}, output={'+'.join(r.output)}, "
            f"count={r.count}, max_interval={r.max_interval}, block_source={r.block_source}, enabled={r.enabled}"
        )

    mapper = HotkeyMapper(rules)
    stop_event = threading.Event()
    watcher = ConfigWatcher(config_path, mapper, stop_event)
    watcher.start()

    def _handle_stop(_signum=None, _frame=None):
        stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                signal.signal(sig, _handle_stop)
            except Exception:
                pass

    try:
        mapper.run(stop_event)
    finally:
        stop_event.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main_entry())
