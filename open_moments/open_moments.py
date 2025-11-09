# -*- coding: utf-8 -*-
#
# open_moments.py (v4.0 - 最终 API 封装版)
# 
# 功能：打开微信朋友圈
# API:
#   open_wechat_moments() -> bool:
#       打开朋友圈，成功返回 True，失败返回 False
#
# 策略：
# 1. 智能查找：先尝试直接找 "微信" 窗口。
# 2. 健全性检查：如果找到，检查坐标是否为 (0, 0)。
# 3. 如果找不到或坐标为 (0, 0)，则执行“任务栏唤醒”。
# 4. 结合 rect 和 DPI 缩放，计算偏移量并点击。
# 5. 验证 "朋友圈" 窗口是否弹出。
#
import time
import ctypes
from pywinauto import Application, Desktop, mouse

# =================================================================
# 
# ⚠️ 启动前必须校准 ⚠️
#
# （基于 100% 缩放 / 96 DPI，从微信主窗口【左上角】量起）
#
# =================================================================
MOMENTS_OFFSET_X = 30   # (待校准) 朋友圈图标中心，距离窗口【左】边缘的像素
MOMENTS_OFFSET_Y = 220  # (待校准) 朋友圈图标中心，距离窗口【上】边缘的像素

# =================================================================
# 内部辅助函数
# =================================================================

def _get_dpi_for_window(hwnd) -> int:
    """获取指定窗口的 DPI 值"""
    try:
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        return int(dpi) if dpi > 0 else 96
    except Exception:
        return 96

def _awaken_wechat_from_taskbar(desk: Desktop) -> bool:
    """
    点击任务栏上的“微信”图标来激活主窗口
    """
    print("   > [唤醒] 正在查找任务栏 (Shell_TrayWnd)...")
    try:
        taskbar = desk.window(class_name="Shell_TrayWnd")
        if not taskbar.exists(timeout=2):
            taskbar = desk.window(title_re="任务栏|Taskbar", control_type="Pane")
        if not taskbar.exists(timeout=2):
            print("   > ❌ [唤醒] 错误：找不到任务栏。")
            return False
    except Exception as e:
        print(f"   > ❌ [唤醒] 错误：查找任务栏时出错: {e}")
        return False

    print("   > [唤醒] 正在查找任务栏中的“微信”图标...")
    wx_btn = None
    try:
        wx_btn = taskbar.child_window(title_re=r"^微信", control_type="Button")
        if wx_btn.exists(timeout=1): print("   > ✅ [唤醒] 策略 A 找到: '微信' Button")
    except Exception: wx_btn = None

    if not wx_btn or not wx_btn.exists():
        print("   > ❌ [唤醒] 错误：在任务栏上找不到“微信”图标。")
        return False

    print("   > [唤醒] 正在模拟点击任务栏图标...")
    try:
        wx_btn.click_input()
        print("   > ✅ [唤醒] 点击成功。")
        return True
    except Exception as e:
        print(f"   > ❌ [唤醒] 错误：点击图标时失败: {e}")
        return False

def _find_or_awaken_main_window(desk: Desktop):
    """
    智能查找主窗口，并增加 (0, 0) 坐标检查。
    """
    print("1. 正在尝试直接查找 '微信' 窗口...")
    
    win_spec = desk.window(title="微信")
    
    try:
        if win_spec.exists(timeout=1.5):
            rect = win_spec.rectangle()
            if rect.left == 0 and rect.top == 0:
                 print("   ⚠️ 窗口 '存在' 但坐标为 (0,0)，视为无效（可能已最小化）。")
            else:
                print("   ✅ 窗口已在桌面上，无需唤醒。")
                return win_spec, rect
    except Exception:
        pass 

    print("2. 窗口未找到或坐标无效，正在尝试从任务栏唤醒...")
    
    if not _awaken_wechat_from_taskbar(desk):
        raise RuntimeError("从任务栏唤醒失败。")
        
    print("3. 唤醒成功，正在重新查找窗口...")
    
    try:
        win_spec = desk.window(title="微信") 
        win_spec.wait("exists", timeout=5)
        rect = win_spec.rectangle()
        
        if rect.left == 0 and rect.top == 0:
            raise RuntimeError("唤醒后获取的坐标依然是 (0,0)。")
            
        print("   ✅ 唤醒后成功找到窗口。")
        return win_spec, rect
        
    except Exception as e:
        raise RuntimeError(f"唤醒后查找窗口失败: {e}")

