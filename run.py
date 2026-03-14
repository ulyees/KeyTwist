import ctypes
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

import pystray
from PIL import Image, ImageDraw

from gui import APP_NAME, DEFAULT_SETTINGS, SettingsApp, enable_hidpi, is_admin

IS_FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
RUN_TARGET = Path(sys.executable).resolve() if IS_FROZEN else Path(__file__).resolve()
MAIN_FILE = BASE_DIR / "main.py"
CONFIG_FILE = BASE_DIR / "hotkeys.json"
SETTINGS_FILE = BASE_DIR / "app_settings.json"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "keytwist.log"
ICON_ICO = BASE_DIR / "icon.ico"
ICON_PNG = BASE_DIR / "icon.png"
SYSTEM = sys.platform


# ---------- engine mode entry for packaged/source runs ----------
def maybe_run_engine_mode() -> bool:
    if "--engine" not in sys.argv:
        return False
    argv = [x for x in sys.argv[1:] if x != "--engine"]
    from main import main_entry

    raise SystemExit(main_entry(argv))


maybe_run_engine_mode()


def show_info_dialog(message: str, title: str = APP_NAME) -> None:
    try:
        import wx

        app = wx.App(False)
        wx.MessageBox(message, title, wx.OK | wx.ICON_INFORMATION)
        app.Destroy()
    except Exception:
        print(message)


class SingleInstanceIPC:
    def __init__(self, token: str, on_show):
        self.token = token
        self.on_show = on_show
        self.server_socket: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        base = abs(hash((str(BASE_DIR), APP_NAME))) % 20000
        self.port = 35000 + base

    def start_or_notify_existing(self) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", self.port))
            sock.listen(5)
            self.server_socket = sock
            self.thread = threading.Thread(target=self._serve, daemon=True)
            self.thread.start()
            return True
        except OSError:
            try:
                sock.close()
            except Exception:
                pass
            return self._notify_existing()

    def _notify_existing(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=1.2) as client:
                client.sendall(f"SHOW {self.token}\n".encode("utf-8"))
                client.shutdown(socket.SHUT_WR)
                return True
        except OSError:
            return False

    def _serve(self) -> None:
        assert self.server_socket is not None
        while not self.stop_event.is_set():
            try:
                self.server_socket.settimeout(0.5)
                conn, _addr = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                data = conn.recv(1024).decode("utf-8", errors="ignore").strip()
                if data == f"SHOW {self.token}":
                    self.on_show()
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    def close(self) -> None:
        self.stop_event.set()
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None


