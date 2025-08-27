# wxautomation · 开源「wxauto PLUS 功能替代」✨

> 非官方、零注入、零 Hook 的桌面微信自动化脚本集合。  
> 基于 Windows UIA（pywinauto） + 轻量图像匹配（pyautogui），逐步替代 `wxauto` PLUS 版的常用能力。

---

## 🧭 项目宗旨

- 我们不是 `wxauto` 的开发者；本仓库旨在提供一个**开源替代**，复刻并扩展其 PLUS 版本常用能力；
- 坚持可读、可维护、可复用：优先使用官方 UI 自动化接口（UIA），避免系统注入和复杂 Hook；
- 小步快跑，持续迭代：先从“获取群列表”做起，逐步扩展更多自动化能力；
- 已在常见桌面微信版本下验证（更高版本如有 UI 差异欢迎提 Issue）。

---

## 📂 当前功能模块

### 1) 从通讯录批量获取「最近群聊」名称
目录：`wxautomation_Retrieve the group name from the address book/`

- **作用**：从**通讯录管理**中批量获取「**最近群聊**」群名称；  
- **实现**：进入界面时使用 `pyautogui` 模板匹配，采集阶段切换到 `pywinauto (UIA)` 读取列表，**固定步长滚动 + 锚点续扫**，减少回弹/漏扫；  
- **运行**
  ```bash
  cd "wxautomation_Retrieve the group name from the address book"
  python Contact_list_group_chat_acquisition.py
````

---

### 2) 群聊 **@所有人 / @指定人**（新增）

目录：`WeChat_group_@_everyone_function/`
脚本：`WeChat_group_@_everyone_function.py`

**能做什么？**

* 一步到群：把群名精确写入**微信主界面搜索框** → **回车**进入**首个搜索结果**；
* 智能 @ 所有人：输入 `@` 后将鼠标**移入**“ChatContactMenu”面板、**滚到顶部**并**只点击**“所有人 / 全体成员 / 所有成员”；

  * 如果该节点不可直接选中，使用\*\*“群成员”分隔条**作为锚点，点击其**上方一行\*\*（等价“所有人”）；
  * **不造假 @**（候选中不存在“所有人”时仅发正文）；
  * **不使用 ESC**（避免关闭微信），失败仅用 Backspace 清理；
* 也支持 **@ 指定成员**（可多名，超量自动分批发送）。

**依赖（统一）**

```bash
pip install -U wxauto pywinauto pyautogui pillow pyperclip PyQt5
```

**快速开始（直接运行示例）**

```bash
cd WeChat_group_@_everyone_function
python WeChat_group_@_everyone_function.py
```

**在你自己的工程里调用**

> 目录名包含 `@` 时不便于 `import`，你可以把脚本重命名为 `wechat_group_at_all.py` 后再导入：

```python
from wxauto import WeChat
from wechat_group_at_all import bind_AtAll  # 把脚本重命名后这样导入

wx = WeChat()
bind_AtAll(wx)  # 给 wx 动态挂载 wx.AtAll(...)

group = "测试1群"
content = """通知：
下午xxxx
xxxx
测试使用"""

wx.AtAll(content, group)  # 若本群支持“所有人”，会真正插入 @所有人 并发送正文
```

**API**

```python
wx.AtAll(
    content: str,                 # 要发送的多行文本
    group: str,                   # 群名称（用于搜索框跳转）
    names: Iterable[str] = None,  # 可选：@ 指定成员名单
    max_per_msg: int = 12,        # 每条消息 @ 的最大人数（超出自动分批）
    mention_first: bool = True    # True：先 @ 后正文；False：先正文后 @
)
```

**稳定性要点**

* 搜索框写入：优先 `ValuePattern.SetValue`，失败回退到 `Ctrl+A` + 粘贴；
* 候选面板滚动：**先把鼠标移入** `ChatContactMenu` 再滚轮（该面板不可聚焦但支持滚轮）；
* 点击位：优先 UIA `Select()`，不行则**点击条目左侧文字区域**（避开滚动条）；
* 兜底：按“群成员”分隔条定位并点击其**上方一行**（“所有人”行）；
* 全程不按 `ESC`，失败仅 Backspace 清理输入。

---

## 📦 依赖（精简版）

* Python 3.8+
* `wxauto`、`pywinauto`、`pyautogui`、`Pillow`、`pyperclip`、`PyQt5`

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
│  └─ ...（模板图片）
└─ WeChat_group_@_everyone_function/
   └─ WeChat_group_@_everyone_function.py
```

---

## 👥 Contributors（贡献者）

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://github.com/1JSK1">
        <img src="https://github.com/1JSK1.png?size=96" width="80" height="80" style="border-radius:50%" alt="1JSK1"/>
        <br/><sub><b>1JSK1</b></sub>
      </a>
    </td>
  </tr>
</table>

> 添加更多贡献者：复制上面的 `<td>...</td>` 块并把 `用户名` 替换为对方 GitHub 用户名即可（头像地址通用：`https://github.com/<username>.png?size=96`，链接：`https://github.com/<username>`）。

---

## ⚠️ 使用提示

* 建议 Windows 显示缩放 100%（避免 DPI 影响矩形/坐标判断）；
* 部分输入法会把 `@` 后拼写替换为特殊符号（如 `℡`），请临时切换英文输入或关闭联想；
* 先在测试群验证流程，再在正式群使用；
* 微信 UI 如有变化，请附 **Inspect 截图** 与日志开 Issue。

---

## 🗺️ Roadmap

* 群成员导出 / 过滤规则
* 批量/定时发送
* 更多 UIA 封装 & 适配更多微信版本
* DPI 自适应与可视化调试工具

---

## 📜 免责声明

* 本项目与腾讯/微信、`wxauto` **无官方关联**；仅用于**学习研究** Windows UI 自动化；
* 使用本项目造成的任何后果由使用者自行承担。

---

## 🤝 贡献指南

* PR 请保持一致的代码风格，并附最小复现步骤/截图；
* 新想法或需求，欢迎在 Issues 中讨论。

```
