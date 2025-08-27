# -*- coding: utf-8 -*-
"""
WeChat UIA 自动化（极简稳态版 + 更稳的 @所有人 选择）
流程：
1) 前置微信
2) 把群名写入搜索框 -> 按 Enter 进入第一个结果（不做多次尝试、不做 ChatInfo 校验）
3) 聚焦输入框
4) 在群里 @：移入 ChatContactMenu -> 滚到顶 ->
   先按文本点击“所有人/全体成员/所有成员”，不行则用“群成员”分隔条做锚点点击其上方行
- 不使用 ESC；失败仅 Backspace 清理
"""

import sys
import time
from typing import Iterable, List, Optional

from wxauto import WeChat
from pywinauto import Desktop, keyboard
from pywinauto.mouse import click as mouse_click
from pywinauto import mouse  # move/scroll

# ---------- 可靠中文粘贴 ----------
def _paste_text(text: str, fallback_type: bool = False):
    try:
        import pyperclip
        pyperclip.copy(text); time.sleep(0.05)
        keyboard.send_keys("^v"); return
    except Exception:
        pass
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv)
        app.clipboard().setText(text); time.sleep(0.05)
        keyboard.send_keys("^v"); return
    except Exception:
        pass
    if fallback_type:
        keyboard.send_keys(text, with_spaces=True, pause=0.01)

# ---------- 窗口 ----------
def _bring_wechat_to_front(timeout: float = 5.0):
    desk = Desktop(backend="uia")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            win = desk.window(title_re="微信|WeChat", class_name="WeChatMainWndForPC")
            if win.exists(timeout=0.5):
                try:
                    if win.is_minimized(): win.restore()
                except Exception:
                    pass
                win.set_focus(); return win
        except Exception:
            pass
        time.sleep(0.2)
    print("[WARN] 未能前置微信主窗口"); return None

# ---------- 搜索框 ----------
def _locate_search_edit(win):
    edit = win.child_window(title_re="搜.*|Search", control_type="Edit")
    if not edit.exists(timeout=0.8):
        edit = win.descendant(title_re="搜.*|Search", control_type="Edit")
    return edit if edit.exists() else None

def _set_search_text_precise(edit, text: str) -> bool:
    try:
        edit.click_input(); time.sleep(0.05)
        try:
            vp = edit.iface_value
            vp.SetValue(""); time.sleep(0.02); vp.SetValue(text)
        except Exception:
            try:
                edit.set_edit_text(""); time.sleep(0.02); edit.set_edit_text(text)
            except Exception:
                edit.set_focus(); keyboard.send_keys("^a{BACKSPACE}"); _paste_text(text)
        time.sleep(0.25)
        try: cur = edit.iface_value.CurrentValue
        except Exception:
            try: cur = edit.window_text()
            except Exception: cur = ""
        if text.strip() and text.strip() in (cur or "").strip(): return True
        edit.set_focus(); keyboard.send_keys("^a{BACKSPACE}"); _paste_text(text); time.sleep(0.25)
        try: cur = edit.iface_value.CurrentValue
        except Exception: cur = edit.window_text()
        ok = text.strip() in (cur or "").strip()
        if not ok: print(f"[ERR] 搜索框读回失败，当前='{cur}' 期望='{text}'")
        return ok
    except Exception as e:
        print(f"[ERR] 写入搜索框失败：{e}"); return False

def _enter_first_search_result(win):
    edit = _locate_search_edit(win)
    if not edit: print("[ERR] 未找到搜索框(Edit)"); return False
    try:
        if not edit.has_keyboard_focus(): edit.click_input(); time.sleep(0.05)
    except Exception:
        edit.click_input(); time.sleep(0.05)
    keyboard.send_keys("{ENTER}"); time.sleep(0.45); return True

# ---------- 输入框聚焦 ----------
def _focus_message_edit(win) -> bool:
    try:
        edits = win.descendants(control_type="Edit")
        candidates = [e for e in edits if e.window_text() not in ("搜索", "Search")]
        if candidates: candidates[-1].click_input(); time.sleep(0.1); return True
    except Exception:
        pass
    try:
        rect = win.rectangle()
        x = rect.left + int(rect.width()*0.65); y = rect.top + int(rect.height()*0.88)
        mouse_click(button="left", coords=(x, y)); time.sleep(0.1); return True
    except Exception:
        pass
    return False

