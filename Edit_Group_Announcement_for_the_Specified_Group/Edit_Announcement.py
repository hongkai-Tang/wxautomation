# -*- coding: utf-8 -*-
# pip install pywinauto==0.6.8
from pywinauto import Application, Desktop, timings, mouse
from pywinauto.keyboard import send_keys
import re, time, json, os, ctypes

# ===== 可按需调整 =====
ANNOUNCEMENT_ENTRY = "群公告"
DONE_BUTTON = "完成"
PUBLISH_BUTTON = "发布"

# 强制先点击“顶级父窗口”的右上角，确保锚定的是外层大窗口
ANCHOR_PRIME_CLICK = True      # True: 先在 (rect.right-2, rect.top+2) 单击一次

# 以【顶级父窗口右上角】为锚点的默认偏移（以 100% 缩放 / DPI=96 为基准）
OFF_RIGHT_FROM_EDGE = 20       # 起点离右边缘（从右向左）
OFF_TOP_FROM_EDGE   = 20       # 起点离上边缘（从上向下）

# 网格参数（仅用于计算 R2C2 的位置；不做扫描）
ROW_STEP_PX      = 20          # 行距
COL_STEP_PX      = 20          # 列距（向“左”推进）
TARGET_ROW       = 2           # 目标行（固定为第二行）
TARGET_COL       = 2           # 目标列（固定为第二列）

# （可选）一次性校准：保存与右上角的相对偏移（off_right/off_top）
CONFIG_FILE = os.path.join(os.path.dirname(__file__) if "__file__" in globals() else os.getcwd(),
                           "wechat_topright_anchor_offset.json")

# ====== 新增：记录当前顶级父窗口句柄（用于嵌入面板等场景，保持不变可备用） ======
LAST_TOP_HANDLE = None

# ===== 基础工具 =====
def _wait_exists(ctrl, timeout=8.0):
    ctrl.wait("exists ready visible enabled", timeout=timeout)
    return ctrl

def connect_wechat():
    try:
        app = Application(backend="uia").connect(title_re=r".*微信", timeout=5)
    except:
        app = Application(backend="uia").connect(path_re=r".*WeChat.*", timeout=5)
    return app

def normalize_group_title(title: str) -> str:
    title = title.strip()
    m = re.match(r"^(.*?)(?:\s*[\(（]\s*\d+\s*[\)）]\s*)?$", title)
    return m.group(1).strip() if m else title

def find_chat_window(app: Application, group_name: str):
    """返回 WindowSpecification（不是 UIAWrapper）"""
    target = group_name.strip()
    for w in app.windows():  # w 是 UIAWrapper
        try:
            t = w.window_text()
            if t and normalize_group_title(t) == target:
                return app.window(handle=w.handle)  # WindowSpecification
        except Exception:
            pass
    raise RuntimeError(f"找不到群聊独立窗口：{group_name}（请先把该群弹出为独立窗口）")

def get_top_level_rect(win_spec):
    """始终以【顶级父窗口】为锚点（整个独立聊天窗口）。"""
    wrapper = win_spec.wrapper_object()
    top = wrapper.top_level_parent()
    return top.rectangle(), top.handle

def get_top_level_spec(app, win_spec):
    """把任意 window spec 映射为顶级父窗口的 WindowSpecification。"""
    rect, hwnd = get_top_level_rect(win_spec)
    return app.window(handle=hwnd)

def get_dpi_for_window(hwnd) -> int:
    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        return int(dpi) if dpi > 0 else 96
    except Exception:
        return 96

def load_saved_offset():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if {"off_right","off_top"} <= d.keys():
                    return int(d["off_right"]), int(d["off_top"])
    except Exception:
        pass
    return None

def save_offset(off_right: int, off_top: int):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"off_right": off_right, "off_top": off_top}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ===== 可选：校准相对偏移 =====
def calibrate_offset_via_topright(win_spec):
    top_rect, _ = get_top_level_rect(win_spec)
    input("请把鼠标移到‘三点(聊天信息)’上保持不动，然后按回车开始校准…")
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    off_right = top_rect.right - pt.x
    off_top   = pt.y - top_rect.top
    save_offset(int(off_right), int(off_top))
    print(f"✅ 校准完成：off_right={off_right}, off_top={off_top}（已保存到 {CONFIG_FILE}）。")