class KeyTwistRunner:
    def __init__(self):
        enable_hidpi()
        self.settings = self.load_settings()
        self.engine_process: Optional[subprocess.Popen] = None
        self.engine_log_handle = None
        self.icon: Optional[pystray.Icon] = None
        self.quitting = False
        self.ipc = SingleInstanceIPC(token=self._instance_token(), on_show=self._show_from_ipc)
        self.app = SettingsApp(
            config_path=str(CONFIG_FILE),
            settings_path=str(SETTINGS_FILE),
            on_rules_changed=self.on_rules_changed,
            on_settings_changed=self.on_settings_changed,
            on_open_logs=self.open_logs_dir,
            on_open_config_dir=self.open_config_dir,
            on_toggle_engine=self.toggle_engine,
            on_reload_engine=self.restart_engine,
            on_set_startup=self.set_launch_at_startup,
            on_restart_as_admin=self.restart_as_admin,
            get_runtime_status=self.get_runtime_status,
        )

    def _instance_token(self) -> str:
        return f"{APP_NAME}:{BASE_DIR}"

    def load_settings(self) -> Dict:
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
        return dict(DEFAULT_SETTINGS)

    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def on_settings_changed(self, settings: Dict):
        self.settings = {**DEFAULT_SETTINGS, **settings}
        self.save_settings()
        self.update_tray_menu()
        self.update_tray_icon_title()
        self.refresh_tray_icon_image()

    def on_rules_changed(self):
        self.write_log(f"规则文件已更新，将重载引擎。配置文件：{CONFIG_FILE}")
        self.restart_engine()

    def write_log(self, message: str):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line)
        print(line.rstrip())

    def create_default_icon(self) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 59, 59), radius=14, fill=(47, 109, 246, 255))
        draw.text((18, 17), "KT", fill="white")
        return image

    def load_icon(self) -> Image.Image:
        paths = []
        if self.settings.get("tray_icon_mode") == "custom":
            custom = self.settings.get("custom_icon_path", "").strip()
            if custom:
                paths.append(Path(custom))
        paths.extend([ICON_ICO, ICON_PNG])
        for path in paths:
            if path.exists():
                try:
                    return Image.open(path)
                except Exception as e:
                    self.write_log(f"图标加载失败 {path.name}: {e}")
        return self.create_default_icon()

    def refresh_tray_icon_image(self):
        if self.icon:
            try:
                self.icon.icon = self.load_icon()
            except Exception as e:
                self.write_log(f"刷新托盘图标失败：{e}")

    def get_runtime_status(self) -> Dict:
        running = self.engine_process is not None and self.engine_process.poll() is None
        admin_note = "（管理员）" if is_admin() else ""
        return {"running": running, "status_text": ("运行中" if running else "已停止") + admin_note}

    def update_tray_icon_title(self):
        if self.icon:
            self.icon.title = f"{APP_NAME} - {self.get_runtime_status()['status_text']}"

    def _ensure_log_stream(self):
        if self.engine_log_handle and not self.engine_log_handle.closed:
            return self.engine_log_handle
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.engine_log_handle = LOG_FILE.open("a", encoding="utf-8")
        return self.engine_log_handle

    def _refresh_gui_runtime_status(self):
        try:
            if hasattr(self.app, "frame") and hasattr(self.app.frame, "refresh_runtime_status"):
                self.app.frame.refresh_runtime_status()
        except Exception as e:
            self.write_log(f"刷新界面运行状态失败：{e}")

    def _build_app_command(self, extra_args=None):
        extra_args = extra_args or []
        if IS_FROZEN:
            return [str(RUN_TARGET), *extra_args]
        return [sys.executable, str(RUN_TARGET), *extra_args]

    def start_engine(self):
        if self.engine_process and self.engine_process.poll() is None:
            self.write_log("热键引擎已在运行，无需重复启动。")
            return

        config_path = str(CONFIG_FILE.resolve())
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["KEYTWIST_CONFIG"] = config_path

        creationflags = 0
        startupinfo = None
        if SYSTEM.startswith("win"):
            creationflags = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        cmd = self._build_app_command(["--engine", config_path])
        try:
            self.engine_process = subprocess.Popen(
                cmd,
                cwd=str(BASE_DIR),
                stdout=self._ensure_log_stream(),
                stderr=self._ensure_log_stream(),
                stdin=subprocess.DEVNULL,
                env=env,
                creationflags=creationflags,
                startupinfo=startupinfo,
            )
            self.write_log(f"热键引擎已启动，PID={self.engine_process.pid}，配置={config_path}")
        except Exception as e:
            self.engine_process = None
            self.write_log(f"热键引擎启动失败：{e}")

        self.update_tray_menu()
        self.update_tray_icon_title()
        self._refresh_gui_runtime_status()

    def stop_engine(self):
        proc = self.engine_process
        if not proc or proc.poll() is not None:
            self.engine_process = None
            self.update_tray_menu()
            self.update_tray_icon_title()
            self._refresh_gui_runtime_status()
            return

        try:
            if SYSTEM.startswith("win"):
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=2.5)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=1)
            except Exception:
                pass

        self.engine_process = None
        self.write_log("热键引擎已停止。")
        self.update_tray_menu()
        self.update_tray_icon_title()
        self._refresh_gui_runtime_status()

    def restart_engine(self):
        self.write_log("正在重载热键引擎...")
        self.stop_engine()
        time.sleep(0.2)
        self.start_engine()

    def toggle_engine(self):
        if self.get_runtime_status()["running"]:
            self.stop_engine()
        else:
            self.start_engine()

    def _show_from_ipc(self):
        try:
            import wx

            wx.CallAfter(self.show_settings)
        except Exception:
            self.show_settings()

    def show_settings(self):
        if hasattr(self.app, "show"):
            self.app.show()
        elif hasattr(self.app, "frame"):
            self.app.frame.Show()
            try:
                self.app.frame.Raise()
            except Exception:
                pass

    def open_logs_dir(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.open_path(LOG_DIR)

    def open_config_dir(self):
        self.open_path(BASE_DIR)

    def open_path(self, path: Path):
        try:
            if SYSTEM.startswith("win"):
                os.startfile(str(path))
            elif SYSTEM == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.write_log(f"打开目录失败：{e}")

    def build_menu(self):
        running = self.get_runtime_status()["running"]
        return pystray.Menu(
            pystray.MenuItem("打开设置", lambda icon, item: self.show_settings(), default=True),
            pystray.MenuItem("暂停映射" if running else "启动映射", lambda icon, item: self.toggle_engine()),
            pystray.MenuItem("重载规则", lambda icon, item: self.restart_engine()),
            pystray.MenuItem("打开日志目录", lambda icon, item: self.open_logs_dir()),
            pystray.MenuItem("退出", lambda icon, item: self.quit_app()),
        )

    def update_tray_menu(self):
        if self.icon:
            self.icon.menu = self.build_menu()
            try:
                self.icon.update_menu()
            except Exception:
                pass

    def setup_tray(self):
        self.icon = pystray.Icon(
            APP_NAME,
            icon=self.load_icon(),
            title=f"{APP_NAME} - {self.get_runtime_status()['status_text']}",
            menu=self.build_menu(),
        )
        try:
            self.icon.run_detached()
        except Exception:
            threading.Thread(target=self.icon.run, daemon=True).start()

    def _windows_startup_path(self) -> Path:
        startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return startup_dir / f"{APP_NAME}.cmd"

    def _linux_autostart_path(self) -> Path:
        return Path.home() / ".config" / "autostart" / f"{APP_NAME.lower()}.desktop"

    def _mac_launch_agent_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"com.keytwist.{APP_NAME.lower()}.plist"

    def _launch_command_string(self) -> str:
        return " ".join(shlex.quote(part) for part in self._build_app_command())

    def set_launch_at_startup(self, enabled: bool) -> bool:
        try:
            if SYSTEM.startswith("win"):
                target = self._windows_startup_path()
                if enabled:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if IS_FROZEN:
                        cmd = f'@echo off\r\ncd /d "{BASE_DIR}"\r\nstart "" "{RUN_TARGET}"\r\n'
                    else:
                        cmd = f'@echo off\r\ncd /d "{BASE_DIR}"\r\nstart "" "{sys.executable}" "{RUN_TARGET}"\r\n'
                    target.write_text(cmd, encoding="gbk", errors="ignore")
                elif target.exists():
                    target.unlink()
                self.write_log("已{}开机自启动。".format("启用" if enabled else "关闭"))
                return True

            if SYSTEM == "darwin":
                target = self._mac_launch_agent_path()
                if enabled:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    args = self._build_app_command()
                    plist = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\"><dict>
<key>Label</key><string>com.keytwist.keytwist</string>
<key>ProgramArguments</key><array>{args}</array>
<key>RunAtLoad</key><true/>
<key>WorkingDirectory</key><string>{cwd}</string>
</dict></plist>
""".format(
                        args="".join(f"<string>{part}</string>" for part in args),
                        cwd=BASE_DIR,
                    )
                    target.write_text(plist, encoding="utf-8")
                elif target.exists():
                    target.unlink()
                self.write_log("已{}登录启动。".format("启用" if enabled else "关闭"))
                return True

            target = self._linux_autostart_path()
            if enabled:
                target.parent.mkdir(parents=True, exist_ok=True)
                desktop = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    f"Name={APP_NAME}\n"
                    f"Exec={self._launch_command_string()}\n"
                    f"Path={BASE_DIR}\n"
                    "Terminal=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                target.write_text(desktop, encoding="utf-8")
            elif target.exists():
                target.unlink()
            self.write_log("已{}登录启动。".format("启用" if enabled else "关闭"))
            return True
        except Exception as e:
            self.write_log(f"设置开机自启动失败：{e}")
            return False

    def restart_as_admin(self):
        try:
            if SYSTEM.startswith("win"):
                if is_admin():
                    return
                params = " ".join(f'"{x}"' for x in self._build_app_command()[1:])
                ctypes.windll.shell32.ShellExecuteW(None, "runas", self._build_app_command()[0], params, str(BASE_DIR), 1)
                self.quit_app()
                return

            if SYSTEM == "darwin":
                command = self._launch_command_string()
                apple = f'do shell script {command!r} with administrator privileges'
                subprocess.Popen(["osascript", "-e", apple], cwd=str(BASE_DIR))
                self.quit_app()
                return

            launcher = None
            for name in ("pkexec", "gksudo", "kdesu"):
                if shutil.which(name):
                    launcher = name
                    break
            if launcher == "pkexec":
                subprocess.Popen([launcher, *self._build_app_command()], cwd=str(BASE_DIR))
                self.quit_app()
                return
            self.write_log("当前 Linux 环境未找到可用的提权启动器（pkexec/gksudo/kdesu）。")
        except Exception as e:
            self.write_log(f"管理员重启失败：{e}")

    def quit_app(self):
        if self.quitting:
            return
        self.quitting = True
        self.stop_engine()
        self.ipc.close()
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
        try:
            if self.engine_log_handle and not self.engine_log_handle.closed:
                self.engine_log_handle.close()
        except Exception:
            pass
        try:
            import wx
            if hasattr(self.app, "frame"):
                wx.CallAfter(self.app.frame.Destroy)
        except Exception:
            pass

    def bootstrap(self):
        if not self.ipc.start_or_notify_existing():
            show_info_dialog("程序已经在运行，已尝试打开现有窗口。", APP_NAME)
            raise SystemExit(0)

        if not CONFIG_FILE.exists():
            self.write_log("未发现 hotkeys.json，可在设置页直接新建规则。")
        self.setup_tray()
        if self.settings.get("auto_start_engine", True):
            self.start_engine()
        if not self.settings.get("start_minimized", False) and not self.settings.get("minimize_to_tray", True):
            self.show_settings()

    def run(self):
        self.bootstrap()
        try:
            self.app.run()
        finally:
            self.quit_app()


if __name__ == "__main__":
    import shutil

    KeyTwistRunner().run()
