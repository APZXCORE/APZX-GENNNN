import os
import sys
import json
import re
import subprocess
import time
import threading
from collections import deque

# ──── Pre-check imports before anything else ────
try:
    from flask import Flask, render_template, send_from_directory
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    print("[APZX] ERROR: Flask not installed. Run: pip install flask")
    sys.exit(1)

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

# ──── Environment ────
if os.name == "nt":
    os.system("")  # Enable ANSI on Windows
    try:
        import ctypes
        myappid = 'apzx.genbot.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Precompiled ANSI escape stripper for terminal output
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

# ──── Flask (minimal, just serves the template) ────
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'gui_templates'),
    static_folder=os.path.join(BASE_DIR, 'gui_static')
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/app-icon')
def app_icon():
    return send_from_directory(ASSETS_DIR, 'apzx_icon.webp', mimetype='image/webp')

@app.route('/health')
def health():
    return 'OK', 200



class WindowController:

    __slots__ = ('_log_buf', '_log_lock', 'current_process', '_reader', '_status_lock', 'status')

    def __init__(self):
        self._log_buf = deque(maxlen=5000)  # Ring buffer – never grows unbounded
        self._log_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self.status = {
            "progress": 0,
            "success": 0,
            "failed": 0,
            "pending": 0,
            "total": 0
        }
        self.current_process = None
        self._reader = None

    # ──── Config I/O ────
    def load_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self._push(f"[!] Config load error: {e}\n")
            return {}

    def save_config(self, cfg_dict):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg_dict, f, indent=4)
            self._push("[✓] Config saved.\n")
            return True
        except Exception as e:
            self._push(f"[!] Config save error: {e}\n")
            return False

    def save_theme(self, hex_color: str):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        cfg["theme_accent"] = hex_color
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            return True
        except Exception:
            return False

    # ──── Input/Output Files I/O ────
    def get_input_files(self):
        try:
            files = []
            for d in ["input", "output"]:
                target_dir = os.path.join(BASE_DIR, d)
                if os.path.isdir(target_dir):
                    for f in os.listdir(target_dir):
                        if f.endswith('.txt'):
                            files.append(f"{d}/{f}")
            return files
        except Exception:
            return []

    def read_input_file(self, filename: str):
        try:
            # Reconstruct absolute path
            path = os.path.abspath(os.path.join(BASE_DIR, filename))
            expected_in = os.path.abspath(os.path.join(BASE_DIR, "input"))
            expected_out = os.path.abspath(os.path.join(BASE_DIR, "output"))

            if not (path.startswith(expected_in) or path.startswith(expected_out)):
                return ""

            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            return ""
        except Exception:
            return ""

    def save_input_file(self, filename: str, content: str):
        try:
            path = os.path.abspath(os.path.join(BASE_DIR, filename))
            expected_in = os.path.abspath(os.path.join(BASE_DIR, "input"))
            expected_out = os.path.abspath(os.path.join(BASE_DIR, "output"))

            if not (path.startswith(expected_in) or path.startswith(expected_out)):
                return False

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._push(f"[✓] Saved data to {filename}\n")
            return True
        except Exception as e:
            self._push(f"[!] Error saving {filename}: {e}\n")
            return False

    # ──── Logging ────
    def _push(self, msg: str):
        with self._log_lock:
            self._log_buf.append(msg)

    def get_logs(self):
        with self._log_lock:
            if not self._log_buf:
                return None
            out = "".join(self._log_buf)
            self._log_buf.clear()
            return out

    # ──── Window Controls ────
    def close(self):
        self.stop_process()
        if HAS_WEBVIEW:
            for w in webview.windows:
                w.destroy()

    def minimize(self):
        if HAS_WEBVIEW:
            for w in webview.windows:
                w.minimize()

    # ──── Process Management ────
    _TARGETS = {
        "generator":     (lambda bd: ([sys.executable, "main.py"], bd)),
        "auth_joiner":   (lambda bd: (["node", "src/index.js"], os.path.join(bd, "engine", "auth_joiner"))),
        "link_joiner":   (lambda bd: ([sys.executable, "engine/joiner.py"], bd)),
        "checker":       (lambda bd: ([sys.executable, "engine/checker.py"], bd)),
        "onliner":       (lambda bd: ([sys.executable, "engine/onliner.py"], bd)),
        "proxy_checker": (lambda bd: ([sys.executable, "engine/proxy_checker.py"], bd)),
        "setup":         (lambda bd: ([sys.executable, "-c",
            "import os, sys, subprocess\n"
            "print('[APZX] Installing dependencies...')\n"
            "subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])\n"
            "auth_dir = os.path.join('engine', 'auth_joiner')\n"
            "if os.path.exists(auth_dir):\n"
            "    print('[APZX] Installing Auth Joiner Node modules...')\n"
            "    subprocess.run(['npm', 'i'], cwd=auth_dir, shell=True)\n"
            "print('[APZX] Setup complete!')\n"
        ], bd)),
        "uninstall_setup": (lambda bd: ([sys.executable, "-c",
            "import os, sys, subprocess\n"
            "print('[APZX] Removing Python dependencies...')\n"
            "subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', '-r', 'requirements.txt'])\n"
            "auth_dir = os.path.join('engine', 'auth_joiner')\n"
            "node_modules = os.path.join(auth_dir, 'node_modules')\n"
            "if os.path.exists(node_modules):\n"
            "    print('[APZX] Removing Auth Joiner Node modules...')\n"
            "    subprocess.run('rmdir /s /q \"' + node_modules + '\"' if os.name == 'nt' else 'rm -rf \"' + node_modules + '\"', shell=True)\n"
            "pkg_lock = os.path.join(auth_dir, 'package-lock.json')\n"
            "if os.path.exists(pkg_lock): os.remove(pkg_lock)\n"
            "print('[APZX] Uninstall complete!')\n"
        ], bd)),
    }

    def start_process(self, target: str, data: str = None):
        if self.current_process and self.current_process.poll() is None:
            self._push("[!] A process is already running. Stop it first.\n")
            return

        with self._status_lock:
            self.status = {"progress": 0, "success": 0, "failed": 0, "pending": 0, "total": 0, "engine": target}

        resolver = self._TARGETS.get(target)
        if not resolver:
            self._push(f"[!] Unknown target: {target}\n")
            return

        cmd, cwd = resolver(BASE_DIR)

        if target == "link_joiner" and data:
            cmd.extend(["--gui-invite", data])

        try:
            kwargs = {}
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["GUI_MODE"] = "1"

            if os.name == "nt":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs["startupinfo"] = si

            self.current_process = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                bufsize=1,
                text=True,
                encoding='utf-8',
                errors='ignore',
                env=env,
                **kwargs
            )

            self._reader = threading.Thread(target=self._drain, daemon=True)
            self._reader.start()
        except Exception as e:
            self._push(f"[!] Launch failed ({target}): {e}\n")

    def _parse_status(self, text: str):
        with self._status_lock:
            if text.startswith("GUI_STAT:"):
                try:
                    parts = text.split("GUI_STAT:")[1].strip().split(",")
                    if len(parts) >= 7:
                        gen, ver, cap_solved, cap_fail, locked, valid, total = map(int, parts[:7])
                        self.status["success"] = gen
                        self.status["failed"] = valid + locked
                        self.status["total"] = total
                        self.status["ver"] = ver
                        self.status["cap_solved"] = cap_solved
                        self.status["cap_fail"] = cap_fail
                        if total > 0:
                            self.status["progress"] = int(((gen + valid + locked) / total) * 100)
                except Exception:
                    pass
                return

            # Look for progress pattern (e.g. 15% or [==  ] 15%)
            prog_match = re.search(r'(\d+)%', text)
            if prog_match:
                try:
                    self.status["progress"] = int(prog_match.group(1))
                except ValueError:
                    pass

            # Skip summary lines and setup logs
            if not ("Joined       :" in text or "Failed       :" in text or "Invalid      :" in text or "Captchas     :" in text or "Output saved to" in text or "X-Context-Properties loaded" in text):
                # Count success markers
                if "✓" in text or "OK" in text or "Success" in text or "working" in text.lower():
                    self.status["success"] += 1
                # Count failure markers
                elif "BLOCKED" in text:
                    self.status.setdefault("blocked", 0)
                    self.status["blocked"] += 1
                elif "✗" in text or "DEAD" in text or "Failed" in text or "Error" in text:
                    self.status["failed"] += 1

            # If total items log exists
            if self.status.get("engine") == "proxy_checker":
                tot_match = re.search(r'Proxies:\s*(\d+)', text, re.IGNORECASE)
            else:
                tot_match = re.search(r'(?:Tokens:|Checking)\s*(\d+)', text, re.IGNORECASE)

            if tot_match:
                try:
                    self.status["total"] = int(tot_match.group(1))
                except ValueError:
                    pass

    def _drain(self):
        proc = self.current_process
        if not proc:
            return
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break

                clean_text = _ANSI_RE.sub('', line)
                if clean_text.startswith("GUI_STAT:"):
                    self._parse_status(clean_text)
                    continue

                raw_text = line.replace('\r', '')
                self._push(raw_text)
                self._parse_status(clean_text)
        except Exception:
            pass
        finally:
            if proc:
                rc = proc.wait()
                self._push(f"\n[-] Exited with code {rc}.\n")
                self.current_process = None

    def get_status_updates(self):
        with self._status_lock:
            # calculate pending
            if self.status["total"] > 0:
                self.status["pending"] = max(0, self.status["total"] - (self.status["success"] + self.status["failed"]))
            res = self.status.copy()
            res["is_running"] = self.current_process is not None
            return res

    def stop_process(self):
        proc = self.current_process
        if proc and proc.poll() is None:
            self._push("[*] Killing process…\n")
            proc.kill()
            self.current_process = None