# ---------- ChatContactMenu / @ ----------
def _wait_chat_contact_menu(win, timeout: float = 2.0):
    """Pane 'ChatContactMenu'（先在主窗，后全局兜底）"""
    desk = Desktop(backend="uia"); t0 = time.time()
    while time.time() - t0 < timeout:
        for finder in (win.child_window, win.descendant):
            try:
                m = finder(title="ChatContactMenu", control_type="Pane")
                if m.exists(timeout=0.1): return m
            except Exception:
                pass
        try:
            m = desk.window(title="ChatContactMenu", control_type="Pane")
            if m.exists(timeout=0.1): return m
        except Exception:
            pass
        time.sleep(0.05)
    return None

def _menu_anchor(menu):
    r = menu.rectangle()
    x = int(r.left + r.width()*0.20)   # 靠左，避开滚动条
    y = int(r.top  + r.height()*0.35)  # 上半部
    return x, y

def _hover_menu(menu):
    x, y = _menu_anchor(menu); mouse.move(coords=(x, y)); time.sleep(0.03)

def _scroll_menu(menu, direction: str, steps: int = 3, dist: int = 4):
    _hover_menu(menu)
    wheel = dist if direction == "up" else -dist
    for _ in range(steps):
        try:
            mouse.scroll(wheel_dist=wheel)
        except Exception:
            keyboard.send_keys("{PGUP}" if direction=="up" else "{PGDN}")
        time.sleep(0.05)

def _list_items(menu):
    try: return menu.descendants(control_type="ListItem")
    except Exception: return []

def _scroll_to_top(menu, max_round: int = 10):
    last_top = None
    for _ in range(max_round):
        items = _list_items(menu)
        top_now = items[0].rectangle().top if items else None
        _scroll_menu(menu, "up", steps=2, dist=5)
        items2 = _list_items(menu)
        top_new = items2[0].rectangle().top if items2 else None
        if top_new == top_now == last_top: break
        last_top = top_new

def _find_any_node_by_text(menu, labels: List[str]):
    """不限控件类型，在面板里找文本节点"""
    ct_types = ["ListItem", "Text", "Button", "Hyperlink", "Custom"]
    for ct in ct_types:
        try: nodes = menu.descendants(control_type=ct)
        except Exception: nodes = []
        for n in nodes:
            try: name = n.window_text().strip()
            except Exception: name = ""
            if not name: continue
            for lab in labels:
                if name == lab or lab in name: return n
    return None

def _click_inside_rect(r, x_ratio: float = 0.30, y_ratio: float = 0.55):
    x = int(r.left + r.width()*x_ratio)
    y = int(r.top  + r.height()*y_ratio)
    mouse_click(button="left", coords=(x, y))

def _cleanup_failed_at(name_len: int = 0):
    keyboard.send_keys("{BACKSPACE " + str(max(1, name_len+1)) + "}")

def _click_everyone_by_header_anchor(menu) -> bool:
    """
    兜底方案：找“群成员”分隔条，点其上方一行（就是‘所有人’）。
    """
    header = None
    try:
        header = menu.descendants(title="群成员", control_type="Text")
        if not header:
            header = menu.descendants(title_re="群.*成.*", control_type="Text")
    except Exception:
        header = None
    if header:
        hr = header[0].rectangle()
        r = menu.rectangle()
        x = int(r.left + r.width()*0.28)         # 左侧 28% 位置，命中文字区
        y = max(r.top+6, hr.top - 12)            # 分隔条上方 12px 近似就是“所有人”行
        mouse_click(button="left", coords=(x, y)); time.sleep(0.05)
        return True
    return False

