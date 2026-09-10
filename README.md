# QQ 身份绑定

[English](README.en.md)

为 QQ 官方机器人补全用户登记的 QQ 号和昵称。在消息进入其他插件的处理流程前，填入 AstrBot 原有的 `message_obj.sender.user_id` 和 `nickname` 字段。其他插件可通过 `get_sender_id()` 和 `get_sender_name()` 读取补全后的资料。

## 语言

插件名称、简介和用户资料页面支持简体中文、英文，跟随 AstrBot WebUI 的语言即时切换。使用英文命令别名时回复英文，中文命令保持中文。用户填写的昵称等内容不会被翻译。

## 使用

- `/设置昵称 小明`：设置昵称，允许空格，最多 32 个字符。
- `/绑定QQ 123456789`：登记 QQ 号，5–12 位数字。
- `/我的资料`：查看资料及原始 OpenID；私聊和群聊均显示完整登记的 QQ 号。
- `/清除资料 确认`：删除自己的绑定。

修改从下一条消息开始生效。未填写的字段沿用平台原值。QQ 号是自行登记的资料，插件不会从 QQ 官方接口反查、核验其归属。

在 AstrBot 后台的插件列表打开“QQ 身份绑定”，进入插件 Pages 的“用户资料”，可以搜索、添加、修改、删除绑定。管理页需要登录 AstrBot，资料按机器人 ID 和原始 OpenID 分开保存；编辑带版本检查，防止多人操作覆盖。

### 仅允许后台管理资料

用户资料页顶部提供此开关，**默认关闭**，切换后自动保存并立即生效。开启后，本插件在所有 QQ 官方机器人实例、私聊和群聊中禁用全部命令及其别名，包括设置昵称、绑定 QQ、我的资料、清除资料；QQ 管理员同样不能绕过。只有登录 AstrBot 后台才能管理资料和更改开关。

已绑定资料的自动补全不受影响。开关保存在插件资料数据库内，重启或重载插件仍保留。关闭开关即可恢复命令。

英文命令：`/nickname Alex`、`/bindqq 123456789`、`/myprofile`、`/clearprofile confirm`。

## 身份信息

补全后的消息示例：

```text
User ID: 123456789, Nickname: 小明, OpenID: 原始UID
```

原始 OpenID 保留在 `event.get_extra("qq_profile_original_openid")`、`event.message_obj.sender.original_openid` 和未修改的 `raw_message` 中。本插件自己的命令始终使用原始 OpenID 查找资料。

AstrBot v4.28.0 的管理员判断和会话建立先于补全执行，因此核心管理员权限、原有 UMO 和会话白名单保持原行为；QQ 发送仍使用原始消息中的 OpenID。其他插件会看到补全后的发送者 ID：若其他插件自行按 QQ 号授权，需要自行使用原始 OpenID 判断。请勿将自报资料作为认证凭据。


## 安装与数据

支持 QQ 官方 WebSocket（`qq_official`）和 Webhook（`qq_official_webhook`）适配器。

将插件文件夹放入 `data/plugins/astrbot_plugin_qq_nickname`，重启 AstrBot 或使用后台插件加载。支持 AstrBot `>=4.28.0`，无新增 Python 依赖。

资料数据库位于 `data/plugin_data/astrbot_plugin_qq_nickname/profiles.sqlite3`。备份时应备份此文件。卸载代码不会自动删除资料库。

实现参考 [AstrBot 消息事件文档](https://docs.astrbot.app/dev/star/guides/listen-message-event.html) 和 [插件 Pages 文档](https://docs.astrbot.app/dev/star/guides/plugin-pages.html)。
