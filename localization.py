"""Translate English command aliases without changing the bot's global language."""

import json
import re
from pathlib import Path

_ROOT = Path(__file__).parent / ".astrbot-plugin" / "i18n"
_ZH = json.loads((_ROOT / "zh-CN.json").read_text(encoding="utf-8"))
_EN = json.loads((_ROOT / "en-US.json").read_text(encoding="utf-8"))
_MESSAGES = {value: _EN["commands"][key] for key, value in _ZH["commands"].items()}
_MESSAGES.update(
    {
        value: _EN["pages"]["profiles"]["errors"][key]
        for key, value in _ZH["pages"]["profiles"]["errors"].items()
    }
)


def reply(event, text: str, **values) -> str:
    """Use English for the English aliases and preserve Chinese command replies."""
    if re.match(
        r"^/?(?:nickname|bindqq|myprofile|clearprofile)(?:\s|$)",
        event.message_str.strip(),
        re.IGNORECASE,
    ):
        text = _MESSAGES.get(text, text)
    return text.format(**values) if values else text
