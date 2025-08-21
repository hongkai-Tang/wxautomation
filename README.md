````markdown
 wxautomation · 开源「wxauto PLUS 功能替代」✨

> 非官方、零注入、零 Hook 的桌面微信自动化脚本集合。  
> 基于 Windows UIA（pywinauto） + 轻量图像匹配（pyautogui），逐步替代 `wxauto` PLUS 版的常用能力。


 🧭 项目宗旨

- 我们不是 `wxauto` 的开发者；本仓库旨在提供一个**开源替代**，复刻并扩展其 PLUS 版本常用能力；
- 坚持可读、可维护、可复用：优先使用官方 UI 自动化接口（UIA），避免系统注入和复杂 Hook；
- 小步快跑，持续迭代：先从'获取群列表'做起，逐步扩展更多自动化能力。
- 适用于微信3.9.12版本，4.0及以上版本未测试

---

 📂 当前功能模块

**`wxautomation_Retrieve the group name from the address book/`**

- 作用：从**通讯录管理**中，批量获取「**最近群聊**」的群名称；
- 特色：
  - 进入界面：通过 **pyautogui 模板匹配** 依次点击「通讯录 → 通讯录管理 → 最近群聊」；
  - 采集阶段：切换 **pywinauto (UIA)** 读取列表，**固定步长滚动**，不再“一下到底”；
  - **锚点续扫**：从**视口底部第一条可点击项**继续，减少回弹/漏扫；
  - **强力避坑**：自动跳过「最近群聊 / 全部 / 标签」等目录项，兼容头部遮挡（置顶）。

---

 📦 依赖（精简版）

本模块未使用 OpenCV，仅需以下依赖：

```python
import time
import ctypes
from collections import deque
from pywinauto import Application, Desktop, keyboard
from pywinauto.mouse import move as mouse_move
import pyautogui
````

**安装：**

```bash
pip install -U pywinauto pyautogui pillow
```

> ℹ️ 未安装 OpenCV 时，`pyautogui.locateOnScreen` 为像素级匹配；
> 请在当前分辨率与缩放（建议 100%）下截取干净的模板图（只保留图标/文字）。

---

## ⚡ 快速开始

1. **克隆仓库**

```bash
git clone https://github.com/hongkai-Tang/wxautomation.git
cd wxautomation
```

2. **准备模板图片**（与脚本放在同一目录）

```
contacts_button.png            # 左侧栏「通讯录」
contacts_manager_button.png    # 「通讯录管理」
groups_button.png              # 「最近群聊」
```

3. **运行示例脚本**

```bash
cd "wxautomation_Retrieve the group name from the address book"
python Contact_list_group_chat_acquisition.py
```

运行后，终端会滚动打印采集到的群聊名称列表。

---

## 🧱 目录结构（节选）

```
wxautomation/
├─ README.md
└─ wxautomation_Retrieve the group name from the address book/
   ├─ Contact_list_group_chat_acquisition.py   # 导航 + 采集主脚本（已更名）
   ├─ contacts_button.png                      # 模板：通讯录
   ├─ contacts_manager_button.png              # 模板：通讯录管理
   └─ groups_button.png                        # 模板：最近群聊
```

---

## ⚙️ 关键参数（可在脚本顶部调节）

| 参数名                      | 含义               | 建议范围           |
| ------------------------ | ---------------- | -------------- |
| `WAIT_AFTER_CLICK`       | 激活一行后等待 UI 刷新    | 0.30 \~ 0.60 s |
| `SLEEP_SCROLL`           | 每轮滚动之后的节奏控制      | 0.12 \~ 0.25 s |
| `WHEEL_NOTCHES_PER_STEP` | 每次固定滚动 notch 数   | 2 \~ 6         |
| `EXTRA_WHEEL_ON_STUCK`   | 无进展时追加补滚 notch 数 | 4 \~ 12        |
| `MAX_CONSEC_NO_PROGRESS` | 连续无进展判定到底/卡住     | 6 \~ 10        |

> 📌 小技巧：若「漏扫」→ 减小 `WHEEL_NOTCHES_PER_STEP`、增大 `WAIT_AFTER_CLICK`；
> 若「太慢」→ 适度增大滚动步长或降低 `WAIT_AFTER_CLICK`。

---

## ❓常见问题（FAQ）

**Q1：图片法为什么偶尔点不到？**

* 像素匹配对 DPI/缩放很敏感：请在\*\*当前 DPI/缩放（建议 100%）\*\*下重截模板，并只保留稳定区域（图标/文字）。

**Q2：UIA 找不到“通讯录管理”窗口？**

* 确认已经点击打开、未被遮挡，且微信与脚本权限一致（通常都非管理员）。

**Q3：采集时会“跳到底”或“回弹”？**

* 本脚本使用**固定步长滚动 + 锚点续扫**降低该风险；可再调低滚动步长、增大等待，或提高 `MAX_CONSEC_NO_PROGRESS`。

---

## 🗺️ Roadmap（持续更新）

* 群成员导出 / 过滤规则
* 批量发送 / 定时发送
* 联系人与标签的更多自动化操作
* 多 DPI/缩放的模板自适应工具
* 更丰富的 UIA 封装与稳定性增强

欢迎 PR / Issue，一起把「wxauto 的开源替代」做得更好！🚀

---

## 📜 免责声明

* 本项目与腾讯/微信、`wxauto` **无任何官方关联**；
* 仅用于**学习与研究** Windows UI 自动化；请遵守法律法规与平台条款；
* 使用本项目造成的任何后果由使用者自行承担。

---

## 🤝 贡献指南

* 提交 PR 时请保持一致的代码风格，并附最小复现步骤/截图；
* 新想法或需求，欢迎在 Issues 中讨论。