# ──── Entry Point ────
if __name__ == "__main__":
    controller = WindowController()

    # Start Flask in background (silent — suppress dev server warnings)
    import logging
    logging.getLogger('werkzeug').setLevel(logging.CRITICAL)

    # Find a free port (start at 5001)
    import socket
    def _find_free_port(start=5001, count=10):
        for port in range(start, start + count):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', port))
                    return port
                except OSError:
                    continue
        return start

    _PORT = _find_free_port(5001)

    def _run_flask():
        app.run(host='127.0.0.1', port=_PORT, debug=False, use_reloader=False)

    flask_thread = threading.Thread(target=_run_flask, daemon=True)
    flask_thread.start()

    # Wait for Flask to be ready (retry up to 5s)
    import urllib.request
    ready = False
    for _ in range(50):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{_PORT}/health', timeout=0.2)
            ready = True
            break
        except Exception:
            time.sleep(0.1)
    if not ready:
        print(f"[APZX] [!] Flask failed to start on port {_PORT}")
        sys.exit(1)

    url = f"http://127.0.0.1:{_PORT}"
    print(f"[APZX] Flask ready on port {_PORT}")
    import webbrowser

    # Try pywebview first
    if HAS_WEBVIEW:
        try:
            webview.create_window(
                title="APZX G3NNNN v1.0",
                url=url,
                js_api=controller,
                width=1100,
                height=720,
                frameless=False,
                resizable=True,
            )
            # Prefer edgechromium on Windows, default on other OS
            gui = "edgechromium" if sys.platform == "win32" else None
            webview.start(debug=False, gui=gui)
        except Exception as e:
            webbrowser.open(url)
    else:
        webbrowser.open(url)
    # Keep script alive so Flask doesn't die
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.close()
        sys.exit(0)
