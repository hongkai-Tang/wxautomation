# location.py
# -*- coding: utf-8 -*-
# 依赖: pip install pywinauto

from typing import List, Optional
from pywinauto import Desktop
import re

# ============== 基础工具 ==============

def _pick_messages_list(chat_win):
    """从聊天窗口中挑出消息列表（优先名字为“消息/Messages”的 List，否则取面积最大的 List）。"""
    lists = chat_win.descendants(control_type="List")
    if not lists:
        return None
    for lst in lists:
        n = (lst.window_text() or "").strip()
        if n in ("消息", "Messages"):
            return lst
    # 兜底：面积最大
    def area(c):
        r = c.rectangle()
        return max(0, r.width()) * max(0, r.height())
    return max(lists, key=area)

def _collect_named_items(list_item):
    """
    收集列表项内“所有带 Name 的子控件”，返回[(top,left,ctltype,name), ...]
    不只看 Text，因为微信常把两行文字挂在 Pane/Custom 上。
    """
    out = []
    for ctrl in list_item.descendants():
        try:
            info = ctrl.element_info
            ct   = getattr(info, "control_type", None) or ctrl.friendly_class_name()
            name = (getattr(info, "name", None) or ctrl.window_text() or "").strip()
            if not name:
                continue
            r = ctrl.rectangle()
            out.append((r.top, r.left, ct, name))
        except Exception:
            continue
    out.sort(key=lambda x: (x[0], x[1]))  # 先按 y 再按 x
    return out

def _cluster_rows(named, eps: int = 8):
    """
    把 (top,left,ct,name) 列表按“行”聚类；同一行的 y 相差不超过 eps。
    返回: [{'y':行顶y, 'items':[同一行元素...]}, ...]，且行内 items 已按 x 升序。
    """
    rows = []
    for t in named:
        y = t[0]
        placed = False
        for row in rows:
            if abs(y - row['y']) <= eps:
                row['items'].append(t)
                row['y'] = min(row['y'], y)
                placed = True
                break
        if not placed:
            rows.append({'y': y, 'items': [t]})
    rows.sort(key=lambda r: r['y'])
    for row in rows:
        row['items'].sort(key=lambda it: it[1])
    return rows

def _is_address_line(s: str) -> bool:
    """更严格的中文地址判定，避免把“××路店”类店名当成地址。"""
    s = (s or "").strip()
    s_nospace = re.sub(r"\s+", "", s)

    # A. 含有行政区级关键词 → 认为像地址
    has_admin = re.search(r"(省|市|自治州|地区|盟|旗|区|县|镇|乡|街道)", s_nospace)

    # B. 道路/街巷等 + 至少一个数字（通常表示门牌/号） → 认为像地址
    has_road_and_number = re.search(
        r"(大道|大街|环路|公路|高速|国道|省道|乡道|路|街|道|巷|弄).*[0-9０-９]+号?", s_nospace
    )

    return bool(has_admin or has_road_and_number)


def _strip_title_people(title: str) -> str:
    """从窗口标题里取昵称/群名（去掉括号人数/角标等），如 '测试3群 (8)' -> '测试3群'。"""
    t = title.strip()
    # 去掉末尾括号部分
    t = re.sub(r"\s*\([^)]*\)\s*$", "", t)
    return t

# ============== 对外接口 ==============

