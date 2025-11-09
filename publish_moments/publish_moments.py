# -*- coding: utf-8 -*-
#
# post_to_moments.py (v1.5.3 - 精确定位发表按钮版)
# 
import time
import os 
from pywinauto import Application, Desktop
import pyautogui 
import pyperclip 

# =================================================================
# 
# ⚠️ 校准参数 ⚠️
#
# =================================================================

# --- post_new_moment ---
CAMERA_OFFSET_X = 70  # 距左边缘的像素
CAMERA_OFFSET_Y = 10  # 距上边缘的像素

# --- 发表按钮位置 ---
PUBLISH_OFFSET_X = -70   # 从窗口中心向左移动70像素
PUBLISH_OFFSET_Y = 200   # 从窗口中心向下移动200像素


# =================================================================
# API: "发布朋友圈" (v1.5.3 - 精确定位发表按钮版)
# =================================================================
def post_new_moment(image_path: str, caption: str = "") -> bool:
    """
    在【已打开】的朋友圈窗口，点击"发布"按钮，选择图片并发布。
    
    :param image_path: 要发布的图片的完整路径
    :param caption: 要发布的文案内容
    :return: bool - 成功返回 True
    """
    try:
        print(f"\n--- 正在执行 [post_new_moment] API ---")
        print(f"   > 目标图片: {image_path}")
        print(f"   > 发布文案: {caption}")
        
        # 使用 UIA 后端
        desk_uia = Desktop(backend="uia")
        
        # 1. 首先连接到已打开的 "朋友圈" 窗口
        try:
            moments_win = desk_uia.window(title="朋友圈")
            moments_win.wait("exists", timeout=3)
            moments_win.set_focus()
        except Exception as e:
            print(f"   ❌ 错误：找不到 '朋友圈' 窗口。请确保朋友圈窗口已打开。 {e}")
            return False
            
        rect_obj = moments_win.rectangle()
        region = (rect_obj.left, rect_obj.top, rect_obj.width(), rect_obj.height())
        print(f"   ✅ 朋友圈窗口已定位: {region}")
        
        # --- 步骤 1: 点击"相机"按钮 ---
        click_x = rect_obj.left + CAMERA_OFFSET_X
        click_y = rect_obj.top + CAMERA_OFFSET_Y
        
        print(f"   > 1. 【移动】并【点击】相机按钮 (坐标: {click_x}, {click_y})")
        pyautogui.moveTo(click_x, click_y)
        time.sleep(0.5)
        pyautogui.click()
        
        print(f"   > 2. 【等待】 2.0 秒，等待文件对话框...")
        time.sleep(2.0)
        
        # --- 步骤 2: 选择文件操作 ---
        print(f"   > 3. 【相对移动】到目录位置")
        
        # 从当前鼠标位置（相机按钮）相对移动
        pyautogui.moveRel(500, 35, duration=0.3)
        time.sleep(0.5)
        
        # 点击目录位置
        pyautogui.click()
        time.sleep(0.5)
        
        # 粘贴文件夹路径
        folder_path = os.path.dirname(image_path)
        print(f"   > 4. 【粘贴】文件夹路径: {folder_path}")
        pyperclip.copy(folder_path)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)
        
        # 按回车确认路径
        pyautogui.press('enter')
        time.sleep(1.0)
        
        # 输入文件名
        file_name = os.path.basename(image_path)
        print(f"   > 5. 【输入】文件名: {file_name}")
        
        # 连续按5次Tab键到达文件名输入位置
        print(f"   > 6. 【按5次Tab键】导航到文件名输入框")
        pyautogui.press('tab', presses=5, interval=0.1)
        time.sleep(0.5)
        
        # 输入文件名
        pyautogui.hotkey('ctrl', 'a')
        pyperclip.copy(file_name)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)
        
        # 按回车确认选择
        pyautogui.press('enter')
        time.sleep(2)
        
        print("   ✅ 文件选择成功完成")
        
        # --- 步骤 3: 强制粘贴文案 ---
        if caption:
            print(f"   > 7. 【强制粘贴】文案内容")
            
            # 等待朋友圈发布界面加载完成
            time.sleep(1.0)
            
            # 确保文案在剪贴板中
            pyperclip.copy(caption)
            
            # 强制粘贴到朋友圈文本输入框
            # 先尝试点击文本输入区域（"这一刻的想法..."位置）
            # 根据图片，文本输入框位于窗口上半部分
            text_input_x = rect_obj.left + rect_obj.width() // 2
            text_input_y = rect_obj.top + rect_obj.height() // 4
            pyautogui.click(text_input_x, text_input_y)
            time.sleep(0.5)
            
            # 全选现有文本（如果有）并粘贴新文案
            pyautogui.hotkey('ctrl', 'a')  # 全选
            pyautogui.hotkey('ctrl', 'v')  # 强制粘贴
            time.sleep(1.0)
            
            print("   ✅ 文案已强制粘贴到朋友圈")
            
            # 等待5秒
            print(f"   > 8. 【等待】 5 秒...")
            time.sleep(5.0)
        
        # --- 步骤 4: 点击发表按钮 ---
        print(f"   > 9. 【点击】发表按钮")
        
        # 计算发表按钮位置：窗口正中间，向下200像素，向左70像素
        center_x = rect_obj.left + rect_obj.width() // 2
        center_y = rect_obj.top + rect_obj.height() // 2
        
        publish_x = center_x + PUBLISH_OFFSET_X  # 向左70像素
        publish_y = center_y + PUBLISH_OFFSET_Y  # 向下200像素
        
        print(f"   >    窗口中心坐标: ({center_x}, {center_y})")
        print(f"   >    发表按钮坐标: ({publish_x}, {publish_y})")
        
        # 移动并点击发表按钮
        pyautogui.moveTo(publish_x, publish_y, duration=0.5)
        pyautogui.click()
        time.sleep(2)
        
        print("   ✅ 朋友圈发布成功完成")
        return True

    except Exception as e:
        print(f"\n❌ [post_new_moment] API 发生错误: {e}")
        return False


# =================================================================
# 启动
# =================================================================
if __name__ == "__main__":
    
    # 请在这里填入你想要发布的图片的完整路径
    YOUR_IMAGE_PATH = r"C:\Users\Wang\Desktop\个人照片\XXX.jpg"
    
    # 请在这里填入你想要发布的文案内容
    YOUR_CAPTION = "分享一张个人照片"
    
    print("--- 微信朋友圈自动化 (v1.5.3 - 精确定位发表按钮版) ---")
    print(f"!!! 目标图片: {YOUR_IMAGE_PATH}")
    print(f"!!! 发布文案: {YOUR_CAPTION}")
    print(f"!!! 发表按钮偏移: 左{PUBLISH_OFFSET_X}px, 下{PUBLISH_OFFSET_Y}px")
    print("将在 3 秒后开始测试...")
    print("!!! 请确保朋友圈窗口已打开并显示在最前端 !!!")
    time.sleep(3)
    
    # 测试 API
    success = post_new_moment(image_path=YOUR_IMAGE_PATH, caption=YOUR_CAPTION)
    
    print("\n=====================")
    print(f"API 调用结果: {success}")
    print("=====================")