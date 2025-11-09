````markdown
 wxautomation · 开源「wxauto PLUS 功能替代」✨

> 非官方、零注入、零 Hook 的桌面微信自动化脚本集合。  
> 基于 Windows UIA（pywinauto） + 轻量图像匹配（pyautogui），逐步替代 `wxauto` PLUS 版的常用能力。


 🧭 项目宗旨

- 我们不是 `wxauto` 的开发者；本仓库旨在提供一个**开源替代**，复刻并扩展其 PLUS 版本常用能力；
- 坚持可读、可维护、可复用：优先使用官方 UI 自动化接口（UIA），避免系统注入和复杂 Hook；
- 小步快跑，持续迭代。
- 适用于微信3.9.12版本，10月后新增功能仅支持4.0及以上版本

---

## 📦 安装
```bash
pip install -U wxauto pywinauto pyautogui pillow pyperclip PyQt5
````

---

## 📂 模块一览

### 1) 批量获取「最近群聊」名称

目录：`wxautomation_Retrieve the group name from the address book/`
**思路**：进入页面用 `pyautogui` 定位入口，采集时切换 `pywinauto (UIA)` 读取列表，**固定步长滚动 + 锚点续扫**，降低“回弹/漏扫”。
**运行**

```bash
cd "wxautomation_Retrieve the group name from the address book"
python Contact_list_group_chat_acquisition.py
```

### 2) 群聊“@所有人 / @指定成员”

目录：`WeChat_group_@_everyone_function/`
脚本：`WeChat_group_@_everyone_function.py`
**能力**：

* 搜索框输入群名 → **回车**进入首个结果；
* 输入 `@` 后把鼠标**移入**候选面板 `ChatContactMenu`，**滚到顶部**并**仅点击**“所有人/全体成员/所有成员”；

  * 拿不到该节点时，用“**群成员**”分隔条做锚点，点击其**上方一行**（即“所有人”）；
  * 不造假 @：候选里没有“所有人”时仅发正文；
  * 不用 ESC（避免关闭微信），失败仅用 Backspace 清理。
* 也支持 **@ 指定成员**（多名自动分批）。

**快速试用**

```bash
cd WeChat_group_@_everyone_function
python WeChat_group_@_everyone_function.py
```

**在你的工程中使用**

> 目录名含 `@` 不便 import，可重命名脚本为 `wechat_group_at_all.py` 再导入。

```python
from wxauto import WeChat
from wechat_group_at_all import bind_AtAll  # ← 若已重命名

wx = WeChat()
bind_AtAll(wx)  # 动态挂载 wx.AtAll(...)

wx.AtAll("""通知：
下午xxxx
xxxx
测试使用""", group="测试1群")
```

**API**

```python
wx.AtAll(
    content: str,                 # 多行正文
    group: str,                   # 群名称（用于搜索跳转）
    names: Iterable[str] = None,  # @ 指定成员名单；为空则尝试 @所有人
    max_per_msg: int = 12,        # 每条消息最多 @ 人数（自动分批）
    mention_first: bool = True    # True: 先 @ 后正文；False: 先正文后 @
) -> bool
```

### 3) 任务栏唤起并发送

目录：`send_wechat_message_to_minimized_chat/`  
脚本：`send_wechat_message_to_minimized_chat.py`

**能力**：当微信所有窗口最小化、或聊天已“独立窗口化”时，先尝试**按窗口标题**直接前置；若不可见，则通过**任务栏 → “任务切换”列表**唤起目标群聊窗口，随后自动**粘贴并发送**文本。已可同时兼容中文/英文系统（`任务栏|Taskbar`、`任务切换程序|Task switching|Task View`、`微信|WeChat`）。

**快速试用**
```bash
cd send_wechat_message_to_minimized_chat
python send_wechat_message_to_minimized_chat.py "测试3群" "今晚八点上新！"
```
**在你的工程中使用**
```python
from send_wechat_message_to_minimized_chat import send_wechat_message_to_minimized_chat

ok = send_wechat_message_to_minimized_chat("测试3群", "Hello from automation!")
print("OK" if ok else "FAILED")
```
**API**

```python
send_wechat_message_to_minimized_chat(
    chat_title: str,              # 目标独立聊天窗口标题（群名），如 "测试3群"
    text: str,                    # 要发送的文本
    timeout: float = 5.0          # 任务栏“任务切换”兜底路径的等待秒数
) -> bool                         # 成功唤起并发送返回 True

```
### 4) 位置卡片解析

目录：`location_message_retrieval/`  
脚本：`location_message_retrieval/location.py`

**能力**：在当前聊天窗口中，定位最近一条**位置卡片**并解析出 **昵称、详细地址、地点/店名**，按顺序返回：
`[sender, address, title]`。适配**群聊/私聊**两种布局；通过 UIAutomation（pywinauto）获取控件文本，使用更严格的中文地址规则避免把“××路店”这类店名误识为地址。详见源码内 `LocationMessage(chat_title: str) -> Optional[List[str]]`。:contentReference[oaicite:1]{index=1}

**快速试用**
```bash
cd location_message_retrieval
python location.py
```
**在你的工程中使用**
```python
from location_message_retrieval.location import LocationMessage

