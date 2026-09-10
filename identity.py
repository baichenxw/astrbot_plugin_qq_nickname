"""Decorate only the current provider-facing identity reminder."""

from astrbot.core.agent.message import TextPart


def decorate_identity(
    messages, openid: str, profile: dict, original_nickname: str = ""
) -> bool:
    """Keep the original OpenID alongside the standard filled sender fields.

    Args:
        messages: The current agent run's structured messages.
        openid: Original authenticated QQ identifier.
        profile: Bound presentation fields.
        original_nickname: Platform nickname used if no nickname is bound.

    Returns:
        Whether a current user message was decorated.
    """
    nickname = profile.get("nickname") or original_nickname or "未设置"
    qq = profile.get("qq", "")
    line = f"User ID: {qq or openid}, Nickname: {nickname}, OpenID: {openid}"
    if qq:
        line += " (QQ号为用户绑定资料，身份及权限以OpenID为准)"
    for message in reversed(messages):
        if message.role != "user":
            continue
        content = message.content
        if not isinstance(content, list):
            content = [TextPart(text=content or "")]
            message.content = content
        # Only AstrBot's separately generated reminder is eligible. Never scan
        # arbitrary user text or recalled memories for an ID-looking substring.
        for i in range(len(content) - 1, -1, -1):
            part = content[i]
            if not isinstance(part, TextPart) or not part.text.startswith(
                "<system_reminder>User ID: "
            ):
                continue
            old_line = (
                part.text[len("<system_reminder>") :]
                .split("\n", 1)[0]
                .split("</system_reminder>", 1)[0]
            )
            if not (
                old_line.startswith(f"User ID: {qq or openid}, Nickname: ")
                or f", OpenID: {openid}" in old_line
            ):
                continue
            replacement = part.model_copy(deep=True)
            replacement.text = part.text.replace(old_line, line, 1)
            content[i] = replacement
            return True
        content.append(TextPart(text=f"<system_reminder>{line}</system_reminder>"))
        return True
    return False