def _mention_everyone_if_available(win) -> bool:
    """
    @ -> 移入面板 -> 滚到顶 ->
    1) 尝试按文本点击“所有人/全体成员/所有成员”
    2) 失败则用“群成员”锚点方式点击其上方一行
    """
    keyboard.send_keys("@"); time.sleep(0.1)
    menu = _wait_chat_contact_menu(win, 2.0)
    if not menu: _cleanup_failed_at(0); return False

    _hover_menu(menu); _scroll_to_top(menu, max_round=10)

    node = _find_any_node_by_text(menu, ["所有人", "全体成员", "所有成员"])
    if node:
        _click_inside_rect(node.rectangle(), 0.30, 0.55)   # 点在节点内部左侧
        keyboard.send_keys(" "); return True

    # 文本节点没拿到，就直接“点顶部那一行”（用‘群成员’分隔条定位）
    if _click_everyone_by_header_anchor(menu):
        keyboard.send_keys(" "); return True

    _cleanup_failed_at(0); return False

def _mention_one(win, name: str):
    keyboard.send_keys("@"); time.sleep(0.05)
    _paste_text(name); time.sleep(0.25)
    menu = _wait_chat_contact_menu(win, 2.0)
    if not menu: _cleanup_failed_at(len(name)); return
    _hover_menu(menu)
    node = _find_any_node_by_text(menu, [name])
    if node:
        _click_inside_rect(node.rectangle(), 0.30, 0.55)
        keyboard.send_keys(" ")
    else:
        _cleanup_failed_at(len(name))

# ---------- 发送 ----------
def _send_multiline(text: str):
    _paste_text(text); time.sleep(0.05); keyboard.send_keys("{ENTER}")

def _chunks(lst: List[str], n: int) -> List[List[str]]:
    return [lst[i:i+n] for i in range(0, len(lst), n)]

# ---------- 对外 API ----------
def bind_AtAll(wx_instance: WeChat):
    """
    wx.AtAll(content, group, names=None, max_per_msg=12, mention_first=True)
    - 搜索写入后仅按一次 Enter 进入第一个结果
    - @所有人：优先文本匹配点击；兜底用“群成员”锚点点顶部行
    - 不使用 ESC；@失败用 Backspace 清理
    """

    def AtAll(content: str,
              group: str,
              names: Optional[Iterable[str]] = None,
              max_per_msg: int = 12,
              mention_first: bool = True) -> bool:
        print(f"[INFO] 目标群：{group}")
        win = _bring_wechat_to_front()
        if not win: return False

        # 1) 搜索并进入首个结果
        edit = _locate_search_edit(win)
        if not edit: print("[ERR] 未找到搜索框(Edit)"); return False
        if not _set_search_text_precise(edit, group):
            print("[ERR] 搜索框写入群名失败"); return False
        if not _enter_first_search_result(win): return False

        # 2) 聚焦输入框
        _focus_message_edit(win)

        # 3) 发送（带 @ 或仅正文）
        name_list: List[str] = []
        if names: name_list = [str(x).strip() for x in names if str(x).strip()]

        if name_list:
            for batch in _chunks(name_list, max_per_msg):
                if mention_first:
                    for n in batch: _mention_one(win, n); time.sleep(0.05)
                    keyboard.send_keys("{ENTER}"); _send_multiline(content)
                else:
                    _paste_text(content); time.sleep(0.05); keyboard.send_keys("{ENTER}")
                    for n in batch: _mention_one(win, n); time.sleep(0.05)
                    keyboard.send_keys("{ENTER}")
                time.sleep(0.2)
            print(f"[DONE] 已向 {group} 发送 {len(_chunks(name_list, max_per_msg))} 条带 @ 的消息。")
            return True
        else:
            if _mention_everyone_if_available(win):
                keyboard.send_keys("{ENTER}"); _send_multiline(content)
                print("[DONE] 有效 @所有人 + 正文 已发送。"); return True
            else:
                _send_multiline(content)
                print("[INFO] 本群无“所有人”，仅发送正文（不造假 @）。"); return True

    setattr(wx_instance, "AtAll", AtAll); return wx_instance

# ---------- 示例 ----------
if __name__ == "__main__":
    wx = WeChat()
    bind_AtAll(wx)

    group = "测试1群"  # ← 改为你的群名
    content = """通知：
下午xxxx
xxxx
测试使用"""

    wx.AtAll(content, group)
    # wx.AtAll(content, group, names=["Tel"], max_per_msg=8)
