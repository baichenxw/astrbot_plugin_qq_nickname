"""QQ profile commands, authenticated administration page, and LLM identity."""

import weakref

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools
from astrbot.api.web import error_response, json_response, request
from astrbot.core.star.filter.command import GreedyStr

from .identity import decorate_identity
from .localization import reply
from .profile_event import QQ_PLATFORMS, fill_profile, original_openid
from .store import ConflictError, ProfileStore

PLUGIN = "astrbot_plugin_qq_nickname"
_active_plugin = None


class ProfileFillFilter(filter.CustomFilter):
    """Fill sender fields before passive capture, without waking the bot."""

    def filter(self, event, cfg):
        plugin = _active_plugin() if _active_plugin else None
        if plugin:
            fill_profile(event, plugin.store)
        return False


class QQProfilePlugin(Star):
    """Fill normal sender fields while retaining the original OpenID."""

    def __init__(self, context: Context):
        super().__init__(context)
        self.store = ProfileStore(StarTools.get_data_dir(PLUGIN) / "profiles.sqlite3")
        global _active_plugin
        _active_plugin = weakref.ref(self)
        for route, handler, methods in (
            ("profiles", self.api_list, ["GET"]),
            ("profiles/save", self.api_save, ["POST"]),
            ("profiles/delete", self.api_delete, ["POST"]),
            ("settings", self.api_settings, ["POST"]),
        ):
            context.register_web_api(
                f"/{PLUGIN}/{route}", handler, methods, "QQ 身份绑定管理"
            )

    @filter.custom_filter(ProfileFillFilter, False, priority=10000)
    async def before_capture(self, event: AstrMessageEvent):
        """The filter fills sender fields and never activates this handler."""
        return

    @filter.on_llm_request(priority=10000)
    async def before_memory_recall(self, event, req):
        """Cover programmatically initiated LLM requests."""
        fill_profile(event, self.store)

    def localized_result(self, event, text):
        return event.plain_result(reply(event, text))

    def command_blocked(self, event) -> bool:
        if self.store.backend_only():
            event.stop_event()
            return True
        return False

    @filter.command("设置昵称", alias={"昵称", "nickname"}, priority=100)
    async def set_nickname(self, event: AstrMessageEvent, nickname: GreedyStr):
        """设置自己的昵称，例如 /设置昵称 小明；不带参数查看用法。"""
        if event.get_platform_name() not in QQ_PLATFORMS:
            yield self.localized_result(event, "此命令只用于 QQ 官方机器人。")
            event.stop_event()
            return
        if self.command_blocked(event):
            yield self.localized_result(
                event, "当前仅允许通过后台管理资料，QQ 端插件命令已关闭。请联系管理员。"
            )
            return
        if not nickname.strip():
            yield self.localized_result(
                event,
                "用法：/设置昵称 小明\n昵称最多 32 个字符。修改后从下一轮对话生效。",
            )
        else:
            try:
                profile = self.store.save(
                    event.get_platform_id(),
                    original_openid(event),
                    {"nickname": nickname},
                )
                yield self.localized_result(
                    event,
                    reply(
                        event,
                        "昵称已设置为：{nickname}。从下一轮对话生效。",
                        nickname=profile["nickname"],
                    ),
                )
            except ValueError as exc:
                yield self.localized_result(event, str(exc))
        event.stop_event()

    @filter.command("绑定QQ", alias={"绑定qq", "bindqq"}, priority=100)
    async def bind_qq(self, event: AstrMessageEvent, qq: GreedyStr):
        """登记自己的 QQ 号，例如 /绑定QQ 123456789。"""
        if event.get_platform_name() not in QQ_PLATFORMS:
            yield self.localized_result(event, "此命令只用于 QQ 官方机器人。")
            event.stop_event()
            return
        if self.command_blocked(event):
            yield self.localized_result(
                event, "当前仅允许通过后台管理资料，QQ 端插件命令已关闭。请联系管理员。"
            )
            return
        if not qq.strip():
            yield self.localized_result(
                event,
                "用法：/绑定QQ 你的QQ号\n这只登记资料，不改变管理员权限。建议在私聊中设置。",
            )
        else:
            try:
                self.store.save(
                    event.get_platform_id(), original_openid(event), {"qq": qq}
                )
                yield self.localized_result(
                    event, "QQ 号已登记。从下一轮对话生效，原始 OpenID 和权限保持不变。"
                )
            except ValueError as exc:
                yield self.localized_result(event, str(exc))
        event.stop_event()

    @filter.command("我的资料", alias={"myprofile"}, priority=100)
    async def my_profile(self, event: AstrMessageEvent):
        """查看当前账号的昵称、绑定 QQ 号和原始 OpenID。"""
        if event.get_platform_name() not in QQ_PLATFORMS:
            return
        if self.command_blocked(event):
            yield self.localized_result(
                event, "当前仅允许通过后台管理资料，QQ 端插件命令已关闭。请联系管理员。"
            )
            return
        p = self.store.get(event.get_platform_id(), original_openid(event)) or {}
        qq = p.get("qq") or reply(event, "未绑定")
        yield self.localized_result(
            event,
            reply(
                event,
                "昵称：{nickname}\nQQ：{qq}\nOpenID：{openid}",
                nickname=p.get("nickname") or reply(event, "未设置"),
                qq=qq,
                openid=original_openid(event),
            ),
        )
        event.stop_event()

    @filter.command("清除资料", alias={"clearprofile"}, priority=100)
    async def clear_profile(self, event: AstrMessageEvent, confirm: GreedyStr):
        """输入 /清除资料 确认，删除自己的绑定资料。"""
        if event.get_platform_name() not in QQ_PLATFORMS:
            return
        if self.command_blocked(event):
            yield self.localized_result(
                event, "当前仅允许通过后台管理资料，QQ 端插件命令已关闭。请联系管理员。"
            )
            return
        if confirm.strip().casefold() not in {"确认", "confirm"}:
            yield self.localized_result(
                event, "如需删除昵称和 QQ 绑定，请发送：/清除资料 确认"
            )
        else:
            p = self.store.get(event.get_platform_id(), original_openid(event))
            if p:
                self.store.delete(p["bot_id"], p["openid"], p["revision"])
            yield self.localized_result(
                event, "绑定资料已清除。原始 OpenID、权限和已有记忆保留。"
            )
        event.stop_event()

    @filter.on_agent_begin(priority=-1000)
    async def inject_profile(self, event: AstrMessageEvent, run_context):
        """Decorate the final user reminder after memory recall and core preparation.

        Args:
            event: Profile-enriched platform event.
            run_context: Current agent context, including prepared messages.
        """
        if event.get_platform_name() not in QQ_PLATFORMS:
            return
        profile = self.store.get(event.get_platform_id(), original_openid(event))
        if profile and (profile["nickname"] or profile["qq"]):
            decorate_identity(
                run_context.messages,
                original_openid(event),
                profile,
                event.get_sender_name(),
            )

    async def api_list(self):
        """List profiles via the Dashboard-authenticated plugin Page API."""
        if not request.username:
            return error_response("请登录 AstrBot 管理面板", status_code=401)
        result = self.store.list(
            str(request.query.get("q", ""))[:128],
            request.query.get("offset", 0, type=int),
        )
        result["bots"] = [
            p["id"]
            for p in self.context.get_config().get("platform", [])
            if p.get("type") in QQ_PLATFORMS
        ]
        result["backend_only"] = self.store.backend_only()
        return json_response(result)

    async def api_settings(self):
        """Persist the command switch; only authenticated Dashboard users may edit it."""
        if not request.username:
            return error_response("请登录 AstrBot 管理面板", status_code=401)
        data = await request.json(default={})
        if not isinstance(data, dict) or type(data.get("backend_only")) is not bool:
            return error_response("请提供有效的开关状态")
        self.store.set_backend_only(data["backend_only"])
        return json_response({"backend_only": self.store.backend_only()})

    async def api_save(self):
        """Validate and save an administrator edit with optimistic concurrency."""
        if not request.username:
            return error_response("请登录 AstrBot 管理面板", status_code=401)
        data = await request.json(default={})
        if not isinstance(data, dict):
            return error_response("请求必须是 JSON 对象")
        bots = {
            p["id"]
            for p in self.context.get_config().get("platform", [])
            if p.get("type") in QQ_PLATFORMS
        }
        if not isinstance(data.get("bot_id"), str) or data["bot_id"] not in bots:
            return error_response("请选择已配置的 QQ 官方机器人")
        if type(data.get("revision")) is not int:
            return error_response("缺少版本号，请刷新列表")
        try:
            profile = self.store.save(
                data.get("bot_id"),
                data.get("openid"),
                {"nickname": data.get("nickname", ""), "qq": data.get("qq", "")},
                data["revision"],
            )
            return json_response(profile)
        except ConflictError as exc:
            return error_response(str(exc), status_code=409)
        except ValueError as exc:
            return error_response(str(exc))

    async def api_delete(self):
        """Remove a selected profile without touching conversations or memories."""
        if not request.username:
            return error_response("请登录 AstrBot 管理面板", status_code=401)
        data = await request.json(default={})
        if not isinstance(data, dict) or type(data.get("revision")) is not int:
            return error_response("请求格式不正确")
        try:
            self.store.delete(data.get("bot_id"), data.get("openid"), data["revision"])
            return json_response({"deleted": True})
        except ConflictError as exc:
            return error_response(str(exc), status_code=409)
        except ValueError as exc:
            return error_response(str(exc))

    async def terminate(self):
        """Remove only the routes owned by this plugin instance."""
        global _active_plugin
        if _active_plugin and _active_plugin() is self:
            _active_plugin = None
        self.context.registered_web_apis[:] = [
            entry
            for entry in self.context.registered_web_apis
            if getattr(entry[1], "__self__", None) is not self
        ]