# ===== 核心：强制以“顶级父窗口右上角”为锚点，只点击 R2C2 一次 =====
def open_chat_info_via_topright_anchor(win_spec, use_calibration=True):
    app = win_spec.app
    top_spec = get_top_level_spec(app, win_spec)
    top_spec.set_focus()
    rect, hwnd = get_top_level_rect(top_spec)

    if ANCHOR_PRIME_CLICK:
        anchor_x = rect.right - 2
        anchor_y = rect.top + 2
        mouse.move(coords=(anchor_x, anchor_y)); time.sleep(0.05)
        mouse.click(button='left', coords=(anchor_x, anchor_y)); time.sleep(0.1)

    saved = load_saved_offset() if use_calibration else None
    if saved:
        off_right, off_top = saved
    else:
        dpi   = get_dpi_for_window(hwnd)
        scale = dpi / 96.0
        off_right = int(round(OFF_RIGHT_FROM_EDGE * scale))
        off_top   = int(round(OFF_TOP_FROM_EDGE   * scale))

    x0 = rect.right - off_right
    y0 = rect.top   + off_top

    dpi   = get_dpi_for_window(hwnd)
    scale = dpi / 96.0
    row_step = int(round(ROW_STEP_PX * scale))
    col_step = int(round(COL_STEP_PX * scale))

    x = x0 - col_step * (TARGET_COL - 1)
    y = y0 + row_step * (TARGET_ROW - 1)

    mouse.move(coords=(x, y)); time.sleep(0.06)
    mouse.click(button='left', coords=(x, y)); time.sleep(0.22)

# ========== 读取标题中的人数（用于小群/大群下移判断） ==========
def _parse_member_count_from_title(win_spec) -> int:
    try:
        wrapper = win_spec.wrapper_object().top_level_parent()
        title = wrapper.window_text() or ""
        m = re.search(r"[\(（]\s*(\d+)\s*[\)）]\s*$", title)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0

# ===== 打开“群公告”（纯坐标；>12 下移；单击后立即返回）=====
def open_group_announcement(win_spec):
    global LAST_TOP_HANDLE
    app = win_spec.app
    top_spec = get_top_level_spec(app, win_spec)
    rect, top_hwnd = get_top_level_rect(top_spec)
    LAST_TOP_HANDLE = top_hwnd  # 记录顶级父窗口句柄（备用）

    member_count = _parse_member_count_from_title(win_spec)
    is_large = member_count > 12

    # 写死坐标（小群/大群仅在纵向上下移）
    x_base = rect.right - 120
    y_small = rect.top + 420
    y_large = rect.top + 460
    y0 = y_large if is_large else y_small

    mouse.move(coords=(x_base, y0)); time.sleep(0.05)
    mouse.click(button='left', coords=(x_base, y0)); time.sleep(0.25)
    return

# ======= 兜底点击工具 =======
def click_by_topright_offset_for_spec(win_spec, off_right=100, off_top=100):
    rect, _ = get_top_level_rect(win_spec)
    x = rect.right - off_right
    y = rect.top + off_top
    mouse.move(coords=(x, y)); time.sleep(0.05)
    mouse.click(button='left', coords=(x, y)); time.sleep(0.15)

def click_by_topright_offset_for_edit(edit_win_spec, off_right=100, off_top=100):
    r = edit_win_spec.rectangle()
    x = r.right - off_right
    y = r.top + off_top
    mouse.move(coords=(x, y)); time.sleep(0.05)
    mouse.click(button='left', coords=(x, y)); time.sleep(0.15)

def click_by_bottomright_offset(win_like_spec, off_right=120, off_bottom=60):
    r = win_like_spec.rectangle()
    x = r.right - off_right
    y = r.bottom - off_bottom
    mouse.move(coords=(x, y)); time.sleep(0.05)
    mouse.click(button='left', coords=(x, y)); time.sleep(0.15)

# ===== 新增：获取当前前台窗口 spec（用于“直接输入”与按钮兜底） =====
def _get_foreground_spec(app):
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd:
            return app.window(handle=hwnd)
    except Exception:
        pass
    return None

def click_center_of_chat_window(app, delay_sec: float = 0.25):
    """在指定群聊的独立窗口上点击一次中心位置（用于关闭右侧侧边栏）"""
    global LAST_TOP_HANDLE
    if not LAST_TOP_HANDLE:
        return
    try:
        win = app.window(handle=LAST_TOP_HANDLE)
        win.set_focus()
        # 给窗口一点时间成为前台
        time.sleep(delay_sec)
        rect = win.rectangle()
        cx = int((rect.left + rect.right) / 2)
        cy = int((rect.top + rect.bottom) / 2)
        mouse.move(coords=(cx, cy)); time.sleep(0.05)
        mouse.click(button='left', coords=(cx, cy)); time.sleep(0.10)
    except Exception:
        pass