print(LocationMessage("XXX"))   # 群聊
print(LocationMessage("XXX"))     # 私聊
# 返回形如：['昵称', 'XXX省XXX市……', 'XXXX店']
```
**API**

```python
from typing import Optional, List
from location_message_retrieval.location import LocationMessage

def LocationMessage(chat_title: str) -> Optional[List[str]]:
    """
    参数：
      chat_title: 聊天窗口标题前缀（群名或联系人名），如 "测试3群" / "XXX"
    返回：
      [sender, address, title, source]
        - sender : 发送者昵称（群聊为成员昵称，私聊为对方昵称）
        - address: 详细地址（例如“XX省XX市……”）
        - title  : 地点/店名（例如“XXX店”）
        - source : 群聊返回群名称；私聊返回 'private'
      若未找到“位置卡片”则返回 None
    """


```

### 5) 指定群聊发布群公告

目录：`Edit_Group_Announcement_for_the_Specified_Group/`  
脚本：`Edit_Announcement.py`

**能力** 
- 在“指定群聊的独立窗口”中，精确点开右上角 **…（聊天信息）**，打开侧边栏后点击 **群公告**。  
- 进入编辑页后：**Ctrl+A + Backspace** 清空 → 输入新内容 → 在编辑窗**右上角**点击 **完成** → 在弹出的确认框上，**以编辑窗中心为基准向右下偏移**点击 **发布**。  
- 发布成功后，自动回到该群的独立聊天窗口，在**窗口中心点击一次**，**收起右侧侧边栏**（新功能）。

**细节**  
- 始终以**顶级父窗口右上角**为锚点定位，不依赖不稳定的层级结构。  
- 通过群标题括号人数判断“小群/大群”（> **12** 视为大群），在侧边栏中选择更合适的 **群公告** 纵向坐标。  
- 提供一次性**偏移校准**：把鼠标移到三点按钮上按回车，会保存相对偏移，之后点击更稳。  
- 不使用 `ESC`（避免把编辑窗口关掉），仅使用 `Ctrl+A + Backspace` 清空内容。

**快速试用**
```bash
python Edit_Announcement.py
```
**在你的工程中使用**
```python
from Edit_Announcement import post_group_announcement
post_group_announcement("测试1群", "群公告1测试", need_calibration=False)
# 第一次可设 need_calibration=True 做一次右上角偏移校准
```
### 6) 打开微信主界面的「朋友圈」

目录：`open_moments/`  
脚本：`open_moments.py`

**能力** 
- 自动查找“微信”主窗口。如果窗口已最小化或被遮挡，则自动尝试从任务栏图标将其唤醒至前台。  
- 坐标定位：以主窗口左上角为锚点，结合 DPI 缩放和固定的 (X, Y) 偏移量，精确定位并点击“朋友圈”图标。  
- 点击后，通过 UIA 查找弹出的“朋友圈”窗口，确保操作成功。

**快速试用**
```bash
python open_moments.py
```
**在你的工程中使用**
```python
from open_moments import open_wechat_moments
ok = open_wechat_moments()
if ok:
    print("成功打开朋友圈！")
```


---

## 🧱 目录结构（简）

```
wxautomation/
├─ README.md
├─ wxautomation_Retrieve the group name from the address book/
│  └─ Contact_list_group_chat_acquisition.py
└─ WeChat_group_@_everyone_function/
   └─ WeChat_group_@_everyone_function.py
└─ send_wechat_message_to_minimized_chat/
   └─ send_wechat_message_to_minimized_chat.py
└─ location_message_retrieval/
   └─ location.py
└─ Edit_Group_Announcement_for_the_Specified_Group/
   └─ Edit_Announcement.py
```

---

## 🔧 常见问题

* **@ 后被输入法替换成特殊符号**：切英文输入或关闭符号联想；脚本会在真正点中“所有人”后补空格完成 @。
* **滚轮不动**：确保显示缩放 100%；脚本已在滚动前把鼠标移动到面板内部。

---

## 👥 co-worker

<p align="left">
  <a href="https://github.com/1JSK1" title="1JSK1">
    <img src="https://github.com/1JSK1.png?size=96" width="80" height="80" style="border-radius:50%; margin-right:12px;" alt="1JSK1"/>
    <br/><sub><b>1JSK1</b></sub>
  </a>
</p>

---

## 📜 免责声明

* 本项目与腾讯/微信、`wxauto` 无官方关联；仅用于学习研究 Windows UI 自动化。
* 使用本项目造成的一切后果由使用者自行承担，请遵守相关法律与平台条款。

```
```
