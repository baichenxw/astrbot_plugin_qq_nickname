# QQ Profile Binding

[简体中文](README.md)

Register QQ numbers and nicknames for official QQ bots. The plugin fills AstrBot's existing sender ID and nickname fields while retaining the original OpenID. Other plugins can read the completed profile through the standard event methods.

## Languages

The plugin name, description and User profiles page support Simplified Chinese and English. The page follows the AstrBot Dashboard language, including changes made while it is open. English command aliases receive English replies; Chinese commands retain Chinese replies. User-entered profile values are never translated.

## Commands

- `/nickname Alex`: set a nickname, up to 32 characters. Spaces are allowed.
- `/bindqq 123456789`: register a 5–12 digit QQ number.
- `/myprofile`: view your nickname, full QQ number and original OpenID in private or group chats.
- `/clearprofile confirm`: delete your profile binding.

Chinese commands remain available: `/设置昵称`, `/绑定QQ`, `/我的资料`, and `/清除资料 确认`.

Changes apply from the next message. Fields that have not been registered keep their platform-provided values. QQ numbers are self-reported; the plugin does not verify ownership or retrieve them from the official API.

## Dashboard

Open **Plugins → QQ Profile Binding → User profiles** to search, add, edit or delete profiles. You must be signed in. Records are separated by bot instance ID and original OpenID. Revision checks prevent stale edits from overwriting newer changes.

**Manage profiles in Dashboard only** is off by default. When enabled, all plugin commands and aliases are blocked for every QQ user, including administrators, in private and group chats. Existing profile completion still works. The setting is saved immediately and survives a restart. Turn it off to allow commands again.

## Identity handling

An example completed identity:

```text
User ID: 123456789, Nickname: Alex, OpenID: ORIGINAL_UID
```

The original OpenID remains in `event.get_extra("qq_profile_original_openid")`, `event.message_obj.sender.original_openid`, and the unmodified raw message. This plugin always looks up profiles by their original OpenID.

With AstrBot 4.28.0, core administrator checks and session creation precede profile completion. Core permissions, UMOs, session allowlists and QQ reply targets retain the original identity. Other plugins see the completed sender ID; custom authorization in those plugins should use the original OpenID, rather than trusting a self-reported QQ number.

## Installation and data

Requires AstrBot `>=4.28.0`. Supported adapters: `qq_official` and `qq_official_webhook`. No additional runtime Python dependencies are needed.

Install the plugin in `data/plugins/astrbot_plugin_qq_nickname`, then reload it in Dashboard or restart AstrBot.

Profiles and settings are stored in `data/plugin_data/astrbot_plugin_qq_nickname/profiles.sqlite3`. Back up this file to preserve them. Updating the code does not replace it.
