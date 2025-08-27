# -*- coding: utf-8 -*-
import time
import ctypes
import os  # 新增：用于判断备用图片是否存在
from collections import deque
from pywinauto import Application, Desktop, keyboard
from pywinauto.mouse import move as mouse_move  # 只用 move，不用 wheel
import pyautogui
import concurrent.futures as futures  # NEW: 并发池
import pyscreeze  # NEW: 单帧上做模板匹配

# ============== PyAutoGUI 基本设置（防误触&提速） ==============
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.02  # 每次动作后的小停顿

APP_BACKEND = "uia"
WAIT_AFTER_CLICK = 0.35     # 行被激活后等待UI刷新
SLEEP_SCROLL    = 0.15      # 左侧滚动节奏

# === 固定步长滚动参数（可按需微调） ===
WHEEL_NOTCHES_PER_STEP   = 4     # 每次“翻页”滚轮 notch 数；越大越快但越可能跳行
EXTRA_WHEEL_ON_STUCK     = 6     # 本轮无进展时追加的补滚 notch 数
MAX_CONSEC_NO_PROGRESS   = 8     # 连续“无新增且签名未变/回弹”这么多轮后认为到底/卡死
DELAY_EACH_NOTCH         = 0.012 # 每个 notch 之间的等待
DELAY_AFTER_WHEEL_BATCH  = 0.03  # 一批滚动后的短暂停

# -------------------- 低层鼠标滚轮（Windows API） --------------------
def mouse_wheel(steps: int):
    """使用 Windows API 模拟鼠标滚轮（负数=向下）"""
    MOUSEEVENTF_WHEEL = 0x0800
    WHEEL_DELTA = 120
    n = int(steps)
    if n == 0:
        return
    sign = 1 if n > 0 else -1
    remaining = abs(n)
    while remaining > 0:
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, sign * WHEEL_DELTA, 0)
        remaining -= 1
        time.sleep(DELAY_EACH_NOTCH)
    time.sleep(DELAY_AFTER_WHEEL_BATCH)

# -------------------- 文本处理与辅助（UIA） --------------------
def normalize_text(s: str) -> str:
    if not s:
        return ""
    for j in ["\u200b", "\u2006", "\u2009", "\u200a", "\u2005", "\u00a0"]:
        s = s.replace(j, " ")
    return " ".join(s.strip().split())

def normalize_group_name(s: str) -> str:
    """标准化群名：去除成员数量后缀 (数字)"""
    if not s:
        return ""
    s = normalize_text(s)
    # 去除末尾的成员数量，如 "群名 (123)" -> "群名"
    import re
    s = re.sub(r'\s*\(\d+\)\s*$', '', s).strip()
    return s

def collect_texts(ctrl):
    parts = []
    for t in ctrl.descendants(control_type="Text"):
        s = normalize_text(t.window_text())
        if s:
            parts.append(s)
    return " ".join(parts).strip()

def get_text_near_point(x, y, dlg):
    try:
        el = Desktop(backend=APP_BACKEND).from_point(x, y)
    except Exception:
        el = None
    if el:
        s = normalize_text(el.window_text())
        if el.element_info.control_type == "Text" and s:
            return s
        parts = [normalize_text(t.window_text()) for t in el.descendants(control_type="Text")]
        parts = [p for p in parts if p]
        if parts:
            return " ".join(parts)
        parent = el.parent()
        for _ in range(2):
            if not parent:
                break
            parts = [normalize_text(t.window_text()) for t in parent.descendants(control_type="Text")]
            parts = [p for p in parts if p]
            if parts:
                return " ".join(parts)
            parent = parent.parent()
    for t in dlg.descendants(control_type="Text"):
        r = t.rectangle()
        if r.left - 5 <= x <= r.right + 5 and r.top - 5 <= y <= r.bottom + 5:
            s = normalize_text(t.window_text())
            if s:
                return s
    return ""

# -------------------- UIA：列表与行检索 --------------------
def pick_left_list(dlg):
    lists = [w for w in dlg.descendants(control_type="List")]
    if not lists:
        raise RuntimeError("未找到任何 List 控件")
    midx = (dlg.rectangle().left + dlg.rectangle().right) / 2
    candidates = [L for L in lists if L.rectangle().right <= midx]
    pool = candidates if candidates else lists
    pool.sort(key=lambda w: w.rectangle().width())
    return pool[0]

