# wxautomation · 开源「wxauto PLUS 功能替代」✨

> 非官方、零注入、零 Hook 的桌面微信自动化脚本集合。
> 基于 Windows UIA（pywinauto）+ 轻量图像匹配（pyautogui），逐步替代 `wxauto` PLUS 版的常用能力。&#x20;

## 🧭 项目宗旨

* 我们不是 `wxauto` 的开发者；本仓库旨在提供一个**开源替代**，复刻并扩展其 PLUS 版本常用能力；
* 坚持可读、可维护、可复用：优先使用官方 UI 自动化接口（UIA），避免系统注入和复杂 Hook；
* 小步快跑，持续迭代：已有获取群聊列表能力，新增**群聊 @所有人**能力；
* 适用于当前桌面版微信的常见版本（更高版本如有差异请提 Issue）。&#x20;

---

## 📂 功能模块

### 1) 从通讯录批量获取「最近群聊」名称

目录：`wxautomation_Retrieve the group name from the address book/`

* **作用**：从**通讯录管理**中批量获取「最近群聊」群名称
* **实现亮点**：UIA 读取列表 + 固定步长滚动 + 锚点续扫，稳定避坑（跳到底/回弹/置顶遮挡）
* **依赖**：`pywinauto`、`pyautogui`、`Pillow`
* **运行**：

  ```bash
  cd "wxautomation_Retrieve the group name from the address book"
  python Contact_list_group_chat_acquisition.py
  ```

（以上为原有模块的摘要，细节与参数说明请参考旧版 README 中对应章节）&#x20;

---

### 2) 群聊 **@所有人 / @指定人**（全新）

目录：`WeChat_group_@_everyone_function/`
脚本：`WeChat_group_@_everyone_function.py` &#x20;

**能做什么？**

* 一步到群：将群名精确写入**主界面搜索框** → **回车**进入**首个搜索结果**；
* 智能 @ 所有人：输入 `@` 后**悬停**至 `ChatContactMenu` 面板、自动**滚到顶部**并**只点击**「所有人 / 全体成员 / 所有成员」；

  * 若控件不可直接选中，使用\*\*“群成员”分隔条作为锚点，点击其上方一行\*\*的兜底策略；
  * **绝不发送假 @**（只有候选中存在“所有人”时才会插入 @）；
  * **不使用 ESC**（避免关闭微信），失败仅用 Backspace 清理；
* 也支持 **@ 指定成员**（支持多名，自动分批发送）；
* 细节同文件内实现注释。&#x20;

**快速开始**

```bash
pip install -U wxauto pywinauto pyautogui pillow pyperclip PyQt5
```

```python
# 示例：在“测试1群”里 @所有人 并发送多行通知
from wxauto import WeChat
from WeChat_group_@_everyone_function import bind_AtAll  # 当前脚本的对外入口

wx = WeChat()
bind_AtAll(wx)  # 给 wx 动态挂载 wx.AtAll(...)

group = "测试1群"
content = """通知：
下午xxxx
xxxx
测试使用"""

wx.AtAll(content, group)  # 若本群支持“所有人”，将会真正插入 @所有人 并发送正文
```

（更多示例见脚本底部 `__main__`）&#x20;

**API**

```python
wx.AtAll(
    content: str,              # 要发送的多行文本
    group: str,                # 群名称（用于搜索框跳转）
    names: Iterable[str] = None,  # 可选：@ 指定成员名单
    max_per_msg: int = 12,        # 每条消息 @ 的最大人数（超出会自动分批）
    mention_first: bool = True     # True：先 @ 后正文；False：先正文后 @
)
```

* 当 `names` 为空时，将尝试 **@所有人**；若候选中无“所有人”，则**仅发送正文**（不造假 @）。
* 当 `names` 非空时，将按批量注入 `@成员` 并发送正文。&#x20;

**实现要点（稳定性）**

* 搜索框写入：优先 `ValuePattern.SetValue`，失败回退到 `Ctrl+A` + 粘贴；
* 面板滚动：**先把鼠标移入** `ChatContactMenu` 再滚轮（面板不可聚焦，滚轮需要光标在内）；
* 点击位：优先 `SelectionItem.Select()`，不行则**点击条目左侧文字区域**（避免点到滚动条）；
* 兜底：按“群成员”分隔条定位并点击其**上方一行**（即“所有人”行）；
* 全过程不使用 `ESC`；失败用 Backspace 清理输入。&#x20;

---

## 📦 依赖（统一）

* Python 3.8+
* `wxauto`、`pywinauto`、`pyautogui`、`Pillow`、`pyperclip`、`PyQt5`（后两者用于稳健粘贴）
  安装：

```bash
pip install -U wxauto pywinauto pyautogui pillow pyperclip PyQt5
```

---

## 🧱 目录结构（节选）

```
wxautomation/
├─ README.md
├─ wxautomation_Retrieve the group name from the address book/
│  ├─ Contact_list_group_chat_acquisition.py
│  └─ ...（模板图片若干）
└─ WeChat_group_@_everyone_function/
   └─ WeChat_group_@_everyone_function.py
```

（如你将 `WeChat_group_@_everyone_function.py` 放在根目录，也同样可运行）&#x20;

---

## ⚠️ 使用提示

* 建议 Windows 显示缩放 100%，避免 DPI 影响；
* 输入法若会把 `@` 后的拼写替换为特殊符号（如 `℡`），请临时切换英文输入或关闭联想；
* 不要在重要群组**首次**试验，先在测试群验证流程；
* 若微信版本 UI 有变更，请附 **Inspect 截图** 与日志开 Issue 反馈。&#x20;

---

## 🗺️ Roadmap

* 群成员导出 / 过滤规则
* 批量发送 / 定时发送
* 更多 UIA 封装、兼容更多微信版本
* DPI 自适应与可视化调试工具
  （欢迎 PR / Issue！）&#x20;

---

## 📜 免责声明

* 本项目与腾讯/微信、`wxauto` **无官方关联**；
* 仅用于**学习与研究** Windows UI 自动化；请遵守法律法规与平台条款；
* 使用本项目造成的任何后果由使用者自行承担。&#x20;

---

## 🤝 贡献指南

* 提交 PR 时请保持一致的代码风格，并附最小复现步骤/截图；
* 新想法或需求，欢迎在 Issues 中讨论。&#x20;

---

需要我把这份 README 直接改成英文版或添加 GIF 演示也没问题。
