````markdown
 wxautomation · 开源「wxauto PLUS 功能替代」✨

> 非官方、零注入、零 Hook 的桌面微信自动化脚本集合。  
> 基于 Windows UIA（pywinauto） + 轻量图像匹配（pyautogui），逐步替代 `wxauto` PLUS 版的常用能力。


 🧭 项目宗旨

- 我们不是 `wxauto` 的开发者；本仓库旨在提供一个**开源替代**，复刻并扩展其 PLUS 版本常用能力；
- 坚持可读、可维护、可复用：优先使用官方 UI 自动化接口（UIA），避免系统注入和复杂 Hook；
- 小步快跑，持续迭代。
- 适用于微信3.9.12版本，4.0及以上版本未测试

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

### 2) 群聊“@所有人 / @指定成员”（新增）

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

---

## 🧱 目录结构（简）

```
wxautomation/
├─ README.md
├─ wxautomation_Retrieve the group name from the address book/
│  └─ Contact_list_group_chat_acquisition.py
└─ WeChat_group_@_everyone_function/
   └─ WeChat_group_@_everyone_function.py
```

---

## 🔧 常见问题

* **@ 后被输入法替换成特殊符号**：切英文输入或关闭符号联想；脚本会在真正点中“所有人”后补空格完成 @。
* **滚轮不动**：确保显示缩放 100%；脚本已在滚动前把鼠标移动到面板内部。

---

## 👥 Contributors

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