def visible_rows(list_wrapper):
    rows = (list_wrapper.descendants(control_type="ListItem")
            or list_wrapper.descendants(control_type="DataItem")
            or list_wrapper.descendants(control_type="Pane"))
    return [r for r in rows]

def get_row_label_without_click(row, dlg):
    pre = collect_texts(row)
    if pre:
        return pre
    r = row.rectangle()
    cx = int((r.left + r.right) / 2)
    cy = int((r.top + r.bottom) / 2)
    return get_text_near_point(cx, cy, dlg).strip()

def row_is_in_skip(row, dlg, skip_names):
    if not skip_names:
        return False
    pre = get_row_label_without_click(row, dlg)
    if pre and pre in skip_names:
        return True
    own = normalize_text(getattr(row, "window_text", lambda: "")())
    if own and own in skip_names:
        return True
    return False

def find_text_rect(dlg, label="最近群聊"):
    norm_label = normalize_text(label)
    for t in dlg.descendants(control_type="Text"):
        if normalize_text(t.window_text()) == norm_label:
            return t.rectangle()
    return None

def page_signature(rows, dlg):
    if not rows:
        return ("", "", 0)
    top = normalize_text(get_row_label_without_click(rows[0], dlg))
    bot = normalize_text(get_row_label_without_click(rows[-1], dlg))
    return (top, bot, len(rows))

def bottom_visible_anchor(rows, dlg, skip_names, header_rect):
    for row in reversed(rows):
        if header_rect and row.rectangle().bottom <= header_rect.bottom + 2:
            continue
        nm = normalize_text(get_row_label_without_click(row, dlg))
        if nm and nm not in skip_names:
            return nm
    return None

# -------------------- 鼠标停放与选择行 --------------------
def park_pointer_in_list(left, header_rect=None):
    r = left.rectangle()
    x = (r.left + r.right) // 2
    min_y = (header_rect.bottom + 12) if header_rect else (r.top + 24)
    y = max(min_y, r.top + 24)
    y = min(y, r.bottom - 24)
    mouse_move(coords=(x, y))

