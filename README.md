````markdown
<!--
  Beautified README.md for the repository.
  Focus: Stable UIA automation for WeChat, plus "@所有人 / @成员" feature.
-->

<h1 align="center">wxautomation · WeChat UIA Automation ✨</h1>

<p align="center">
  非官方、零注入、零 Hook 的 <b>桌面微信自动化</b> 脚本集合。<br/>
  基于 Windows UIA（pywinauto）实现：<b>搜索直达群聊</b>、<b>@所有人</b> / <b>@指定成员</b>、批量发送等。
</p>

<p align="center">
  <a href="https://www.python.org/"><img alt="Python 3.8+" src="https://img.shields.io/badge/Python-3.8%2B-3776ab?logo=python&logoColor=white"></a>
  <img alt="Windows" src="https://img.shields.io/badge/Platform-Windows-00a2ed?logo=windows&logoColor=white">
  <img alt="UI Automation" src="https://img.shields.io/badge/Automation-UIA%20(pywinauto)-6a5acd">
  <img alt="No Injection" src="https://img.shields.io/badge/No-Hook%20%2F%20Injection-brightgreen">
</p>

---

## 目录
- [特性](#特性)
- [安装](#安装)
- [快速开始](#快速开始)
- [API](#api)
- [工作原理](#工作原理)
- [目录结构](#目录结构)
- [排错与建议](#排错与建议)
- [贡献者](#贡献者)
- [免责声明](#免责声明)

---

## 特性

- ✅ **搜索直达群聊**：将群名写入 *微信主界面搜索框*，一键回车进入第一个匹配结果  
- ✅ **@所有人**（真实有效）：  
  - 输入 `@` → 自动将鼠标**移入**候选面板 `ChatContactMenu` → **滚到顶部** → **仅点击**“所有人 / 全体成员 / 所有成员”  
  - 若控件不响应：使用“**群成员**”分隔条做锚点，点击其**上方一行**（稳定选中“所有人”）
- ✅ **@指定成员**：支持名单、自动分批  
- ✅ **安全发送**：不使用 `ESC`（避免误关微信），失败使用 Backspace 清理  
- ✅ **可插拔**：对外暴露 `bind_AtAll(wx)`，一行挂载 `wx.AtAll(...)` 即可使用

---

## 安装

```bash
pip install -U wxauto pywinauto pyautogui pillow pyperclip PyQt5
````

> 说明
>
> * `pyperclip` / `PyQt5` 用于**可靠粘贴中文**（剪贴板兜底）
> * 建议 **Python 3.8+**，Windows 显示缩放 **100%**

---

## 快速开始

### 方式 A：直接运行示例脚本

```bash
cd WeChat_group_@_everyone_function
python WeChat_group_@_everyone_function.py
```

### 方式 B：集成到你的工程

> 目录名包含 `@` 不便于 import；可将脚本重命名为 `wechat_group_at_all.py` 再导入。

```python
from wxauto import WeChat
from wechat_group_at_all import bind_AtAll   # ← 将脚本重命名后这样导入

wx = WeChat()
bind_AtAll(wx)   # 动态挂载 wx.AtAll(...)

group = "测试1群"
content = """通知：
下午xxxx
xxxx
测试使用"""

wx.AtAll(content, group)  # 若本群支持“所有人”，会真正插入 @所有人 并发送正文
```

---

## API

```python
wx.AtAll(
    content: str,                 # 要发送的多行文本
    group: str,                   # 群名称（用于搜索框跳转）
    names: Iterable[str] = None,  # 可选：@ 指定成员名单（为空则尝试 @所有人）
    max_per_msg: int = 12,        # 每条消息中 @ 的最大人数（超出自动分批）
    mention_first: bool = True    # True：先 @ 后正文；False：先正文后 @
) -> bool
```

**行为说明**

* 当 `names` 为空：仅当候选面板存在“所有人/全体成员/所有成员”时才会**真实插入** @所有人；否则**只发正文**（不造假 @）。
* 当 `names` 非空：逐个插入 `@成员`，必要时按 `max_per_msg` 自动分批。

---

## 工作原理

1. **前置微信主窗**：通过 UIA 匹配 `class=WeChatMainWndForPC`
2. **写入搜索框**：优先 `ValuePattern.SetValue`，失败回退 `Ctrl+A` + 粘贴；回车进入首条
3. **定位输入框**：过滤掉左侧“搜索”编辑框，聚焦底部消息编辑区
4. **触发候选面板**：输入 `@`，查找 `Pane "ChatContactMenu"`
5. **滚动与选择**：将鼠标移入面板 → 滚到顶 →

   * 首选：定位“所有人/全体成员/所有成员”文本节点并**点其左侧文字区域**
   * 兜底：定位“群成员”分隔条，点击其**上方一行**
6. **粘贴正文并发送**：避免 ESC，异常用 Backspace 清理

---

## 目录结构

```
wxautomation/
├─ README.md
├─ wxautomation_Retrieve the group name from the address book/
│  ├─ Contact_list_group_chat_acquisition.py
│  └─ ...（模板图片）
└─ WeChat_group_@_everyone_function/
   └─ WeChat_group_@_everyone_function.py
```

> 说明：通讯录模块用于批量获取“最近群聊”名称；`@所有人/成员` 模块提供消息发送自动化。

---

## 排错与建议

* **输入法替换 `@` 后字符为 `℡` 等**
  切换到**英文输入**或关闭“特殊符号联想”；我们的脚本会在真正点中“所有人”后插入空格完成 @，避免误替换。
* **滚轮不生效**
  我们已在滚动前将鼠标**移动到候选面板内部**；若你的环境依然无效，可尝试把显示缩放改为 **100%**。
* **微信 UI 变化**
  请附上 **Inspect 截图**（尤其是搜索框、候选面板）以及运行日志开 Issue。

---

## 贡献者

<p align="left">
  <a href="https://github.com/1JSK1" title="1JSK1">
    <img src="https://github.com/1JSK1.png?size=96" width="80" height="80" style="border-radius:50%; margin-right:12px;" alt="1JSK1"/>
  </a>
</p>

> 想新增贡献者？复制上面的头像标签，将链接与用户名替换为对方的 GitHub 主页即可：
> `https://github.com/<username>` 与 `https://github.com/<username>.png?size=96`

---

## 免责声明

* 本项目与腾讯/微信、`wxauto` **无官方关联**；仅用于**学习与研究** Windows UI 自动化。
* 使用本项目造成的任何后果由使用者自行承担；请遵守相关法律法规及平台条款。

```
```
