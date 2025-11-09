# -*- coding: utf-8 -*-
#
# open_moments.py (v7.2 - “PageDown” 终极版)
# 
# 功能：
# 1. (已移除) 打开朋友圈 API
# 2. (保留) "视觉+偏移法" 滚动点赞 (like_moments_by_pagedown)
# 
# ⚠️ 必须安装: pip install pyautogui opencv-python
# ⚠️ 必须有 1 张截图: 
#    1. ellipsis_button.png (来自)
#
import time
import ctypes
from pywinauto import Application, Desktop, mouse
import pyautogui # (v6.1) 导入核心库
try:
    import cv2 # pyautogui 需要它
except ImportError:
    pass

# =================================================================
# 
# ⚠️ 校准参数 ⚠️
#
# =================================================================

# --- like_moments_by_pagedown ---
# (v6.3) 图像识别文件名 (只需要这一个！)
ELLIPSIS_BUTTON_IMAGE = 'ellipsis_button.png'   # 两个点的按钮

# (v6.7) “赞”按钮在“...”按钮左侧的【固定 X 偏移量】
LIKE_CLICK_OFFSET_X = 200 # (待校准) 假设“赞”在“...”左侧 200 像素

# 图像识别的相似度
CONFIDENCE_LEVEL = 0.85


# =================================================================
# API: "视觉+偏移法" 滚动点赞 (v7.2)
# =================================================================
def like_moments_by_pagedown(target_like_count: int) -> int:
    """
    在【已打开】的朋友圈窗口，使用“视觉+PageDown”滚动点赞。
    (查找“...” -> 点击 -> 点击“...”左侧 -> 循环整页 -> PageDown)
    
    :param target_like_count: 目标点赞数量
    :return: int - 实际点赞数量
    """
    try:
        print(f"\n--- 正在执行 [like_moments_by_pagedown] API (目标: {target_like_count}) ---")
        
        desk = Desktop(backend="uia")
        
        # 1. 首先连接到已打开的 "朋友圈" 窗口
        try:
            moments_win = desk.window(title="朋友圈")
            moments_win.wait("exists", timeout=3)
            moments_win.set_focus()
        except Exception as e:
            print(f"   ❌ 错误：找不到 '朋友圈' 窗口。请确保朋友圈窗口已打开。 {e}")
            return 0
            
        rect_obj = moments_win.rectangle()
        region = (rect_obj.left, rect_obj.top, rect_obj.width(), rect_obj.height())
        print(f"   ✅ 朋友圈窗口已定位: {region}")
        
        # 3. 准备循环
        liked_count = 0
        scroll_attempts = 0 # 滚动次数，防止死循环
        
        # 4. 开始探测
        while liked_count < target_like_count and scroll_attempts < 20:
            
            print(f"\n--- 扫描屏幕 (第 {scroll_attempts + 1} 屏) ---")
            
            # (v7.2) 确保窗口是激活的，以便接收 PageDown
            moments_win.set_focus()
            time.sleep(0.2)
            
            # (v6.3 核心) 查找所有 "..." 按钮
            found_buttons = []
            try:
                found_buttons = list(pyautogui.locateAllOnScreen(
                    ELLIPSIS_BUTTON_IMAGE,
                    region=region,
                    confidence=CONFIDENCE_LEVEL
                ))
            except pyautogui.ImageNotFoundException:
                pass # 正常，没找到
            except Exception as e:
                print(f"   > 图像查找警告 (ellipsis): {e}")

            if not found_buttons:
                print("   > 当前屏幕未找到 '...' 按钮，视为已到底部。")
                scroll_attempts += 1 # 连续 20 次找不到就退出
                # (v7.2) 尝试再滚动一次，以防万一
                pyautogui.press('pagedown')
                time.sleep(1.5)
                continue # 继续下一次 while 循环
            else:
                print(f"   > 找到 {len(found_buttons)} 个 '...' 按钮。")
                scroll_attempts = 0 # 找到了，重置无效滚动
            
            sorted_buttons = sorted(found_buttons, key=lambda box: box.top)
            
            for button_box in sorted_buttons:
                if liked_count >= target_like_count: break
                
                center = pyautogui.center(button_box)
                
                # (v7.2) 删除了所有“记忆”检查，因为 PageDown 保证了是新页面

                # --- (v6.6) "一步一步" 慢动作 ---
                
                # 步骤 1.1: 【移动】到 "..."
                print(f"   > 1. 【移动】到 '...' (坐标: {center})")
                pyautogui.moveTo(center)
                time.sleep(0.5) 

                # 步骤 1.2: 【点击】 "..."
                print(f"   > 2. 【点击】 '...' (坐标: {center})")
                pyautogui.click() 
                
                # (v6.6) 等待弹窗 出现
                print(f"   > 3. 【等待】 1.5 秒...")
                time.sleep(1.5) 

                # 步骤 2.1: (v6.7) 【计算】“赞”的坐标 (你的“左移200”)
                like_x = center.x - LIKE_CLICK_OFFSET_X
                like_y = center.y
                
                # 步骤 2.2: 【移动】到“赞”
                print(f"   > 4. 【移动】到 '赞' (坐标: {like_x}, {like_y})")
                pyautogui.moveTo(like_x, like_y)
                time.sleep(0.5) 
                
                # 步骤 2.3: 【点击】“赞”
                print(f"   > 5. 【点击】 '赞' (坐标: {like_x}, {like_y})")
                pyautogui.click()

                liked_count += 1
                print(f"   > ✅ 点赞 {liked_count} / {target_like_count} 完成。")
                
                # (v6.6) 等待菜单关闭
                print(f"   > 6. 【等待】 1.5 秒...")
                time.sleep(1.5) 
            
            # 5. (v7.2 核心) 【翻页】
            #    在处理完本页所有按钮后
            if liked_count < target_like_count:
                print(f"--- 本屏处理完毕，执行【PageDown】翻页... ---")
                
                # (v7.2) 确保窗口激活，然后按 PageDown
                moments_win.set_focus()
                pyautogui.press('pagedown')
                
                time.sleep(1.5) # 等待新内容加载

        print(f"\n--- [like_moments_by_pagedown] API 结束，总共点赞 {liked_count} 个 ---")
        return liked_count
        
    except Exception as e:
        print(f"\n❌ [like_moments_by_pagedown] API 发生严重错误: {e}")
        return 0

# =================================================================
# 启动 (v7.2)
# (假设朋友圈窗口【已经打开】)
# =================================================================
if __name__ == "__main__":
    print("--- 微信朋友圈自动化 (v7.2 - “PageDown” 终极版) ---")
    print("!!! 必须安装: pip install pyautogui opencv-python")
    print(f"!!! 必须有 1 张截图: {ELLIPSIS_BUTTON_IMAGE}")
    print(f"!!! 必须校准: LIKE_CLICK_OFFSET_X = {LIKE_CLICK_OFFSET_X}")
    print("将在 3 秒后开始测试 [like_moments_by_pagedown]...")
    print("!!! 请确保朋友圈窗口已打开并显示在最前端 !!!")
    time.sleep(3)
    
    # --- 测试 API ---
    total_liked = like_moments_by_pagedown(target_like_count=5) # 目标：点赞5个
    
    print("\n=====================")
    print(f"API 调用结果: 成功点赞 {total_liked} 个。")
    print("=====================")