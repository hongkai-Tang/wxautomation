# wechat_taskbar_awaken_send.py
# Title: WeChat Taskbar Awaken & Send
# Activate a minimized (independent) WeChat chat window by title (or via the Taskbar's
# "Task switching" list) and send a text message. Designed to avoid flicker and only
# use the taskbar path when strictly necessary.
#
# Public API:
#   send_wechat_message_to_minimized_chat(chat_title: str, text: str, timeout: float = 5.0) -> bool
#
# Usage example:
#   from wechat_taskbar_awaken_send import send_wechat_message_to_minimized_chat
#   ok = send_wechat_message_to_minimized_chat("测试3群", "Hello from automation!")
#   print("OK" if ok else "Failed")

from typing import Optional
import time
import re

# Required
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

# Optional (better restore/foreground on some systems)
try:
    import win32gui, win32con  # type: ignore
    _HAS_PYWIN32 = True
except Exception:
    _HAS_PYWIN32 = False

# Optional (safer text paste for CJK/emoji/long texts)
try:
    import pyperclip  # type: ignore
    _HAS_PYPERCLIP = True
except Exception:
    _HAS_PYPERCLIP = False


# ---------- Internal helpers ----------

def _try_activate_chat_by_title(chat_name: str) -> bool:
    """
    First choice: directly find the independent chat window by title and bring it front.
    - Matches exact "群名" or "群名 - 微信".
    - If minimized, attempts to restore; if visible, only foreground/focus (no flicker).
    """
    # A) UIA path
    try:
        desk = Desktop(backend="uia")
        w = desk.window(title_re=rf"^{re.escape(chat_name)}(\s*-\s*微信)?$", control_type="Window")
        if w.exists(timeout=0.5):
            try:
                try:
                    w.restore()
                except Exception:
                    pass
                w.set_focus()
                w.set_foreground()
                return True
            except Exception:
                pass
    except Exception:
        pass

    # B) Win32 fallback (optional)
    if _HAS_PYWIN32:
        try:
            targets = []
            def _enum_cb(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and (title == chat_name or title.startswith(chat_name)):
                        targets.append(hwnd)
            win32gui.EnumWindows(_enum_cb, None)
            for hwnd in targets:
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.05)
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                except Exception:
                    continue
        except Exception:
            pass

    return False


def _activate_chat_via_taskbar(chat_name: str, timeout: float = 4.0) -> bool:
    """
    点击任务栏“微信”→打开任务切换列表→点击目标聊天项。
    兼容：列表标题缺失 / 列表延迟出现 / 列表项在其它容器内。
    """
    desk = Desktop(backend="uia")

    # 1) 定位任务栏
    try:
        taskbar = desk.window(class_name="Shell_TrayWnd")
        if not taskbar.exists():
            taskbar = desk.window(title_re="任务栏|Taskbar", control_type="Pane")
    except Exception:
        taskbar = None
    if not taskbar or not taskbar.exists():
        return False

    # 2) 找任务栏上的“微信”按钮/菜单项（Win10/11兼容）
    wx_btn = None
    for patt in (r"^微信", r"WeChat"):
        try:
            wx_btn = taskbar.child_window(title_re=patt, control_type="Button")
            if wx_btn.exists(): break
        except Exception:
            wx_btn = None
    if not wx_btn or not wx_btn.exists():
        try:
            # 兼容 “微信-3个运行窗口”/“WeChat - 3 windows”等
            wx_btn = taskbar.child_window(title_re=r"微信.*运行窗口|WeChat.*windows", control_type="MenuItem")
        except Exception:
            wx_btn = None
    if not wx_btn or not wx_btn.exists():
        # 最后兜底：在任务栏下所有后代里搜名字里带“微信/WeChat”的可见元素
        try:
            for ctrl in taskbar.descendants():
                name = (getattr(ctrl, 'window_text', lambda: "")() or "").strip()
                if name and (name.startswith("微信") or name.startswith("WeChat")):
                    wx_btn = ctrl
                    break
        except Exception:
            pass
    if not wx_btn or not wx_btn.exists():
        return False

    # 3) 点击任务栏“微信”以展开任务切换列表
    try:
        wx_btn.set_focus()
    except Exception:
        pass
    wx_btn.click_input()
    time.sleep(0.1)

    # 4) 等“任务切换”列表；若找不到标题，就全局找目标 ListItem
    t0 = time.time()
    while time.time() - t0 < timeout:
        # 4.1 优先找有标题的列表
        try:
            lst = desk.window(title_re="任务切换程序|Task switching|Task View", control_type="List")
            if lst.exists():
                item = lst.child_window(title_re=rf"{re.escape(chat_name)}.*", control_type="ListItem")
                if item.exists():
                    item.click_input()
                    return True
        except Exception:
            pass

        # 4.2 兜底：全桌面直接搜列表项（有些系统列表无标题）
        try:
            item = desk.child_window(title_re=rf"{re.escape(chat_name)}.*", control_type="ListItem")
            if item.exists():
                item.click_input()
                return True
        except Exception:
            pass

        time.sleep(0.1)

    return False



def _paste_and_send_text(text: str) -> bool:
    """
    Paste the text and send Enter. Prefer clipboard (handles CJK/emoji/long text).
    Fallback to direct typing if clipboard lib not available.
    """
    try:
        if _HAS_PYPERCLIP:
            pyperclip.copy(text)
            time.sleep(0.05)
            # Ctrl+V then Enter
            send_keys("^v")
            time.sleep(0.05)
            send_keys("{ENTER}")
            return True
        else:
            # Direct typing fallback (may be impacted by IME)
            send_keys(text, with_spaces=True, pause=0.01)
            time.sleep(0.05)
            send_keys("{ENTER}")
            return True
    except Exception:
        return False


# ---------- Public API ----------

def send_wechat_message_to_minimized_chat(chat_title: str, text: str, timeout: float = 5.0) -> bool:
    """
    Bring an (independent) WeChat chat window to the foreground even if all windows are minimized,
    then send the provided text.

    Args:
        chat_title:  The exact chat window title (group name), e.g. "测试3群".
                     If your title shows as "群名 - 微信", just pass "群名".
        text:        The message to send.
        timeout:     Max seconds to wait for task-switching list in the fallback path.

    Returns:
        True on success (activated + sent), False otherwise.
    """
    # Step 1: Try to activate by window title (no flicker if already visible)
    if _try_activate_chat_by_title(chat_title):
        return _paste_and_send_text(text)

    # Step 2: Fallback via taskbar "Task switching" list (when minimized)
    if _activate_chat_via_taskbar(chat_title, timeout=timeout):
        return _paste_and_send_text(text)

    return False


# ---------- CLI hook for quick testing ----------
if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        title = sys.argv[1]
        msg = " ".join(sys.argv[2:])
        ok = send_wechat_message_to_minimized_chat(title, msg)
        print("OK" if ok else "FAILED")
    else:
        print("Usage: python send_wechat_message_to_minimized_chat.py <ChatTitle> <Message>")
        print('Example: python send_wechat_message_to_minimized_chat.py "测试3群" "今晚八点上新！"')