def _verify_moments_window(main_window_handle) -> bool:
    """
    验证 "朋友圈" 窗口是否弹出
    """
    print("5. 正在验证“朋友圈”窗口是否弹出...")
    try:
        app = Application(backend="uia").connect(handle=main_window_handle)
        moments_win = app.window(title="朋友圈") 
        
        moments_win.wait("exists ready visible enabled", timeout=10)
        moments_win.set_focus()
        print(f"   ✅ 验证成功！已聚焦到“朋友圈”窗口 (Handle: {moments_win.handle})。")
        return True
    except Exception as e:
        print(f"   ⚠️ 验证失败：未能检测到“朋友圈”弹出窗口。{e}")
        return False

# =================================================================
# 公开 API (Public API)
# =================================================================
def open_wechat_moments() -> bool:
    """
    执行打开微信朋友圈的完整流程。
    
    1. 智能查找并激活微信主窗口
    2. 获取主窗口坐标 (修复 0,0 问题)
    3. 计算 DPI 和偏移量
    4. 模拟鼠标点击
    5. 验证“朋友圈”窗口是否弹出
    
    :return: bool - 成功打开并验证返回 True, 否则返回 False
    """
    try:
        print("--- 正在执行 [open_wechat_moments] API ---")
        
        desk = Desktop(backend="uia")
        
        # --- 第一步 & 第二步：智能查找与定位 ---
        main_win, rect = _find_or_awaken_main_window(desk)
        
        print(f"\n   > 坐标 (Left, Top): ({rect.left}, {rect.top})")
        
        # --- 第三步：计算 & 点击 ---
        print("4. 正在计算DPI缩放与最终坐标...")
        
        hwnd = main_win.handle
        dpi = _get_dpi_for_window(hwnd)
        scale = dpi / 96.0
        
        click_x = rect.left + int(round(MOMENTS_OFFSET_X * scale))
        click_y = rect.top  + int(round(MOMENTS_OFFSET_Y * scale))
        
        print(f"   > DPI: {dpi} (Scale: {scale:.2f})")
        print(f"   > [!] 计算点击坐标 (X, Y): ({click_x}, {click_y})")
        
        mouse.move(coords=(click_x, click_y)); time.sleep(0.06)
        mouse.click(button='left', coords=(click_x, click_y)); time.sleep(0.25)
        print("   ✅ 点击执行完毕。")
        
        # --- 第四步：验证 ---
        success = _verify_moments_window(main_window_handle=hwnd)
        
        if success:
            print("--- [open_wechat_moments] API 执行成功 ---")
        else:
            print("--- [open_wechat_moments] API 执行失败 (验证步骤) ---")
            
        return success

    except Exception as e:
        print(f"\n❌ [open_wechat_moments] API 发生严重错误: {e}")
        return False

# ===== 启动 (用于直接运行此文件测试) =====
if __name__ == "__main__":
    print("--- 微信朋友圈自动化 (v4.0 - API 封装版) ---")
    print(f"请确保 M_OFFSET_X={MOMENTS_OFFSET_X}, M_OFFSET_Y={MOMENTS_OFFSET_Y} 已校准。")
    print("将在 3 秒后开始测试 API...")
    time.sleep(3)
    
    # 调用 API
    is_ok = open_wechat_moments()
    
    print("\n=====================")
    print(f"API 调用结果: {is_ok}")
    print("=====================")