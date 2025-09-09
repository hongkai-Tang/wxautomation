# -*- coding: utf-8 -*-
"""
UIA-only implementation for reading WeChat "Recent Group Chats" without image matching.
This version ensures the mouse hovers over the list area before wheel scrolling,
so scrolling actually affects the list instead of the sidebar.

Place at:
weixinassistant/Weixinassistant_function/Contact_list_group_chat_acquisition/Contact_list_group_chat_acquisition.py
"""

from time import sleep, time
from typing import Iterable, List, Optional, Sequence, Tuple

from pywinauto import Desktop, mouse
from pywinauto.base_wrapper import BaseWrapper
from pywinauto.controls.uiawrapper import UIAWrapper


# ------------------------- 工具 -------------------------

def _now() -> float:
    return time()


def _find_wechat_main(timeout: float = 10.0) -> UIAWrapper:
    """找到并激活“微信/WeChat”主窗口（UIA）"""
    end = _now() + timeout
    while _now() < end:
        wins = Desktop(backend="uia").windows(title="微信", visible_only=True)
        if not wins:
            wins = Desktop(backend="uia").windows(title="WeChat", visible_only=True)
        if wins:
            main = wins[0]
            try:
                main.set_focus()
            except Exception:
                pass
            return main

        # 兜底：类名里含 WeChat 的也算
        for w in Desktop(backend="uia").windows(visible_only=True):
            try:
                name = (w.window_text() or "").strip()
                cls = (w.element_info.class_name or "")
            except Exception:
                continue
            if name in ("微信", "WeChat") or ("WeChat" in cls):
                try:
                    w.set_focus()
                except Exception:
                    pass
                return w
        sleep(0.2)
    raise RuntimeError("未找到微信主窗口（title='微信' / 'WeChat'）")


def _child_by_names(
    parent: BaseWrapper,
    names: Sequence[str],
    control_types: Sequence[str] = ("Button", "List", "Pane", "Text", "ListItem"),
    depth: int = 8,
) -> Optional[UIAWrapper]:
    """
    在 parent 下递归查找“名称相等或包含”的控件，返回第一个命中的。
    """
    wanted = [n for n in names if n]
    if not wanted:
        return None
    try:
        nodes = parent.descendants(depth=depth)
    except Exception:
        nodes = []
    for n in nodes:
        try:
            ct = (n.element_info.control_type or "")
            if ct not in control_types:
                continue
            text = (n.window_text() or "").strip()
            # 某些控件没有 name，试试友好类名
            if not text:
                text = (getattr(n, "friendly_class_name", lambda: "")() or "").strip()
        except Exception:
            continue

        if text:
            for key in wanted:
                if (text == key) or (key in text):
                    return n
    return None


def _ensure_visible(ctrl: UIAWrapper) -> None:
    """尽量把控件滚动到可见区域"""
    try:
        ctrl.iface_scrollitempattern.scroll_into_view()
    except Exception:
        pass


def _invoke(ctrl: UIAWrapper) -> None:
    """优先 Invoke，失败再 Click"""
    _ensure_visible(ctrl)
    try:
        ctrl.iface_invokepattern.Invoke()
        return
    except Exception:
        pass
    try:
        ctrl.click_input()
    except Exception as e:
        raise RuntimeError(f"点击控件失败: {e}")


def _wait_dialog(title_candidates: Iterable[str], timeout: float = 8.0) -> UIAWrapper:
    """等待弹出窗口（按标题匹配）"""
    end = _now() + timeout
    cans = tuple(title_candidates)
    while _now() < end:
        for t in cans:
            wins = Desktop(backend="uia").windows(title=t, visible_only=True)
            if wins:
                return wins[0]
        sleep(0.2)
    raise RuntimeError(f"未找到对话框：{cans}")