def safe_click_row(row, header_rect=None, header_margin=4):
    r = row.rectangle()
    w = max(1, r.right - r.left)
    h = max(1, r.bottom - r.top)
    rx = min(max(16, w // 3), w - 10)
    ry = min(max(14, int(h * 0.6)), h - 6)
    if header_rect:
        abs_y = r.top + ry
        min_abs_y = header_rect.bottom + header_margin
        if abs_y <= min_abs_y:
            ry = min(h - 6, max(ry, min_abs_y - r.top))
    row.click_input(coords=(rx, ry))

def select_row_no_mouse(row, header_rect=None):
    try:
        si = getattr(row, "iface_selection_item", None)
        if si:
            si.Select()
            return True
    except Exception:
        pass
    try:
        inv = getattr(row, "iface_invoke", None)
        if inv:
            inv.Invoke()
            return True
    except Exception:
        pass
    try:
        legacy = getattr(row, "iface_legacy", None)
        if legacy:
            legacy.DoDefaultAction()
            return True
    except Exception:
        pass
    try:
        safe_click_row(row, header_rect=header_rect, header_margin=4)
        return True
    except Exception:
        return False

# -------------------- UIA：连接窗口 --------------------
def attach_contact_manager():
    try:
        # 尝试连接，但忽略多窗口错误
        Application(backend=APP_BACKEND).connect(class_name_re="WeChat.*", timeout=10)
    except Exception as e:
        print(f"⚠️ 连接WeChat应用时出现警告: {e}")
        # 继续执行，因为可能已经有连接了

    # 等待“通讯录管理”弹出
    for _ in range(40):
        try:
            dlg = Desktop(backend=APP_BACKEND).window(title_re=".*通讯录管理.*", visible_only=True)
            dlg.set_focus()
            time.sleep(0.15)
            return dlg
        except Exception:
            time.sleep(0.15)
    raise RuntimeError("未能找到【通讯录管理】窗口")

# -------------------- 影像法：点击模板（已做异常安全） --------------------
def click_by_image(template_path, confidence=0.8, timeout=6.0, interval=0.25, grayscale=True, region=None):
    """
    在屏幕上找模板并点击中心点；返回 True/False
    - 捕获 ImageNotFoundException/其他异常，匹配不到仅返回 False，不再让程序崩溃
    - 可选 region 限定搜索区域（默认全屏）
    """
    end = time.time() + timeout
    last_err = None
    attempt = 0
    
    # 检查模板图片是否存在
    if not os.path.exists(template_path):
        print(f"[ERROR] 模板图片不存在: {template_path}")
        return False
    
    print(f"[INFO] 开始搜索模板: {os.path.basename(template_path)} (超时{timeout}秒)")
    
    while time.time() < end:
        attempt += 1
        try:
            # 降低confidence可以提高识别成功率
            current_confidence = max(0.6, confidence - (attempt * 0.05))
            
            box = pyautogui.locateOnScreen(
                template_path,
                confidence=current_confidence,
                grayscale=grayscale,
                region=region
            )
        except Exception as e:
            last_err = e
            box = None

        if box:
            cx, cy = pyautogui.center(box)
            print(f"[SUCCESS] 找到模板 {os.path.basename(template_path)} 在 ({cx}, {cy})")
            pyautogui.moveTo(cx, cy, duration=0.05)
            pyautogui.click(cx, cy)
            time.sleep(0.2)  # 点击后稍等
            return True
            
        print(f"[ATTEMPT {attempt}] 未找到模板 {os.path.basename(template_path)} (confidence={current_confidence:.2f})")
        time.sleep(interval)

    if last_err:
        print(f"[WARN] locateOnScreen('{template_path}') failed: {last_err}")
    print(f"[TIMEOUT] 模板搜索超时: {os.path.basename(template_path)}")
    return False

# -------------------- 冗余图片匹配小助手（只做你要求的图片冗余匹配） --------------------

# ========== NEW: 并发模板匹配（同一按钮多图） ==========
def _expand_templates(seed):
    """
    将单一路径或路径列表扩展为候选模板列表：
    - 若传入 str：自动收集同目录下同“前缀”的多张图片，如:
      contacts_button.png / contacts_button1.png / contacts_button2.png ...
    - 若传入 list/tuple：按传入顺序使用（仅保留存在的文件）。
    """
    import os, re, glob
    if isinstance(seed, (list, tuple)):
        return [os.path.abspath(p) for p in seed if os.path.exists(p)]
    p = os.path.abspath(seed)
    d, fn = os.path.split(p)
    name, ext = os.path.splitext(fn)
    prefix = re.sub(r'\d+$', '', name)  # 去掉末尾数字得到前缀
    cand = sorted(glob.glob(os.path.join(d, f"{prefix}*{ext}")))
    return [c for c in cand if os.path.exists(c)] or ([p] if os.path.exists(p) else [])


def _locate_one_on_haystack(tpl_path, haystack, confidence, grayscale):
    """在已截图的 haystack(PIL.Image) 上查找单个模板；命中返回 Box，否则 None。"""
    try:
        return pyscreeze.locate(tpl_path, haystack, confidence=confidence, grayscale=grayscale)
    except Exception:
        return None


def _locate_any_concurrent(template_paths, haystack, confidence=0.8, grayscale=True, max_workers=8):
    """在同一帧截图上并发查找多张模板；先命中者先返回 (box, tpl_path)，都未命中返回 (None, None)。"""
    if not template_paths:
        return None, None
    workers = min(max(1, len(template_paths)), max_workers)
    with futures.ThreadPoolExecutor(max_workers=workers) as ex:
        fut2p = {ex.submit(_locate_one_on_haystack, p, haystack, confidence, grayscale): p
                 for p in template_paths}
        for fut in futures.as_completed(fut2p):
            box = fut.result()
            if box:
                return box, fut2p[fut]
    return None, None


def click_by_images_fast(template_paths, confidence=0.8, timeout=6.0, interval=0.2, grayscale=True, region=None):
    """
    一次截图 → 多模板并发匹配 → 命中即点。支持 region。
    - template_paths: 可以是 str 或 多个路径的 list/tuple
    """
    import time, os
    tpl_list = _expand_templates(template_paths)
    if not tpl_list:
        print(f"[ERROR] 无有效模板: {template_paths}")
        return False

    print("[FAST] 候选模板：", ", ".join(os.path.basename(p) for p in tpl_list))
    end = time.time() + timeout
    attempt = 0

    while time.time() < end:
        attempt += 1
        # 单帧截图（避免每个模板各截一次）
        shot = pyautogui.screenshot(region=region)  # PIL.Image
        # 逐步放宽阈值（同你现有的退火思路保持一致）
        curr_conf = max(0.6, confidence - (attempt * 0.05))

        box, which = _locate_any_concurrent(tpl_list, shot, confidence=curr_conf, grayscale=grayscale)
        if box:
            # region 偏移修正
            x_off = region[0] if region else 0
            y_off = region[1] if region else 0
            cx, cy = pyscreeze.center(box)
            cx += x_off; cy += y_off

            print(f"[FAST HIT] {os.path.basename(which)} @ ({cx}, {cy}) [conf~{curr_conf:.2f}]")
            pyautogui.moveTo(cx, cy, duration=0.05)
            pyautogui.click(cx, cy)
            time.sleep(0.2)
            return True

        print(f"[FAST MISS {attempt}] 无命中（conf={curr_conf:.2f}）")
        time.sleep(interval)

    print("[FAST TIMEOUT] 并发匹配超时")
    return False
# ========== NEW 结束 ==========
def _pair_paths(path: str):
    """生成 [path, 备用path]，备用为把文件名末尾的 '1' 去掉/补上后的同名 png；只返回存在的文件。"""
    d, fn = os.path.split(path)
    name, ext = os.path.splitext(fn)
    if name.endswith("1"):
        alt = os.path.join(d, name[:-1] + ext)
    else:
        alt = os.path.join(d, name + "1" + ext)
    out = []
    for p in [path, alt]:
        if p not in out and os.path.exists(p):
            out.append(p)
    return out

def try_click_pair(path: str, **kwargs) -> bool:
    """按顺序尝试 path 与其备用 path（去掉/加上 1），哪个能匹配就用哪个。"""
    for p in _pair_paths(path):
        if click_by_image(p, **kwargs):
            return True
    return False

# -------------------- 打开通讯录管理：仅加入冗余图片匹配，其余逻辑不变 --------------------
def open_manager_via_images(img_contacts, img_manager, img_recent):
    """
    1) 点击“通讯录”  2) 点击“通讯录管理” 3) 点击“最近群聊”
    同一按钮支持多图并发匹配（自动收集同前缀模板），命中即点。
    “最近群聊”仍保留 UIA 兜底。
    """
    if not click_by_images_fast(img_contacts, confidence=0.75, timeout=8):
        raise RuntimeError("未找到【通讯录】按钮图片（contacts_button1.png / contacts_button.png 均失败）")
    time.sleep(0.6)

    if not click_by_images_fast(img_manager, confidence=0.75, timeout=10):
        raise RuntimeError("未找到【通讯录管理】按钮图片（contacts_manager_button1.png / contacts_manager_button.png 均失败）")
    time.sleep(0.8)

    # 等“通讯录管理”窗口出现后再点“最近群聊”
    dlg = attach_contact_manager()

    if not click_by_images_fast(img_recent, confidence=0.75, timeout=8):
        # 如果图片法没点到，尝试 UIA 兜底找一次“最近群聊”（保持你原来的兜底逻辑）
        target = None
        for t in dlg.descendants(control_type="Text"):
            if normalize_text(t.window_text()) == "最近群聊":
                target = t
                break
        if target:
            try:
                target.scroll_into_view()
            except Exception:
                pass
            try:
                target.click_input()
            except Exception:
                pass
        else:
            raise RuntimeError("未找到【最近群聊】按钮图片/控件（groups_button1.png / groups_button.png 均失败）")

    time.sleep(0.6)
    return dlg  # 返回通讯录管理窗口

# -------------------- 主流程（固定步长滚动） --------------------
def iterate_group_names(dlg, skip_names=None, max_groups=None):
    """
    固定步长向下滚动，不用 PageDown / LargeIncrement，避免一下到底；
    每轮只滚固定 notch 数；若无进展，追加少量补滚，仍然是固定步长。
    """
    left = pick_left_list(dlg)
    left.set_focus()
    keyboard.send_keys("{HOME}")
    time.sleep(SLEEP_SCROLL)

    skip_names = set(normalize_text(s) for s in (skip_names or set()))
    names, seen = [], set()
    last_name = None
    count = 0

    last_sig = None
    sig_history = deque(maxlen=20)
    no_progress_pages = 0

    while True:
        left.set_focus()
        rows = visible_rows(left)
        curr_sig = page_signature(rows, dlg)
        header_rect = find_text_rect(dlg, "最近群聊")

        # 构建本页候选
        items = []
        for row in rows:
            if row_is_in_skip(row, dlg, skip_names):
                continue
            pre_name = normalize_text(get_row_label_without_click(row, dlg))
            if pre_name and pre_name in skip_names:
                continue
            if header_rect and row.rectangle().bottom <= header_rect.bottom + 2:
                continue
            items.append((row, pre_name))

        # 从锚点之后开始
        start_idx = 0
        if last_name:
            for i, (_, nm) in enumerate(items):
                if nm and nm == last_name:
                    start_idx = i + 1
                    break

        # 逐行采集
        added_in_page = 0
        if start_idx < len(items):
            for i in range(start_idx, len(items)):
                row, pre_name = items[i]
                if pre_name and pre_name in skip_names:
                    continue
                if not select_row_no_mouse(row, header_rect=header_rect):
                    continue
                time.sleep(WAIT_AFTER_CLICK)

                name = pre_name or normalize_text(collect_texts(row))
                if not name:
                    name = normalize_text(get_row_label_without_click(row, dlg))

                # 标准化群名：去除成员数量后缀
                normalized_name = normalize_group_name(name)
                if not normalized_name or normalized_name in skip_names or normalized_name in seen:
                    continue

                seen.add(normalized_name)
                names.append(normalized_name)
                count += 1
                added_in_page += 1
                print(f"[{count}] {normalized_name}")

                if max_groups and count >= max_groups:
                    return names

        # 更新锚点为当前视口底部可点击项（即使本轮无新增）
        new_anchor = bottom_visible_anchor(rows, dlg, skip_names, header_rect)
        if new_anchor:
            last_name = new_anchor

        # 判断是否无进展/回弹
        bounced = (added_in_page == 0 and curr_sig in sig_history)
        no_change = (added_in_page == 0 and curr_sig == last_sig)
        if bounced or no_change:
            no_progress_pages += 1
        else:
            no_progress_pages = 0

        # 到底/卡死保护
        if no_progress_pages >= MAX_CONSEC_NO_PROGRESS:
            break

        # 固定步长向下滚动
        left.set_focus()
        park_pointer_in_list(left, header_rect)
        mouse_wheel(-WHEEL_NOTCHES_PER_STEP)
        if bounced or no_change:
            mouse_wheel(-EXTRA_WHEEL_ON_STUCK)

        sig_history.append(curr_sig)
        last_sig = curr_sig
        time.sleep(SLEEP_SCROLL)

    return names

# -------------------- 入口 --------------------
if __name__ == "__main__":
    # 1) 用图片法完成：通讯录 -> 通讯录管理 -> 最近群聊
    script_dir = os.path.dirname(os.path.abspath(__file__))
    CONTACTS_IMG = os.path.join(script_dir, "contacts_button1.png")
    MANAGER_IMG  = os.path.join(script_dir, "contacts_manager_button1.png")
    RECENT_IMG   = os.path.join(script_dir, "groups_button1.png")
    dlg = open_manager_via_images(CONTACTS_IMG, MANAGER_IMG, RECENT_IMG)

    # 2) 采集群名
    SKIP = {"全部", "标签", "最近群聊", ""}  # 目录项一律跳过
    group_names = iterate_group_names(dlg, skip_names=SKIP, max_groups=None)

    print("\n========== 采集完成 ==========")
    print(f"共采集到 {len(group_names)} 个群：")
    for i, g in enumerate(group_names, 1):
        print(f"{i:>3}. {g}")