def LocationMessage(chat_title: str) -> Optional[List[str]]:
    """
    输入：群名称/私聊名称（聊天窗口标题前缀，如 '测试3群' 或 '左宇科'）
    返回：['<sender>', '<address>', '<title>']
         - sender : 发送者昵称（首行识别；私聊优先匹配窗口标题；群聊优先非Text控件）
         - address: 详细地址（第二行起第一条“像地址”的文本）
         - title  : 地点名（首行里非昵称的文本）
    若未找到“位置”卡片则返回 None。
    """
    desk = Desktop(backend="uia")

    # 1) 聊天窗口（前缀匹配，兼容 '测试3群 (8)' 这类）
    chat = desk.window(title_re=rf"^{re.escape(chat_title)}.*", control_type="Window")
    if not chat.exists(timeout=2.0):
        return None

    # 2) 消息列表
    lst = _pick_messages_list(chat)
    if not lst:
        return None

    # 3) 最近一条“位置/Location”列表项
    items = lst.descendants(control_type="ListItem")
    reserved = {"[位置]", "位置", "Location"}
    for it in reversed(items):
        raw = (it.window_text() or "").strip()
        if ("位置" not in raw) and ("Location" not in raw):
            continue

        named = _collect_named_items(it)  # [(top,left,ct,name), ...] 已按 y/x 排序
        if not named:
            continue

        # —— 行聚类，取首行元素（x 从左到右）——
        rows = _cluster_rows(named)
        if not rows:
            continue
        top_items = rows[0]['items']

        # 窗口标题（去掉人数等），用于私聊昵称匹配
        win_title_clean = _strip_title_people(chat.window_text() or "")

        # --- 选 sender ---
        sender = None
        # a) 私聊：与窗口标题相等/包含关系
        for _, _, _, nm in top_items:
            s = nm.strip()
            if not s or s in reserved:
                continue
            if s == win_title_clean or s in win_title_clean or win_title_clean in s:
                sender = s
                break
        # b) 群聊：优先非 Text 的控件（如 Button [表情]）
        if not sender:
            for _, _, ct, nm in reversed(top_items):
                s = nm.strip()
                if not s or s in reserved:
                    continue
                if (ct or "").lower() != "text":
                    sender = s
                    break
        # c) 兜底：首行最右侧的非保留文本
        if not sender:
            for _, _, _, nm in reversed(top_items):
                s = nm.strip()
                if s and s not in reserved:
                    sender = s
                    break

        # --- 选 title（首行里非 sender 的文本） ---
        title = None
        for _, _, _, nm in top_items:
            s = nm.strip()
            if not s or s in reserved:
                continue
            if sender and s == sender:
                continue
            title = s
            break

        # --- 选 address（第二行起第一条“像地址”的文本） ---
        # —— 地址：优先在第二行及以后寻找 —— 
        address = None
        sec_texts = []
        for row in rows[1:]:
            for _, _, _, nm in row['items']:
                t = (nm or "").strip()
                if t and t not in reserved:
                    sec_texts.append(t)

        # 先按“像地址”的规则挑
        for t in sec_texts:
            if _is_address_line(t) and t not in {title, sender}:
                address = t
                break

        # 次选：第二行里的第一条、且 != title/sender
        if not address and sec_texts:
            for t in sec_texts:
                if t not in {title, sender}:
                    address = t
                    break

        # 兜底：全体可见文本里再找第一条“像地址”的
        if not address:
            lines = [nm for _, _, _, nm in named if nm.strip() and nm not in reserved]
            cand = next((s for s in lines if _is_address_line(s) and s not in {title, sender}), None)
            if cand:
                address = cand


        # ---- 兜底：用整体可见文本修补缺项 ----
        lines = [nm for _, _, _, nm in named if nm.strip() and nm not in reserved]
        if not address:
            cand = next((s for s in lines if _is_address_line(s)), None)
            address = cand or (lines[1] if len(lines) >= 2 else "")
        if not title and lines:
            # 取第一条非 sender 的文本
            for s in lines:
                if sender and s == sender:
                    continue
                title = s
                break
        if not sender:
            # 极端情况：首行只有地点名——退回窗口标题
            sender = win_title_clean

        # 返回顺序：昵称、地址、店名
        return [sender or "", address or "", title or ""]

    return None

# ============== 演示 ==============
if __name__ == "__main__":
    # 示例一：群聊
    print(LocationMessage("测试3群"))
    # 示例二：私聊
    # print(LocationMessage("左宇科"))