def _click_by_names(
    parent: BaseWrapper,
    names: Sequence[str],
    control_types: Sequence[str] = ("Button", "Pane", "Text", "ListItem"),
    depth: int = 10,
    retries: int = 2,
    retry_pause: float = 0.35,
) -> UIAWrapper:
    """
    更强健的点击：多次查找+滚动可见+Invoke/Click。
    返回被点击的控件。
    """
    last_err = None
    for _ in range(max(1, retries)):
        ctrl = _child_by_names(parent, names, control_types=control_types, depth=depth)
        if ctrl:
            try:
                _invoke(ctrl)
                return ctrl
            except Exception as e:
                last_err = e
        sleep(retry_pause)
    if last_err:
        raise last_err
    raise RuntimeError(f"UIA 未找到控件：{tuple(names)}")


def _hover_center(ctrl: UIAWrapper) -> Tuple[int, int]:
    """把鼠标移到控件内部(偏上方一点)，返回坐标"""
    rect = ctrl.rectangle()
    # 靠近顶部一点，避免遮挡/分隔线
    x = int((rect.left + rect.right) / 2)
    y = int(rect.top + min(40, (rect.height() // 4) or 1))
    mouse.move(coords=(x, y))
    sleep(0.05)
    return x, y


# ------------------------- 主流程 -------------------------

def open_contacts_manager_and_switch_to_recent_groups() -> UIAWrapper:
    """
    主界面 → 点击“通讯录” → 点击“通讯录管理” → 对话框里点击“最近群聊”
    返回“通讯录管理”对话框对象
    """
    main = _find_wechat_main()

    # 1) 点击左侧导航“通讯录”
    print("[UIA] 点击：通讯录")
    contacts_btn_names = ("通讯录", "Contacts")
    _click_by_names(main, contacts_btn_names, control_types=("Button", "Pane", "Text"), depth=12)
    sleep(0.2)

    # 2) 点击顶部的“通讯录管理”
    print("[UIA] 点击：通讯录管理")
    manage_btn_names = ("通讯录管理", "Contacts Manager", "通讯录 管理")
    try:
        _click_by_names(main, manage_btn_names, control_types=("Button", "Pane", "Text"), depth=15, retries=3)
    except Exception:
        # 兜底：把所有 Button 扫一遍，挑 name 里含“通讯录”和“管理”的
        try:
            buttons = main.descendants(control_type="Button", depth=15)
        except Exception:
            buttons = []
        target = None
        for b in buttons:
            try:
                nm = (b.window_text() or "").strip()
            except Exception:
                nm = ""
            if nm and ("通讯录" in nm) and ("管" in nm):  # 粗匹配“通讯录…管…”
                target = b
                break
        if not target:
            raise RuntimeError("UIA 未找到控件：('通讯录管理','Contacts Manager')")
        _invoke(target)

    # 3) 等待“通讯录管理”对话框
    dlg = _wait_dialog(("通讯录管理", "Contacts Manager"), timeout=10.0)
    try:
        dlg.set_focus()
    except Exception:
        pass
    sleep(0.2)

    # 4) 在对话框左侧点击“最近群聊”
    print("[UIA] 点击：最近群聊")
    recent_btn_names = ("最近群聊", "Recent Group Chats", "最近", "最近的群聊")
    _click_by_names(dlg, recent_btn_names,
                    control_types=("Button", "ListItem", "Text", "Pane"), depth=12, retries=3)
    sleep(0.25)

    return dlg


def _extract_texts_from_item(item: UIAWrapper) -> List[str]:
    """从单个条目尽量抽取文本（经验：第一段通常是群名）"""
    texts: List[str] = []
    try:
        name = (item.window_text() or "").strip()
        if name:
            texts.append(name)
    except Exception:
        pass

    try:
        for t in item.descendants(control_type="Text", depth=3):
            tx = (t.window_text() or "").strip()
            if tx:
                texts.append(tx)
    except Exception:
        pass

    out: List[str] = []
    for s in texts:
        if s and (s not in out) and len(s) <= 100:
            out.append(s)
    return out


def _resolve_list_container(dlg: UIAWrapper) -> UIAWrapper:
    """定位右侧“群列表”容器（List/Table/DataGrid/Pane）"""
    # 先找典型列表控件
    for ct in ("List", "Table", "DataGrid"):
        try:
            lst = dlg.descendants(control_type=ct, depth=8)
        except Exception:
            lst = []
        if lst:
            return lst[-1]  # 右侧内容区往往是最后一个
    # 兜底：选个较大的 Pane 当作列表区域
    panes = dlg.descendants(control_type="Pane", depth=8)
    if not panes:
        raise RuntimeError("未找到群列表控件（List/DataGrid）")
    # 选取面积最大的一个 Pane（通常是内容区）
    def area(w):
        r = w.rectangle()
        return max(0, r.width() * r.height())
    panes_sorted = sorted(panes, key=area, reverse=True)
    return panes_sorted[0]


def get_recent_group_names_from_dialog(dlg: UIAWrapper, max_items: int = 200) -> List[str]:
    """
    在“通讯录管理/最近群聊”界面读取群名列表（仅滚轮读取，不再进行任何点击）。
    """
    # 定位列表容器
    list_like = _resolve_list_container(dlg)

    # 把焦点和鼠标都放到列表控件上，确保滚轮对准列表
    try:
        list_like.set_focus()
    except Exception:
        pass
    cx, cy = _hover_center(list_like)
    # 轻点一下，不影响逻辑但能更稳拿到焦点
    try:
        list_like.click_input(coords=(5, 5))
    except Exception:
        pass
    sleep(0.05)

    groups: List[str] = []
    stagnant_rounds = 0  # 连续无新增的轮数，用来判断是否到达底部
    MAX_STAGNANT = 3
    MAX_SWIPES = 80

    for _ in range(MAX_SWIPES):
        # 采集当前一屏
        raw: List[str] = []
        for ct in ("ListItem", "DataItem", "TreeItem", "Pane"):
            try:
                items = list_like.descendants(control_type=ct, depth=3)
            except Exception:
                items = []
            for it in items:
                parts = _extract_texts_from_item(it)
                if not parts:
                    continue
                name = parts[0].strip()
                if not name:
                    continue
                if name in ("最近群聊", "全部", "标签", "备注", "好友权限"):
                    continue
                raw.append(name)

        before = len(groups)
        for n in raw:
            if n not in groups:
                groups.append(n)
            if len(groups) >= max_items:
                break

        if len(groups) >= max_items:
            break

        # 判定是否到底：本轮没有任何新增，则累加 stagnation；连续几轮无新增认为到底
        if len(groups) == before:
            stagnant_rounds += 1
        else:
            stagnant_rounds = 0
        if stagnant_rounds >= MAX_STAGNANT:
            break

        # 向下滚动一屏（确保鼠标在列表上）
        cx, cy = _hover_center(list_like)
        try:
            mouse.scroll(coords=(cx, cy), wheel_dist=-5)  # 负数为向下
        except Exception:
            # 兜底：再尝试一次
            sleep(0.05)
            mouse.scroll(coords=(cx, cy), wheel_dist=-8)
        sleep(0.15)

    return groups


def get_recent_group_names(max_items: int = 200) -> List[str]:
    """
    便捷入口：自动打开“通讯录管理/最近群聊”，然后滚轮读取群名。
    """
    dlg = open_contacts_manager_and_switch_to_recent_groups()
    return get_recent_group_names_from_dialog(dlg, max_items=max_items)


# ------------------------- 自检：python 直接运行 -------------------------
if __name__ == "__main__":
    print(">>> 打开并切换到 最近群聊 …")
    dlg = open_contacts_manager_and_switch_to_recent_groups()
    print(">>> 读取：")
    print(get_recent_group_names_from_dialog(dlg))
