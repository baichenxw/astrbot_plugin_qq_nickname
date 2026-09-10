"""Fill normal sender fields before downstream plugins inspect the event."""

QQ_PLATFORMS = {"qq_official", "qq_official_webhook"}
ORIGINAL_KEY = "qq_profile_original_openid"


def original_openid(event) -> str:
    return event.get_extra(ORIGINAL_KEY) or event.get_sender_id()


def fill_profile(event, store) -> bool:
    """Fill sender fields, preserving the authenticated source and session.

    Args:
        event: QQ event after core authorization and session initialization.
        store: Profile store indexed by original OpenID and bot instance.

    Returns:
        Whether any bound sender field was filled.
    """
    if event.get_platform_name() not in QQ_PLATFORMS:
        return False
    # An event can pass through multiple hooks. Never use the mapped QQ as a key.
    openid = original_openid(event)
    event.set_extra(ORIGINAL_KEY, openid)
    sender = event.message_obj.sender
    sender.original_openid = openid
    profile = store.get(event.get_platform_id(), openid)
    if not profile:
        return False
    if profile["qq"]:
        sender.user_id = profile["qq"]
    if profile["nickname"]:
        sender.nickname = profile["nickname"]
    return bool(profile["qq"] or profile["nickname"])