# ===== 编辑并发布（改为：点击群公告后，直接输入；按钮 UIA→坐标兜底）=====
def edit_and_publish_announcement(app, content: str):
    """
    点击‘群公告’后立即输入：不再用 ESC，改为 Ctrl+A + Backspace 清空。
    然后输入内容 → 在【编辑窗本体】右上角偏移点击完成 → 点击发布（编辑窗中心→右下偏移，单击一次）。
    """
    # 给编辑区一点时间获得焦点
    time.sleep(0.35)

    # —— 先把焦点“锁”到可输入区域 —— #
    fg = _get_foreground_spec(app)
    if fg is not None:
        focused = False
        try:
            doc = fg.child_window(control_type="Document")
            if doc.exists(timeout=0.6):
                _wait_exists(doc, 2.0)
                doc.click_input()
                focused = True
        except Exception:
            pass
        if not focused:
            try:
                r = fg.rectangle()
                cx = int((r.left + r.right) / 2)
                cy = int((r.top + r.bottom) / 2) + 40
                mouse.move(coords=(cx, cy)); time.sleep(0.05)
                mouse.click(button='left', coords=(cx, cy)); time.sleep(0.10)
            except Exception:
                pass

    # —— 清空：仅 Ctrl+A + Backspace（不发送 ESC） —— #
    send_keys("^a"); time.sleep(0.05)
    send_keys("^a"); time.sleep(0.05)
    send_keys("{BACKSPACE}")
    timings.wait_until_passes(1.0, 0.2, lambda: True)

    # —— 输入新内容 —— #
    if content:
        send_keys(content, with_spaces=True, pause=0.02)

    # ========== 锁定“编辑窗本体”并在其内点【完成】 ==========
    def _locate_editor_window():
        ed = app.window(title_re=r".+的群公告$")
        if ed.exists(timeout=0.5):
            return ed
        candidates = []
        for w in app.windows():
            try:
                doc = w.child_window(control_type="Document")
                if doc.exists(timeout=0.15):
                    rr = w.rectangle()
                    if (rr.right - rr.left) > 300 and (rr.bottom - rr.top) > 200:
                        candidates.append((rr.width() * rr.height(), w))
            except Exception:
                continue
        if candidates:
            return sorted(candidates, key=lambda t: t[0], reverse=True)[0][1]
        return _get_foreground_spec(app)

    editor = _locate_editor_window()
    if editor is None:
        raise RuntimeError("未能锁定群公告编辑窗口。")

    try:
        editor.set_focus()
    except Exception:
        pass

    # —— 在编辑窗右上角相对偏移点击“完成”（仅窗口内坐标） —— #
    try:
        r = editor.rectangle()
        x = r.right - 40   # 你的界面上“完成”更靠右上，这里已调小偏移
        y = r.top   + 60
        mouse.move(coords=(x, y)); time.sleep(0.05)
        mouse.click(button='left', coords=(x, y)); time.sleep(0.20)
    except Exception:
        pass

    # ========== 点击“发布”：以编辑窗为参考，窗口中心 → 右下偏移单击一次 ==========
    # 说明：确认框位于编辑窗中央，绿色“发布”在其右下侧。为避免点到外面，不再做 UIA/桌面兜底。
    try:
        r = editor.rectangle()
        # 根据 DPI 进行缩放后的偏移（可按需微调）
        hwnd = editor.wrapper_object().handle
        dpi = get_dpi_for_window(hwnd)
        scale = dpi / 96.0

        dx = int(round(80 * scale))   # 从中心向右偏移
        dy = int(round(40  * scale))   # 从中心向下偏移

        cx = int((r.left + r.right) / 2)
        cy = int((r.top  + r.bottom) / 2)
        px = cx + dx
        py = cy + dy

        mouse.move(coords=(px, py)); time.sleep(0.06)
        mouse.click(button='left', coords=(px, py)); time.sleep(0.20)
    except Exception:
        # 不做任何兜底，避免点击到编辑窗外
        pass
        # —— 发布点击完成后，回到该群的独立窗口中心点一下，收起侧边栏 —— #
    click_center_of_chat_window(app, delay_sec=0.35)




# ===== 主流程 =====
def post_group_announcement(group_name: str, content: str, need_calibration=False):
    """
    顶级父窗口锚定：
      右上角 prime-click → 以右上角为锚点仅点击 R2C2 打开侧栏
      → 纯坐标点击‘群公告’（人数>12 下移；单击后立即返回）
      → 直接输入（Esc→Ctrl+A→Backspace→内容）→ 完成 → 发布
    """
    app = connect_wechat()
    win_spec = find_chat_window(app, group_name)

    if need_calibration:
        calibrate_offset_via_topright(win_spec)

    open_chat_info_via_topright_anchor(win_spec, use_calibration=True)
    open_group_announcement(win_spec)
    edit_and_publish_announcement(app, content)
    print("✅ 已发布群公告（点击群公告后即直接输入）。")

# ===== 示例 =====
if __name__ == "__main__":
    post_group_announcement("测试1群", "群公告1测试", need_calibration=False)
